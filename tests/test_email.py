"""Live email endpoint tests."""

from __future__ import annotations

from postio import AsyncPostioClient, Deliverability, PostioClient

from .conftest import ClientKwargs


def test_email_valid(client_kwargs: ClientKwargs) -> None:
    with PostioClient(**client_kwargs) as client:
        result = client.email.validate("admin@postio.co.uk")
    assert result.success is True
    assert len(result.results) == 1
    record = result.results[0]
    assert record.email == "admin@postio.co.uk"
    assert record.isValidSyntax is True
    assert record.deliverability in set(Deliverability)


def test_email_invalid_syntax(client_kwargs: ClientKwargs) -> None:
    with PostioClient(**client_kwargs) as client:
        result = client.email.validate("not-an-email")
    record = result.results[0]
    assert record.isValidSyntax is False
    assert record.deliverability == Deliverability.invalid


async def test_email_async(client_kwargs: ClientKwargs) -> None:
    async with AsyncPostioClient(**client_kwargs) as client:
        result = await client.email.validate("admin@postio.co.uk")
    assert result.success is True
