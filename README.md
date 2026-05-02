# Postio Python SDK

[![PyPI](https://img.shields.io/pypi/v/postio.svg)](https://pypi.org/project/postio/)
[![Python versions](https://img.shields.io/pypi/pyversions/postio.svg)](https://pypi.org/project/postio/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Python SDK for the [Postio API](https://postio.co.uk) — UK address, email, and
phone validation. Backed by Royal Mail PAF and Ordnance Survey. Sync + async,
type-safe via Pydantic v2.

## Install

```bash
pip install postio
```

Requires Python 3.10+.

## 30-second example

```python
from postio import PostioClient

client = PostioClient(api_key="pk_live_...")  # or set POSTIO_API_KEY

result = client.address.search("downing street")
for hit in result.results:
    print(hit.udprn, hit.suggestion)

print("request id:", result.meta.requestId)
```

## Async

```python
import asyncio
from postio import AsyncPostioClient

async def main():
    async with AsyncPostioClient(api_key="pk_live_...") as client:
        result = await client.address.postcode("SW1A 2AA")
        for addr in result.results:
            print(addr.address_line_1, addr.post_town)

asyncio.run(main())
```

## API

| Method | Returns | Notes |
|---|---|---|
| `client.address.search(q, max_results=None)` | `AddressSearchEnvelope` | Free-text typeahead lookup |
| `client.address.postcode(postcode, max_results=None)` | `AddressPostcodeEnvelope` | Full addresses for a postcode |
| `client.address.udprn(udprn)` | `AddressUdprnEnvelope` | Single address by UDPRN |
| `client.email.validate(address)` | `EmailEnvelope` | Syntax + MX + SMTP + deliverability |
| `client.phone.validate(number)` | `PhoneEnvelope` | E.164 format + carrier + reachability |
| `client.connect()` | `ConnectSuccess` | Free health probe |

`AsyncPostioClient` exposes the same surface, awaitable.

## Errors

Every non-2xx response raises a typed exception. `PostioError` is the base.

```python
from postio import (
    PostioClient,
    PostioInvalidKey,       # 401
    PostioOutOfCredit,      # 402
    PostioForbidden,        # 403
    PostioNotFound,         # 404
    PostioValidationError,  # 400 / 422
    PostioRateLimit,        # 429 — has .retry_after
    PostioServerError,      # 5xx — retried by default
    PostioTimeout,
    PostioConnectionError,
)

try:
    client.address.postcode("not-a-postcode")
except PostioValidationError as err:
    print(err.status, err.code, err.request_id, err.envelope)
```

Every error carries `status`, `code`, `details`, `request_id`, and the raw
`envelope`. The `request_id` is the support handle to quote when reporting
issues to `admin@postio.co.uk`.

## Configuration

```python
from postio import PostioClient, RetryConfig

client = PostioClient(
    api_key="pk_live_...",
    base_url="https://api.postio.co.uk/v1",   # default
    timeout=10.0,                              # seconds
    retries=2,                                 # or RetryConfig(...) or None to disable
    headers={"x-tracking-id": "..."},          # extra headers, merged
)
```

Default retry policy: 2 retries, exponential backoff with full jitter
(0.5s → 8s cap), retries on 408, 409, 429, 5xx, and network/timeout errors.
Pass `retries=None` to disable.

## Frameworks

The SDK is framework-agnostic but ships classifiers for Django, Flask, and
FastAPI. Drop the client on your app state at startup:

**FastAPI**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from postio import AsyncPostioClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.postio = AsyncPostioClient()  # reads POSTIO_API_KEY
    yield
    await app.state.postio.close()

app = FastAPI(lifespan=lifespan)
```

**Django** — instantiate one `PostioClient` in `apps.py`'s `ready()` and stash
it on a module-level singleton; close it in a shutdown signal handler.

**Flask** — `PostioClient` on `app.extensions["postio"]`, close in
`app.teardown_appcontext`.

## Links

- [Docs](https://postio.co.uk/docs)
- [API reference (OpenAPI)](https://postio.co.uk/openapi.json)
- [Changelog](./CHANGELOG.md)
- [Issues](https://github.com/postio-uk/postio-python/issues)

## License

MIT — see [LICENSE](./LICENSE).

> *Postio is a trading name of Onno Group Limited, registered in
> England & Wales (company no. 08622799). Registered office:
> Suite 22 Trym Lodge, 1 Henbury Road, Westbury-On-Trym, Bristol BS9 3HQ.*
