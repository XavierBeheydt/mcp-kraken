# mcp-kraken — Reorientation Plan (May 2026)

Active working plan for the upcoming refactor. Supersedes the original v0.1
focus on Spot-only / hand-rolled HTTP. Keep this file in sync with
[`TODO.md`](TODO.md) and the project brief in [`CLAUDE.md`](CLAUDE.md) /
[`AGENTS.md`](AGENTS.md).

## TL;DR

1. Switch the Kraken HTTP layer to **python-kraken-sdk** (Apache-2.0, async
   Spot + Futures REST clients). Our MCP / auth / quota stack sits on top.
2. Add **Kraken Futures REST** with a **demo mode**
   (`demo-futures.kraken.com`). Earn stays on Spot.
3. Kraken API keys come only from **env or docker secret** — never from
   the MCP request. Bearer token unchanged. OAuth deferred.
4. **Dry-run** (`validate=true`) on every Spot order endpoint, so unit
   tests and humans can rehearse orders without placing them. Futures has
   no equivalent — use the Futures demo env.
5. **Quota per token** as an opt-in feature; default = no limit.
6. CI / CD moves to a **GitFlow** layout (`develop`, `release/*`,
   `hotfix/*`) with path-filtered workflows, **GHCR + Docker Hub**
   registries, automated release notes, and **Postiz**-driven community
   announcements.
7. Docs migrate to **MkDocs Material** on GitHub Pages, single source of
   truth.

## Decisions in answer to the May 2026 requirements

### 1. MCP authentication

- Keep the existing bearer-token model (`Authorization: Bearer …` +
  `?apikey=` query alias).
- Keep the **stdio** transport (local-only, bypasses auth).
- OAuth 2.1 / DCR stays planned for v0.2.0 (see [`TODO.md`](TODO.md)) but
  is **out of scope for the current reorientation**.

### 2. Plugins for other LLMs

As of May 2026, MCP is natively consumed by Anthropic (Claude, Claude
Code), OpenAI (ChatGPT), Google (Gemini), Cursor, VS Code Copilot,
JetBrains Copilot, Ollama, and LM Studio. A single MCP server reaches them
all — no per-LLM plugin code is required for basic tool consumption.

What still belongs in the roadmap:

- A **Claude Code plugin bundle** (`.plugin`) that ships mcp-kraken plus
  a set of crypto / investment-flavoured skills (e.g. "rebalance to
  target allocation", "explain my recent ledger entries") that a generic
  MCP client would not preload.
- A "Connect" page in the docs with copy-paste setup snippets per
  client.
- Listings in MCP registries: smithery.ai, mcpmarket.com, glama.ai/mcp,
  punkpeye/awesome-mcp-servers.

### 3. Per-token quotas

A FastMCP middleware that decrements a per-token counter in the SQLite
store next to the bearer hashes ([`src/mcp_kraken/auth/store.py`](src/mcp_kraken/auth/store.py)).

- **Default = off.** A token created without `--rate` / `--daily` flags is
  unmetered.
- Opt-in at creation time: `mcp-kraken token create NAME --rate 60/min
  --daily 10000`.
- Sliding window 60 s and 24 h.
- Response headers `X-RateLimit-Remaining` and `Retry-After` on 429.
- Independent of Kraken's own outbound rate limits.

### 4. Kraken key storage — env-only with docker secrets

| Option                          | Decision         | Rationale |
| ------------------------------- | ---------------- | --------- |
| Env vars / `.env`               | keep             | Already works in stdio + docker compose. |
| `*_FILE` env (Docker secrets)   | add              | `KRAKEN_API_KEY_FILE=/run/secrets/kraken_api_key` reads the secret at startup. Standard for Docker Swarm / Kubernetes / Compose secrets. |
| Per-MCP-request header          | reject           | Conflates two trust boundaries. Bearer holder would see Kraken keys. |
| Per-token mapping in DB         | TODO (post-OAuth)| Multi-tenant scenario; comes with OAuth in v0.2.0. |

`docker/compose.yml` already passes env from the host; the `_FILE` variant
lands in PR-4 together with the quota work (both touch config loading).

### 5. Dry-run on order endpoints

- **Spot.** Kraken's `AddOrder`, `AmendOrder`, `EditOrder`,
  `AddOrderBatch` accept `validate=true`. Expose it as a `dry_run: bool
  = False` parameter on each MCP tool that maps to those endpoints.
  Default `False` keeps the surface honest — opting into a no-op trade is
  explicit. Unit tests exercise `dry_run=True` against respx-mocked
  responses to confirm the wiring.
- **Futures.** No `validate` parameter; the sandbox is the way.
  Documented as such, with a link to the demo env.
- **Cancel / Withdraw / Allocate-Earn.** No native dry-run; rely on the
  permission gate and on the demo env for rehearsal.

### 6. Demo / sandbox mode

| Surface       | Sandbox? | URL                                       |
| ------------- | -------- | ----------------------------------------- |
| Futures REST  | yes      | `https://demo-futures.kraken.com`         |
| Futures WS    | yes (TODO) | `wss://demo-futures.kraken.com/ws/v1`   |
| Spot REST     | no       | use `validate=true` dry-run               |
| Spot WS       | no       | n/a                                       |

Sandbox keys are minted at
`https://demo-futures.kraken.com/settings/api` after a *separate* signup
(no email verification, no real funds). They are **independent** from the
user's production Spot / Futures keys.

Config:

- `KRAKEN_FUTURES_MODE=live|demo` (default `live`).
- `KRAKEN_FUTURES_API_KEY` / `KRAKEN_FUTURES_API_SECRET` (separate from
  the Spot key — they don't share an HMAC scheme either).
- Docs include a "Get demo credentials" page that walks through the
  signup, key creation, and rotation.

### 7. REST-only — confirmed

Spot REST + Futures REST in scope. WebSocket v2 and FIX remain in
[`TODO.md`](TODO.md).

### 8. Workflows — GitFlow + path filters + Docker Hub + announce

Branch model (per [nvie.com GitFlow](https://nvie.com/posts/a-successful-git-branching-model/)):

| Branch     | Purpose                       | Protection |
| ---------- | ----------------------------- | ---------- |
| `main`     | latest released commit        | strong: PR + status checks + linear history + no force push + 1 review |
| `develop`  | integration branch            | PR + status checks + no force push |
| `feature/*`| topic branches off `develop`  | none |
| `release/*`| stabilisation, hotfix bundling| ruleset: PR-to-main, status checks |
| `hotfix/*` | emergency from `main`         | ruleset: PR-to-main + back-merge to `develop` |

Workflows after PR-8:

| File                    | Trigger                          | Path filter | What it does |
| ----------------------- | -------------------------------- | ----------- | ------------ |
| `test.yml`              | push develop, PR → develop/main  | code        | ruff + format + mypy + pytest (3.12, 3.13) |
| `codeql.yml`            | unchanged                        | —           | scan python + actions |
| `docs.yml`              | push develop/main, PR            | docs        | `mkdocs build --strict` |
| `develop-publish.yml`   | push develop                     | code        | image `:develop` + `:develop-<sha>` to GHCR + Docker Hub |
| `release-candidate.yml` | tag `vX.Y.Z-rcN`                 | —           | image `:X.Y.Z-rcN`, wheel → TestPyPI, GH Release prerelease |
| `release.yml`           | tag `vX.Y.Z` final               | —           | image semver tags, wheel → PyPI, GH Release, fast-forward main, kick `pages.yml`, post via Postiz |
| `pages.yml`             | push main `docs/**` or release   | docs        | `mkdocs gh-deploy` |

Code path filter (default): `src/**`, `tests/**`, `pyproject.toml`,
`uv.lock`, `Justfile`, `docker/**`, `.github/workflows/*.yml`.

Docs path filter: `docs/**`, `mkdocs.yml`.

Docker Hub: secrets `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN`, repo
`docker.io/xavierbeheydt/mcp-kraken` created upfront.

Release notes: keep `generate_release_notes: true` and add
`.github/release.yml` to group entries by labels (feat / fix / docs /
security / chore). Optional upgrade later: `release-please` for changelog
+ auto-PR release flow.

Release announcements: Postiz running on Xavier's host, called via its
API from `release.yml`. Targets: Mastodon, X, Bluesky, Reddit, Discord,
LinkedIn, Threads. Community list maintained in
`docs/contributing/release.md`.

GitHub permissions: every job declares the minimum required scopes
(already the norm; audit during PR-8).

### 9. Docs — MkDocs Material

Single source documentation. The current static landing
([`docs/index.html`](docs/index.html), [`docs/styles.css`](docs/styles.css))
is rebuilt as a Material hero block + features in `docs/index.md`. No
two-system setup.

Top-level structure:

```
mkdocs.yml
docs/
├── index.md
├── getting-started/
│   ├── install.md
│   ├── claude-desktop.md
│   ├── chatgpt.md          # ChatGPT / Gemini / Cursor / VS Code / Claude Code
│   └── docker.md
├── configuration.md
├── auth/
│   ├── bearer-tokens.md
│   └── oauth.md            # v0.2.0 placeholder
├── tools/                  # generated by mkdocstrings from docstrings
│   ├── spot.md
│   ├── futures.md
│   └── earn.md
├── demo-mode.md
├── architecture.md
├── contributing/
│   ├── branching.md        # GitFlow + branch protection setup
│   └── release.md          # how to cut a release
└── roadmap.md
```

Plugins: `mkdocs-material`, `mkdocstrings[python]`, `mkdocs-redirects`,
`mkdocs-minify-plugin`.

## Code architecture target

```
src/mcp_kraken/
├── __init__.py __main__.py cli.py config.py logging.py server.py
├── auth/                # bearer store, verifier, quota middleware
├── exchange/            # ex-kraken/
│   ├── spot/            # python-kraken-sdk SpotAsyncClient wrapper + perms
│   ├── futures/         # FuturesAsyncClient wrapper + demo toggle + perms
│   └── errors.py        # shared classifier
└── tools/
    ├── spot/            # market_data.py, account.py, trading.py, funding.py, earn.py, subaccounts.py, websocket_auth.py
    └── futures/         # market_data.py, account.py, trading.py
tests/
├── auth/
├── exchange/
│   ├── spot/
│   └── futures/
└── tools/
    ├── spot/
    └── futures/
```

Tests mirror `src/` so each module has a dedicated test directory.
`kraken/signing.py` and `kraken/client.py` disappear (the SDK signs).
`kraken/permissions.py` is kept and moves under `exchange/`.

## Implementation order

| PR    | Scope |
| ----- | ----- |
| PR-1  | This plan + AGENTS.md rename + versioning rule + `compose.yml` moved to `docker/` + **AGPL-3.0** license adoption. No runtime source changes. |
| PR-2  | Branch rename `dev` → `develop`; GitHub Rulesets; workflow refs; README badges; license decision applied. |
| PR-3  | Migrate Spot to `python-kraken-sdk`; rename `kraken/` → `exchange/spot/`; tests mirror `src/`. |
| PR-4  | Quota middleware (opt-in); Docker secret (`*_FILE`) env support. |
| PR-5  | `dry_run` parameter on Spot order tools + tests. |
| PR-6  | Kraken Futures REST: `exchange/futures/`, `tools/futures/`, permissions. |
| PR-7  | Futures demo-mode toggle + docs page. |
| PR-8  | GitFlow workflows: path filters, Docker Hub registry, RC vs release, Postiz announcer, `.github/release.yml`. |
| PR-9  | MkDocs Material site; landing reborn in `index.md`; old `docs/index.html` removed. |
| PR-10 | Claude Code plugin bundle (`.plugin`) shipping mcp-kraken + investment skills. |

Each PR opens against `develop` (until PR-2 lands, it's `dev`), reviewed,
merged, then released via GitFlow.

## Open questions

- **Postiz host** — confirm public URL and API token plumbing before
  PR-8.
- **Earn / Subaccounts / Export coverage in python-kraken-sdk** — verify
  via the [SDK docs](https://python-kraken-sdk.readthedocs.io/en/stable)
  during PR-3; if any endpoint is missing, keep an in-house wrapper for
  that subset and contribute upstream later.
- **respx vs SDK transport** — the SDK might call `httpx` directly,
  `requests`, or its own wrapper. Adapt the test mocking strategy in
  PR-3.
- **`AGENTS.md` canonicalisation** — today `AGENTS.md` is a symlink to
  [`CLAUDE.md`](CLAUDE.md). If the `agents.md` ecosystem matures, flip
  the canonical/symlink relationship later.

## Sources

- [python-kraken-sdk](https://github.com/btschwertfeger/python-kraken-sdk) — Apache-2.0, async Spot + Futures
- [Kraken Futures demo env](https://support.kraken.com/articles/360024809011-api-testing-environment-derivatives)
- [Kraken API global intro](https://docs.kraken.com/api/docs/guides/global-intro)
- [FastMCP OAuth](https://gofastmcp.com/clients/auth/oauth)
- [State of MCP clients — May 2026](https://www.mcpbundles.com/blog/state-of-mcp-clients)
- [nvie.com GitFlow](https://nvie.com/posts/a-successful-git-branching-model/)
- [agents.md convention](https://agents.md)
