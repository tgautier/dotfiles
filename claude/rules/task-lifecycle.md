# Task Lifecycle

How Claude approaches tasks, from intake to completion: assess → research → plan → implement → verify → done. Includes quality principles and context discipline.

## Project grounding

At the start of any task, read the project's `CLAUDE.md` for verification commands, constraints, and rule pointers.

## Assess

- **Trivial** (single-line fix, obvious typo) — just do it
- **Non-trivial** (multi-file changes, new features, architectural decisions) — plan first
- **Bug report or failing test** — fix autonomously: read the error, find root cause, implement, verify

Before starting, identify how you'll verify the work.

## Research

Before planning, deeply read all code that will be affected:

1. Read the files you'll change AND the files that call/import them
2. Use subagents for research — one focused task per subagent, parallel when possible

## Plan

1. **Use plan mode** (`shift+tab`) for anything non-trivial
2. **Include a task checklist** — mark tasks complete during implementation
3. **List files to change** and the order of changes
4. **Scope explicitly** — list what's in scope AND what you're deliberately skipping
5. **Get user approval** before writing code

For plan quality methodology → `/code-planning`.

## Implement

- **Scope to what was asked** — do not build features the user did not request
- **Always the proper fix** — never describe the right approach and implement the easier one. Every shortcut lowers the bar
- **Just-first**: if the project has a `Justfile`, always use `just` recipes instead of raw tool commands
- Mark each task complete as you go
- Run verification **after every edit**, not batched at the end
- If an approach isn't working after one fix attempt, **revert and re-plan**
- Compact at ~50% context usage — manual `/compact` preserves more than auto-truncation

## Verify

- **Prove it works** — run tests, show output. Never mark a task complete on faith
- **Staff engineer bar** — "Would a staff engineer approve this?"
- **Demand elegance** — "Is there a more elegant way?" If yes, implement it
- **Diff against intent** — does the change do exactly what was asked? No more, no less?
- **CLAUDE.md drift check** — if the PR adds new files/config/rules, verify CLAUDE.md still reflects reality

### Failing tests are blockers

- **Never dismiss a test failure** — "pre-existing" or "unrelated" are not valid reasons to skip investigation
- If the fix is genuinely out of scope, explain the root cause to the user and let them decide

## Quality principles

- **No laziness** — find root causes. No temporary fixes. Senior developer standards
- **Never degrade quality incrementally** — every change must meet the same standard as the codebase
- **Stop early, re-plan, do it right** — stopping is a signal to think harder, not to lower standards

## Self-improvement

After ANY correction from the user:

1. Identify the pattern (wrong assumption, missed convention, skipped verification)
2. Update memory (`MEMORY.md` or topic file) with the lesson
3. If the mistake could recur across sessions, write or update a rule

## Anti-patterns

- Writing code before reading the files you'll change
- Speculative fixes without understanding root cause
- Patching a bad approach instead of reverting and re-planning
- Running raw `yarn test`, `cargo test` when a `just` recipe exists
- Building adjacent features the user didn't ask for
- Identifying the correct fix but implementing the easier alternative
- Type assertions (`as`) when a runtime type guard is correct
- Auto-resolving review findings without user's explicit decision
- Per-entry tests for a data mapping instead of table lookup refactoring
- Reading every file in a directory before knowing which ones matter
- Running exploratory searches in main context instead of a subagent
