# Project guidance — mcp-kraken

This file is the canonical project brief for Claude (and humans). It is
mirrored at [AGENTS.md](AGENTS.md) (a symlink, so non-Claude coding agents
that follow the `agents.md` convention find the same guidance). Read it
before making changes; keep it under 300 lines.

## What this project is

An MCP server that wraps the **Kraken Spot REST API** and exposes it over
HTTP with bearer-token authentication, plus a CLI for managing those bearer
tokens. Built on FastMCP. Single process, stateless beyond a SQLite token
store.

WebSocket v2 and FIX are explicitly **out of scope for v1** — they live in
[`TODO.md`](TODO.md).

> **Active reorientation.** The project is moving to a `python-kraken-sdk`
> backend with Spot + Futures REST coverage, a Futures demo mode, opt-in
> per-token quotas, and a GitFlow release process. The current scope is
> tracked in [`PLAN.md`](PLAN.md).

## Stack

- Python **3.12+** (CI matrix tests 3.12 and 3.13)
- Dependency manager: **uv** (`uv add`, `uv sync`, `uv run`)
- Build backend: **hatchling** + **hatch-vcs** — version is derived from the
  git tag (`vX.Y.Z` → `X.Y.Z`). Never hand-edit a version field.
- HTTP framework: **FastMCP** (streamable HTTP transport)
- HTTP client: **httpx** (async)
- Validation/config: **pydantic** + **pydantic-settings**
- CLI: **typer** + **rich**
- Tests: **pytest** + **pytest-asyncio** + **respx** (httpx mocks)
- Quality: **ruff** (lint + format), **mypy** (strict)
- Container: multi-stage **Dockerfile**, non-root uid 10001, distroless-style runtime

## Layout

```
src/mcp_kraken/
├── __init__.py __main__.py cli.py config.py logging.py server.py
├── auth/          # bearer-token store (SQLite), FastMCP TokenVerifier
├── kraken/        # async REST client, HMAC signing, errors, permission map
└── tools/         # MCP tool registrations, one module per Kraken category
tests/             # pytest; uses respx to mock httpx
docker/            # Dockerfile + compose.yml (build context is repo root)
.github/workflows/ # test.yml, develop-publish.yml, release.yml, pages.yml, codeql.yml
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

Use `uv add <pkg>` / `uv add --dev <pkg>` to add a dependency — never
hand-edit `pyproject.toml`.

**Versions belong to tools, not to the agent.** Wherever a version literal
appears, it must come from the tool that owns that ecosystem:

| Domain                                | Tool / mechanism |
| ------------------------------------- | ---------------- |
| `mcp-kraken` package version          | `hatch-vcs` derives it from git tags. Never write a version in `pyproject.toml`. |
| Python dependencies                   | `uv add <pkg>` — uv picks a compatible range. |
| GitHub Actions                        | Pin to a major (`@v7`); Dependabot bumps it. |
| Docker base images                    | Pin a major tag; refresh via Dependabot or an explicit `docker pull`. |
| pre-commit hooks                      | `pre-commit autoupdate`. |
| Python interpreter                    | `uv python install`; CI matrix picks 3.12 / 3.13 / etc. |

If the right version is unknowable without running the tool, run the tool —
never guess.

## Auth model — two boundaries

| Boundary                              | Mechanism                                  |
| ------------------------------------- | ------------------------------------------ |
| MCP client → mcp-kraken (you control) | Opaque bearer tokens, SHA-256 hashed in DB |
| mcp-kraken → Kraken                   | `KRAKEN_API_KEY` + HMAC-SHA512 signature   |

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
- The repository follows [GitFlow](docs/contributing/branching.md):
  `feature/*` → PR into `develop`; `release/*` and `hotfix/*` → PR into
  `main`; tag `vX.Y.Z` on the merge commit in `main` triggers the
  release workflow.
- Every push to `develop` triggers the `develop-publish` workflow →
  image `ghcr.io/xavierbeheydt/mcp-kraken:develop` (+ `:develop-<sha>`).
- Tagging a commit on `main` as `vX.Y.Z` triggers the `release` workflow:
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
- Tests aim for behaviour, not implementation: prefer respx-mocked Kraken
  responses to monkey-patching internals.

## Gotchas (read before changing tool signatures)

- **Tool parameters of type `list[T] | None = None` lose their JSON-schema
  `type: array` annotation** in the schema FastMCP exposes over MCP. Claude
  Code passes such values as JSON-encoded strings, which Pydantic strict
  mode then rejects. Use
  `Annotated[list[T], Field(default_factory=list)]` (with `# noqa: B008`)
  or a similar idiom that keeps Pydantic from collapsing the type.
- Kraken returns errors as a `200 OK` with a non-empty `error` array, not
  as HTTP errors. `KrakenClient._unwrap` classifies them — extend
  `errors.classify` when adding a new error category, not the call sites.
- Do **not** call `git push --force` against `main` without an explicit
  user instruction.
- The project is licensed under **AGPL-3.0-only** ([LICENSE](LICENSE)).
  New source files should carry an SPDX header
  (`# SPDX-License-Identifier: AGPL-3.0-only`). Network use triggers the
  Affero copyleft clause — a forked SaaS deployment must publish its
  source modifications.
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
