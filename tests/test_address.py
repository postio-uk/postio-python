"""Live address endpoint tests."""

from __future__ import annotations

import pytest

from postio import (
    AsyncPostioClient,
    PostioClient,
    PostioNotFound,
    PostioValidationError,
)

from .conftest import ClientKwargs


def test_search(client_kwargs: ClientKwargs) -> None:
    with PostioClient(**client_kwargs) as client:
        result = client.address.search("downing street", max_results=5)
    assert result.success is True
    assert len(result.results) >= 1
    first = result.results[0]
    assert first.udprn > 0
    assert isinstance(first.suggestion, str) and first.suggestion
    assert result.meta.countResults == len(result.results)


def test_postcode(client_kwargs: ClientKwargs) -> None:
    with PostioClient(**client_kwargs) as client:
        result = client.address.postcode("SW1A 2AA")
    assert result.success is True
    assert len(result.results) >= 1
    addr = result.results[0]
    assert addr.postcode.replace(" ", "").upper() == "SW1A2AA"
    assert addr.post_town


def test_postcode_invalid_returns_validation_error(
    client_kwargs: ClientKwargs,
) -> None:
    with PostioClient(**client_kwargs) as client:
        with pytest.raises((PostioValidationError, PostioNotFound)) as exc_info:
            client.address.postcode("not-a-postcode")
    assert exc_info.value.status in (400, 404)
    assert exc_info.value.request_id


def test_udprn(client_kwargs: ClientKwargs) -> None:
    with PostioClient(**client_kwargs) as client:
        # First find a real UDPRN, then look it up.
        search = client.address.search("downing street", max_results=1)
        udprn = search.results[0].udprn
        result = client.address.udprn(udprn)
    assert result.success is True
    assert len(result.results) == 1
    assert result.results[0].udprn == udprn


async def test_search_async(client_kwargs: ClientKwargs) -> None:
    async with AsyncPostioClient(**client_kwargs) as client:
        result = await client.address.search("trafalgar square", max_results=3)
    assert result.success is True
    assert len(result.results) >= 1
