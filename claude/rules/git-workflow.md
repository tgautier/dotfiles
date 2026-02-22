# Git Workflow

## Branching

- If on `main` or `master`, create a new feature branch before committing
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
- Fetch latest before pushing: `git fetch origin`
- Rebase onto main if needed — check with `git merge-base --is-ancestor origin/main HEAD` (exit 0 = clean)
  - If rebase hits conflicts: abort, inform the user of the conflicting files, and stop
- Push with `--force-with-lease` — the safety net for remote divergence; don't add redundant pulls before it
  - Add `-u` if no upstream is set
  - If `--force-with-lease` rejects (remote has unknown commits): stop and inform the user
  - If push fails because the remote branch was deleted: re-push with `-u` to recreate it
- After every push to a branch with an open PR, invoke the `/github` skill to update the PR and request a Copilot review

## Merge strategy

- Always squash merge — never use merge or rebase strategies
- Post-merge cleanup is handled by the `/github` skill

## Principles

- Prevent problems, don't recover from them — design workflows so errors can't happen rather than adding complex recovery logic
- Stop and inform the user on failures — rebase conflicts, rejected pushes, failing checks. Never auto-resolve or retry blindly.
