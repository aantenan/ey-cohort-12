import structlog
from fastapi import APIRouter, Query, WebSocket
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.websockets import WebSocketDisconnect

from app.auth.jwt import validate_access_token
from app.core.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(include_in_schema=False)


@router.websocket("/ws/agents/{agent_id}/queue")
async def agent_queue_ws(
    websocket: WebSocket,
    agent_id: str,
    token: str | None = Query(None, description="Entra ID access token (same validation as HTTP)"),
) -> None:
    settings = get_settings()
    if not settings.auth_disabled:
        if not token:
            await websocket.close(code=4001, reason="missing_token")
            return
        try:
            validate_access_token(token, settings)
        except StarletteHTTPException:
            await websocket.close(code=4001, reason="invalid_token")
            return

    hub = getattr(websocket.app.state, "ws_hub", None)
    if hub is None:
        await websocket.close(code=1013, reason="redis_unavailable")
        return

    await websocket.accept()
    await hub.register(agent_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.debug("websocket_disconnect", agent_id=agent_id)
    except Exception:
        logger.debug("websocket_session_ended", agent_id=agent_id)
    finally:
        await hub.unregister(agent_id, websocket)
