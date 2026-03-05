---
user-invocable: true
description: Comprehensive project health audit — drift detection, tech currency, cross-reference integrity, and codebase quality
---

# Project Audit

Methodology for periodic comprehensive project audits. Verifies that rules, skills, documentation, and code stay aligned as the project evolves.

## When to Audit

| Trigger | Scope |
|---|---|
| Quarterly (scheduled) | Full audit — all dimensions |
| After major dependency upgrade | Tech currency — affected skills |
| After adding/removing rules or skills | Cross-reference integrity |
| After significant architectural change | Drift detection — affected rules |
| Before major release | Full audit |

Automated structural checks run continuously via `just check` (includes `claude-check-accuracy`). This skill covers the AI-driven semantic audit that automation cannot perform.

## Two Layers

### Layer 1: Automated (CI-safe)

These run in `just check` and catch structural drift deterministically:

| Recipe | What it catches |
|---|---|
| `claude-check-rule-scopes` | Path-scoped rule globs that match no files |
| `claude-check-escaping` | zsh `\!` corruption in rule/skill files |
| `claude-check-refs` | Broken cross-references to rules or skills |
| `claude-check-accuracy` | CLAUDE.md commands table listing nonexistent recipes; rule counts that don't match filesystem |

### Layer 2: AI-driven (periodic)

Semantic drift that no script can detect — requires reading code and comparing to rules:

- Does the CQRS rule match how handlers actually use pools?
- Do validation rules match the actual validation code?
- Are skill recommendations current with dependency versions?
- Does the CLAUDE.md request flow diagram match the actual middleware chain?
- Is the testing trophy shape still accurate?

## Audit Dimensions

### 1. Drift Detection

Rules and skills whose content no longer matches code reality.

**Method:** For each rule, read the rule then read the code it governs. Compare claims against actual patterns.

**Checklist:**
- [ ] Each always-loaded rule — content matches code behavior
- [ ] Each path-scoped rule — content matches code in scoped paths
- [ ] CLAUDE.md request flow — matches actual auth/middleware chain
- [ ] CLAUDE.md endpoint table — matches actual route registrations
- [ ] CLAUDE.md service URLs — matches actual docker-compose ports
- [ ] CLAUDE.md directory structure — matches actual filesystem
- [ ] CLAUDE.md dangerous operations — all warnings still relevant

### 2. Tech Currency

Skills that reference outdated framework versions or deprecated patterns.

**Method:** For each tech-specific skill, compare recommendations against the project's actual dependency versions and the framework's latest documentation.

**Checklist:**
- [ ] `/rust` — Axum, Diesel, utoipa versions match `Cargo.toml`
- [ ] `/react` — React, React Router versions match `package.json`; patterns match current API
- [ ] `/typescript` — TypeScript version; strict flags still optimal
- [ ] `/css-responsive` — Tailwind version; utility patterns still valid
- [ ] `/web-security` — OAuth/OIDC standards still current (RFC numbers, draft status)
- [ ] `/observability` — OTEL SDK versions; browser SIG status

### 3. Cross-Reference Integrity

Broken links between config files that cause hallucinated guidance.

**Method:** Automated checks handle existence verification. AI audit verifies semantic correctness — does the referenced section still say what the referencing file assumes it says?

**Checklist:**
- [ ] `skill-triggers.md` — all existing skills are routed (no orphaned skills)
- [ ] `skill-triggers.md` — composite workflows reference valid combinations
- [ ] CLAUDE.md rules index — matches actual rule files and their scoping
- [ ] Bidirectional cross-references — if A references B, B references A

## Execution

### Setup

Launch parallel subagents for independent research. Recommended split:

1. **Rust API agent** — handlers, models, migrations, CQRS, validation, auth, tests
2. **Frontend agent** — routes, components, utilities, tests, config, telemetry
3. **Infrastructure agent** — Justfile, Docker, CI/CD, config files, hooks
4. **Skills/rules agent** — all global skills, all rules, skill-triggers, cross-references

### Codebase Quality

Beyond drift, assess overall codebase health:

- [ ] **API** — error handling, per-user scoping, BigDecimal preservation, security headers
- [ ] **Frontend** — SSR safety, error boundaries, accessibility, responsive patterns
- [ ] **Tests** — coverage gaps, correct layer selection, DB isolation
- [ ] **Infrastructure** — Docker health checks, image pinning, CI integrity
- [ ] **Dependencies** — outdated packages, security advisories (`just dep-audit`)

### Output

After completing the audit, produce:

1. **Summary table** — area, verdict, issues found, severity
2. **GitHub issues** — one per finding, labeled by severity and category
3. **Memory update** — save audit date, key findings, and known minor issues to project memory
4. **Rule/skill updates** — fix any drift discovered during the audit

## Cadence

| Frequency | What to run |
|---|---|
| Every commit | `just check` (automated structural checks) |
| Every PR | `just pre-commit` (structural checks + tests) |
| Monthly | `just audit` (structural checks + dependency vulnerabilities) |
| Quarterly | `/project-audit` (full AI-driven semantic audit) |
| After major upgrade | `/project-audit` scoped to affected dimensions |

## Anti-patterns

- Running the AI audit without first running automated checks (`just check`)
- Auditing without creating issues — findings decay if not tracked
- Fixing drift in the code but not updating the rule (or vice versa)
- Skipping the memory update — next audit loses context from this one
- Auditing only the layer you changed — drift accumulates in untouched areas
