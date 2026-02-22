---
name: observability
description: |
  Language-agnostic observability skill covering traces, metrics, structured logging,
  health checks, frontend RUM, security, and configuration patterns.
  Covers: three pillars, span naming, metric naming, cardinality discipline, sampling,
  health check contracts, error tracking, client-side telemetry, PII exclusion.
  Use when: instrumenting services, designing health checks, adding telemetry to frontends,
  reviewing observability posture, or making tracing/metrics decisions.
version: 1.0.0
date: 2026-02-22
user-invocable: true
---

# Observability

Language-agnostic methodology for instrumenting production systems. Language-specific implementation lives in dedicated skills (`/rust` §10 for Rust, `/typescript` for frontend patterns). Project-specific config (service names, concrete metrics, endpoints) belongs in project rules — check the project's `CLAUDE.md`.

---

## 1. Observability Philosophy

Three pillars — traces, metrics, logs — each answers different questions:

| Pillar | Answers | Example |
|---|---|---|
| **Traces** | What happened during this request? | Latency breakdown across services |
| **Metrics** | What's the system doing right now? | Request rate, error rate, saturation |
| **Logs** | Why did this specific thing happen? | Validation failure details, error context |

**Instrument what matters:**
- Request latency and error rates (RED method: Rate, Errors, Duration)
- Resource saturation (USE method: Utilization, Saturation, Errors)
- Business-critical operations (payments, auth, data mutations)

**Avoid vanity metrics** — if nobody would act on an alert from a metric, don't collect it.

---

## 2. Service Identity

Name services consistently across all telemetry:

- Pattern: `<product>-<component>` (e.g., `myapp-api`, `myapp-frontend-ssr`, `myapp-worker`)
- The same name appears in traces, metrics, logs, and health check responses
- Use lowercase kebab-case
- Separate browser telemetry from SSR telemetry — they are different services with different lifecycles

---

## 3. Traces

### Span naming

Use `<noun>.<verb>` for span names:

```
http.request          // incoming HTTP request
db.query              // database query
cache.lookup          // cache read
email.send            // outbound email
payment.process       // business operation
```

**Never use high-cardinality values as span names** — URLs with IDs, user emails, or query strings cause cardinality explosion in trace backends. Put variable data in span attributes, not the span name.

### Context propagation

Use W3C TraceContext (`traceparent` / `tracestate` headers) for cross-service propagation. This is the standard — avoid vendor-specific propagation formats unless required by infrastructure.

### Cardinality discipline

Span attributes must have bounded cardinality:

| Safe | Dangerous |
|---|---|
| `http.method = "GET"` | `http.url = "/users/abc123/posts/def456"` |
| `db.table = "assets"` | `db.query = "SELECT * FROM..."` |
| `error.type = "NotFound"` | `error.message = "User 550e84... not found"` |

**Rule:** If an attribute can take more than ~100 distinct values, it needs review. Use parameterized forms (`/users/{id}`) instead of concrete values.

### Sampling strategies

| Environment | Strategy | Rationale |
|---|---|---|
| Development | 100% (sample all) | Full visibility for debugging |
| Staging | 100% or 50% | Catch issues before production |
| Production | Parent-based + ratio (1-10%) | Cost control without losing distributed context |

**Parent-based sampling** preserves trace completeness — if the parent span is sampled, all child spans in that trace are also sampled. This prevents orphaned spans.

---

## 4. Metrics

### Prometheus naming convention

Pattern: `<namespace>_<subsystem>_<name>_<unit>`

```
myapp_http_requests_total              // counter — total request count
myapp_http_request_duration_seconds    // histogram — request latency
myapp_db_connections_active            // gauge — current connection count
myapp_db_query_duration_seconds        // histogram — query latency
```

### Metric types

| Type | Use for | Example |
|---|---|---|
| **Counter** | Monotonically increasing values | Requests served, errors, bytes sent |
| **Gauge** | Values that go up and down | Active connections, queue depth, temperature |
| **Histogram** | Distribution of values | Request duration, response size |

**Counters** must only increase. Rate of change is computed at query time (`rate()`, `increase()`).

### Label cardinality

Labels multiply the number of time series. A metric with labels `method` (4 values) x `status` (5 values) x `endpoint` (50 values) = 1,000 series. Add `user_id` and you have unbounded growth.

**Rule:** Total label combinations per metric should stay under 1,000. Never use unbounded values (user IDs, request IDs, email addresses) as metric labels.

---

## 5. Structured Logging

### Typed fields over string interpolation

```
// CORRECT — structured, filterable, aggregatable
level=info resource.id=550e8400 resource.name="Widget" msg="Resource created"

// WRONG — unstructured, can't filter or aggregate
level=info msg="Resource 550e8400 created with name Widget"
```

### Log levels

| Level | When | Example |
|---|---|---|
| **ERROR** | Action required — something failed that shouldn't | DB connection lost, payment failed |
| **WARN** | Degraded but functional — investigate if persistent | Retry succeeded, cache miss fallback |
| **INFO** | Normal operations worth noting | Server started, request completed, config loaded |
| **DEBUG** | Diagnostic detail for development | Query parameters, intermediate state |

### Error logging discipline

Log errors **once, at the handling point** — never during propagation. This prevents duplicate log entries across the call stack.

```
// WRONG — logs at every level of the stack
fn inner() -> Result<T> {
    let result = db_call()?;  // log here
    Ok(transform(result)?)    // and here
}

// CORRECT — propagate with ?, log once when handled
fn handler() {
    match service.do_work() {
        Ok(v) => respond(v),
        Err(e) => {
            log_error(e);     // log once here
            error_response()
        }
    }
}
```

### Sensitive data exclusion

Never log: passwords, tokens, API keys, credit card numbers, SSNs, session IDs, PII beyond what's needed for debugging. See `claude/rules/secrets.md` for the full exclusion list.

---

## 6. Health Checks

Three distinct probe types with different contracts:

| Probe | Path | Checks | Fails when |
|---|---|---|---|
| **Liveness** | `/health` | Process alive | Process is deadlocked or crashed |
| **Readiness** | `/ready` | Can serve traffic | Dependencies unavailable |
| **Startup** | `/startup` | Initialization complete | Still warming up |

### Contracts

- **Liveness must never check external dependencies.** If the database is down, the process is still alive — the orchestrator should stop routing traffic (readiness), not restart the process (liveness).
- **Readiness checks dependencies** needed to serve traffic (DB pools, caches, required services).
- **Startup probes** prevent liveness checks during slow initialization (migration runs, cache warming).

### Response format

Return 200 for healthy, 503 for unhealthy. Keep responses minimal:

```json
{ "status": "ok" }
```

Add dependency details only to readiness checks, and only in non-production environments (to avoid leaking infrastructure info).

---

## 7. Frontend Observability (RUM)

Real User Monitoring captures what happens in the user's browser — the final mile of observability.

**Maturity note:** Browser OTEL instrumentation is experimental and evolving. The OpenTelemetry Browser SIG is actively reworking semantic conventions and shifting from span-based toward event-based instrumentations. Build on the stable patterns below, but expect API changes.

### Auto vs manual instrumentation

Auto-instrumentations handle the common signals. Add manual instrumentation only for business-specific operations.

| Signal | Instrumentation | Type | Notes |
|---|---|---|---|
| **Document load** | `DocumentLoadInstrumentation` | Auto | Navigation Timing API, resource timing |
| **User interactions** | `UserInteractionInstrumentation` | Auto | Click, submit events (opt-in per event type) |
| **Fetch/XHR requests** | `FetchInstrumentation` | Auto | Enables browser→API trace propagation |
| **Web Vitals** | `web-vitals` library + custom instrumentation | Manual | LCP, INP, CLS as spans or metrics |
| **JS errors** | `window.onerror` / `onunhandledrejection` | Manual | Global error capture outside component trees |
| **Business operations** | Custom spans via `tracer.startSpan()` | Manual | Checkout flow, search, form submission |

**Fetch instrumentation requires CORS coordination.** The browser injects `traceparent` and `tracestate` headers into outgoing requests. Configure `propagateTraceHeaderCorsUrls` to match your API origin, and ensure the backend CORS policy allows these headers. Without this, browser and API traces are disconnected.

### SSR-to-browser trace correlation

SSR renders HTML on the server — the browser needs the server's trace context to connect its spans to the SSR trace. Two patterns:

**Server-Timing header** (preferred, no HTML injection needed):
```
Server-Timing: traceresponse;desc="00-{traceId}-{spanId}-{flags}"
```
The browser's Performance API exposes `Server-Timing` entries, so client OTEL can read them without extra DOM manipulation. Multiple vendors (Splunk, Microsoft, Grafana) converged on this pattern independently.

**Meta tag injection** (alternative for SSR frameworks):
```html
<meta name="traceparent" content="00-{traceId}-{spanId}-{flags}" />
```
Client-side OTEL reads the meta tag during initialization and sets it as the parent context.

Both approaches create a single trace spanning SSR render → browser hydration → user interactions → API calls.

### Web Vitals integration

Core Web Vitals (LCP, INP, CLS) can be captured as OTEL spans or metrics via Google's `web-vitals` library:

**As spans** — each vital becomes a span with attributes (`web_vital.name`, `web_vital.value`, `web_vital.rating`). Enables correlation with page load traces in the trace timeline.

**As metrics** — export vitals as OTEL metrics for aggregation, trend analysis, and alerting. Better for dashboards and SLO monitoring.

**Recommendation:** Use spans for debugging and root-cause analysis, metrics for alerting and trends. Start with metrics (lower overhead), add spans when investigating specific performance regressions.

Decouple vital measurement from pageload span completion — vitals like CLS accumulate throughout the page lifecycle and should be sent as standalone spans/metrics, not tied to an arbitrary "page loaded" event.

### Client-side sampling

Browser telemetry generates high volume from potentially millions of users. Sample aggressively in production.

**Session-based sampling** (preferred over event-based):
- Sample all-or-nothing per session — preserves complete user journeys
- A sampled-out session produces zero telemetry, reducing both bandwidth and collector load
- 1-5% session sample rate for routine page loads

**Error sampling exception:**
- Always capture errors at 100% regardless of session sample rate
- Unhandled exceptions, promise rejections, and HTTP 5xx responses bypass the session sampler

**Span processor choice:**
- Development: `SimpleSpanProcessor` (immediate export, easier debugging)
- Production: `BatchSpanProcessor` (buffers and batches exports, reduces network overhead)

### Bundle size discipline

The full OTEL browser auto-instrumentation bundle is ~300 KB uncompressed (~60 KB gzipped). This matters for LCP.

**Mandatory: lazy load via dynamic `import()`**. Never block initial paint with telemetry SDK loading. Accept the trade-off of missing the first few seconds of telemetry — user experience always wins over diagnostics.

**Reduce bundle size:**
- Import individual instrumentations — never use `@opentelemetry/auto-instrumentations-web` (catch-all, includes unused packages)
- Ensure consistent `@opentelemetry/*` package versions to avoid duplicate bundling
- Mark `sideEffects: false` if your bundler doesn't detect it automatically (~40 KB savings)
- Use OTEL JS SDK 2.x+ for improved tree-shakability

### Async context propagation

Browsers lack Node's `AsyncLocalStorage`. The `ZoneContextManager` (from `@opentelemetry/context-zone`, wraps `zone.js`) provides async context propagation, so spans created in `setTimeout`, `Promise`, and `fetch` callbacks properly attach to their parent spans.

**Trade-off:** `zone.js` adds ~40 KB to the bundle and patches all async APIs. Without it, async operations lose trace context — manually created spans won't connect to their parent. Skip it if you rely only on auto-instrumentations (which manage their own context); add it if you create manual spans across async boundaries.

### Error tracking

**Global error capture:**
- `window.onerror` catches synchronous errors and some async errors
- `window.onunhandledrejection` catches unhandled promise rejections
- Both should create error spans with the current route/page as context

**React error boundaries as telemetry sources:**
```tsx
componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
  const span = trace.getActiveSpan();
  if (span) {
    span.recordException(error);
    span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
  }
  // Render fallback UI — never let telemetry failure prevent error recovery
}
```

**Error grouping:** Use `error.name` + normalized `error.message` (strip variable parts like IDs) as the grouping key. High-cardinality error messages (containing user data or request IDs) cause the same cardinality explosion as high-cardinality span names.

**Stack trace safety:** Strip source map details and file paths before sending to external collectors. Internal file paths leak project structure; source-mapped stack traces leak source code.

### Developer overrides

Provide a mechanism to enable telemetry in environments where it's disabled by default (e.g., `localStorage.setItem("otel", "true")`). This lets developers debug telemetry pipelines without changing config.

---

## 8. Security

### PII and secret exclusion

- **Span attributes:** Use an allowlist approach — only include fields you've explicitly reviewed
- **Logs:** Never log authentication tokens, passwords, credit card numbers, or PII (see `claude/rules/secrets.md`)
- **Metrics labels:** Never use PII as label values (email, name, IP address)
- **Error messages:** Sanitize before including in spans — DB errors may contain table/column names or query fragments

### Safe error reporting

- Server-side: Log full error context internally, return generic messages to clients
- Client-side: Capture errors for telemetry but never send full stack traces to third-party collectors without sanitization
- Never include internal service names, infrastructure details, or dependency versions in client-visible telemetry

### OTEL endpoint security

- Use HTTPS for production OTEL endpoints
- Authenticate with API keys or mTLS — never send telemetry to unauthenticated endpoints in production
- Separate dev/staging/production collector endpoints

For broader security patterns, see `/web-security`. For secret handling, see `claude/rules/secrets.md`.

---

## 9. Configuration

### Toggle pattern

Observability should be toggleable per environment:

```
telemetry:
  enabled: true/false      # master switch
  endpoint: "https://..."  # collector URL
```

- **Development:** Enabled when local collector is running (Docker), disabled otherwise
- **CI:** Disabled (no collector available)
- **Production:** Always enabled

### Dev overrides

Support developer-level overrides that don't require config changes:

- Environment variable (server-side): e.g., `OTEL_ENABLED=true`
- LocalStorage (browser-side): e.g., `localStorage.setItem("otel", "true")`

These overrides should OR with the config toggle — if either is true, telemetry initializes.

---

## 10. Anti-patterns

| Anti-pattern | Problem | Fix |
|---|---|---|
| User IDs as span names | Cardinality explosion | Put in span attributes with bounded hashing |
| Logging during error propagation | Duplicate log entries | Log once at the handling point |
| 100% sampling in production | Cost and storage explosion | Parent-based + ratio sampling (server), session-based (browser) |
| Chatty client telemetry | Bandwidth waste, collector overload | Session-based sampling at 1-5%, `BatchSpanProcessor` |
| Sensitive data in traces | Security/compliance violation | Allowlist span attributes, sanitize errors |
| Health checks that test dependencies | False restarts on dependency failures | Liveness = process only, readiness = dependencies |
| Blocking page load with OTEL SDK | User experience degradation | Lazy `import()` after interactive |
| Vanity metrics nobody alerts on | Noise, storage cost | If you won't alert on it, don't collect it |
| `auto-instrumentations-web` catch-all | Bundle bloat (~300 KB), includes unused packages | Import individual instrumentations selectively |
| `SimpleSpanProcessor` in production | Synchronous export per span, performance impact | Use `BatchSpanProcessor` for batched async export |
| Fetch without CORS coordination | Browser→API traces disconnected | Configure `propagateTraceHeaderCorsUrls` + backend CORS |
| Tying Web Vitals to pageload span | CLS accumulates over page lifetime, value is stale | Send vitals as standalone spans/metrics |
| Source maps in external telemetry | Leaks project structure and source code | Strip paths and source map details before export |
| High-cardinality error messages | Grouping explosion in error tracking | Normalize messages, strip variable IDs |
