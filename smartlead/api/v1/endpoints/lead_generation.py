import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from smartlead.api.v1.schemas.lead_generation import (
    GeneratedLead,
    GeneratedLeadsStateResponse,
    LeadGenerationRequest,
    LeadGenerationResponse,
)
from smartlead.api.v1.schemas.leads import LeadInput, LeadResult, LeadsProcessResponse
from smartlead.core.settings import Settings, get_settings
from smartlead.services.generated_leads_store import (
    generated_leads_summary,
    get_generated_leads,
    get_generated_warnings,
    set_generated_leads,
)
from smartlead.services.icp_store import get_active_icp
from smartlead.services.leadgen_factory import get_lead_generator
from smartlead.services.pipeline import iter_pipeline_events, run_pipeline
from smartlead.services.pipeline_context import set_last_lead_results

router = APIRouter(prefix="/lead-generation", tags=["lead-generation"])

_MOCK_GENERATED_LEADS: list[tuple[str, str, str]] = [
    ("Openxcell - AI Development Company", "https://www.openxcell.com/", ""),
    ("Zoho Corporation", "https://www.zoho.com/", "sales@zoho.com"),
    ("Persistent Systems", "https://www.persistent.com/", "info@persistent.com"),
    ("L&T Technology Services", "https://www.ltts.com/", "info@ltts.com"),
    ("Tech Mahindra", "https://www.techmahindra.com/", "corporate@techmahindra.com"),
    ("Wipro", "https://www.techmahindra.com/", "info@wipro.com"),
    ("Amul", "https://amul.com/", "gcmmf@amul.coop"),
]

_QUOTA_WARNING_TOKENS = (
    "quota exhausted",
    "quota exceeded",
    "resource_exhausted",
    "generate_content_free_tier_requests",
)


def _is_quota_warning(msg: str) -> bool:
    low = (msg or "").lower()
    return any(token in low for token in _QUOTA_WARNING_TOKENS)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/state", response_model=GeneratedLeadsStateResponse)
def generated_state() -> GeneratedLeadsStateResponse:
    state = generated_leads_summary()
    return GeneratedLeadsStateResponse.model_validate(state)


@router.post("/generate", response_model=LeadGenerationResponse)
def generate_leads(
    body: LeadGenerationRequest,
    settings: Settings = Depends(get_settings),
) -> LeadGenerationResponse:
    if settings.use_mock_llm:
        payload = [
            GeneratedLead(
                company_name=company_name,
                website=website,
                contact_email=email,
                confidence=0.99,
                source_query="mock",
                source_url=website,
            )
            for company_name, website, email in _MOCK_GENERATED_LEADS
        ]
        lead_inputs = [
            LeadInput(
                company_name=row.company_name,
                website=row.website,
                contact_email=row.contact_email,
            )
            for row in payload
        ]
        warnings = ["Mock mode is enabled. Returned fixed demo leads."]
        set_generated_leads(lead_inputs, warnings)
        return LeadGenerationResponse(
            leads=payload,
            warnings=warnings,
            generated_count=len(payload),
        )

    if not settings.has_active_leadgen_credentials:
        raise HTTPException(
            status_code=503,
            detail=settings.leadgen_config_error_detail(),
        )

    try:
        service = get_lead_generator(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    try:
        generated, lead_inputs, warnings = service.generate(
            geo=body.geo,
            sector=body.sector,
            keywords=body.keywords,
            max_results=body.max_results,
            enable_email_discovery=body.enable_email_discovery,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Lead generation failed: {exc}") from exc

    if not lead_inputs:
        raise HTTPException(
            status_code=400,
            detail={"message": "No leads generated.", "warnings": warnings},
        )

    # If we successfully generated leads, suppress quota noise in user-facing warnings.
    warnings = [w for w in warnings if not _is_quota_warning(w)]

    set_generated_leads(lead_inputs, warnings)

    payload = [
        GeneratedLead(
            company_name=row.company_name,
            website=row.website,
            contact_email=row.contact_email,
            confidence=row.confidence,
            source_query=row.source_query,
            source_url=row.source_url,
        )
        for row in generated
    ]

    return LeadGenerationResponse(
        leads=payload,
        warnings=warnings,
        generated_count=len(payload),
    )


@router.post("/run-pipeline", response_model=LeadsProcessResponse)
def run_pipeline_on_generated(
    settings: Settings = Depends(get_settings),
) -> LeadsProcessResponse:
    if not settings.use_mock_llm and not settings.has_active_llm_credentials:
        raise HTTPException(
            status_code=503,
            detail=settings.live_llm_config_error_detail(),
        )

    leads = get_generated_leads()
    warnings = get_generated_warnings()
    if not leads:
        raise HTTPException(
            status_code=400,
            detail="No generated leads found. Run /lead-generation/generate first.",
        )

    icp = get_active_icp()
    try:
        results = run_pipeline(leads, icp, settings)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Pipeline error: {exc}") from exc

    set_last_lead_results(results)
    return LeadsProcessResponse(leads=results, errors=warnings)


@router.post("/run-pipeline-stream")
def run_pipeline_on_generated_stream(
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    if not settings.use_mock_llm and not settings.has_active_llm_credentials:
        raise HTTPException(
            status_code=503,
            detail=settings.live_llm_config_error_detail(),
        )

    leads = get_generated_leads()
    warnings = get_generated_warnings()
    if not leads:
        raise HTTPException(
            status_code=400,
            detail="No generated leads found. Run /lead-generation/generate first.",
        )

    icp = get_active_icp()

    def event_generator():
        collected: list[LeadResult] = []
        try:
            for ev in iter_pipeline_events(leads, icp, settings, warnings):
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
