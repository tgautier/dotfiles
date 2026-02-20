# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Cross-platform personal dotfiles for macOS and Linux/WSL2, managed with **rcm** (Thoughtbot's dotfile manager). Symlinks are created via `rcup`, configured in `rcrc`. A companion private repo (`dotfiles-private`) is merged via `DOTFILES_DIRS` in `rcrc`.

## Key Commands

```sh
# Link/update dotfiles after changes
rcup -d ~/Workspace/tgautier/dotfiles

# Install macOS packages
brew bundle --file=~/Workspace/tgautier/dotfiles/Brewfile

# Install Linux packages
brew bundle --file=~/Workspace/tgautier/dotfiles/Brewfile.linux
```

## Architecture

### Platform Detection
`zshenv` detects the platform (`macos`, `wsl`, `linux`) into `$PLATFORM`. Platform-specific logic is spread across `zshenv`, `zprofile`, `zsh/zcompletion`, and `zshrc`. Always guard platform-specific code with `$PLATFORM` checks.

### Shell Configuration Load Order
`zshenv` → `zprofile` → `zshrc` → `zsh/zaliases` + `zsh/zcompletion`

Custom functions live in `zsh/functions/` and are autoloaded. Scripts in `bin/` are added to PATH automatically.

### Performance
Shell startup is optimized with caching (kubectl context, environment vars). Avoid adding slow operations to shell init files.

### Git Configuration
- SSH key signing via 1Password (`op-ssh-sign`)
- `gh` credential helper for GitHub HTTPS
- Rebase-based pulls with fast-forward only

## Commit Conventions

Per `claude/rules/commits.md`:
- Conventional commit format: `type(scope): description`
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`
- First line under 72 characters
- Never include `Co-Authored-By` lines mentioning Claude or any AI
- Never mention Claude, AI, or LLM in commit messages
- Only commit when explicitly asked
