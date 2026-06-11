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
# Link/update dotfiles after changes (uses DOTFILES_DIRS from rcrc)
rcup

# Install macOS packages (auto-selects the work/personal overlay)
brew bundle --file=~/Workspace/tgautier/dotfiles/Brewfile

# Declare this Mac's profile (work|personal); absent defaults to work
just set-profile personal

# Install Linux packages
brew bundle --file=~/Workspace/tgautier/dotfiles/Brewfile.linux

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

`zshenv` → `zprofile` → `zshrc` → `zsh/zaliases` + `zsh/zcompletion`

Custom functions live in `zsh/functions/` and are autoloaded. Scripts in `bin/` are added to PATH automatically.

### Tool Version Management (mise)

Runtime versions are managed by **mise** via `config/mise/config.toml` (symlinked to `~/.config/mise/config.toml`). Mise is activated in `zshrc`. Pinned tools include node, python, ruby, go, erlang, elixir, deno, helm, and yarn.

### Performance

Shell startup is optimized with caching (kubectl context, environment vars). Avoid adding slow operations to shell init files.

### CI / Linting

The `Justfile` defines local CI targets mirroring the GitHub Actions workflow:

- `just ci` — runs all checks (shell, markdown, Brewfile, mise)
- `just lint-shell` — shellcheck on `bin/*` and zsh files
- `just setup` — full machine bootstrap (profile, packages, symlinks, runtimes, hooks, tools)

### tmux

`tmux.conf` (symlinked to `~/.tmux.conf` by rcm). Prefix is `C-a`, vi-style bindings, platform-aware clipboard. See `docs/tmux.md` for the full cheat sheet.

### Git Configuration

- SSH key signing via 1Password (`op-ssh-sign`)
- `gh` credential helper for GitHub HTTPS
- Rebase-based pulls with fast-forward only

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

- `docs/tmux.md` — configuration overview, cheat sheet, troubleshooting
