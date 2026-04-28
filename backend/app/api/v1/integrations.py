"""External integration endpoints secured with API keys (IVR, chatbot)."""

from fastapi import APIRouter, Depends

from app.integrations.integration_deps import require_chatbot_api_key, require_ivr_api_key

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/ivr/webhook", dependencies=[Depends(require_ivr_api_key)])
def ivr_webhook_stub() -> dict[str, bool]:
    """Placeholder for IVR callbacks — validates `X-API-Key` against the IVR secret."""
    return {"received": True}


@router.post("/chatbot/webhook", dependencies=[Depends(require_chatbot_api_key)])
def chatbot_webhook_stub() -> dict[str, bool]:
    """Placeholder for chatbot callbacks."""
    return {"received": True}
