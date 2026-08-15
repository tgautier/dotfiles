# Chezmoi target inventory

This document describes the public chezmoi target manifest and the parity guard that validates it.

## Authoritative target map

[`chezmoi-targets.tsv`](chezmoi-targets.tsv) is the machine-readable inventory. It maps every public source to its chezmoi deployment target.

| Column | Meaning |
| --- | --- |
| `source` | Public source path in this repository |
| `target` | Path relative to the managed home directory |
| `disposition` | Ownership classification |
| `chezmoi_source` | Source-state path under `home/`, or `-` for repository-only targets |
| `mode` | Required rendered mode: `file` or `executable` |

The dispositions cover every target:

- `shadow`: targets deployed by chezmoi from sources under `home/`
- `repository-only`: `CLAUDE.md` stays as project guidance and is not a global home target

## Ownership rules

- `home/` is the only chezmoi source state; `.chezmoiroot` selects it from repository-root invocations
- Repository metadata, recipes, tests, and documentation stay outside the managed home
- The private companion repository owns secrets, identity-bearing Git configuration, and global agent configuration
- Application-owned mutable state is excluded from chezmoi management
- Every migration PR updates the manifest when a source, target, mode, or disposition changes

## Parity guard

Run `just test-chezmoi-canary`. The guard uses an isolated temporary HOME, config, cache, persistent state, and destination. It performs no apply against the operator's real home.

The guard:

1. Validates every manifest row against the repository source tree
1. Invokes chezmoi from the repository root and verifies that `.chezmoiroot` selects `home/`
1. Compares the exact chezmoi target/source map with the `shadow` rows
1. Runs the optional companion ownership preflight before the first public apply
1. Applies into the isolated destination and verifies bytes plus executable modes
1. Applies twice and requires an empty diff after each apply
1. Runs the optional companion source canary after the public apply is idempotent
1. Runs companion available, conflicting-package, absent, non-directory, stale, ownership-rejection, source-rejection, and output-withholding fixtures plus sabotage fixtures for a misnamed target, omitted shadow rows, a duplicate row, a missing source, and an extra source

The guard resolves the private companion checkout from `DOTFILES_PRIVATE_DIR`, defaulting to `~/Workspace/tgautier/dotfiles-private`. If that path is absent, it reports a generic skip without printing the configured path and continues the public-only canary. If the checkout exists, a stdlib Python bridge requires the companion checker for each phase and rejects symlinks anywhere in its package or module import path. It invokes the target-ownership checker before the first public apply and the isolated private source canary only after the public second apply leaves no diff. The phases share a private mode-`0600` state file containing only an opaque checkout identity derived from the resolved root, Git HEAD and status when available, tracked and nonignored source content, and every importable top-level Python module or package tree even when ignored. Source symlinks are accepted only when they resolve inside the checkout to content included in that same snapshot. The source phase fails if the companion appears, disappears, is replaced, switches revision, or changes source content after ownership. Python and Git environment overrides plus virtual-environment site-package discovery are disabled for both invocations. The bridge also replaces HOME and all inherited XDG paths with a temporary root before either checker starts. It captures all companion output on success and failure, starts each check in its own process group, and performs bounded cleanup of that complete group after every checker exit, including a deadline expiry. A stale, partial, failing, or wedged private checkout fails without exposing private checker output.

## Upgrade and rollback

Pull the private companion repository first when it is installed, then pull this repository and run `just test-chezmoi-canary`. The command changes no HOME file. A machine without the private repository continues to run the complete public-only canary without private paths or target identifiers in its output. Use `just link` for deployment and run `just ci` before publishing changes.

After the canary passes, `just chezmoi-status`, `just chezmoi-diff`, and `just chezmoi-apply-dry-run` inspect the real HOME through explicit public and private source roots. They do not modify managed targets, but they create owner-only operator metadata under `${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/chezmoi` and `${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/chezmoi`. The diff and verbose dry run can display complete private target contents; review them only in the local terminal and never paste their output into this public repository. Do not invoke bare `chezmoi apply`.

To roll back a bad change, revert the commit that introduced it and run `just link`. Chezmoi re-renders every target from the current source state on each apply, so a reverted source restores the previous content.
