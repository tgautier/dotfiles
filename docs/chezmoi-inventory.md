# Chezmoi migration inventory

This is the Phase 1 baseline for issue #232. It records the current rcm-owned
targets before any source files are moved into chezmoi's `home/` tree. The
cutover remains intentionally deferred until the shadow-apply and rollback
criteria are demonstrated.

| Current source | Target | Current owner | Phase 1 disposition |
| --- | --- | --- | --- |
| `gitconfig` | `~/.gitconfig` | rcm | defer: identity-bearing; split public defaults from private identity/signing overlay |
| `gitignore` | `~/.gitignore` | rcm | migrate as a plain chezmoi file |
| `agignore` | `~/.agignore` | rcm | migrate as a plain chezmoi file |
| `editorconfig` | `~/.editorconfig` | rcm | migrate as a plain chezmoi file |
| `tmux.conf` | `~/.tmux.conf` | rcm | migrate as a plain chezmoi file |
| `zshenv` | `~/.zshenv` | rcm | migrate as a plain chezmoi file |
| `zprofile` | `~/.zprofile` | rcm | migrate as a plain chezmoi file |
| `zshrc` | `~/.zshrc` | rcm | migrate as a plain chezmoi file |
| `zlogin` | `~/.zlogin` | rcm | migrate as a plain chezmoi file |
| `zsh/` | `~/.zsh/` | rcm | migrate as a directory; verify function modes |
| `psqlrc` | `~/.psqlrc` | rcm | migrate as a plain chezmoi file |
| `config/ghostty/config` | `~/.config/ghostty/config` | rcm | migrate as a plain chezmoi file |
| `config/mise/config.toml` | `~/.config/mise/config.toml` | rcm | migrate as a plain chezmoi file; preserve machine-local overrides |
| `bin/*` | `~/.bin/*` | rcm | migrate as executable files; verify modes |
| `git_template/` | `~/.git_template/` | rcm | defer: empty placeholder only; migrate when functional template content exists |
| `rcrc` | `~/.rcrc` | rcm | retain during shadow phase; remove only in cleanup PR |
| `Brewfile`, `Brewfile.linux`, `Brewfile.personal`, `Brewfile.work` | `~/.Brewfile*` | rcm | preserve these links while `HOMEBREW_BUNDLE_FILE` depends on them |
| `docs/`, `Justfile`, `README.md`, `CHANGELOG.md` | repository-only | rcm excludes | remain outside `home/` |

## Ownership rules

- `home/` is the only future chezmoi source state. Repository metadata,
  recipes, tests, and changelog files stay at the repository root.
- The private repository remains the owner of private Claude configuration and
  secrets; none of it is copied into this public source tree.
- Identity-bearing Git configuration remains private. Public Git defaults may
  be extracted later, but `user.*`, signing keys, and account-specific
  credential wiring must be supplied by the private overlay.
- Application-owned mutable state is not imported until its reconciliation
  behavior has a dedicated fixture.
- Empty directories and marker-only trees are not materialized in `home/` just
  to satisfy chezmoi; they remain rcm-owned until they contain functional
  content that can be tested.
- Every migration PR must update this table and provide a disposition for any
  target not yet represented in chezmoi.

## Evidence still required

1. Capture the live rcm target map on each supported platform.
2. Record backup and rollback commands before changing `just link` or
   `just setup`.

## Canary evidence

The `tmux.conf`, `zshrc`, `zshenv`, `zprofile`, `zlogin`, `zsh/`, `psqlrc`,
`gitignore`, `agignore`, `editorconfig`, and four
public executable slices and Ghostty config are represented under `home/`, with
executable-mode checks. On 2026-08-07 they rendered byte-for-byte
identical to the current rcm sources in an isolated HOME, and a second
`chezmoi apply` produced no changes. This is shadow evidence only; rcm remains
the active deployment owner until the complete target set has equivalent
evidence.

Existing machines should run `just cleanup-retired-iterm` once after updating;
it removes only the retired `~/.iterm2/com.googlecode.iterm2.plist` symlink.
