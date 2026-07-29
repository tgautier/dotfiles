# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ This repo is PUBLIC

Every `Write`, `Edit`, and `git add` in this working tree ships to a public GitHub repo. Before any such action, apply the `public-repo-hygiene` rule (auto-loaded from `~/.claude/rules/public-repo-hygiene.md` via rcm symlinks):

1. Read the sensitive-terms list at `~/.claude/sensitive-terms.md` (rcm symlink to `dotfiles-private/claude/sensitive-terms.md` — portable across macOS, Linux, WSL)
2. Scan the new/changed content against that list AND the categorical examples in the rule (PII, employer, financial, colleagues, internal references, session context)
3. Sensitive content → route to `dotfiles-private` or redact to neutral placeholders. **Never** rely on "I'll catch it at commit time" — scan on every write

Personal financial workflows, vault-specific content, employer-tied notes, colleague names, and the global Claude Code config (rules, skills, hooks) all live in `dotfiles-private`, never here.

## Repository Overview

Cross-platform personal dotfiles for macOS and Linux/WSL2, managed with **rcm** (Thoughtbot's dotfile manager). Symlinks are created via `rcup`, configured in `rcrc`. A companion private repo (`dotfiles-private`) is merged via `DOTFILES_DIRS` in `rcrc`; it hosts plaintext shell secrets, personal workflow config, and the global Claude Code config.

## Key Commands

```sh
# Re-apply the rcm symlinks (uses DOTFILES_DIRS from rcrc). Required for an
# edit to a symlinked dotfile — gitconfig, zshrc, zshenv, tmux.conf — to take
# effect on this machine. `just update` does NOT re-link. Prefer this over a
# bare `rcup`, which finds the same config only once ~/.rcrc is itself linked.
# Run it from this checkout — ~/.justfile points at the private repo's justfile
just link

# Install packages (auto-selects the platform Brewfile and, on macOS, the
# work/personal overlay). Never run raw `brew install` / `brew bundle` —
# packages always flow through the just recipes; raw `brew bundle` is only
# for first bootstrap, before `just` itself is installed
just setup

# Declare this Mac's profile (work|personal) — required before brew bundle;
# interactive `just setup` prompts for it on first run (default: work)
just set-profile personal

# Run all linters locally (same as CI)
just ci

# Update everything (brew, mas, mise, rust)
just update

# Bootstrap a machine: profile, packages, symlinks, runtimes, hooks, tools
just setup
```

## Cross-Platform Discipline

This repo targets **three platforms**: macOS, Linux, and WSL2. Every change must consider all three:

- Shell config: guard platform-specific code with `$PLATFORM` checks (set in `zshenv`)
- Brewfiles: shared CLI tools go in **both** `Brewfile` and `Brewfile.linux`; macOS apps that belong to only one Mac go in `Brewfile.work` / `Brewfile.personal` (see `.claude/rules/brewfile.md`)
- tmux: use `if-shell` platform detection for OS-specific commands (clipboard, terminfo)
- Never assume macOS-only tools exist (`pbcopy`, `open`) — provide WSL (`clip.exe`) and Linux (`xclip`) alternatives

## Architecture

### Platform Detection

`zshenv` detects the platform (`macos`, `wsl`, `linux`) into `$PLATFORM`. Platform-specific logic is spread across `zshenv`, `zprofile`, `zsh/zcompletion`, and `zshrc`. Always guard platform-specific code with `$PLATFORM` checks.

### Shell Configuration Load Order

`zshenv` → `zprofile` → `zshrc` (sources `zsh/zaliases` + `zsh/zcompletion`) →
`zlogin`. The last is a pure optimisation — it precompiles `~/.zcompdump` in the
background for the *next* login. `README.md` → Shell load order has the
per-file detail; don't duplicate that list here.

Custom functions live in `zsh/functions/`, which `zsh/zcompletion` prepends to
`fpath` and autoloads. Scripts in `bin/` are linked by rcm into `~/.bin`, which
`zshenv` puts on `PATH`.

### Tool Version Management (mise)

Runtime versions are managed by **mise** via `config/mise/config.toml` (symlinked to `~/.config/mise/config.toml`). Mise is activated in `zshrc`. Pinned tools include node, python, ruby, go, erlang, elixir, deno, helm, and yarn.

### Performance

Shell startup is optimized with caching (kubectl context, environment vars). Avoid adding slow operations to shell init files.

### CI / Linting

The `Justfile` defines local CI targets mirroring the GitHub Actions workflow:

- `just ci` — runs every lint (the individual targets are listed in
  `README.md`'s CI / Linting table)
- `just setup` — full machine bootstrap (profile, packages, symlinks, runtimes, hooks, tools)

Duplicating that target list here has drifted from the table before — keep the
single enumeration in `README.md`.

### tmux

`tmux.conf` (symlinked to `~/.tmux.conf` by rcm). Prefix is `C-a`, vi-style bindings, platform-aware clipboard. See `docs/tmux.md` for the full cheat sheet.

### Git Configuration

- SSH key signing via 1Password (`op-ssh-sign`)
- `gh` credential helper for GitHub HTTPS — declared as `!gh auth git-credential`,
  resolved via `PATH`. Never hardcode an absolute path here: `gh` comes from
  Homebrew on every platform — `/opt/homebrew/bin` on macOS,
  `/home/linuxbrew/.linuxbrew/bin` on Linux/WSL (`Brewfile.linux` declares
  `brew "gh"`, and `zshenv` puts that directory on `PATH`) — never `/usr/bin`,
  and this file is symlinked to all three platforms. Caveat: being PATH-resolved,
  git invoked from
  a minimal-`PATH` context on macOS (a GUI client launched from Finder,
  `launchd`, `cron`) needs `/opt/homebrew/bin` on its `PATH` for the helper to
  resolve
- Rebase-based pulls with fast-forward only
- Isolated worktrees go in `.claude/worktrees/<name>` (per the global
  `git-conventions.md` §Branching). That path is gitignored **and** excluded from
  the markdownlint globs, so a nested checkout can neither be swept into a commit
  nor linted as this branch's content

## Project-Local Rules

`.claude/rules/` contains rules specific to this repo (not symlinked to other projects):

| Rule | Scope | Purpose |
| --- | --- | --- |
| `brewfile.md` | `Brewfile`, `Brewfile.work`, `Brewfile.personal`, `Brewfile.linux`, `Justfile` | Brewfile sync, work/personal overlays, alphabetical sorting, native-installer pattern (`just setup` as single source of truth) |

Global Claude Code rules and skills (commit conventions, task lifecycle, code-planning, language-specific patterns, etc.) live in `dotfiles-private/claude/` and auto-load via the rcm symlinks at `~/.claude/`. Edit them there.

## Changelog

`CHANGELOG.md` tracks notable changes. This is a rolling repo with no tagged
releases, so entries are **date-based** (`## [YYYY-MM-DD]`), newest first, in
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. Any
user-visible change (new tool, version bump, config behavior, removed feature)
adds an entry under the current date — group it by `Added` / `Changed` /
`Removed` / `Fixed` and reference the PR. The `[Unreleased]` section holds
entries not yet dated.

## Documentation

Detailed guides live in `docs/`:

- `docs/homebrew.md` — update flow, cask-upgrade recovery, `just update` troubleshooting
- `docs/tmux.md` — configuration overview, cheat sheet, troubleshooting
