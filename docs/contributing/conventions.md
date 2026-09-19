# Conventions — language, commits, branches, code

These are the working rules for this repository. They are shared with
[`XavierBeheydt/dotfiles`](https://github.com/XavierBeheydt/dotfiles), so a
habit learned in one repo transfers to the other.

## Language

All repository content — code, comments, docstrings, log and error
messages, commit messages, documentation — is written in **English**, always.
In an interactive session an agent replies to the user in whatever language
the user writes; that rule is about conversation, not about repo content.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
type(scope): description

optional body

optional footer
```

- `type` — one of the types below (same vocabulary as the branch prefixes).
- `scope` — optional, the area touched: `auth`, `kraken`, `tools`, `server`,
  `cli`, `config`, `docker`, `ci`, `docs`, `deps`.
- `description` — imperative mood, lower case, no trailing period, subject
  line ≤ 72 characters.
- Breaking change — either a `!` after the scope (`feat(tools)!: …`) or a
  `BREAKING CHANGE: …` footer. This is what drives the major version bump,
  see [release.md](release.md).

| Type       | Use for                                                        |
| ---------- | -------------------------------------------------------------- |
| `feat`     | A new user-visible capability (a new MCP tool, a new flag).     |
| `fix`      | A bug fix. Security fixes use the `security` scope: `fix(security): …`. |
| `docs`     | Documentation only.                                             |
| `refactor` | Behaviour-preserving code change.                               |
| `perf`     | Performance work.                                               |
| `test`     | Tests only.                                                     |
| `ci`       | Workflows, actions, rulesets.                                   |
| `build`    | Build backend, packaging, Dockerfile, dependencies.             |
| `chore`    | Housekeeping that fits nothing above.                           |
| `revert`   | Reverting a previous commit.                                    |

Commits written by a coding agent keep a `Co-Authored-By:` trailer; pull
requests are authored by the maintainer unless they ask otherwise.

## Branch names

`<type>/<slug>` — the prefix is the commit type the branch mostly carries,
the slug is kebab-case:

```
feat/futures-rest-client
fix/apikey-query-redaction
docs/mkdocs-migration
ci/dockerhub-registry
```

Prefixes: `feat/`, `fix/`, `docs/`, `refactor/`, `perf/`, `test/`, `ci/`,
`build/`, `chore/`.

Two prefixes are reserved by the release process and carry a version rather
than a slug — `release/vX.Y.Z` and `hotfix/vX.Y.Z` (see
[branching.md](branching.md)).

## Code

- Type annotations everywhere; `mypy` runs in **strict** mode.
- Line length 100. `ruff` does both lint and format (no black, no isort).
- Every source file starts with the SPDX header
  `# SPDX-License-Identifier: AGPL-3.0-only`.
- Tests target behaviour, not implementation: prefer respx-mocked Kraken
  responses over monkey-patching internals.
- `just check` (lint + format check + mypy + pytest) and `uv build` must both
  be green before pushing.

### Comment tags

| Tag     | Meaning                                                      |
| ------- | ------------------------------------------------------------ |
| `TODO`  | Task to do later.                                             |
| `FIXME` | Known bug or fragile code.                                    |
| `HACK`  | Deliberate workaround, not the real fix.                      |
| `XXX`   | Doubtful or dangerous code — look before touching.            |
| `BUG`   | Confirmed, documented bug.                                    |
| `NOTE`  | Context for the reader, no action needed.                     |

## Versions belong to tools, not to people

Wherever a version literal appears, it comes from the tool that owns that
ecosystem — never from memory, never hand-written:

| Domain                       | Tool / mechanism |
| ---------------------------- | ---------------- |
| `mcp-kraken` package version | `hatch-vcs` derives it from the git tag. Never write a version in `pyproject.toml`. |
| Python dependencies          | `uv add <pkg>` / `uv add --dev <pkg>` — uv picks a compatible range. |
| GitHub Actions               | Pinned to a major (`@v7`); Dependabot bumps them. |
| Docker base images           | Pinned to a major tag; refreshed by Dependabot or an explicit `docker pull`. |
| Python interpreter           | `uv python install`; the CI matrix picks the versions. |

If the right version is unknowable without running the tool, run the tool.

## See also

- [branching.md](branching.md) — GitFlow branches and branch protection.
- [release.md](release.md) — versioning scheme and how to cut a release.
- [CLAUDE.md](../../CLAUDE.md) / [AGENTS.md](../../AGENTS.md) — the short
  project brief that points here.
