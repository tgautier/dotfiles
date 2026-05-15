# Dotfiles Repository Conventions

Cross-platform personal dotfiles for macOS, Linux, and WSL2, managed with rcm (Thoughtbot's dotfile manager). Symlinks are created via `rcup`, configured in `rcrc`. The global Claude Code config (rules, skills, hooks) lives in the companion private repo `dotfiles-private` and is NOT in this tree.

## Hard Invariants

Flag violations of these as blockers:

1. **Secrets**: never commit credentials, tokens, API keys, or secrets. This repo is public on GitHub. The only exception is `dotfiles-private` (a separate private repo).
2. **Personal/sensitive content**: never include PII, employer name, colleague names, broker/financial figures, internal product/project names, or memory-file references that hint at sensitive content. Examples and placeholders count. This repo is public.
3. **Shell compatibility**: Claude Code's Bash tool passes through zsh, which corrupts `!` to `\!` in file content. Files must not contain `\!` — flag any occurrence as corruption.
4. **Cross-platform**: any shell, tmux, or tool config change must consider macOS, Linux, and WSL2. Guard platform-specific code with `$PLATFORM` checks (set in `zshenv`). Brewfile edits must be mirrored in `Brewfile.linux` for CLI tools.
5. **Project-local rule** (`.claude/rules/brewfile.md`): dual-Brewfile sync + alphabetical sorting inside sections.

## Cross-Platform Discipline

This repo targets macOS, Linux, and WSL2. Every change must consider all three:

- Shell config: guard platform-specific code with `$PLATFORM` checks
- Brewfiles: edit both `Brewfile` (macOS) and `Brewfile.linux` for CLI tools. Keep alphabetical order within sections.
- tmux: use `if-shell` platform detection for OS-specific commands (clipboard, terminfo)
- Never assume macOS-only tools exist (`pbcopy`, `open`) — provide WSL (`clip.exe`) and Linux (`xclip`) alternatives

## Commit Conventions

- Conventional commit format: `type(scope): description`
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`
- First line under 72 characters
- Never mention Claude, AI, or LLM in commit messages, PR titles, or PR bodies
- Never include `Co-Authored-By` lines mentioning Claude or any AI

## What Not to Flag

- Shell scripts using `jq` for JSON parsing — `jq` is expected to be available on macOS/Linux
- Brewfile lines that look long — keep them as written, alphabetically sorted within their section
