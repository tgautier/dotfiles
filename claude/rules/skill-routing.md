# Skill Routing

How to combine skills for multi-skill tasks and how to disambiguate when intent could map to several. Companion to `claude/rules/skill-triggers.md`, which defines the base mappings; this rule defines how to compose them.

## Composite workflows

Most real tasks need multiple skills. When a task matches a pattern below, load all listed skills — primary first.

| Task shape | Primary | Also load | Trigger signals |
| --- | --- | --- | --- |
| Full-stack feature (API + page) | project feature skill | `/rust`, `/api-design`, `/react-router`, `/react`, `/css-responsive` | "add X feature", "new endpoint with UI" |
| API endpoint (no frontend) | `/rust` | `/api-design` | "add endpoint", "new handler" |
| Frontend page with data | `/react-router` | `/react`, `/css-responsive` | "new page", "add a route with data", "new page with loader" |
| Form mutation | `/react-router` | `/ux-design` | "form submission", "mutation", "add an action" |
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
| Full-stack feature with mobile | project feature skill | `/flutter`, `/rust`, `/api-design` | "add X to mobile", "new mobile screen", "API + mobile" |
| Flutter feature with generated client | `/flutter` | `/api-design` | "new screen with API data", "Flutter + REST" |
| Flutter design system | `/flutter` | `/ux-design` | "Flutter theming", "design tokens in Flutter" |
| New project scaffold | `/code-planning` | language skill (`/rust`, `/typescript`, `/phoenix`, `/flutter`) | "new project", "scaffold X", "create X from scratch", "basic X app" |

For full-stack features: check the project's `CLAUDE.md` for an end-to-end feature skill (e.g., `/new-feature`) that orchestrates the pipeline order.

## Disambiguation

When intent is ambiguous, prefer the more specific skill:

- "Fix a bug" → investigate first, then load the skill matching the root cause layer
- "Add validation" → `/rust` if server-side, `/ux-design` if form UX, `/react` if client logic
- "Refactor" → load the skill matching the code layer being refactored
- "Write tests" → `/typescript` (testing methodology), plus the layer-specific skill for context
