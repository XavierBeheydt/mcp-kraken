"""FastMCP server factory.

Creates an HTTP-bound MCP server with bearer-token auth, holding a shared
`KrakenClient` for the lifetime of the process.
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import parse_qsl, urlencode

from fastmcp import FastMCP
from starlette.types import ASGIApp, Receive, Scope, Send

from . import __version__
from .auth import KrakenTokenVerifier, TokenStore
from .config import Settings
from .kraken import KrakenClient, KrakenFuturesClient
from .logging import get_logger
from .tools import register_all

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Access-log sanitiser
# ---------------------------------------------------------------------------

_REDACT_RE = re.compile(r"(apikey=)[^\s&\"']+")


class _ApiKeyLogFilter(logging.Filter):
    """Redact ``apikey=<token>`` from uvicorn access-log records.

    uvicorn logs the raw request line (including query string) at the
    protocol layer, before our ``_ApiKeyQueryMiddleware`` has had a chance
    to strip the bearer token.  This filter scrubs the value so the token
    never lands in stdout / log files.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            args = record.args if isinstance(record.args, tuple) else (record.args,)
            record.args = tuple(
                _REDACT_RE.sub(r"\1***", a) if isinstance(a, str) else a for a in args
            )
        if isinstance(record.msg, str):
            record.msg = _REDACT_RE.sub(r"\1***", record.msg)
        return True


_HEALTH_BODY = b'{"status":"ok"}'
_HEALTH_HEADERS = [
    (b"content-type", b"application/json"),
    (b"content-length", str(len(_HEALTH_BODY)).encode()),
]


class _ApiKeyQueryMiddleware:
    """Lift ``?apikey=...`` query param into a Bearer ``Authorization`` header.

    Some MCP clients — notably the current Claude Desktop remote-MCP
    config — cannot send custom HTTP headers. This middleware accepts
    the bearer as a URL query parameter (the convention used by Alpha
    Vantage and several other public MCP servers) and rewrites the
    request so it looks like it came in with ``Authorization: Bearer
    <token>``.

    The ``apikey`` parameter is stripped from the query string before
    the inner app sees it, so FastMCP and the token verifier never see
    the secret in the URL. Note: uvicorn's default access log runs
    *before* this middleware in the protocol layer, so the raw request
    line may still appear in stdout. Operators who care about that
    should configure uvicorn's access log format or place a reverse
    proxy in front that scrubs the param.

    If an ``Authorization`` header is already present, the query
    parameter is ignored (the header wins) and the URL is left
    unchanged.
    """

    __slots__ = ("_app",)

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        query: bytes = scope.get("query_string", b"") or b""
        if b"apikey" not in query:
            await self._app(scope, receive, send)
            return

        headers: list[tuple[bytes, bytes]] = list(scope.get("headers", []) or [])
        if any(name.lower() == b"authorization" for name, _ in headers):
            await self._app(scope, receive, send)
            return

        token, stripped_query = _extract_apikey(query)
        if token is None:
            await self._app(scope, receive, send)
            return

        new_scope = dict(scope)
        new_scope["query_string"] = stripped_query
        new_scope["headers"] = [
            *headers,
            (b"authorization", b"Bearer " + token.encode("latin-1", errors="replace")),
        ]
        await self._app(new_scope, receive, send)


def _extract_apikey(query: bytes) -> tuple[str | None, bytes]:
    """Pull the first ``apikey`` value out of a raw query string.

    Returns ``(token, stripped_query)``. When the parameter is absent
    or has an empty value, returns ``(None, original_query)`` so the
    caller can short-circuit without rebuilding the URL.
    """
    pairs = parse_qsl(query.decode("latin-1"), keep_blank_values=True)
    token: str | None = None
    remaining: list[tuple[str, str]] = []
    for key, value in pairs:
        if key == "apikey" and token is None and value:
            token = value
            continue
        remaining.append((key, value))
    if token is None:
        return None, query
    return token, urlencode(remaining).encode("latin-1")


class _HealthMiddleware:
    """Short-circuit ``GET /health`` before auth — no credentials required.

    Any HTTP request whose path is exactly ``/health`` receives a ``200 OK``
    with ``{"status":"ok"}`` and never reaches FastMCP's token verifier.
    All other requests are forwarded to the inner ASGI app unchanged.
    """

    __slots__ = ("_app",)

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] == "/health":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": _HEALTH_HEADERS,
                }
            )
            await send({"type": "http.response.body", "body": _HEALTH_BODY})
            return
        await self._app(scope, receive, send)


def _make_client(settings: Settings) -> KrakenClient | KrakenFuturesClient:
    key_secret, secret_secret = settings.active_credentials()
    key = key_secret.get_secret_value() if key_secret else None
    secret = secret_secret.get_secret_value() if secret_secret else None
    if settings.kraken_api == "futures":
        return KrakenFuturesClient(
            api_key=key,
            api_secret=secret,
            base_url=settings.kraken_futures_base_url,
            sandbox=settings.kraken_futures_sandbox,
            timeout=settings.http_timeout,
        )
    return KrakenClient(
        api_key=key,
        api_secret=secret,
        base_url=settings.kraken_base_url,
        timeout=settings.http_timeout,
        user_agent=f"mcp-kraken/{__version__}",
    )


def build_server(settings: Settings) -> tuple[FastMCP, KrakenClient | KrakenFuturesClient]:
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
        log.info("mcp-kraken %s starting (api=%s)", __version__, settings.kraken_api)
        try:
            yield
        finally:
            log.info("mcp-kraken shutting down")
            await client.aclose()

    api_label = "Spot" if settings.kraken_api == "spot" else "Futures"
    mcp = FastMCP(
        name=f"kraken-{settings.kraken_api}",
        instructions=(
            f"MCP server for the Kraken {api_label} REST API. "
            "Public market-data tools work without an API key. "
            "Private tools require KRAKEN_API_KEY and KRAKEN_API_SECRET to "
            "be configured server-side. Set MCP_KRAKEN_API=spot|futures "
            "(or --api on the CLI) to choose which product surface this "
            "instance exposes."
        ),
        auth=auth,
        lifespan=_lifespan,
    )
    register_all(mcp, client, api=settings.kraken_api)
    return mcp, client


def build_http_app(settings: Settings) -> ASGIApp:
    """Return an ASGI app for use with uvicorn / a reverse proxy.

    The returned app wraps the FastMCP Starlette application with two
    layers, applied outermost-first:

    * :class:`_HealthMiddleware` — answers ``GET /health`` with
      ``200 {"status":"ok"}`` before auth is checked.
    * :class:`_ApiKeyQueryMiddleware` — translates ``?apikey=<token>``
      into an ``Authorization: Bearer <token>`` header, so MCP clients
      that can't set custom headers (e.g. current Claude Desktop) can
      still authenticate by URL.
    """
    mcp, _client = build_server(settings)
    inner = _ApiKeyQueryMiddleware(mcp.http_app(path=settings.path))
    return _HealthMiddleware(inner)


def run_http(settings: Settings) -> None:
    """Blocking entry point: start uvicorn on settings.host:settings.port.

    Speaks HTTPS when both `ssl_keyfile` and `ssl_certfile` are set.
    """
    import uvicorn

    # Scrub ?apikey= from uvicorn access logs before the server starts.
    logging.getLogger("uvicorn.access").addFilter(_ApiKeyLogFilter())

    app = build_http_app(settings)
    use_tls = settings.ssl_keyfile is not None and settings.ssl_certfile is not None
    scheme = "https" if use_tls else "http"
    log.info(
        "serving on %s://%s:%d%s (auth=%s, api=%s)",
        scheme,
        settings.host,
        settings.port,
        settings.path,
        "off" if settings.auth_disabled else "on",
        settings.kraken_api,
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
