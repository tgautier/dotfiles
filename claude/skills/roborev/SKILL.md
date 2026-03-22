---
name: roborev
description: |
  Automated code review management with roborev daemon and CLI.
  Covers: multi-agent reviews (claude, copilot, codex), review modes (interactive/auto),
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
   - **Reflect first** — before presenting options, reason about the finding against the project's architecture and design philosophy. Read the relevant code, check project rules, and determine which action best serves codebase coherence. Present your recommendation with rationale, not a bare option list
   - Present: severity, file, location, reviewer's description, **your recommendation and why**
   - Ask via `AskUserQuestion`: **Fix** / **Dismiss** / **Discuss** / **Skip** — with your recommended option clearly marked
   - **Fix** → implement the change, move to next finding
   - **Dismiss** → note the user's reason, no code change
   - **Discuss** → investigate deeper (read code, verify claims, check docs), report back, re-ask
   - **Skip** → defer, revisit after remaining findings
4. After all findings processed, commit fixes (if any), wait for re-review
5. Repeat until clean or user says stop
6. Summarize: what was fixed, what was dismissed (with reasons)

**Never auto-resolve in interactive mode.** Every finding requires the user's explicit decision. Claude recommends — the user decides. Never mark a finding as addressed, dismissed, or resolved without the user choosing that action through `AskUserQuestion`. This applies even when the recommendation is obvious — the user must confirm.

### Auto mode

Invoked with `/roborev auto`. Fixes everything without asking — but verifies first.

1. Run `roborev show` to get the latest review
2. If no findings → report clean and stop
3. Verify each claim before fixing (reviewer can be wrong — check exit codes, API behavior, docs)
4. Fix all verified findings, commit, wait for re-review, repeat until clean
5. If a claim is wrong, report it as dismissed with rationale

### Behavioral rules (both modes)

- **Reflect and recommend** — for every finding, reason about which action best fits the project's architecture before presenting options. Never present a bare option list without a recommendation and rationale
- **Never auto-resolve in interactive mode** — every finding requires the user's explicit decision via `AskUserQuestion`. Claude recommends, the user decides. This is non-negotiable even for obvious fixes
- **Never auto-dismiss** — only the user (interactive) or verified-wrong claims (auto) can dismiss
- **Verify before fixing** — check the reviewer's technical claims before implementing
- **Severity-first** — blockers before mediums before lows
- **High/blocker findings default to Fix** — never recommend Dismiss for high-severity or blocker findings. "Already mitigated by convention" is not a fix — if the proper fix exists and is reasonable, recommend it. Existing bad patterns in the codebase are not permission to continue them. The only valid reason to recommend Dismiss on a high-severity finding is if the reviewer's claim is factually wrong (verified, not assumed)
- **One commit per review round** — batch all fixes from one review into a single commit, using `fix:` conventional commit format (e.g., `fix: address roborev findings`)

## Multi-Agent Reviews

### Why multiple agents

Different AI reviewers catch different things. Claude focuses on architecture and design coherence, Copilot on correctness and security, Codex on patterns and edge cases. Running all three gives broad coverage with minimal overlap.

### Trigger reviews with multiple agents

Use `--branch` to review all commits on the branch vs main, and `--agent` to specify the reviewer:

```sh
roborev review --branch --agent claude-code
roborev review --branch --agent copilot
roborev review --branch --agent codex
```

Each command creates a separate job. Run all three before reading any — they execute concurrently in the daemon.

### Default workflow (interactive)

The default behavior is to wait for all agents, consolidate, and walk through findings interactively:

1. **Trigger** — run `roborev review --branch --agent <name>` for each agent
2. **Wait** — poll `roborev list` until all jobs show `done`. Do not read partial results — wait for every agent to finish so you can cross-reference findings. If a job shows `failed`, skip it immediately. If a job stays `running` for more than 5 minutes, it may be stuck — skip it and proceed with the agents that completed
3. **Collect** — read all findings from all agents (`roborev show <job-id>` for each). Merge into a single list, deduplicating findings that multiple agents flagged on the same code
4. **Sort by severity** — order the consolidated list: blocker → medium → low. Within the same severity, group by file path for context
5. **Reflect and recommend** — for each finding (highest severity first):
   - Read the relevant code and check project rules before presenting the finding
   - Reason about which action best serves the project's architecture and design philosophy
   - Show: severity, file, location, which agent(s) flagged it, description, **your recommendation and why**
   - Ask via `AskUserQuestion`: **Fix** / **Dismiss** / **Discuss** / **Skip** — with your recommended option marked
   - **Fix** → implement the change, move to next
   - **Dismiss** → note the user's reason, move to next
   - **Discuss** → investigate the claim deeper, report back, re-ask
   - **Skip** → defer, revisit after remaining findings
   - Multi-agent consensus increases confidence: if 2+ agents flag the same issue, recommend **Fix**
   - Never resolve any finding without the user's explicit choice — see interactive mode rules
6. **Commit** — batch all fixes into a single commit (`fix: address review findings`)
7. **Re-review** — re-trigger multi-agent reviews if fixes were substantial (logic changes, not typos)
8. **Converge or stop** — if a re-review produces only low/medium findings that fail closed (block incorrectly, not bypass), create issues for relevant ones and stop. Do not iterate beyond 3 review rounds on the same file — repeated fix/review cycles on the same code signal growing complexity, not convergence
9. **Push** — when all agents are clean or remaining findings are dismissed/tracked with rationale

### Triage signals

| Signal | Confidence | Action |
| --- | --- | --- |
| Multiple agents flag same issue | High | Fix it — independent reviewers agree |
| One agent flags, others silent | Medium | Verify the claim before fixing |
| Agent reports zero issues | Clean | Move on — no further action needed |
| Finding contradicts project rules | Low | Dismiss with reference to the rule |
| Finding fails closed (blocks, no bypass) | Lower | UX issue, not security — fix or defer to issue |
| Finding fails open (bypasses gate) | Higher | Security issue — must fix before merge |

### Available agents

The `--agent` flag overrides the default agent from `.roborev.toml` for a single review. Common agents:

- `claude-code` — Claude Code reviewer
- `copilot` — GitHub Copilot reviewer
- `codex` — OpenAI Codex reviewer

The `.roborev.toml` only configures one `agent` (default) and one `backup_agent`. Multi-agent reviews use CLI `--agent` overrides, not toml configuration.

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

A global PreToolUse hook blocks `git push` and `gh pr merge` when:

- No reviews exist for the branch (must run `roborev review --branch` first)
- Any review is still `running` or `queued`
- All reviews `failed` (zero actual coverage — at least one must be `done`)

The hook allows through only when at least one review is `done` and no reviews are still in progress. For `gh pr merge`, the hook resolves the PR's head branch (not the local branch) to avoid bypass when merging from `main`.

1. Commit triggers a post-commit hook → daemon queues a review
2. When you attempt to push or merge, the hook queries `roborev list --json` and checks review statuses for the target branch
3. If blocked: check status with `roborev list`, re-run reviews with `roborev review --branch`

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
- Recommending Dismiss on high-severity findings because "it's mitigated by convention" — conventions are bypassed, proper fixes are not
- Auto-resolving findings in interactive mode — every finding needs explicit user approval, even trivial ones
- Presenting bare option lists without reasoning — always reflect on the finding and recommend the architecturally correct action
- Treating existing bad patterns as justification — "the old code did it too" is not a reason to dismiss
- Running `roborev init` in a repo that already has `.roborev.toml` — use `install-hook` instead
- Manually editing review results — use `roborev address` or `roborev comment` to interact with findings
