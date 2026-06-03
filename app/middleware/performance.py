import logging
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response

from app.utils.request_context import request_id_var

logger = logging.getLogger(__name__)


async def request_timing_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid4())
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "http_request_complete",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code if response is not None else 500,
                "duration_ms": round(duration_ms, 2),
                "request_id": request_id,
            },
        )
        request_id_var.reset(token)
