---
name: roborev
description: |
  Automated code review management with roborev daemon and CLI.
  Covers: review modes (interactive/auto), fixing findings, pre-push workflow, daemon management, per-project config.
  Use when: checking reviews, fixing findings, managing review status, or before pushing.
version: 1.1.0
date: 2026-02-28
user-invocable: true
---

# Roborev — Automated Code Review

Roborev is a daemon-based automated code review tool. It runs post-commit hooks that trigger AI-powered reviews, and provides CLI commands to inspect, fix, and iterate on findings.

## When to Use

- After roborev flags issues — read findings, fix them, verify
- When the PreToolUse hook blocks a push or merge due to unaddressed findings
- For manual review commands (dirty review, branch review, specific commit)

## Review Modes

### Interactive mode (default)

Invoked with `/roborev` or `/roborev interactive`. Walks through each finding with the user.

1. Run `roborev show` to get the latest review
2. If no findings → report clean and stop
3. For each finding (severity order: blocker → medium → low):
   - Present: severity, file, location, reviewer's description
   - Ask via `AskUserQuestion`: **Fix** / **Dismiss** / **Discuss** / **Skip**
   - **Fix** → implement the change, move to next finding
   - **Dismiss** → note the user's reason, no code change
   - **Discuss** → investigate (read code, verify claims, check docs), report back, re-ask
   - **Skip** → defer, revisit after remaining findings
4. After all findings processed, commit fixes (if any), wait for re-review
5. Repeat until clean or user says stop
6. Summarize: what was fixed, what was dismissed (with reasons)

### Auto mode

Invoked with `/roborev auto`. Fixes everything without asking — but verifies first.

1. Run `roborev show` to get the latest review
2. If no findings → report clean and stop
3. Verify each claim before fixing (reviewer can be wrong — check exit codes, API behavior, docs)
4. Fix all verified findings, commit, wait for re-review, repeat until clean
5. If a claim is wrong, report it as dismissed with rationale

### Behavioral rules (both modes)

- **Never auto-dismiss** — only the user (interactive) or verified-wrong claims (auto) can dismiss
- **Verify before fixing** — check the reviewer's technical claims before implementing
- **Severity-first** — blockers before mediums before lows
- **One commit per review round** — batch all fixes from one review into a single commit

## Commands

### Setup

```sh
roborev init          # Initialize a new repo (creates .roborev.toml + installs hooks)
roborev install-hook  # Install hooks only (when .roborev.toml already exists)
```

### Check status

```sh
roborev list          # List reviews for current branch
roborev show          # Show review for HEAD commit
roborev show <sha>    # Show review for a specific commit
```

### Fix findings

```sh
roborev fix           # One-shot fix for all unaddressed findings
roborev refine        # Iterative fix loop: fix → re-review → repeat until passing
```

### Interactive TUI

```sh
roborev tui --repo --branch   # Terminal UI filtered to current repo + branch
roborev tui                   # Full TUI (all repos)
```

### Manual review

```sh
roborev review              # Review HEAD commit (if hook missed it)
roborev review --branch     # Review all commits on current branch vs main
roborev review --dirty      # Review uncommitted changes
roborev review --since HEAD~3  # Review last 3 commits
```

## Push and Merge Enforcement

A global PreToolUse hook blocks `git push` and `gh pr merge` when roborev has running or failed reviews. The workflow is:

1. Commit triggers a post-commit hook → daemon queues a review
2. When you attempt to push or merge, the hook checks `roborev list`
3. If blocked: `roborev fix` or `roborev refine`, then retry the push/merge

## Per-Project Config

Each repo has a `.roborev.toml` at the root with:

- `agent` — which AI agent to use (e.g. `copilot`, `claude-code`)
- `backup_agent` — fallback agent if primary is unavailable
- `review_guidelines` — project-specific rules injected into every review prompt
- `excluded_branches` — branches that skip review (e.g. `main`, `wip`, `scratch`)

The review guidelines should encode the project's hard invariants so roborev flags violations as blockers automatically.

## Daemon

The roborev daemon runs in the background, processing review jobs:

```sh
roborev daemon start   # Start daemon
roborev daemon stop    # Stop daemon
roborev status         # Check daemon health + recent jobs
```

The post-commit hook sends jobs to the daemon. If the daemon is not running, reviews queue and process when it starts.

## Anti-patterns

- Ignoring blocker-level findings — these represent hard invariant violations
- Running `roborev init` in a repo that already has `.roborev.toml` — use `install-hook` instead
- Manually editing review results — use `roborev address` or `roborev comment` to interact with findings
