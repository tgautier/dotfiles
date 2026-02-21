# Git Workflow

## Squash merge

- Delete the remote branch after merge: `git push origin --delete <branch>` (skip if already deleted by GitHub)
- Use `git branch -D` (not `-d`) after squash merge — squash creates new commit hashes, so git never considers the branch "fully merged"
- Check PR `state` is `OPEN` before acting on it — `gh pr view` returns merged/closed PRs too
- Detect stale branches early — PRs can be merged outside your control (GitHub UI, standalone `gh`); check before committing on top

## Pushing

- `--force-with-lease` is the safety net for remote divergence — don't add redundant pulls before it

## Automated PR reviews (Codex / Copilot)

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

- Only resolve threads from bot reviewers (`chatgpt-codex-connector[bot]`, `copilot-pull-request-reviewer[bot]`) — never resolve human reviewer threads

## Merging

- Before merging, verify all todo list tasks are completed — never merge with pending or in-progress items
- PR reviews (Codex, Copilot, or any reviewer) may add new tasks — treat accepted review comments as todo items that must be resolved before merging
- Check that CI checks pass before merging: `gh pr checks`
- Confirm the PR is still `OPEN` immediately before merging

## Principles

- Prevent problems, don't recover from them — design workflows so errors can't happen rather than adding complex recovery logic
- Stop and inform the user on failures — rebase conflicts, rejected pushes, failing checks. Never auto-resolve or retry blindly.
