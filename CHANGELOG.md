# Changelog

All notable changes to `postio` are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning
follows [SemVer](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-05-02

Initial release. First Postio SDK published to PyPI.

### Added

- `PostioClient` — synchronous client.
- `AsyncPostioClient` — async client (httpx-based).
- Address endpoints: `address.search`, `address.postcode`, `address.udprn`.
- Email endpoint: `email.validate`.
- Phone endpoint: `phone.validate`.
- Health probe: `connect()`.
- Typed Pydantic v2 models for every response, generated from the public
  OpenAPI spec at `https://postio.co.uk/openapi.json`.
- Typed exception hierarchy: `PostioError`, `PostioInvalidKey`,
  `PostioOutOfCredit`, `PostioForbidden`, `PostioNotFound`,
  `PostioValidationError`, `PostioRateLimit`, `PostioServerError`,
  `PostioTimeout`, `PostioConnectionError`. Every error carries `status`,
  `code`, `details`, `request_id`, and `envelope`.
- Configurable retries (default 2 on 408/409/429/5xx + network) with
  exponential backoff and full jitter, mirroring `@postio/node`.
- `POSTIO_API_KEY` env var picked up automatically when no `api_key=` is
  passed to the constructor.
- PEP 561 typed marker (`postio/py.typed`) so type checkers see the SDK as
  fully annotated.
- Codegen script at `scripts/codegen.py` to refresh `_models.py` from the
  live spec.

### Notes

- The current spec (`@postio/openapi@1.0.2`) marks every optional field on
  `PhoneResult` as `required`, even though the live API drops them on
  invalid input. The SDK applies a manual patch in `postio/_models.py` to
  default those fields to `None` so customer code doesn't get a parse error
  on real responses. Will revisit when postio-api aligns the spec with
  runtime.

[Unreleased]: https://github.com/postio-uk/postio-python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/postio-uk/postio-python/releases/tag/v0.1.0
