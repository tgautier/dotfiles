# Findings Capture

When you learn something non-obvious during work — drift, quirk, working pattern,
anti-pattern, or a contradiction with an existing skill or rule — persist it
before moving on. The user shouldn't have to ask twice.

## What counts as a finding

- **Drift** — a crate API/feature/version that contradicts what you assumed
  (e.g. `rand_core 0.10` dropped the `std` feature, `reqwest 0.13` renamed
  `rustls-tls` → `rustls`).
- **Undocumented quirk** — an API returns 404 where docs imply 200; a service
  rate-limits below its published ceiling; a config requires `localhost` and
  rejects `127.0.0.1`.
- **Working pattern** — a non-obvious construction that turned out right
  (e.g. "`std::sync::Mutex` for a sync trait method called from an async
  context; `tokio::sync::Mutex` only when the guard crosses an `await`").
- **Anti-pattern** — a thing you tried that failed for an instructive reason.
- **Skill or rule inaccuracy** — a section of a global skill that doesn't
  apply to the current context, or contradicts the actual API state.

## When to capture

- After a user correction (the classic trigger).
- After any discovery during normal work, even unprompted.
- Before declaring a non-trivial task done — ask: *did I learn anything a
  future reader of the project docs and global skills wouldn't already know?*

## Where to capture (first match wins)

1. **Project docs** (`README.md`, `CLAUDE.md`, `docs/**`) — project-specific
   facts: stack choices, verification recipes, known limitations.
2. **Global skill** (`claude/skills/<name>/SKILL.md`) — cross-project
   methodology and patterns. Update the skill *and* fix any inbound
   cross-references that drift.
3. **Global rule** (`claude/rules/*.md`) — constraints that must always hold
   even without the user invoking a skill.
4. **Memory** (`memory/*.md`) — last resort, only for project-specific
   context that doesn't generalize and isn't already in the code.

## Anti-patterns

- "I'll remember this for next time" — you won't. Capture it now.
- Writing memory when the fact generalizes (memory bloats; rules/skills
  scale across sessions and projects).
- Updating a skill but forgetting the inbound cross-reference in the project's
  `CLAUDE.md`.
- Capturing something that's already in the spec — read first, capture only
  the delta.
