"""Tests for permission parsing and endpoint requirement mapping."""

from __future__ import annotations

from mcp_kraken.kraken.permissions import (
    PERMISSION_REQUIREMENTS,
    KrakenPermission,
    parse_permissions,
)


def test_parse_full_permission_payload() -> None:
    payload = {
        "key": "abc",
        "permissions": {
            "funding": {"query": True, "deposit": True, "withdraw": False, "earn": True},
            "orders": {
                "query": {"open_orders_trades": True, "closed_orders_trades": False},
                "create_modify": True,
                "cancel": True,
            },
            "data": {"query_ledger_entries": True, "export_data": False},
            "websocket": {"interface": True},
        },
    }
    perms = parse_permissions(payload)
    assert KrakenPermission.QUERY_FUNDS in perms
    assert KrakenPermission.DEPOSIT in perms
    assert KrakenPermission.EARN in perms
    assert KrakenPermission.WITHDRAW not in perms
    assert KrakenPermission.QUERY_OPEN_ORDERS in perms
    assert KrakenPermission.QUERY_CLOSED_ORDERS not in perms
    assert KrakenPermission.CREATE_MODIFY_ORDERS in perms
    assert KrakenPermission.CANCEL_ORDERS in perms
    assert KrakenPermission.QUERY_LEDGER in perms
    assert KrakenPermission.EXPORT_DATA not in perms
    assert KrakenPermission.WEBSOCKET in perms


def test_parse_empty_payload_returns_empty() -> None:
    assert parse_permissions({}) == frozenset()
    assert parse_permissions({"permissions": {}}) == frozenset()


def test_known_endpoints_have_requirements() -> None:
    assert KrakenPermission.QUERY_FUNDS in PERMISSION_REQUIREMENTS["Balance"]
    assert KrakenPermission.CREATE_MODIFY_ORDERS in PERMISSION_REQUIREMENTS["AddOrder"]
    assert KrakenPermission.CANCEL_ORDERS in PERMISSION_REQUIREMENTS["CancelOrder"]
    assert KrakenPermission.WEBSOCKET in PERMISSION_REQUIREMENTS["GetWebSocketsToken"]
    assert KrakenPermission.WITHDRAW in PERMISSION_REQUIREMENTS["Withdraw"]


def test_get_api_key_info_has_no_requirements() -> None:
    """Must always be callable to bootstrap permission detection."""
    assert PERMISSION_REQUIREMENTS["GetAPIKeyInfo"] == frozenset()
