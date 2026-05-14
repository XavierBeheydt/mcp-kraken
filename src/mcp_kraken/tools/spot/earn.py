"""Earn (staking / yield) tools."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ...kraken import KrakenClient
from .._common import drop_none


def register(mcp: FastMCP, client: KrakenClient) -> None:
    @mcp.tool(tags={"private", "earn"})
    async def list_earn_strategies(
        asset: str | None = None,
        lock_type: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
        ascending: bool | None = None,
    ) -> Any:
        """Browse available earn strategies."""
        return await client.private(
            "Earn/Strategies",
            drop_none(
                {
                    "asset": asset,
                    "lock_type": lock_type,
                    "cursor": cursor,
                    "limit": limit,
                    "ascending": ascending,
                }
            ),
        )

    @mcp.tool(tags={"private", "earn"})
    async def list_earn_allocations(
        ascending: bool | None = None,
        hide_zero_allocations: bool | None = None,
        converted_asset: str | None = None,
    ) -> Any:
        """List current allocations across earn strategies."""
        return await client.private(
            "Earn/Allocations",
            drop_none(
                {
                    "ascending": ascending,
                    "hide_zero_allocations": hide_zero_allocations,
                    "converted_asset": converted_asset,
                }
            ),
        )

    @mcp.tool(tags={"private", "earn", "write"})
    async def allocate_earn(strategy_id: str, amount: str) -> Any:
        """Allocate `amount` of the strategy's asset into `strategy_id`."""
        return await client.private("Earn/Allocate", {"strategy_id": strategy_id, "amount": amount})

    @mcp.tool(tags={"private", "earn", "write"})
    async def deallocate_earn(strategy_id: str, amount: str) -> Any:
        """Withdraw `amount` from `strategy_id`."""
        return await client.private(
            "Earn/Deallocate", {"strategy_id": strategy_id, "amount": amount}
        )

    @mcp.tool(tags={"private", "earn"})
    async def get_earn_allocation_status(strategy_id: str) -> Any:
        """Track the progress of a pending allocation."""
        return await client.private("Earn/AllocateStatus", {"strategy_id": strategy_id})

    @mcp.tool(tags={"private", "earn"})
    async def get_earn_deallocation_status(strategy_id: str) -> Any:
        """Track the progress of a pending deallocation."""
        return await client.private("Earn/DeallocateStatus", {"strategy_id": strategy_id})
