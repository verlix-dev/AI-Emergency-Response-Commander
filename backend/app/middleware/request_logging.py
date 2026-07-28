"""Request lifecycle logging middleware."""

from time import perf_counter

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.logging import get_logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request method, path, response status, and elapsed time."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started_at = perf_counter()
        response = await call_next(request)
        get_logger(__name__).info(
            "request_completed method=%s path=%s status_code=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started_at) * 1000,
        )
        return response
