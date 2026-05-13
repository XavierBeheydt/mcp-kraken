"""Async Kraken Spot REST client.

The client is intentionally thin: it handles transport, signing, error
translation, and permission gating, but does not model individual endpoint
schemas. Each MCP tool calls `public()` or `private()` directly and returns
the parsed `result` to the caller.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ..logging import get_logger
from .errors import KrakenError, KrakenPermissionError, classify
from .permissions import (
    PERMISSION_REQUIREMENTS,
    KrakenPermission,
    parse_permissions,
)
from .signing import next_nonce, sign

API_VERSION = "0"

log = get_logger(__name__)


class KrakenClient:
    """Async client over `httpx.AsyncClient`.

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
        user_agent: str = "mcp-kraken/0",
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={"User-Agent": user_agent},
        )
        self._permissions: frozenset[KrakenPermission] | None = None
        self._permissions_lock = asyncio.Lock()

    # ------------------------------------------------------------------ infra

    async def aclose(self) -> None:
        await self._client.aclose()

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
        path = f"/{API_VERSION}/public/{endpoint}"
        log.debug("kraken public %s params=%s", path, params)
        resp = await self._client.get(path, params=params or {})
        return self._unwrap(resp, endpoint=endpoint)

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
        assert self._api_key and self._api_secret  # noqa: S101 — type narrowing

        if not skip_permission_check:
            await self._enforce_permissions(endpoint)

        path = f"/{API_VERSION}/private/{endpoint}"
        body = dict(data or {})
        body["nonce"] = next_nonce()
        headers = {
            "API-Key": self._api_key,
            "API-Sign": sign(path, body, self._api_secret),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        log.debug("kraken private %s keys=%s", path, sorted(body.keys()))
        resp = await self._client.post(path, data=body, headers=headers)
        return self._unwrap(resp, endpoint=endpoint)

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
                # GetAPIKeyInfo is a newer endpoint; on older keys it may not
                # be enabled. Fall back to "unknown" so we let Kraken enforce.
                log.warning("could not introspect API key permissions: %s", exc)
                self._permissions = frozenset()
                return self._permissions
            self._permissions = parse_permissions(info if isinstance(info, dict) else {})
            log.info("API key permissions: %s", sorted(p.value for p in self._permissions))
            return self._permissions

    async def _enforce_permissions(self, endpoint: str) -> None:
        required = PERMISSION_REQUIREMENTS.get(endpoint)
        if not required:
            return
        held = await self.get_permissions()
        if not held:
            # We could not introspect — let Kraken decide.
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

    # -------------------------------------------------------------- response

    @staticmethod
    def _unwrap(resp: httpx.Response, *, endpoint: str) -> Any:
        try:
            payload = resp.json()
        except ValueError as exc:
            resp.raise_for_status()
            raise KrakenError(f"non-JSON response from Kraken ({resp.status_code})") from exc
        if resp.status_code >= 500:
            raise KrakenError(f"Kraken server error {resp.status_code}: {payload}")
        errors = payload.get("error") or []
        if errors:
            raise classify(errors, endpoint=endpoint)
        return payload.get("result")
