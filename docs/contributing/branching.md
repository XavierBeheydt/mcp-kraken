# Branching model — GitFlow

mcp-kraken follows the
[nvie GitFlow model](https://nvie.com/posts/a-successful-git-branching-model/).

## Branches

| Branch        | Purpose                                                             | Lifetime    |
| ------------- | ------------------------------------------------------------------- | ----------- |
| `main`        | Latest released commit. Protected, tag-only, never pushed to directly. | Permanent   |
| `develop`     | Integration branch; **default branch on GitHub**.                    | Permanent   |
| `<type>/<slug>` | Topic branches off `develop` — `feat/`, `fix/`, `docs/`, `refactor/`, `perf/`, `test/`, `ci/`, `build/`, `chore/`. | Short-lived |
| `release/vX.Y.Z` | Stabilisation; PR into `main` when ready.                         | Short-lived |
| `hotfix/vX.Y.Z` | Emergency fix off `main`; PR into `main` + back-merge to `develop`. | Short-lived |

The topic-branch prefix is the Conventional Commit type the branch mostly
carries, so the branch name and its commits agree — the full list and the
commit format live in [conventions.md](conventions.md).

### Day-to-day flow

- New work → `feat/<slug>` (or `fix/`, `docs/`, …) from `develop` → PR into
  `develop`.
- Cut a release → `release/vX.Y.Z` from `develop` → stabilise → PR into
  `main` → tag `vX.Y.Z` on the merge commit → back-merge `main` to `develop`.
- Emergency → `hotfix/vX.Y.Z` from `main` → fix → PR into `main` → tag →
  back-merge to `develop`.

Every one of those tags is a release; how the number is chosen is in
[release.md](release.md).

## Branch protection — rulesets

Four rulesets live under [`rulesets/`](rulesets/) and are applied with
`gh api`:

- [`main.json`](rulesets/main.json) — strongest: pull request required,
  `dismiss_stale_reviews_on_push`, `require_last_push_approval`, no force
  push, no deletion, and the status checks `test (3.12)`, `test (3.13)`,
  `analyze (python)`, `analyze (actions)` under a strict (up-to-date)
  policy.
- [`develop.json`](rulesets/develop.json) — moderate: pull request required,
  no force push, no deletion, same status checks.
- [`release-hotfix.json`](rulesets/release-hotfix.json) — light: no force
  push, tests only, no pull-request requirement so stabilisation pushes stay
  fluid.
- [`tags.json`](rulesets/tags.json) — `v*` tags cannot be moved or deleted
  once pushed, and must match `vX.Y.Z` or `vX.Y.Z-rcN`. A published version
  is immutable.

Topic branches (`feat/*`, `fix/*`, …) are intentionally **unprotected** —
they are ephemeral working space.

`required_approving_review_count` is `0` for now because the project has a
single maintainer: the pull-request requirement is what matters, since it
keeps every change to `main` reviewable and CI-gated. Bump the count to `1`
(or higher) once other maintainers join — edit the JSON and re-apply.

### Why `main` allows merge commits

`main.json` deliberately does **not** require a linear history. GitFlow
merges `release/*` and `hotfix/*` into `main` with a merge commit, and the
release tag is placed on that commit; requiring linear history would force a
squash and detach `main`'s history from the commits reviewed on `develop`.

### Nothing automated pushes to `main`

No workflow writes to `main`: the release workflow only reads the tag, and it
refuses a final `vX.Y.Z` tag that is not contained in `main` (its `guard`
job). `main` therefore advances only through a reviewed pull request, and the
rulesets need **no bypass actor** — the bypass list stays empty.

### Apply or refresh the rulesets

```bash
./docs/contributing/rulesets/apply.sh
```

The script POSTs each JSON to `repos/.../rulesets`. Re-running creates
duplicates, so delete the previous ruleset in the GitHub UI first if you want
to recreate it from scratch.

To **update** an existing ruleset in place:

```bash
RULESET_ID="$(gh api repos/XavierBeheydt/mcp-kraken/rulesets \
    --jq '.[] | select(.name=="main protection") | .id')"
gh api -X PUT "repos/XavierBeheydt/mcp-kraken/rulesets/${RULESET_ID}" \
    --input docs/contributing/rulesets/main.json
```

## See also

- [release.md](release.md) — versioning scheme and release procedure.
- [conventions.md](conventions.md) — commit and branch naming.
- [PLAN.md](../../PLAN.md) — the reorientation plan this model is part of.
