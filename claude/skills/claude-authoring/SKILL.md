---
name: claude-authoring
description: >
  Methodology for writing Claude Code rules, skills, CLAUDE.md files, and memory.
  Covers: decision test, rule structure, skill structure, CLAUDE.md patterns, memory discipline, evolution, hygiene.
  Use when: creating or editing rules, skills, CLAUDE.md, or memory files.
  Companion to the `claude-config.md` rule (system structure) and `/markdown` skill (formatting).
version: "1.0"
date: 2026-02-23
user-invocable: true
argument-hint: ""
---

# Claude Authoring

Methodology for writing Claude Code configuration files: rules, skills, CLAUDE.md, and memory. The `claude-config.md` rule covers *system structure* (tiers, locations, loading). This skill covers *how to write them well*.

## 1. Decision test

Where does something belong? Extended from the brief test in `claude-config.md`:

| If... | Then... | Example |
|---|---|---|
| Must hold even if nobody invokes it | **Rule** | "Never use write_pool for GET handlers" |
| Is a methodology applied deliberately | **Skill** | "How to design a REST endpoint" |
| Is project architecture, commands, or concern map | **CLAUDE.md** | Tech stack, directory structure, verification commands |
| Is a stable pattern learned across sessions | **Memory** | "User prefers `just` over raw yarn" |

### Edge cases

- **Convention that gets violated repeatedly** — start as a rule, not a skill. Rules auto-load and prevent the violation
- **Methodology invoked on every task** — promote its core constraint to a rule, keep the methodology as a skill
- **Project-specific constraint** — project-local rule (`.claude/rules/`), not global
- **One-off decision** — CLAUDE.md or memory, not a rule (rules are for recurring patterns)
- **Debugging insight** — memory (topic file), not a rule (too narrow for a rule)

## 2. Writing rules

### Structure

````markdown
---
paths:
  - api/src/handlers/**
  - api/src/main.rs
---

# Rule Title

Brief context sentence — why this rule exists.

## Rules

- Imperative statements: "Never X", "Always Y", "Use Z when..."
- Each rule is a constraint, invariant, or convention

## Examples

```rust
// CORRECT — shows the right pattern
// WRONG — shows the anti-pattern
```
````

### Sizing

- **One concern per file** — if a rule covers two unrelated topics, split it
- **80-line signal** — rules over 80 lines likely cover too much
- If a rule has a long "how to" section, extract that into a skill and reference it

### Path scoping

- Add `paths:` frontmatter when a rule is relevant only to specific directories
- Omit `paths:` when the rule applies globally (CQRS, testing, config)
- Use glob patterns: `**` for recursive, `*` for single-level
- Verify globs resolve: `just claude-check-rule-scopes` (if the project defines it)

### Naming

- `kebab-case.md` — descriptive noun or noun-phrase
- Path-scoped rules use a layer prefix: `domain-`, `frontend-`, `rust-`, `db-`
- Global rules have no prefix: `invariants`, `cqrs`, `generated-code`

### What makes a good rule

- **Constraints** — "never do X" (e.g., never cross CQRS pools)
- **Invariants** — "X must always hold" (e.g., BigDecimal end-to-end)
- **Conventions** — "when doing X, use Y" (e.g., snake_case in SQL)
- **Not methodology** — "how to design X" belongs in a skill

### Anti-patterns

- Rules that read like tutorials or guides — extract to a skill
- Rules with more examples than constraints — trim examples
- Rules that duplicate another rule — merge or cross-reference
- Rules that reference project-local files from global config — use generic language

## 3. Writing skills

### Frontmatter

```yaml
---
name: skill-name
description: >
  One-paragraph description of what the skill covers and when to use it.
  First sentence is the summary. Use "Covers:" and "Use when:" patterns.
version: "1.0"
date: 2026-02-23
user-invocable: true
argument-hint: "optional hint for arguments"
---
```

Required fields: `name`, `description`, `version`, `date`, `user-invocable`.

Advanced fields (use when needed):
- `allowed-tools` — restrict which tools the skill can use
- `context` — additional files to load when skill is invoked
- `agent` — run as a subagent with specific configuration
- `argument-hint` — shown in autocomplete to hint at expected arguments

### Body structure

- **Numbered sections** (`## 1. Section Name`) — provides clear progression
- **Scope boundary** — explicitly state what the skill does NOT cover, with cross-references
- **Examples** — show correct and incorrect patterns with `// CORRECT` / `// WRONG` markers
- **Anti-patterns section** — common mistakes, ideally as a table

### Sizing

- **200-800 lines typical** — enough depth to be useful, not so long it's ignored
- Under 200 lines: might be too shallow to justify a skill — consider a rule instead
- Over 800 lines: split into focused skills or extract sub-skills

### Cross-references

- Reference other skills with invoke syntax: `/skill-name`
- Reference rules with relative paths: `claude/rules/rule-name.md`
- Never reference project-local files from global skills

## 4. Writing CLAUDE.md

### Role

CLAUDE.md is the project epicenter — the first file Claude reads for any task. It should orient Claude to the project quickly.

### What belongs here

- **Project summary** — one-line description, tech stack
- **How to work here** — model-first pipeline, verification commands
- **Architecture** — request flow, directory structure, tech stack
- **Commands** — `just` recipes, non-obvious commands
- **Configuration** — config files, env vars, how they relate
- **Concern map** — index of all skills and rules by domain
- **Rules index** — table of all rules with scope and purpose
- **Common gotchas** — things that bite developers repeatedly

### What does NOT belong

- Detailed methodology (→ skills)
- Constraints that must auto-load (→ rules)
- Session-specific context (→ memory)
- Full API documentation (→ Swagger UI or generated docs)

### Patterns

- Use `@path/to/file` import syntax for content that lives in other files
- Child directory `CLAUDE.md` files auto-load when working in that directory
- Keep tables for structured reference (commands, rules), prose for narrative (architecture, flow)
- Update the rules index and concern map when adding/removing rules

### Sizing

- No strict limit, but aim for quick orientation — a developer should understand the project in under 2 minutes of reading
- Move detailed content to rules or skills and cross-reference

## 5. Writing memory

### MEMORY.md

- **200-line cap** — loaded at conversation startup, always in context
- Organize semantically by topic using `##` sections, not chronologically
- Keep entries concise — one line per fact when possible
- Update or remove outdated entries rather than appending
- No duplicate content — check existing sections before adding

### Topic files

- Create `memory/topic-name.md` for detailed notes on specific topics
- Link from MEMORY.md: "See `memory/topic-name.md` for details"
- Topic files are loaded on demand, not at startup — size is less critical

### What to save

- Stable patterns confirmed across multiple interactions
- Key architectural decisions, important file paths, project structure
- User preferences for workflow, tools, and communication style
- Solutions to recurring problems and debugging insights
- Explicit user requests ("always use bun", "never auto-commit")

### What NOT to save

- Session-specific context (current task, in-progress work)
- Unverified conclusions from reading a single file
- Anything that duplicates CLAUDE.md or rules
- Speculative or temporary information

## 6. Evolution triggers

| Signal | Action |
|---|---|
| Rule > 80 lines | Split into focused rules, or extract methodology into a skill |
| Rule referenced only from one skill | Merge into that skill |
| Skill invoked on every task | Promote core constraint to a rule |
| Rule `paths:` globs match zero files | Fix the globs or delete the rule |
| Two rules overlap significantly | Merge into one |
| Convention violated repeatedly | Tighten the rule or add a verification command |
| Skill < 200 lines | Consider merging into a rule if it's mostly constraints |
| Skill > 800 lines | Split into focused skills |
| CLAUDE.md has detailed methodology | Extract to a skill, cross-reference |
| Memory entry contradicts a rule | Remove the memory entry (rules are authoritative) |

## 7. Hygiene checklist

Before committing Claude config changes:

- [ ] Each rule file covers exactly one concern
- [ ] Path-scoped rules have valid `paths:` frontmatter
- [ ] `just claude-check-rule-scopes` passes (no orphaned globs), if the project defines it
- [ ] No duplicate content across rules and skills
- [ ] Rules table in `CLAUDE.md` reflects current `.claude/rules/` contents (if applicable)
- [ ] Cross-references point to existing files
- [ ] Global skills/rules don't reference project-local files
- [ ] Skill frontmatter has all required fields (`name`, `description`, `version`, `date`, `user-invocable`)
- [ ] New rules are under 80 lines
- [ ] New skills are 200-800 lines
- [ ] MEMORY.md stays under 200 lines after updates
- [ ] Naming follows convention (kebab-case, layer prefixes for path-scoped rules)
