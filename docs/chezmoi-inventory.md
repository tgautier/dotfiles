# Chezmoi migration inventory

This document records the public rcm-to-chezmoi migration boundary for issue #232. Rcm remains the deployment owner until every target is classified, the shadow guard passes from a fresh checkout, and a separate cutover change documents backup and rollback commands.

## Authoritative target map

[`chezmoi-targets.tsv`](chezmoi-targets.tsv) is the machine-readable inventory. It contains all 35 public leaf targets reported by rcm and maps each one to an explicit migration disposition. The parity guard independently asks `lsrc` for the current rcm map, so deleting or misnaming an inventory row fails instead of redefining the expected set.

| Column | Meaning |
| --- | --- |
| `rcm_source` | Current public source path selected by rcm |
| `target` | Path relative to the managed home directory |
| `disposition` | Ownership decision for the chezmoi cutover |
| `chezmoi_source` | Source-state path under `home/`, or `-` when deferred |
| `mode` | Required rendered mode: `file` or `executable` |

The dispositions cover every current target:

- `shadow`: 26 targets already represented and verified under `home/`
- `defer-homebrew-link`: the four Brewfile links remain rcm-owned while `HOMEBREW_BUNDLE_FILE` depends on them
- `repository-only`: `CLAUDE.md` stays as project guidance and will not become a global home target
- `defer-machine-overrides`: mise configuration waits for an explicit machine-local override strategy
- `drop-empty-placeholder`: the empty git-template marker is intentionally not reproduced by chezmoi
- `defer-private-overlay`: Git defaults wait for a public/private split that keeps identity and signing configuration private
- `retire-at-cutover`: `rcrc` remains active during shadow operation and disappears only after chezmoi owns deployment

## Ownership rules

- `home/` is the only chezmoi source state; `.chezmoiroot` selects it from repository-root invocations
- Repository metadata, recipes, tests, and documentation stay outside the managed home
- The private companion repository owns secrets, identity-bearing Git configuration, and global agent configuration
- Application-owned mutable state remains deferred until its reconciliation behavior has a dedicated fixture
- Every migration PR updates the manifest when a source, target, mode, or disposition changes

## Parity guard

Run `just test-chezmoi-canary`. The guard uses an isolated temporary HOME, config, cache, persistent state, and destination. It performs no apply against the operator's real home.

The guard:

1. Compares the complete manifest with the target/source map produced by `lsrc`
1. Invokes chezmoi from the repository root and verifies that `.chezmoiroot` selects `home/`
1. Compares the exact chezmoi target/source map with the 26 `shadow` rows
1. Applies into the isolated destination and verifies bytes plus executable modes
1. Applies twice and requires an empty diff after each apply
1. Runs sabotage fixtures for a misnamed target, an omitted row, a duplicate row, a missing source, and an extra source

The guard now maps `zsh/zaliases` and `zsh/zcompletion` to `~/.zsh/zaliases` and `~/.zsh/zcompletion`, matching both rcm and `zshrc`. The previous source names rendered an extra dot in each target while the hand-maintained canary still passed.

## Upgrade and rollback

This shadow change does not alter installed dotfiles. Pull the repository and run `just ci`; keep using `just link` for active rcm deployment. Do not run chezmoi against the real home as part of this phase.

Rollback is a repository revert only: restore the previous revision and rerun `just ci`. Existing rcm links and their targets remain untouched because every chezmoi apply in the guard is confined to a temporary destination.

The future cutover remains blocked until the exact guard passes from a fresh checkout and the cutover PR records the backup, apply, verification, and rcm rollback sequence for macOS, Linux, and WSL2.
