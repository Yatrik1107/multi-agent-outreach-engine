from fastapi import APIRouter

from smartlead.services.icp import ICP
from smartlead.services.icp_store import get_active_icp, reset_icp_to_default, set_active_icp

router = APIRouter(prefix="/icp", tags=["icp"])


@router.get("", response_model=ICP)
def read_icp() -> ICP:
    return get_active_icp()


@router.put("", response_model=ICP)
def update_icp(body: ICP) -> ICP:
    set_active_icp(body)
    return get_active_icp()


@router.post("/reset", response_model=ICP)
def reset_icp() -> ICP:
    return reset_icp_to_default()