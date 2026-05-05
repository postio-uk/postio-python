"""Python SDK for the Postio API.

UK address, email, and phone validation. PAF + Ordnance Survey backed.

.. code-block:: python

    from postio import PostioClient

    client = PostioClient(api_key="pk_...")
    result = client.address.search("downing street")
    print(result.results[0].suggestion)
"""

from ._http import RetryConfig
from ._models import (
    Address,
    AddressPostcodeEnvelope,
    AddressSearchEnvelope,
    AddressSearchResult,
    AddressUdprnEnvelope,
    ConnectSuccess,
    Deliverability,
    EmailEnvelope,
    EmailResult,
    ErrorEnvelope,
    Meta,
    MetaConnect,
    Performance,
    PhoneEnvelope,
    PhoneResult,
)
from ._version import __version__
from .client import AsyncPostioClient, PostioClient
from .exceptions import (
    PostioConnectionError,
    PostioError,
    PostioForbidden,
    PostioInvalidKey,
    PostioNotFound,
    PostioOutOfCredit,
    PostioRateLimit,
    PostioServerError,
    PostioTimeout,
    PostioValidationError,
)

__all__ = [
    # Client classes
    "PostioClient",
    "AsyncPostioClient",
    "RetryConfig",
    # Models
    "Address",
    "AddressPostcodeEnvelope",
    "AddressSearchEnvelope",
    "AddressSearchResult",
    "AddressUdprnEnvelope",
    "ConnectSuccess",
    "Deliverability",
    "EmailEnvelope",
    "EmailResult",
    "ErrorEnvelope",
    "Meta",
    "MetaConnect",
    "Performance",
    "PhoneEnvelope",
    "PhoneResult",
    # Exceptions
    "PostioError",
    "PostioInvalidKey",
    "PostioOutOfCredit",
    "PostioForbidden",
    "PostioNotFound",
    "PostioValidationError",
    "PostioRateLimit",
    "PostioServerError",
    "PostioTimeout",
    "PostioConnectionError",
    # Version
    "__version__",
]
