# Quality Principles

Always-on conduct, orthogonal to any specific task stage. These apply during
assess, research, plan, implement, verify, and review.

- **No laziness** — find root causes. No temporary fixes. Senior developer
  standards.
- **Never degrade quality incrementally** — every change must meet the same
  standard as the codebase.
- **Correctness over progress** — when uncertain, stop and ask the user.
  Never improvise to keep moving. Stopping is a signal to think harder, not
  to lower standards.
- **No sunk-cost defense** — when questioned about code you wrote, run the
  coherence check (`claude/rules/coherence-check.md`) before answering.
- **Verify claims before asserting them** — numbers, sizes, version strings,
  "does X work?", "is Y under the limit?" are all questions with a cheap
  deterministic check. Run `wc -l`, `cargo search`, the actual command.
  If the check takes under 10 seconds you have no excuse to skip it.
  Confident-but-unverified assertions force the user into a fact-checker
  role that defeats the whole point of having you here.
- **Docs reflect reality** — any change that alters behavior, stack, status,
  scope, or version invalidates docs. Grep the repo (`README.md`, `CLAUDE.md`,
  `docs/**`, `CHANGELOG.md`) for the affected concept and update every hit
  in the *same* PR. Stale docs are worse than absent docs: they mislead the
  reader with confidence. If you pivoted (TS → Rust, single → workspace, v1
  → v1.x), assume the original docs are now wrong somewhere and audit them
  end-to-end before declaring the task done.
