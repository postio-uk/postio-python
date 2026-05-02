from __future__ import annotations

from typing import Any


class PostioError(Exception):
    """Base error for any failed Postio request."""

    def __init__(
        self,
        message: str,
        *,
        status: int = 0,
        code: str | None = None,
        details: str | None = None,
        request_id: str | None = None,
        envelope: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.details = details
        self.request_id = request_id
        self.envelope = envelope

    def __repr__(self) -> str:
        parts = [f"status={self.status}"]
        if self.code:
            parts.append(f"code={self.code!r}")
        if self.request_id:
            parts.append(f"request_id={self.request_id!r}")
        return f"{type(self).__name__}({', '.join(parts)}: {self})"


class PostioValidationError(PostioError):
    """400 — request shape is invalid (bad postcode, missing query, etc.)."""


class PostioInvalidKey(PostioError):
    """401 — missing or invalid API key."""


class PostioOutOfCredit(PostioError):
    """402 — account is out of credit. Top up to resume."""


class PostioForbidden(PostioError):
    """403 — origin / IP / key-restriction blocked the request."""


class PostioNotFound(PostioError):
    """404 — the resource (postcode, UDPRN) was not found."""


class PostioRateLimit(PostioError):
    """429 — rate limit hit. Inspect ``retry_after`` for the suggested wait."""

    def __init__(self, *args: Any, retry_after: float | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class PostioServerError(PostioError):
    """5xx — server-side failure. Retryable."""


class PostioTimeout(PostioError):
    """Local request timeout."""


class PostioConnectionError(PostioError):
    """Network failure before a response was received."""


_STATUS_MAP: dict[int, type[PostioError]] = {
    400: PostioValidationError,
    401: PostioInvalidKey,
    402: PostioOutOfCredit,
    403: PostioForbidden,
    404: PostioNotFound,
    422: PostioValidationError,
    429: PostioRateLimit,
}


def error_for_status(status: int) -> type[PostioError]:
    if status in _STATUS_MAP:
        return _STATUS_MAP[status]
    if status >= 500:
        return PostioServerError
    return PostioError
