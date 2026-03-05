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

Automated structural checks run continuously via the project's check recipe (e.g., `just check`). This skill covers the AI-driven semantic audit that automation cannot perform.

## Two Layers

### Layer 1: Automated (CI-safe)

Check the project's `CLAUDE.md` for available recipes. Common automated checks:

- Path-scoped rule globs that match no files
- zsh `\!` corruption in rule/skill files
- Broken cross-references to rules or skills
- CLAUDE.md accuracy — commands table listing nonexistent recipes, rule counts that don't match filesystem

Run all automated checks first. Fix structural issues before starting the AI-driven audit.

### Layer 2: AI-driven (periodic)

Semantic drift that no script can detect — requires reading code and comparing to rules:

- Do rules match how the code actually behaves?
- Do skill recommendations match the project's current dependency versions?
- Does CLAUDE.md accurately describe the project's architecture and workflows?
- Are testing conventions still reflected in actual test patterns?

## Audit Dimensions

### 1. Drift Detection

Rules and skills whose content no longer matches code reality.

**Method:** For each rule, read the rule then read the code it governs. Compare claims against actual patterns.

**Checklist:**
- [ ] Each always-loaded rule — content matches code behavior
- [ ] Each path-scoped rule — content matches code in scoped paths
- [ ] CLAUDE.md architecture description — matches actual project structure
- [ ] CLAUDE.md commands table — matches actual available recipes
- [ ] CLAUDE.md directory structure — matches actual filesystem

### 2. Tech Currency

Skills that reference outdated framework versions or deprecated patterns.

**Method:** For each tech-specific skill, compare recommendations against the project's actual dependency versions and the framework's latest documentation.

**Checklist:**
- [ ] Each tech-specific skill — recommended patterns match installed versions
- [ ] Security skills — referenced standards still current (RFC numbers, draft status)
- [ ] Build/tooling skills — recommended flags and config still optimal

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

Launch parallel subagents for independent research. Split by project layer — check the project's `CLAUDE.md` for its architecture and layer boundaries. Common splits:

- **Backend agent** — handlers, models, data access, auth, tests
- **Frontend agent** — routes, components, utilities, tests, config
- **Infrastructure agent** — build config, CI/CD, Docker, hooks
- **Skills/rules agent** — all rules, all skills, skill-triggers, cross-references

### Codebase Quality

Beyond drift, assess overall codebase health. Check the project's `CLAUDE.md` for specific quality concerns and dangerous operations. Common areas:

- [ ] **Error handling** — consistent patterns, no swallowed errors
- [ ] **Security** — auth, input validation, dependency advisories
- [ ] **Tests** — coverage gaps, correct layer selection, isolation
- [ ] **Infrastructure** — CI integrity, dependency pinning, health checks

### Output

After completing the audit, produce:

1. **Summary table** — area, verdict, issues found, severity
2. **GitHub issues** — one per finding, labeled by severity and category
3. **Memory update** — save audit date, key findings, and known minor issues to project memory
4. **Rule/skill updates** — fix any drift discovered during the audit

## Anti-patterns

- Running the AI audit without first running automated checks
- Auditing without creating issues — findings decay if not tracked
- Fixing drift in the code but not updating the rule (or vice versa)
- Skipping the memory update — next audit loses context from this one
- Auditing only the layer you changed — drift accumulates in untouched areas
