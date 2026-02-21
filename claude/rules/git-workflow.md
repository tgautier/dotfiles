# Git Workflow

## Squash merge

- Delete the remote branch after merge: `git push origin --delete <branch>` (skip if already deleted by GitHub)
- Use `git branch -D` (not `-d`) after squash merge — squash creates new commit hashes, so git never considers the branch "fully merged"
- Check PR `state` is `OPEN` before acting on it — `gh pr view` returns merged/closed PRs too
- Detect stale branches early — PRs can be merged outside your control (GitHub UI, standalone `gh`); check before committing on top

## Pushing

- `--force-with-lease` is the safety net for remote divergence — don't add redundant pulls before it

## Automated PR reviews (Codex / Copilot)

- After fixing review feedback, resolve the corresponding review threads via GraphQL before pushing:
  ```
  gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "THREAD_ID"}) { thread { isResolved } } }'
  ```
- To list unresolved thread IDs:
  ```
  gh api graphql -f query='query { repository(owner: "OWNER", name: "REPO") { pullRequest(number: <PR_NUMBER>) { reviewThreads(first: 100) { nodes { id isResolved comments(first: 1) { nodes { body author { login } } } } } } } }'
  ```
- Only resolve threads from bot reviewers (`chatgpt-codex-connector[bot]`, `copilot-pull-request-reviewer[bot]`) — never resolve human reviewer threads

## Principles

- Prevent problems, don't recover from them — design workflows so errors can't happen rather than adding complex recovery logic
- Stop and inform the user on failures — rebase conflicts, rejected pushes, failing checks. Never auto-resolve or retry blindly.
