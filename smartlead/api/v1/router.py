from fastapi import APIRouter

from smartlead.api.v1.endpoints import chat, health, icp, lead_generation, leads

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(chat.router)
api_router.include_router(leads.router)
api_router.include_router(icp.router)
api_router.include_router(lead_generation.router)