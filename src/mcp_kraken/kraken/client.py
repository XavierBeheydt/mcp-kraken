"""Async Kraken Spot REST client.

A thin wrapper around `kraken.spot.SpotAsyncClient` from
[python-kraken-sdk](https://github.com/btschwertfeger/python-kraken-sdk).
The SDK owns transport, request signing, nonce handling, and primary error
classification; this wrapper exposes the same `public()` / `private()`
surface the rest of mcp-kraken is built against and translates SDK
exceptions into our local hierarchy.

Each MCP tool calls `public()` or `private()` directly and receives the
parsed `result` payload.
"""

from __future__ import annotations

import asyncio
from typing import Any

from kraken import exceptions as sdk_exc
from kraken.spot import SpotAsyncClient

from ..logging import get_logger
from .errors import (
    KrakenAPIError,
    KrakenAuthError,
    KrakenError,
    KrakenPermissionError,
    KrakenRateLimitError,
)
from .permissions import (
    PERMISSION_REQUIREMENTS,
    KrakenPermission,
    parse_permissions,
)

API_VERSION = "0"

log = get_logger(__name__)


# Endpoint name → JSON-body flag. Kraken's batch endpoints expect the request
# body to be JSON-encoded; the SDK has a `do_json` switch for this.
_JSON_BODY_ENDPOINTS: frozenset[str] = frozenset(
    {
        "AddOrderBatch",
        "CancelOrderBatch",
    }
)


class KrakenClient:
    """Async Kraken client backed by `kraken.spot.SpotAsyncClient`.

    Designed to be created once and reused for the lifetime of the server.
    Use as an async context manager, or call `aclose()` explicitly.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str = "https://api.kraken.com",
        timeout: float = 30.0,
        user_agent: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = int(timeout) or 1
        self._user_agent = user_agent
        # The SDK builds an aiohttp.ClientSession in its constructor, which
        # requires a running event loop. We instantiate it lazily on the
        # first call so KrakenClient can still be constructed outside one
        # (e.g. during server wiring).
        self._sdk: SpotAsyncClient | None = None
        self._sdk_lock = asyncio.Lock()
        self._permissions: frozenset[KrakenPermission] | None = None
        self._permissions_lock = asyncio.Lock()

    async def _get_sdk(self) -> SpotAsyncClient:
        if self._sdk is not None:
            return self._sdk
        async with self._sdk_lock:
            if self._sdk is not None:
                return self._sdk  # type: ignore[unreachable]
            sdk = SpotAsyncClient(
                key=self._api_key or "",
                secret=self._api_secret or "",
                url=self._base_url,
            )
            if self._user_agent:
                # Override the session's User-Agent so request logs identify
                # mcp-kraken rather than the upstream SDK.
                try:
                    sdk._SpotAsyncClient__session.headers["User-Agent"] = self._user_agent  # type: ignore[attr-defined]
                except (AttributeError, KeyError):
                    log.debug("could not set custom User-Agent on SDK session", exc_info=True)
            self._sdk = sdk
            return self._sdk

    # ------------------------------------------------------------------ infra

    async def aclose(self) -> None:
        if self._sdk is not None:
            await self._sdk.close()
            self._sdk = None

    async def __aenter__(self) -> KrakenClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    @property
    def has_credentials(self) -> bool:
        return bool(self._api_key and self._api_secret)

    # ------------------------------------------------------------------ public

    async def public(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Call an unauthenticated endpoint under `/0/public/`."""
        uri = f"/{API_VERSION}/public/{endpoint}"
        log.debug("kraken public %s params=%s", uri, params)
        return await self._call(
            method="GET",
            uri=uri,
            params=params,
            auth=False,
            endpoint=endpoint,
        )

    # ----------------------------------------------------------------- private

    async def private(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        *,
        skip_permission_check: bool = False,
    ) -> Any:
        """Call an authenticated endpoint under `/0/private/`.

        Permissions are checked proactively against `GetAPIKeyInfo` the first
        time a private call is made. If we know the key lacks the permission,
        we raise `KrakenPermissionError` without hitting the network.
        """
        if not self.has_credentials:
            raise KrakenError(
                "Kraken API credentials are not configured "
                "(set KRAKEN_API_KEY and KRAKEN_API_SECRET)"
            )

        if not skip_permission_check:
            await self._enforce_permissions(endpoint)

        uri = f"/{API_VERSION}/private/{endpoint}"
        log.debug(
            "kraken private %s keys=%s",
            uri,
            sorted((data or {}).keys()),
        )
        return await self._call(
            method="POST",
            uri=uri,
            params=data,
            auth=True,
            endpoint=endpoint,
            do_json=endpoint in _JSON_BODY_ENDPOINTS,
        )

    # ------------------------------------------------------------- transport

    async def _call(
        self,
        *,
        method: str,
        uri: str,
        params: dict[str, Any] | None,
        auth: bool,
        endpoint: str,
        do_json: bool = False,
    ) -> Any:
        sdk = await self._get_sdk()
        try:
            result = await sdk.request(
                method=method,
                uri=uri,
                params=dict(params) if params else None,
                timeout=self._timeout,
                auth=auth,
                do_json=do_json,
            )
        except Exception as exc:
            raise self._translate(exc, endpoint=endpoint) from exc

        # The SDK's `check()` returns `data["result"]` on success but falls
        # back to returning the full `{error: [...], result: ...}` envelope
        # when the error code is not in its known table. Catch that case
        # here so callers always see a typed exception on failure.
        if isinstance(result, dict):
            errors = result.get("error")
            if errors:
                raise KrakenAPIError(list(errors))
        return result

    # -------------------------------------------------------------- perms

    async def get_permissions(self) -> frozenset[KrakenPermission]:
        """Return the cached set of permissions held by the configured key."""
        if self._permissions is not None:
            return self._permissions
        async with self._permissions_lock:
            if self._permissions is not None:
                return self._permissions  # type: ignore[unreachable]
            try:
                info = await self.private("GetAPIKeyInfo", skip_permission_check=True)
            except KrakenError as exc:
                # GetAPIKeyInfo is a newer endpoint; on older keys or in some
                # regions Kraken answers with "Unknown method". Fall back to
                # "unknown" so we let Kraken itself enforce permissions.
                log.warning("could not introspect API key permissions: %s", exc)
                self._permissions = frozenset()
                return self._permissions
            self._permissions = parse_permissions(info if isinstance(info, dict) else {})
            log.info(
                "API key permissions: %s",
                sorted(p.value for p in self._permissions),
            )
            return self._permissions

    async def _enforce_permissions(self, endpoint: str) -> None:
        required = PERMISSION_REQUIREMENTS.get(endpoint)
        if not required:
            return
        held = await self.get_permissions()
        if not held:
            # We could not introspect — let Kraken decide over the wire.
            return
        missing = required - held
        if missing:
            raise KrakenPermissionError(
                [
                    "EAPI:Invalid permissions — this API key is missing: "
                    + ", ".join(sorted(p.value for p in missing))
                ],
                required=", ".join(sorted(p.value for p in missing)),
                endpoint=endpoint,
            )

    # --------------------------------------------------------- error mapping

    @staticmethod
    def _translate(exc: BaseException, *, endpoint: str) -> KrakenError:
        """Map SDK / transport exceptions onto our local hierarchy."""
        if isinstance(exc, KrakenError):
            return exc

        msg = str(exc) or exc.__class__.__name__
        errors = [msg]

        if isinstance(exc, sdk_exc.KrakenPermissionDeniedError):
            return KrakenPermissionError(errors, endpoint=endpoint)
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

        # Any other SDK-defined Kraken exception → generic API error so
        # callers can `except KrakenAPIError` and get useful messages.
        if exc.__class__.__module__.startswith("kraken.exceptions"):
            return KrakenAPIError(errors)

        # Transport / unexpected — wrap as KrakenError, preserve original
        # via __cause__.
        return KrakenError(msg)
