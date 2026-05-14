"""MCP tools mapping the Kraken **Futures** REST API.

This is an initial set: market data (tickers / orderbook / instruments),
account (wallets / open orders / open positions), and basic trading
(create_order / cancel_order / cancel_all_orders). It can be extended
incrementally — Kraken Futures has many more endpoints, but the goal of
v1 is parity with what mcp-kraken Spot users already do day to day.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import account, market_data, trading

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ...kraken import KrakenFuturesClient


def register(mcp: FastMCP, client: KrakenFuturesClient) -> None:
    """Register every Futures-backed tool on the given FastMCP server."""
    market_data.register(mcp, client)
    account.register(mcp, client)
    trading.register(mcp, client)
