"""Small process-local guard for protected API paths.

This is intentionally a prototype control. A multi-worker or multi-region
deployment must enforce the same policy at the edge or in a shared store.
"""

import asyncio
from collections import deque
from time import monotonic
from fastapi import Request
from fastapi.responses import JSONResponse

from .errors import error_body

_PROTECTED_PREFIXES = (
    "/v1/assessment-sessions",
    "/v1/diagnostics",
    "/v1/internal",
    "/v1/issue-reports",
    "/v1/mastery",
    "/v1/practice-sets",
    "/v1/remediation-cycles",
)


class ProcessRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def check(
        self,
        request: Request,
        *,
        max_requests: int,
        window_seconds: int,
    ) -> JSONResponse | None:
        if not self._should_limit(request):
            return None

        client_host = request.client.host if request.client else "unknown"
        key = f"{client_host}:{request.method}:{request.url.path}"
        now = monotonic()
        async with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= max_requests:
                retry_after = max(1, int(window_seconds - (now - hits[0])))
                return JSONResponse(
                    status_code=429,
                    content=error_body(
                        request,
                        "rate_limited",
                        "Too many requests; try again shortly.",
                    ),
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(max_requests),
                    },
                )
            hits.append(now)
            self._prune_empty(now, window_seconds)
        return None

    @staticmethod
    def _should_limit(request: Request) -> bool:
        return request.url.path.startswith(_PROTECTED_PREFIXES)

    def _prune_empty(self, now: float, window_seconds: int) -> None:
        expired = [
            key
            for key, hits in self._hits.items()
            if not hits or hits[-1] <= now - window_seconds
        ]
        for key in expired:
            self._hits.pop(key, None)


rate_limiter = ProcessRateLimiter()


__all__ = ["ProcessRateLimiter", "rate_limiter"]
