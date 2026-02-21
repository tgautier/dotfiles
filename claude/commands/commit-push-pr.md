---
allowed-tools: Bash, Read, Glob, Grep
description: Commit all changes, push, and create/update a PR if needed
user-invocable: true
---

# Commit, Push, and PR

Follow these steps in order:

## 1. Assess current state

Run these in parallel:
- `git status` (no -uall flag)
- `git diff --stat` (staged + unstaged summary)
- `git log --oneline -5` (recent commit style)
- `git branch --show-current` (current branch)
- `git rev-parse --abbrev-ref @{upstream} 2>/dev/null || echo "no-upstream"` (tracking info)

## 2. Stage and commit

- Stage all relevant changed files (avoid secrets, .env, credentials)
- Write a conventional commit message: `type(scope): description`
- Do NOT include `Co-Authored-By` or mention Claude/AI
- Keep first line under 72 characters
- Use a HEREDOC for the commit message

## 3. Push

- Push to the remote, using `-u` if no upstream is set
- If the branch is `main` or `master`, STOP and warn the user

## 4. Create or update PR

- Check if a PR already exists for this branch: `gh pr view --json number,url 2>/dev/null`
- If a PR exists: report its URL, do NOT create a new one
- If no PR exists: create one with `gh pr create` using this format:

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
