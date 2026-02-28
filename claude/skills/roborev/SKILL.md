---
name: roborev
description: |
  Automated code review management with roborev daemon and CLI.
  Covers: multi-agent reviews (copilot, codex, gemini), review modes (interactive/auto),
  fixing findings, pre-push workflow, daemon management, per-project config.
  Use when: checking reviews, fixing findings, managing review status, or before pushing.
version: 1.2.0
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
- **One commit per review round** — batch all fixes from one review into a single commit, using `fix:` conventional commit format (e.g., `fix: address roborev findings`)

## Multi-Agent Reviews

### Why multiple agents

Different AI reviewers catch different things. Copilot focuses on correctness and security, Codex on architecture and patterns, Gemini on edge cases and testing gaps. Running all three gives broad coverage with minimal overlap.

### Trigger reviews with multiple agents

Use `--branch` to review all commits on the branch vs main, and `--agent` to specify the reviewer:

```sh
roborev review --branch --agent copilot
roborev review --branch --agent codex
roborev review --branch --agent gemini
```

Each command creates a separate job. Run all three before reading any — they execute concurrently in the daemon.

### Default workflow (interactive)

The default behavior is to wait for all agents, consolidate, and walk through findings interactively:

1. **Trigger** — run `roborev review --branch --agent <name>` for each agent
2. **Wait** — poll `roborev list` until all jobs show `done`. Do not read partial results — wait for every agent to finish so you can cross-reference findings
3. **Collect** — read all findings from all agents (`roborev show <job-id>` for each). Merge into a single list, deduplicating findings that multiple agents flagged on the same code
4. **Sort by severity** — order the consolidated list: blocker → medium → low. Within the same severity, group by file path for context
5. **Present one by one** — for each finding (highest severity first):
   - Show: severity, file, location, which agent(s) flagged it, description
   - Ask via `AskUserQuestion`: **Fix** / **Dismiss** / **Discuss** / **Skip**
   - **Fix** → implement the change, move to next
   - **Dismiss** → note the reason, move to next
   - **Discuss** → investigate the claim (read code, check docs), report back, re-ask
   - **Skip** → defer, revisit after remaining findings
   - Multi-agent consensus increases confidence: if 2+ agents flag the same issue, recommend **Fix**
6. **Commit** — batch all fixes into a single commit (`fix: address review findings`)
7. **Re-review** — re-trigger multi-agent reviews if fixes were substantial (logic changes, not typos)
8. **Push** — when all agents are clean or remaining findings are dismissed with rationale

### Triage signals

| Signal | Confidence | Action |
| --- | --- | --- |
| Multiple agents flag same issue | High | Fix it — independent reviewers agree |
| One agent flags, others silent | Medium | Verify the claim before fixing |
| Agent reports zero issues | Clean | Move on — no further action needed |
| Finding contradicts project rules | Low | Dismiss with reference to the rule |

### Available agents

The agents available depend on your roborev configuration. Common agents:

- `copilot` — GitHub Copilot reviewer
- `codex` — OpenAI Codex reviewer
- `gemini` — Google Gemini reviewer
- `claude-code` — Claude Code reviewer (often the default agent in `.roborev.toml`)

Check available agents with `roborev config get agents` or see your `.roborev.toml`.

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
