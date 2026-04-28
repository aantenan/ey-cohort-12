import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Bind `request_id` into structlog context for the lifetime of each HTTP request."""

    header_name = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get(self.header_name) or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=rid)
        try:
            response = await call_next(request)
            response.headers[self.header_name] = rid
            return response
        finally:
            structlog.contextvars.clear_contextvars()
