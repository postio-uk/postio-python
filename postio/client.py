"""PostioClient (sync) and AsyncPostioClient (async).

Public surface mirrors @postio/core. The two classes share a private base
that holds config (api key, base url, timeouts, retry policy) and the
URL-building logic; only the request-execution layer differs.
"""

from __future__ import annotations

import asyncio
import os
import time
from types import TracebackType
from typing import Any, ClassVar
from urllib.parse import quote

import httpx

from . import _models as m
from ._http import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    RetryConfig,
    backoff_delay,
    build_headers,
    parse_envelope,
    raise_for_envelope,
)
from .exceptions import (
    PostioConnectionError,
    PostioServerError,
    PostioTimeout,
)


class _PostioBase:
    _api_key: str
    _base_url: str
    _timeout: float
    _retry: RetryConfig | None
    _extra_headers: dict[str, str]

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int | RetryConfig | None = 2,
        headers: dict[str, str] | None = None,
    ) -> None:
        key = api_key or os.environ.get("POSTIO_API_KEY")
        if not key:
            raise TypeError("Postio: api_key is required (pass api_key=... or set POSTIO_API_KEY).")
        self._api_key = key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        if retries is None or retries is False:
            self._retry = None
        elif isinstance(retries, RetryConfig):
            self._retry = retries
        else:
            self._retry = RetryConfig(max_retries=int(retries))
        self._extra_headers = dict(headers or {})

    def _build_url(self, path: str, query: dict[str, Any] | None = None) -> str:
        url = f"{self._base_url}{path}"
        if query:
            params = [(k, str(v)) for k, v in query.items() if v is not None]
            if params:
                from urllib.parse import urlencode

                url = f"{url}?{urlencode(params)}"
        return url

    def _headers(self) -> dict[str, str]:
        return build_headers(self._api_key, self._extra_headers)


# ---------------------------------------------------------------------------
# Sync client
# ---------------------------------------------------------------------------


class _AddressNamespace:
    def __init__(self, client: PostioClient) -> None:
        self._c = client

    def search(self, q: str, *, max_results: int | None = None) -> m.AddressSearchEnvelope:
        body = self._c._request("/address/search", query={"q": q, "max_results": max_results})
        return m.AddressSearchEnvelope.model_validate(body)

    def postcode(
        self, postcode: str, *, max_results: int | None = None
    ) -> m.AddressPostcodeEnvelope:
        body = self._c._request(
            f"/address/postcode/{quote(postcode, safe='')}",
            query={"max_results": max_results},
        )
        return m.AddressPostcodeEnvelope.model_validate(body)

    def udprn(self, udprn: int | str) -> m.AddressUdprnEnvelope:
        body = self._c._request(f"/address/udprn/{quote(str(udprn), safe='')}")
        return m.AddressUdprnEnvelope.model_validate(body)


class _EmailNamespace:
    def __init__(self, client: PostioClient) -> None:
        self._c = client

    def validate(self, address: str) -> m.EmailEnvelope:
        body = self._c._request(f"/email/{quote(address, safe='')}")
        return m.EmailEnvelope.model_validate(body)


class _PhoneNamespace:
    def __init__(self, client: PostioClient) -> None:
        self._c = client

    def validate(self, number: str) -> m.PhoneEnvelope:
        body = self._c._request(f"/phone/{quote(number, safe='')}")
        return m.PhoneEnvelope.model_validate(body)


class PostioClient(_PostioBase):
    """Synchronous Postio API client.

    .. code-block:: python

        from postio import PostioClient

        client = PostioClient(api_key="pk_...")
        result = client.address.search("downing street")
        print(result.results[0].suggestion)
    """

    _httpx: httpx.Client
    address: _AddressNamespace
    email: _EmailNamespace
    phone: _PhoneNamespace

    _AddressNS: ClassVar[type[_AddressNamespace]] = _AddressNamespace

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int | RetryConfig | None = 2,
        headers: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(
            api_key,
            base_url=base_url,
            timeout=timeout,
            retries=retries,
            headers=headers,
        )
        self._httpx = httpx.Client(timeout=timeout, transport=transport)
        self.address = _AddressNamespace(self)
        self.email = _EmailNamespace(self)
        self.phone = _PhoneNamespace(self)

    def connect(self) -> m.ConnectSuccess:
        """Health probe. Returns 200 if the key is active."""
        body = self._request("/connect")
        return m.ConnectSuccess.model_validate(body)

    def close(self) -> None:
        self._httpx.close()

    def __enter__(self) -> PostioClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _request(self, path: str, *, query: dict[str, Any] | None = None) -> dict[str, Any]:
        url = self._build_url(path, query)
        headers = self._headers()
        retry = self._retry
        max_attempts = (retry.max_retries if retry else 0) + 1

        last_response_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                response = self._httpx.get(url, headers=headers)
            except httpx.TimeoutException as err:
                if not retry or attempt == max_attempts - 1:
                    raise PostioTimeout("Request timed out.", code="request_timeout") from err
                time.sleep(backoff_delay(retry, attempt))
                continue
            except httpx.HTTPError as err:
                if not retry or attempt == max_attempts - 1:
                    raise PostioConnectionError(
                        f"Network error: {err}", code="network_error"
                    ) from err
                time.sleep(backoff_delay(retry, attempt))
                continue

            body = parse_envelope(response)
            if response.is_success:
                return body

            try:
                raise_for_envelope(response, body)
            except PostioServerError as err:
                last_response_error = err
                if (
                    retry
                    and response.status_code in retry.retry_on_status
                    and attempt < max_attempts - 1
                ):
                    time.sleep(backoff_delay(retry, attempt))
                    continue
                raise
            except Exception as err:
                # 4xx (other than retry list) — don't retry, raise immediately.
                if (
                    retry
                    and response.status_code in retry.retry_on_status
                    and attempt < max_attempts - 1
                ):
                    last_response_error = err
                    time.sleep(backoff_delay(retry, attempt))
                    continue
                raise

        # Unreachable: loop above either returns or raises.
        assert last_response_error is not None
        raise last_response_error


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------


class _AsyncAddressNamespace:
    def __init__(self, client: AsyncPostioClient) -> None:
        self._c = client

    async def search(self, q: str, *, max_results: int | None = None) -> m.AddressSearchEnvelope:
        body = await self._c._request("/address/search", query={"q": q, "max_results": max_results})
        return m.AddressSearchEnvelope.model_validate(body)

    async def postcode(
        self, postcode: str, *, max_results: int | None = None
    ) -> m.AddressPostcodeEnvelope:
        body = await self._c._request(
            f"/address/postcode/{quote(postcode, safe='')}",
            query={"max_results": max_results},
        )
        return m.AddressPostcodeEnvelope.model_validate(body)

    async def udprn(self, udprn: int | str) -> m.AddressUdprnEnvelope:
        body = await self._c._request(f"/address/udprn/{quote(str(udprn), safe='')}")
        return m.AddressUdprnEnvelope.model_validate(body)


class _AsyncEmailNamespace:
    def __init__(self, client: AsyncPostioClient) -> None:
        self._c = client

    async def validate(self, address: str) -> m.EmailEnvelope:
        body = await self._c._request(f"/email/{quote(address, safe='')}")
        return m.EmailEnvelope.model_validate(body)


class _AsyncPhoneNamespace:
    def __init__(self, client: AsyncPostioClient) -> None:
        self._c = client

    async def validate(self, number: str) -> m.PhoneEnvelope:
        body = await self._c._request(f"/phone/{quote(number, safe='')}")
        return m.PhoneEnvelope.model_validate(body)


class AsyncPostioClient(_PostioBase):
    """Asynchronous Postio API client.

    .. code-block:: python

        from postio import AsyncPostioClient

        async with AsyncPostioClient(api_key="pk_...") as client:
            result = await client.address.search("downing street")
            print(result.results[0].suggestion)
    """

    _httpx: httpx.AsyncClient
    address: _AsyncAddressNamespace
    email: _AsyncEmailNamespace
    phone: _AsyncPhoneNamespace

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int | RetryConfig | None = 2,
        headers: dict[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(
            api_key,
            base_url=base_url,
            timeout=timeout,
            retries=retries,
            headers=headers,
        )
        self._httpx = httpx.AsyncClient(timeout=timeout, transport=transport)
        self.address = _AsyncAddressNamespace(self)
        self.email = _AsyncEmailNamespace(self)
        self.phone = _AsyncPhoneNamespace(self)

    async def connect(self) -> m.ConnectSuccess:
        """Health probe. Returns 200 if the key is active."""
        body = await self._request("/connect")
        return m.ConnectSuccess.model_validate(body)

    async def close(self) -> None:
        await self._httpx.aclose()

    async def __aenter__(self) -> AsyncPostioClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def _request(self, path: str, *, query: dict[str, Any] | None = None) -> dict[str, Any]:
        url = self._build_url(path, query)
        headers = self._headers()
        retry = self._retry
        max_attempts = (retry.max_retries if retry else 0) + 1

        last_response_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                response = await self._httpx.get(url, headers=headers)
            except httpx.TimeoutException as err:
                if not retry or attempt == max_attempts - 1:
                    raise PostioTimeout("Request timed out.", code="request_timeout") from err
                await asyncio.sleep(backoff_delay(retry, attempt))
                continue
            except httpx.HTTPError as err:
                if not retry or attempt == max_attempts - 1:
                    raise PostioConnectionError(
                        f"Network error: {err}", code="network_error"
                    ) from err
                await asyncio.sleep(backoff_delay(retry, attempt))
                continue

            body = parse_envelope(response)
            if response.is_success:
                return body

            try:
                raise_for_envelope(response, body)
            except PostioServerError as err:
                last_response_error = err
                if (
                    retry
                    and response.status_code in retry.retry_on_status
                    and attempt < max_attempts - 1
                ):
                    await asyncio.sleep(backoff_delay(retry, attempt))
                    continue
                raise
            except Exception as err:
                if (
                    retry
                    and response.status_code in retry.retry_on_status
                    and attempt < max_attempts - 1
                ):
                    last_response_error = err
                    await asyncio.sleep(backoff_delay(retry, attempt))
                    continue
                raise

        assert last_response_error is not None
        raise last_response_error
