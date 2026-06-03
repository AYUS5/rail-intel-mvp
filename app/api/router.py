from fastapi import APIRouter

from app.api.v1.routes import health, monitors, search

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(monitors.router, prefix="/monitors", tags=["monitors"])

