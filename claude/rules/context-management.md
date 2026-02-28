# Context Management

How Claude manages context window resources across a session. Extracted from *task-lifecycle* (which governs process); this rule governs context discipline.

## Subagent delegation

- Use subagents for research — offload exploration and parallel analysis to keep the main context clean
- One focused task per subagent; for complex problems, spin up multiple in parallel
- When spawning teammates for implementation, give each a non-overlapping scope to avoid conflicts
- Never duplicate work a subagent is already doing

## Proactive compaction

- Compact at ~50% context usage — don't wait for auto-compaction
- Manual `/compact` preserves more useful context than automatic truncation
- After compaction, verify you still have the critical details (file paths, plan items, constraints)

## Context loading

- Read only the files you'll change and their immediate callers/importers
- Don't speculatively read files "just in case" — fetch on demand
- For broad exploration, use an Explore subagent rather than polluting the main window
- Large search results belong in subagents, not the main conversation

## Anti-patterns

- Reading every file in a directory before knowing which ones matter
- Pasting full file contents when a targeted grep would suffice
- Running exploratory searches in the main context instead of a subagent
- Waiting for auto-compaction instead of compacting proactively
