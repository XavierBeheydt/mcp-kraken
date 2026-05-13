"""Public market-data tools (no Kraken API key required)."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..kraken import KrakenClient
from ._common import csv, drop_none


def register(mcp: FastMCP, client: KrakenClient) -> None:
    @mcp.tool(tags={"public", "market-data"})
    async def get_server_time() -> Any:
        """Return Kraken's current server time (unix and RFC1123)."""
        return await client.public("Time")

    @mcp.tool(tags={"public", "market-data"})
    async def get_system_status() -> Any:
        """Return the current trading-engine status (`online`, `maintenance`,
        `cancel_only`, `post_only`)."""
        return await client.public("SystemStatus")

    @mcp.tool(tags={"public", "market-data"})
    async def get_assets(
        asset: list[str] | None = None,
        aclass: str | None = None,
    ) -> Any:
        """Return info about one or more assets.

        Args:
            asset: Restrict to specific asset codes (e.g. `["XBT", "ETH"]`).
            aclass: Asset class filter (default `currency`).
        """
        return await client.public(
            "Assets",
            drop_none({"asset": csv(asset), "aclass": aclass}),
        )

    @mcp.tool(tags={"public", "market-data"})
    async def get_asset_pairs(
        pair: list[str] | None = None,
        info: str | None = None,
        country_code: str | None = None,
    ) -> Any:
        """Return tradable pair metadata.

        Args:
            pair: Restrict to specific pairs (e.g. `["XBTUSD"]`).
            info: One of `info`, `leverage`, `fees`, `margin`.
            country_code: Two-letter ISO code, filters region-restricted pairs.
        """
        return await client.public(
            "AssetPairs",
            drop_none({"pair": csv(pair), "info": info, "country_code": country_code}),
        )

    @mcp.tool(tags={"public", "market-data"})
    async def get_ticker(pair: list[str] | None = None) -> Any:
        """Return ticker data (ask, bid, last, vol, etc.) for the given pairs."""
        return await client.public("Ticker", drop_none({"pair": csv(pair)}))

    @mcp.tool(tags={"public", "market-data"})
    async def get_ohlc(
        pair: str,
        interval: int = 1,
        since: int | None = None,
    ) -> Any:
        """Return OHLC candles.

        Args:
            pair: Trading pair (e.g. `XBTUSD`).
            interval: Candle width in minutes — one of
                `1, 5, 15, 30, 60, 240, 1440, 10080, 21600`.
            since: Unix timestamp; return candles after this.
        """
        return await client.public(
            "OHLC",
            drop_none({"pair": pair, "interval": interval, "since": since}),
        )

    @mcp.tool(tags={"public", "market-data"})
    async def get_order_book(pair: str, count: int = 100) -> Any:
        """Return an order-book snapshot.

        Args:
            pair: Trading pair.
            count: Max number of asks/bids (1–500).
        """
        return await client.public("Depth", {"pair": pair, "count": count})

    @mcp.tool(tags={"public", "market-data"})
    async def get_recent_trades(
        pair: str,
        since: int | None = None,
        count: int | None = None,
    ) -> Any:
        """Return recent trades for a pair."""
        return await client.public(
            "Trades",
            drop_none({"pair": pair, "since": since, "count": count}),
        )

    @mcp.tool(tags={"public", "market-data"})
    async def get_recent_spreads(pair: str, since: int | None = None) -> Any:
        """Return recent bid/ask spread snapshots."""
        return await client.public("Spread", drop_none({"pair": pair, "since": since}))
