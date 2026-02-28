# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Cross-platform personal dotfiles for macOS and Linux/WSL2, managed with **rcm** (Thoughtbot's dotfile manager). Symlinks are created via `rcup`, configured in `rcrc`. A companion private repo (`dotfiles-private`) is merged via `DOTFILES_DIRS` in `rcrc`.

## Key Commands

```sh
# Link/update dotfiles after changes (uses DOTFILES_DIRS from rcrc)
rcup

# Install macOS packages
brew bundle --file=~/Workspace/tgautier/dotfiles/Brewfile

# Install Linux packages
brew bundle --file=~/Workspace/tgautier/dotfiles/Brewfile.linux

# Run all linters locally (same as CI)
just ci

# Update everything (brew, mas, mise, rust)
just update

# Enable pre-commit hook and install native tools
just setup
```

## Cross-Platform Discipline

This repo targets **three platforms**: macOS, Linux, and WSL2. Every change must consider all three:

- Shell config: guard platform-specific code with `$PLATFORM` checks (set in `zshenv`)
- Brewfiles: edit **both** `Brewfile` and `Brewfile.linux` for CLI tools (see `.claude/rules/brewfile.md`)
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
- `just setup` — enables `.githooks/pre-commit`

### tmux

`tmux.conf` (symlinked to `~/.tmux.conf` by rcm). Prefix is `C-a`, vi-style bindings, platform-aware clipboard. See `docs/tmux.md` for the full cheat sheet.

### Git Configuration

- SSH key signing via 1Password (`op-ssh-sign`)
- `gh` credential helper for GitHub HTTPS
- Rebase-based pulls with fast-forward only

## Commit Conventions

Per `claude/rules/git-conventions.md` (commit conventions section):

- Conventional commit format: `type(scope): description`
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`
- First line under 72 characters
- Never include `Co-Authored-By` lines mentioning Claude or any AI
- Never mention Claude, AI, or LLM in commit messages
- Only commit when explicitly asked

## GitHub Integration

GitHub PR workflows (creating, merging) use the GitHub MCP Server (`github`, configured in `~/.claude.json` user scope). The `/github` skill (`claude/skills/github/SKILL.md`) handles PR creation and merge gates. Post-push PR updates (title/body) are done directly via `gh pr edit` per `claude/rules/git-conventions.md`.

Pre-push code reviews are handled locally by **roborev** (`/roborev` skill). The `git-conventions` rule gates pushes on roborev passing.

## Global Rules and Skills

Global rules (`claude/rules/`) are symlinked from this repo to all projects:

| Rule | Purpose |
| --- | --- |
| `git-conventions.md` | Branching, commits, push workflow, merge strategy |
| `skill-triggers.md` | Routing table — maps intents and file patterns to skills |
| `task-lifecycle.md` | How to assess, plan, implement, and verify work |
| `ci-integrity.md` | CI must reflect reality — no silencing failures |
| `secrets.md` | Never commit credentials outside dotfiles-private |
| `shell.md` | zsh `!` corruption, jq compatibility |
| `claude-config.md` | Two-tier config system (rules vs skills) |

Skills (`claude/skills/`) provide on-demand methodology invoked via `/skill-name`. Routing is defined in `skill-triggers.md`.

## Project-Local Rules

`.claude/rules/` contains rules specific to this repo (not symlinked to other projects):

| Rule | Scope | Purpose |
| --- | --- | --- |
| `brewfile.md` | `Brewfile`, `Brewfile.linux` | Dual-Brewfile sync and alphabetical sorting |

## Documentation

Detailed guides live in `docs/`:

- `docs/tmux.md` — configuration overview, cheat sheet, troubleshooting
