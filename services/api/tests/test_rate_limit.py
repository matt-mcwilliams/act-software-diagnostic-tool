import asyncio
from types import SimpleNamespace

from app.rate_limit import ProcessRateLimiter


def _request(path: str = "/v1/issue-reports") -> SimpleNamespace:
    return SimpleNamespace(
        method="POST",
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(request_id="rate-limit-test"),
        url=SimpleNamespace(path=path),
    )


def test_protected_paths_are_limited_and_unrelated_paths_are_not() -> None:
    limiter = ProcessRateLimiter()

    first = asyncio.run(limiter.check(_request(), max_requests=1, window_seconds=60))
    second = asyncio.run(limiter.check(_request(), max_requests=1, window_seconds=60))
    health = asyncio.run(limiter.check(_request("/healthz"), max_requests=1, window_seconds=60))

    assert first is None
    assert second is not None
    assert second.status_code == 429
    assert 1 <= int(second.headers["retry-after"]) <= 60
    assert second.headers["x-ratelimit-limit"] == "1"
    assert health is None
