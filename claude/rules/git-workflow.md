# Git Workflow

## Squash merge

- Delete the remote branch after merge: `git push origin --delete <branch>` (skip if already deleted by GitHub)
- Use `git branch -D` (not `-d`) after squash merge — squash creates new commit hashes, so git never considers the branch "fully merged"
- Check PR `state` is `OPEN` before acting on it — `gh pr view` returns merged/closed PRs too
- Detect stale branches early — PRs can be merged outside your control (GitHub UI, standalone `gh`); check before committing on top

## Pushing

- `--force-with-lease` is the safety net for remote divergence — don't add redundant pulls before it

## Principles

- Prevent problems, don't recover from them — design workflows so errors can't happen rather than adding complex recovery logic
- Stop and inform the user on failures — rebase conflicts, rejected pushes, failing checks. Never auto-resolve or retry blindly.
