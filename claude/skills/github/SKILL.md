---
name: github
description: |
  GitHub PR & review skill powered by GitHub MCP Server.
  Use when: creating PRs, updating PRs, requesting Copilot reviews, processing review comments,
  merging PRs, or reviewing PRs as a code reviewer.
  Covers: PR lifecycle, automated Copilot reviews, outbound code review, merge gates.
user-invocable: true
---

# GitHub PR & Review Skill

All GitHub interactions use the GitHub MCP Server tools when available, with `gh` CLI as fallback.

## PR Lifecycle

### Check for existing PR

Before creating a PR, check for an existing one:

- **MCP**: `get_me` to identify the current user, then `list_pull_requests` or `get_pull_request`
- **Fallback**: `gh pr view --json number,url,state 2>/dev/null`
- Check `state` is `OPEN` before acting — closed/merged PRs are also returned

### Create a PR

- **MCP**: `create_pull_request` with `owner`, `repo`, `head` (branch), `base` (main), `title`, `body`
- **Fallback**:

  ```sh
  gh pr create --title "short title" --body "$(cat <<'EOF'
  ## Summary
  <1-3 bullet points>

  ## Test plan
  - [ ] Tests pass locally
  - [ ] CI passes
  EOF
  )"
  ```

- PR title under 70 chars, reflecting all commits on the branch vs main
- Summary covers ALL commits in the branch, not just the latest
- Test plan reflects the current state (check off completed items, add new items for new commits)

### Update a PR

After every push to a branch with an open PR:

- **MCP**: `update_pull_request` with updated `title`, `body`
- **Fallback**: `gh pr edit` with `--title` and `--body`
- Title, summary, and test plan must reflect ALL commits on the branch vs main

## Automated Reviews (Copilot)

### Request a review

After each push:

- **MCP**: `request_copilot_review` with `owner`, `repo`, `pullNumber`
- **Fallback**:

  ```sh
  gh api --method POST repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers \
    -f 'reviewers[]=copilot-pull-request-reviewer[bot]' 2>/dev/null || true
  ```

- If the request fails (Copilot not enabled, already requested), continue — an auto-triggered review may still arrive

### Wait for CI and Copilot review

After requesting a review, **always** wait for both CI and the Copilot review to complete before proceeding. Never skip this step.

1. **CI**: run `gh pr checks <number> --repo {owner}/{repo} --watch` to block until all check runs finish. The MCP `get_status` method only reads legacy commit statuses, not GitHub Actions check runs — do not use it for CI status.
2. **Copilot review**: poll using **MCP** `get_pull_request_reviews`, checking for a review authored by `copilot-pull-request-reviewer[bot]`. Poll every 30 seconds, up to 10 attempts (5 minutes). **Fallback** (if MCP is unavailable):

   ```sh
   for i in $(seq 1 10); do
     review_state=$(gh api graphql -f query='query { repository(owner: "OWNER", name: "REPO") {
       pullRequest(number: <PR_NUMBER>) { reviews(last: 1) { nodes { author { login } state } } } } }' \
       --jq '.data.repository.pullRequest.reviews.nodes[] | select(.author.login == "copilot-pull-request-reviewer[bot]") | .state' 2>/dev/null)
     if [ -n "$review_state" ]; then break; fi
     sleep 30
   done
   ```

3. If the review has not appeared after 5 minutes, inform the user and ask whether to continue without it
4. Once the review appears, read review comments below

### Read review comments

- **MCP**: `get_pull_request_reviews` then `get_pull_request_comments` to get review threads
- **Fallback** (GraphQL — needed for comments on outdated diff lines):

  ```sh
  gh api graphql -f query='query { repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: <PR_NUMBER>) { reviewThreads(first: 100) { nodes {
      id isResolved comments(first: 5) { nodes { body author { login }
        pullRequestReview { databaseId } } } } } } } }'
  ```

- Filter to unresolved threads from Copilot reviewers only (`copilot-pull-request-reviewer[bot]` or `copilot-pull-request-reviewer`)
- Track the most recent Copilot review ID (max `pullRequestReview.databaseId`); only skip threads from earlier rounds if they have already been accepted and fixed, or replied to with an explanation
- Never process human reviewer threads automatically

### Accept or reject each comment

- **Accept**: fix the issue, then resolve the thread
- **Reject**: reply explaining why, then resolve the thread

### Resolve threads

- No dedicated MCP method for resolving individual threads; use the GraphQL fallback
- **GraphQL fallback**:

  ```sh
  gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "THREAD_ID"}) { thread { isResolved } } }'
  ```

### Reply to rejected threads

- **MCP**: `add_pull_request_review_comment_reply` with the reason
- **Fallback**:

  ```sh
  gh api repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies -f body='Reason for not accepting'
  ```

### Review-fix cycle

After processing all comments from a Copilot review:

1. Resolve all accepted/rejected threads
2. Commit the fixes
3. Push (triggers the standard push workflow — update PR description, request new Copilot review)
4. Read the new review and process any new comments
5. Repeat until the review comes back clean (no new comments)

- **3-round cap**: if the reviewer keeps finding issues after 3 rounds, inform the user and let them decide
- Never skip re-requesting the review — every push that fixes review comments must trigger a fresh Copilot review

## Outbound PR Reviewing

Triggered by: `review this pr`, `code review`, or a PR URL.

### Fetch PR context

- **MCP**: `get_pull_request` with `get_diff`, `get_commits`, `get_comments`
- Understand the full scope: all commits, changed files, existing discussion

### Review criteria

- **Functionality**: correctness, edge cases, error handling
- **Readability**: naming, structure, complexity
- **Style**: consistency with codebase conventions
- **Performance**: unnecessary allocations, N+1 queries, missing indexes
- **Security**: injection, auth, data exposure
- **Testing**: coverage, edge cases, test quality
- **PR quality**: title, description, commit messages

### Findings taxonomy

Categorize each finding: `blocker` | `important` | `nit` | `suggestion` | `question` | `praise`

### Post the review

Two-stage process:

1. Generate review locally — show the user all findings before posting
2. Add inline comments via `add_comment_to_pending_review` to a pending review
3. After user approval, submit via **MCP**: `create_pull_request_review` with `event` (`APPROVE`, `REQUEST_CHANGES`, `COMMENT`)

## Merge Gates

Before merging, verify all gates pass:

1. **Zero unresolved threads** — check via `get_pull_request_comments` or GraphQL:

   ```sh
   gh api graphql -f query='query { repository(owner: "OWNER", name: "REPO") {
     pullRequest(number: <PR_NUMBER>) { reviewThreads(first: 100) { nodes { id isResolved } } } } }' \
     --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length'
   ```

   If the count is not `0`, stop and resolve remaining threads first

2. **All test plan items checked** — never merge with unchecked items. If an item cannot be completed, remove it with an explanation or ask the user
3. **CI passes** — use `gh pr checks <number> --repo {owner}/{repo} --watch` to block until all checks complete. The MCP `get_status` method only reads legacy commit statuses, not GitHub Actions check runs, so it will miss CI results
4. **PR still OPEN** — confirm immediately before merging
5. **All todo list tasks completed** — never merge with pending or in-progress items

### Execute merge

- **MCP**: `merge_pull_request` with `owner`, `repo`, `pullNumber`, `merge_method: "squash"`
- **Fallback**: `gh pr merge <number> --squash`
- If merge fails due to failing checks: inform the user and stop

### Post-merge cleanup

1. Switch to main: `git checkout main`
2. Pull latest: `git pull`
3. Delete the remote branch: `git push origin --delete <branch>` (skip if already deleted by GitHub)
4. Delete the local branch: `git branch -D <branch>` (squash merge requires `-D` since commit hashes differ)

## Shell Compatibility

For any `gh` CLI fallback commands that use jq, reference `claude/rules/shell.md`:

- Never use `!=` in jq filters — use `== ... | not` instead
- zsh history expansion corrupts `!` even inside single quotes
