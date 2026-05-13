"""Subaccount tools (available to qualifying institutional clients)."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..kraken import KrakenClient


def register(mcp: FastMCP, client: KrakenClient) -> None:
    @mcp.tool(tags={"private", "subaccounts", "write"})
    async def create_subaccount(username: str, email: str) -> Any:
        """Create a new sub-account.

        Args:
            username: Unique username for the sub-account.
            email: Contact email.
        """
        return await client.private("CreateSubaccount", {"username": username, "email": email})

    @mcp.tool(tags={"private", "subaccounts", "write"})
    async def account_transfer(asset: str, amount: str, from_account: str, to_account: str) -> Any:
        """Transfer funds between the master account and a sub-account.

        Args:
            asset: Asset code.
            amount: Amount.
            from_account: Source account email or username.
            to_account: Destination account email or username.
        """
        return await client.private(
            "AccountTransfer",
            {
                "asset": asset,
                "amount": amount,
                "from": from_account,
                "to": to_account,
            },
        )
