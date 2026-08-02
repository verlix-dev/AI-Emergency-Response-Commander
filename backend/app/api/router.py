from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.operations import router as operations_router
from app.api.routes.vision import router as vision_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(vision_router, tags=["vision"])
api_router.include_router(incidents_router, tags=["incidents"])
api_router.include_router(operations_router, tags=["operations"])
