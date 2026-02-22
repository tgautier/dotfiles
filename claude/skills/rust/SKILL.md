---
name: rust
description: |
  Industrial-grade Rust development skill for Axum + Diesel + utoipa APIs.
  Covers: handler design, error handling, validation, Diesel models & migrations,
  Tower middleware, observability, testing, security, performance, API design, resilience,
  transactions, and dependency management.
  Use when: writing handlers, models, migrations, tests, or reviewing Rust code quality.
version: 3.0.0
date: 2026-02-21
user-invocable: true
---

# Rust Industrial-Grade Development

Implements the API Design skill conventions using Axum + Diesel + utoipa. See that skill for HTTP semantics, error format, status codes, pagination contracts, security patterns, and DX principles.

Comprehensive Rust guidance for building production-quality Axum + Diesel APIs. Based on industry best practices from Cloudflare, Discord, AWS, and the broader Rust ecosystem.

---

## 1. Crate-Level Safety

Set these at the top of your crate root (`main.rs` or `lib.rs`):

```rust
#![forbid(unsafe_code)]
#![deny(clippy::all)]
#![warn(clippy::pedantic, clippy::nursery)]
```

- `forbid(unsafe_code)` — hard guarantee: no unsafe in your crate. Dependencies may use unsafe, but your code does not.
- `clippy::nursery` catches real bugs: `significant_drop_tightening` (long-held locks), `redundant_pub_crate` (visibility hygiene), `or_fun_call` (unnecessary allocations in `unwrap_or`).

---

## 2. Handler Design

Every handler is a public async function returning `Result<T, ApiError>`.

```rust
#[utoipa::path(
    get,
    path = "/api/resources",
    params(ListParams),
    responses(
        (status = 200, description = "Success", body = PaginatedResponse<Resource>),
        (status = 400, description = "Validation error", body = ProblemDetail),
    ),
    tag = "resources"
)]
#[tracing::instrument(skip(state), fields(otel.kind = "server"))]
pub async fn list_resources(
    State(state): State<AppState>,
    Query(params): Query<ListParams>,
) -> Result<Json<PaginatedResponse<Resource>>, ApiError> {
    // 1. Validate input (or use extractor-based validation)
    // 2. Acquire database connection
    // 3. Execute query
    // 4. Transform and return
}
```

**Mandatory annotations** — both must be present on every public handler:
- `#[utoipa::path]` with method, path, params, responses (including error shapes), and tag
- `#[tracing::instrument]` with `skip(state)` and `fields(otel.kind = "server")`

**For mutation handlers**, skip the payload and add domain-relevant fields:
```rust
#[tracing::instrument(skip(state, payload), fields(otel.kind = "server", resource.name = %payload.name))]
```

### Custom extractors

Build `FromRequestParts` extractors for cross-cutting concerns:

```rust
pub struct AuthUser(pub UserId);

#[async_trait]
impl<S> FromRequestParts<S> for AuthUser
where S: Send + Sync {
    type Rejection = ApiError;
    async fn from_request_parts(parts: &mut Parts, _state: &S) -> Result<Self, Self::Rejection> {
        // Extract and validate JWT/session from headers
    }
}
```

### Rejection handling

Override Axum's default rejection responses (which return plain text) with a custom handler to return consistent JSON error bodies matching your RFC 9457 format.

---

## 3. Error Handling

### Error enum with thiserror

Use `thiserror` for all error enums. Reserve `anyhow` for CLI tools, test helpers, and one-off scripts — never for handler return types where callers need to match on failure modes.

```rust
#[derive(Debug, thiserror::Error)]
pub enum ApiError {
    #[error("Validation error: {0}")]
    Validation(String),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Conflict: {0}")]
    Conflict(String),

    #[error(transparent)]
    Database(#[from] diesel::result::Error),

    #[error(transparent)]
    Pool(#[from] deadpool::managed::PoolError<diesel_async::pooled_connection::PoolError>),
}
```

### `#[from]` vs `map_err`

- Use `#[from]` when a single error type maps unambiguously to one variant (e.g., `diesel::result::Error` always means `Database`).
- Use `map_err` when the same underlying error type could mean different things in different call sites, or when you need to add contextual information.

### Error chain preservation

Always preserve the error chain via `#[source]` or `#[from]`. Log errors **only when handled** (in `IntoResponse`), never during propagation — this prevents duplicate log entries.

### RFC 9457 Problem Details

Implement RFC 9457 Problem Details (see API Design skill section 5 for the contract). Rust implementation:

```rust
impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, title, detail) = match &self {
            ApiError::Validation(msg) => (StatusCode::BAD_REQUEST, "Validation Error", msg.as_str()),
            ApiError::NotFound(msg) => (StatusCode::NOT_FOUND, "Not Found", msg.as_str()),
            ApiError::Conflict(msg) => (StatusCode::CONFLICT, "Conflict", msg.as_str()),
            ApiError::Database(e) => {
                tracing::error!(error = %e, "Database error");
                (StatusCode::INTERNAL_SERVER_ERROR, "Internal Error", "An internal error occurred")
            }
            ApiError::Pool(e) => {
                tracing::error!(error = %e, "Pool error");
                (StatusCode::INTERNAL_SERVER_ERROR, "Internal Error", "An internal error occurred")
            }
        };
        let body = serde_json::json!({
            "type": format!("urn:error:{}", status.as_u16()),
            "title": title,
            "status": status.as_u16(),
            "detail": detail,
        });
        (status, Json(body)).into_response()
    }
}
```

**Rules:**
- Never leak database error details to clients — SQL syntax, table names, constraint names are internal
- Validation and not-found errors return the actual message (they're user-facing)
- Database and pool errors log internally with `tracing::error!` and return generic text
- Never `.unwrap()` or `.expect()` in handlers — always propagate with `?`

---

## 4. Input Validation

### Extractor-based validation (preferred)

Use `garde` for struct-level validation with `axum-valid` for automatic extractor integration:

```rust
use garde::Validate;

#[derive(Debug, Deserialize, Validate, ToSchema)]
pub struct CreateResource {
    #[garde(length(min = 1, max = 255))]
    pub name: String,

    #[garde(email)]
    pub email: String,

    #[garde(range(min = 0))]
    pub quantity: i32,
}
```

**With `axum-valid`**, validation runs before your handler:
```rust
use axum_valid::Valid;

pub async fn create_resource(
    State(state): State<AppState>,
    Valid(Json(payload)): Valid<Json<CreateResource>>,
) -> Result<(StatusCode, Json<Resource>), ApiError> {
    // payload is already validated — handler focuses on business logic
}
```

### Manual validation (when extractors aren't enough)

For complex cross-field validation that garde can't express:

```rust
if payload.start_date >= payload.end_date {
    return Err(ApiError::Validation("Start date must precede end date".into()));
}
```

**Validation order:**
1. Trim strings
2. Required fields (non-empty after trim)
3. Length constraints
4. Format constraints (regex, character classes)
5. Numeric ranges and business rules
6. Cross-field rules

### Server-side pagination limits

Always enforce bounds — never trust client values:

```rust
let limit = params.limit.clamp(1, 100);
let offset = params.offset.max(0);
```

**Do not trust the client.** Validate at the API boundary even if the frontend also validates.

---

## 5. Diesel Models & Type Safety

Follow **model-first development**: Rust structs are the source of truth for the API contract.

### Three separate models per entity

**Read model (Queryable)** — what comes out of the database:
```rust
#[derive(Debug, Queryable, Selectable, Serialize, ToSchema)]
#[diesel(table_name = resources)]
#[diesel(check_for_backend(diesel::pg::Pg))]
pub struct Resource {
    pub id: uuid::Uuid,
    pub name: String,
    pub created_at: DateTime<Utc>,
}
```

**Write model (Insertable)** — what goes into the database:
```rust
#[derive(Insertable)]
#[diesel(table_name = resources)]
pub struct NewResource {
    pub id: uuid::Uuid,
    pub name: String,
    pub resource_type: ResourceType,
}
```

**API input model (Deserialize + ToSchema)** — what the client sends:
```rust
#[derive(Debug, Deserialize, Validate, ToSchema)]
pub struct CreateResource {
    pub name: String,
    pub resource_type: ResourceType,
}
```

**Keep read, write, and input models separate.** Never use `Queryable` on an input struct.

### Custom enum types with Diesel

```rust
#[derive(Debug, Clone, Serialize, Deserialize, diesel_derive_enum::DbEnum, ToSchema, PartialEq)]
#[ExistingTypePath = "crate::schema::sql_types::ResourceType"]
#[DbValueStyle = "SCREAMING_SNAKE_CASE"]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ResourceType {
    TypeA,
    TypeB,
}
```

**CI gotcha:** `diesel-derive-enum` with `ExistingTypePath` does NOT generate `QueryId`. Use `Insertable` structs for inserts — tuple-based `.values()` requires `QueryId` and fails on Linux CI.

### Precision-sensitive numeric types

- Use `BigDecimal` for values where floating-point error is unacceptable (financial, scientific, rates)
- Serialize as JSON string to preserve precision:
```rust
#[serde(serialize_with = "serialize_bigdecimal_as_string")]
#[schema(value_type = String)]
pub amount: BigDecimal,
```

---

## 6. Domain Types & Newtype Pattern

Use the Rust type system to **make invalid states unrepresentable**.

### Newtypes with `nutype`

The `nutype` crate generates smart constructors via proc macros — no boilerplate:

```rust
use nutype::nutype;

#[nutype(
    sanitize(trim),
    validate(not_empty, len_char_max = 255),
    derive(Debug, Clone, Serialize, Deserialize, AsRef),
)]
pub struct DisplayName(String);

#[nutype(
    validate(regex = r"^[a-z0-9_]+$"),
    derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash),
)]
pub struct Slug(String);
```

`nutype` makes `::try_new()` the only constructor. The inner field is private. Invalid values cannot exist.

### Manual newtypes (when nutype is overkill)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PositiveQuantity(i32);

impl PositiveQuantity {
    pub fn try_new(value: i32) -> Result<Self, ApiError> {
        if value <= 0 {
            return Err(ApiError::Validation("Quantity must be positive".into()));
        }
        Ok(Self(value))
    }

    pub fn get(&self) -> i32 {
        self.0
    }
}
```

**Rule:** Keep the inner field private. Expose access via `as_str()`, `get()`, or `AsRef` — never `pub`.

### From/TryFrom for layer conversions

```rust
impl TryFrom<CreateResource> for ValidatedResource {
    type Error = ApiError;

    fn try_from(input: CreateResource) -> Result<Self, Self::Error> {
        Ok(Self {
            name: DisplayName::try_new(input.name)?,
            slug: Slug::try_new(input.slug)?,
            resource_type: input.resource_type,
        })
    }
}

impl From<ValidatedResource> for NewResource {
    fn from(v: ValidatedResource) -> Self {
        Self {
            id: Uuid::new_v4(),
            name: v.name.as_ref().to_string(),
            slug: v.slug.as_ref().to_string(),
            resource_type: v.resource_type,
            created_at: Utc::now(),
        }
    }
}
```

### Typed IDs

Prevent mixing entity IDs:

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct ResourceId(Uuid);

impl ResourceId {
    pub fn new() -> Self { Self(Uuid::new_v4()) }
    pub fn as_uuid(&self) -> &Uuid { &self.0 }
}
```

The compiler catches `fn link(from: ResourceId, to: UserId)` called with swapped args. No test needed.

### Validated pagination

```rust
pub struct Pagination {
    limit: i64,   // invariant: 1..=100
    offset: i64,  // invariant: >= 0
}

impl Pagination {
    pub fn new(limit: i64, offset: i64) -> Self {
        Self {
            limit: limit.clamp(1, 100),
            offset: offset.max(0),
        }
    }

    pub fn limit(&self) -> i64 { self.limit }
    pub fn offset(&self) -> i64 { self.offset }
}
```

### When to use newtypes vs bare types

| Use newtype | Use bare type |
|---|---|
| Value has validation rules | Truly unconstrained (rare) |
| Two+ fields share the same primitive | Only one field of that type exists |
| Value crosses module/layer boundaries | Stays local to one function |
| Domain meaning matters (IDs, codes, quantities) | Infrastructure plumbing (pool sizes, ports) |

### Diesel integration

Newtypes need Diesel trait impls to work in queries. Three approaches, simplest first:

1. **Convert at the DB boundary** — newtypes live in the domain layer, `From` impls convert to/from bare types for Diesel models. Start here.
2. **`#[derive(AsExpression, FromSqlRow)]`** — for wrappers that appear directly in queries.
3. **Manual `FromSql`/`ToSql`** — for custom serialization needs.

---

## 7. Transactions & Batch Operations

### Transactions

Wrap multi-step mutations in an explicit transaction:

```rust
use diesel_async::scoped_futures::ScopedFutureExt;
use diesel_async::AsyncConnection;

let mut conn = pool.get().await?;
conn.transaction::<_, ApiError, _>(|conn| {
    async move {
        diesel::insert_into(resources::table)
            .values(&new_resource)
            .execute(conn).await?;

        diesel::insert_into(audit_log::table)
            .values(&log_entry)
            .execute(conn).await?;

        Ok(())
    }.scope_boxed()
}).await?;
```

**Rules:**
- Any handler that performs two or more write operations must use a transaction
- Never hold a transaction open across `.await` points that involve I/O outside the DB
- Keep transactions short — acquire the connection, do the work, release

### Batch operations

Prevent N+1 queries:

```rust
// WRONG — N+1
for id in &ids {
    let item = resources::table.find(id).first(&mut conn).await?;
}

// CORRECT — single query
let results = resources::table
    .filter(resources::id.eq_any(&ids))
    .load::<Resource>(&mut conn).await?;
```

For bulk inserts:
```rust
diesel::insert_into(resources::table)
    .values(&vec_of_new_resources)  // batch insert
    .execute(&mut conn).await?;
```

Do aggregations at the database level (`SUM`, `COUNT`, `GROUP BY`), not in application code.

---

## 8. Schema Migrations

Diesel migrations are the database schema source of truth.

**Workflow:**
1. `diesel migration generate <name>` — creates `up.sql` and `down.sql`
2. Write `up.sql` with the DDL change
3. Write `down.sql` with the reverse operation
4. Run migrations against your database(s)
5. Run `diesel print-schema` and update `schema.rs` (add any needed annotations)
6. Update Rust models to match the new schema
7. Regenerate any derived artifacts (OpenAPI spec, client code)
8. Run tests to verify

**SQL conventions:**
- Use quoted identifiers if your naming convention differs from Postgres defaults
- Always include `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- Always include `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` where applicable
- Write idempotent rollbacks (`DROP TABLE IF EXISTS`, `DROP INDEX IF EXISTS`)
- Include indexes on columns used in `WHERE`, `ORDER BY`, and `JOIN` clauses

**Never hand-edit the generated `schema.rs`** beyond adding required annotations (`#[sql_name]`, `#[diesel(column_name)]`).

---

## 9. Tower Middleware & Server Hardening

See API Design skill sections 11 and 15 for the security and resilience rationale. This section covers Rust/Axum implementation.

### Middleware stack order

Layer outermost to innermost:

```rust
use tower_http::{
    trace::TraceLayer,
    timeout::TimeoutLayer,
    limit::RequestBodyLimitLayer,
    cors::CorsLayer,
    compression::CompressionLayer,
    set_header::SetResponseHeaderLayer,
};

let app = Router::new()
    .route("/api/resources", get(list_resources).post(create_resource))
    // ... routes
    .with_state(state)
    // Innermost (applied last to request, first to response)
    .layer(CompressionLayer::new())
    .layer(cors_layer)
    .layer(RequestBodyLimitLayer::new(1024 * 1024))  // 1 MB
    .layer(TimeoutLayer::new(Duration::from_secs(30)))
    .layer(TraceLayer::new_for_http());
    // Outermost (applied first to request, last to response)
```

### Request body limits

```rust
.layer(RequestBodyLimitLayer::new(1024 * 1024))  // 1 MB for JSON APIs
```

### Request timeouts

```rust
.layer(TimeoutLayer::new(Duration::from_secs(30)))
```

### Response compression

```rust
.layer(CompressionLayer::new())  // gzip, br, deflate, zstd
```

### CORS hardening

```rust
CorsLayer::new()
    .allow_origin(AllowOrigin::list(allowed_origins))
    .allow_methods([Method::GET, Method::POST, Method::PUT, Method::DELETE])
    .allow_headers([CONTENT_TYPE, AUTHORIZATION])
    .max_age(Duration::from_secs(3600))
```

**Never** use `CorsLayer::permissive()` in production.

### Security headers

```rust
use axum::http::HeaderValue;

.layer(SetResponseHeaderLayer::overriding(
    header::X_CONTENT_TYPE_OPTIONS,
    HeaderValue::from_static("nosniff"),
))
.layer(SetResponseHeaderLayer::overriding(
    header::X_FRAME_OPTIONS,
    HeaderValue::from_static("DENY"),
))
```

### Rate limiting

```rust
let governor = GovernorConfigBuilder::default()
    .per_second(10)
    .burst_size(20)
    .finish()
    .unwrap();
app.layer(GovernorLayer { config: governor });
```

### Graceful shutdown

Drains in-flight requests before terminating — prevents 502s during deploys:

```rust
let listener = tokio::net::TcpListener::bind(addr).await?;
axum::serve(listener, app)
    .with_graceful_shutdown(shutdown_signal())
    .await?;

async fn shutdown_signal() {
    let ctrl_c = tokio::signal::ctrl_c();
    let mut terminate = tokio::signal::unix::signal(
        tokio::signal::unix::SignalKind::terminate(),
    ).expect("SIGTERM handler");
    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate.recv() => {},
    }
}
```

---

## 10. Observability

### Handler instrumentation

`#[tracing::instrument]` is mandatory on every public handler (see section 2).

**Inside handlers** — add spans for expensive operations:
```rust
let results = {
    let _span = tracing::info_span!("db.query", table = "resources").entered();
    resources::table.load::<Resource>(&mut conn).await?
};
```

### Structured logging

Always use typed fields, never string interpolation:

```rust
// CORRECT
tracing::info!(resource.id = %id, resource.name = %name, "Resource created");

// WRONG — unstructured, can't filter/aggregate
tracing::info!("Resource {} created with name {}", id, name);
```

**Never log sensitive data** — passwords, tokens, PII, full request bodies.

Log errors **only when handled** (in `IntoResponse`), never during propagation. This prevents duplicate log entries.

### Health checks — three endpoints

| Endpoint | Purpose | What it checks |
|---|---|---|
| `GET /health` | **Liveness** — process alive? | Always returns 200 (no dependencies) |
| `GET /ready` | **Readiness** — can serve traffic? | DB pool connectivity |
| `GET /metrics` | **Prometheus scrape** | All registered metrics |

The liveness probe must **never** check external dependencies. If Postgres is down, the process is still alive — the orchestrator should stop routing traffic (readiness), not restart the process.

```rust
pub async fn health() -> StatusCode {
    StatusCode::OK  // no dependency checks
}

pub async fn ready(State(state): State<AppState>) -> StatusCode {
    match state.pool.get().await {
        Ok(_) => StatusCode::OK,
        Err(_) => StatusCode::SERVICE_UNAVAILABLE,
    }
}
```

### Metric naming (Prometheus)

Follow the pattern `<namespace>_<subsystem>_<name>_<unit>`:

```
myapp_http_requests_total              // counter
myapp_http_request_duration_seconds    // histogram
myapp_db_connections_active            // gauge
myapp_db_query_duration_seconds        // histogram
```

### Trace sampling

For production, sample rather than recording 100% of traces:

```rust
use opentelemetry_sdk::trace::Sampler;
Sampler::ParentBased(Box::new(Sampler::TraceIdRatioBased(0.1)))  // 10%
```

Avoid high-cardinality span fields (e.g., user IDs as span names) — they cause cardinality explosion in trace backends.

---

## 11. Testing

### Parameterized tests with `rstest`

Test every validation branch without repetitive test functions:

```rust
use rstest::rstest;

#[rstest]
#[case("", false)]
#[case("   ", false)]
#[case("a".repeat(256).as_str(), false)]
#[case("Valid Name", true)]
fn test_display_name_validation(#[case] input: &str, #[case] valid: bool) {
    assert_eq!(DisplayName::try_new(input).is_ok(), valid);
}
```

Use `rstest::fixture` for test setup (like pytest fixtures):

```rust
#[fixture]
fn test_config() -> Config { Config::test_defaults() }

#[rstest]
fn test_pool_creation(test_config: Config) { ... }
```

### Snapshot testing with `insta`

For complex JSON responses and serialization correctness:

```rust
use insta::assert_json_snapshot;

#[test]
fn test_resource_serialization() {
    let resource = Resource { /* fields */ };
    assert_json_snapshot!(resource);
}
```

Run `cargo insta review` to approve/reject snapshot changes interactively. Snapshots live alongside tests in `__snapshots__/` directories.

### Property-based testing with `proptest`

Test invariants across random inputs:

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn pagination_offset_never_negative(page in 0i64..10000, per_page in 1i64..100) {
        let p = Pagination::new(per_page, page);
        prop_assert!(p.offset() >= 0);
        prop_assert!(p.limit() >= 1);
        prop_assert!(p.limit() <= 100);
    }
}
```

### Handler testing without a server

Axum handlers are `tower::Service` — test them directly:

```rust
use axum::body::Body;
use tower::ServiceExt;  // for oneshot

#[tokio::test]
async fn test_list_resources_returns_200() {
    let app = build_test_app().await;
    let response = app
        .oneshot(Request::builder().uri("/api/resources").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
}
```

### What to test

- **Every validation branch** — empty, too long, negative, wrong format
- **Happy path** — successful create, read, update, delete
- **Error paths** — not found, conflict, pool exhaustion
- **Serialization** — numeric format, enum casing, date format (use `insta`)
- **Pagination** — default limit, max limit enforcement, offset behavior
- **Transactions** — rollback on partial failure
- **Edge cases** — concurrent inserts, duplicate keys, empty results

### When to run

- `cargo test` after every handler/model change
- `cargo clippy` + `cargo fmt --check` before every commit
- **Never skip a failing test** — investigate root cause first

---

## 12. Security & Dependency Hygiene

### `cargo-deny`

Run in CI on every PR. Configure `deny.toml`:

```toml
[advisories]
vulnerability = "deny"
unmaintained = "warn"
yanked = "warn"

[licenses]
unlicensed = "deny"
allow = ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unicode-3.0"]

[bans]
multiple-versions = "warn"
wildcards = "deny"

[sources]
unknown-registry = "deny"
unknown-git = "deny"
```

### `cargo-audit`

Run `cargo audit` in CI. The RustSec Advisory Database is the canonical vulnerability source.

### Minimal feature flags

Disable unnecessary defaults to reduce attack surface and compile time:

```toml
# Prefer rustls over native-tls (no OpenSSL dependency)
reqwest = { version = "0.12", default-features = false, features = ["rustls-tls", "json"] }
```

### Input sanitization

- Trim all string inputs
- Enforce maximum lengths (prevent oversized payloads)
- Validate enum values against known variants
- Use `serde(deny_unknown_fields)` on API input structs to reject unexpected fields

### SQL injection prevention

Diesel's query builder parameterizes all queries. When `diesel::dsl::sql()` is needed, **never** interpolate user values into the SQL string.

### Response safety

- Never expose internal error details (SQL, stack traces, connection strings)
- Set appropriate CORS origins (section 9)
- Add security headers (section 9)

---

## 13. Performance

### Database

- Aggregations at the DB level (`SUM`, `COUNT`, `GROUP BY`), not in application code
- `LIMIT`/`OFFSET` with server-side max (or cursor pagination for deep pages)
- `.select()` to fetch only needed columns for list endpoints
- Index columns in `WHERE`, `ORDER BY`, and `JOIN` clauses
- Batch lookups with `.filter(id.eq_any(&ids))` instead of N queries

### Connection pool sizing

Start conservative and tune from metrics:
- **General formula**: `pool_size = num_cpus * 2` to `num_cpus * 4`
- Read-heavy workloads can use larger pools for read replicas
- Monitor connection wait times via metrics; adjust based on observed p99 latency, not guesswork

### Response compression

See section 9 — `CompressionLayer` reduces JSON bandwidth 60-80% for free.

### Allocator

Consider `tikv-jemallocator` for production binaries:

```rust
#[cfg(not(target_env = "msvc"))]
#[global_allocator]
static GLOBAL: tikv_jemallocator::Jemalloc = tikv_jemallocator::Jemalloc;
```

Cloudflare and Discord both report measurable memory reduction and more predictable latency with jemalloc.

### Async discipline

- Never block the async runtime — no `std::thread::sleep`, no synchronous I/O
- Use `tokio::time::sleep` if delays are needed
- All DB operations via `diesel-async` — never sync diesel in an async context
- Avoid `clone()` on large structs — prefer references and borrows
- Use `#[serde(skip_serializing_if = "Option::is_none")]` for optional fields

---

## 14. API Design Patterns

See API Design skill for contract definitions (idempotency, pagination, ETags, versioning). This section covers Rust implementation.

### Idempotency keys

```rust
pub async fn create_resource(
    State(state): State<AppState>,
    idempotency_key: Option<TypedHeader<IdempotencyKey>>,
    Json(payload): Json<CreateResource>,
) -> Result<(StatusCode, Json<Resource>), ApiError> {
    if let Some(key) = &idempotency_key {
        if let Some(cached) = lookup_idempotency(key, &state).await? {
            return Ok((StatusCode::OK, Json(cached)));
        }
    }
    // ... create resource, store result keyed by idempotency key (24h TTL)
}
```

### Cursor-based pagination

```rust
#[derive(Deserialize, IntoParams)]
pub struct CursorParams {
    pub after: Option<Uuid>,  // opaque cursor (last seen ID)
    pub limit: Option<i64>,
}

// Query: WHERE id > $cursor ORDER BY id ASC LIMIT $limit + 1
// If result has limit+1 items, there's a next page
// Return items[0..limit] and next_cursor = items[limit-1].id
```

Response shape:
```json
{
  "items": [...],
  "next_cursor": "550e8400-e29b-41d4-a716-446655440000",
  "has_more": true
}
```

### ETags and conditional requests

Implement via `TypedHeader<IfNoneMatch>` extractor and `ETag` response header. Use `updatedAt` timestamp or content hash as ETag basis.

### API versioning

Use nested `Router` for version grouping: `Router::new().nest("/v1", v1_routes).nest("/v2", v2_routes)`. Add `Sunset` and `Deprecation` headers via middleware on deprecated routers.

---

## 15. Resilience Patterns

See API Design skill section 15 for resilience concepts. Rust crate recommendations and implementation patterns:

### Circuit breaker

```rust
let breaker = CircuitBreaker::builder()
    .failure_policy(consecutive_failures(5))
    .success_policy(ConsecutiveSuccesses::new(3))
    .build();
```

### Retry with exponential backoff

Use `backon` crate:

```rust
use backon::{ExponentialBuilder, Retryable};

let result = || async { fetch_external_data().await }
    .retry(ExponentialBuilder::default().with_max_times(3))
    .await;
```

### Bulkhead (concurrency limiting)

```rust
use tower::limit::ConcurrencyLimitLayer;
app.layer(ConcurrencyLimitLayer::new(100))
```

### Fallback responses

```rust
match fetch_live_data(&state).await {
    Ok(data) => Ok(Json(data)),
    Err(e) => {
        tracing::warn!(error = %e, "Falling back to cached data");
        Ok(Json(get_cached_data(&state).await?))
    }
}
```

---

## 16. Clippy, Lints & Deprecated Patterns

### Clippy configuration

```toml
[lints.clippy]
pedantic = { level = "warn", priority = -1 }
nursery = { level = "warn", priority = -1 }
# Selectively allow noisy lints with justification:
module_name_repetitions = "allow"
must_use_candidate = "allow"
```

**Rules:**
- Fix all warnings — do not add `#[allow]` without a comment explaining why
- Run `cargo clippy` and `cargo fmt --check` before every commit
- Format with `cargo fmt` — no manual formatting debates

### Deprecated patterns to avoid

| Deprecated | Replacement | Since |
|---|---|---|
| `lazy_static!` | `std::sync::LazyLock` | Rust 1.80 |
| `once_cell::sync::Lazy` | `std::sync::LazyLock` | Rust 1.80 |
| `once_cell::sync::OnceCell` | `std::sync::OnceLock` | Rust 1.80 |
| `#[async_trait]` | Native async trait methods | Rust 1.75 |
| `native-tls` feature | `rustls-tls` (pure Rust) | ecosystem shift |

### MSRV

Set `rust-version` in `Cargo.toml` to a recent stable version. Update quarterly.

---

## 17. Pre-Commit Checklist

Before committing Rust changes, verify:

```bash
cargo clippy --all-targets -- -D warnings   # Lint (must pass clean)
cargo fmt --check                            # Format check
cargo test                                   # All tests pass
cargo audit                                  # No known vulnerabilities
cargo deny check                             # License + ban compliance
```

**Blocking issues — do not commit if any exist:**
- Clippy warnings (pedantic + nursery mode)
- Failing tests
- `.unwrap()` or `.expect()` in handler code
- Leaked database error details in client-facing responses
- `CorsLayer::permissive()` in production code
- Missing request body limit on routes accepting POST/PUT
- Missing timeout middleware
- Missing `#[utoipa::path]` or `#[tracing::instrument]` on public handlers
- `unsafe` code (should be caught by `#![forbid(unsafe_code)]`)
- `lazy_static!` or `#[async_trait]` (use std equivalents)
- Stale generated artifacts (OpenAPI spec, client code) after model/handler changes

---

## Quick Reference

| Task | Command | When |
|---|---|---|
| Lint | `cargo clippy --all-targets` | Before every commit |
| Format check | `cargo fmt --check` | Before every commit |
| Run tests | `cargo test` | After every change |
| Audit deps | `cargo audit` | CI, and before releases |
| License check | `cargo deny check` | CI, on every PR |
| Snapshot review | `cargo insta review` | After changing serialization |
| Generate schema | `diesel print-schema` | After migrations |
| Run migrations | `diesel migration run` | After writing migration SQL |
| Revert migration | `diesel migration revert` | To undo last migration |
