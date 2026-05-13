"""Account / user-data tools (balances, ledger, trade history)."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..kraken import KrakenClient
from ._common import csv, drop_none


def register(mcp: FastMCP, client: KrakenClient) -> None:
    @mcp.tool(tags={"private", "account"})
    async def get_account_balance() -> Any:
        """Return the spot wallet balance per asset."""
        return await client.private("Balance")

    @mcp.tool(tags={"private", "account"})
    async def get_extended_balance() -> Any:
        """Return balance with hold/available breakdowns per asset."""
        return await client.private("ExtendedBalance")

    @mcp.tool(tags={"private", "account"})
    async def get_trade_balance(asset: str = "ZUSD") -> Any:
        """Return trade balance summary (equity, margin, free margin) in `asset`."""
        return await client.private("TradeBalance", {"asset": asset})

    @mcp.tool(tags={"private", "account"})
    async def get_trade_volume(
        pair: list[str] = [],  # noqa: B006
    ) -> Any:
        """Return 30-day volume and current fee tier for the requested pairs."""
        return await client.private("TradeVolume", drop_none({"pair": csv(pair)}))

    @mcp.tool(tags={"private", "account"})
    async def get_ledgers(
        asset: list[str] = [],  # noqa: B006
        aclass: str | None = None,
        type: str | None = None,
        start: int | None = None,
        end: int | None = None,
        ofs: int | None = None,
        without_count: bool | None = None,
    ) -> Any:
        """Return ledger entries (deposits, withdrawals, trades, fees…).

        Args:
            asset: Restrict to specific assets.
            aclass: Asset class filter (default `currency`).
            type: Entry type filter (`deposit`, `withdrawal`, `trade`, ...).
            start: Unix start time, exclusive.
            end: Unix end time, exclusive.
            ofs: Pagination offset.
            without_count: Skip total-count computation for speed.
        """
        return await client.private(
            "Ledgers",
            drop_none(
                {
                    "asset": csv(asset),
                    "aclass": aclass,
                    "type": type,
                    "start": start,
                    "end": end,
                    "ofs": ofs,
                    "without_count": without_count,
                }
            ),
        )

    @mcp.tool(tags={"private", "account"})
    async def query_ledgers(
        id: list[str],
        trades: bool | None = None,
    ) -> Any:
        """Look up specific ledger entries by id.

        Args:
            id: Up to 20 ledger ids.
            trades: Include trade detail rows for `trade` entries.
        """
        return await client.private("QueryLedgers", drop_none({"id": csv(id), "trades": trades}))

    @mcp.tool(tags={"private", "account"})
    async def get_credit_lines() -> Any:
        """Return any available credit facilities on the account."""
        return await client.private("CreditLines")

    @mcp.tool(tags={"private", "account"})
    async def get_api_key_info() -> Any:
        """Return metadata about the API key currently in use, including
        the set of permissions granted to it."""
        return await client.private("GetAPIKeyInfo", skip_permission_check=True)

    # --------------------------------------------------------------- exports

    @mcp.tool(tags={"private", "account", "export"})
    async def request_export_report(
        report: str,
        description: str,
        format: str | None = None,
        fields: list[str] = [],  # noqa: B006
        starttm: int | None = None,
        endtm: int | None = None,
    ) -> Any:
        """Submit a request to export trades or ledgers as CSV/TSV.

        Args:
            report: `trades` or `ledgers`.
            description: Human label shown in the UI.
            format: `CSV` (default) or `TSV`.
            fields: Comma-separated column list (`all` for everything).
            starttm: Start time (unix), defaults to one year ago.
            endtm: End time (unix), defaults to now.
        """
        return await client.private(
            "AddExport",
            drop_none(
                {
                    "report": report,
                    "description": description,
                    "format": format,
                    "fields": csv(fields),
                    "starttm": starttm,
                    "endtm": endtm,
                }
            ),
        )

    @mcp.tool(tags={"private", "account", "export"})
    async def get_export_status(report: str) -> Any:
        """List the current status of every export of type `report`."""
        return await client.private("ExportStatus", {"report": report})

    @mcp.tool(tags={"private", "account", "export"})
    async def retrieve_export(id: str) -> Any:
        """Retrieve the binary content of a completed export by id.

        Returns the raw bytes Base64-encoded as a string under the `data` key.
        """
        return await client.private("RetrieveExport", {"id": id})

    @mcp.tool(tags={"private", "account", "export"})
    async def remove_export(id: str, type: str = "delete") -> Any:
        """Cancel a pending export or delete the file of a completed one.

        Args:
            id: Export request id.
            type: `cancel` or `delete`.
        """
        return await client.private("RemoveExport", {"id": id, "type": type})
