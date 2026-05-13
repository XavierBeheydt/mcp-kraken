"""Tests for the Kraken async client. Uses respx to stub httpx."""

from __future__ import annotations

import pytest
import respx
from httpx import Request, Response

from mcp_kraken.kraken import (
    KrakenAuthError,
    KrakenClient,
    KrakenPermissionError,
    KrakenRateLimitError,
)


async def test_public_endpoint_returns_result(kraken_client: KrakenClient) -> None:
    with respx.mock(base_url="https://api.kraken.test") as mock:
        mock.get("/0/public/Time").mock(
            return_value=Response(200, json={"error": [], "result": {"unixtime": 1700000000}})
        )
        result = await kraken_client.public("Time")
    assert result == {"unixtime": 1700000000}


async def test_public_error_array_raises(kraken_client: KrakenClient) -> None:
    with (
        respx.mock(base_url="https://api.kraken.test") as mock,
        pytest.raises(Exception, match="EService"),
    ):
        mock.get("/0/public/Time").mock(
            return_value=Response(200, json={"error": ["EService:Busy"], "result": None})
        )
        await kraken_client.public("Time")


async def test_rate_limit_error_classified(kraken_client: KrakenClient) -> None:
    with (
        respx.mock(base_url="https://api.kraken.test") as mock,
        pytest.raises(KrakenRateLimitError),
    ):
        mock.get("/0/public/Trades").mock(
            return_value=Response(
                200,
                json={"error": ["EAPI:Rate limit exceeded"], "result": None},
            )
        )
        await kraken_client.public("Trades", {"pair": "XBTUSD"})


async def test_auth_error_classified(kraken_client: KrakenClient) -> None:
    """The proactive permission probe (`GetAPIKeyInfo`) is the first call;
    when Kraken refuses with an auth error we surface it as KrakenAuthError.
    """
    with (
        respx.mock(base_url="https://api.kraken.test") as mock,
        pytest.raises(KrakenAuthError),
    ):
        # GetAPIKeyInfo probe + the real call land on the same endpoint here.
        mock.post("/0/private/GetAPIKeyInfo").mock(
            return_value=Response(200, json={"error": ["EAPI:Invalid key"], "result": None})
        )
        mock.post("/0/private/Balance").mock(
            return_value=Response(200, json={"error": ["EAPI:Invalid key"], "result": None})
        )
        await kraken_client.private("Balance")


async def test_private_call_includes_signature_headers(
    kraken_client: KrakenClient,
) -> None:
    """The signing headers must be set on every private call."""
    seen: dict[str, str] = {}
    with respx.mock(base_url="https://api.kraken.test") as mock:
        mock.post("/0/private/GetAPIKeyInfo").mock(
            return_value=Response(
                200,
                json={
                    "error": [],
                    "result": {"permissions": {"funding": {"query": True}}},
                },
            )
        )

        def _capture(request: Request) -> Response:
            seen["API-Key"] = request.headers.get("API-Key", "")
            seen["API-Sign"] = request.headers.get("API-Sign", "")
            return Response(200, json={"error": [], "result": {"ZUSD": "100"}})

        mock.post("/0/private/Balance").mock(side_effect=_capture)
        await kraken_client.private("Balance")

    assert seen["API-Key"] == "testkey"
    assert seen["API-Sign"]  # non-empty base64 signature


async def test_proactive_permission_block(kraken_client: KrakenClient) -> None:
    """When GetAPIKeyInfo says the key lacks `withdraw`, calling `Withdraw`
    must raise without hitting the network."""
    with (
        respx.mock(base_url="https://api.kraken.test") as mock,
        pytest.raises(KrakenPermissionError),
    ):
        mock.post("/0/private/GetAPIKeyInfo").mock(
            return_value=Response(
                200,
                json={
                    "error": [],
                    "result": {"permissions": {"funding": {"query": True, "withdraw": False}}},
                },
            )
        )
        # The Withdraw route is deliberately not mocked; if it gets hit
        # respx will raise. The proactive block should prevent that.
        await kraken_client.private("Withdraw", {"asset": "XBT", "key": "k", "amount": "0.01"})


async def test_permissions_introspection_is_cached(
    kraken_client: KrakenClient,
) -> None:
    """GetAPIKeyInfo should be called at most once."""
    with respx.mock(base_url="https://api.kraken.test") as mock:
        info = mock.post("/0/private/GetAPIKeyInfo").mock(
            return_value=Response(
                200,
                json={
                    "error": [],
                    "result": {"permissions": {"funding": {"query": True}}},
                },
            )
        )
        balance = mock.post("/0/private/Balance").mock(
            return_value=Response(200, json={"error": [], "result": {}})
        )
        await kraken_client.private("Balance")
        await kraken_client.private("Balance")

    assert info.call_count == 1
    assert balance.call_count == 2


async def test_missing_credentials_raises() -> None:
    client = KrakenClient(base_url="https://api.kraken.test")
    try:
        with pytest.raises(Exception, match="credentials"):
            await client.private("Balance")
    finally:
        await client.aclose()
