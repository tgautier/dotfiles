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

Use subagents for research — see *context-management* rule for delegation strategy.

## Plan

1. **Use plan mode** (`shift+tab`) for anything non-trivial
2. **Include a task checklist** — mark tasks complete during implementation to track progress
3. **List files to change** and the order of changes
4. **Scope explicitly** — for refactoring tasks, list what's in scope AND what you're deliberately skipping, with rationale for each
5. **Get user approval** before writing code

For iterating on plans before implementation, see the annotation cycle in `/code-planning`.

## Implement

- **Scope to what was asked** — do not build features, integrations, or configuration the user did not request. If you think something adjacent would be valuable, suggest it and wait for approval. "Add a tmux conf" does not mean "add iTerm2 keybindings"
- **Always the proper fix** — when you identify the clean solution, implement it. Never describe the right approach and then implement the easier one. "That changes more than needed" is not a valid reason to choose an inferior fix. Every shortcut quietly lowers the bar — the cumulative effect is a degraded codebase
- **Just-first**: if the project has a `Justfile`, always use `just` recipes instead of raw tool commands (`yarn`, `cargo`, `npx`, `docker compose`). Load the `/just` skill when editing or reviewing the Justfile
- Mark each task complete as you go — never stop mid-implementation with tasks unchecked
- Run verification (typecheck, lint, tests) **after every edit**, not batched at the end. If a test fails, fix it before moving on
- Do not add unnecessary comments, jsdocs, or type annotations to code you didn't change
- Keep corrections terse — single-sentence when context already exists. Reference existing code for consistency: "match the pattern in X"
- If an approach isn't working after one fix attempt, **revert and re-plan** rather than layering patches. One failed fix attempt is the signal to step back — don't push through a bad approach
- Compact proactively — see *context-management* rule for compaction and subagent strategy

## Verify

Before presenting work as done:

- **Prove it works** — run tests, show output, demonstrate the fix. Never mark a task complete on faith
- **Run all verification commands** in the plan, not just the ones you expect to pass
- **Staff engineer bar** — "Would a staff engineer approve this?" If the answer is hesitant, improve it before presenting
- **Demand elegance** — pause and ask "is there a more elegant way?" If a fix feels hacky: "Knowing everything I know now, what's the clean solution?" Then implement that clean solution — never settle for the hacky one after identifying the better approach
- **Diff against intent** — does the change do exactly what was asked? No more, no less?
- **CLAUDE.md drift check** — if the PR adds new files, config, rules, or docs, verify CLAUDE.md still reflects reality. New config files need architecture entries, new rules need the rules index, new docs need the documentation section. Update CLAUDE.md in the same PR — not as a follow-up

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

- **No laziness** — find root causes. No temporary fixes. No "this works for now" patches. Senior developer standards
- **Never degrade quality incrementally** — every fix, every example, every documentation change must meet the same standard as the rest of the codebase. Renaming a section to match broken content instead of writing correct content is degradation. Adding a comment instead of a type guard is degradation. Each small shortcut compounds — the worst outcome is a slowly eroding stack that nobody notices until it's too late
- **Stop early, re-plan, do it right** — if an approach isn't working, stop and re-plan. But "re-plan" means finding the correct approach, not downgrading to a lesser fix. Stopping is a signal to think harder, not to lower standards

## Anti-patterns

- Writing code before reading the files you'll change
- Making speculative fixes without understanding root cause
- Dismissing failing tests as "pre-existing" or "unrelated" without investigating
- Incrementally patching a bad approach instead of reverting and re-planning
- Running raw `yarn test`, `cargo test`, `docker compose up` when a `just` recipe exists for the same operation
- Building adjacent features the user didn't ask for (e.g., adding keybindings when asked for a config file)
- Identifying the correct fix but implementing an easier alternative ("changes more than needed")
- Renaming or relabeling to hide a gap instead of filling it (e.g., renaming a section vs writing proper content)
- Using type assertions (`as`, generics-as-cast) when a runtime type guard is the correct solution
- Adding a comment or annotation as a substitute for actual validation or implementation
