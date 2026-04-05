"""
Request/response logging middleware.

Logs every incoming request and its response status at INFO level.
Services should NOT duplicate this — they log business events, not HTTP events.
"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging.config import get_logger

log = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        start = time.perf_counter()

        response: Response = await call_next(request)  # type: ignore[operator]

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response
