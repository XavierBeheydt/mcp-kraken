"""Funding tools: deposit/withdrawal addresses, status, transfers."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..kraken import KrakenClient
from ._common import drop_none


def register(mcp: FastMCP, client: KrakenClient) -> None:
    # ---------------------------------------------------------- deposits

    @mcp.tool(tags={"private", "funding", "deposit"})
    async def get_deposit_methods(asset: str, aclass: str | None = None) -> Any:
        """List available deposit methods for an asset."""
        return await client.private("DepositMethods", drop_none({"asset": asset, "aclass": aclass}))

    @mcp.tool(tags={"private", "funding", "deposit"})
    async def get_deposit_addresses(
        asset: str,
        method: str,
        new: bool | None = None,
        amount: str | None = None,
    ) -> Any:
        """Return deposit addresses for `asset` via `method`.

        Args:
            asset: Asset code (e.g. `XBT`).
            method: Deposit method as returned by `get_deposit_methods`.
            new: Generate a new address if True.
            amount: Optional amount, for methods that bind addresses to amounts.
        """
        return await client.private(
            "DepositAddresses",
            drop_none({"asset": asset, "method": method, "new": new, "amount": amount}),
        )

    @mcp.tool(tags={"private", "funding", "deposit"})
    async def get_deposit_status(
        asset: str | None = None,
        method: str | None = None,
        start: int | None = None,
        end: int | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> Any:
        """Return status of recent deposits."""
        return await client.private(
            "DepositStatus",
            drop_none(
                {
                    "asset": asset,
                    "method": method,
                    "start": start,
                    "end": end,
                    "cursor": cursor,
                    "limit": limit,
                }
            ),
        )

    # ---------------------------------------------------------- withdrawals

    @mcp.tool(tags={"private", "funding", "withdraw"})
    async def get_withdrawal_methods(
        asset: str | None = None,
        aclass: str | None = None,
        network: str | None = None,
    ) -> Any:
        """List available withdrawal methods."""
        return await client.private(
            "WithdrawalMethods",
            drop_none({"asset": asset, "aclass": aclass, "network": network}),
        )

    @mcp.tool(tags={"private", "funding", "withdraw"})
    async def get_withdrawal_addresses(
        asset: str | None = None,
        aclass: str | None = None,
        method: str | None = None,
        key: str | None = None,
        verified: bool | None = None,
    ) -> Any:
        """List whitelisted withdrawal addresses."""
        return await client.private(
            "WithdrawalAddresses",
            drop_none(
                {
                    "asset": asset,
                    "aclass": aclass,
                    "method": method,
                    "key": key,
                    "verified": verified,
                }
            ),
        )

    @mcp.tool(tags={"private", "funding", "withdraw"})
    async def get_withdrawal_info(asset: str, key: str, amount: str) -> Any:
        """Preview withdrawal cost (fee, limits).

        Args:
            asset: Asset code.
            key: Withdrawal-address nickname as registered on Kraken.
            amount: Amount of `asset` to withdraw.
        """
        return await client.private(
            "WithdrawalInfo", {"asset": asset, "key": key, "amount": amount}
        )

    @mcp.tool(tags={"private", "funding", "withdraw", "write"})
    async def withdraw(
        asset: str,
        key: str,
        amount: str,
        address: str | None = None,
        max_fee: str | None = None,
    ) -> Any:
        """Submit a withdrawal.

        Args:
            asset: Asset code.
            key: Whitelisted address nickname.
            amount: Amount.
            address: Optional address override (only for methods that allow it).
            max_fee: Maximum acceptable fee.
        """
        return await client.private(
            "Withdraw",
            drop_none(
                {
                    "asset": asset,
                    "key": key,
                    "amount": amount,
                    "address": address,
                    "max_fee": max_fee,
                }
            ),
        )

    @mcp.tool(tags={"private", "funding", "withdraw"})
    async def get_withdrawal_status(
        asset: str | None = None,
        aclass: str | None = None,
        method: str | None = None,
        start: int | None = None,
        end: int | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> Any:
        """Return status of recent withdrawals."""
        return await client.private(
            "WithdrawalStatus",
            drop_none(
                {
                    "asset": asset,
                    "aclass": aclass,
                    "method": method,
                    "start": start,
                    "end": end,
                    "cursor": cursor,
                    "limit": limit,
                }
            ),
        )

    @mcp.tool(tags={"private", "funding", "withdraw", "write"})
    async def cancel_withdrawal(asset: str, refid: str) -> Any:
        """Request cancellation of a pending withdrawal."""
        return await client.private("CancelWithdrawal", {"asset": asset, "refid": refid})

    @mcp.tool(tags={"private", "funding", "withdraw", "write"})
    async def wallet_transfer(asset: str, from_wallet: str, to_wallet: str, amount: str) -> Any:
        """Transfer between Kraken wallet types (e.g. Spot ↔ Futures).

        Args:
            asset: Asset code.
            from_wallet: Source wallet (`Spot Wallet`, `Futures Wallet`, ...).
            to_wallet: Destination wallet.
            amount: Amount.
        """
        return await client.private(
            "WalletTransfer",
            {
                "asset": asset,
                "from": from_wallet,
                "to": to_wallet,
                "amount": amount,
            },
        )
