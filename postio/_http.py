"""Shared HTTP plumbing: defaults, retry config, response → envelope/exception."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

import httpx

from ._version import __version__
from .exceptions import (
    PostioError,
    PostioRateLimit,
    error_for_status,
)

DEFAULT_BASE_URL = "https://api.postio.co.uk/v1"
DEFAULT_TIMEOUT = 10.0
USER_AGENT = f"postio-python/{__version__}"
CLIENT_ID = f"postio-python/{__version__}"

# 408 isn't currently in the spec but we keep it: HTTP-correct + costs nothing.
DEFAULT_RETRY_STATUSES = frozenset({408, 409, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class RetryConfig:
    max_retries: int = 2
    base_delay: float = 0.5
    cap_delay: float = 8.0
    retry_on_status: frozenset[int] = field(default_factory=lambda: DEFAULT_RETRY_STATUSES)


def backoff_delay(cfg: RetryConfig, attempt: int) -> float:
    """Exponential backoff with full jitter — same shape as @postio/node."""
    exp = min(cfg.cap_delay, cfg.base_delay * (2**attempt))
    return random.uniform(0, exp)


def build_headers(api_key: str, extra: dict[str, str] | None) -> dict[str, str]:
    headers = dict(extra or {})
    headers["x-api-key"] = api_key
    headers["accept"] = "application/json"
    headers["user-agent"] = USER_AGENT
    headers["x-postio-client"] = CLIENT_ID
    return headers


def parse_envelope(response: httpx.Response) -> dict[str, Any]:
    """Parse JSON response body or raise PostioError."""
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        text = response.text[:500] if response.text else ""
        raise PostioError(
            f"Unexpected response content-type {content_type!r}.",
            status=response.status_code,
            code="unexpected_content_type",
            details=text or None,
        )
    try:
        body = response.json()
    except ValueError as err:
        raise PostioError(
            "Failed to parse response body as JSON.",
            status=response.status_code,
            code="parse_error",
        ) from err
    if not isinstance(body, dict):
        raise PostioError(
            "Response body is not a JSON object.",
            status=response.status_code,
            code="parse_error",
        )
    return body


def raise_for_envelope(response: httpx.Response, body: dict[str, Any]) -> None:
    """If the response is non-2xx, raise the appropriate typed exception."""
    if response.is_success:
        return

    error_msg = str(body.get("error") or f"HTTP {response.status_code}")
    details = body.get("details")
    request_id = (body.get("meta") or {}).get("requestId")
    cls = error_for_status(response.status_code)

    kwargs: dict[str, Any] = {
        "status": response.status_code,
        "code": str(body.get("error")) if body.get("error") else None,
        "details": str(details) if details is not None else None,
        "request_id": str(request_id) if request_id else None,
        "envelope": body,
    }
    if cls is PostioRateLimit:
        retry_after_header = response.headers.get("retry-after")
        retry_after: float | None = None
        if retry_after_header:
            try:
                retry_after = float(retry_after_header)
            except ValueError:
                retry_after = None
        raise PostioRateLimit(error_msg, retry_after=retry_after, **kwargs)
    raise cls(error_msg, **kwargs)
