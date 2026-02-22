# Plan First

Always start with a plan before writing code.

> **Scope boundary:** This rule governs planning *process* — when to plan, the annotation cycle, verification-first workflow. For plan *quality* methodology (trade-off evaluation, task decomposition, scope management, risk identification) → **Code Planning skill** (`/code-planning`).

## When to plan

- Multi-file changes
- New features or endpoints
- Architectural or schema changes
- Bug fixes that aren't obviously single-line

## Research first

Before planning, deeply read all code that will be affected or that the changes must integrate with:

1. Read the files you'll change AND the files that call/import them
2. Write findings to a persistent file (`research.md` or similar) — not just chat summaries
3. Document: existing patterns, conventions, gotchas, and integration points
4. The research artifact survives context compression and informs the plan

## How

1. **Identify verification method first** — how will you prove it works? (test, shell command, CI, browser)
2. **Read relevant code** — understand what exists before proposing changes
3. **Use plan mode** (`shift+tab`) for anything non-trivial — for complex multi-step work, also write the plan to a persistent file (`plan.md`) that survives context compression
4. **Include a task checklist** in the plan — mark tasks complete during implementation to track progress
5. **List files to change** and the order of changes
6. **Get user approval** before writing code
7. **Scope explicitly** — for refactoring tasks, list what's in scope AND what you're deliberately skipping, with rationale for each

## Annotation cycle

For non-trivial changes, iterate on the plan before implementation:

1. Claude generates a plan (as a markdown file, in addition to plan mode)
2. You add inline notes directly in the plan — corrections, rejections, domain knowledge
3. Claude addresses all notes and updates the plan. **No code yet.**
4. Repeat this cycle 1–6 times until the plan is right
5. Only then: "implement it all"

Guard phrase: include "don't implement yet" when refining the plan to prevent premature code generation.

## Verification-first (TDD)

Before writing any code, determine how to verify it works:

- Existing test suite (`just api-test`, `just test`)
- New test you'll write first
- Shell command or curl
- Browser check
- CI pipeline

Run verification **after every edit**, not batched at the end. If a test fails, fix it before moving on.

## Failing tests are blockers

- **Never dismiss a test failure** — "pre-existing", "unrelated", or "infrastructure issue" are not valid reasons to skip investigation
- If a test fails during verification, **stop and fix it** before continuing with the original task
- If the fix is genuinely out of scope, explain the root cause to the user and let them decide — don't silently move on
- Run **all** verification commands in the plan (`just check`, `just test`, `just test-e2e`), not just the ones you expect to pass

## Anti-patterns

- Writing code before reading the files you'll change
- Making speculative fixes without understanding root cause
- Batching all verification to the end
- Skipping plan mode to "save time" — it costs more time when changes need rework
- Dismissing failing tests as "pre-existing" or "unrelated" without investigating
- Incrementally patching a bad approach instead of reverting and re-planning
