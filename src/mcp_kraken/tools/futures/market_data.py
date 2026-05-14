"""Public market-data tools for Kraken Futures (no API key required)."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ...kraken import KrakenFuturesClient
from .._common import drop_none


def register(mcp: FastMCP, client: KrakenFuturesClient) -> None:
    @mcp.tool(tags={"public", "futures", "market-data"})
    async def futures_get_tickers() -> Any:
        """Return live tickers for every Futures instrument
        (last/bid/ask/funding rate)."""
        return await client.request("GET", "/derivatives/api/v3/tickers", auth=False)

    @mcp.tool(tags={"public", "futures", "market-data"})
    async def futures_get_instruments() -> Any:
        """Return every Futures product the venue lists (tradable + retired)."""
        return await client.request("GET", "/derivatives/api/v3/instruments", auth=False)

    @mcp.tool(tags={"public", "futures", "market-data"})
    async def futures_get_orderbook(symbol: str) -> Any:
        """Return the current Futures order-book for `symbol` (e.g. `PI_XBTUSD`)."""
        return await client.request(
            "GET",
            "/derivatives/api/v3/orderbook",
            query_params={"symbol": symbol},
            auth=False,
        )

    @mcp.tool(tags={"public", "futures", "market-data"})
    async def futures_get_history(symbol: str, last_time: str | None = None) -> Any:
        """Return historical trades for a Futures `symbol`.

        Args:
            symbol: Instrument id (e.g. `PI_XBTUSD`).
            last_time: ISO8601 timestamp; return trades older than this.
        """
        return await client.request(
            "GET",
            "/derivatives/api/v3/history",
            query_params=drop_none({"symbol": symbol, "lastTime": last_time}),
            auth=False,
        )
