---
name: github
description: |
  GitHub PR lifecycle skill powered by GitHub MCP Server.
  Use when: creating PRs, updating PR format, or merging PRs.
  Covers: PR creation, PR format (summary, test plan, issue refs), merge gates, post-merge cleanup.
version: 1.0.0
date: 2026-02-23
user-invocable: true
---

# GitHub PR Lifecycle

All GitHub interactions use the GitHub MCP Server tools when available, with `gh` CLI as fallback.

## 1. PR Lifecycle

### Check for existing PR

Before creating a PR, check for an existing one:

- **MCP**: `get_me` to identify the current user, then `list_pull_requests` or `get_pull_request`
- **Fallback**: `gh pr view --json number,url,state 2>/dev/null`
- Check `state` is `OPEN` before acting — closed/merged PRs are also returned

### Link issues before creating or updating a PR

Before creating or updating a PR, ensure every distinct fix or feature on the branch has a corresponding GitHub issue:

1. Review all commits on the branch vs main — enumerate each distinct change
2. Check for existing issues: **MCP** `list_issues` or `search_issues`, **Fallback** `gh issue list --search "keyword"`
3. Create missing issues: **MCP** `issue_write`, **Fallback** `gh issue create --title "short title" --body "description"`
4. Reference all linked issues in the PR body using `Fixes #N` (auto-closes on merge) or `Addresses #N` (no auto-close)

If a single commit addresses multiple concerns, each concern should have its own issue.

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

## 2. Merge Gates

Before merging, verify all gates pass:

1. **Zero unresolved threads** — check via `get_pull_request_comments` or GraphQL:

   ```sh
   gh api graphql -f query='query { repository(owner: "OWNER", name: "REPO") {
     pullRequest(number: <PR_NUMBER>) { reviewThreads(first: 100) { nodes { id isResolved } } } } }' \
     --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length'
   ```

   If the count is not `0`, stop and resolve remaining threads first

2. **All test plan items checked** — never merge with unchecked items. If an item cannot be completed, remove it with an explanation or ask the user
3. **CI passes** — use `gh pr checks <number> --repo {owner}/{repo} --watch` to block until all checks complete. This is the only point where you wait for CI — never block on CI earlier in the workflow. The MCP `get_status` method only reads legacy commit statuses, not GitHub Actions check runs, so it will miss CI results
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

## 3. Shell Compatibility

For any `gh` CLI fallback commands that use jq, reference `claude/rules/shell.md`:

- Never use `!=` in jq filters — use `== ... | not` instead
- zsh history expansion corrupts `!` even inside single quotes
