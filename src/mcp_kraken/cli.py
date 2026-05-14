"""Command-line entry point.

Subcommands:

    mcp-kraken serve                 — run the HTTP MCP server
    mcp-kraken token create NAME     — mint a new bearer token
    mcp-kraken token list            — list known tokens
    mcp-kraken token revoke ID       — revoke a token by id
    mcp-kraken version               — print the installed version
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .auth import TokenStore
from .config import load_settings
from .logging import configure_logging

app = typer.Typer(
    name="mcp-kraken",
    help="MCP server exposing the Kraken REST API with bearer-token auth.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
token_app = typer.Typer(name="token", help="Manage HTTP bearer tokens.")
app.add_typer(token_app, name="token")

console = Console()


def _parse_duration(expr: str) -> timedelta:
    """Parse `90d`, `12h`, `30m`, or a number of seconds."""
    expr = expr.strip().lower()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if expr and expr[-1] in units:
        return timedelta(seconds=int(expr[:-1]) * units[expr[-1]])
    return timedelta(seconds=int(expr))


# ---------------------------------------------------------------- serve


@app.command("serve")
def serve(
    host: Annotated[str | None, typer.Option(help="Bind address.")] = None,
    port: Annotated[int | None, typer.Option(help="TCP port.")] = None,
    path: Annotated[str | None, typer.Option(help="MCP HTTP path.")] = None,
    api: Annotated[
        str | None,
        typer.Option(
            "--api",
            help=(
                "Which Kraken product to expose: `spot` (default) or `futures`. "
                "A single server speaks one API at a time."
            ),
        ),
    ] = None,
    futures_sandbox: Annotated[
        bool,
        typer.Option(
            "--futures-sandbox",
            help="When --api=futures, talk to demo-futures.kraken.com instead of production.",
        ),
    ] = False,
    ssl_keyfile: Annotated[
        Path | None,
        typer.Option(
            "--ssl-keyfile",
            help="TLS private key (PEM). Pair with --ssl-certfile to serve HTTPS.",
        ),
    ] = None,
    ssl_certfile: Annotated[
        Path | None,
        typer.Option(
            "--ssl-certfile",
            help="TLS certificate (PEM). Pair with --ssl-keyfile to serve HTTPS.",
        ),
    ] = None,
    stdio: Annotated[
        bool,
        typer.Option(
            "--stdio",
            help=(
                "Use the stdio transport instead of HTTP. "
                "Use this for local Claude Desktop or `uvx mcp-kraken` setups."
            ),
        ),
    ] = False,
) -> None:
    """Start the MCP server (blocks until interrupted).

    Defaults to HTTP. Pass `--stdio` to speak over stdin/stdout instead, or
    provide both `--ssl-keyfile` and `--ssl-certfile` to serve HTTPS.
    """
    settings = load_settings()
    if host is not None:
        settings.host = host
    if port is not None:
        settings.port = port
    if path is not None:
        settings.path = path
    if api is not None:
        if api not in ("spot", "futures"):
            raise typer.BadParameter("--api must be 'spot' or 'futures'")
        settings.kraken_api = api  # type: ignore[assignment]
    if futures_sandbox:
        settings.kraken_futures_sandbox = True
    if ssl_keyfile is not None:
        settings.ssl_keyfile = ssl_keyfile
    if ssl_certfile is not None:
        settings.ssl_certfile = ssl_certfile
    configure_logging(settings.log_level)

    if (settings.ssl_keyfile is None) ^ (settings.ssl_certfile is None):
        raise typer.BadParameter("--ssl-keyfile and --ssl-certfile must be set together")

    # Import lazily so `mcp-kraken --help` does not pull in uvicorn etc.
    from .server import run_http, run_stdio

    if stdio:
        run_stdio(settings)
    else:
        run_http(settings)


# ---------------------------------------------------------------- token


@token_app.command("create")
def token_create(
    name: Annotated[str, typer.Argument(help="Human label for the token.")],
    expires_in: Annotated[
        str | None,
        typer.Option(
            "--expires-in",
            "-e",
            help="Validity duration: `90d`, `12h`, `30m`, or seconds. Omit for no expiry.",
        ),
    ] = None,
) -> None:
    """Mint a bearer token. The plaintext is printed ONCE; store it now."""
    settings = load_settings()
    store = TokenStore(settings.token_db)
    expires_at = None
    if expires_in:
        expires_at = datetime.now(UTC) + _parse_duration(expires_in)
    issued = store.create(name=name, expires_at=expires_at)

    console.print()
    console.print(
        "[bold green]Bearer token issued[/bold green] — copy it now, it will not be shown again."
    )
    console.print()
    console.print(f"  id      [bold]{issued.record.id}[/bold]")
    console.print(f"  name    {issued.record.name}")
    console.print(
        f"  expires {issued.record.expires_at.isoformat() if issued.record.expires_at else 'never'}"
    )
    console.print()
    console.print(f"  [bold cyan]{issued.plaintext}[/bold cyan]")
    console.print()
    console.print("Use it as: [italic]Authorization: Bearer <token>[/italic]")


@token_app.command("list")
def token_list(
    show_revoked: Annotated[bool, typer.Option("--all", help="Include revoked tokens.")] = False,
) -> None:
    """List known bearer tokens (hashes only)."""
    settings = load_settings()
    store = TokenStore(settings.token_db)
    records = store.list(include_revoked=show_revoked)
    if not records:
        console.print(
            "[yellow]No tokens yet.[/yellow] Mint one with `mcp-kraken token create NAME`."
        )
        return

    table = Table(title=f"Tokens ({settings.token_db})")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Created")
    table.add_column("Expires")
    table.add_column("Last used")

    for r in records:
        if r.is_revoked:
            status = "[red]revoked[/red]"
        elif r.is_expired:
            status = "[yellow]expired[/yellow]"
        else:
            status = "[green]active[/green]"
        table.add_row(
            r.id,
            r.name,
            status,
            r.created_at.isoformat(timespec="seconds"),
            r.expires_at.isoformat(timespec="seconds") if r.expires_at else "—",
            r.last_used_at.isoformat(timespec="seconds") if r.last_used_at else "—",
        )
    console.print(table)


@token_app.command("revoke")
def token_revoke(
    token_id: Annotated[str, typer.Argument(help="Token id (the short prefix shown by `list`).")],
) -> None:
    """Revoke a token by id. Already-revoked tokens are a no-op."""
    settings = load_settings()
    store = TokenStore(settings.token_db)
    record = store.get(token_id)
    if record is None:
        console.print(f"[red]Unknown token id:[/red] {token_id}")
        raise typer.Exit(code=1)
    if record.is_revoked:
        console.print(f"[yellow]Already revoked:[/yellow] {token_id}")
        return
    store.revoke(token_id)
    console.print(f"[green]Revoked[/green] {token_id} ({record.name})")


# ---------------------------------------------------------------- version


@app.command("version")
def version() -> None:
    """Print the installed mcp-kraken version."""
    console.print(__version__)


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
