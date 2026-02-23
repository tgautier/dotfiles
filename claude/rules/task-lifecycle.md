# Task Lifecycle

How Claude approaches tasks, from intake to completion. Organized by the task lifecycle: assess → research → plan → implement → verify → done.

> **Scope boundary:** This rule governs *process* — when to plan, how to work, verification discipline. For plan *quality* methodology (trade-off evaluation, task decomposition, scope management, risk identification, annotation cycles) → **Code Planning skill** (`/code-planning`).

## Project grounding

At the start of any task, read the project's `CLAUDE.md`. It contains:

- Which verification commands to run and when
- Critical constraints specific to this codebase
- Pointers to rules (`.claude/rules/`) — path-scoped rules auto-load for matching files

## Assess

Determine the right approach before doing anything:

- **Trivial** (single-line fix, obvious typo) — just do it. No plan needed
- **Non-trivial** (multi-file changes, new features, architectural decisions, non-obvious bug fixes) — plan first
- **Bug report or failing test** — fix it autonomously. Read the error, find the root cause, implement the fix, verify it works. Zero hand-holding. Don't ask for clarification unless the bug is genuinely ambiguous

Before starting, identify how you'll verify the work: existing test suite, new test, shell command, browser check, or CI pipeline.

## Research

Before planning, deeply read all code that will be affected:

1. Read the files you'll change AND the files that call/import them
2. Document findings: existing patterns, conventions, gotchas, and integration points

Use subagents for research to keep the main context window clean. Offload exploration and parallel analysis — don't pollute the main conversation with hundreds of lines of search results.

## Plan

1. **Use plan mode** (`shift+tab`) for anything non-trivial
2. **Include a task checklist** — mark tasks complete during implementation to track progress
3. **List files to change** and the order of changes
4. **Scope explicitly** — for refactoring tasks, list what's in scope AND what you're deliberately skipping, with rationale for each
5. **Get user approval** before writing code

For iterating on plans before implementation, see the annotation cycle in `/code-planning`.

## Implement

- **Just-first**: if the project has a `Justfile`, always use `just` recipes instead of raw tool commands (`yarn`, `cargo`, `npx`, `docker compose`). Load the `/just` skill when editing or reviewing the Justfile
- Mark each task complete as you go — never stop mid-implementation with tasks unchecked
- Run verification (typecheck, lint, tests) **after every edit**, not batched at the end. If a test fails, fix it before moving on
- Do not add unnecessary comments, jsdocs, or type annotations to code you didn't change
- Keep corrections terse — single-sentence when context already exists. Reference existing code for consistency: "match the pattern in X"
- If an approach isn't working after one fix attempt, **revert and re-plan** rather than layering patches. One failed fix attempt is the signal to step back — don't push through a bad approach
- Compact proactively at ~50% context. Don't wait for auto-compaction — manual `/compact` preserves more useful context

### Subagent strategy

- Use subagents liberally — one focused task per subagent
- For complex problems, throw more compute at it: spin up multiple subagents in parallel
- When spawning teammates for implementation, use worktree isolation so agents don't conflict

## Verify

Before presenting work as done:

- **Prove it works** — run tests, show output, demonstrate the fix. Never mark a task complete on faith
- **Run all verification commands** in the plan, not just the ones you expect to pass
- **Staff engineer bar** — "Would a staff engineer approve this?" If the answer is hesitant, improve it before presenting
- **Demand elegance (non-trivial changes only)** — pause and ask "is there a more elegant way?" If a fix feels hacky: "Knowing everything I know now, what's the clean solution?" Skip this for simple, obvious fixes
- **Diff against intent** — does the change do exactly what was asked? No more, no less?

### Failing tests are blockers

- **Never dismiss a test failure** — "pre-existing", "unrelated", or "infrastructure issue" are not valid reasons to skip investigation
- If a test fails, **stop and fix it** before continuing with the original task
- If the fix is genuinely out of scope, explain the root cause to the user and let them decide — don't silently move on

## Self-improvement

After ANY correction from the user:

1. Identify the pattern — what class of mistake was this? (wrong assumption, missed convention, skipped verification)
2. Update memory (`MEMORY.md` or a topic-specific memory file) with the lesson
3. If the mistake could recur across sessions, write or update a rule that prevents it

Write lessons to `MEMORY.md` (auto-memory) so they persist across sessions and inform future work.

The goal is zero repeat mistakes. If the same correction happens twice, the rule wasn't specific enough — tighten it.

## Principles

- **Simplicity first** — make every change as simple as possible. The right amount of complexity is the minimum needed for the current task
- **No laziness** — find root causes. No temporary fixes. No "this works for now" patches. Senior developer standards
- **Minimal impact** — changes should only touch what's necessary. Avoid introducing bugs by changing code outside the task scope
- **Stop early, not late** — if something goes sideways, STOP and re-plan immediately. Don't push through hoping it will work out

## Anti-patterns

- Writing code before reading the files you'll change
- Making speculative fixes without understanding root cause
- Dismissing failing tests as "pre-existing" or "unrelated" without investigating
- Incrementally patching a bad approach instead of reverting and re-planning
- Running raw `yarn test`, `cargo test`, `docker compose up` when a `just` recipe exists for the same operation
