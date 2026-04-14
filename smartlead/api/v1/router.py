from fastapi import APIRouter

from smartlead.api.v1.endpoints import chat, health, leads

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(chat.router)
api_router.include_router(leads.router)