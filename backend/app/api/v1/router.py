from fastapi import APIRouter

from app.api.v1 import common, health, integrations

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(common.router)
router.include_router(integrations.router)
