import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logging_config import get_logger

REQUEST_ID_HEADER = "X-Request-Id"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id, user_id=None)
        log = get_logger("http")
        started = time.perf_counter()
        status = 500
        response: Response | None = None
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            latency_ms = (time.perf_counter() - started) * 1000
            log.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=status,
                latency_ms=round(latency_ms, 2),
            )
            structlog.contextvars.clear_contextvars()
