# mcp-kraken

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![test](https://github.com/XavierBeheydt/mcp-kraken/actions/workflows/test.yml/badge.svg)](https://github.com/XavierBeheydt/mcp-kraken/actions/workflows/test.yml)
[![release](https://github.com/XavierBeheydt/mcp-kraken/actions/workflows/release.yml/badge.svg)](https://github.com/XavierBeheydt/mcp-kraken/actions/workflows/release.yml)
[![dev image](https://github.com/XavierBeheydt/mcp-kraken/actions/workflows/dev-publish.yml/badge.svg?branch=dev)](https://github.com/XavierBeheydt/mcp-kraken/actions/workflows/dev-publish.yml)
[![CodeQL](https://github.com/XavierBeheydt/mcp-kraken/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/XavierBeheydt/mcp-kraken/security/code-scanning)
[![GHCR](https://img.shields.io/github/v/tag/XavierBeheydt/mcp-kraken?label=ghcr.io&logo=docker&color=2496ED&sort=semver)](https://github.com/XavierBeheydt/mcp-kraken/pkgs/container/mcp-kraken)
[![PyPI](https://img.shields.io/pypi/v/mcp-kraken.svg?logo=pypi&logoColor=white)](https://pypi.org/project/mcp-kraken/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-kraken.svg?logo=python&logoColor=white)](https://pypi.org/project/mcp-kraken/)
[![Downloads](https://img.shields.io/pypi/dm/mcp-kraken.svg)](https://pypi.org/project/mcp-kraken/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

An MCP server that exposes the [Kraken](https://www.kraken.com/) cryptocurrency
exchange Spot REST API over HTTP, secured with bearer tokens you manage
locally.

- Full Kraken Spot REST surface, mapped to typed MCP tools.
- Proactive API-key permission detection — calls that the key cannot perform
  are rejected before they leave the box, with a clear error.
- Built-in token CLI: generate, list, and revoke bearer tokens used by HTTP
  clients to authenticate against the MCP itself.
- Single-process, stateless beyond the SQLite token store; ready for
  containerised deployment behind a reverse proxy.

WebSocket v2 and FIX transports are explicitly out of scope for the first
release — see [`TODO.md`](TODO.md).

## Architecture

```
┌────────────┐    HTTPS / bearer    ┌───────────────┐    HMAC-signed    ┌─────────┐
│ MCP client │ ───────────────────▶ │  mcp-kraken   │ ─────────────────▶│ Kraken  │
│ (Claude…)  │ ◀─────────────────── │  FastMCP HTTP │ ◀───────────────  │ REST v0 │
└────────────┘                      └───────────────┘                   └─────────┘
                                          │
                                          ▼
                                   SQLite (bearer-token hashes)
```

Two authentication boundaries:

| Boundary                              | Mechanism                         |
| ------------------------------------- | --------------------------------- |
| MCP client → mcp-kraken (you control) | Opaque bearer tokens (SHA-256)    |
| mcp-kraken → Kraken (you control)     | `KRAKEN_API_KEY` + HMAC signature |

## Requirements

- Python `>=3.12`
- [uv](https://docs.astral.sh/uv/) for dependency management
- [just](https://github.com/casey/just) for the dev command runner (optional)
- A Kraken Spot API key — generate one in
  [Account → Security → API](https://www.kraken.com/u/security/api). The
  permissions you enable on the key directly determine which MCP tools succeed
  (see [Permissions](#kraken-api-key-permissions) below).

## Quick start

```bash
# Clone and install
git clone https://github.com/XavierBeheydt/mcp-kraken.git
cd mcp-kraken
uv sync --dev

# Configure
cp .env.example .env
$EDITOR .env  # set KRAKEN_API_KEY and KRAKEN_API_SECRET

# Issue a bearer token for your MCP client
uv run mcp-kraken token create "claude-desktop" --expires-in 90d
# → copy the printed token; it will never be shown again

# Start the HTTP server (defaults to 0.0.0.0:8765/mcp)
uv run mcp-kraken serve
```

Point your MCP client at `http://localhost:8765/mcp/` with the header
`Authorization: Bearer mck_…`.

## CLI

```text
mcp-kraken serve              # run the HTTP server
mcp-kraken token create NAME  # mint a new bearer token (printed once)
mcp-kraken token list         # list known tokens (hashes only)
mcp-kraken token revoke ID    # revoke a token by id
mcp-kraken version            # print the installed version
```

`token create` accepts `--expires-in 90d` (or `12h`, `30m`, `3600` seconds).
Omit it for a token that never expires. The full plaintext is only shown once
at creation — the server only stores the SHA-256 hash plus the short id.

## Local testing with Claude Desktop

Claude Desktop accepts MCP servers either as a remote HTTPS connector or as a
local command (stdio). Pure self-signed certs are rejected — the cert has to
be signed by a CA the OS trusts.

### Option A — HTTPS via mkcert (Custom Connector)

[`mkcert`](https://github.com/FiloSottile/mkcert) creates a local CA, installs
it into the system trust store, and signs certs from it.

```bash
brew install mkcert            # or your package manager's equivalent
just cert-local                # mkcert -install + generates certs/{key,cert}.pem
just serve-https               # serves HTTPS on 0.0.0.0:8765/mcp
```

Then in Claude Desktop: **Settings → Connectors → Add custom connector**, with
URL `https://localhost:8765/mcp/` and the bearer token from
`mcp-kraken token create`.

### Option B — stdio (Command Connector)

For purely local use you can skip HTTPS entirely:

```bash
uv run mcp-kraken serve --stdio
```

Wire it into Claude Desktop's config file (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kraken": {
      "command": "uv",
      "args": ["--directory", "/abs/path/to/mcp-kraken", "run", "mcp-kraken", "serve", "--stdio"],
      "env": {
        "KRAKEN_API_KEY": "...",
        "KRAKEN_API_SECRET": "..."
      }
    }
  }
}
```

stdio sessions are inherently local — the bearer-token layer is bypassed.

## Configuration

Settings come from environment variables, optionally loaded from `.env`:

| Variable                   | Default              | Purpose                                                 |
| -------------------------- | -------------------- | ------------------------------------------------------- |
| `KRAKEN_API_KEY`           | —                    | Kraken API public key.                                  |
| `KRAKEN_API_SECRET`        | —                    | Kraken API private key (base64).                        |
| `KRAKEN_BASE_URL`          | `https://api.kraken.com` | Override for testing.                               |
| `MCP_KRAKEN_HOST`          | `0.0.0.0`            | Bind address.                                           |
| `MCP_KRAKEN_PORT`          | `8765`               | TCP port.                                               |
| `MCP_KRAKEN_PATH`          | `/mcp`               | HTTP path the MCP transport mounts on.                  |
| `MCP_KRAKEN_TOKEN_DB`      | `./data/tokens.db`   | SQLite file holding bearer-token metadata.              |
| `MCP_KRAKEN_SSL_KEYFILE`   | —                    | TLS private key (PEM). Pair with `_SSL_CERTFILE`.       |
| `MCP_KRAKEN_SSL_CERTFILE`  | —                    | TLS certificate (PEM). Pair with `_SSL_KEYFILE`.        |
| `MCP_KRAKEN_HTTP_TIMEOUT`  | `30`                 | Seconds before outbound Kraken calls time out.          |
| `MCP_KRAKEN_LOG_LEVEL`     | `INFO`               | Standard Python log level.                              |
| `MCP_KRAKEN_AUTH_DISABLED` | `false`              | **Dev only.** Skip bearer-token enforcement.            |

The full sample lives in [`.env.example`](.env.example).

## Tools

Public market-data tools (no Kraken credentials needed):

`get_server_time`, `get_system_status`, `get_assets`, `get_asset_pairs`,
`get_ticker`, `get_ohlc`, `get_order_book`, `get_recent_trades`,
`get_recent_spreads`.

Private tools (require `KRAKEN_API_KEY` + `KRAKEN_API_SECRET`):

- **Account**: `get_account_balance`, `get_extended_balance`,
  `get_trade_balance`, `get_trade_volume`, `get_ledgers`, `query_ledgers`,
  `get_credit_lines`, `get_api_key_info`, `request_export_report`,
  `get_export_status`, `retrieve_export`, `remove_export`.
- **Trading**: `get_open_orders`, `get_closed_orders`, `query_orders`,
  `get_trade_history`, `query_trades`, `get_open_positions`, `add_order`,
  `add_order_batch`, `amend_order`, `edit_order`, `cancel_order`,
  `cancel_all_orders`, `cancel_all_orders_after`, `cancel_order_batch`.
- **Funding**: `get_deposit_methods`, `get_deposit_addresses`,
  `get_deposit_status`, `get_withdrawal_methods`, `get_withdrawal_addresses`,
  `get_withdrawal_info`, `withdraw`, `get_withdrawal_status`,
  `cancel_withdrawal`, `wallet_transfer`.
- **Earn**: `list_earn_strategies`, `list_earn_allocations`, `allocate_earn`,
  `deallocate_earn`, `get_earn_allocation_status`,
  `get_earn_deallocation_status`.
- **Subaccounts**: `create_subaccount`, `account_transfer`.
- **WebSocket auth**: `get_websockets_token` (token for the future WS layer —
  see [`TODO.md`](TODO.md)).

## Kraken API key permissions

Kraken keys can be issued with any subset of:

| UI label                          | Capability flag         |
| --------------------------------- | ----------------------- |
| Query funds                       | `query_funds`           |
| Deposit                           | `deposit`               |
| Withdraw                          | `withdraw`              |
| Earn                              | `earn`                  |
| View open orders & trades         | `query_open_orders`     |
| View closed orders & trades       | `query_closed_orders`   |
| Create & modify orders            | `create_modify_orders`  |
| Cancel & close orders             | `cancel_orders`         |
| View ledger entries               | `query_ledger`          |
| Export data                       | `export_data`           |
| WebSocket interface               | `websocket`             |

On the first private call, `mcp-kraken` introspects the key via
`GetAPIKeyInfo` and caches the resulting permission set. Subsequent tool
invocations are checked against that cache; missing permissions raise
`KrakenPermissionError` with the list of flags the key would need. If the
introspection itself fails (older keys may not support `GetAPIKeyInfo`), the
server falls back to letting Kraken enforce permissions over the wire.

IP restrictions, expiry, query date ranges, and custom nonce windows are
configured on the key itself in the Kraken UI; the server passes through
whatever the key allows.

## Development

```bash
just sync          # uv sync --all-extras --dev
just test          # pytest
just check         # lint + format-check + mypy + tests
just fix           # auto-fix lint and format
just docker-build  # local image build
```

Run `just` with no arguments for the full recipe list.

## Docker

The published image is `ghcr.io/xavierbeheydt/mcp-kraken`:

| Tag                      | Pushed by             | Notes                          |
| ------------------------ | --------------------- | ------------------------------ |
| `latest`                 | release workflow      | Latest non-prerelease tag.     |
| `vX.Y.Z`, `vX.Y`, `vX`   | release workflow      | Semver tags on every release.  |
| `dev`                    | dev-publish workflow  | Tip of the `dev` branch.       |
| `dev-<sha7>`             | dev-publish workflow  | Per-commit tag on `dev`.       |

The reference deployment uses [`compose.yml`](compose.yml):

```bash
cp .env.example .env  # set KRAKEN_API_KEY / KRAKEN_API_SECRET
docker compose up -d
```

The container runs as a non-root user (`uid 10001`), with a read-only root
filesystem, no added capabilities, and a SQLite token-store volume at
`/data`. Put it behind a TLS-terminating reverse proxy in production — the
server speaks plain HTTP internally.

## Versioning & release flow

Versions are derived from git tags via
[hatch-vcs](https://github.com/ofek/hatch-vcs); there is no version number
to bump in `pyproject.toml`.

```
        feature → PR → dev   →  dev-publish workflow → ghcr.io/…:dev[-sha]
                                                      ↑
                                                test workflow

                  tag v1.2.3  →  release workflow    → ghcr.io/…:1.2.3, :latest
                                                      + GitHub Release
                                                      + fast-forward main to the tag
```

Branch conventions:

- `main` — protected; always equals the latest released commit.
- `dev` — default integration branch; every push runs tests and republishes
  the `:dev` image.
- topic branches → PR into `dev`.
- Releases are cut by tagging the desired `dev` commit `vX.Y.Z`. The release
  workflow tests it, builds and pushes the image with semver tags, opens a
  GitHub Release with auto-generated notes, and fast-forwards `main` to the
  tag. If `main` cannot be fast-forwarded (e.g. `main` has diverged) the
  workflow emits a warning and leaves the merge for a human.

To prerelease, tag `v1.2.3-rc1`: the workflow builds and pushes
`1.2.3-rc1`, `1.2-rc1`, `1-rc1`, marks the GitHub Release as prerelease, and
does not publish the `:latest` tag.
