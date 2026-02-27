---
name: domain-design
description: |
  Language-agnostic domain design skill for modeling business domains.
  Covers: bounded contexts, aggregates, entities, value objects, domain events,
  data modeling, schema evolution, system decomposition, and anti-patterns.
  Use when: designing new domain models, evaluating aggregate boundaries, planning
  schema changes, decomposing systems, or reviewing domain modeling decisions.
version: 1.0.0
date: 2026-02-22
user-invocable: true
---

# Domain Design

Language-agnostic guidance for modeling business domains. Covers the *what* of domain modeling — aggregates, bounded contexts, data modeling, schema evolution. Implementation skills handle the *how*:

- **Rust skill** (`/rust`) — newtypes, Diesel models, migrations
- **TypeScript skill** (`/typescript`) — branded types, discriminated unions
- **API Design skill** (`/api-design`) — resource design, pagination, error format

Based on Eric Evans (*Domain-Driven Design*), Vaughn Vernon (*Implementing Domain-Driven Design*, *Domain-Driven Design Distilled*), Martin Fowler (*Patterns of Enterprise Application Architecture*, refactoring.guru), and Microsoft Azure Architecture Center.

> **Project-specific:** Check the project's `CLAUDE.md` for domain-specific rules covering aggregate definitions, field mappings, validation rules, and financial correctness constraints.

---

## 1. Design Philosophy

The domain model reflects business reality, not database tables or UI screens.

- **Ubiquitous language** — code names match domain expert vocabulary. If the business says "asset kind," the code says `AssetKind`, not `asset_type` or `asset_category`. Rename code to match the domain, not the other way around
- **Model behavior, not just data** — entities and value objects carry the business logic that protects their invariants. A `Money` type that can represent negative amounts when the domain forbids it is a data structure, not a domain model
- **Start simple, extract complexity only when proven necessary** — a single module with clear boundaries beats premature microservice decomposition. Complexity is a cost; justify every addition
- **Separate what changes together from what changes independently** — this is the fundamental driver for aggregate boundaries, bounded contexts, and module structure

> **Scope boundary:** This skill defines *what* to model. For plan structure and task decomposition, see the **Code Planning skill** (`/code-planning`). For implementation patterns, see `/rust` or `/typescript`. For API contract design, see `/api-design`.

---

## 2. Bounded Contexts

A bounded context is an explicit boundary where a particular domain model applies. The same real-world concept can have different representations in different contexts — and that's correct, not a bug.

### When to draw boundaries

- Different teams own different parts of the domain
- The same word means different things in different parts of the system (e.g., "account" in billing vs authentication)
- Parts of the system change at different rates or have different quality requirements
- Different consistency or performance requirements exist across subdomains

### Context mapping patterns

When two bounded contexts interact, choose a relationship pattern:

| Pattern | When to use | Key characteristic |
|---------|-------------|-------------------|
| **Anti-Corruption Layer (ACL)** | Integrating with external/legacy systems | Translation layer isolates your model from theirs |
| **Shared Kernel** | Two contexts co-evolve and share a subset of the model | Both teams agree on the shared code; changes require coordination |
| **Open Host Service** | One context serves many consumers with a published API | Versioned, stable interface decoupled from internal model |
| **Customer-Supplier** | Upstream provides what downstream needs | Downstream has input into upstream's priorities |
| **Partnership** | Two contexts co-evolve with mutual dependency | Both teams coordinate releases and model changes |
| **Conformist** | Upstream has no incentive to accommodate downstream | Downstream adopts upstream's model as-is |
| **Separate Ways** | Integration cost exceeds benefit | Contexts don't interact; each solves the problem independently |

### Default choices

- **Default to ACL for external integrations** — never let an external system's data model leak into your domain. Translate at the boundary
- **Prefer Open Host Service when exposing functionality** — a stable published API decouples internal evolution from consumers
- **Bounded context is not microservice** — a context can be a module within a monolith, a separate service, or anything in between. The boundary is logical, not physical

### Context map documentation

Document context relationships explicitly. A context map shows which contexts exist, how they relate, and who owns each boundary. Keep it in a living document (not just code comments) that the team references during design discussions.

---

## 3. Aggregates

An aggregate is a cluster of domain objects treated as a single unit for data changes. Every aggregate has exactly one root entity.

### Vernon's four rules

1. **Protect true invariants in consistency boundaries** — an aggregate boundary exists precisely to enforce a business invariant that must be immediately consistent
2. **Design small aggregates** — 70% of aggregates should be a single root entity with value objects. Large aggregates cause contention, slow queries, and merge conflicts
3. **Reference other aggregates by identity only** — store the ID, not the object reference. This enforces loose coupling and enables independent loading
4. **Use eventual consistency outside aggregate boundaries** — if two aggregates need to stay in sync, use domain events, not transactions spanning both

### All modifications through the aggregate root

External code never reaches inside an aggregate to modify a child entity directly. The root exposes methods that enforce invariants and emit events.

### One repository per aggregate root

A repository loads and saves an entire aggregate. There is no repository for child entities — they're always accessed through the root.

### Decision table: when to split

| Signal | Action |
|--------|--------|
| Aggregate has > 5 entities | Consider splitting — it's likely two aggregates |
| Different fields change at different rates | Split along the change boundary |
| Concurrent edits cause frequent conflicts | Smaller aggregates reduce contention |
| A business rule only involves a subset of the fields | That subset might be its own aggregate |
| Loading the aggregate requires joining 4+ tables | Performance signal — consider splitting |
| Two users editing different parts of the "same" thing | They're editing different aggregates |

### Aggregate design process

1. Identify the business invariants that must be immediately consistent
2. Group the minimum set of entities/value objects required to enforce those invariants
3. Choose the root entity (the one that controls access and enforces rules)
4. Everything else references this aggregate by ID

> **Implementation:** For Rust newtype patterns and `From`/`TryFrom` layer conversions, see **Rust skill** (`/rust` §6). For three separate models per entity (Queryable, Insertable, input DTO), see **Rust skill** (`/rust` §5).

---

## 4. Entities and Value Objects

### Entities

- Have a unique **identity** that persists across state changes
- Equality is determined by ID, not by attribute values
- Can be mutable — their attributes change over time, but their identity doesn't
- Examples: `User`, `Order`, `Asset`, `Account`

### Value Objects

- Have **no identity** — defined entirely by their attributes
- **Immutable** — changing any attribute creates a new instance
- Equality is determined by comparing all attributes
- Examples: `Money`, `Currency`, `EmailAddress`, `DateRange`, `Address`

### Value objects cure primitive obsession

Replace bare primitives with value objects when the value has:

- Validation rules (email format, currency code format, positive amounts)
- Behavior (money arithmetic, date range overlap detection)
- Multiple fields that travel together (amount + currency = money)

| Bare primitive | Value object | Why |
|---------------|-------------|-----|
| `String` | `EmailAddress` | Format validation, normalization |
| `String` | `Currency` | 3-letter ISO 4217, uppercase |
| `f64` / `BigDecimal` | `Money(amount, currency)` | Prevents cross-currency arithmetic |
| `(DateTime, DateTime)` | `DateRange` | Enforces start < end, overlap detection |
| `Uuid` | `AssetId`, `UserId` | Prevents mixing entity IDs at compile time |
| `i32` | `Quantity` | Enforces positive, prevents negative inventory |

### Where business logic belongs

Business logic belongs on the entity or value object that protects the invariant:

- `Money.add(other: Money)` validates same currency before adding — not the caller
- `Order.addItem(item)` checks inventory and order limits — not the handler
- `DateRange.overlaps(other)` is a method on `DateRange` — not a utility function

### Immutability by default

Value objects are always immutable. Entities should minimize mutable surface — only expose mutation methods that enforce invariants.

> **Implementation:** For Rust newtypes (`nutype` crate, manual newtypes), see **Rust skill** (`/rust` §6). For TypeScript branded types and discriminated unions for state machines, see **TypeScript skill** (`/typescript` §1-2).

---

## 5. Domain Events

Domain events capture something meaningful that happened in the domain. They are facts — past tense, immutable once created.

### Domain events vs integration events

| | Domain events | Integration events |
|---|---|---|
| **Scope** | Within a bounded context | Across bounded contexts |
| **Delivery** | Can be synchronous (in-process) | Always asynchronous (message bus) |
| **Timing** | During or immediately after the operation | After the transaction commits |
| **Schema** | Internal, can change freely | Published contract, versioned |
| **Example** | `AssetCreated` triggers a recalculation | `AssetCreated` notifies the reporting context |

### Event naming

- Past tense: `AssetCreated`, `OrderShipped`, `PaymentFailed`
- Include the aggregate type: `Asset` + `Created`, not just `Created`
- Be specific: `OrderItemQuantityChanged` over `OrderUpdated`

### Event content

Include the minimum essential information:

```
AssetCreated {
    asset_id: Uuid,
    kind: AssetKind,
    currency: Currency,
    occurred_at: DateTime<Utc>,
}
```

- Always include the aggregate ID and timestamp
- Include fields consumers need to decide whether to act — avoid forcing them to fetch the full aggregate
- Never include the entire aggregate state (coupling trap)
- Include a correlation/causation ID for tracing event chains

### Event ordering guarantees

- Events for the same aggregate should be ordered (use a sequence number or timestamp)
- Events across aggregates have no ordering guarantee — design consumers to be idempotent
- Exactly-once delivery is a myth in distributed systems — design for at-least-once with idempotent handlers

### When NOT to use events

- Simple CRUD with no side effects — events add complexity without benefit
- Synchronous operations within a single aggregate — just call the method
- When you need immediate consistency — events introduce latency

---

## 6. Data Modeling

### Normalization defaults

- **Default to Third Normal Form (3NF)** for transactional systems — eliminates update anomalies, keeps writes simple
- **Denormalize only with measured evidence** — and only in read models. If a query is slow, add a materialized view or read-optimized table, don't denormalize the write model
- Tables represent **aggregates and entities**, not DTOs or API response shapes

### Database constraints as last line of defense

Application-level validation is defense-in-depth, not a substitute for DB constraints:

| Constraint type | Use for | Example |
|----------------|---------|---------|
| `NOT NULL` | Required fields | All non-optional columns |
| `CHECK` | Value range, format rules | `CHECK (value > 0)`, `CHECK (currency ~ '^[A-Z]{3}$')` |
| `UNIQUE` | Business uniqueness rules | Email, slug, natural keys |
| `FOREIGN KEY` | Referential integrity | Aggregate references |
| `EXCLUDE` | Non-overlap constraints | Date ranges, spatial data |

**Every new monetary column must include a `CHECK` constraint** enforcing the valid range. Every new enum column should have a `CHECK` or foreign key enforcing valid values.

### Deterministic sort orders for pagination

Sorting by a non-unique column (e.g., `created_at`) alone produces non-deterministic results across pages. Always include a unique tiebreaker:

```sql
ORDER BY created_at DESC, id DESC
```

This ensures rows with identical timestamps appear in a consistent order across paginated queries.

> **Implementation:** For Diesel model patterns (Queryable, Insertable, migrations), see **Rust skill** (`/rust` §5, §8). For pagination contracts, see **API Design skill** (`/api-design` §6).

### Monetary precision

- Use `NUMERIC` / `DECIMAL` types — **never floating point** (`float`, `double`, `real`)
- Precision: `NUMERIC(19,4)` handles values up to 999 trillion with 4 decimal places
- Serialize as JSON string to preserve precision end-to-end (DB → API → frontend)
- Never round in application code — let the DB type handle precision, let the frontend handle display rounding

### Currency safety

- **Never aggregate monetary values across different currencies** without explicit conversion
- Store currency alongside every monetary value — `(amount, currency)` is the minimum unit
- Group-by-currency before any aggregation (`SUM`, `AVG`)
- Cross-currency totals require a conversion rate source and a reference timestamp

### Temporal data

- Use `TIMESTAMPTZ` (timestamp with time zone), never `TIMESTAMP` — timezone-naive timestamps cause bugs in every system that crosses time zones
- Store in UTC, convert for display
- Include `created_at` and `updated_at` on every table — they're free debugging tools
- For audit-sensitive data, `updated_at` is insufficient — use an audit log or event table

---

## 7. Schema Evolution

### Expand-Migrate-Contract pattern

Safe schema changes follow three phases:

1. **Expand** — add new columns/tables, make them nullable or with defaults. Old code ignores new columns. No breaking changes
2. **Migrate** — backfill data into new columns, update application code to use new schema. Both old and new paths work
3. **Contract** — remove old columns/tables once all code uses the new schema. This is the only breaking phase

### Safe changes (single release)

- Adding a nullable column
- Adding a column with a default value
- Adding a new table
- Adding an index (use `CREATE INDEX CONCURRENTLY` to avoid locking)
- Widening a column (e.g., `VARCHAR(50)` → `VARCHAR(100)`)

### Unsafe changes (require expand-migrate-contract)

- Removing or renaming a column
- Changing a column type
- Adding a `NOT NULL` constraint to an existing column
- Narrowing a column (e.g., `VARCHAR(100)` → `VARCHAR(50)`)
- Splitting or merging tables

### Migration rules

- **Every `up.sql` needs a `down.sql`** — rollback must be possible
- Write idempotent rollbacks: `DROP TABLE IF EXISTS`, `DROP INDEX IF EXISTS`
- **Never drop a column the current application depends on** in the same release — deploy the code change first, then drop in the next release
- Test migrations against a copy of production data when possible — empty-table migrations always succeed; real data surfaces edge cases

### Migration ordering

When a feature requires changes across layers:

1. Schema migration (DB)
2. Backend code (handlers, models)
3. Frontend code (components, routes)
4. Tests (update existing, add new)

Each layer should be independently deployable — the backend should handle both old and new schema during transition.

> **Implementation:** For Diesel migration workflow, see **Rust skill** (`/rust` §8). For project-specific migration steps, check the project's `CLAUDE.md`.

---

## 8. System Decomposition

### Start with a modular monolith

A modular monolith is a monolithic deployment with well-defined module boundaries internally. It's the correct default for most systems.

- **Module boundaries = bounded context boundaries** — each module encapsulates a complete domain model
- Modules communicate through explicit interfaces (public API, events), not by reaching into each other's internals
- Enforce boundaries with access control (Rust: crate visibility, TypeScript: barrel exports with lint rules)
- A well-structured monolith can be split into services later; a poorly-structured microservice architecture cannot be easily merged back

### When to extract a service

Extract to a separate service only with evidence:

| Evidence | Example |
|----------|---------|
| Independent scaling requirements | Search index needs 10x the compute of the core app |
| Different deployment cadence | Auth changes weekly, billing changes quarterly |
| Team autonomy needs | Team A can't deploy without coordinating with Team B |
| Technology mismatch | ML pipeline needs Python; core app is Rust |
| Isolation for reliability | Payment processing must survive core app outages |

**Absence of evidence is not evidence for monolith** — it just means don't split yet.

### Strangler Fig for incremental extraction

Never big-bang rewrite. Instead:

1. Put a routing layer in front of the monolith
2. Build the new service alongside the old code
3. Route traffic to the new service one endpoint at a time
4. Remove old code only after the new service is proven

### CQRS: selective, not default

Command Query Responsibility Segregation separates read and write models. Apply it when:

- Read and write patterns differ significantly (e.g., writes are transactional, reads are aggregated across multiple entities)
- Read performance requires denormalized views that would complicate the write model
- Different scaling requirements for reads vs writes

**CQRS adds complexity** — separate models, eventual consistency, synchronization. Don't apply it system-wide; apply it per-aggregate where the evidence supports it.

### Event sourcing: selective, not system-wide

Event sourcing stores state as a sequence of events rather than current state. Apply it when:

- Complete audit trail is a business requirement (financial transactions, compliance)
- Temporal queries ("what was the state at time T?") are needed
- Multiple read models must be derived from the same write history

**Event sourcing as default is an anti-pattern** — it adds complexity to every query, makes simple CRUD operations harder, and requires specialized infrastructure. Use it for the specific aggregates that benefit, not the whole system.

### Task-based APIs over CRUD

When possible, design APIs around business operations rather than raw data manipulation:

- `POST /orders/{id}:ship` instead of `PATCH /orders/{id} { "status": "shipped" }`
- `POST /accounts/{id}:transfer` instead of two `PATCH` calls to debit and credit

Task-based operations capture intent, enable richer validation, and produce meaningful domain events.

> **Implementation:** For mapping domain aggregates to API resources, see **API Design skill** (`/api-design` §2, §8). For security at service boundaries, see **Web Security skill** (`/web-security`).

---

## 9. Anti-patterns

| Anti-pattern | Why it fails | Fix |
|-------------|-------------|-----|
| **Anemic domain model** | Entities are data bags with getters/setters; logic lives in service layers. Invariants scatter across the codebase | Move behavior onto the entity/value object that owns the invariant |
| **God objects** | One entity accumulates all behavior. Changes in any part of the domain touch this entity | Split into focused aggregates with single responsibilities |
| **Database-driven design** | Tables drive the model; every DB column becomes a field on one mega-entity | Design the domain model first, then map to tables. Tables serve the model, not the other way around |
| **Premature decomposition** | Splitting into microservices before understanding the domain boundaries | Start with a modular monolith; extract services only with evidence (§8) |
| **Leaky abstractions** | Internal implementation details (DB schemas, wire formats) leak into the domain model | Use anti-corruption layers and separate DTOs from domain objects |
| **Smart UI / dumb backend** | Business logic lives in the frontend; backend is a thin CRUD pass-through | Business rules belong in the domain model (backend). Frontend validates for UX, backend enforces for correctness |
| **Cross-currency aggregation** | Summing monetary values across currencies produces meaningless numbers | Always group by currency before aggregation; require conversion rates for cross-currency totals |
| **Primitive obsession** | Using bare `String`, `i32`, `f64` for domain concepts with validation rules | Replace with value objects that enforce invariants at construction time (§4) |
| **Shared database** | Multiple services read/write the same tables, coupling their schemas | Each service owns its data; communicate through APIs or events |
| **Distributed monolith** | Microservices that must be deployed together due to tight coupling | If services can't be deployed independently, they should be a single service |

---

## 10. Pre-Design Checklist

Before implementing a new domain model or modifying an existing one:

- [ ] **Requirements gathered** — for the process that produces inputs to this checklist, see `/requirements`
- [ ] **Ubiquitous language** — have you confirmed naming with domain experts? Do code names match business vocabulary?
- [ ] **Aggregate boundaries** — what invariants must be immediately consistent? Is the aggregate as small as possible while still enforcing them?
- [ ] **Entity vs value object** — does this concept have identity? If not, model as a value object (immutable, equality by value)
- [ ] **Primitive obsession** — are you using bare primitives where a value object would enforce constraints?
- [ ] **DB constraints** — do new monetary/enum columns have `CHECK` constraints? Are referential integrity constraints in place?
- [ ] **Currency safety** — are monetary values always paired with currency? Is cross-currency aggregation prevented?
- [ ] **Deterministic pagination** — do paginated queries include a unique tiebreaker column?
- [ ] **Schema evolution** — can this migration be rolled back? Does it follow expand-migrate-contract?
- [ ] **Event design** — if this change triggers side effects, are they modeled as domain events?
- [ ] **Project rules** — have you checked the project's `CLAUDE.md` for domain-specific rules and constraints?

---

## 11. Quick Reference

### "Should I split this aggregate?"

| Question | If yes → |
|----------|----------|
| Does the aggregate enforce a single business invariant? | Keep together |
| Do different parts change at different rates? | Split along the change boundary |
| Do concurrent edits cause conflicts? | Smaller aggregates reduce contention |
| Does loading require 4+ table joins? | Performance signal — consider splitting |
| Can users edit different parts independently? | Likely separate aggregates |

### "Entity or value object?"

| Question | Entity | Value Object |
|----------|--------|-------------|
| Does it have a lifecycle (created, modified, deleted)? | Yes | No |
| Is identity meaningful ("this specific order")? | Yes | No |
| Can two instances with identical attributes coexist? | Yes (different IDs) | No (they're equal) |
| Should changes create a new instance? | No (mutate in place) | Yes (immutable) |

### "When to use domain events?"

| Scenario | Use events? |
|----------|-------------|
| Side effect in another aggregate | Yes — domain event |
| Side effect in another bounded context | Yes — integration event |
| Simple CRUD with no side effects | No — direct operation |
| Audit trail requirement | Yes — event captures the fact |
| Need to notify external systems | Yes — integration event |

### "CQRS for this aggregate?"

| Signal | CQRS likely helps |
|--------|-------------------|
| Read patterns differ significantly from write patterns | Yes |
| Read performance requires denormalized views | Yes |
| Reads outnumber writes 100:1 | Consider it |
| Simple CRUD with similar read/write patterns | No — overhead not justified |
