import json

from fastapi.responses import StreamingResponse

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from smartlead.api.v1.schemas.leads import (
    LeadsProcessResponse,
    LeadResult,
    SendOutreachEmailRequest,
    SendOutreachEmailResponse,
)
from smartlead.services.gmail_outreach import send_plain_email
from smartlead.core.settings import Settings, get_settings
from smartlead.services.csv_ingest import parse_leads_csv, parse_leads_csv_bytes
from smartlead.services.icp_store import get_active_icp
from smartlead.services.pipeline import run_pipeline, iter_pipeline_events
from smartlead.services.pipeline_context import (
    get_last_lead_results,
    last_run_summary,
    set_last_lead_results,
)

router = APIRouter(prefix="/leads", tags=["leads"])


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

@router.get("/context")
def get_pipeline_context_status() -> dict[str, bool | int]:
    """Whether the server has a last completed run (for UI hints)."""
    return last_run_summary()

@router.get("/outreach-mail-status")
def outreach_mail_status(settings: Settings = Depends(get_settings)) -> dict[str, bool]:
    return {"configured": settings.gmail_outreach_configured}


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
    to_raw = (str(body.to_email) if body.to_email else lead_result.lead.contact_email or "").strip()
    if not to_raw:
        raise HTTPException(
            status_code=400,
            detail="No recipient. Add contact_email to CSV or pass to_email.",
        )

    try:
        send_plain_email(
            settings,
            to_addr=to_raw,
            subject=lead_result.outreach.subject,
            body=lead_result.outreach.body,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"SMTP failed: {exc}") from exc

    return SendOutreachEmailResponse(to=to_raw)

@router.post("/process", response_model=LeadsProcessResponse)
async def process_leads_csv(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> LeadsProcessResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    if not settings.use_mock_llm and not settings.has_active_llm_credentials:
        raise HTTPException(
            status_code=503,
            detail=settings.live_llm_config_error_detail(),
        )

    leads, parse_errors = await parse_leads_csv(file)
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
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    if not settings.use_mock_llm and not settings.has_active_llm_credentials:
        raise HTTPException(
            status_code=503,
            detail=settings.live_llm_config_error_detail(),
        )

    raw = await file.read()
    leads, parse_errors = parse_leads_csv_bytes(raw)
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