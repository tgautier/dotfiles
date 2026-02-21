# Git Workflow

## Branching

- If on `main` or `master`, create a new feature branch before committing
- Branch naming: `type/short-description` (lowercase, hyphens, no spaces)
- Derive the branch name from the changes (e.g. `feat/add-libpq`, `fix/shell-startup`)
- Detect stale branches early — PRs can be merged outside your control (GitHub UI, standalone `gh`); check before committing on top
- If on a feature branch, check if its PR was already merged/closed: `gh pr view --json state 2>/dev/null`
  - If `state` is `MERGED` or `CLOSED`: warn the user about uncommitted changes, switch to main, pull, delete the stale branch (`git branch -D`), and create a fresh branch from main

## Pushing

- Never push directly to `main` or `master`
- Fetch latest before pushing: `git fetch origin`
- Rebase onto main if needed — check with `git merge-base --is-ancestor origin/main HEAD` (exit 0 = clean)
  - If rebase hits conflicts: abort, inform the user of the conflicting files, and stop
- Push with `--force-with-lease` — the safety net for remote divergence; don't add redundant pulls before it
  - Add `-u` if no upstream is set
  - If `--force-with-lease` rejects (remote has unknown commits): stop and inform the user
  - If push fails because the remote branch was deleted: re-push with `-u` to recreate it
- After every push to a branch with an open PR:
  1. Update the PR description (`gh pr edit`) — title, summary, and test plan must reflect ALL commits on the branch vs main
  2. Request a Copilot review and poll for it (up to 5 minutes), then process any comments before continuing

## Pull requests

- Check for an existing open PR: `gh pr view --json number,url,state 2>/dev/null`
- Check PR `state` is `OPEN` before acting on it — `gh pr view` returns merged/closed PRs too
- If a PR exists and `state` is `OPEN`: update its title, summary, and test plan with `gh pr edit` to reflect ALL commits on the branch, then report its URL
- If no open PR exists: create one with `gh pr create` using this format:

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
- Every push must be followed by a PR description update — after addressing review feedback, always run `gh pr edit` to keep the summary and test plan in sync

## Automated PR reviews (Copilot)

GitHub may auto-trigger a Copilot review on the first push to a PR. Subsequent pushes typically require a manual re-request.

- Before pushing, record the latest Copilot review ID to distinguish old from new:

  ```sh
  LAST_REVIEW_ID=$(gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews \
    --jq '[.[] | select(.user.login | test("^copilot-pull-request-reviewer"))] | sort_by(.submitted_at) | last | .id // 0')
  ```

- After pushing, request a Copilot review:

  ```sh
  gh api --method POST repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers \
    -f 'reviewers[]=copilot-pull-request-reviewer[bot]' 2>/dev/null || true
  ```

  - If this fails (e.g. Copilot not enabled or already requested), continue — an auto-triggered review may still arrive
  - If a review was auto-triggered by the push, the manual request is harmless (GitHub deduplicates)

- Poll for a **new** review every 15 seconds, up to 5 minutes — pipe to `jq` for safe variable passing (`--arg` is a `jq` flag, not a `gh api` flag):

  ```sh
  NEW_REVIEW_ID=$(gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews \
    | jq --arg lastId "$LAST_REVIEW_ID" \
    '[.[] | select(.user.login | test("^copilot-pull-request-reviewer"))] | sort_by(.submitted_at) | last | select(.id != ($lastId | tonumber)) | .id')
  ```

  - If `NEW_REVIEW_ID` is empty, the new review hasn't arrived yet — keep polling
  - If no new review appears after 5 minutes, inform the user and continue

- Read inline comments **from the new review only** — use GraphQL to reliably get review threads (the REST comments endpoint may not return comments on outdated diff lines):

  ```sh
  gh api graphql -f query='query { repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: PR_NUMBER) { reviewThreads(first: 100) { nodes {
      id isResolved comments(first: 5) { nodes { body author { login }
        pullRequestReview { databaseId } } } } } } } }' \
    | jq --arg newReviewId "$NEW_REVIEW_ID" \
    '.data.repository.pullRequest.reviewThreads.nodes[]
      | select(.isResolved == false)
      | select(.comments.nodes | length > 0)
      | select(.comments.nodes[0].author.login | test("^copilot-pull-request-reviewer"))
      | select(.comments.nodes[0].pullRequestReview != null)
      | select(.comments.nodes[0].pullRequestReview.databaseId == ($newReviewId | tonumber))
      | {threadId: .id, body: .comments.nodes[0].body}'
  ```

  - This filters to unresolved threads from the specific new review only
  - Prevents re-processing comments from previous review rounds

- For each bot review comment, decide whether to accept or reject:
  - **Accept**: fix the issue, then resolve the thread via GraphQL
  - **Reject**: reply to the thread explaining why, then resolve it
- Resolve accepted threads via GraphQL before pushing:

  ```sh
  gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "THREAD_ID"}) { thread { isResolved } } }'
  ```

- Reply to rejected threads via the REST API:

  ```sh
  gh api repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies -f body='Reason for not accepting'
  ```

- To list unresolved thread IDs:

  ```sh
  gh api graphql -f query='query { repository(owner: "OWNER", name: "REPO") { pullRequest(number: <PR_NUMBER>) { reviewThreads(first: 100) { nodes { id isResolved comments(first: 1) { nodes { body author { login } } } } } } } }'
  ```

- Only resolve threads from Copilot bot reviewers (`copilot-pull-request-reviewer[bot]` or `copilot-pull-request-reviewer`) — never resolve human reviewer threads

### Review-fix cycle

After processing all comments from a Copilot review:

1. Resolve all accepted/rejected threads (GraphQL mutations + REST replies)
2. Commit the fixes
3. Push (the standard push workflow applies — including updating the PR description with `gh pr edit` and requesting a new Copilot review)
4. Poll for the new Copilot review and process any new comments
5. Repeat from step 1 until the review comes back clean (no new comments)

- 3-round cap: if the reviewer keeps finding issues after 3 rounds, inform the user and let them decide
- Never skip re-requesting the review — every push that fixes review comments **must** trigger a fresh Copilot review

## Merging

- Always use squash merge: `gh pr merge <number> --squash`
- Never use `--merge` or `--rebase` strategies
- **Never merge with unresolved review threads** — every thread from every reviewer (bot or human) must be resolved before merging:
  - Accepted: fix applied and thread resolved via GraphQL
  - Rejected: reply posted explaining why, then thread resolved
- Verify zero unresolved threads before merging:

  ```sh
  gh api graphql -f query='query { repository(owner: "OWNER", name: "REPO") { pullRequest(number: <PR_NUMBER>) { reviewThreads(first: 100) { nodes { id isResolved } } } } }' --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length'
  ```

  If the count is not `0`, stop and resolve remaining threads first
- Before merging, verify all todo list tasks are completed — never merge with pending or in-progress items
- PR reviews (Copilot or any reviewer) may add new tasks — treat accepted review comments as todo items that must be resolved before merging
- Check that CI checks pass before merging: `gh pr checks`
- Confirm the PR is still `OPEN` immediately before merging
- If merge fails due to failing checks: inform the user and stop
- After merge completes:
  1. Switch to main: `git checkout main`
  2. Pull latest: `git pull`
  3. Delete the remote branch: `git push origin --delete <branch>` (skip if already deleted by GitHub)
  4. Delete the local branch: `git branch -D <branch>` (squash merge requires `-D` since commit hashes differ)

## Principles

- Prevent problems, don't recover from them — design workflows so errors can't happen rather than adding complex recovery logic
- Stop and inform the user on failures — rebase conflicts, rejected pushes, failing checks. Never auto-resolve or retry blindly.
