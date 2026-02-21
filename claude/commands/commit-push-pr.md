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
EOF
)"
```

- The PR title should be short (under 70 chars) and reflect all commits on the branch vs main
- The summary should cover ALL commits in the branch, not just the latest
- Return the PR URL when done

## 6. Wait for Codex and Copilot reviews

After creating or pushing to a PR, wait for both the OpenAI Codex review and the GitHub Copilot review.

### 6a. Wait for Codex review

1. First, check for a usage-limit comment from Codex:
   ```
   gh api repos/{owner}/{repo}/issues/{pr_number}/comments --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]") | .body'
   ```
   - If the comment contains "usage limits", report "Codex review skipped (usage limit reached)" and continue to the next step — do not poll

2. Poll for the Codex reaction on the PR (from `chatgpt-codex-connector[bot]`):
   ```
   gh api repos/{owner}/{repo}/issues/{pr_number}/reactions --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]") | .content'
   ```
   - Poll every 15 seconds, up to 5 minutes
   - `eyes` (👀) means review is in progress — keep waiting
   - `+1` (👍) means review passed with no issues
   - If no reaction appears after 5 minutes, inform the user and continue

3. Check for review comments from Codex:
   ```
   gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]")'
   gh api repos/{owner}/{repo}/pulls/{pr_number}/comments --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]")'
   ```

4. If Codex left review comments or requested changes:
   - Read each comment carefully
   - Fix the issues locally
   - Resolve the addressed review threads via GraphQL:
     ```
     # List unresolved Codex threads
     gh api graphql -f query='query { repository(owner: "{owner}", name: "{repo}") { pullRequest(number: {pr_number}) { reviewThreads(first: 100) { nodes { id isResolved comments(first: 1) { nodes { author { login } } } } } } } }' --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false) | select(.comments.nodes[0].author.login == "chatgpt-codex-connector[bot]") | .id'
     # Resolve each thread
     gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "THREAD_ID"}) { thread { isResolved } } }'
     ```
   - Commit with a descriptive message (e.g. `fix(scope): address Codex review feedback`)
   - Push (go back to step 4 for sync/push)
   - Wait for the new Codex review (repeat this step)

5. If Codex gave 👍 with no comments: report "Codex review passed" and continue

### 6b. Wait for Copilot review

Request and wait for the GitHub Copilot code review:

1. Request the review via API:
   ```
   gh api --method POST repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers -f 'reviewers[]=copilot-pull-request-reviewer[bot]'
   ```
   - If this fails (e.g. Copilot not enabled for the repo), report "Copilot review skipped (not available)" and continue

2. Poll for the Copilot review:
   ```
   gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --jq '.[] | select(.user.login == "copilot-pull-request-reviewer[bot]") | {state: .state, body: .body}'
   ```
   - Poll every 15 seconds, up to 5 minutes
   - If no review appears after 5 minutes, inform the user and continue
   - Copilot always leaves a "COMMENTED" review (never "APPROVED" or "CHANGES_REQUESTED")

3. Check for inline review comments from Copilot:
   ```
   gh api repos/{owner}/{repo}/pulls/{pr_number}/comments --jq '.[] | select(.user.login == "copilot-pull-request-reviewer[bot]") | {path: .path, line: .line, body: .body}'
   ```

4. If Copilot left inline comments with suggestions:
   - Read each comment carefully
   - Fix the issues locally
   - Resolve the addressed review threads via GraphQL:
     ```
     # List unresolved Copilot threads
     gh api graphql -f query='query { repository(owner: "{owner}", name: "{repo}") { pullRequest(number: {pr_number}) { reviewThreads(first: 100) { nodes { id isResolved comments(first: 1) { nodes { author { login } } } } } } } }' --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false) | select(.comments.nodes[0].author.login == "copilot-pull-request-reviewer[bot]") | .id'
     # Resolve each thread
     gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "THREAD_ID"}) { thread { isResolved } } }'
     ```
   - Commit with a descriptive message (e.g. `fix(scope): address Copilot review feedback`)
   - Push (go back to step 4 for sync/push)
   - Request a new Copilot review (repeat this step)

5. If Copilot review has no inline comments: report "Copilot review passed" and continue

### 6c. Handle combined review feedback

- If both Codex and Copilot left feedback, address all comments in a single commit when possible
- If either reviewer keeps finding issues after 3 rounds, inform the user and let them decide whether to continue iterating

## 7. Merge (only if user explicitly asks to merge)

- Always use squash merge: `gh pr merge <number> --squash`
- Never use `--merge` or `--rebase` strategies
- If merge fails due to failing checks: inform the user and stop
- After merge completes:
  1. Switch back to main: `git checkout main`
  2. Pull latest: `git pull`
  3. Delete the remote branch: `git push origin --delete <branch-name>` (skip if already deleted by GitHub)
  4. Delete the local feature branch: `git branch -D <branch-name>` (squash merge requires `-D` since commit hashes differ)
