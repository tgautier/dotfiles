# Config Audit

When adding, removing, or modifying any file in `.claude/rules/`, `.claude/skills/`, `claude/rules/`, or `claude/skills/`, verify the following before marking the task complete.

## Checklist

- [ ] **No duplication** — search existing rules and skills for overlapping content. Cross-reference, don't copy
- [ ] **Bidirectional cross-references** — if file A references file B, file B references file A where relevant
- [ ] **CLAUDE.md concern map updated** — correct typographic convention: *italic* for global rules (from dotfiles), `backtick` for project-local rules
- [ ] **CLAUDE.md rules index updated** — new rules appear in the correct subsection (global vs path-scoped) with concern and description
- [ ] **`skill-triggers.md` updated** — if adding a skill: task-triggered table entry + composite workflows row if applicable
- [ ] **Path-scoped globs verified** — run `just claude-check-rule-scopes` (if the project provides it) to confirm globs match existing files
- [ ] **`just check` passes** — escaping + cross-refs + lint + typecheck
- [ ] **No orphaned cross-references** — if removing a rule or skill, grep for references to it and update or remove them
- [ ] **One concern per file** — if a rule covers two unrelated topics, split it
- [ ] **80-line signal** — rules over 80 lines likely cover too much; consider splitting or converting detailed sections into a skill

## Scope

This rule applies to both project-local config (`.claude/`) and global config (`claude/` in dotfiles). The checklist is the same regardless of location — consistency across the config system prevents drift.
