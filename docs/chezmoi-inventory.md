# Chezmoi migration inventory

This document records the public rcm-to-chezmoi migration boundary for issue #232. Rcm remains the deployment owner until every target is classified, the shadow guard passes from a fresh checkout, and a separate cutover change documents backup and rollback commands.

## Authoritative target map

[`chezmoi-targets.tsv`](chezmoi-targets.tsv) is the machine-readable inventory. It contains every public leaf target reported by rcm and maps each one to an explicit migration disposition. The parity guard independently asks `lsrc` for the current rcm map, so deleting or misnaming an inventory row fails instead of redefining the expected set.

| Column | Meaning |
| --- | --- |
| `rcm_source` | Current public source path selected by rcm |
| `target` | Path relative to the managed home directory |
| `disposition` | Ownership decision for the chezmoi cutover |
| `chezmoi_source` | Source-state path under `home/`, or `-` when deferred |
| `mode` | Required rendered mode: `file` or `executable` |

The dispositions cover every current target:

- `shadow`: targets already represented and verified under `home/`
- `defer-homebrew-link`: the four Brewfile links remain rcm-owned while `HOMEBREW_BUNDLE_FILE` depends on them
- `repository-only`: `CLAUDE.md` stays as project guidance and will not become a global home target
- `defer-machine-overrides`: mise configuration waits for an explicit machine-local override strategy
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
1. Compares the exact chezmoi target/source map with the `shadow` rows
1. Applies into the isolated destination and verifies bytes plus executable modes
1. Applies twice and requires an empty diff after each apply
1. Runs private-checkout available, conflicting-package, absent, non-directory, stale, and rejection fixtures plus sabotage fixtures for a misnamed target, omitted shadow and deferred rows, a retired disposition, a duplicate row, a missing source, and an extra source

The guard resolves the private companion checkout from `DOTFILES_PRIVATE_DIR`, defaulting to `~/Workspace/tgautier/dotfiles-private`. If that path is absent, it reports an explicit skip and continues the public-only canary. If the checkout exists, the guard requires its target-ownership checker and invokes it before the first isolated `chezmoi apply`. Python-specific environment overrides and site-package discovery are disabled for that invocation, keeping module resolution inside the selected checkout and the standard library. A stale or partial private checkout fails instead of silently dropping the cross-repository gate.

The guard now maps `zsh/zaliases` and `zsh/zcompletion` to `~/.zsh/zaliases` and `~/.zsh/zcompletion`, matching both rcm and `zshrc`. The previous source names rendered an extra dot in each target while the hand-maintained canary still passed.

## Upgrade and rollback

Pull the private companion repository first when it is installed, then pull this repository and run `just test-chezmoi-canary`. The command changes no HOME file: both chezmoi applies still target the temporary destination. A machine without the private repository continues to run the complete public-only parity canary. Keep using `just link` for active rcm deployment, and run `just ci` before publishing changes.

The removed empty Git-template marker may leave `~/.git_template/hooks/gitkeep` as an obsolete rcm symlink. Run `just link-inventory` after pulling. If the inventory reports that exact target as obsolete, follow the approval-bound plan, cleanup, and verification steps in [Rcm link reconciliation](rcm-link-reconciliation.md). Review every path in the generated plan because it can include other obsolete links.

To roll back this checkpoint before HOME cleanup, restore the earlier public revision and run `just ci`. No HOME action or private-repository rollback is needed for the overlap-gate integration. After cleanup, restore the retained approved plan before reverting the repository, as described in the reconciliation guide. Every chezmoi apply in the guard remains confined to a temporary destination.

The future cutover remains blocked until the exact guard passes from a fresh checkout, `just link-inventory` reconciles current and historical rcm HOME links with no unresolved obsolete set after the approval-bound cleanup decision, and the cutover PR records the backup, apply, verification, and rcm rollback sequence for macOS, Linux, and WSL2.
