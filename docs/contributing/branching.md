# Branching model — GitFlow

mcp-kraken follows the
[nvie GitFlow model](https://nvie.com/posts/a-successful-git-branching-model/).

## Branches

| Branch       | Purpose                                                        | Lifetime    |
| ------------ | -------------------------------------------------------------- | ----------- |
| `main`       | Latest released commit, tag-only.                              | Permanent   |
| `develop`    | Integration branch; **default branch on GitHub**.              | Permanent   |
| `feature/*`  | Topic branches off `develop`.                                  | Short-lived |
| `release/*`  | Stabilisation; PR into `main` when ready.                      | Short-lived |
| `hotfix/*`   | Emergency fix off `main`; PR into `main` + back-merge to `develop`. | Short-lived |

### Day-to-day flow

- New work → `feature/<slug>` from `develop` → PR into `develop`.
- Cut release → `release/vX.Y.Z` from `develop` → stabilise → PR into
  `main` → tag `vX.Y.Z` on the merge commit → back-merge to `develop`.
- Emergency → `hotfix/vX.Y.Z+1` from `main` → fix → PR into `main` →
  tag → back-merge to `develop`.

## Branch protection — rulesets

Three rulesets live under [`rulesets/`](rulesets/) and are applied via
`gh api`:

- [`main.json`](rulesets/main.json) — strong: PR required, linear
  history, no force push, no deletion, status checks
  (`test (3.12)`, `test (3.13)`, `analyze (python)`, `analyze (actions)`),
  `require_last_push_approval`.
- [`develop.json`](rulesets/develop.json) — moderate: PR required, no
  force push, no deletion, same status checks.
- [`release-hotfix.json`](rulesets/release-hotfix.json) — light: no
  force push, status checks only (no PR requirement, so stabilisation
  pushes stay fluid).

`feature/*` is intentionally **unprotected** — these branches are
ephemeral working space.

`required_approving_review_count` is `0` for now because the project has
a single maintainer. Bump it to `1` (or higher) once additional
maintainers join: edit the corresponding JSON file and re-apply.

### Apply or refresh the rulesets

```bash
./docs/contributing/rulesets/apply.sh
```

The script POSTs each JSON to `repos/.../rulesets`. Re-running creates
duplicates, so delete the previous ruleset in the GitHub UI first if you
want to recreate it from scratch.

To **update** an existing ruleset without deleting it:

```bash
RULESET_ID="$(gh api repos/XavierBeheydt/mcp-kraken/rulesets \
    --jq '.[] | select(.name=="main protection") | .id')"
gh api -X PUT "repos/XavierBeheydt/mcp-kraken/rulesets/${RULESET_ID}" \
    --input docs/contributing/rulesets/main.json
```

### Post-apply manual step

`release.yml`'s `fast-forward-main` job pushes to `main` as
`github-actions[bot]`. The job needs to bypass the `main protection`
ruleset to succeed:

1. Settings → Rules → **main protection**.
2. Bypass list → Add bypass.
3. Search **github-actions[bot]**.
4. Bypass mode: **Always**.
5. Save.

Without this, the job exits with a warning instead of fast-forwarding
`main` to the release tag.

## See also

- [PLAN.md](../../PLAN.md) — full reorientation plan.
- [TODO.md](../../TODO.md) — longer-horizon roadmap.
- The nvie.com GitFlow article linked at the top.
