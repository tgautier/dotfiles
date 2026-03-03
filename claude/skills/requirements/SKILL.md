---
name: requirements
description: |
  Pre-implementation requirements elicitation using EARS notation.
  Covers: acceptance criteria, edge cases, entity sketches, open questions.
  Use when: clarifying what to build before implementation on complex features
  (new entities, multi-endpoint features, new domain concepts).
  NOT for: simple additions (new column, sort option, bug fix).
version: 1.0.0
date: 2026-02-27
user-invocable: true
---

# Requirements

Pre-implementation thinking tool for complex features. Produces disposable requirements artifacts — specs are thinking tools, not sources of truth. Once implemented, the code absorbs and replaces them.

> **Scope boundary:** This skill defines *what* to build. For *how* to plan the implementation, see `/code-planning`. For domain modeling decisions, see `/domain-design` (section 10 pre-design checklist). For the end-to-end build pipeline, check the project's `CLAUDE.md` for a feature pipeline skill.

---

## When to use

Use this skill before implementation when a feature involves:

- A new domain entity or aggregate
- Multiple new endpoints working together
- A new domain concept that needs naming and boundary definition
- Cross-cutting behavior changes (e.g., new permission model, new currency support)
- Features where edge cases are non-obvious

Skip this skill for:

- Adding a column to an existing table
- Adding a sort/filter option to an existing endpoint
- Bug fixes with clear reproduction steps
- Simple CRUD additions to existing entities

---

## EARS notation

EARS (Easy Approach to Requirements Syntax) produces unambiguous, testable requirements. Five patterns:

### 1. Ubiquitous

Requirements that always hold, with no trigger or condition.

```
The system shall store all monetary values as NUMERIC(19,4).
The system shall never aggregate monetary values across different currencies without conversion.
```

### 2. Event-driven

Triggered by a specific event — uses "When."

```
When a user creates an asset, the system shall validate that the currency is a 3-letter ISO 4217 code.
When a transaction is deleted, the system shall archive it to the deleted_record table before removal.
```

### 3. State-driven

Active while a condition holds — uses "While."

```
While the replica database is unreachable, the system shall serve read requests from the primary.
While an import job is in progress, the system shall reject concurrent imports for the same account.
```

### 4. Conditional

Applies only when a precondition is true — uses "If...then."

```
If the asset value exceeds 1,000,000, then the system shall require additional verification.
If the user has no assets, then the dashboard shall display an empty state with onboarding guidance.
```

### 5. Complex

Combines multiple patterns.

```
While the system is in maintenance mode, when a user attempts a write operation, the system shall return 503 with a retry-after header.
If the account has multi-currency assets, when the user requests a portfolio summary, the system shall group totals by currency.
```

---

## Output format

When invoking `/requirements`, produce these sections:

### Acceptance criteria

List requirements in EARS notation. Group by feature area. Each requirement must be independently testable.

### Entity sketch

For new entities: name, key fields, relationships, aggregate boundary. Not a full schema — just enough to validate the domain model before implementation.

```
Asset
  - id: UUID (PK)
  - name: String (required, 1-255 chars)
  - kind: AssetKind enum (stock, bond, cash, real_estate, crypto, other)
  - currency: Currency (ISO 4217, 3 uppercase letters)
  - value: Money (NUMERIC(19,4), positive)
  - Aggregate root: yes
  - References: belongs to User (by user_id)
```

### Edge cases

Enumerate scenarios that are easy to overlook:

- Boundary values (zero, negative, maximum precision)
- Concurrent access (two users editing the same entity)
- Missing/null states (what happens when optional fields are absent?)
- Currency edge cases (same value, different currencies — are they equal?)
- Pagination boundaries (empty pages, last page, single-item pages)

### Open questions

List anything that needs a decision before implementation. Tag each with who should answer (domain expert, tech lead, designer).

---

## Where requirements go

- **PR description** — acceptance criteria in the PR body, not a separate spec file
- **GitHub issue** — if the feature needs discussion before a PR, put requirements in the issue body
- **Never a living spec file** — no `docs/specs/` directory, no versioned requirement documents. The code is the spec after implementation

---

## Cross-references

- `/domain-design` (section 10) — pre-design checklist that validates domain modeling decisions
- `/code-planning` — plan structure for the implementation phase
- Check the project's `CLAUDE.md` for an end-to-end pipeline skill and derivation rules
