import csv
import io
import json

from openpyxl import Workbook

from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse

from smartlead.api.v1.schemas.leads import (
    LeadResult,
    LeadsProcessResponse,
    SendOutreachEmailRequest,
    SendOutreachEmailResponse,
    UpdateFinalOutreachRequest,
    UpdateRecipientRequest
)
from smartlead.core.settings import Settings, get_settings
from smartlead.services.csv_ingest import parse_leads_csv, parse_leads_csv_bytes
from smartlead.services.excel_ingest import (
    parse_leads_xlsx_bytes,
    parse_leads_xls_bytes,
)
from smartlead.services.gmail_outreach import send_plain_email
from smartlead.services.icp_store import get_active_icp
from smartlead.services.pipeline import iter_pipeline_events, run_pipeline, run_single_lead
from smartlead.services.pipeline_context import (
    get_last_lead_results,
    last_run_summary,
    patch_final_outreach,
    replace_lead_at_index,
    set_last_lead_results,
    patch_recipient_override
)

router = APIRouter(prefix="/leads", tags=["leads"])


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

def _get_ext(filename: str | None) -> str:
    return (filename or "").lower().rsplit(".", 1)[-1] if filename and "." in filename else ""


def parse_leads_upload_bytes(filename: str | None, raw: bytes):
    ext = _get_ext(filename)

    if ext == "csv":
        return parse_leads_csv_bytes(raw)
    if ext == "xlsx":
        return parse_leads_xlsx_bytes(raw)
    if ext == "xls":
        return parse_leads_xls_bytes(raw)

    return [], ["Unsupported file type. Upload .csv, .xlsx, or .xls."]

async def parse_leads_upload(file: UploadFile):
    raw = await file.read()
    return parse_leads_upload_bytes(file.filename, raw)

@router.get("/context")
def get_pipeline_context_status() -> dict[str, bool | int]:
    return last_run_summary()


@router.get("/outreach-mail-status")
def outreach_mail_status(settings: Settings = Depends(get_settings)) -> dict[str, bool]:
    return {"configured": settings.gmail_outreach_configured}


@router.get("/export-csv")
def export_last_run_csv() -> Response:
    rows = get_last_lead_results()
    if not rows:
        raise HTTPException(status_code=404, detail="No results. Run the pipeline first.")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "company_name",
            "website",
            "contact_email",
            "csv_email",
            "discovered_email",
            "recipient_override",
            "recipient_effective",
            "score",
            "subject",
            "body",
            "is_final_edited",
        ],
    )
    for r in rows:
        o = r.effective_outreach()
        writer.writerow(
            [
                r.lead.company_name,
                r.lead.website,
                r.lead.contact_email,
                r.lead.contact_email,  # csv_email
                r.discovered_contact_email or "",  # discovered_email
                r.recipient_override or "",  # recipient_override
                r.effective_recipient(),  # recipient_effective
                r.score.score,
                o.subject,
                o.body,
                "yes" if r.final_outreach is not None else "no",  # is_final_edited
            ],
        )
    content = "\ufeff" + buf.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="smartlead_last_run.csv"',
        },
    )


@router.get("/export-json")
def export_last_run_json() -> JSONResponse:
    rows = get_last_lead_results()
    if not rows:
        raise HTTPException(status_code=404, detail="No results. Run the pipeline first.")

    payload: list[dict[str, object]] = []
    for r in rows:
        o = r.effective_outreach()
        payload.append(
            {
                "company_name": r.lead.company_name,
                "website": r.lead.website,
                "contact_email": r.lead.contact_email,
                "csv_email": r.lead.contact_email,  # from CSV
                "discovered_email": r.discovered_contact_email or "",  # from website discovery
                "recipient_override": r.recipient_override or "",  # user edit
                "recipient_effective": r.effective_recipient(),  # the one that will be used
                "score": r.score.score,
                "subject": o.subject,
                "body": o.body,
                "is_final_edited": "yes" if r.final_outreach is not None else "no",
            },
        )
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": 'attachment; filename="smartlead_last_run.json"',
        },
    )


@router.put("/{lead_index}/final-outreach", response_model=LeadResult)
def save_final_outreach(
    lead_index: int = Path(..., ge=0),
    body: UpdateFinalOutreachRequest = ...,
) -> LeadResult:
    rows = get_last_lead_results()
    if not rows or lead_index >= len(rows):
        raise HTTPException(
            status_code=404,
            detail="No lead at this index. Run the pipeline first.",
        )
    from smartlead.api.v1.schemas.leads import OutreachDraft

    try:
        return patch_final_outreach(
            lead_index,
            OutreachDraft(subject=body.subject.strip(), body=body.body),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{lead_index}/regenerate", response_model=LeadResult)
def regenerate_single_lead(
    lead_index: int = Path(..., ge=0),
    settings: Settings = Depends(get_settings),
) -> LeadResult:
    if not settings.use_mock_llm and not settings.has_active_llm_credentials:
        raise HTTPException(
            status_code=503,
            detail=settings.live_llm_config_error_detail(),
        )

    rows = get_last_lead_results()
    if not rows or lead_index >= len(rows):
        raise HTTPException(
            status_code=404,
            detail="No lead at this index. Run the pipeline first.",
        )
    
    lead = rows[lead_index].lead
    icp = get_active_icp()
    try:
        old = rows[lead_index]
        new_row = run_single_lead(lead, icp, settings)
        new_row = new_row.model_copy(update={"recipient_override": old.recipient_override})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Regenerate failed: {exc}") from exc

    try:
        replace_lead_at_index(lead_index, new_row)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return new_row


@router.post("/send-outreach-email", response_model=SendOutreachEmailResponse)
def send_outreach_email(
    body: SendOutreachEmailRequest,
    settings: Settings = Depends(get_settings),
) -> SendOutreachEmailResponse:
    if not settings.gmail_outreach_configured:
        raise HTTPException(
            status_code=503,
            detail="Set SENDER_EMAIL and GMAIL_SMTP_KEY (Gmail App Password).",
        )

    rows = get_last_lead_results()
    if not rows or body.lead_index >= len(rows):
        raise HTTPException(
            status_code=404,
            detail="No lead at this index. Run the pipeline first.",
        )

    lead_result = rows[body.lead_index]
    draft = lead_result.effective_outreach()

    to_raw = (str(body.to_email) if body.to_email else lead_result.effective_recipient()).strip()
    if not to_raw:
        raise HTTPException(
            status_code=400,
            detail=(
                "No recipient. Add email in CSV, save a discovered/recipient override in the UI, "
                "or pass to_email when sending."
            ),
        )

    try:
        send_plain_email(
            settings,
            to_addr=to_raw,
            subject=draft.subject,
            body=draft.body,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"SMTP failed: {exc}") from exc

    return SendOutreachEmailResponse(to=to_raw)


@router.post("/process", response_model=LeadsProcessResponse)
async def process_leads_csv(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> LeadsProcessResponse:
    ext = _get_ext(file.filename)
    if ext not in {"csv", "xlsx", "xls"}:
        raise HTTPException(
            status_code=400,
            detail="Please upload a .csv, .xlsx, or .xls file.",
        )
    
    if file.content_type and file.content_type not in {
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }:
        # optional: log instead of failing
        print(f"Warning: unexpected content-type {file.content_type}")

    if not settings.use_mock_llm and not settings.has_active_llm_credentials:
        raise HTTPException(
            status_code=503,
            detail=settings.live_llm_config_error_detail(),
        )

    leads, parse_errors = await parse_leads_upload(file)
    if not leads:
        raise HTTPException(
            status_code=400,
            detail={"message": "No valid leads parsed.", "errors": parse_errors},
        )

    icp = get_active_icp()
    try:
        results = run_pipeline(leads, icp, settings)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Pipeline error: {exc}") from exc

    set_last_lead_results(results)

    return LeadsProcessResponse(leads=results, errors=parse_errors)


@router.post("/process-stream")
async def process_leads_csv_stream(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    ext = _get_ext(file.filename)
    if ext not in {"csv", "xlsx", "xls"}:
        raise HTTPException(
            status_code=400,
            detail="Please upload a .csv, .xlsx, or .xls file.",
        )

    if file.content_type and file.content_type not in {
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }:
        # optional: log instead of failing
        print(f"Warning: unexpected content-type {file.content_type}")
        
    if not settings.use_mock_llm and not settings.has_active_llm_credentials:
        raise HTTPException(
            status_code=503,
            detail=settings.live_llm_config_error_detail(),
        )

    raw = await file.read()
    leads, parse_errors = parse_leads_upload_bytes(file.filename, raw)
    if not leads:
        raise HTTPException(
            status_code=400,
            detail={"message": "No valid leads parsed.", "errors": parse_errors},
        )

    icp = get_active_icp()

    def event_generator():
        collected: list[LeadResult] = []
        try:
            for ev in iter_pipeline_events(leads, icp, settings, parse_errors):
                if ev.get("event") == "lead" and "data" in ev:
                    collected.append(LeadResult.model_validate(ev["data"]))
                yield _sse(ev)
                if ev.get("event") == "complete":
                    set_last_lead_results(collected)
        except Exception as exc:  # noqa: BLE001
            yield _sse({"event": "error", "message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.put("/{lead_index}/recipient", response_model=LeadResult)
def save_recipient_override(
    lead_index: int = Path(..., ge=0),
    body: UpdateRecipientRequest = ...,
) -> LeadResult:
    rows = get_last_lead_results()
    if not rows or lead_index >= len(rows):
        raise HTTPException(status_code=404, detail="No lead at this index. Run the pipeline first.")
    try:
        return patch_recipient_override(lead_index, body.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
@router.get("/export-xlsx")
def export_last_run_xlsx() -> Response:
    rows = get_last_lead_results()
    if not rows:
        raise HTTPException(status_code=404, detail="No results. Run the pipeline first.")

    wb = Workbook()
    ws = wb.active
    ws.title = "smartlead_last_run"

    headers = [
        "company_name",
        "website",
        "contact_email",
        "csv_email",
        "discovered_email",
        "recipient_override",
        "recipient_effective",
        "score",
        "subject",
        "body",
        "is_final_edited",
    ]
    ws.append(headers)

    for r in rows:
        o = r.effective_outreach()
        ws.append([
            r.lead.company_name,
            r.lead.website,
            r.lead.contact_email,
            r.lead.contact_email,
            r.discovered_contact_email or "",
            r.recipient_override or "",
            r.effective_recipient(),
            r.score.score,
            o.subject,
            o.body,
            "yes" if r.final_outreach is not None else "no",
        ])

    out = io.BytesIO()
    wb.save(out)
    data = out.getvalue()

    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="smartlead_last_run.xlsx"'},
    )