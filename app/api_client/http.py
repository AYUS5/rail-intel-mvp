from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.api_client.errors import (
    ApiClientHTTPStatusError,
    ApiClientPayloadError,
    ApiClientTimeoutError,
)
from app.utils.request_context import get_request_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_backoff_seconds: float = 0.25
    max_backoff_seconds: float = 2.0
    retry_status_codes: frozenset[int] = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True)
class AsyncHttpClientConfig:
    base_url: str
    timeout_seconds: float = 5.0
    max_connections: int = 100
    max_keepalive_connections: int = 20
    api_key: str | None = None
    retry_policy: RetryPolicy = RetryPolicy()
    request_id_header: str = "X-Request-ID"


class AsyncHttpClient:
    """Small resilient JSON client around httpx.AsyncClient.

    The client is retry-safe for GET requests and designed to be shared per process so
    httpx can reuse connection pools.
    """

    def __init__(
        self,
        config: AsyncHttpClientConfig,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/") + "/",
            timeout=httpx.Timeout(config.timeout_seconds),
            limits=httpx.Limits(
                max_connections=config.max_connections,
                max_keepalive_connections=config.max_keepalive_connections,
            ),
            transport=transport,
        )

    async def get_json(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request_headers = self._headers(headers)
        retry_policy = self._config.retry_policy
        last_error: Exception | None = None

        for attempt in range(1, retry_policy.max_attempts + 1):
            start = time.perf_counter()
            try:
                response = await self._client.get(
                    path.lstrip("/"),
                    params=params or {},
                    headers=request_headers,
                )
                duration_ms = (time.perf_counter() - start) * 1000
                if response.status_code in retry_policy.retry_status_codes:
                    last_error = ApiClientHTTPStatusError(
                        f"Retryable upstream status {response.status_code}",
                        response.status_code,
                    )
                    logger.warning(
                        "api_client_retryable_status",
                        extra={
                            "path": path,
                            "status_code": response.status_code,
                            "attempt": attempt,
                            "duration_ms": round(duration_ms, 2),
                            "request_id": request_headers[self._config.request_id_header],
                        },
                    )
                else:
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise ApiClientPayloadError("Expected JSON object from upstream provider")
                    logger.info(
                        "api_client_request_success",
                        extra={
                            "path": path,
                            "status_code": response.status_code,
                            "attempt": attempt,
                            "duration_ms": round(duration_ms, 2),
                            "request_id": request_headers[self._config.request_id_header],
                        },
                    )
                    return payload
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "api_client_timeout",
                    extra={
                        "path": path,
                        "attempt": attempt,
                        "request_id": request_headers[self._config.request_id_header],
                    },
                )
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code not in retry_policy.retry_status_codes:
                    raise ApiClientHTTPStatusError(
                        f"Non-retryable upstream status {status_code}",
                        status_code,
                    ) from exc
                last_error = exc
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "api_client_http_error",
                    extra={
                        "path": path,
                        "attempt": attempt,
                        "error": str(exc),
                        "request_id": request_headers[self._config.request_id_header],
                    },
                )

            if attempt < retry_policy.max_attempts:
                await asyncio.sleep(self._backoff(attempt, retry_policy))

        if isinstance(last_error, httpx.TimeoutException):
            raise ApiClientTimeoutError(f"Timed out calling {path}") from last_error
        if isinstance(last_error, ApiClientHTTPStatusError):
            raise last_error
        raise ApiClientHTTPStatusError(f"Upstream unavailable for {path}", 503) from last_error

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        request_headers = {"Accept": "application/json", self._config.request_id_header: get_request_id()}
        if self._config.api_key:
            request_headers["Authorization"] = f"Bearer {self._config.api_key}"
        if headers:
            request_headers.update(headers)
        return request_headers

    def _backoff(self, attempt: int, retry_policy: RetryPolicy) -> float:
        return min(
            retry_policy.base_backoff_seconds * 2 ** (attempt - 1),
            retry_policy.max_backoff_seconds,
        )

