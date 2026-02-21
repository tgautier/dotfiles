---
allowed-tools: Bash, Read, Glob, Grep
description: Commit, push, create/update PR, and optionally merge
user-invocable: true
---

# Commit, Push, and PR

Follow these steps in order:

## 1. Assess current state

Run these in parallel:
- `git status` (no -uall flag)
- `git diff HEAD --stat` (all changes vs last commit)
- `git log --oneline -5` (recent commit style)
- `git branch --show-current` (current branch)
- `git rev-parse --abbrev-ref @{upstream} 2>/dev/null || echo "no-upstream"` (tracking info)

## 2. Clean up stale branch or create new one

- If on a feature branch, check if its PR was already merged/closed: `gh pr view --json state 2>/dev/null`
  - If `state` is `MERGED` or `CLOSED`: warn the user if there are uncommitted changes, then switch to main, pull, delete the stale branch, and create a fresh feature branch from main
- If the current branch is `main` or `master`, create a new feature branch before committing
- Derive the branch name from the changes (e.g. `feat/add-libpq`, `fix/shell-startup`)
- Use the format: `type/short-description` (lowercase, hyphens, no spaces)
- Checkout the new branch: `git checkout -b <branch-name>`
- If already on a feature branch with no merged/closed PR, skip this step

## 3. Stage and commit

- If there are no changes to commit and nothing unpushed, inform the user and stop
- If there are no changes to commit but there are unpushed commits, skip to step 4
- Stage all relevant changed files (avoid secrets, .env, credentials)
- Write a conventional commit message: `type(scope): description`
- Do NOT include `Co-Authored-By` or mention Claude/AI
- Keep first line under 72 characters
- Use a HEREDOC for the commit message

## 4. Sync, rebase, and push

- Fetch latest: `git fetch origin`
- Check if branch needs rebasing onto main: `git merge-base --is-ancestor origin/main HEAD` (exit 0 = clean)
- If rebase is needed: `git rebase origin/main`
  - If rebase hits conflicts: abort, inform the user of the conflicting files, and stop
- Push with `--force-with-lease`, adding `-u` if no upstream is set
  - If `--force-with-lease` rejects the push (remote has unknown commits): stop and inform the user
  - If push fails because the remote branch was deleted: re-push with `-u` to recreate it
- Never push directly to `main` or `master`

## 5. Create or update PR

- Check if an **open** PR exists: `gh pr view --json number,url,state 2>/dev/null`
- If a PR exists and `state` is `OPEN`: report its URL, do NOT create a new one
- If no open PR exists: create one with `gh pr create` using this format:

```
gh pr create --title "short title" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points>

## Test plan
- [ ] Tests pass locally
- [ ] CI passes

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- The PR title should be short (under 70 chars) and reflect all commits on the branch vs main
- The summary should cover ALL commits in the branch, not just the latest
- Return the PR URL when done

## 6. Merge (only if user explicitly asks to merge)

- Always use squash merge: `gh pr merge <number> --squash`
- Never use `--merge` or `--rebase` strategies
- If merge fails due to failing checks: inform the user and stop
- After merge completes:
  1. Switch back to main: `git checkout main`
  2. Pull latest: `git pull`
  3. Delete the local feature branch: `git branch -D <branch-name>` (squash merge requires `-D` since commit hashes differ)
