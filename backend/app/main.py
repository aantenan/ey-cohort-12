from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from slowapi.middleware import SlowAPIMiddleware

from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.integrations.secrets import load_integration_api_keys
from app.integrations.service_bus import ServiceBusPublisher
from app.limiter import limiter
from app.middleware.request_id import RequestIdMiddleware
from app.websocket.routes import ws_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    try:
        app.state.integration_keys = load_integration_api_keys(settings)
    except Exception:
        logger.exception("integration_keys_load_failed")
        app.state.integration_keys = {}

    app.state.service_bus = ServiceBusPublisher(settings)

    redis_url = settings.redis_url.strip()
    if redis_url:
        redis = Redis.from_url(redis_url, decode_responses=False)
        try:
            await redis.ping()
        except Exception:
            logger.warning("redis_unreachable")
            await redis.aclose()
            app.state.redis = None
            app.state.ws_hub = None
        else:
            app.state.redis = redis
            from app.websocket.hub import WebSocketHub

            hub = WebSocketHub(redis)
            await hub.start()
            app.state.ws_hub = hub
    else:
        app.state.redis = None
        app.state.ws_hub = None

    yield

    sb: ServiceBusPublisher = app.state.service_bus
    await sb.close()
    hub = getattr(app.state, "ws_hub", None)
    if hub:
        await hub.stop()
    r = getattr(app.state, "redis", None)
    if r:
        await r.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(json_logs=not settings.debug, log_level="DEBUG" if settings.debug else "INFO")

    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.state.limiter = limiter

    register_exception_handlers(application)

    application.add_middleware(SlowAPIMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestIdMiddleware)

    @application.get("/")
    def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "environment": settings.environment,
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
        }

    application.include_router(api_router, prefix=settings.api_v1_prefix)
    application.include_router(ws_router)
    return application


app = create_app()
