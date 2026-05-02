"""Shared test fixtures.

Live tests pick up an API key from one of:
1. ``POSTIO_API_KEY_STAGE`` → uses ``stage-api.postio.co.uk`` (preferred for CI).
2. ``POSTIO_API_KEY_PROD`` → uses ``api.postio.co.uk``.
3. ``POSTIO_API_KEY`` → uses ``api.postio.co.uk`` (fallback).

The umbrella ``.env`` at ``~/PROJECTS/ONNO/POSTIO/.env`` is auto-loaded for
local dev runs. CI passes the secret via job ``env:``.

If no key is found, live tests are skipped — offline tests still run.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

import pytest
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
_UMBRELLA_ENV = _REPO_ROOT.parent / ".env"

if _UMBRELLA_ENV.exists():
    load_dotenv(_UMBRELLA_ENV)
else:
    load_dotenv()


STAGE_BASE_URL = "https://stage-api.postio.co.uk/v1"
PROD_BASE_URL = "https://api.postio.co.uk/v1"


class ClientKwargs(TypedDict):
    api_key: str
    base_url: str


@pytest.fixture(scope="session")
def client_kwargs() -> ClientKwargs:
    """Return ``{api_key, base_url}`` matched to whichever env var is set."""
    if key := os.environ.get("POSTIO_API_KEY_STAGE"):
        return {"api_key": key, "base_url": STAGE_BASE_URL}
    if key := os.environ.get("POSTIO_API_KEY_PROD"):
        return {"api_key": key, "base_url": PROD_BASE_URL}
    if key := os.environ.get("POSTIO_API_KEY"):
        return {"api_key": key, "base_url": PROD_BASE_URL}
    pytest.skip("no Postio API key in env — skipping live test")


@pytest.fixture(scope="session")
def stage_key(client_kwargs: ClientKwargs) -> str:
    return client_kwargs["api_key"]
