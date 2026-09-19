# Versioning & releases

## The version number

`mcp-kraken` follows [Semantic Versioning](https://semver.org/): **`a.b.c`**,
tagged in git as `va.b.c`.

| Position | Name  | Bump it when the release contains…                         |
| -------- | ----- | ----------------------------------------------------------- |
| `a`      | major | A **breaking change** — an MCP tool signature or return shape that changes incompatibly, a removed or renamed config key or CLI command, a token-store format that old versions cannot read. |
| `b`      | minor | **New features**, backwards compatible — a new MCP tool, a new Kraken endpoint, a new config option or CLI flag. |
| `c`      | patch | **Fixes and security** — bug fixes, security fixes, dependency bumps, docs and CI-only changes. |

The bump follows mechanically from the Conventional Commit types merged into
`dev` since the previous tag (see [conventions.md](conventions.md)):

- any commit marked `!` or carrying a `BREAKING CHANGE:` footer → **major**
- otherwise, any `feat:` → **minor**
- otherwise (`fix:`, `perf:`, `docs:`, `build:`, `ci:`, `chore:`) → **patch**

> **While the project is `0.x`** every release is alpha, as stated in the
> README disclaimer: a breaking change bumps the **minor** (`0.3.0` →
> `0.4.0`) instead of the major, and features land in the patch position when
> a minor is not warranted. The first stable API freeze is what makes `1.0.0`.

Nothing in the source tree carries a version.
[`hatch-vcs`](https://github.com/ofek/hatch-vcs) derives it from the git tag
(`v1.2.3` → `1.2.3`), so **the tag is the version** — there is no field to
bump in `pyproject.toml`.

## Every merge into `main` is a release

`main` only ever advances through a reviewed pull request coming from a
`release/*` or `hotfix/*` branch, and that merge commit is then tagged. If a
change reached `main`, it ships — there is no "merged but unreleased" state
on `main`.

```
feat/* fix/* docs/*  ─PR─►  dev  ──►  dev-publish  ──►  ghcr.io/…:dev
                             │
                             └─ release/vX.Y.Z ─PR─► main ─ tag vX.Y.Z ─► release
                                                      │                    │
                        hotfix/vX.Y.Z ─PR─────────────┘                    ├─ ghcr.io/…:X.Y.Z, :X.Y, :X, :latest
                                                                           ├─ PyPI (OIDC trusted publishing)
                                                                           └─ GitHub Release + built artifacts
```

## Cutting a release

1. Make sure `dev` is green and holds everything you want to ship.

   ```bash
   git switch dev && git pull
   just check && uv build
   ```

2. Decide the number with the table above, then open the release branch:

   ```bash
   git switch -c release/v1.2.0
   ```

3. Stabilise on that branch — documentation, changelog-worthy README or
   `TODO.md` updates, last-minute fixes. No version field to edit. Push it;
   the `test` workflow runs on the pull request.

4. Open a PR `release/v1.2.0` → `main`, get it reviewed, merge it. The `main`
   ruleset requires the PR and the status checks, so this is the only way in.

5. Tag the merge commit on `main` and push the tag — this is what publishes:

   ```bash
   git switch main && git pull
   git tag -a v1.2.0 -m "v1.2.0"
   git push origin v1.2.0
   ```

6. Back-merge `main` into `dev` so the release commits (and the tag's
   history) are part of the integration branch:

   ```bash
   git switch dev && git merge --no-ff main && git push
   ```

7. Delete the `release/*` branch.

## Hotfixes

Same shape, starting from `main` instead of `dev`:

```bash
git switch main && git pull
git switch -c hotfix/v1.2.1
# fix, test, push, PR into main, merge
git switch main && git pull && git tag -a v1.2.1 -m "v1.2.1" && git push origin v1.2.1
git switch dev && git merge --no-ff main && git push   # never skip this
```

## Prereleases

Tag a `release/*` branch `vX.Y.Z-rcN` (for example `v1.2.0-rc1`) before
merging into `main`. The release workflow then:

- pushes the images `:1.2.0-rc1`, `:1.2-rc1`, `:1-rc1` and **not** `:latest`,
- publishes the wheel to **TestPyPI** instead of PyPI,
- marks the GitHub Release as a prerelease.

Because a prerelease is cut before the merge, it is the one tag that is not
required to be on `main` — the release workflow's lineage guard skips it.

## What the release workflow does

Triggered by any `v*` tag push ([`.github/workflows/release.yml`](../../.github/workflows/release.yml)):

| Job                | What it does                                                        |
| ------------------ | -------------------------------------------------------------------- |
| `guard`            | For a final `vX.Y.Z` tag, verifies the tagged commit is contained in `main` and fails the release otherwise. Prereleases are exempt. |
| `test`             | Reuses `test.yml` — ruff, format check, mypy, pytest on 3.12 and 3.13. |
| `build-dist`       | `uv build` → sdist + wheel, uploaded as an artifact.                  |
| `publish-image`    | Multi-arch image to GHCR with semver tags, provenance and SBOM.       |
| `publish-pypi`     | OIDC trusted publishing to PyPI (final tags only).                    |
| `publish-testpypi` | Same, to TestPyPI (prerelease tags only).                             |
| `github-release`   | GitHub Release with auto-generated notes and the built artifacts.     |

No job pushes to `main` — see [branching.md](branching.md) for why that
matters for branch protection.

## See also

- [branching.md](branching.md) — branches and protection rulesets.
- [conventions.md](conventions.md) — commit types that drive the bump.
- [TODO.md](../../TODO.md) — what is planned for the next versions.
