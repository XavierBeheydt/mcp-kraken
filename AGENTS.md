# AGENTS.md — Instructions for AI agents

## Project

See [README.md](README.md) for the full project description and
[CONTRIBUTING.md](CONTRIBUTING.md) for the dev tasks.

An MCP server that wraps the **Kraken Spot REST API** and exposes it over
streamable HTTP (bearer-token auth) or stdio, plus a CLI that manages those
bearer tokens. Single process, stateless beyond a SQLite token store.

**Hard constraint: stay a thin, faithful wrapper of the Kraken API.** One MCP
tool per Kraken endpoint, parameters named as Kraken names them, no business
logic Kraken does not have. WebSocket v2 and FIX are out of scope (see
[TODO.md](TODO.md)).

## Project organization

src layout. Scaffold on demand: create a file or directory only when a change
needs it, never as empty placeholders.

```text
.
├── src/mcp_kraken/
│   ├── cli.py config.py logging.py server.py
│   ├── auth/              # bearer-token store (SQLite) + FastMCP TokenVerifier
│   ├── kraken/            # async REST client, signing, errors, permissions
│   └── tools/
│       └── <category>.py  # one module per Kraken API category
├── tests/
│   └── test_<module>.py
├── docker/                # Dockerfile (build context is the repo root)
├── docs/                  # GitHub Pages site
├── .github/
│   ├── workflows/         # test, codeql, dev-publish, release, pages
│   └── rulesets/          # branch/tag protection, applied with `just rulesets`
├── Justfile               # dev tasks: sync, check, test, fix, serve, …
├── pyproject.toml         # hatchling + hatch-vcs, ruff, mypy, pytest config
├── README.md
└── LICENSE
```

Conventions:

- `tools/<category>.py` mirrors a section of the Kraken Spot REST reference
  (market data, account data, trading, funding, subaccounts, earn,
  transparency). Each tool calls exactly one endpoint.
- Every private endpoint is listed in
  `kraken/permissions.py::PERMISSION_REQUIREMENTS`.
- Tests are behavioural: mock Kraken with **respx**, never monkey-patch
  internals. Every tool has at least one respx-backed test.
- Dependencies go through uv (`uv add`, `uv add --dev`); never edit the
  dependency lists in `pyproject.toml` by hand, never invent versions.
- No version number lives in source: hatch-vcs derives it from the git tag.

## Kraken API rules

- The Kraken reference is the source of truth:
  <https://docs.kraken.com/exchange/api-reference/overview> and its release
  notes <https://docs.kraken.com/api/docs/change-log>. Check both before
  adding or changing a tool.
- Endpoint names are exact and case-sensitive (`BalanceEx`, `TradesHistory`,
  `WithdrawMethods`, `CancelAll`, `GetApiKeyInfo`). `EGeneral:Unknown method`
  means the name is wrong, not that the account lacks the feature.
- Kraken returns errors as `200 OK` with a non-empty `error` array.
  `KrakenClient._unwrap` classifies them: extend `errors.classify` for a new
  error category, not the call sites.
- Tools that move funds or orders (`add_order`, `cancel_*`, `withdraw`,
  `wallet_transfer`, `account_transfer`, `allocate_earn`, …) are dangerous:
  never call them with real credentials in tests, docs or demos. Order tools
  expose Kraken's `validate` flag for dry runs.

## Code style

- Python 3.12+, type annotations everywhere, mypy strict.
- ruff does lint and format, line length 100 (no black, no isort).
- Comment sparingly and stay concise: no comment that restates the code, no
  verbose docblocks. Comment only the non-obvious *why*. Tool docstrings are
  the exception: they are the tool description the LLM reads, so document
  every parameter.
- Tool parameters typed `list[T] | None = None` lose their `type: array` JSON
  schema and Claude Code then sends them as strings. Use
  `Annotated[list[T], Field(default_factory=list)]` (with `# noqa: B008`).
- Every source file, whatever its language, starts with a copyright header in
  that language's comment syntax, using the current year and the name(s) of
  the person(s) who wrote the code; add a line as others contribute:

  ```text
  Copyright (c) <ACTUAL-YEAR> FirstName Lastname <email>
  ```

## Agent configuration

- `AGENTS.md` (this file) is the single source of truth for agent instructions.
- `CLAUDE.md` is a symlink pointing at it — edit `AGENTS.md`, never `CLAUDE.md`.
- Extra agent assets (subagents, slash commands, tool-specific settings) live in
  `.agents/`, the canonical directory.
- `.claude` is a **committed symlink** to `.agents` (like `CLAUDE.md`), so a
  fresh clone is ready to use by AI agents as-is. Never commit regular files
  under `.claude/` — edit `.agents/` and commit there.

## Git workflow

- Never commit directly on `main`. Work on another branch (e.g. `dev`, or a
  worktree) and bring changes into `main` through a merge or a PR.
- `main` is protected (pull request required, merge commit only, CI green) and
  is the default branch. `dev` is the permanent working branch: never delete
  it, locally or on the remote, even after a `dev` → `main` merge, and never
  enable "delete branch on merge". Cleaning up after a merge removes only the
  merged feature or fix branch and its worktree.
- Feature and fix branches start from `dev` and come back to it through a PR.
  Every push to `dev` publishes the `ghcr.io/xavierbeheydt/mcp-kraken:dev`
  image.
- Releases are tagged by hand as semver `vX.Y.Z`, right after the `dev` →
  `main` PR is merged and CI is green: tag the merge commit of `main`, never
  `dev`. The tag runs the `release` workflow (PyPI, GHCR, GitHub Release),
  which refuses a tag that is not on `main`. Never tag unless the user asks.

  ```sh
  git switch main && git pull
  git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z
  ```
- Work is planned in GitHub milestones (`vX.Y.Z`) and issues; reference the
  issue in the PR (`Closes #N`).
- Branch worktrees live under `.worktrees/`, ignored by git. Use them per
  feature or fix instead of juggling branches in the main tree. Name each
  worktree after its branch, so the path carries the Conventional Commits
  type, and remove it once its branch is merged:

  ```sh
  git worktree add -b feat/my-new-feature .worktrees/feat/my-new-feature dev
  git worktree remove .worktrees/feat/my-new-feature
  ```
- Commit messages and PR titles (a squash merge keeps the title) follow
  Conventional Commits: <https://www.conventionalcommits.org/en/v1.0.0/>. Read
  that spec when in doubt.
- Keep commits small and atomic. `just check` and `uv build` pass before every
  push.
- Never force-push `main` or `dev`.
- No AI co-author: commits and PRs carry no `Co-Authored-By` trailer or
  "generated with" line for an AI, unless the user explicitly asks for it.

## Language rules

- All code, comments, documentation, and anything committed to the
  repository are written in **English**, unless the user explicitly asks for
  another language.
- The interactive conversation with the user happens in **the user's own
  language**.

## License

See [LICENSE](LICENSE).
