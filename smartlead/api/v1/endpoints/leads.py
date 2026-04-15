from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from smartlead.api.v1.schemas.leads import LeadsProcessResponse
from smartlead.core.settings import Settings, get_settings
from smartlead.services.csv_ingest import parse_leads_csv
from smartlead.services.icp import get_default_icp
from smartlead.services.pipeline import run_pipeline
from smartlead.services.pipeline_context import last_run_summary, set_last_lead_results

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/context")
def get_pipeline_context_status() -> dict[str, bool | int]:
    """Whether the server has a last completed run (for UI hints)."""
    return last_run_summary()


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

    icp = get_default_icp()
    try:
        results = run_pipeline(leads, icp, settings)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Pipeline error: {exc}") from exc

    set_last_lead_results(results)

    return LeadsProcessResponse(leads=results, errors=parse_errors)