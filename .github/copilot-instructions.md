# Dotfiles Repository Conventions

Cross-platform personal dotfiles for macOS, Linux, and WSL2, managed with rcm (Thoughtbot's dotfile manager). Symlinks are created via `rcup`, configured in `rcrc`.

## Config System

Two-tier model for organizing Claude Code instructions:

- **Rules** (`claude/rules/`): global, always loaded. Constraints and invariants that must hold across all projects. Symlinked from this repo to `~/.claude/rules/` by rcm.
- **Skills** (`claude/skills/<name>/SKILL.md`): on-demand, invoked via `/name`. Reusable methodology and checklists.
- **Project-local rules** (`.claude/rules/`): specific to this repo, not symlinked elsewhere.

### Frontmatter conventions

Skill files (`SKILL.md`) require YAML frontmatter with: `name`, `description`, `version` (semver, unquoted), `date`, `user-invocable` (boolean). This is required metadata, not boilerplate.

Rules may include `paths:` frontmatter for auto-loading only when working on matching files. Rules without `paths:` apply globally.

### Naming

- Rules: `kebab-case.md` — descriptive noun or noun-phrase
- Skills: `kebab-case/SKILL.md` — verb-phrase or domain name
- Path-scoped rules use a layer prefix (`domain-`, `frontend-`, `rust-`, `db-`)

## Hard Invariants

Flag violations of these as blockers:

1. **Secrets**: never commit credentials, tokens, API keys, or secrets. This repo is public on GitHub. The only exception is `dotfiles-private` (a separate private repo).
2. **Shell compatibility**: Claude Code's Bash tool passes through zsh, which corrupts `!` to `\!` in file content. Rule and skill `.md` files must not contain `\!` — flag any occurrence as corruption.
3. **One concern per file**: each rule covers exactly one topic. If two unrelated topics exist in one file, flag for split.
4. **80-line signal**: rules over 80 lines likely cover too much. Flag for review. Skills are allowed to be longer.
5. **Cross-references**: if file A references file B, verify B exists. Broken cross-refs are blockers.
6. **Hook exit codes**: PreToolUse hooks in `claude/hooks/` must use `exit 2` (block with reason on stderr) or `exit 0` (allow). Never `exit 1` for intentional blocks.
7. **No project-specific references**: global rules and skills must never reference project-local paths (`.claude/rules/`, specific source paths). Use generic language like "check the project's CLAUDE.md".

## Cross-Platform Discipline

This repo targets macOS, Linux, and WSL2. Every change must consider all three:

- Shell config: guard platform-specific code with `$PLATFORM` checks (set in `zshenv`)
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

- YAML frontmatter in `SKILL.md` files — it is required metadata
- Files over 200 lines in `claude/skills/` — skills are allowed to be longer than rules
- Shell scripts using `jq` for JSON parsing — `jq` is expected to be available on macOS/Linux
- Files excluded from markdownlint: `claude/skills/**` (skills have their own formatting conventions)
