"""Kraken REST client and supporting types."""

from .client import KrakenClient
from .errors import (
    KrakenAPIError,
    KrakenAuthError,
    KrakenError,
    KrakenPermissionError,
    KrakenRateLimitError,
)
from .permissions import PERMISSION_REQUIREMENTS, KrakenPermission

__all__ = [
    "PERMISSION_REQUIREMENTS",
    "KrakenAPIError",
    "KrakenAuthError",
    "KrakenClient",
    "KrakenError",
    "KrakenPermission",
    "KrakenPermissionError",
    "KrakenRateLimitError",
]
