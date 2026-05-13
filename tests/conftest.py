"""Shared fixtures."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from mcp_kraken.auth import TokenStore
from mcp_kraken.kraken import KrakenClient


@pytest.fixture
def token_db(tmp_path: Path) -> Path:
    return tmp_path / "tokens.db"


@pytest.fixture
def store(token_db: Path) -> TokenStore:
    return TokenStore(token_db)


@pytest.fixture
async def kraken_client() -> AsyncIterator[KrakenClient]:
    client = KrakenClient(
        api_key="testkey",
        api_secret="dGVzdHNlY3JldA==",  # base64("testsecret")
        base_url="https://api.kraken.test",
    )
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    return asyncio.DefaultEventLoopPolicy()
