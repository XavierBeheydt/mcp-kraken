# Project guidance — mcp-kraken

This file is the canonical project brief for Claude (and humans). Read it
before making changes; keep it under 300 lines.

## What this project is

An MCP server that wraps the **Kraken REST API** (Spot or Futures, chosen
at launch via `--api {spot|futures}` / `MCP_KRAKEN_API`) and exposes it
over HTTP with bearer-token authentication, plus a CLI for managing those
bearer tokens. Built on FastMCP. Single process, stateless beyond a
SQLite token store. A single instance speaks **one API at a time** — run
two servers if you need both surfaces.

WebSocket v2 and FIX are explicitly **out of scope for v1** — they live in
[`TODO.md`](TODO.md).

## Stack

- Python **3.12+** (CI matrix tests 3.12 and 3.13)
- Dependency manager: **uv** (`uv add`, `uv sync`, `uv run`)
- Build backend: **hatchling** + **hatch-vcs** — version is derived from the
  git tag (`vX.Y.Z` → `X.Y.Z`). Never hand-edit a version field.
- HTTP framework: **FastMCP** (streamable HTTP transport)
- Kraken REST client: **[python-kraken-sdk](https://github.com/btschwertfeger/python-kraken-sdk)**
  — `kraken.spot.SpotAsyncClient` for Spot, `kraken.futures.FuturesAsyncClient`
  for Futures. Both own transport (aiohttp), request signing, nonce handling,
  and primary error classification.
- Validation/config: **pydantic** + **pydantic-settings**
- CLI: **typer** + **rich**
- Tests: **pytest** + **pytest-asyncio** (mock the SDK's `request()` method
  with `unittest.mock.AsyncMock`)
- Quality: **ruff** (lint + format), **mypy** (strict)
- Container: multi-stage **Dockerfile**, non-root uid 10001, distroless-style runtime

## Layout

```
src/mcp_kraken/
├── __init__.py __main__.py cli.py config.py logging.py server.py
├── auth/          # bearer-token store (SQLite), FastMCP TokenVerifier
├── kraken/        # SDK wrappers — client.py (Spot), futures.py (Futures),
│                  #   errors.py, permissions.py (Spot only)
└── tools/         # MCP tool registrations
    ├── spot/      #   Spot tools (account, trading, funding, earn, …)
    └── futures/   #   Futures tools (market_data, account, trading)
tests/             # pytest; mock SDK request() via AsyncMock
docker/            # Dockerfile (build context is repo root)
.github/workflows/ # test.yml, dev-publish.yml, release.yml
```

Source files live at `src/mcp_kraken/` (src layout). Docker files in `docker/`.

## Common commands

```bash
just sync          # uv sync --all-extras --dev
just check         # ruff + format-check + mypy + pytest (= what CI runs)
just test          # pytest
just fix           # auto-fix lint + reformat
just serve         # plain HTTP on :8765/mcp
just serve-https   # HTTPS using ./certs/{key,cert}.pem
just serve-stdio   # stdio transport (for local Claude Desktop / uvx)
just cert-local    # mkcert: generates locally-trusted TLS certs
just docker-build  # local image build (tagged :dev)
```

Use `uv add <pkg>` / `uv add --dev <pkg>` — never edit `pyproject.toml`
dependencies by hand. Never invent versions: let uv pick.

## Auth model — two boundaries

| Boundary                              | Mechanism                                  |
| ------------------------------------- | ------------------------------------------ |
| MCP client → mcp-kraken (you control) | Opaque bearer tokens, SHA-256 hashed in DB |
| mcp-kraken → Kraken Spot              | `KRAKEN_API_KEY` + HMAC-SHA512 signature   |
| mcp-kraken → Kraken Futures           | `KRAKEN_FUTURES_API_KEY` + Authent header  |

Spot and Futures keys are issued separately and **not interchangeable** —
each instance reads only the pair that matches its active `kraken_api`.

Bearer tokens are minted by `mcp-kraken token create NAME [--expires-in 90d]`,
printed once, then only the hash is kept. `token list` shows ids only.
`token revoke ID` flags one as revoked.

The stdio transport bypasses the bearer layer entirely (sessions are local
by construction).

## Kraken API key permissions

On the first private call the client probes `/private/GetAPIKeyInfo`,
parses the returned permission tree, and caches it. Subsequent tools check
their required permission against that cache and reject early with
`KrakenPermissionError` if missing. The mapping endpoint → permission lives
in `kraken/permissions.py::PERMISSION_REQUIREMENTS`.

**Note**: in some regions/accounts `GetAPIKeyInfo` returns `EGeneral:Unknown
method`. The client catches this, logs a warning, and falls back to letting
Kraken itself enforce permissions over the wire. That fallback is in
`KrakenClient.get_permissions`.

## Versioning & release flow

- No version number lives in source. `pyproject.toml` declares
  `dynamic = ["version"]`; the build hook reads it from git tags.
- Topic branches → PR into `dev`.
- Every push to `dev` triggers the `dev-publish` workflow → image
  `ghcr.io/xavierbeheydt/mcp-kraken:dev` (+ `:dev-<sha>`).
- Tagging a commit on `dev` as `vX.Y.Z` triggers the `release` workflow:
  runs the test workflow, builds + pushes semver-tagged images
  (`:X.Y.Z`, `:X.Y`, `:X`, plus `:latest` for non-prereleases), publishes a
  GitHub Release with auto-generated notes, and fast-forwards `main` to the
  tag.
- Tagging `vX.Y.Z` also publishes the package to **PyPI** via OIDC
  trusted publishing (no token stored). Prerelease tags `vX.Y.Z-rcN` go to
  TestPyPI instead. Setup lives on PyPI's "publishing" page and in the
  GitHub `pypi` / `testpypi` environments.

## Style conventions

- All code, comments, docstrings, log messages, error strings in **English**.
- Type annotations everywhere; mypy runs in strict mode.
- Line length 100. ruff handles both lint and format (no black, no isort).
- Tests aim for behaviour, not implementation: mock
  `SpotAsyncClient.request` via `unittest.mock.AsyncMock` at the wrapper
  boundary (see `tests/test_kraken_client.py::_patch_sdk`).

## Gotchas (read before changing tool signatures)

- **Tool parameters of type `list[T] | None = None` lose their JSON-schema
  `type: array` annotation** in the schema FastMCP exposes over MCP. Claude
  Code passes such values as JSON-encoded strings, which Pydantic strict
  mode then rejects. Use
  `Annotated[list[T], Field(default_factory=list)]` (with `# noqa: B008`)
  or a similar idiom that keeps Pydantic from collapsing the type.
- Kraken returns errors as a `200 OK` with a non-empty `error` array. The
  SDK turns most known codes into typed `kraken.exceptions.*` exceptions;
  `KrakenClient._translate` then maps those onto our local hierarchy
  (`KrakenAuthError`, `KrakenPermissionError`, `KrakenRateLimitError`,
  `KrakenAPIError`). Unknown codes fall through to `KrakenAPIError`. Extend
  `_translate` when adding a new mapping, not the call sites.
- Batch endpoints (`AddOrderBatch`, `CancelOrderBatch`) require a JSON
  body, not form-encoded. The wrapper sets `do_json=True` on the SDK call
  for any endpoint listed in `_JSON_BODY_ENDPOINTS` in `kraken/client.py`.
  Add new batch-style endpoints there.
- Do **not** call `git push --force` against `main` without an explicit
  user instruction.
- Never write a `LICENSE` file or mention licensing in the code or docs
  unless the user explicitly asks; the license decision is pending.
- Tools that move funds/orders (`add_order`, `cancel_order`, `withdraw`,
  `wallet_transfer`, `allocate_earn`, etc.) are dangerous. In tests and
  documentation never invoke them with real credentials without an opt-in.

## Pre-commit checklist

```bash
just check    # everything CI checks
uv build      # confirm a wheel can be produced
```

Both must be green before pushing.

## Where to look first

- Adding a new Kraken endpoint as a tool → `tools/<category>.py` + add the
  endpoint name to `PERMISSION_REQUIREMENTS` in `kraken/permissions.py`.
- Changing transport behaviour → `server.py`.
- Changing token lifecycle → `auth/store.py` + `auth/verifier.py`.
- Changing CI → `.github/workflows/`.
- Anything cross-cutting → discuss in an issue first.
