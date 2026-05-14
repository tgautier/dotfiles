# Versioning

All releasable artifacts follow [Semantic Versioning 2.0.0](https://semver.org). The version lives in a single canonical location per project (Cargo workspace `[workspace.package].version`, `package.json`, `pubspec.yaml`, `mix.exs`, etc.) and propagates from there.

## Format

`MAJOR.MINOR.PATCH[-PRERELEASE]`.

| Bump | When (≥ 1.0.0) | When (0.x.y, pre-1.0) |
| --- | --- | --- |
| MAJOR | Breaking change to public API, CLI flags, on-disk format, schema, wire protocol | n/a — stay 0.x |
| MINOR | Backwards-compatible feature | Any user-visible change, including breaking ones (pre-1.0 caveat) |
| PATCH | Bug fix, internal refactor, no surface change | Bug fix, internal refactor |

**Pre-1.0 is unstable by definition.** Breaking changes are allowed at any minor bump. The project's `README.md` / `CHANGELOG.md` must call out breaking changes explicitly so users notice without reading the diff.

## Commit type → version bump

Conventional commits map to bumps (consistent with the `git-conventions` rule):

- `fix:` / `perf:` → PATCH
- `feat:` → MINOR
- `feat!:` or any commit with `BREAKING CHANGE:` in the body → MAJOR (pre-1.0: still MINOR; document in `CHANGELOG.md`)
- `docs:` / `chore:` / `test:` / `refactor:` (no behavior change) → no bump on their own; ride the next release

Multiple commits between releases collapse to the highest bump implied by any of them.

## Changelog

Every project keeps a `CHANGELOG.md` at the root, in [Keep a Changelog](https://keepachangelog.com) format:

- `## [Unreleased]` at the top accumulates entries as work lands.
- On release: rename `[Unreleased]` → `[X.Y.Z] - YYYY-MM-DD`, create a new empty `[Unreleased]` above it.
- Group entries under `### Added`, `### Changed`, `### Deprecated`, `### Removed`, `### Fixed`, `### Security`.
- Reference issues/PRs inline.

## Release procedure

1. **Bump the version** in the canonical location, no other places — derive everywhere else.
2. **Update `CHANGELOG.md`**: move `[Unreleased]` content under the new version heading; date it.
3. **Commit** with `chore(release): vX.Y.Z`.
4. **Tag** with `git tag vX.Y.Z` (annotated, signed if signing is configured). Tag and crate/package versions must agree.
5. **Push** the tag (`git push origin vX.Y.Z`) and the commit. The tag is the immutable artifact.
6. **GitHub release** (`gh release create vX.Y.Z --notes-from-tag` or with `--notes-file CHANGELOG.md` excerpt). Releases attach binaries / artifacts if the project ships them.

Never reuse a tag. If a release is broken, ship `vX.Y.Z+1` (PATCH bump) — never `git tag -f`.

## Workspace projects

Cargo / pnpm / Pub workspaces have a choice: single workspace-wide version vs per-package independent versions. Default to **single workspace version** — simpler bookkeeping, one tag per release. Switch to per-package only when one of the crates is published independently and needs its own cadence; document the switch in the project's `CLAUDE.md`.

## Anti-patterns

- Bumping the version in `Cargo.toml` without a corresponding `CHANGELOG.md` entry.
- Releasing without tagging — leaves no immutable reference for rollback or downstream pinning.
- Tagging without pushing — local-only tags are lost on machine swap.
- Force-pushing a tag (`git tag -f`) or moving an existing tag.
- Treating `0.x.y` as stable — pre-1.0 versions exist precisely so the API can churn.
- Bumping MAJOR for refactors that don't change the public surface.
- Skipping versions ("we went 0.3 → 0.5 to match the issue tracker"). Versions are not labels.
