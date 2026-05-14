"""Exception hierarchy for Kraken interactions.

The python-kraken-sdk classifies most Kraken errors into its own exception
types. `KrakenClient` translates those into the hierarchy below so the rest
of the codebase can rely on a small, stable set of error classes.
"""

from __future__ import annotations


class KrakenError(Exception):
    """Base class for all Kraken-related failures."""


class KrakenAPIError(KrakenError):
    """Generic API error returned by Kraken (non-empty `error` array)."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors) or "Unknown Kraken error")
        self.errors = errors


class KrakenAuthError(KrakenAPIError):
    """API key invalid, signature wrong, or nonce out of window."""


class KrakenPermissionError(KrakenAPIError):
    """Caller's API key lacks the permission required for this endpoint.

    Raised both proactively (we inspect `GetAPIKeyInfo` and know the
    permission is missing) and reactively (Kraken returned a permission
    denial).
    """

    def __init__(
        self,
        errors: list[str],
        *,
        required: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        super().__init__(errors)
        self.required = required
        self.endpoint = endpoint


class KrakenRateLimitError(KrakenAPIError):
    """Per-account or per-endpoint rate limit exceeded."""
