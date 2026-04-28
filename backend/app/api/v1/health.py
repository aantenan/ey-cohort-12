from fastapi import APIRouter, Depends, Request

from app.core.config import Settings, get_settings
from app.limiter import limiter

router = APIRouter()


@router.get("")
@limiter.limit("200/minute")
def health(request: Request, settings: Settings = Depends(get_settings)) -> dict[str, str]:
    _ = request  # slowapi / rate-limit keying
    return {
        "status": "ok",
        "environment": settings.environment,
    }
