---
name: documentation
description: >
  Documentation audit and authoring methodology for keeping project docs accurate, navigable, and in sync with code.
  Covers: doc auditing, drift detection, structure, writing style, navigation, doc types, maintenance discipline.
  Use when: auditing stale docs, writing new documentation, restructuring docs/, or reviewing doc quality.
version: 1.0.0
date: 2026-02-25
user-invocable: true
argument-hint: "audit, write <topic>, or restructure"
---

# Documentation

Methodology for writing, auditing, and maintaining project documentation. Docs exist to orient developers quickly and accurately — stale docs are worse than no docs because they create false confidence.

> **Scope boundary:** This skill covers human-written docs (`docs/`, `README.md`). For generated artifacts (OpenAPI, TS client, schema files) → check the project's generated-code rule. For Claude config files (rules, skills, CLAUDE.md, memory) → `/claude-authoring`.

## 1. Documentation types

Each doc type has a distinct audience and update cadence:

| Type | Audience | Purpose | Update trigger |
| --- | --- | --- | --- |
| **README.md** | New developers, GitHub visitors | First impression, setup, quick orientation | Setup steps change, new prerequisites, project scope changes |
| **Architecture** | All developers | System structure, request flow, tech stack | New services, new layers, structural changes |
| **API reference** | Frontend developers, integrators | Endpoints, params, responses, errors | Any endpoint or validation change |
| **Domain/entities** | All developers | Business objects, invariants, relationships | Schema changes, new entities, rule changes |
| **Auth** | All developers, security reviewers | Auth flow, session management, config | Auth implementation changes |
| **Database** | Backend developers | Schema, migrations, CQRS, replication | Migration changes, new tables/columns |
| **Testing** | All developers | Test layers, commands, isolation, fixtures | New test infrastructure, new test patterns |
| **Features/roadmap** | Product stakeholders, developers | What's shipped, what's planned | Features ship or plans change |
| **Audit/report** | Historical reference | Point-in-time assessment | Findings resolved or new audit performed |
| **Executive summary** | Leadership, new team members | Vision, methodology, philosophy | Rare — only when strategy changes |

## 2. Auditing existing docs

### Process

1. **Inventory** — list every doc file with its line count and last-modified date
2. **Cross-reference** — for each doc, compare claims against actual code:
   - Endpoints documented vs. endpoints in router
   - Schema documented vs. actual `schema.rs` or migrations
   - Features marked "planned" vs. features actually shipped
   - Auth status vs. actual auth implementation
   - Commands documented vs. actual Justfile recipes
3. **Classify findings**:
   - **Critical** — doc claims the opposite of reality (e.g., "API is unauthenticated" when auth is enforced)
   - **High** — significant missing content (undocumented endpoints, unresolved audit findings)
   - **Medium** — incomplete or outdated details (wrong field names, missing params)
   - **Low** — style, formatting, minor wording

### Common drift patterns

| Pattern | Signal | Fix |
| --- | --- | --- |
| Outdated auth status | "unauthenticated", "future", "TODO" | Update to reflect current auth implementation |
| Missing endpoints | Router has more routes than docs list | Add undocumented endpoints to API reference |
| Stale audit findings | Findings marked "open" for resolved bugs | Mark as resolved with commit/PR reference |
| Planned features that shipped | "planned", "future", "coming soon" labels | Move to Current Features section |
| Wrong field names | `type` vs `kind`, `amount` vs `value` | Grep codebase for actual field name, update docs |
| Missing pagination | Endpoint has limit/offset but docs don't mention it | Document query params with defaults and limits |
| Missing error responses | Only 200/400 documented, but 401/404/500 exist | Document all status codes the endpoint can return |

### Reporting

Present findings as a prioritized table:

```markdown
| Priority | Issue | File | Impact |
| --- | --- | --- | --- |
| Critical | Auth status wrong | docs/api.md | Misleading |
| High | 3 endpoints missing | docs/api.md | 50% undocumented |
```

## 3. Writing new documentation

### Structure principles

- **Title** — `# Project Name - Topic` (consistent across all docs)
- **Overview/intro** — one paragraph, no more. What this doc covers and who it's for
- **Tables for structured data** — endpoints, commands, config fields, properties
- **Code blocks for examples** — realistic data, not lorem ipsum
- **Diagrams for flows** — ASCII art for text-based docs, keep it readable
- **Cross-references** — link to related docs with `[Text](other-doc.md)`, don't duplicate content

### README.md specifically

The README is the project's front door. It must answer five questions:

1. **What is this?** — one-line description + key features
2. **What's the tech stack?** — bullet list of major technologies
3. **How do I set it up?** — prerequisites, setup command, auth setup
4. **How do I run it?** — dev server commands
5. **Where do I learn more?** — table of doc links

Keep the README under 120 lines. If a section grows beyond a few paragraphs, extract to a dedicated doc and link to it.

### API reference specifically

For each endpoint, document:

- Method and path
- Auth requirements
- Query parameters (with types, defaults, constraints)
- Request body (with validation rules table)
- Response body (with realistic example)
- Error responses (all possible status codes)
- CQRS pool usage (read vs. write)

### Writing style

- **Imperative for instructions** — "Run `just setup`", not "You should run `just setup`"
- **Present tense for descriptions** — "The API validates tokens", not "The API will validate tokens"
- **No hedging** — "Requires authentication", not "Should probably require authentication"
- **Concrete over abstract** — show the actual command, actual config value, actual response
- **Consistent terminology** — pick one term and use it everywhere (e.g., `kind` not `type`)

## 4. Navigation and discoverability

### Doc file organization

- One file per concern (auth, API, database, testing — not one mega-doc)
- README.md links to all docs via a table
- Docs cross-reference each other where related (auth doc links to API doc for endpoint details)

### Within-file navigation

- Use `---` horizontal rules to separate major sections
- Use descriptive headings that work as table-of-contents entries
- Put the most-referenced content first (endpoints before error codes, current features before roadmap)

### Cross-reference conventions

- Link to other docs: `See [Authentication](authentication.md) for details`
- Link to external tools: `Swagger UI at http://localhost:3001/swagger-ui`
- Link to code: reference file paths, not line numbers (lines change)
- Never duplicate content across docs — link instead

## 5. Preventing drift

### The core discipline

Documentation is a **deliverable**, not an afterthought. A feature is not shipped until its docs are updated. A bug fix is not complete if the audit report still lists it as open.

### Triggers for doc updates

When any of these happen, docs must be updated in the same PR:

- New endpoint added → API reference
- Endpoint behavior changed → API reference
- Validation rules changed → API reference + entities
- New migration → database doc
- Feature shipped → features doc (planned → current)
- Auth flow changed → authentication doc
- Setup steps changed → README
- New command added → README commands table
- Bug fixed that was tracked in audit → audit report

### Automation opportunities

- Path-scoped rules that auto-load when touching code files — reminding to check docs
- Generated docs (Swagger UI, OpenAPI) eliminate drift for API signatures
- `just check` or `just pre-commit` could include a doc freshness check (future)

### What to skip

Not every code change needs a doc update:

- Refactoring internals that don't change behavior
- Adding tests (unless it changes testing docs infrastructure)
- Style/formatting changes
- Dependency updates (unless they change setup steps)

## 6. Maintenance cadence

### Per-PR

- Update docs for any behavior change (enforced by project rule if present)
- Check that no doc still describes the old behavior

### Quarterly (or after major milestones)

- Full audit: run the process from section 2
- Check all "planned" features — have any shipped?
- Check all audit findings — have any been resolved?
- Verify README setup steps still work end-to-end

### Anti-patterns

- **Write-once docs** — written at project start, never updated. Guaranteed to drift
- **Mega-docs** — one file covering everything. Hard to navigate, hard to update
- **Duplicated content** — same info in README, API doc, and architecture doc. Triples the maintenance burden
- **Aspirational docs** — describing features that don't exist yet as if they do
- **Over-documentation** — documenting implementation details that change frequently. Document behavior and contracts, not internals
- **Comment-level docs in doc files** — "TODO: update this section" left for months
