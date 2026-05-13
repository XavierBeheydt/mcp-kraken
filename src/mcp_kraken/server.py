"""FastMCP server factory.

Creates an HTTP-bound MCP server with bearer-token auth, holding a shared
`KrakenClient` for the lifetime of the process.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastmcp import FastMCP

from . import __version__
from .auth import KrakenTokenVerifier, TokenStore
from .config import Settings
from .kraken import KrakenClient
from .logging import get_logger
from .tools import register_all

if TYPE_CHECKING:
    from starlette.applications import Starlette


log = get_logger(__name__)


def _make_client(settings: Settings) -> KrakenClient:
    return KrakenClient(
        api_key=(settings.kraken_api_key.get_secret_value() if settings.kraken_api_key else None),
        api_secret=(
            settings.kraken_api_secret.get_secret_value() if settings.kraken_api_secret else None
        ),
        base_url=settings.kraken_base_url,
        timeout=settings.http_timeout,
        user_agent=f"mcp-kraken/{__version__}",
    )


def build_server(settings: Settings) -> tuple[FastMCP, KrakenClient]:
    """Wire up a FastMCP instance with auth + Kraken-backed tools.

    Returns the server and the underlying Kraken client (so callers can
    close it on shutdown).
    """
    client = _make_client(settings)

    auth = None
    if not settings.auth_disabled:
        store = TokenStore(settings.token_db)
        auth = KrakenTokenVerifier(store)
        log.info("bearer-token auth enabled (db=%s)", settings.token_db)
    else:
        log.warning(
            "AUTHENTICATION DISABLED — set MCP_KRAKEN_AUTH_DISABLED=false in any "
            "non-development environment"
        )

    @asynccontextmanager
    async def _lifespan(_mcp: FastMCP) -> AsyncIterator[None]:
        log.info("mcp-kraken %s starting", __version__)
        try:
            yield
        finally:
            log.info("mcp-kraken shutting down")
            await client.aclose()

    mcp = FastMCP(
        name="kraken",
        instructions=(
            "MCP server for the Kraken cryptocurrency exchange. "
            "Public market-data tools work without an API key. "
            "Private tools (account, trading, funding, earn) require "
            "KRAKEN_API_KEY and KRAKEN_API_SECRET to be configured server-side."
        ),
        auth=auth,
        lifespan=_lifespan,
    )
    register_all(mcp, client)
    return mcp, client


def build_http_app(settings: Settings) -> Starlette:
    """Return an ASGI app for use with uvicorn / a reverse proxy."""
    mcp, _client = build_server(settings)
    return mcp.http_app(path=settings.path)


def run_http(settings: Settings) -> None:
    """Blocking entry point: start uvicorn on settings.host:settings.port.

    Speaks HTTPS when both `ssl_keyfile` and `ssl_certfile` are set.
    """
    import uvicorn

    app = build_http_app(settings)
    use_tls = settings.ssl_keyfile is not None and settings.ssl_certfile is not None
    scheme = "https" if use_tls else "http"
    log.info(
        "serving on %s://%s:%d%s (auth=%s)",
        scheme,
        settings.host,
        settings.port,
        settings.path,
        "off" if settings.auth_disabled else "on",
    )
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        ssl_keyfile=str(settings.ssl_keyfile) if settings.ssl_keyfile else None,
        ssl_certfile=str(settings.ssl_certfile) if settings.ssl_certfile else None,
    )


def run_stdio(settings: Settings) -> None:
    """Run the MCP server on stdio — for local Claude Desktop / `uvx` use.

    The bearer-token layer is irrelevant here: stdio sessions are inherently
    local and trusted. Kraken credentials still come from settings.
    """
    mcp, _client = build_server(settings)
    mcp.run(transport="stdio")
