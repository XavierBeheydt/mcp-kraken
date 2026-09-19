# CLAUDE.md - AGENTS.md

Short project brief for coding agents and humans. It stays short on purpose:
anything detailed lives in the [README](README.md) or under [`docs/`](docs/),
and this file points there. `AGENTS.md` is a symlink to this file (see
[agents.md](https://agents.md/)).

## What this project is

An MCP server wrapping the **Kraken REST API**, exposed over HTTP with
bearer-token authentication, plus a CLI to manage those tokens. Built on
FastMCP; single process, stateless beyond a SQLite token store. Python 3.12+,
managed with **uv**.

> **Active reorientation** toward a `python-kraken-sdk` backend, Spot +
> Futures REST, a Futures demo mode, opt-in per-token quotas and a GitFlow
> release process — the current scope is [`PLAN.md`](PLAN.md), the longer
> horizon [`TODO.md`](TODO.md). WebSocket v2 and FIX stay out of scope.

## Language

All repo content — code, comments, docstrings, log and error messages,
commits, docs — in English, always. In an interactive session, reply to the
user in whatever language they use: that rule is about repo content, not
conversation.

## Layout

- `src/mcp_kraken/` — the package (src layout); `tests/` mirrors it
- `docker/` — Dockerfile + compose.yml, build context is the repo root
- `docs/` — GitHub Pages site and contributor docs, versioned with the code
- `.claude/` — agent working dir; only `commands/`, `skills/`, `agents/` and
  `settings.json` are tracked, the rest is local. `.agents` is a tracked
  symlink to it, same idea as `AGENTS.md` → `CLAUDE.md`
- `.tmp/` — untracked scratch space

Module map, auth boundaries and the non-obvious traps:
[`docs/architecture.md`](docs/architecture.md).

## Commands

```bash
just sync     # uv sync --all-extras --dev
just check    # ruff + format-check + mypy + pytest (= what CI runs)
just fix      # auto-fix lint + reformat
just serve    # plain HTTP on :8765/mcp
```

`just` with no argument lists every recipe. Dependencies go in with
`uv add <pkg>` / `uv add --dev <pkg>` — never hand-edit `pyproject.toml`, and
never invent a version number
([why](docs/contributing/conventions.md#versions-belong-to-tools-not-to-people)).

## Branches & commits

- `main` is protected: released commits only, reached through a reviewed PR,
  never pushed to directly and never force-pushed.
- `develop` is the integration branch; work happens on `feat/<slug>`,
  `fix/<slug>`, `docs/<slug>`… branched off it.
- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):
  `type(scope): description`, `!` or a `BREAKING CHANGE:` footer for breaking
  changes. The branch prefix is the type it carries.

Full rules — types, scopes, comment tags, code style:
[`docs/contributing/conventions.md`](docs/contributing/conventions.md).
Branch model and protection rulesets:
[`docs/contributing/branching.md`](docs/contributing/branching.md).

## Versioning & releases

No version lives in the source: `hatch-vcs` derives it from the git tag, so
**the tag is the version**. Semantic versioning, `va.b.c`:

- `a` — breaking change (incompatible tool signature, config key, CLI, token
  store)
- `b` — new backwards-compatible feature
- `c` — bug fix, security fix, dependency or docs update

Every merge into `main` is a release: merge the `release/*` or `hotfix/*` PR,
tag the merge commit `vX.Y.Z`, push the tag — that publishes the images, the
PyPI wheel and the GitHub Release. While the project is `0.x`, a breaking
change bumps the minor. Procedure, prereleases and workflow jobs:
[`docs/contributing/release.md`](docs/contributing/release.md).

## Non-negotiables

- Never push (or force-push) to `main`, and never bypass its ruleset.
- `just check` and `uv build` must both be green before pushing.
- Tools that move funds or orders (`add_order`, `cancel_order`, `withdraw`,
  `wallet_transfer`, `allocate_earn`, …) are never run against real
  credentials without an explicit opt-in.
- The project is **AGPL-3.0-only**; new source files carry
  `# SPDX-License-Identifier: AGPL-3.0-only`.

## Where to look first

| Task                          | Start at                                        |
| ----------------------------- | ----------------------------------------------- |
| New Kraken endpoint as a tool | `tools/<category>.py` + `PERMISSION_REQUIREMENTS` in `kraken/permissions.py` |
| Transport behaviour           | `server.py`                                      |
| Token lifecycle               | `auth/store.py` + `auth/verifier.py`             |
| CI / release plumbing         | `.github/workflows/`                             |
| Anything cross-cutting        | Open an issue first                              |
