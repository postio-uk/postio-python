"""Live phone endpoint tests."""

from __future__ import annotations

from postio import AsyncPostioClient, PostioClient

from .conftest import ClientKwargs


def test_phone_uk_valid(client_kwargs: ClientKwargs) -> None:
    with PostioClient(**client_kwargs) as client:
        # Public UK helpline number — known valid, never changes.
        result = client.phone.validate("+442079460000")
    assert result.success is True
    record = result.results[0]
    assert record.isValid is True
    assert record.countryCode == "44"  # dial code, not ISO 3166


def test_phone_invalid(client_kwargs: ClientKwargs) -> None:
    with PostioClient(**client_kwargs) as client:
        result = client.phone.validate("not-a-phone-number")
    record = result.results[0]
    assert record.isValid is False


async def test_phone_async(client_kwargs: ClientKwargs) -> None:
    async with AsyncPostioClient(**client_kwargs) as client:
        result = await client.phone.validate("+442079460000")
    assert result.success is True
