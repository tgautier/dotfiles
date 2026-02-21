# Plan First

Always start with a plan before writing code.

## When to plan

- Multi-file changes
- New features or endpoints
- Architectural or schema changes
- Bug fixes that aren't obviously single-line

## How

1. **Identify verification method first** — how will you prove it works? (test, shell command, CI, browser)
2. **Read relevant code** — understand what exists before proposing changes
3. **Use plan mode** (`shift+tab`) for anything non-trivial
4. **List files to change** and the order of changes
5. **Get user approval** before writing code

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
