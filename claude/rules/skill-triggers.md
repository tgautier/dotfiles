---
paths:
  - Justfile
  - justfile
  - "*.just"
  - "*.md"
  - "**/CLAUDE.md"
  - ".claude/**"
  - "claude/**"
  - "memory/**"
---

# Skill Triggers

When editing files that match a pattern below, load the corresponding skill before making changes.

| File pattern | Skill | Why |
|---|---|---|
| `Justfile`, `justfile`, `*.just` | `/just` | Rare edits, specific conventions easy to forget |
| `*.md` | `/markdown` | Consistent formatting across all Markdown files |
| `**/CLAUDE.md`, `.claude/**`, `claude/**`, `memory/**` | `/claude-authoring` | Config structure and authoring conventions |

## Task-triggered skills

When the user's request matches an intent below, invoke the corresponding skill before starting work. Match on meaning, not exact keywords — the examples are illustrative, not exhaustive.

| Skill | Intent | Example phrases |
|---|---|---|
| `/code-planning` | Planning an implementation | "plan", "design the approach", "how should we implement" |
| `/code-research` | Researching patterns or evaluating approaches | "research", "evaluate", "compare options", "what's best practice" |
| `/claude-authoring` | Auditing, writing, or reviewing Claude config | "audit rules", "review config hygiene", "write a rule for" |
| `/rust` | Substantial Rust work | "add a handler", "new model", "write a migration" |
| `/typescript` | Substantial frontend work | "add a component", "new route", "write a hook" |
| `/api-design` | Designing or reviewing API contracts | "design the endpoint", "review the API", "what status code" |
| `/domain-design` | Modeling business domains | "model the domain", "aggregate boundaries", "schema evolution" |
| `/observability` | Instrumenting or adding telemetry | "add tracing", "instrument", "add metrics", "health check" |
| `/web-security` | Security implementation or review | "security review", "add auth", "configure CORS", "harden" |
| `/github` | After every push | Per `git-conventions` rule — automatic, not user-triggered |
