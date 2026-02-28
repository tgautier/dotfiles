# Git Conventions

## Branching

- Never commit directly to `main` or `master` — always create a feature branch first
- If on `main` or `master` with uncommitted changes, create a branch before committing
- Branch naming: `type/short-description` (lowercase, hyphens, no spaces)
- Derive the branch name from the changes (e.g. `feat/add-libpq`, `fix/shell-startup`)
- Detect stale branches early — PRs can be merged outside your control (GitHub UI, standalone `gh`); check before committing on top
- If on a feature branch, check if its PR was already merged/closed: `gh pr view --json state 2>/dev/null`
  - If `state` is `MERGED` or `CLOSED`: warn the user about uncommitted changes, switch to main, pull, delete the stale branch (`git branch -D`), and create a fresh branch from main

## Commit conventions

- Never mention Claude, AI, or LLM anywhere in git output — commit messages, PR titles, PR bodies, branch names
- Never include `Co-Authored-By` lines mentioning Claude or any AI
- Never add "Generated with Claude Code" or similar footers to PRs
- Use conventional commit format: `type(scope): description`
  - `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`
- Keep the first line under 72 characters
- Only commit when explicitly asked

## Pushing

- Never push directly to `main` or `master`
- **Multi-agent review before pushing** — run `roborev review --branch` with multiple agents (copilot, codex, gemini) before the first push. Read all findings, fix verified issues, commit fixes. See `/roborev` for the full workflow
- **Roborev gate** — enforced by a PreToolUse hook on `git push` and `gh pr merge`. The hook blocks when reviews are running or have unaddressed failures. If blocked, fix findings (`roborev fix` or `roborev refine`) before retrying
- Fetch latest before pushing: `git fetch origin`
- Rebase onto main if needed — check with `git merge-base --is-ancestor origin/main HEAD` (exit 0 = clean)
  - If rebase hits conflicts: abort, inform the user of the conflicting files, and stop
- Push with `--force-with-lease` — the safety net for remote divergence; don't add redundant pulls before it
  - Add `-u` if no upstream is set
  - If `--force-with-lease` rejects (remote has unknown commits): stop and inform the user
  - If push fails because the remote branch was deleted: re-push with `-u` to recreate it
- After every push, if no PR exists for the branch, invoke the `/github` skill to create one (handles issue linking, test plan, PR format)
- After every push to a branch with an open PR, update the PR title and body to reflect ALL commits on the branch vs main — use MCP `update_pull_request` or `gh pr edit`. Keep the PR format from the `/github` skill (summary bullets, test plan checklist, issue references)
- For merging, invoke the `/github` skill (handles merge gates, squash merge, post-merge cleanup)

## Issue linking

- Each PR should reference at least one GitHub issue
- Multi-concern PRs: each distinct fix or feature gets its own issue
- Use `Fixes #N` (auto-closes on merge) or `Addresses #N` (no auto-close) in the PR body
- If work addresses something not yet tracked, create the issue before or at PR time
- Branch names may include the issue number: `fix/42-shell-startup`

## Merge strategy

- Always squash merge — never use merge or rebase strategies
- Post-merge cleanup is handled by the `/github` skill

## Merge gates

Before merging any PR, **all** of these must be true:

- Zero unresolved review threads
- **Roborev gate** passes — enforced by PreToolUse hook (blocks `gh pr merge` with unaddressed findings)
- All test plan items checked — never merge with unchecked items. If an item cannot be verified (e.g., requires manual testing), remove it with an explanation or ask the user before merging
- CI passes — use `gh pr checks <number> --repo {owner}/{repo} --watch` to confirm
- PR is still in `OPEN` state
- All session todos completed — never merge with pending or in-progress task items
- PR body is up to date — check off verified test plan items (`[x]`), update summary/title if commits changed. Do this via `gh pr edit` **before** merging, not after

## Principles

- Prevent problems, don't recover from them — design workflows so errors can't happen rather than adding complex recovery logic
- Stop and inform the user on failures — rebase conflicts, rejected pushes, failing checks. Never auto-resolve or retry blindly.
