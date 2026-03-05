# Skill Triggers

Routing table for skill selection. Always loaded — no path scoping, because intent-based routing must be available regardless of which files are open.

## File-pattern triggers

When editing files that match a pattern below, load the corresponding skill before making changes.

| File pattern | Skill | Why |
| --- | --- | --- |
| `Justfile`, `justfile`, `*.just` | `/just` | Rare edits, specific conventions easy to forget |
| `*.md` | `/markdown` | Consistent formatting across all Markdown files |
| `docs/**` | `/documentation` | Doc structure, navigation, drift prevention |
| `**/CLAUDE.md`, `.claude/**`, `claude/**`, `memory/**` | `/claude-authoring` | Config structure and authoring conventions |

## Task-triggered skills

When the user's request matches an intent below, invoke the skill before starting work. Match on meaning, not exact keywords — examples are illustrative, not exhaustive.

| Skill | Intent | Example signals |
| --- | --- | --- |
| `/code-planning` | Planning before implementation | "plan", "design the approach", "how should we" |
| `/code-research` | Evaluating approaches or sources | "research", "compare options", "best practice" |
| `/claude-authoring` | Writing or auditing Claude config | "audit rules", "write a rule", "config hygiene" |
| `/rust` | Rust handlers, models, errors, config | "add a handler", "new model", "Rust error" |
| `/react` | React components, hooks, routes, loaders | "add a component", "new route", "write a hook" |
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
| `/project-audit` | Comprehensive project health audit | "full audit", "audit the project", "check for drift", "are our rules still accurate" |

## Composite workflows

Most real tasks need multiple skills. When a task matches a pattern below, load all listed skills — primary first.

| Task shape | Primary | Also load | Trigger signals |
| --- | --- | --- | --- |
| Full-stack feature (API + page) | project feature skill | `/rust`, `/api-design`, `/react` | "add X feature", "new endpoint with UI" |
| API endpoint (no frontend) | `/rust` | `/api-design` | "add endpoint", "new handler" |
| Frontend page with data | `/react` | `/css-responsive` | "new page", "add a route with data" |
| Database/schema change | `/domain-design` | `/rust` | "add a migration", "new column", "change schema" |
| Design system work | `/ux-design` | `/css-responsive` | "update tokens", "theme", "component variants" |
| Dashboard or analytics | `/saas-product` | `/react`, `/css-responsive` | "build dashboard", "add charts", "KPI cards" |
| Security hardening | `/web-security` | `/rust` or `/react` | "security audit", "pen test findings" |
| Testing campaign | `/typescript` | `/react` or `/rust` | "add test coverage", "write E2E tests" |
| Performance optimization | `/typescript` | `/css-responsive` | "bundle analysis", "lighthouse", "CLS" |
| Pre-push workflow | `/roborev` | — | "push my changes", "ready to push" |
| Complex domain feature | `/requirements` | `/domain-design`, `/code-planning` | "new entity", "new domain concept", "multi-entity feature" |
| Full-stack Phoenix feature | `/phoenix` | `/api-design`, `/domain-design` | "add LiveView with Ecto", "new Phoenix feature", "LiveView + schema" |
| Phoenix testing campaign | `/phoenix` | `/domain-design` | "write LiveView tests", "test Ecto queries" |

For full-stack features: check the project's `CLAUDE.md` for an end-to-end feature skill (e.g., `/new-feature`) that orchestrates the pipeline order.

## Disambiguation

When intent is ambiguous, prefer the more specific skill:

- "Fix a bug" → investigate first, then load the skill matching the root cause layer
- "Add validation" → `/rust` if server-side, `/ux-design` if form UX, `/react` if client logic
- "Refactor" → load the skill matching the code layer being refactored
- "Write tests" → `/typescript` (testing methodology), plus the layer-specific skill for context
