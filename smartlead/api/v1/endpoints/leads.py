from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from smartlead.api.v1.schemas.leads import LeadsProcessResponse
from smartlead.core.settings import Settings, get_settings
from smartlead.services.csv_ingest import parse_leads_csv
from smartlead.services.icp import get_default_icp
from smartlead.services.pipeline import run_pipeline

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/process", response_model=LeadsProcessResponse)
async def process_leads_csv(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> LeadsProcessResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    if not settings.use_mock_llm and not (settings.gemini_api_key or "").strip():
        raise HTTPException(
            status_code=503,
            detail="Live mode requires GEMINI_API_KEY (or GOOGLE_API_KEY). Or set USE_MOCK_LLM=true.",
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

    return LeadsProcessResponse(leads=results, errors=parse_errors)