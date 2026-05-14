"""Async Kraken Futures REST client.

A thin wrapper around `kraken.futures.FuturesAsyncClient` from
python-kraken-sdk, mirroring the shape of `KrakenClient` (Spot) but
exposed as `request()` because Futures URIs are richer
(`/derivatives/api/v3/...`) than the `endpoint`-name convention used by
the Spot wrapper.
"""

from __future__ import annotations

import asyncio
from typing import Any

from kraken import exceptions as sdk_exc
from kraken.futures import FuturesAsyncClient

from ..logging import get_logger
from .errors import (
    KrakenAPIError,
    KrakenAuthError,
    KrakenError,
    KrakenPermissionError,
    KrakenRateLimitError,
)

log = get_logger(__name__)


class KrakenFuturesClient:
    """Async Kraken Futures client backed by `FuturesAsyncClient`.

    Designed to be created once and reused for the lifetime of the server.
    Use as an async context manager, or call `aclose()` explicitly.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str = "",
        sandbox: bool = False,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._sandbox = sandbox
        self._timeout = int(timeout) or 1
        # Lazy SDK init so we can be constructed outside an event loop.
        self._sdk: FuturesAsyncClient | None = None
        self._sdk_lock = asyncio.Lock()

    async def _get_sdk(self) -> FuturesAsyncClient:
        if self._sdk is not None:
            return self._sdk
        async with self._sdk_lock:
            if self._sdk is not None:
                return self._sdk  # type: ignore[unreachable]
            self._sdk = FuturesAsyncClient(
                key=self._api_key or "",
                secret=self._api_secret or "",
                url=self._base_url,
                sandbox=self._sandbox,
            )
            return self._sdk

    # ------------------------------------------------------------------ infra

    async def aclose(self) -> None:
        if self._sdk is not None:
            await self._sdk.close()
            self._sdk = None

    async def __aenter__(self) -> KrakenFuturesClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    @property
    def has_credentials(self) -> bool:
        return bool(self._api_key and self._api_secret)

    # --------------------------------------------------------------- request

    async def request(
        self,
        method: str,
        uri: str,
        *,
        post_params: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> Any:
        """Call a Futures endpoint.

        URIs follow the Kraken Futures convention
        (`/derivatives/api/v3/<resource>`). `query_params` are URL-encoded;
        `post_params` go into the form body for non-GET methods.
        """
        if auth and not self.has_credentials:
            raise KrakenError(
                "Kraken API credentials are not configured "
                "(set KRAKEN_API_KEY and KRAKEN_API_SECRET)"
            )

        sdk = await self._get_sdk()
        log.debug(
            "kraken futures %s %s post=%s query=%s",
            method,
            uri,
            sorted((post_params or {}).keys()),
            sorted((query_params or {}).keys()),
        )
        try:
            return await sdk.request(
                method=method,
                uri=uri,
                post_params=dict(post_params) if post_params else None,
                query_params=dict(query_params) if query_params else None,
                timeout=self._timeout,
                auth=auth,
            )
        except Exception as exc:
            raise self._translate(exc, uri=uri) from exc

    # --------------------------------------------------------- error mapping

    @staticmethod
    def _translate(exc: BaseException, *, uri: str) -> KrakenError:
        """Map SDK / transport exceptions onto our local hierarchy."""
        if isinstance(exc, KrakenError):
            return exc

        msg = str(exc) or exc.__class__.__name__
        errors = [msg]

        if isinstance(exc, sdk_exc.KrakenPermissionDeniedError):
            return KrakenPermissionError(errors, endpoint=uri)
        if isinstance(
            exc,
            (
                sdk_exc.KrakenInvalidAPIKeyError,
                sdk_exc.KrakenInvalidSignatureError,
                sdk_exc.KrakenInvalidNonceError,
                sdk_exc.KrakenAuthenticationError,
                sdk_exc.KrakenAuthenticationFailedError,
            ),
        ):
            return KrakenAuthError(errors)
        if isinstance(
            exc,
            (sdk_exc.KrakenRateLimitExceededError, sdk_exc.KrakenApiLimitExceededError),
        ):
            return KrakenRateLimitError(errors)

        if exc.__class__.__module__.startswith("kraken.exceptions"):
            return KrakenAPIError(errors)

        return KrakenError(msg)
