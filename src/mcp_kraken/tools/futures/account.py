"""Account / user-data tools for Kraken Futures."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ...kraken import KrakenFuturesClient


def register(mcp: FastMCP, client: KrakenFuturesClient) -> None:
    @mcp.tool(tags={"private", "futures", "account"})
    async def futures_get_wallets() -> Any:
        """Return wallet balances across every Futures account
        (cash / margin / multi-collateral)."""
        return await client.request("GET", "/derivatives/api/v3/accounts")

    @mcp.tool(tags={"private", "futures", "account"})
    async def futures_get_open_orders() -> Any:
        """List every open Futures order on the account."""
        return await client.request("GET", "/derivatives/api/v3/openorders")

    @mcp.tool(tags={"private", "futures", "account"})
    async def futures_get_open_positions() -> Any:
        """List every open Futures position (with P&L if the venue returns it)."""
        return await client.request("GET", "/derivatives/api/v3/openpositions")

    @mcp.tool(tags={"private", "futures", "account"})
    async def futures_get_notifications() -> Any:
        """Return outstanding venue notifications for the account."""
        return await client.request("GET", "/derivatives/api/v3/notifications")
