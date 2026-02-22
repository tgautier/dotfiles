# Claude Config System

Two-tier model for organizing Claude instructions.

## Tiers

| Tier | Location | Loaded | Purpose |
| --- | --- | --- | --- |
| **Rules** | `.claude/rules/` (project), `claude/rules/` (global) | Auto — always, or when `paths:` match | Constraints, invariants, conventions that must hold |
| **Skills** | `claude/skills/<name>/SKILL.md` (global) | On-demand via `/name` | Reusable methodology, checklists, design patterns |

### Decision test

- "Must this hold even if nobody remembers to invoke it?" → **Rule**
- "Is this a methodology I apply deliberately to a specific task?" → **Skill**

## Path-scoped rules

Rules can include `paths:` frontmatter to auto-load only when working on matching files:

```yaml
---
paths:
  - api/src/handlers/**
  - api/src/main.rs
---
```

- Use path scoping when a rule is relevant only to specific directories
- Omit `paths:` when the rule applies globally (e.g., CQRS, testing, config)
- After directory restructuring, run `just claude-check-rule-scopes` (if the project defines it) to verify all globs still resolve

## Size and scope discipline

- One concern per file — if a rule covers two unrelated topics, split it
- 80-line signal — rules over 80 lines likely cover too much; consider splitting or converting detailed sections into a skill
- Path-scope when possible — reduces noise for unrelated work

## Evolution triggers

| Signal | Action |
| --- | --- |
| Rule > 80 lines | Split into focused rules, or extract methodology into a skill |
| Rule referenced only from one skill | Merge into that skill |
| Skill invoked on every task | Promote the core constraint to a rule |
| Rule `paths:` globs match zero files | Fix the globs or delete the rule |
| Two rules overlap significantly | Merge into one |
| A convention is violated repeatedly | Tighten the rule or add a verification command |

## Naming convention

- Rules: `kebab-case.md` — descriptive noun or noun-phrase (`domain-invariants`, `generated-code`)
- Skills: `kebab-case/SKILL.md` — verb-phrase or domain name (`code-planning`, `api-design`)
- Path-scoped rules use a layer prefix (`domain-`, `frontend-`, `rust-`, `db-`) to signal scope from the filename. Global rules have no prefix. No numbering — filesystem order doesn't matter

## Cross-reference format

Reference other config files with relative paths from the project root:

- Rules → `.claude/rules/test-isolation.md` (project-local) or `claude/rules/git-conventions.md` (global)
- Skills → `/skill-name` (invoke syntax)
- Project docs → `CLAUDE.md`

**Global skills and rules must never reference project-local files** (`.claude/rules/`, project source paths). Global config is reusable across projects — project-specific bridging belongs in each project's `CLAUDE.md`. Use generic language like "check the project's `CLAUDE.md`" instead.

## Hygiene checklist

When modifying Claude config:

- [ ] Each rule file covers exactly one concern
- [ ] Path-scoped rules have valid `paths:` frontmatter
- [ ] `just claude-check-rule-scopes` passes, if the project defines it (no orphaned globs)
- [ ] No duplicate content across rules and skills
- [ ] If the repo defines project-local rules in `.claude/rules/`, any rules table in `CLAUDE.md` reflects their current contents
- [ ] Cross-references point to existing files
- [ ] Global skills/rules don't reference project-local files (`.claude/rules/`, project source paths)
