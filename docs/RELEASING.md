# Releasing `fit-tool`

This document is the checklist for publishing a new version to PyPI and GitHub
Releases. Day-to-day contribution rules live in [`AGENTS.md`](../AGENTS.md).

## How release works

| Piece | Role |
| --- | --- |
| `pyproject.toml` → `[project].version` | **Source of truth** for the package version (wheel / sdist / PyPI) |
| Git tag `vX.Y.Z` | Triggers [`.github/workflows/publish.yml`](../.github/workflows/publish.yml) |
| `news/*` + Towncrier | Builds the new section in `CHANGELOG.md` |
| PyPI | Trusted Publishing (OIDC); no long-lived API token in the repo |
| GitHub Release | Created by the same workflow; body = the matching `CHANGELOG.md` section |

The workflow **does not** rewrite the package version from the tag. It only
checks that they match. If they differ, the job fails before publish.

**Tag rules**

- Stable: `v0.9.16` (must match `version = "0.9.16"` in `pyproject.toml`)
- Prerelease: `v0.9.16a1`, `v0.9.16rc1`, `v0.9.16.dev0` (same string without `v` in `pyproject.toml`)
- Do not use bare `0.9.16` or legacy `version/0.9.x` tags for new releases

## Checklist

1. **`main` is green** — CI (Python 3.9–3.14 + Garmin JS interop) passes on the commit you will tag.
2. **News fragments are ready** — user-visible changes have `news/<id>.<type>` files (see `AGENTS.md`). Do not hand-edit an already-released section of `CHANGELOG.md`.
3. **Choose the version** — e.g. `0.9.16` (patch) or `0.10.0` (broader capability signal). PyPI will not accept re-uploading an existing version.
4. **Bump the package version** in `pyproject.toml`:
   ```toml
   version = "0.9.16"
   ```
5. **Build the changelog**:
   ```bash
   uv run towncrier build --version 0.9.16
   # optional dry-run first:
   uv run towncrier build --version 0.9.16 --draft
   ```
   This prepends `## Release v0.9.16 (YYYY-MM-DD)` to `CHANGELOG.md` and removes consumed `news/*` fragments (keep `news/.gitkeep`).
6. **Review** the new `CHANGELOG.md` section and the diff (version + changelog + deleted news files only, unless the release intentionally includes other commits already on `main`).
7. **Commit and merge to `main`** (via PR if that is your normal process).
8. **Tag and push the tag** on the release commit:
   ```bash
   git checkout main
   git pull
   git tag v0.9.16
   git push origin v0.9.16
   ```
9. **Watch** Actions → workflow **Release**. Expect: version gate → `uv build` → dist version check → **changelog section gate** → PyPI publish → GitHub Release with changelog body and `prerelease=false` for stable tags. (Changelog is validated *before* PyPI so a missing Towncrier section cannot leave an orphan upload.)
10. **Verify**:
    - https://pypi.org/project/fit-tool/ shows the new version
    - `pip install fit-tool==X.Y.Z` (or `uv add fit-tool==X.Y.Z`) works
    - GitHub Release page body matches the changelog section and is not marked Pre-release for stable tags

## What the workflow rejects

- Tags that are not `v…`
- Tag version ≠ `pyproject.toml` version
- Built wheel/sdist version ≠ tag version
- Missing `## Release vX.Y.Z` section in `CHANGELOG.md`
- Empty extracted changelog body

## Failure notes

- **PyPI succeeded, GitHub Release failed**: do **not** re-run the whole job blindly (PyPI will reject the same files). Create or edit the GitHub Release for that tag and paste the matching changelog section, or fix the Release step and re-run only that step if the workflow is later split.
- **Version already on PyPI**: bump to a new version; never try to overwrite.
- **Never** push a release tag or publish to PyPI from an automated agent unless a human explicitly requested that release.

## Related docs

- [`AGENTS.md`](../AGENTS.md) — news fragment types and agent constraints
- [`CHANGELOG.md`](../CHANGELOG.md) — published history
- [`EPIC_SHA12_RELEASE_NOTES.md`](EPIC_SHA12_RELEASE_NOTES.md) — narrative rollup for the protocol epic (not a substitute for Towncrier)
