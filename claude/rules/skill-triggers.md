# Skill Triggers

Routing tables for skill selection. Always loaded — no path scoping, because intent-based routing must be available regardless of which files are open. For composite workflows (combining skills) and disambiguation when intent maps to several skills, see `claude/rules/skill-routing.md`.

## File-pattern triggers

When editing files that match a pattern below, load the corresponding skill before making changes. A `PreToolUse` hook (`claude/hooks/skill-trigger-reminder.sh`) injects a reminder into context on every `Edit`/`Write` whose path matches a row. Keep the hook's pattern list in sync with this table when adding rows.

| File pattern | Skill | Why |
| --- | --- | --- |
| `Justfile`, `justfile`, `*.just` | `/just` | Rare edits, specific conventions easy to forget |
| `*.md` | `/markdown` | Consistent formatting across all Markdown files |
| `docs/**` | `/documentation` | Doc structure, navigation, drift prevention |
| `**/CLAUDE.md`, `.claude/**`, `claude/**`, `memory/**` | `/claude-authoring` | Config structure and authoring conventions |
| `Cargo.toml`, `*.rs` | `/rust` | Rust conventions, error handling, testing discipline |
| `*.tsx`, `*.jsx` | `/react` | React component patterns, hooks, composition |
| `tsconfig.json`, `*.ts`, `*.mts`, `*.cts` | `/typescript` | Type safety, testing, build configuration |
| `*.css`, `tailwind.config.*` | `/css-responsive` | Tailwind v4 conventions, responsive patterns |
| `*.ex`, `*.exs` | `/phoenix` | Elixir/Phoenix conventions, Ecto, HEEx |
| `*.dart`, `pubspec.yaml`, `pubspec.lock` | `/flutter` | Flutter architecture and widget patterns |
| `openapi.yaml`, `openapi.yml`, `*.openapi.yaml`, `*.openapi.yml` | `/api-design` | HTTP semantics, error format, pagination |

## Task-triggered skills

When the user's request matches an intent below, invoke the skill before starting work. Match on meaning, not exact keywords — examples are illustrative, not exhaustive.

| Skill | Intent | Example signals |
| --- | --- | --- |
| `/code-planning` | Planning before implementation | "plan", "design the approach", "how should we" |
| `/code-research` | Evaluating approaches or sources | "research", "compare options", "best practice" |
| `/claude-authoring` | Writing or auditing Claude config | "audit rules", "write a rule", "config hygiene" |
| `/rust` | Any Rust code — CLI, library, or service | "new rust project", "rust CLI", "cargo new", "add a handler", "new model", "Rust error" |
| `/react` | React components, hooks, composition | "add a component", "write a hook", "extract component" |
| `/react-router` | Route data loading, mutations, SSR | "new route with data", "form mutation", "loader", "action" |
| `/typescript` | Type safety, testing, build tooling | "write a test", "fix type error", "bundle size" |
| `/css-responsive` | Responsive layout, Tailwind, touch | "mobile layout", "responsive", "touch targets" |
| `/ux-design` | Design system, accessibility, form UX | "design tokens", "a11y audit", "form validation UX" |
| `/saas-product` | Product-level UX patterns | "onboarding", "empty state", "dashboard design" |
| `/api-design` | API contracts and HTTP semantics | "design the endpoint", "status code", "pagination" |
| `/domain-design` | Domain modeling and schema changes | "aggregate boundaries", "schema evolution" |
| `/observability` | Tracing, metrics, health checks | "add tracing", "instrument", "health check" |
| `/web-security` | Security review or hardening | "security review", "add auth", "CORS", "harden" |
| `/documentation` | Doc audit, writing, or restructuring | "audit docs", "update docs", "docs are stale", "revamp documentation" |
| `/roborev` | Automated review management | "check reviews", "fix findings", "review status", "before push" |
| `/project-management` | Writing issues or PR descriptions | "create an issue", "write a PR description", "file a bug", "plan work items" |
| `/requirements` | Clarifying what to build before implementation | "what should this do", "requirements", "acceptance criteria", "EARS", "user stories" |
| `/phoenix` | Phoenix/Elixir LiveView, Ecto, HEEx | "add a LiveView", "new migration", "Ecto query", "Phoenix route", "HEEx template" |
| `/flutter` | Flutter widgets, state, navigation, theming | "add a screen", "new widget", "Riverpod provider", "Flutter navigation", "dart model" |
| `/project-audit` | Comprehensive project health audit | "full audit", "audit the project", "check for drift", "are our rules still accurate" |

For composite workflows (multi-skill tasks) and ambiguity resolution, see `claude/rules/skill-routing.md`.
