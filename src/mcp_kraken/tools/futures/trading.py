"""Trading tools for Kraken Futures: place / amend / cancel orders."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ...kraken import KrakenFuturesClient
from .._common import drop_none


def register(mcp: FastMCP, client: KrakenFuturesClient) -> None:
    # ---------------------------------------------------------- create_order

    @mcp.tool(tags={"private", "futures", "trading", "write"})
    async def futures_create_order(
        symbol: str,
        side: str,
        order_type: str,
        size: float,
        limit_price: float | None = None,
        stop_price: float | None = None,
        trigger_signal: str | None = None,
        cli_ord_id: str | None = None,
        reduce_only: bool | None = None,
        post_only: bool | None = None,
    ) -> Any:
        """Place a new Futures order.

        Args:
            symbol: Instrument id (e.g. `PI_XBTUSD`).
            side: `buy` or `sell`.
            order_type: `lmt`, `mkt`, `stp`, `take_profit`, `ioc`, `post`, etc.
            size: Contracts to trade.
            limit_price: Required for limit / post-only / stop-limit.
            stop_price: Trigger price for stop / take-profit orders.
            trigger_signal: `mark`, `index`, or `last` — what price feed the
                stop trigger watches.
            cli_ord_id: Client-supplied order id (string).
            reduce_only: Only reduce existing position size.
            post_only: Reject if order would take liquidity.
        """
        return await client.request(
            "POST",
            "/derivatives/api/v3/sendorder",
            post_params=drop_none(
                {
                    "symbol": symbol,
                    "side": side,
                    "orderType": order_type,
                    "size": size,
                    "limitPrice": limit_price,
                    "stopPrice": stop_price,
                    "triggerSignal": trigger_signal,
                    "cliOrdId": cli_ord_id,
                    "reduceOnly": reduce_only,
                    "postOnly": post_only,
                }
            ),
        )

    # ---------------------------------------------------------- cancellations

    @mcp.tool(tags={"private", "futures", "trading", "write"})
    async def futures_cancel_order(
        order_id: str | None = None,
        cli_ord_id: str | None = None,
    ) -> Any:
        """Cancel one Futures order. Provide either `order_id` or `cli_ord_id`."""
        return await client.request(
            "POST",
            "/derivatives/api/v3/cancelorder",
            post_params=drop_none({"order_id": order_id, "cliOrdId": cli_ord_id}),
        )

    @mcp.tool(tags={"private", "futures", "trading", "write"})
    async def futures_cancel_all_orders(symbol: str | None = None) -> Any:
        """Cancel every open Futures order. If `symbol` is set, scope to it."""
        return await client.request(
            "POST",
            "/derivatives/api/v3/cancelallorders",
            post_params=drop_none({"symbol": symbol}),
        )

    @mcp.tool(tags={"private", "futures", "trading", "write"})
    async def futures_dead_mans_switch(timeout: int = 0) -> Any:
        """Schedule a bulk cancel after `timeout` seconds.

        Pass `timeout=0` to disable the switch (default).
        """
        return await client.request(
            "POST",
            "/derivatives/api/v3/cancelallordersafter",
            post_params={"timeout": timeout},
        )
