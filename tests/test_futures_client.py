"""Tests for the Kraken Futures async client.

Mocks the SDK's `request()` rather than the HTTP layer. The wrapper
under test is responsible for routing GET vs POST and query-vs-post
params correctly, requiring credentials on private calls, and
translating SDK exceptions into our local hierarchy.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from kraken import exceptions as sdk_exc

from mcp_kraken.kraken import (
    KrakenAuthError,
    KrakenError,
    KrakenFuturesClient,
    KrakenPermissionError,
)


@pytest.fixture
async def futures_client() -> AsyncIterator[KrakenFuturesClient]:
    client = KrakenFuturesClient(
        api_key="testkey",
        api_secret="dGVzdHNlY3JldA==",  # base64("testsecret")
        base_url="https://futures.kraken.test",
    )
    try:
        yield client
    finally:
        await client.aclose()


def _patch_sdk(client: KrakenFuturesClient, responses: list[Any]) -> AsyncMock:
    mock = AsyncMock(side_effect=responses)
    stub = type("_SdkStub", (), {"request": mock, "close": AsyncMock()})()

    async def _get_stub() -> Any:
        return stub

    client._get_sdk = _get_stub  # type: ignore[method-assign]
    return mock


# ------------------------------------------------------------------ public


async def test_public_get_forwards_query_params(futures_client: KrakenFuturesClient) -> None:
    mock = _patch_sdk(futures_client, [{"orderBook": {}}])
    await futures_client.request(
        "GET",
        "/derivatives/api/v3/orderbook",
        query_params={"symbol": "PI_XBTUSD"},
        auth=False,
    )
    call = mock.await_args
    assert call is not None
    assert call.kwargs["method"] == "GET"
    assert call.kwargs["uri"] == "/derivatives/api/v3/orderbook"
    assert call.kwargs["query_params"] == {"symbol": "PI_XBTUSD"}
    assert call.kwargs["post_params"] is None
    assert call.kwargs["auth"] is False


# ----------------------------------------------------------------- private


async def test_private_call_requires_credentials() -> None:
    client = KrakenFuturesClient(base_url="https://futures.kraken.test")
    try:
        with pytest.raises(KrakenError, match="credentials"):
            await client.request("GET", "/derivatives/api/v3/accounts")
    finally:
        await client.aclose()


async def test_private_post_forwards_post_params(futures_client: KrakenFuturesClient) -> None:
    mock = _patch_sdk(futures_client, [{"sendStatus": {"status": "placed"}}])
    await futures_client.request(
        "POST",
        "/derivatives/api/v3/sendorder",
        post_params={"symbol": "PI_XBTUSD", "side": "buy", "orderType": "lmt", "size": 1},
    )
    call = mock.await_args
    assert call is not None
    assert call.kwargs["method"] == "POST"
    assert call.kwargs["post_params"]["symbol"] == "PI_XBTUSD"
    assert call.kwargs["auth"] is True


# -------------------------------------------------------- error translation


async def test_permission_denied_is_translated(futures_client: KrakenFuturesClient) -> None:
    _patch_sdk(futures_client, [sdk_exc.KrakenPermissionDeniedError("nope")])
    with pytest.raises(KrakenPermissionError):
        await futures_client.request("GET", "/derivatives/api/v3/accounts")


async def test_invalid_key_is_translated(futures_client: KrakenFuturesClient) -> None:
    _patch_sdk(futures_client, [sdk_exc.KrakenInvalidAPIKeyError("bad key")])
    with pytest.raises(KrakenAuthError):
        await futures_client.request("GET", "/derivatives/api/v3/accounts")


# -------------------------------------------------- credentials dispatch


def test_active_credentials_use_futures_pair_when_api_is_futures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`Settings.active_credentials()` must return the Futures pair when
    `MCP_KRAKEN_API=futures`, regardless of whether Spot keys are set."""
    from mcp_kraken.config import Settings

    monkeypatch.setenv("KRAKEN_API_KEY", "spot-key")
    monkeypatch.setenv("KRAKEN_API_SECRET", "spot-secret")
    monkeypatch.setenv("KRAKEN_FUTURES_API_KEY", "futures-key")
    monkeypatch.setenv("KRAKEN_FUTURES_API_SECRET", "futures-secret")
    monkeypatch.setenv("MCP_KRAKEN_API", "futures")

    settings = Settings()
    key, secret = settings.active_credentials()
    assert key is not None and key.get_secret_value() == "futures-key"
    assert secret is not None and secret.get_secret_value() == "futures-secret"
    assert settings.have_kraken_credentials() is True


def test_active_credentials_use_spot_pair_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mcp_kraken.config import Settings

    monkeypatch.setenv("KRAKEN_API_KEY", "spot-key")
    monkeypatch.setenv("KRAKEN_API_SECRET", "spot-secret")
    monkeypatch.delenv("KRAKEN_FUTURES_API_KEY", raising=False)
    monkeypatch.delenv("KRAKEN_FUTURES_API_SECRET", raising=False)
    monkeypatch.delenv("MCP_KRAKEN_API", raising=False)

    settings = Settings()
    key, secret = settings.active_credentials()
    assert key is not None and key.get_secret_value() == "spot-key"
    assert secret is not None and secret.get_secret_value() == "spot-secret"


def test_futures_without_futures_credentials_reports_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setting Spot keys must NOT satisfy the credential check when
    Futures is the active API."""
    from mcp_kraken.config import Settings

    monkeypatch.setenv("KRAKEN_API_KEY", "spot-key")
    monkeypatch.setenv("KRAKEN_API_SECRET", "spot-secret")
    monkeypatch.delenv("KRAKEN_FUTURES_API_KEY", raising=False)
    monkeypatch.delenv("KRAKEN_FUTURES_API_SECRET", raising=False)
    monkeypatch.setenv("MCP_KRAKEN_API", "futures")

    settings = Settings()
    assert settings.have_kraken_credentials() is False
    assert settings.active_credentials() == (None, None)
