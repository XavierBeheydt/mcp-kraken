<!--
Copyright (c) 2026 Xavier Beheydt <xavier.beheydt@gmail.com>
-->

# Contributing

Tasks are driven by [just](https://github.com/casey/just) and
[uv](https://docs.astral.sh/uv/) — run `just` to list them:

- `just sync` — create or update `.venv` with every extra and dev dependency
- `just check` — lint, format check, mypy and pytest (what CI runs)
- `just test` — pytest only
- `just fix` — auto-fix lint findings and reformat
- `just serve` / `just serve-stdio` — run the server over HTTP or stdio
- `just build` — build the sdist and wheel (`uv build`)
- `just rulesets` — apply the branch and tag rulesets (needs `gh`, admin)

`just check` and `uv build` must both pass before a push.

## Branches

```text
feat/x ─┐
fix/y  ─┼─ PR ─► dev ─── PR (merge commit) ─► main ── tag vX.Y.Z ─► release
docs/z ─┘         │
                  └─► ghcr.io/xavierbeheydt/mcp-kraken:dev
```

| Branch        | Role                                   | Protection                       |
| ------------- | -------------------------------------- | -------------------------------- |
| `main`        | default branch, released code          | PR, merge commit only, CI green  |
| `dev`         | permanent working branch               | no deletion, no force push       |
| `<type>/<slug>` | one feature or fix, off `dev`        | none, deleted once merged        |

`<type>` is the Conventional Commits type the branch mostly carries (`feat`,
`fix`, `docs`, `refactor`, `test`, `ci`, `build`, `chore`). Work in a worktree
under `.worktrees/`:

```sh
git worktree add -b feat/my-new-feature .worktrees/feat/my-new-feature dev
git worktree remove .worktrees/feat/my-new-feature
```

The rulesets live in [`.github/rulesets/`](.github/rulesets/); `just rulesets`
creates or updates them by name. The required status checks are the `test`
matrix and the CodeQL analyses.

## Releases

The version comes from the git tag (hatch-vcs); nothing to bump in source.

1. Open a `dev` → `main` PR, wait for CI, merge it with a merge commit.
2. Tag the merge commit on `main`:

   ```sh
   git switch main && git pull
   git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z
   ```

The `release` workflow refuses a tag that is not on `main`, then publishes
the wheel to PyPI (OIDC trusted publishing), the multi-arch image to GHCR
(`:X.Y.Z`, `:X.Y`, `:X`, `:latest`) and a GitHub Release with generated
notes.

## Trying the server from a checkout

```sh
cp .env.example .env    # set KRAKEN_API_KEY / KRAKEN_API_SECRET
just sync
just serve-stdio        # or: just serve, then `just token-create NAME`
```

Use a read-only Kraken API key while developing: tools that move funds or
orders are never exercised against real credentials.
