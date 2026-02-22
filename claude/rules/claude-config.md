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
- After directory restructuring, run `just check-rule-scopes` to verify all globs still resolve

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
- No prefixes, no numbering — filesystem order doesn't matter

## Cross-reference format

Reference other config files with relative paths from the project root:

- Rules → `.claude/rules/testing.md`
- Skills → `/skill-name` (invoke syntax)
- Project docs → `CLAUDE.md`

## Hygiene checklist

When modifying Claude config:

- [ ] Each rule file covers exactly one concern
- [ ] Path-scoped rules have valid `paths:` frontmatter
- [ ] `just check-rule-scopes` passes (no orphaned globs)
- [ ] No duplicate content across rules and skills
- [ ] `CLAUDE.md` rules table reflects current `.claude/rules/` contents
- [ ] Cross-references point to existing files
