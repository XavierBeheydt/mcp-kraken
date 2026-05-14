"""MCP tools mapping the Kraken **Spot** REST API.

Each module groups one functional area (market data, account, trading,
etc.). `register(mcp, client)` attaches every Spot tool to the supplied
`FastMCP` instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import (
    account,
    earn,
    funding,
    market_data,
    subaccounts,
    trading,
    websocket_auth,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ...kraken import KrakenClient


def register(mcp: FastMCP, client: KrakenClient) -> None:
    """Register every Spot-backed tool on the given FastMCP server."""
    market_data.register(mcp, client)
    account.register(mcp, client)
    trading.register(mcp, client)
    funding.register(mcp, client)
    earn.register(mcp, client)
    subaccounts.register(mcp, client)
    websocket_auth.register(mcp, client)
