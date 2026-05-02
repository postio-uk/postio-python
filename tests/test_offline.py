"""Offline tests — no network, no key required.

Uses respx to mock httpx transport. These run on every PR and on every
Python version in the CI matrix; the live tests above are gated.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from postio import (
    AsyncPostioClient,
    PostioClient,
    PostioInvalidKey,
    PostioOutOfCredit,
    PostioRateLimit,
    PostioServerError,
)

BASE = "https://api.postio.co.uk/v1"


def _envelope(success: bool = True, **extra: object) -> dict[str, object]:
    return {
        "success": success,
        "results": [],
        "meta": {
            "requestId": "test-req-id",
            "countResults": 0,
            "performance": {"workerMs": 5, "lookupMs": 2},
        },
        **extra,
    }


@respx.mock
def test_search_sends_correct_request() -> None:
    route = respx.get(f"{BASE}/address/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "results": [{"udprn": 12345, "suggestion": "10 Downing Street"}],
                "meta": {
                    "requestId": "abc-123",
                    "countResults": 1,
                    "performance": {"workerMs": 10, "lookupMs": 5},
                },
            },
        )
    )
    with PostioClient(api_key="pk_test", retries=0) as client:
        result = client.address.search("downing", max_results=10)

    assert route.called
    request = route.calls.last.request
    assert request.headers["x-api-key"] == "pk_test"
    assert request.headers["accept"] == "application/json"
    assert request.headers["user-agent"].startswith("postio-python/")
    assert request.url.params["q"] == "downing"
    assert request.url.params["max_results"] == "10"
    assert result.results[0].udprn == 12345
    assert result.meta.requestId == "abc-123"


@respx.mock
def test_401_raises_invalid_key() -> None:
    respx.get(f"{BASE}/connect").mock(
        return_value=httpx.Response(
            401,
            json={
                "success": False,
                "error": "invalid_api_key",
                "details": "Key not recognised",
                "results": [],
                "meta": {
                    "requestId": "req-401",
                    "countResults": 0,
                    "performance": {"workerMs": 1, "lookupMs": 0},
                },
            },
        )
    )
    with PostioClient(api_key="pk_bad", retries=0) as client:
        with pytest.raises(PostioInvalidKey) as exc_info:
            client.connect()
    assert exc_info.value.status == 401
    assert exc_info.value.code == "invalid_api_key"
    assert exc_info.value.details == "Key not recognised"
    assert exc_info.value.request_id == "req-401"


@respx.mock
def test_402_raises_out_of_credit() -> None:
    respx.get(f"{BASE}/connect").mock(
        return_value=httpx.Response(
            402,
            json={
                "success": False,
                "error": "out_of_credit",
                "results": [],
                "meta": {
                    "requestId": "req-402",
                    "countResults": 0,
                    "performance": {"workerMs": 1, "lookupMs": 0},
                },
            },
        )
    )
    with PostioClient(api_key="pk_test", retries=0) as client, pytest.raises(PostioOutOfCredit):
        client.connect()


@respx.mock
def test_429_raises_rate_limit_with_retry_after() -> None:
    respx.get(f"{BASE}/connect").mock(
        return_value=httpx.Response(
            429,
            headers={"retry-after": "12"},
            json={
                "success": False,
                "error": "rate_limited",
                "results": [],
                "meta": {
                    "requestId": "req-429",
                    "countResults": 0,
                    "performance": {"workerMs": 1, "lookupMs": 0},
                },
            },
        )
    )
    with PostioClient(api_key="pk_test", retries=0) as client:
        with pytest.raises(PostioRateLimit) as exc_info:
            client.connect()
    assert exc_info.value.retry_after == 12.0


@respx.mock
def test_5xx_retried_then_succeeds() -> None:
    respx.get(f"{BASE}/connect").mock(
        side_effect=[
            httpx.Response(
                502,
                json={
                    "success": False,
                    "error": "bad_gateway",
                    "results": [],
                    "meta": {
                        "requestId": "req-1",
                        "countResults": 0,
                        "performance": {"workerMs": 1, "lookupMs": 0},
                    },
                },
            ),
            httpx.Response(
                200,
                json={
                    "success": True,
                    "meta": {
                        "requestId": "req-2",
                        "performance": {"workerMs": 5, "lookupMs": 2},
                    },
                },
            ),
        ]
    )
    # Tighten the retry config so the test isn't slow.
    from postio import RetryConfig

    cfg = RetryConfig(max_retries=2, base_delay=0.0, cap_delay=0.0)
    with PostioClient(api_key="pk_test", retries=cfg) as client:
        result = client.connect()
    assert result.success is True
    assert result.meta.requestId == "req-2"


@respx.mock
def test_5xx_exhausted_raises_server_error() -> None:
    respx.get(f"{BASE}/connect").mock(
        return_value=httpx.Response(
            500,
            json={
                "success": False,
                "error": "internal",
                "results": [],
                "meta": {
                    "requestId": "req-500",
                    "countResults": 0,
                    "performance": {"workerMs": 1, "lookupMs": 0},
                },
            },
        )
    )
    from postio import RetryConfig

    cfg = RetryConfig(max_retries=1, base_delay=0.0, cap_delay=0.0)
    with PostioClient(api_key="pk_test", retries=cfg) as client:
        with pytest.raises(PostioServerError):
            client.connect()


@respx.mock
async def test_async_5xx_retry() -> None:
    respx.get(f"{BASE}/connect").mock(
        side_effect=[
            httpx.Response(
                503,
                json={
                    "success": False,
                    "error": "unavailable",
                    "results": [],
                    "meta": {
                        "requestId": "a-1",
                        "countResults": 0,
                        "performance": {"workerMs": 1, "lookupMs": 0},
                    },
                },
            ),
            httpx.Response(
                200,
                json={
                    "success": True,
                    "meta": {
                        "requestId": "a-2",
                        "performance": {"workerMs": 5, "lookupMs": 2},
                    },
                },
            ),
        ]
    )
    from postio import RetryConfig

    cfg = RetryConfig(max_retries=2, base_delay=0.0, cap_delay=0.0)
    async with AsyncPostioClient(api_key="pk_test", retries=cfg) as client:
        result = await client.connect()
    assert result.meta.requestId == "a-2"


def test_user_agent_format() -> None:
    """User-Agent must always identify the SDK by name and version."""
    from postio._http import USER_AGENT
    from postio._version import __version__

    assert f"postio-python/{__version__}" == USER_AGENT
