"""Tests for the Kraken async client.

Since the transport now lives in `python-kraken-sdk`, we mock the SDK's
`request()` method rather than the HTTP layer. The wrapper under test is
responsible for:

* invoking the SDK with the right URI / method / auth flag / `do_json`,
* translating SDK exceptions into our local hierarchy,
* enforcing API-key permissions before private calls,
* surfacing Kraken's `error` array even when the SDK returns the envelope.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from kraken import exceptions as sdk_exc

from mcp_kraken.kraken import (
    KrakenAPIError,
    KrakenAuthError,
    KrakenClient,
    KrakenError,
    KrakenPermissionError,
    KrakenRateLimitError,
)


def _patch_sdk(client: KrakenClient, responses: list[Any]) -> AsyncMock:
    """Replace the SDK request method with a sequence of canned responses.

    `responses` may contain return values or exception instances; exceptions
    are raised, anything else is returned.
    """
    mock = AsyncMock(side_effect=responses)
    # Short-circuit lazy SDK init: hand back a stub whose `request` is
    # the mock above.
    stub = type("_SdkStub", (), {"request": mock, "close": AsyncMock()})()

    async def _get_stub() -> Any:
        return stub

    client._get_sdk = _get_stub  # type: ignore[method-assign]
    return mock


# --------------------------------------------------------------------- public


async def test_public_endpoint_returns_result(kraken_client: KrakenClient) -> None:
    mock = _patch_sdk(kraken_client, [{"unixtime": 1700000000}])
    result = await kraken_client.public("Time")
    assert result == {"unixtime": 1700000000}
    call = mock.await_args
    assert call is not None
    assert call.kwargs["method"] == "GET"
    assert call.kwargs["uri"] == "/0/public/Time"
    assert call.kwargs["auth"] is False


async def test_public_passes_query_params(kraken_client: KrakenClient) -> None:
    mock = _patch_sdk(kraken_client, [{"XXBTZUSD": {}}])
    await kraken_client.public("Ticker", {"pair": "XBTUSD"})
    call = mock.await_args
    assert call is not None
    assert call.kwargs["params"] == {"pair": "XBTUSD"}


async def test_envelope_with_error_array_raises(kraken_client: KrakenClient) -> None:
    """When the SDK doesn't classify an error code, it returns the full
    envelope. The wrapper must still raise so callers see a typed error.
    """
    _patch_sdk(kraken_client, [{"error": ["EService:Busy"], "result": None}])
    with pytest.raises(KrakenAPIError, match="EService:Busy"):
        await kraken_client.public("Time")


# ---------------------------------------------------------------- private


async def test_missing_credentials_raises() -> None:
    client = KrakenClient(base_url="https://api.kraken.test")
    try:
        with pytest.raises(KrakenError, match="credentials"):
            await client.private("Balance")
    finally:
        await client.aclose()


async def test_private_call_targets_correct_uri(kraken_client: KrakenClient) -> None:
    mock = _patch_sdk(
        kraken_client,
        [
            # GetAPIKeyInfo probe — permissions covered for Balance.
            {"permissions": {"funding": {"query": True}}},
            # Balance response.
            {"ZUSD": "100"},
        ],
    )
    result = await kraken_client.private("Balance")
    assert result == {"ZUSD": "100"}

    probe, real = mock.await_args_list
    assert probe.kwargs["uri"] == "/0/private/GetAPIKeyInfo"
    assert probe.kwargs["auth"] is True
    assert real.kwargs["uri"] == "/0/private/Balance"
    assert real.kwargs["method"] == "POST"
    assert real.kwargs["do_json"] is False


async def test_batch_endpoints_request_json_body(kraken_client: KrakenClient) -> None:
    """AddOrderBatch / CancelOrderBatch must send `do_json=True` so the SDK
    encodes the payload as JSON (Kraken rejects URL-encoded arrays here)."""
    mock = _patch_sdk(
        kraken_client,
        [
            {"permissions": {"orders": {"create_modify": True, "cancel": True}}},
            {"orders": []},
            {"count": 1},
        ],
    )
    await kraken_client.private(
        "AddOrderBatch",
        {"pair": "XBTUSD", "orders": [{"ordertype": "market"}]},
    )
    await kraken_client.private("CancelOrderBatch", {"orders": ["O1"]})

    calls = mock.await_args_list
    assert calls[1].kwargs["uri"] == "/0/private/AddOrderBatch"
    assert calls[1].kwargs["do_json"] is True
    assert calls[2].kwargs["uri"] == "/0/private/CancelOrderBatch"
    assert calls[2].kwargs["do_json"] is True


# --------------------------------------------------------- error translation


async def test_permission_denied_sdk_error_is_translated(
    kraken_client: KrakenClient,
) -> None:
    _patch_sdk(
        kraken_client,
        [
            # Permissions probe succeeds with everything granted, so the
            # proactive check passes and we reach the SDK call that fails.
            {"permissions": {"funding": {"query": True}}},
            sdk_exc.KrakenPermissionDeniedError("denied"),
        ],
    )
    with pytest.raises(KrakenPermissionError):
        await kraken_client.private("Balance")


async def test_invalid_key_sdk_error_is_translated(kraken_client: KrakenClient) -> None:
    _patch_sdk(
        kraken_client,
        [
            # The probe also fails; the wrapper falls back to "permissions
            # unknown" and lets the real call run, which then raises.
            sdk_exc.KrakenInvalidAPIKeyError("bad key"),
            sdk_exc.KrakenInvalidAPIKeyError("bad key"),
        ],
    )
    with pytest.raises(KrakenAuthError):
        await kraken_client.private("Balance")


async def test_rate_limit_sdk_error_is_translated(kraken_client: KrakenClient) -> None:
    _patch_sdk(kraken_client, [sdk_exc.KrakenRateLimitExceededError("slow down")])
    with pytest.raises(KrakenRateLimitError):
        await kraken_client.public("Trades", {"pair": "XBTUSD"})


# ------------------------------------------------------ permission caching


async def test_proactive_permission_block(kraken_client: KrakenClient) -> None:
    """When GetAPIKeyInfo says the key lacks `withdraw`, calling `Withdraw`
    must raise without invoking the SDK a second time."""
    mock = _patch_sdk(
        kraken_client,
        [{"permissions": {"funding": {"query": True, "withdraw": False}}}],
    )
    with pytest.raises(KrakenPermissionError):
        await kraken_client.private("Withdraw", {"asset": "XBT", "key": "k", "amount": "0.01"})
    # Only the GetAPIKeyInfo probe should have been issued.
    assert mock.await_count == 1


async def test_permissions_introspection_is_cached(kraken_client: KrakenClient) -> None:
    mock = _patch_sdk(
        kraken_client,
        [
            {"permissions": {"funding": {"query": True}}},
            {},
            {},
        ],
    )
    await kraken_client.private("Balance")
    await kraken_client.private("Balance")

    uris = [c.kwargs["uri"] for c in mock.await_args_list]
    assert uris.count("/0/private/GetAPIKeyInfo") == 1
    assert uris.count("/0/private/Balance") == 2


async def test_permissions_probe_falls_back_on_unknown_method(
    kraken_client: KrakenClient,
) -> None:
    """If GetAPIKeyInfo isn't supported, the client must NOT block calls."""
    _patch_sdk(
        kraken_client,
        [
            sdk_exc.KrakenInvalidArgumentsError("Unknown method"),
            {"ZUSD": "100"},
        ],
    )
    # Despite the probe failing, the Balance call must reach the SDK and
    # return its result — Kraken itself becomes the source of truth for
    # permissions.
    assert await kraken_client.private("Balance") == {"ZUSD": "100"}
