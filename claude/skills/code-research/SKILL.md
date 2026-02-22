---
name: code-research
description: |
  Source evaluation and research methodology skill for code and architecture decisions.
  Covers: source authority hierarchy, evaluating recency and context, conflict resolution,
  idiomatic code selection, research process, and reporting findings with attribution.
  Use when: researching unfamiliar patterns, evaluating competing approaches, choosing
  libraries, or reviewing architectural decisions against industry best practice.
  Sources: IETF, W3C, ECMA, POSIX, Google engineering blogs, Stripe, Cloudflare, recognized expert writings.
version: 1.0.0
date: 2026-02-22
user-invocable: true
---

# Code Research

Methodology for researching code patterns, architecture decisions, and implementation approaches. This skill governs *how to find answers* and *which sources to trust* — ensuring research always prioritizes industry best practice, elegant idiomatic implementations, and authoritative sources.

Based on standards bodies (IETF, W3C, ECMA, ISO, POSIX), Big Tech engineering publications (Google, Stripe, Cloudflare, Meta, AWS, Netflix, Discord), recognized expert writings (Fowler, Beck, Hickey, Kleppmann, Pike, Cantrill), and well-governed OSS reference implementations.

> **Scope boundary:** This skill covers research *methodology* — where to look, what to trust, how to report findings. For domain-specific guidance:
> - API contract decisions and HTTP semantics → **API Design skill** (`/api-design`)
> - Rust implementation patterns → **Rust skill** (`/rust`)
> - TypeScript/React patterns → **TypeScript skill** (`/typescript`)
> - Security posture and threat models → **Web Security skill** (`/web-security`)

---

## 1. Source Authority Hierarchy

Rank sources by authority. Higher tiers override lower tiers when they conflict.

### Tier 1 — Standards and specifications

The ground truth. Always check here first when a standard exists.

| Source | Domain |
|--------|--------|
| IETF RFCs | HTTP, TLS, DNS, URI, OAuth, JWT, email |
| W3C | HTML, CSS, DOM, Web APIs, accessibility |
| ECMA | JavaScript/TypeScript language semantics |
| ISO | Character encoding, date/time, security |
| POSIX / IEEE | Shell, filesystem, signals, process model |
| Language specs | Rust Reference, Go Spec, Python Language Reference |

### Tier 2 — Big Tech engineering (on topics where they lead)

Trust a company's engineering publications *only on topics where they are a recognized leader*. A company's blog post outside their domain of expertise is Tier 5.

| Company | Trust on | Do not generalize to |
|---------|----------|---------------------|
| Google | Distributed systems, API design (AIP), SRE, protocol buffers, observability | Frontend patterns, DX |
| Stripe | Payments, API developer experience, idempotency, webhook design | Infrastructure, systems |
| Cloudflare | Networking, edge computing, DNS, DDoS, HTTP semantics | Application architecture |
| Meta | React, UI component design, GraphQL, large-scale frontend | Backend API design |
| AWS | Cloud infrastructure, serverless, managed services | Application-level patterns |
| Netflix | Resilience engineering, chaos engineering, streaming at scale | API design, frontend |
| Discord | Real-time communication at scale, WebSocket patterns, Rust at scale | Enterprise patterns |

### Tier 3 — Recognized expert figures

Individuals with sustained, peer-recognized contributions. Their writings carry authority on their specific domains.

| Expert | Domain |
|--------|--------|
| Martin Fowler | Architecture, refactoring, enterprise patterns |
| Kent Beck | TDD, XP, software design |
| Rich Hickey | Simplicity, data-oriented design, immutability |
| Martin Kleppmann | Distributed data, consistency models, stream processing |
| Rob Pike | Systems programming, Go philosophy, simplicity |
| Bryan Cantrill | Systems observability, debugging, DTrace |
| Dan Abramov | React patterns, mental models for UI |

### Tier 4 — Well-maintained OSS projects

Reference implementations with strong governance. Code as documentation of best practice.

- **Criteria:** active maintenance, multiple contributors, clear governance, production use at scale
- **Examples:** tokio (async Rust), React (UI), PostgreSQL (relational DB), Linux kernel (OS), Axum (web framework), Go standard library

### Tier 5 — Community content

Useful for discovery and initial orientation. Never rely on as sole authority.

- Conference talks, blog posts, tutorials, Stack Overflow answers, Reddit discussions, dev.to articles, Medium posts
- **Always verify** claims from Tier 5 sources against higher-tier sources before adopting

---

## 2. Evaluating Sources

### Recency

- **Check version alignment:** Is the advice for the current major version of the tool/language? Post-React 18 patterns differ significantly from pre-hooks era. Rust 2021 edition changed trait resolution.
- **Check standard status:** Is the RFC ratified or still a draft? Draft standards may change. Note the distinction explicitly (e.g., "OAuth 2.1 draft" vs "RFC 9700").
- **Deprecation signals:** Archived repos, "this approach is no longer recommended" notices, superseded RFCs.

### Context match

- **Production scale vs hobby project:** A pattern that works for a personal blog may fail at 10k RPS. Match the source's deployment context to yours.
- **Team size:** Patterns designed for 500-engineer organizations may be over-engineered for a 3-person team.
- **Language/ecosystem:** A pattern idiomatic in Go (explicit error returns) should not be cargo-culted into Rust (Result types) or TypeScript (exceptions).

### Conflict resolution

When authoritative sources disagree:

1. **Trace to Tier 1:** If a standard exists, it wins
2. **Compare production evidence:** Which approach is proven at scale? By how many independent organizations?
3. **Check recency:** The more recent source may reflect lessons learned
4. **Note the conflict explicitly** in findings — don't silently pick a winner
5. **Present both positions** with their trade-offs and let the planner/user decide

---

## 3. Research Process

### Search strategy

Follow this order. Stop when you have sufficient authoritative coverage.

1. **Official docs and specs** — language reference, framework docs, relevant RFCs
2. **Engineering blogs from domain leaders** — Tier 2 companies on their specialty topics
3. **Expert writings** — Tier 3 figures on their domains
4. **Reference implementations** — Tier 4 OSS projects, read the actual code
5. **Community content** — Tier 5 for discovery, patterns you haven't considered

### Cross-reference requirement

Before adopting a pattern or recommendation:

- **Verify against at least two authoritative sources** (Tier 1-3)
- If only Tier 5 sources exist, flag this explicitly in findings
- If a single authoritative source exists with no corroboration, note this — it may still be correct, but confidence is lower

### Web search guidance

- Start with specific queries: `"RFC 9457" problem details` not `api error handling`
- Include version numbers: `react 19 server components` not `react server components`
- Prefer primary sources in results: `site:datatracker.ietf.org`, `site:stripe.com/docs`
- When evaluating blog posts, check the author's credentials and the publication date

---

## 4. Quality Standards

When researching implementations, evaluate every candidate pattern against these quality dimensions — in priority order:

### Standards compliance

The best solution conforms to established standards. A technically elegant approach that violates HTTP semantics, language specifications, or protocol requirements is not a good solution. Standards exist because they encode hard-won consensus about interoperability and correctness.

### Reliability and robustness

Prefer patterns that handle failure gracefully, degrade predictably, and have been battle-tested under adversarial conditions. Evaluate:

- **Error handling completeness** — does the pattern account for all failure modes, not just the happy path?
- **Edge case behavior** — how does it handle empty inputs, concurrent access, network partitions, clock skew?
- **Recovery characteristics** — does it fail fast, fail safe, or fail silently? Fail-fast with clear diagnostics is preferred.
- **Observability** — can you tell what went wrong from logs and metrics alone, without attaching a debugger?

### Elegance and simplicity

The best solution is the simplest one that fully solves the problem. Evaluate:

- **Idiomatic to the language/framework** — not translated from another ecosystem. Go error handling should not look like Java exceptions. Rust should use `?` and `Result`, not boolean flags.
- **Minimal moving parts** — fewer allocations, fewer indirections, fewer configuration knobs. Three lines of clear code beats a clever one-liner or a premature abstraction.
- **Conceptual clarity** — can a new team member understand the pattern without a 30-minute explanation? If not, the complexity must be justified by the problem's inherent complexity.
- **Composability** — does the pattern compose well with the rest of the system, or does it require special plumbing everywhere it's used?

### Industrial-grade quality

The pattern should be production-ready — not a prototype that "works on my machine":

- **Proven at scale** — used in production by organizations that have validated the approach under load, failure, and maintenance pressure
- **Maintainable** — easy to modify, extend, and debug six months from now by someone who didn't write it
- **Testable** — can be unit tested, integration tested, and property tested without elaborate mocking
- **Operationally sound** — supports deployment, rollback, monitoring, and incident response

### Language-specific idiom sources

Defer to the language-specific skill for detailed idiom guidance:

- Rust idioms → **Rust skill** (`/rust`)
- TypeScript/React idioms → **TypeScript skill** (`/typescript`)
- For languages without a dedicated skill, refer to the language's official style guide and Tier 4 reference implementations

---

## 5. Reporting Findings

### Attribution format

When writing `research.md` or reporting findings, attribute sources with:

- **Tier level** — so the reader knows the authority weight
- **Author or organization** — who said this
- **Date or version** — when, to assess recency
- **URL** — when available, for verification

Example: `(Tier 1, IETF RFC 9457, 2023)` or `(Tier 2, Stripe engineering blog, 2024)` or `(Tier 5, Stack Overflow answer, 2022 — verify against primary source)`

### Confidence signals

- **Flag when only lower-tier sources exist** — "No Tier 1-3 sources found; recommendation is based on community consensus only"
- **Flag conflicts explicitly** — "Google AIP recommends X; Stripe practice differs with Y. Trade-off: ..."
- **Flag draft standards** — "Based on OAuth 2.1 draft (not yet ratified); may change"
- **Flag recency concerns** — "Source predates React 19; patterns may be outdated"

### Structure

Follow the `research.md` format defined by the **researcher agent** (`claude/agents/researcher.md`). Add a `## Sources` section at the end with tiered attribution for all referenced materials.

---

## 6. Anti-patterns

| Anti-pattern | Why it fails | Fix |
|-------------|-------------|-----|
| Treating Stack Overflow as authoritative | Answers are community-voted, not peer-reviewed; many are outdated | Verify against Tier 1-3 sources |
| Following outdated blog posts | Pre-major-version advice can be actively harmful | Check version alignment and deprecation signals |
| Cargo-culting patterns without context | A pattern from a 10M-user system may be over-engineered for your use case | Match the source's deployment context to yours |
| Conflating popularity with correctness | Most-upvoted answer may be most accessible, not most correct | Trace to authoritative sources |
| Citing a company outside their domain | Google's frontend advice is not as authoritative as their distributed systems guidance | Check the Tier 2 domain column |
| Silently picking a winner when sources conflict | Hides important trade-off information from the decision-maker | Present both positions with trade-offs |
| Relying on a single source | Even authoritative sources can be wrong or context-specific | Cross-reference at least two sources |
| Translating idioms across ecosystems | Java patterns in Go, Python patterns in Rust — produces non-idiomatic code | Research the target language's conventions first |
