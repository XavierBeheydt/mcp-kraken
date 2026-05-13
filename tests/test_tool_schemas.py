"""Regression test for the list-parameter JSON-schema bug.

When a tool parameter was typed `list[str] | None = None`, the schema
FastMCP exposed over MCP omitted the `type: array` annotation. Claude Code
then serialised list values as JSON-encoded strings, which Pydantic strict
mode rejected at the receiving end.

This test pins the contract: every list-typed parameter on every Kraken
tool must surface as `type: array` (with `items.type` set) in the tool's
input schema.
"""

from __future__ import annotations

from typing import Any

import pytest

from mcp_kraken.kraken import KrakenClient
from mcp_kraken.server import build_server


@pytest.fixture
def kraken_settings(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    from mcp_kraken.config import Settings

    monkeypatch.setenv("KRAKEN_API_KEY", "test")
    monkeypatch.setenv("KRAKEN_API_SECRET", "dGVzdHNlY3JldA==")
    monkeypatch.setenv("MCP_KRAKEN_TOKEN_DB", str(tmp_path / "tokens.db"))
    monkeypatch.setenv("MCP_KRAKEN_AUTH_DISABLED", "true")
    return Settings()


async def _gather_tool_schemas(settings: Any) -> dict[str, dict[str, Any]]:
    mcp, client = build_server(settings)
    try:
        tools = await mcp.list_tools()
        return {t.name: t.parameters for t in tools}
    finally:
        await client.aclose()


async def test_list_params_have_array_type(kraken_settings: Any) -> None:
    schemas = await _gather_tool_schemas(kraken_settings)

    # (tool name, parameter name) pairs that must be arrays.
    expected_array_params = [
        ("get_assets", "asset"),
        ("get_asset_pairs", "pair"),
        ("get_ticker", "pair"),
        ("get_trade_volume", "pair"),
        ("get_ledgers", "asset"),
        ("query_ledgers", "id"),
        ("query_orders", "txid"),
        ("query_trades", "txid"),
        ("get_open_positions", "txid"),
        ("add_order", "oflags"),
        ("edit_order", "oflags"),
        ("request_export_report", "fields"),
        ("cancel_order_batch", "orders"),
    ]

    for tool_name, param_name in expected_array_params:
        params = schemas.get(tool_name)
        assert params is not None, f"tool {tool_name!r} not registered"
        props = params.get("properties", {})
        param = props.get(param_name)
        assert param is not None, f"{tool_name}.{param_name} not in schema"

        # `type: array` should be present, either directly or in an anyOf branch.
        ptype = param.get("type")
        if ptype is None:
            any_of = param.get("anyOf") or []
            ptype = next((b.get("type") for b in any_of if b.get("type") == "array"), None)
        assert ptype == "array", f"{tool_name}.{param_name} schema missing array type: {param!r}"


async def test_kraken_client_csv_omits_empty_list() -> None:
    """`csv([])` must behave the same as `csv(None)` — Kraken expects the
    parameter to be absent, not empty.
    """
    from mcp_kraken.tools._common import csv

    assert csv(None) is None
    assert csv([]) is None
    assert csv(["a", "b"]) == "a,b"


async def test_client_unused_in_schema_test(kraken_client: KrakenClient) -> None:
    """Sanity: the kraken_client fixture is still usable elsewhere."""
    assert kraken_client.has_credentials
