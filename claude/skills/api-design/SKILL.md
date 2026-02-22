---
name: api-design
description: |
  Language-agnostic REST API design skill for production APIs.
  Covers: resource design, HTTP semantics, status codes, error format (RFC 9457),
  pagination, filtering, versioning, idempotency, authentication, authorization,
  security headers, caching, developer experience, resilience, and OpenAPI standards.
  Use when: designing new endpoints, reviewing API contracts, or making HTTP semantics decisions.
version: 1.0.0
date: 2026-02-22
user-invocable: true
---

# REST API Design

Language-agnostic REST API design guidance. Covers the *contract* — what a well-designed API looks like. Implementation skills (Rust, TypeScript) handle the *how*.

Based on Google API Design Guide (AIP system), Microsoft Azure REST API Guidelines, Zalando RESTful API Guidelines, Stripe API design patterns, RFC 9457 (Problem Details), and OWASP API Security Top 10 (2023).

---

## 1. Design Philosophy

APIs are user interfaces for developers. Design for the developer who has never read your docs.

- **Principle of least surprise** — every endpoint should behave the way a developer expects before reading the docs
- **Consistency over cleverness** — identical patterns across all endpoints; same naming, same error shape, same pagination, same auth
- **Pit of success** — make the right thing easy, the wrong thing hard. Sensible defaults, forgiving input, strict output
- **API as product** (Zalando) — treat every API as a product with users, lifecycle, and quality standards. Peer review API designs before implementation
- **Progressive complexity** (Stripe) — simple integrations work in a few lines. Advanced features layer on without rewriting the basic integration
- **Resource-oriented design** (Google) — model entities as resources with standard operations. Standard methods (CRUD) are predictable; custom methods are the escape hatch
- **Postel's Law** (Zalando) — be liberal in what you accept, be conservative in what you send. Trim whitespace, normalize case, accept optional fields gracefully. Return strict, well-defined shapes

---

## 2. Resource Design & URL Structure

- Plural nouns for collections: `/api/assets`, not `/api/getAssets` or `/api/asset`
- Hierarchical nesting for ownership: `/api/users/{id}/assets` — max 2 levels, flatten beyond that
- Collection (`/api/assets`) vs singleton (`/api/assets/{id}`) semantics
- Custom methods when CRUD doesn't fit: use `:action` suffix (Google AIP-136) — `/api/assets/{id}:archive`
- Query parameters for filtering, sorting, field selection — never in the URL path
- Resource IDs: UUIDs over sequential integers (OWASP BOLA mitigation — prevents enumeration)
- Standard fields on every resource (Google AIP-148): `id`, `created_at`, `updated_at`. Consider `metadata` (Stripe) — arbitrary key-value pairs for developer use

---

## 3. HTTP Methods & Semantics

| Method | Safe | Idempotent | Request Body | Typical Use |
|--------|------|------------|--------------|-------------|
| GET | Yes | Yes | No | Retrieve resource(s) |
| POST | No | No | Yes | Create resource, trigger action |
| PUT | No | Yes | Yes | Full replace |
| PATCH | No | Depends | Yes | Partial update (JSON Merge Patch RFC 7396) |
| DELETE | No | Yes | No | Remove resource |

**Method choice rules:**
- GET must never have side effects — no creating, no deleting, no state changes
- PUT replaces the entire resource — omitted fields reset to defaults
- PATCH updates only provided fields — use JSON Merge Patch (RFC 7396): send only changed fields, omitted fields stay unchanged. Idempotency depends on patch semantics: patches representing desired final state are idempotent; operational patches (e.g., "increment balance by 10") are not
- DELETE is idempotent — deleting an already-deleted resource returns 204, not 404
- Non-idempotent operations (commonly POST, sometimes PATCH) are not safe to retry — use an `Idempotency-Key` header to make retries safe

---

## 4. Status Codes

**Every expected failure mode gets its own status code. 500 is never part of your API contract — it means a bug.**

| Code | Name | When to Use |
|------|------|-------------|
| 200 | OK | GET, PUT, PATCH success with response body |
| 201 | Created | POST success — **MUST include `Location` header** pointing to the created resource |
| 204 | No Content | DELETE success, PUT/PATCH when no response body needed |
| 304 | Not Modified | Conditional GET when `If-None-Match` matches the `ETag` |
| 400 | Bad Request | Malformed syntax, missing required fields, unparseable JSON |
| 401 | Unauthorized | No credentials or expired token — **MUST include `WWW-Authenticate` header** |
| 403 | Forbidden | Valid credentials, insufficient permissions. Use 404 instead if resource existence is sensitive (Google, Microsoft) |
| 404 | Not Found | Resource doesn't exist, or 403 disguised to prevent resource enumeration |
| 409 | Conflict | Duplicate resource, state conflict, optimistic locking failure not expressed via HTTP conditional headers |
| 412 | Precondition Failed | `If-Match` / `If-None-Match` precondition not met — use this (not 409) when `If-*` headers are present |
| 422 | Unprocessable Entity | Valid syntax but semantic/business rule violation (e.g., insufficient balance, invalid date range) |
| 429 | Too Many Requests | Rate limited — **MUST include `Retry-After` header** |
| 503 | Service Unavailable | Dependency down, maintenance — **SHOULD include `Retry-After` header** |

**Permission checks before existence checks** (Google, Microsoft): Return 401/403 *before* checking if the resource exists. Never leak resource existence to unauthorized callers.

**Anti-patterns:**
- Documenting 500 in OpenAPI specs — expand your error model instead
- Using 200 for everything with `{ "success": false }` in the body
- Using 400 as a catch-all for all client errors — distinguish 401, 403, 404, 409, 422, 429
- Returning 404 for a collection endpoint with no results — return 200 with empty `items: []`

---

## 5. Error Responses — RFC 9457 Problem Details

Adopt RFC 9457 (formerly RFC 7807) as the universal error format. Content-Type: `application/problem+json`.

**Standard fields:**

| Field | Type | Purpose |
|-------|------|---------|
| `type` | URI | Machine-readable problem identifier. Primary key for programmatic handling. Can be opaque (non-dereferenceable) |
| `title` | string | Short, stable, human-readable summary. SHOULD NOT change between occurrences |
| `status` | integer | HTTP status code (advisory — actual response status takes precedence) |
| `detail` | string | Per-occurrence explanation. Tell the developer what went wrong AND how to fix it |
| `instance` | URI | Identifies this specific occurrence (e.g., request ID or log entry URI) |

**Extension fields for richer errors:**

Validation errors — return field-level detail so developers fix all issues in one round-trip (not one at a time):
```json
{
  "type": "urn:error:validation",
  "title": "Validation Error",
  "status": 422,
  "detail": "2 fields failed validation",
  "errors": [
    { "field": "currency", "message": "Must be a 3-letter uppercase ISO 4217 code", "rejected_value": "us" },
    { "field": "value", "message": "Must be positive", "rejected_value": "-10" }
  ]
}
```

Inspired by Stripe: include `doc_url` linking to error documentation, and consider `request_id` for support correlation.

**Rules:**
- Never leak internals — SQL syntax, table names, constraint names, stack traces are never client-facing
- Validation and not-found errors return the actual message (they're user-facing and actionable)
- Infrastructure errors (DB, pool, timeout) return opaque message ("An internal error occurred") and log details server-side
- Same error shape from every endpoint — clients parse errors once, not per-endpoint
- Microsoft: duplicate the top-level error code in an `x-error-code` response header — enables error routing without parsing the body

---

## 6. Pagination

### Offset pagination

- Parameters: `?limit=25&offset=0`
- Pros: simple, supports random page access, "page 3 of 10" UI
- Cons: inconsistent under concurrent writes (items shift), performance degrades with depth (DB scans skipped rows), clients can request absurd offsets
- Use for: admin UIs with page numbers, small datasets

### Cursor pagination (keyset)

- Parameters: `?limit=25&after=<opaque_cursor>` (Stripe: `starting_after`, `ending_before`)
- Pros: stable under mutations, O(1) for any depth, opaque cursor prevents abuse
- Cons: no random page access, no "page 3 of 10"
- Use for: infinite scroll, feeds, large datasets, public APIs

### Response shapes

Pick one strategy per endpoint — never mix offset and cursor fields in the same response (Twilio's hybrid is a cautionary tale).

**Cursor-based** (preferred — Stripe, Google, Slack pattern):

```json
{
  "data": [...],
  "has_more": true,
  "next_cursor": "eyJpZCI6MTIzfQ=="
}
```

- `has_more`: boolean — unambiguous signal, avoids client inferring end-of-list from `len(data) < limit`
- `next_cursor`: opaque string, `null` when `has_more` is `false`. Never expose internal IDs or timestamps as the cursor format
- Request params: `cursor` (opaque), `limit` (integer with default and max)

**Offset-based** (only when random page access is a hard requirement):

```json
{
  "data": [...],
  "page": 1,
  "page_size": 25,
  "total": 1042
}
```

- Request params: `page` (integer, 1-indexed), `page_size` (integer)

### Rules

- Deterministic sort order — always include a unique tiebreaker column (e.g., `created_at DESC, id DESC`)
- Server-enforced limits — clamp to `[1, 100]`, don't reject. If client requests 500, silently coerce to 100 (Google)
- Omit `total` from cursor responses — expensive to compute at scale, often stale. Offer as a separate endpoint or opt-in field if needed (Zalando)
- Never return pagination metadata without items (no empty `{ total: 0 }` without `data: []`)
- Cursors must be opaque strings — clients must not parse or construct them

---

## 7. Filtering, Sorting & Field Selection

**Filtering:** `?status=active&type=STOCK` for simple equality. For complex queries, consider a structured syntax (Google AIP-160 or OData-style operators: `?filter=value gt 1000`).

**Sorting:** `?sort=created_at:desc,name:asc` — explicit, composable, same syntax across all list endpoints.

**Field selection:** `?fields=id,name,value` — reduces payload. More sophisticated: `?expand=account` to inline related resources (Stripe pattern — default returns IDs, expand returns full objects).

**Consistency:** same parameter names and semantics across all list endpoints. Document the default sort order for each collection.

---

## 8. Versioning & API Evolution

**Design for evolution first** — avoid versioning as long as possible:
- Additive changes are not breaking: new optional fields, new endpoints, new enum values (with "must-ignore" client pattern)
- Breaking changes: removing/renaming fields, adding required fields, changing types, tightening validation, changing error format

**When versioning is needed:**
- URL path versioning (`/v1/assets`) — explicit, cacheable, easy to route (Google: major versions only, never expose minor/patch)
- Date-based header versioning (`API-Version: 2024-06-20`) — Stripe pattern, accounts pinned to a version, fine-grained evolution
- Choose one approach and use it consistently

**Deprecation lifecycle** (RFC 8594 + RFC 9745):
1. Mark `deprecated: true` in OpenAPI spec
2. Add `Deprecation: <date>` header (when the replacement became available)
3. Add `Sunset: <date>` header (when the old endpoint stops responding)
4. Communicate via changelog, docs, email
5. Monitor usage — don't sunset until clients have migrated
6. Minimum 90-180 day grace period (Zalando recommends partner consent)

**Field mutability** (Microsoft): classify every field as create-only (set at creation, immutable after), update-capable (mutable via PUT/PATCH), or read-only (server-generated, never client-settable). Document this in the OpenAPI schema.

---

## 9. Idempotency

Network failures during non-idempotent operations (POST, sometimes PATCH) create "did it work?" ambiguity. Use idempotency keys to make retries safe.

**`Idempotency-Key` header** (Stripe pattern):
- Client generates a UUID, sends via `Idempotency-Key` header
- Server processes the request, stores the key + response (24h TTL)
- Subsequent requests with the same key return the cached response — same status, same body
- Reusing a key with different parameters returns 422 (prevents accidental misuse)
- Keys are scoped per-client, not global
- GET/PUT/DELETE are inherently idempotent — keys have no effect

**Microsoft alternative:** `Repeatability-Request-ID` + `Repeatability-First-Sent` headers — achieves the same goal with explicit timestamp for replay detection.

---

## 10. Security — Authentication, Authorization & Audit

### Authentication (AuthN) — Who are you?

- Bearer tokens in `Authorization: Bearer <token>` header — **never in URL query parameters** (logged in access logs, cached by proxies, visible in browser history)
- JWT: stateless verification (no DB lookup), but hard to revoke (need blocklist). Best for microservices. 15-minute max expiry, RS256 or ES256 (not HS256), single-use refresh tokens with rotation
- Opaque tokens: require server lookup, but support instant revocation. Better for monoliths needing immediate revocation
- OAuth 2.0 + PKCE for SPAs: Authorization Code Flow with PKCE (Implicit Flow deprecated in OAuth 2.1). Client proves it started the flow using code verifier/challenge pair
- 401 when missing/expired — **MUST include `WWW-Authenticate` header** specifying the auth scheme
- Store tokens in `httpOnly`/`Secure`/`SameSite=Strict` cookies (never localStorage)

### API Keys vs Bearer Tokens (Stripe pattern)

- API keys identify the **application** (rate limiting, billing, audit). Prefixed for leak detection (`pk_test_`, `sk_live_`)
- Bearer tokens identify the **user** (authorization decisions)
- Support both: API key for app identity, bearer token for user context
- Restricted keys with per-resource scopes enforce least-privilege (e.g., `assets:read` only)

### Authorization (AuthZ) — What can you do?

- Check permissions in middleware, not scattered through handlers. Default deny — require explicit grants
- Permission checks before existence checks (Google, Microsoft) — never leak resource existence to unauthorized callers
- RBAC (role-based) or ABAC (attribute-based) access control. Scoped tokens: `assets:read`, `assets:write`
- 403 when authenticated but insufficient permissions. Use 404 instead if resource existence itself is sensitive (prevents enumeration)
- OWASP BOLA (#1 risk): validate requester owns/has access to the specific resource on **every** endpoint that uses a user-supplied ID
- OWASP BOPLA (#3): use separate DTOs for create vs update vs response. Never expose all DB columns blindly. Reject unknown fields (Microsoft: return 400 for unrecognized JSON fields)
- OWASP Broken Function Level Auth (#5): segregate admin endpoints with separate middleware groups

### Audit — What did you do?

- Log every state-changing operation: `{ actor, action, resource, resource_id, timestamp, request_id, source_ip, result }`
- Include `X-Request-ID` in audit entries for end-to-end correlation
- Never log credentials, tokens, or PII in audit logs
- Immutable, append-only audit trail — never delete or modify entries
- Audit authorization *decisions* (both grants and denials) — not just successful actions

### Machine-to-machine auth

- OAuth 2.0 Client Credentials Flow, short-lived tokens (5 min), no refresh tokens

---

## 11. Security — Transport & Headers

- **HTTPS only** — redirect HTTP to HTTPS, set HSTS (`Strict-Transport-Security: max-age=63072000; includeSubDomains`)
- **Security headers:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`
- **CORS:** explicit origin allow-list, never wildcard in production. Include `max_age` for preflight caching. Credential-bearing requests require explicit `Access-Control-Allow-Credentials`
- **Rate limiting:** per-client and per-endpoint. Return standardized headers:
  - `RateLimit` (IETF draft) or `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
  - 429 response with `Retry-After` header when exceeded
  - Stripe: also return `Should-Retry: true/false` boolean for explicit retry guidance
- **Request size limits** — reject oversized payloads before parsing (defense against resource exhaustion — OWASP #4)
- **Request timeouts** — enforce server-side, return 504 if exceeded
- **Never return secrets via GET** (Microsoft) — secrets in POST responses only if absolutely necessary
- **OWASP SSRF (#7):** if the API fetches external URLs based on user input, validate against allowlists and block private IP ranges

---

## 12. Caching & Conditional Requests

### ETags for bandwidth savings

- Return `ETag` header on GET responses (content hash or version counter)
- Client sends `If-None-Match: <etag>` on subsequent GET — server returns 304 Not Modified if unchanged

### ETags for optimistic concurrency

- Client sends `If-Match: <etag>` on PUT/PATCH/DELETE — server returns 412 Precondition Failed if the resource changed since the client last read it
- Prevents lost updates in multi-user scenarios
- `updated_at` timestamp can serve as the ETag basis for simple cases

### Cache-Control directives

- `no-store` for sensitive/authenticated data
- `max-age=N` for static or rarely-changing resources
- `must-revalidate` for dynamic data (forces ETag check)
- `Vary: Authorization` when caching authenticated responses

---

## 13. Standard Headers

### Request headers the API should support

| Header | Purpose |
|--------|---------|
| `Authorization` | Bearer token or API key |
| `Content-Type` | Request body format (`application/json`) |
| `Accept` | Preferred response format |
| `Idempotency-Key` | Safe POST retries (client-generated UUID) |
| `If-Match` / `If-None-Match` | Conditional requests (ETags) |
| `X-Request-ID` | Client-generated correlation ID |

### Response headers the API should return

| Header | Purpose | When |
|--------|---------|------|
| `Content-Type` | Response format | Always |
| `Location` | URI of created resource | 201 Created |
| `ETag` | Resource version | GET responses |
| `X-Request-ID` | Echo back or server-generated | Always |
| `Retry-After` | Seconds to wait | 429, 503 |
| `RateLimit` | Quota remaining + reset | Always (if rate limiting enabled) |
| `Deprecation` | When replacement became available | Deprecated endpoints |
| `Sunset` | When this endpoint stops responding | Deprecated endpoints |
| `WWW-Authenticate` | Auth scheme required | 401 |

---

## 14. Developer Experience

DX is what separates a good API from a great one. **Time to first successful API call** is the single most important metric (Stripe).

### Consistency

- snake_case for all JSON fields — matches Stripe, GitHub, Zalando, Cloudflare conventions. Rust emits snake_case natively; other languages configure their serializers accordingly
- kebab-case for URL paths, plural nouns for collections
- Same envelope for all list endpoints (`{ items, total, limit, offset }`)
- Same error shape from every endpoint (RFC 9457)
- Same auth pattern on every endpoint
- Same pagination parameters on every list endpoint

### Error messages that help

- Tell the developer what went wrong AND how to fix it
- Include the field name, the rejected value, and the constraint: `"'currency' must be a 3-letter uppercase ISO 4217 code, got 'us'"`
- Stripe: include `doc_url` linking to error documentation. Include `request_id` for support correlation
- Return ALL validation errors at once — not one at a time (developer shouldn't need 5 round-trips to fix 5 fields)

### Forgiving input, strict output

- Trim whitespace on strings
- Normalize case where unambiguous (e.g., currency `usd` -> `USD`)
- Accept `null` and missing interchangeably for optional fields
- Silently coerce oversized pagination limits (Google) instead of rejecting
- But always return strict, well-defined, predictable output

### Documentation

- Interactive documentation (Swagger UI / Redoc) — always up-to-date, try-it-out enabled
- Realistic examples in OpenAPI spec — not `"string"` and `0`, but `"Apple Stock"` and `"15000.00"`
- Schema descriptions for every field — not just the type, the business meaning
- Changelog with every release — breaking changes highlighted, migration guide included
- SDKs generated from OpenAPI — type-safe, versioned, always current

### Sensible defaults

- Pagination defaults to reasonable limit (25 or 50)
- Optional fields have documented default values
- Sorting defaults to most-recently-created-first for time-series data

---

## 15. Resilience & Graceful Degradation

### Health endpoints (three tiers)

| Endpoint | Purpose | Checks | Failure Action |
|----------|---------|--------|----------------|
| `GET /health` | Liveness | None (always 200) | Orchestrator restarts process |
| `GET /ready` | Readiness | DB pool, critical deps | Orchestrator stops routing traffic |
| `GET /metrics` | Prometheus scrape | All registered metrics | Alerting |

Liveness must **never** check dependencies. If Postgres is down, the process is still alive — the orchestrator should stop routing (readiness), not restart (liveness).

### Client retry guidance

- Only retry on 429 (rate limited) and 503 (unavailable) — honor `Retry-After` when present; if absent, fall back to your exponential backoff policy
- Never retry on 4xx (client errors) — the request is wrong, retrying won't help
- Exponential backoff with jitter — prevents thundering herd
- Stripe: `Should-Retry` header makes retry decisions explicit

### Server resilience

- Circuit breaker for external dependencies — fail fast when downstream is unhealthy, return 503
- Graceful shutdown — drain in-flight requests before terminating (prevents 502s during deploys)
- Request timeouts — set and enforce, return 504 if exceeded
- Fallback responses — return degraded but useful data when a non-critical dependency fails
- Concurrency limiting / bulkhead — prevent one slow subsystem from consuming all capacity

---

## 16. API Documentation & OpenAPI Standards

- OpenAPI 3.1 as the spec format — **generated from code annotations** (utoipa, SpringDoc, etc.), never hand-written
- Every endpoint must document: summary, description, parameters, request body, success response, error responses with typed bodies
- **Do not document 500** — if you find yourself wanting to, expand your error model with a specific status code instead
- Schema descriptions for every field: not just `type: string`, but the business meaning, format, constraints, default value
- Realistic examples — `"Apple Stock"`, `"15000.00"`, `"USD"` — not `"string"`, `0`, `"string"`
- Authentication requirements per-endpoint (which scopes are needed)
- Rate limit expectations documented in description text
- Changelog maintained alongside the spec — ideally auto-generated from git history

### Anti-patterns

- Hand-editing generated OpenAPI specs
- Documenting 500 Internal Server Error as an expected response
- Examples using placeholder values (`"string"`, `0`)
- Missing error response schemas (just status codes without body shapes)
