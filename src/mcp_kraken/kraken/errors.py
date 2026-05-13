"""Exception hierarchy for Kraken interactions.

Kraken reports application-level errors in the `error` field of every response
body, even on HTTP 200. We translate those into typed exceptions.
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


def classify(errors: list[str], *, endpoint: str | None = None) -> KrakenAPIError:
    """Pick the most specific exception class for a Kraken error list."""
    joined = " ".join(errors).lower()
    if "permission denied" in joined or "invalid permissions" in joined:
        return KrakenPermissionError(errors, endpoint=endpoint)
    if "invalid key" in joined or "invalid signature" in joined or "invalid nonce" in joined:
        return KrakenAuthError(errors)
    if "rate limit" in joined or "too many requests" in joined:
        return KrakenRateLimitError(errors)
    return KrakenAPIError(errors)
