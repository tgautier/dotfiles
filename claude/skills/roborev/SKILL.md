---
name: roborev
description: |
  Automated code review management with roborev daemon and CLI.
  Covers: review status, fixing findings, pre-push workflow, daemon management, per-project config.
  Use when: checking reviews, fixing findings, managing review status, or before pushing.
version: 1.0.0
date: 2026-02-26
user-invocable: true
---

# Roborev — Automated Code Review

Roborev is a daemon-based automated code review tool. It runs post-commit hooks that trigger AI-powered reviews, and provides CLI commands to inspect, fix, and iterate on findings.

## When to Use

- After roborev flags issues — read findings, fix them, verify
- When the PreToolUse hook blocks a push or merge due to unaddressed findings
- For manual review commands (dirty review, branch review, specific commit)

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
