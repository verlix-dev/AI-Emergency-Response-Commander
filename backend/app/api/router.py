from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.resources import router as resources_router
from app.api.routes.uploads import router as uploads_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(incidents_router, tags=["incidents"])
api_router.include_router(uploads_router, tags=["uploads"])
api_router.include_router(resources_router, tags=["resources"])
