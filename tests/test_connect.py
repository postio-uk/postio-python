"""Live connect/health probe tests against api.postio.co.uk."""

from __future__ import annotations

import pytest

from postio import AsyncPostioClient, PostioClient, PostioInvalidKey

from .conftest import PROD_BASE_URL, ClientKwargs


def test_connect_sync(client_kwargs: ClientKwargs) -> None:
    with PostioClient(**client_kwargs) as client:
        result = client.connect()
    assert result.success is True
    assert result.meta.requestId
    assert result.meta.performance.workerMs >= 0


async def test_connect_async(client_kwargs: ClientKwargs) -> None:
    async with AsyncPostioClient(**client_kwargs) as client:
        result = await client.connect()
    assert result.success is True
    assert result.meta.requestId


def test_connect_invalid_key() -> None:
    with (
        PostioClient(api_key="pk_obviously_invalid", base_url=PROD_BASE_URL, retries=0) as client,
        pytest.raises(PostioInvalidKey) as exc_info,
    ):
        client.connect()
    assert exc_info.value.status == 401
    assert exc_info.value.request_id  # API still issues one


def test_constructor_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTIO_API_KEY", raising=False)
    with pytest.raises(TypeError, match="api_key is required"):
        PostioClient()
