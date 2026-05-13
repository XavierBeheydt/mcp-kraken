"""Kraken API-key permission model.

Maps each private REST endpoint to the permission(s) it requires. We use
this both to (a) reject calls proactively when we know the key lacks a
permission, and (b) attach a helpful hint to the error returned by the MCP
tool.

The permission names mirror the ones shown in the Kraken UI when issuing a
key. Permissions reported by `GetAPIKeyInfo` are mapped onto this enum at
runtime.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum


class KrakenPermission(StrEnum):
    """Capability flags toggled on a Kraken API key."""

    # Funds
    QUERY_FUNDS = "query_funds"
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    EARN = "earn"

    # Orders & trades
    QUERY_OPEN_ORDERS = "query_open_orders"
    QUERY_CLOSED_ORDERS = "query_closed_orders"
    CREATE_MODIFY_ORDERS = "create_modify_orders"
    CANCEL_ORDERS = "cancel_orders"

    # Data
    QUERY_LEDGER = "query_ledger"
    EXPORT_DATA = "export_data"

    # WebSocket interface (REST works by default; this enables WS)
    WEBSOCKET = "websocket"


PERMISSION_REQUIREMENTS: dict[str, frozenset[KrakenPermission]] = {
    # ------------------------------------------------------------------ Funds
    "Balance": frozenset({KrakenPermission.QUERY_FUNDS}),
    "ExtendedBalance": frozenset({KrakenPermission.QUERY_FUNDS}),
    "TradeBalance": frozenset({KrakenPermission.QUERY_FUNDS}),
    "DepositMethods": frozenset({KrakenPermission.DEPOSIT}),
    "DepositAddresses": frozenset({KrakenPermission.DEPOSIT}),
    "DepositStatus": frozenset({KrakenPermission.DEPOSIT}),
    "WithdrawalMethods": frozenset({KrakenPermission.WITHDRAW}),
    "WithdrawalAddresses": frozenset({KrakenPermission.WITHDRAW}),
    "WithdrawalInfo": frozenset({KrakenPermission.WITHDRAW}),
    "Withdraw": frozenset({KrakenPermission.WITHDRAW}),
    "WithdrawalStatus": frozenset({KrakenPermission.WITHDRAW}),
    "CancelWithdrawal": frozenset({KrakenPermission.WITHDRAW}),
    "WalletTransfer": frozenset({KrakenPermission.WITHDRAW}),
    # ----------------------------------------------------------------- Orders
    "OpenOrders": frozenset({KrakenPermission.QUERY_OPEN_ORDERS}),
    "ClosedOrders": frozenset({KrakenPermission.QUERY_CLOSED_ORDERS}),
    "QueryOrders": frozenset({KrakenPermission.QUERY_CLOSED_ORDERS}),
    "TradeHistory": frozenset({KrakenPermission.QUERY_CLOSED_ORDERS}),
    "QueryTrades": frozenset({KrakenPermission.QUERY_CLOSED_ORDERS}),
    "OpenPositions": frozenset({KrakenPermission.QUERY_OPEN_ORDERS}),
    "TradeVolume": frozenset({KrakenPermission.QUERY_CLOSED_ORDERS}),
    "AddOrder": frozenset({KrakenPermission.CREATE_MODIFY_ORDERS}),
    "AmendOrder": frozenset({KrakenPermission.CREATE_MODIFY_ORDERS}),
    "EditOrder": frozenset({KrakenPermission.CREATE_MODIFY_ORDERS}),
    "AddOrderBatch": frozenset({KrakenPermission.CREATE_MODIFY_ORDERS}),
    "CancelOrder": frozenset({KrakenPermission.CANCEL_ORDERS}),
    "CancelAllOrders": frozenset({KrakenPermission.CANCEL_ORDERS}),
    "CancelAllOrdersAfter": frozenset({KrakenPermission.CANCEL_ORDERS}),
    "CancelOrderBatch": frozenset({KrakenPermission.CANCEL_ORDERS}),
    # ------------------------------------------------------------------ Data
    "Ledgers": frozenset({KrakenPermission.QUERY_LEDGER}),
    "QueryLedgers": frozenset({KrakenPermission.QUERY_LEDGER}),
    "AddExport": frozenset({KrakenPermission.EXPORT_DATA}),
    "ExportStatus": frozenset({KrakenPermission.EXPORT_DATA}),
    "RetrieveExport": frozenset({KrakenPermission.EXPORT_DATA}),
    "RemoveExport": frozenset({KrakenPermission.EXPORT_DATA}),
    # ------------------------------------------------------------------ Earn
    "Earn/Allocate": frozenset({KrakenPermission.EARN}),
    "Earn/Deallocate": frozenset({KrakenPermission.EARN}),
    "Earn/AllocateStatus": frozenset({KrakenPermission.EARN}),
    "Earn/DeallocateStatus": frozenset({KrakenPermission.EARN}),
    "Earn/Strategies": frozenset({KrakenPermission.EARN}),
    "Earn/Allocations": frozenset({KrakenPermission.EARN}),
    # ------------------------------------------------------------- WebSocket
    "GetWebSocketsToken": frozenset({KrakenPermission.WEBSOCKET}),
    # Subaccounts and credit lines: not gated by a discrete permission flag.
    "CreateSubaccount": frozenset(),
    "AccountTransfer": frozenset(),
    "CreditLines": frozenset({KrakenPermission.QUERY_FUNDS}),
    "GetAPIKeyInfo": frozenset(),  # always callable on a valid key
}


def _flatten(node: object, prefix: str = "") -> list[str]:
    """Walk the nested permission tree returned by `GetAPIKeyInfo`.

    Returns a list of `dot.path` strings for every boolean leaf set to True.
    """
    found: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            path = f"{prefix}.{k}" if prefix else k
            found.extend(_flatten(v, path))
    elif node is True:
        found.append(prefix)
    return found


# Mapping from Kraken's reported permission paths to our enum.
# Paths are lower-cased dot-separated keys from the nested permissions object.
# This is best-effort: Kraken's exact payload shape is not formally documented
# and may evolve. If a path is unknown we ignore it and fall back to letting
# Kraken itself enforce permissions.
_PATH_TO_PERMISSION: dict[str, KrakenPermission] = {
    "funding.query": KrakenPermission.QUERY_FUNDS,
    "funding.deposit": KrakenPermission.DEPOSIT,
    "funding.withdraw": KrakenPermission.WITHDRAW,
    "funding.earn": KrakenPermission.EARN,
    "trade_data.query_balance": KrakenPermission.QUERY_FUNDS,
    "orders.query.open_orders_trades": KrakenPermission.QUERY_OPEN_ORDERS,
    "orders.query.closed_orders_trades": KrakenPermission.QUERY_CLOSED_ORDERS,
    "orders.create_modify": KrakenPermission.CREATE_MODIFY_ORDERS,
    "orders.cancel": KrakenPermission.CANCEL_ORDERS,
    "data.query_ledger_entries": KrakenPermission.QUERY_LEDGER,
    "data.export_data": KrakenPermission.EXPORT_DATA,
    "earn.query": KrakenPermission.EARN,
    "earn.allocate": KrakenPermission.EARN,
    "websocket.interface": KrakenPermission.WEBSOCKET,
}


def parse_permissions(api_key_info: Mapping[str, object]) -> frozenset[KrakenPermission]:
    """Translate a `GetAPIKeyInfo` response into our permission set."""
    raw = api_key_info.get("permissions", {})
    perms: set[KrakenPermission] = set()
    for path in _flatten(raw):
        mapped = _PATH_TO_PERMISSION.get(path.lower())
        if mapped is not None:
            perms.add(mapped)
    return frozenset(perms)
