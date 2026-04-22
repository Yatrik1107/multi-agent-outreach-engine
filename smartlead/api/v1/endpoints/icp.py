from fastapi import APIRouter, HTTPException

from smartlead.api.v1.schemas.icp import (
    ApplyTemplateRequest,
    ICPStateResponse,
    IndustryTemplateResponse,
)
from smartlead.services.icp import ICP
from smartlead.services.icp import get_industry_templates
from smartlead.services.icp_store import (
    apply_template_defaults,
    get_active_icp,
    get_active_template_id,
    reset_icp_to_default,
    set_active_icp,
)

router = APIRouter(prefix="/icp", tags=["icp"])


def _build_state() -> ICPStateResponse:
    icp = get_active_icp()
    return ICPStateResponse(
        active_template_id=get_active_template_id(),
        target_industries=icp.target_industries,
        keywords=icp.keywords,
        notes=icp.notes,
    )


@router.get("", response_model=ICP)
def read_icp() -> ICP:
    return get_active_icp()


@router.get("/templates", response_model=list[IndustryTemplateResponse])
def read_icp_templates() -> list[IndustryTemplateResponse]:
    return [IndustryTemplateResponse.model_validate(t.model_dump()) for t in get_industry_templates()]


@router.post("/apply-template", response_model=ICPStateResponse)
def apply_icp_template(body: ApplyTemplateRequest) -> ICPStateResponse:
    try:
        apply_template_defaults(body.template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _build_state()


@router.put("", response_model=ICP)
def update_icp(body: ICP) -> ICP:
    set_active_icp(body)
    return get_active_icp()


@router.post("/reset", response_model=ICP)
def reset_icp() -> ICP:
    return reset_icp_to_default()