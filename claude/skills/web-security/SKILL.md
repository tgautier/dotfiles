---
name: web-security
description: |
  Browser-facing and cross-cutting web security skill for production applications.
  Covers: CSRF, XSS, CSP, cookie security, CORS, session management, authentication,
  JWT security, OAuth 2.1, SSRF, security headers, input validation, dependency scanning,
  and OWASP API Security Top 10.
  Use when: implementing auth, reviewing security posture, configuring CORS/CSP/cookies,
  or hardening endpoints against browser-based attacks.
  Sources: OWASP cheat sheets, Google BeyondCorp, Stripe, Cloudflare, Mozilla, Auth0, RFC 9700.
version: 1.0.0
date: 2026-02-22
user-invocable: true
---

# Web Security

Cross-cutting browser-facing security guidance for production web applications. This skill deepens topics that span API design, frontend, and backend — CSRF, XSS, CSP, cookies, sessions, auth, JWT, OAuth 2.1, CORS, headers, SSRF, input validation, and supply chain security.

Based on OWASP cheat sheets (2024), Google BeyondCorp, Stripe security patterns, Cloudflare production configs, Mozilla Web Security Guidelines, Auth0/Okta best practices, and OAuth 2.1 / RFC 9700 (January 2025).

> **Scope boundary:** This skill covers *what* to enforce and *why*. For implementation:
> - Rust/Axum middleware and Tower layers → **Rust skill** (`/rust` §9, §12)
> - React patterns, `dangerouslySetInnerHTML`, `href` validation → **TypeScript skill** (`/typescript` §11)
> - API contract decisions (error format, status codes, auth headers) → **API Design skill** (`/api-design` §10-11)

---

## 1. Threat Model

### Browser vs API attack surfaces

| Attack | Vector | Target |
|--------|--------|--------|
| CSRF | Forged cross-origin request with ambient cookies | Cookie-authenticated mutations |
| XSS | Injected script in HTML context | Session tokens, user data, DOM |
| Clickjacking | Transparent iframe overlay | User actions on framed page |
| SSRF | Server fetches attacker-controlled URL | Internal services, cloud metadata |
| CORS misconfiguration | Overly permissive origin policy | Cross-origin data leakage |
| Session fixation | Attacker sets victim's session ID | Account takeover |
| JWT confusion | Algorithm substitution or claim bypass | Authentication bypass |

### OWASP API Security Top 10 (2023) — quick reference

| # | Risk | Key mitigation |
|---|------|---------------|
| API1 | Broken Object-Level Authorization | Check object ownership in every handler |
| API2 | Broken Authentication | Rate limit auth endpoints, enforce MFA |
| API3 | Broken Object Property-Level Authorization | Filter response fields by role |
| API4 | Unrestricted Resource Consumption | Rate limiting, pagination limits, payload size caps |
| API5 | Broken Function-Level Authorization | RBAC middleware on every route |
| API6 | Unrestricted Access to Sensitive Business Flows | Bot detection, CAPTCHA on sensitive actions |
| API7 | Server-Side Request Forgery | Input validation, private IP denylist, egress firewall |
| API8 | Security Misconfiguration | Security headers, disable debug endpoints, least privilege |
| API9 | Improper Inventory Management | API versioning, deprecation policy, endpoint registry |
| API10 | Unsafe Consumption of APIs | Validate third-party responses, timeout external calls |

> See **API Design skill** (`/api-design` §10) for contract-level auth patterns.

---

## 2. CSRF Protection

### When CSRF matters

- **Needed:** Cookie-based authentication + state-changing operations (POST/PUT/DELETE)
- **Not needed:** Bearer token auth (no ambient credentials), API keys in headers, machine-to-machine

### Defense layers (OWASP — implement at least two)

1. **Signed double-submit cookie** (primary defense)
   - Generate HMAC-signed token bound to the session ID — `HMAC(session_id, secret_key)`
   - Send in cookie + require in request header (`X-CSRF-Token`) or form field
   - Server verifies HMAC signature matches session — prevents cookie-tossing attacks
   - **Never use unsigned/naive double-submit** — OWASP explicitly discourages it (attacker on subdomain can overwrite unsigned cookies)

2. **Fetch Metadata validation** (server-side, 98% browser coverage)
   - Reject requests where `Sec-Fetch-Site: cross-site` on state-changing endpoints
   - Also check `Sec-Fetch-Mode` and `Sec-Fetch-Dest` for defense-in-depth
   - Graceful degradation: allow requests without Fetch Metadata headers (older browsers)

3. **Custom request headers** (CORS-based defense)
   - Require a custom header (e.g., `X-Requested-With`) on mutations
   - CORS preflight blocks cross-origin requests with custom headers unless explicitly allowed
   - Simple but effective — cross-origin `<form>` and `<img>` cannot set custom headers

4. **SameSite cookies** (necessary but insufficient alone)
   - `SameSite=Lax` minimum — blocks cross-site POST submissions
   - `SameSite=Strict` — blocks all cross-site requests (breaks inbound links that need auth)
   - **Not sufficient alone:** subdomain attacks bypass SameSite, method override can convert GET→POST

5. **Origin / Referer verification** (secondary check)
   - Verify `Origin` header matches expected domain on mutations
   - Fall back to `Referer` if `Origin` absent
   - Secondary defense — don't rely on this alone (privacy extensions strip headers)

### Key rule

**XSS defeats all CSRF protections.** If an attacker can execute JavaScript on your origin, they can read CSRF tokens from the DOM or cookies. Fix XSS first.

### CSRF in OAuth flows

Stripe pattern: use the `state` parameter as a CSRF token — bind to the user's session, verify on callback. One-time use, expire after 5 minutes.

---

## 3. XSS Prevention

### Context-specific output encoding (OWASP 5 rules)

| Context | Encoding | Example |
|---------|----------|---------|
| HTML body | HTML entity encode `& < > " '` | `<p>Hello &lt;script&gt;</p>` |
| HTML attribute | Attribute encode (all non-alphanumeric as `&#xHH;`) | `<input value="&#x22;injected">` |
| JavaScript string | JavaScript hex encode (`\xHH`) | `var x = '\x3cscript\x3e'` |
| URL parameter | URL encode (`%HH`) | `?q=%3Cscript%3E` |
| CSS value | CSS hex encode (`\HH`) | `background: \3cscript\3e` |

### Dangerous contexts — never place untrusted data in

- Inside `<script>` blocks (even encoded)
- Event handler attributes (`onclick`, `onerror`, `onload`)
- `eval()`, `setTimeout(string)`, `new Function(string)`
- CSS `expression()` or `url()` with user input
- `javascript:` URLs in `href` or `src`

### Framework-specific

- **React:** Auto-escapes JSX curly braces. Risk vectors: `dangerouslySetInnerHTML` (sanitize with DOMPurify), `href` attributes (validate against `javascript:` URLs), `ref` callbacks with user data
- **Trusted Types API:** Enforce via CSP `require-trusted-types-for 'script'` — prevents DOM XSS at the browser level
- **User-authored HTML:** Sanitize with DOMPurify configured with an explicit tag/attribute allowlist

> See **TypeScript skill** (`/typescript` §11) for React-specific XSS patterns and `<SafeHTML>` component.

---

## 4. Content Security Policy

### Strict nonce-based policy (recommended)

```
Content-Security-Policy:
  default-src 'self';
  script-src 'nonce-{RANDOM}' 'strict-dynamic';
  style-src 'self' 'nonce-{RANDOM}';
  object-src 'none';
  base-uri 'none';
  form-action 'self';
  frame-ancestors 'none';
```

- **Nonce:** Generate a cryptographically random value per response, inject into `<script nonce="...">` tags
- **`strict-dynamic`:** Allows scripts loaded by nonced scripts (dynamic imports, trusted loaders) without explicit allowlisting
- **`object-src 'none'`:** Blocks Flash/Java plugin abuse
- **`base-uri 'none'`:** Prevents `<base>` tag injection (relative URL hijacking)
- **`frame-ancestors 'none'`:** Replaces `X-Frame-Options: DENY` for clickjacking protection

### API-only CSP

```
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
```

APIs serve no HTML — lock everything down. Cloudflare recommends different header sets for API vs HTML responses.

### Never use

- `unsafe-inline` for scripts (defeats CSP purpose)
- `unsafe-eval` (allows `eval()` — XSS vector)
- Wildcard `*` in `script-src` or `default-src`

### Rollout strategy (all sources agree)

1. Deploy `Content-Security-Policy-Report-Only` with report-uri
2. Monitor violations for 1-2 weeks
3. Fix legitimate violations (inline scripts → nonced, `eval()` → alternatives)
4. Switch to enforcing `Content-Security-Policy`
5. Keep report-uri active for ongoing monitoring

---

## 5. Cookie Security

### Recommended cookie configuration (Mozilla)

```
__Host-SESSION=<value>; Path=/; Secure; HttpOnly; SameSite=Strict
```

### Cookie prefixes

| Prefix | Requirements | Use for |
|--------|-------------|---------|
| `__Host-` | `Secure`, no `Domain`, `Path=/` | Session cookies (strictest — prevents subdomain attacks) |
| `__Secure-` | `Secure` only | Cookies that need subdomain sharing |

### Required attributes

| Attribute | Value | Why |
|-----------|-------|-----|
| `Secure` | (flag) | HTTPS only — prevents network sniffing |
| `HttpOnly` | (flag) | No JavaScript access — mitigates XSS token theft |
| `SameSite` | `Strict` or `Lax` | CSRF mitigation (see §2 for limitations) |
| `Path` | `/` | Scope to entire site |

### Session cookies

- **No `Max-Age` or `Expires`** — cookie dies with browser session
- Explicit expiry on the server side via session store TTL

### Token storage comparison

| Location | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| `HttpOnly` cookie | XSS-proof, auto-sent | CSRF risk (mitigate per §2) | **Preferred for auth** |
| `localStorage` | Simple API | XSS reads it directly | **Never for auth tokens** |
| `sessionStorage` | Tab-scoped | XSS reads it, lost on tab close | **Never for auth tokens** |
| Web Worker | No DOM access | Complex setup | Acceptable for SPAs |

### BFF pattern (Auth0)

Backend-for-Frontend: the frontend never sees tokens. The backend holds access/refresh tokens in `HttpOnly` cookies, proxies API calls with Bearer tokens attached server-side. Eliminates frontend token storage concerns entirely.

> See **API Design skill** (`/api-design` §10) for token type decisions (JWT vs opaque).

---

## 6. Session Management

### Session ID requirements (OWASP)

- **128-bit minimum entropy** generated by CSPRNG
- Regenerate session ID on: login, privilege escalation, switching from HTTP to HTTPS
- Rename default session cookie (don't use `JSESSIONID`, `PHPSESSID`, etc.)

### Timeouts

| Type | High-value apps | Low-risk apps |
|------|----------------|---------------|
| Idle timeout | 2-5 minutes | 15-30 minutes |
| Absolute timeout | 4-8 hours | 12-24 hours |

### Logout

Server-side destruction is mandatory — expiring the cookie alone is insufficient:

1. Destroy session in server store (database/cache)
2. Clear session cookie (`Set-Cookie` with `Max-Age=0`)
3. Clear any related tokens (refresh tokens, CSRF tokens)

### Session binding

Bind sessions to client fingerprint for theft detection:

- Client IP address (detect IP change → force re-auth)
- User-Agent string (detect browser change)
- TLS certificate (mutual TLS environments)

### Re-authentication triggers

Require fresh authentication before:

- Password change
- Email/phone change
- Payment method changes
- New device or unfamiliar IP
- Elevated privilege actions

---

## 7. Authentication

### Password rules (NIST SP 800-63B)

| Rule | Value |
|------|-------|
| Minimum length | 8 chars (with MFA) / 15 chars (without) |
| Maximum length | 64+ characters (never truncate) |
| Composition rules | **None** — no uppercase/special char requirements |
| Rotation | **Never** require periodic rotation |
| Breached check | Check against known breached databases (HIBP API) |
| Feedback | Show real-time strength meter based on entropy |

### Password storage

- **Argon2id** (preferred) — memory-hard, resists GPU/ASIC attacks
- **bcrypt** (acceptable) — widely supported, 72-byte input limit
- **scrypt** (acceptable) — memory-hard alternative
- **Always** use constant-time comparison for hash verification
- **Never** use MD5, SHA-1, SHA-256, or PBKDF2-SHA1 for password storage

### Brute force protection

- Track failed attempts per account (not per IP — attackers rotate IPs)
- Exponential backoff: 1s, 2s, 4s, 8s after consecutive failures
- Lockout threshold: 5-10 failed attempts → temporary lock (15-30 min)
- CAPTCHA after 3 failures as an alternative to lockout

### User enumeration prevention

All authentication failure responses must be **identical** in:

- Error message text ("Invalid credentials" — never "User not found" vs "Wrong password")
- Response time (add artificial delay to fast-path failures)
- HTTP status code (same 401 for all failure types)
- Response body structure

> See **API Design skill** (`/api-design` §10) for auth header patterns and token types.

---

## 8. JWT Security

### Algorithm selection

- **RS256** (RSA + SHA-256) — asymmetric, preferred (Auth0/OWASP consensus)
- **ES256** (ECDSA) — smaller keys, equivalent security
- **Never HS256** for multi-party systems — shared secret means any verifier can forge tokens
- **Never `alg: none`** — disable in JWT library configuration
- **Algorithm confusion attack:** Server must enforce expected algorithm, never trust the `alg` header

### Required claim validation

| Claim | Check | On failure |
|-------|-------|-----------|
| `iss` (issuer) | Exact match against known issuer | Reject |
| `aud` (audience) | Must contain this service's identifier | Reject |
| `exp` (expiration) | Current time < exp (with clock skew tolerance) | Reject |
| `nbf` (not before) | Current time >= nbf | Reject |
| `iat` (issued at) | Reasonable recency check | Reject |
| `sub` (subject) | Valid user identifier format | Reject |

### Token lifetimes

| Token | Lifetime | Storage |
|-------|----------|---------|
| Access token | 15-30 minutes | `HttpOnly` cookie or memory |
| Refresh token (absolute) | 30 days max | `HttpOnly` cookie, server-side record |
| Refresh token (idle) | 7 days | Revoke if unused |

### Token sidejacking prevention (OWASP)

1. Generate a random fingerprint at authentication
2. Store fingerprint in a hardened `HttpOnly` cookie
3. Hash the fingerprint (SHA-256) and embed in JWT claim
4. On each request: hash the cookie value, compare to JWT claim
5. Mismatch → reject (token was stolen but cookie wasn't)

### Revocation

- Maintain a SHA-256 denylist of revoked token identifiers (`jti` claim)
- Check denylist on every validation (cache in Redis/memory)
- Retain denylist entries until the token's `exp` passes
- Revoke on: logout, password change, security incident

---

## 9. OAuth 2.1 & RFC 9700

### What OAuth 2.1 (RFC 9700, January 2025) changes

**Removed:**
- Implicit grant (was `response_type=token`) — tokens in URL fragments are insecure
- Resource Owner Password Credentials (ROPC) grant — exposes credentials to client
- Bearer tokens in URL query strings (`?access_token=...`) — logged in server access logs

**Required:**
- **PKCE for ALL clients** — not just public clients (confidential clients too)
- **Exact redirect URI matching** — no wildcards, no partial matching, no path traversal
- **Sender-constrained refresh tokens** for public clients — rotation on every use, or DPoP/mTLS binding

### PKCE flow (required for all)

1. Client generates `code_verifier` (43-128 chars, `[A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"`)
2. Client computes `code_challenge = BASE64URL(SHA256(code_verifier))`
3. Authorization request includes `code_challenge` + `code_challenge_method=S256`
4. Token exchange includes `code_verifier` — server verifies against stored challenge
5. **Never use `plain` method** — always `S256`

### Refresh token rotation (Auth0)

- Issue new refresh token on every use, invalidate the old one
- **Reuse detection:** If a previously-used refresh token is presented → revoke entire token family (theft signal)
- 200 token cap per user per application
- Absolute lifetime: 30 days (re-auth required after)

### Security requirements (RFC 9700 specifics)

- No CORS headers at the authorization endpoint
- Never use HTTP 307 redirects with credentials (use 302/303)
- `state` parameter must be one-time-use CSRF token bound to session
- Authorization codes: single-use, expire in 10 minutes max

---

## 10. CORS Hardening

### Rules

- **Explicit origin allowlist** — never `Access-Control-Allow-Origin: *` with credentials
- Validate `Origin` header against allowlist on every request (not just preflight)
- **Preflight caching:** Set `Access-Control-Max-Age` (e.g., 7200 seconds) to reduce preflight requests
- **Credential requests:** `Access-Control-Allow-Credentials: true` requires a specific origin (not `*`)

### Common mistakes

- Reflecting the `Origin` header back as `Access-Control-Allow-Origin` without validation (allows any origin)
- Allowing `null` origin (local files, sandboxed iframes can send `Origin: null`)
- Trusting subdomains blindly (XSS on `evil.sub.example.com` compromises `api.example.com`)
- Exposing sensitive headers via `Access-Control-Expose-Headers` unnecessarily

### API vs HTML distinction (Cloudflare)

- HTML responses: full security header set (CSP, HSTS, X-Frame-Options, etc.)
- API responses: minimal headers (CORS, Content-Type, cache controls) — HTML-specific headers are unnecessary noise

> See **Rust skill** (`/rust` §9) for Axum Tower CORS middleware implementation.

---

## 11. Security Headers Checklist

### Consensus header set (OWASP + Cloudflare + Mozilla)

| Header | Value | Notes |
|--------|-------|-------|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | 2 years, all subdomains, HSTS preload list |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Clickjacking defense (pair with CSP `frame-ancestors`) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Send origin only on cross-origin, full URL same-origin |
| `Cross-Origin-Opener-Policy` | `same-origin` | Isolates browsing context from cross-origin popups |
| `Cross-Origin-Embedder-Policy` | `require-corp` | Enables `SharedArrayBuffer`, cross-origin isolation |
| `Cross-Origin-Resource-Policy` | `same-site` | Prevents cross-site embedding of resources |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=(), interest-cohort=()` | Disable unused browser features |
| `X-XSS-Protection` | `0` | Auditor removed from all browsers — disable to avoid false positives |
| `Content-Type` | Include charset: `application/json; charset=UTF-8` | Prevents charset-based XSS |

### Headers to remove

| Header | Why |
|--------|-----|
| `Server` | Leaks server software and version |
| `X-Powered-By` | Leaks framework (Express, Rails, etc.) |
| `Expect-CT` | Deprecated — Certificate Transparency is now enforced by default |
| `Public-Key-Pins` | Deprecated — risk of bricking sites, replaced by CT |

---

## 12. SSRF Prevention

### Application layer (OWASP)

1. **Validate input:** Check URL format before processing
2. **Resolve domain:** DNS-resolve the hostname before connecting
3. **Check against private IP denylist:**
   - `10.0.0.0/8` (RFC 1918)
   - `172.16.0.0/12` (RFC 1918)
   - `192.168.0.0/16` (RFC 1918)
   - `127.0.0.0/8` (loopback)
   - `169.254.0.0/16` (link-local, including cloud metadata at `169.254.169.254`)
   - `::1`, `fc00::/7`, `fe80::/10` (IPv6 equivalents)
4. **Disable redirect following** — or re-validate after each redirect
5. **Protocol allowlist:** HTTP and HTTPS only (block `file://`, `gopher://`, `dict://`)
6. **Response handling:** Don't return raw responses to users (information leakage)

### Network layer

- Firewall egress rules: restrict outbound connections from application servers
- Network segmentation: application servers cannot reach internal services directly
- Cloud metadata: use IMDSv2 only (AWS) — requires session token, prevents SSRF to metadata endpoint

---

## 13. Input Validation

### Principles (OWASP)

- **Server-side mandatory** — client-side validation is UX only, never a security boundary
- **Allow-list over deny-list** — define what IS valid, not what ISN'T
- **Validate syntactically, then semantically** — check format first, then business rules

### String validation

| Check | Rule |
|-------|------|
| Length | Enforce min and max (prevent buffer abuse, empty strings) |
| Charset | Allowlist valid characters for the field |
| Unicode | Normalize (NFKC) before validation (prevents homograph attacks) |
| Regex | Always anchor: `^pattern$` (unanchored regex matches substrings) |
| ReDoS | Test regex patterns for catastrophic backtracking — avoid nested quantifiers `(a+)+` |

### Email validation

- Max 254 characters (RFC 5321)
- Don't over-validate format — send a verification email instead
- Verification token: single-use, 32+ characters, 8-hour TTL
- Normalize: lowercase the domain portion (local part is case-sensitive per spec, but lowercase in practice)

### File upload validation

| Check | Rule |
|-------|------|
| Extension | Allowlist (`jpg`, `png`, `pdf`) — never denylist |
| Filename | Rename to random UUID (prevents path traversal) |
| Content-Type | Verify magic bytes match declared type |
| Size | Enforce max file size at web server level (before application) |
| Storage | Store outside web root, serve via controlled endpoint |
| Malware | Scan with antivirus on upload |

> See **Rust skill** (`/rust` §12) for Diesel parameterized queries (SQL injection prevention).
> See **TypeScript skill** (`/typescript` §11) for framework-level input handling.

---

## 14. Dependency & Supply Chain Security

### Automated scanning

| Tool | Language | Run in CI |
|------|----------|-----------|
| `yarn npm audit` | JavaScript/TypeScript | Every PR |
| `cargo audit` | Rust | Every PR |
| `cargo deny` | Rust (license + advisory) | Every PR |

### Lock file integrity

- Commit lock files (`yarn.lock`, `Cargo.lock`) — ensures reproducible builds
- CI should fail if lock file is out of sync with manifest
- Review lock file diffs on dependency updates (detect supply chain substitution)

### API key leak prevention (Stripe pattern)

- Prefix keys: `sk_live_`, `sk_test_`, `pk_live_`, `pk_test_`
- Prefixes enable automated scanning in: git hooks, CI, GitHub secret scanning
- Rotate immediately on exposure — assume compromised

### Subresource Integrity (SRI)

```html
<script src="https://cdn.example.com/lib.js"
        integrity="sha384-{hash}"
        crossorigin="anonymous"></script>
```

- Required for all externally-hosted scripts
- Prevents CDN compromise from injecting malicious code
- Generate with `shasum -b -a 384 lib.js | awk '{ print $1 }' | xxd -r -p | base64`

### Minimal dependency philosophy

- Every dependency is an attack surface — prefer standard library when possible
- Audit new dependencies before adding: maintenance status, contributor count, known vulnerabilities
- Pin major versions, allow patch updates only in CI

> See **TypeScript skill** (`/typescript` §11) for npm-specific patterns.
> See **Rust skill** (`/rust` §12) for cargo-specific patterns.
