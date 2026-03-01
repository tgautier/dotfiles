# Quality Standards

Quality discipline that applies to every change. Separated from *task-lifecycle* (which governs process) to keep each rule focused on one concern.

## Principles

- **No laziness** — find root causes. No temporary fixes. No "this works for now" patches. Senior developer standards
- **Never degrade quality incrementally** — every fix, every example, every documentation change must meet the same standard as the rest of the codebase. Renaming a section to match broken content instead of writing correct content is degradation. Adding a comment instead of a type guard is degradation. Each small shortcut compounds — the worst outcome is a slowly eroding stack that nobody notices until it's too late
- **Stop early, re-plan, do it right** — if an approach isn't working, stop and re-plan. But "re-plan" means finding the correct approach, not downgrading to a lesser fix. Stopping is a signal to think harder, not to lower standards

## Self-improvement

After ANY correction from the user:

1. Identify the pattern — what class of mistake was this? (wrong assumption, missed convention, skipped verification)
2. Update memory (`MEMORY.md` or a topic-specific memory file) with the lesson
3. If the mistake could recur across sessions, write or update a rule that prevents it

Write lessons to `MEMORY.md` (auto-memory) so they persist across sessions and inform future work.

The goal is zero repeat mistakes. If the same correction happens twice, the rule wasn't specific enough — tighten it.

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
- Presenting review findings as bare option lists without reasoning about which action fits the architecture
- Auto-resolving review findings without the user's explicit decision — Claude recommends, the user decides
- Writing per-entry tests for a data mapping (switch/match) instead of refactoring to a table lookup
- Testing a loader/handler to prove inline logic works instead of extracting the pure function
