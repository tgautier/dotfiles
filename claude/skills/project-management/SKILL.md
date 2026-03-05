---
name: project-management
description: |
  Tool-agnostic conventions for writing issues and PRs.
  Covers: issue structure, PR format, naming consistency, lifecycle.
  Use when: creating issues, writing PR descriptions, filing bugs, or planning work items.
  For merge gates and push workflow see `claude/rules/git-conventions.md`.
version: 1.0.0
date: 2026-03-03
user-invocable: true
---

# Project Management Conventions

Tool-agnostic — applies equally to GitHub Issues, Linear issues, and any PR host.

## 1. Issue Conventions

### Title format

- Imperative verb phrase, under 70 chars
- Conventional commit prefix: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `ci:`, `perf:`, `test:`
- Example: `fix: shell startup hangs when config is missing`

### Description structure

Four sections — omit any that are empty:

1. **Context** — what exists today, what triggered this work
2. **Problem** — what's wrong or missing
3. **Proposal** — what to do about it (scope, approach)
4. **References** — related issues, PRs, docs, audit findings

### Scope discipline

One concern per issue. If an issue covers two unrelated changes, split it. Multi-concern PRs reference multiple issues — each concern gets its own.

## 2. PR Conventions

### Title

- Mirrors conventional commit format: `type(scope): description`
- Matches the branch type prefix
- Under 70 chars

### Summary bullets

- What changed and why (not how)
- Each bullet maps to a commit or concern
- Cover ALL commits on the branch vs main, not just the latest

### Test plan

- Verifiable actions: "Run `just api-test`", not vague "Tests pass"
- Unchecked `[ ]` = pending, checked `[x]` = verified
- Never merge with unchecked items — remove with explanation or verify first

### Issue references

- Every `Fixes #N` or `Addresses #N` on its own line in the PR body
- `Fixes` auto-closes on merge; `Addresses` does not
- If work addresses something not yet tracked, create the issue first

### Draft PRs

Use when work is in-progress and you want early CI or review feedback. Mark ready when all test plan items are checkable.

## 3. Naming Consistency

The naming chain uses the same type prefix and describes the same concern:

| Artifact | Example |
|---|---|
| Issue title | `fix: shell startup hangs when config is missing` |
| Branch | `fix/42-shell-startup` |
| Commits | `fix(shell): prevent startup hang on missing config` |
| PR title | `fix(shell): prevent startup hang on missing config` |

## 4. Lifecycle

- Close issues via PR merge (`Fixes #N`) — don't close manually unless the issue is withdrawn
- Partial fix: use `Addresses #N` (no auto-close) and note what remains
- Stale issues: if the fix shipped without linking, close with a comment referencing the commit or PR
- Re-opened issues: add a comment explaining why the original fix was insufficient
