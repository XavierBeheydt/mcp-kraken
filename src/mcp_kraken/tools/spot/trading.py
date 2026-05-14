"""Trading tools: orders, positions, trade history."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ...kraken import KrakenClient
from .._common import csv, drop_none


def register(mcp: FastMCP, client: KrakenClient) -> None:
    # ---------------------------------------------------------- query orders

    @mcp.tool(tags={"private", "trading"})
    async def get_open_orders(
        trades: bool | None = None,
        userref: int | None = None,
        cl_ord_id: str | None = None,
    ) -> Any:
        """List currently open orders."""
        return await client.private(
            "OpenOrders",
            drop_none({"trades": trades, "userref": userref, "cl_ord_id": cl_ord_id}),
        )

    @mcp.tool(tags={"private", "trading"})
    async def get_closed_orders(
        trades: bool | None = None,
        userref: int | None = None,
        cl_ord_id: str | None = None,
        start: int | None = None,
        end: int | None = None,
        ofs: int | None = None,
        closetime: str | None = None,
        consolidate_taker: bool | None = None,
        without_count: bool | None = None,
    ) -> Any:
        """List closed orders.

        Args:
            trades: Embed individual trade fills.
            userref: Filter by user-supplied reference id.
            cl_ord_id: Filter by client order id.
            start: Lower bound (unix or transaction id).
            end: Upper bound.
            ofs: Pagination offset.
            closetime: `open`, `close` (default), or `both`.
            consolidate_taker: Aggregate fills (default True).
            without_count: Skip total-count for speed.
        """
        return await client.private(
            "ClosedOrders",
            drop_none(
                {
                    "trades": trades,
                    "userref": userref,
                    "cl_ord_id": cl_ord_id,
                    "start": start,
                    "end": end,
                    "ofs": ofs,
                    "closetime": closetime,
                    "consolidate_taker": consolidate_taker,
                    "without_count": without_count,
                }
            ),
        )

    @mcp.tool(tags={"private", "trading"})
    async def query_orders(
        txid: list[str],
        trades: bool | None = None,
        userref: int | None = None,
        consolidate_taker: bool | None = None,
    ) -> Any:
        """Look up specific orders by transaction id (up to 50)."""
        return await client.private(
            "QueryOrders",
            drop_none(
                {
                    "txid": csv(txid),
                    "trades": trades,
                    "userref": userref,
                    "consolidate_taker": consolidate_taker,
                }
            ),
        )

    # ---------------------------------------------------------- trade history

    @mcp.tool(tags={"private", "trading"})
    async def get_trade_history(
        type: str | None = None,
        trades: bool | None = None,
        start: int | None = None,
        end: int | None = None,
        ofs: int | None = None,
        consolidate_taker: bool | None = None,
        without_count: bool | None = None,
    ) -> Any:
        """Return historical fills.

        Args:
            type: `all`, `any position`, `closed position`, `closing position`,
                `no position`.
            trades: Embed associated trade records.
            start: Lower bound (unix or txid).
            end: Upper bound.
            ofs: Pagination offset.
        """
        return await client.private(
            "TradeHistory",
            drop_none(
                {
                    "type": type,
                    "trades": trades,
                    "start": start,
                    "end": end,
                    "ofs": ofs,
                    "consolidate_taker": consolidate_taker,
                    "without_count": without_count,
                }
            ),
        )

    @mcp.tool(tags={"private", "trading"})
    async def query_trades(txid: list[str], trades: bool | None = None) -> Any:
        """Look up specific trades by id (up to 20)."""
        return await client.private("QueryTrades", drop_none({"txid": csv(txid), "trades": trades}))

    # ---------------------------------------------------------- positions

    @mcp.tool(tags={"private", "trading"})
    async def get_open_positions(
        txid: list[str] = [],  # noqa: B006
        docalcs: bool | None = None,
        consolidation: str | None = None,
    ) -> Any:
        """List open margin positions.

        Args:
            txid: Restrict to specific position ids.
            docalcs: Include realised P&L calculations.
            consolidation: `market` to consolidate by market.
        """
        return await client.private(
            "OpenPositions",
            drop_none(
                {
                    "txid": csv(txid),
                    "docalcs": docalcs,
                    "consolidation": consolidation,
                }
            ),
        )

    # ---------------------------------------------------------- add order

    @mcp.tool(tags={"private", "trading", "write"})
    async def add_order(
        pair: str,
        type: str,
        ordertype: str,
        volume: str,
        price: str | None = None,
        price2: str | None = None,
        leverage: str | None = None,
        oflags: list[str] = [],  # noqa: B006
        timeinforce: str | None = None,
        starttm: str | None = None,
        expiretm: str | None = None,
        userref: int | None = None,
        cl_ord_id: str | None = None,
        validate: bool | None = None,
        close_ordertype: str | None = None,
        close_price: str | None = None,
        close_price2: str | None = None,
        deadline: str | None = None,
        reduce_only: bool | None = None,
        stptype: str | None = None,
        trigger: str | None = None,
        displayvol: str | None = None,
    ) -> Any:
        """Place a new order.

        Args:
            pair: Asset pair (e.g. `XBTUSD`).
            type: `buy` or `sell`.
            ordertype: `market`, `limit`, `stop-loss`, `take-profit`,
                `stop-loss-limit`, `take-profit-limit`, `trailing-stop`,
                `trailing-stop-limit`, `iceberg`, `settle-position`.
            volume: Order quantity in base asset units.
            price: Limit/stop price.
            price2: Secondary price (e.g. for stop-limit).
            leverage: Margin leverage (e.g. `2:1`).
            oflags: Order flags (`post`, `fcib`, `fciq`, `nompp`, `viqc`).
            timeinforce: `GTC`, `IOC`, `GTD`.
            expiretm: Expiration time.
            userref: User reference id (integer).
            cl_ord_id: Client order id (string).
            validate: If True, only validate — do not submit.
            reduce_only: Reduce existing position only (margin).
            stptype: Self-trade prevention behaviour.
            trigger: Price trigger source (`index` or `last`).
        """
        return await client.private(
            "AddOrder",
            drop_none(
                {
                    "pair": pair,
                    "type": type,
                    "ordertype": ordertype,
                    "volume": volume,
                    "price": price,
                    "price2": price2,
                    "leverage": leverage,
                    "oflags": csv(oflags),
                    "timeinforce": timeinforce,
                    "starttm": starttm,
                    "expiretm": expiretm,
                    "userref": userref,
                    "cl_ord_id": cl_ord_id,
                    "validate": validate,
                    "close[ordertype]": close_ordertype,
                    "close[price]": close_price,
                    "close[price2]": close_price2,
                    "deadline": deadline,
                    "reduce_only": reduce_only,
                    "stptype": stptype,
                    "trigger": trigger,
                    "displayvol": displayvol,
                }
            ),
        )

    @mcp.tool(tags={"private", "trading", "write"})
    async def add_order_batch(
        pair: str,
        orders: list[dict[str, Any]],
        deadline: str | None = None,
        validate: bool | None = None,
    ) -> Any:
        """Submit up to 15 orders for the same pair in a single call.

        Args:
            pair: Asset pair the batch targets.
            orders: List of order dicts (same fields as `add_order`, but as a
                list of objects rather than positional parameters).
            deadline: Send timeout.
            validate: Only validate — do not submit.
        """
        body: dict[str, Any] = {"pair": pair, "orders": orders}
        if deadline is not None:
            body["deadline"] = deadline
        if validate is not None:
            body["validate"] = validate
        return await client.private("AddOrderBatch", body)

    @mcp.tool(tags={"private", "trading", "write"})
    async def amend_order(
        txid: str | None = None,
        cl_ord_id: str | None = None,
        order_qty: str | None = None,
        display_qty: str | None = None,
        limit_price: str | None = None,
        trigger_price: str | None = None,
        post_only: bool | None = None,
        deadline: str | None = None,
    ) -> Any:
        """Amend an existing order in-place (preserves queue priority where
        the venue allows). Provide either `txid` or `cl_ord_id`."""
        return await client.private(
            "AmendOrder",
            drop_none(
                {
                    "txid": txid,
                    "cl_ord_id": cl_ord_id,
                    "order_qty": order_qty,
                    "display_qty": display_qty,
                    "limit_price": limit_price,
                    "trigger_price": trigger_price,
                    "post_only": post_only,
                    "deadline": deadline,
                }
            ),
        )

    @mcp.tool(tags={"private", "trading", "write"})
    async def edit_order(
        txid: str,
        pair: str,
        volume: str | None = None,
        price: str | None = None,
        price2: str | None = None,
        oflags: list[str] = [],  # noqa: B006
        deadline: str | None = None,
        cancel_response: bool | None = None,
        userref: int | None = None,
        validate: bool | None = None,
    ) -> Any:
        """Edit an order by replacing it (cancels + recreates atomically)."""
        return await client.private(
            "EditOrder",
            drop_none(
                {
                    "txid": txid,
                    "pair": pair,
                    "volume": volume,
                    "price": price,
                    "price2": price2,
                    "oflags": csv(oflags),
                    "deadline": deadline,
                    "cancel_response": cancel_response,
                    "userref": userref,
                    "validate": validate,
                }
            ),
        )

    # ---------------------------------------------------------- cancellations

    @mcp.tool(tags={"private", "trading", "write"})
    async def cancel_order(
        txid: str | None = None,
        cl_ord_id: str | None = None,
    ) -> Any:
        """Cancel one order by id."""
        return await client.private(
            "CancelOrder", drop_none({"txid": txid, "cl_ord_id": cl_ord_id})
        )

    @mcp.tool(tags={"private", "trading", "write"})
    async def cancel_all_orders() -> Any:
        """Cancel every open order."""
        return await client.private("CancelAllOrders")

    @mcp.tool(tags={"private", "trading", "write"})
    async def cancel_all_orders_after(timeout: int) -> Any:
        """Dead-man-switch: schedule a bulk cancel after `timeout` seconds.

        Setting timeout=0 disables the switch.
        """
        return await client.private("CancelAllOrdersAfter", {"timeout": timeout})

    @mcp.tool(tags={"private", "trading", "write"})
    async def cancel_order_batch(orders: list[str]) -> Any:
        """Cancel up to 50 orders in a single call.

        `orders` may contain `txid`s or `cl_ord_id`s.
        """
        return await client.private("CancelOrderBatch", {"orders": orders})
