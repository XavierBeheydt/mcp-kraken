"""Kraken REST clients and supporting types.

`KrakenClient` covers the Spot REST API (`/0/public/`, `/0/private/`).
`KrakenFuturesClient` covers the Futures REST API
(`/derivatives/api/v3/`). The MCP server instantiates exactly one of
them based on `Settings.kraken_api`.
"""

from .client import KrakenClient
from .errors import (
    KrakenAPIError,
    KrakenAuthError,
    KrakenError,
    KrakenPermissionError,
    KrakenRateLimitError,
)
from .futures import KrakenFuturesClient
from .permissions import PERMISSION_REQUIREMENTS, KrakenPermission

__all__ = [
    "PERMISSION_REQUIREMENTS",
    "KrakenAPIError",
    "KrakenAuthError",
    "KrakenClient",
    "KrakenError",
    "KrakenFuturesClient",
    "KrakenPermission",
    "KrakenPermissionError",
    "KrakenRateLimitError",
]
