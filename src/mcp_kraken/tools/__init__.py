"""MCP tools mapping the Kraken REST APIs.

The MCP server speaks **one Kraken API at a time** — Spot by default,
Futures when `MCP_KRAKEN_API=futures` (or `--api futures` on the CLI).
`register_all` dispatches to the right sub-package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ..config import KrakenApi
    from ..kraken import KrakenClient, KrakenFuturesClient


def register_all(
    mcp: FastMCP,
    client: KrakenClient | KrakenFuturesClient,
    *,
    api: KrakenApi,
) -> None:
    """Register every tool for the active Kraken API on `mcp`."""
    if api == "spot":
        from . import spot

        spot.register(mcp, client)  # type: ignore[arg-type]
    elif api == "futures":
        from . import futures

        futures.register(mcp, client)  # type: ignore[arg-type]
    else:  # pragma: no cover — enum guarded upstream
        raise ValueError(f"unknown Kraken API: {api!r}")
