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
- **Every push requires a review cycle** — run `roborev review --branch --agent <agent>` for each configured agent (check `.roborev.toml` and `/roborev` for the current agent list). Review findings, fix or defer per user decision. This is not optional and not just for the first push — every push triggers a review
- **Roborev gate** — enforced by a PreToolUse hook on `git push` and `gh pr merge`. The hook blocks when: reviews are missing for the branch, reviews are still running/queued, or all reviews failed (zero coverage). Only allows through when at least one review is `done`. If blocked, check status with `roborev list`
- Fetch latest before pushing: `git fetch origin`
- Rebase onto main if needed — check with `git merge-base --is-ancestor origin/main HEAD` (exit 0 = clean)
  - If rebase hits conflicts: abort, inform the user of the conflicting files, and stop
- Push with `--force-with-lease` — the safety net for remote divergence; don't add redundant pulls before it
  - Add `-u` if no upstream is set
  - If `--force-with-lease` rejects (remote has unknown commits): stop and inform the user
  - If push fails because the remote branch was deleted: re-push with `-u` to recreate it
- After every push, if no PR exists for the branch, create one with `gh pr create` (include issue refs, test plan, summary per `/project-management`)
- After every push to a branch with an open PR, update the PR title and body to reflect ALL commits on the branch vs main — use `gh pr edit`. Keep the PR format (summary bullets, test plan checklist, issue references)
- For merging, verify all merge gates (below), then `gh pr merge <number> --squash`

## Issue linking

- Each PR should reference at least one GitHub issue
- Multi-concern PRs: each distinct fix or feature gets its own issue
- Use `Fixes #N` (auto-closes on merge) or `Addresses #N` (no auto-close) in the PR body
- If work addresses something not yet tracked, create the issue before or at PR time
- Branch names may include the issue number: `fix/42-shell-startup`

## Merge strategy

- Always squash merge — never use merge or rebase strategies
- Post-merge cleanup: switch to main, pull, delete the remote branch (`git push origin --delete <branch>`), delete local branch (`git branch -D <branch>`)

## Merge gates

Before merging any PR — and when assessing whether a PR is mergeable — **all** of these must be true. Run the full checklist even for status questions like "is this ready?":

- Zero unresolved review threads
- **Roborev reviews complete** — run `roborev list` and verify: at least one review is `done`, no reviews are `running` or `queued`, and `failed` reviews are acceptable only alongside a `done` review. If reviews are missing, trigger them. The PreToolUse hook enforces this at push/merge time, but you must also check proactively when reporting merge readiness
- **Test plan complete** — read the PR body and verify every test plan item is checked (`[x]`). If any item is unchecked, run the verification yourself or ask the user. Never merge with unchecked items. If an item cannot be verified (e.g., requires manual testing), ask the user before merging
- CI passes — use `gh pr checks <number> --repo {owner}/{repo} --watch` to confirm
- PR is still in `OPEN` state
- All session todos completed — never merge with pending or in-progress task items
- PR body is up to date — check off verified test plan items (`[x]`), update summary/title if commits changed. Do this via `gh pr edit` **before** merging, not after

## Principles

- Prevent problems, don't recover from them — design workflows so errors can't happen rather than adding complex recovery logic
- Stop and inform the user on failures — rebase conflicts, rejected pushes, failing checks. Never auto-resolve or retry blindly.
