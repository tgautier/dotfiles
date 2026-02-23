---
name: typescript
description: |
  TypeScript language patterns, testing methodology, and build tooling for production applications.
  Covers: type safety, testing (Vitest/Playwright), performance optimization,
  security practices, linting, module patterns, and build configuration.
  Use when: configuring TypeScript strictness, writing tests, optimizing bundles,
  reviewing security, or setting up build tooling.
version: 2.0.0
date: 2026-02-23
user-invocable: true
---

# TypeScript Language & Build Tooling

For React-specific patterns (hooks, state, data fetching, error boundaries), see the React skill (`/react`). For component design, form UX, and accessibility, see the UX Design skill (`/ux-design`). For CSS and responsive patterns, see the CSS & Responsive skill (`/css-responsive`).

---

## 1. TypeScript Strictness

### Maximum strictness in `tsconfig.json`

```jsonc
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noPropertyAccessFromIndexSignature": true,
    "noFallthroughCasesInSwitch": true,
    "verbatimModuleSyntax": true
  }
}
```

- `noUncheckedIndexedAccess` — adds `| undefined` to array/object index access. Forces narrowing on `arr[0]` and `Record` lookups.
- `exactOptionalPropertyTypes` — distinguishes "property missing" from "property is `undefined`". Optional `foo?: string` can be omitted but cannot be explicitly set to `undefined`.
- `noPropertyAccessFromIndexSignature` — forces bracket notation for index signatures, clarifying dynamic vs known property access.
- `verbatimModuleSyntax` — preserves ES module syntax untouched, critical for tree-shaking in Vite/Rollup.

### `satisfies` over type annotations

Use `satisfies` when you want validation against a type but need to preserve literal inference:

```typescript
// WRONG: loses literal type information
const config: Config = { theme: "dark", retries: 3 };

// CORRECT: validates against Config but preserves literals
const config = { theme: "dark", retries: 3 } as const satisfies Config;
// config.theme is "dark", not string
```

### Branded types for domain identifiers

> For identifying which concepts need branded types (entities vs value objects, aggregate boundaries), see the **Domain Design skill** (`/domain-design` §3-4).

Prevent mixing semantically different values that share the same primitive type:

```typescript
type UserId = string & { readonly __brand: unique symbol };
type OrderId = string & { readonly __brand: unique symbol };

function createUserId(id: string): UserId { return id as UserId; }
function createOrderId(id: string): OrderId { return id as OrderId; }

function getUser(id: UserId): User { /* ... */ }
getUser(orderId); // compile error
```

### Discriminated unions for state machines

Eliminate impossible states:

```typescript
type FetchState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: Error };
```

No `data` on error, no `error` on success. Enables exhaustive `switch` narrowing.

### Anti-patterns

- **Never use `any`** — use `unknown` and narrow, or use generics
- **Never use `as` for type assertions** unless you've proven correctness (prefer type guards)
- **Never use `// @ts-ignore`** — use `// @ts-expect-error` with an explanation if truly needed
- **Never use `enum`** — use `as const` objects or string literal unions (enums have runtime footprint and tree-shaking issues)

```typescript
// WRONG
enum Status { Active, Inactive }

// CORRECT
const Status = { Active: "active", Inactive: "inactive" } as const;
type Status = (typeof Status)[keyof typeof Status];
```

---

## 2. Testing

### Layered strategy

1. **Unit tests (Vitest):** Pure functions, hooks, validation schemas. Fast feedback loop.
2. **Component tests (Vitest + Testing Library):** User-facing behavior with `userEvent`.
3. **Integration tests (Vitest + MSW):** Full component trees with mocked API responses.
4. **E2E tests (Playwright):** 3-5 critical user flows only. Keep the suite small.

### Test user behavior, not implementation

```tsx
// WRONG: testing implementation details
expect(component.state.isOpen).toBe(true);

// CORRECT: testing what the user sees
await userEvent.click(screen.getByRole("button", { name: /open menu/i }));
expect(screen.getByRole("menu")).toBeVisible();
```

### Use `userEvent` over `fireEvent`

`userEvent` simulates real user interactions (focus, hover, type individual characters). `fireEvent` dispatches raw DOM events that skip browser behavior:

```tsx
// WRONG
fireEvent.change(input, { target: { value: "hello" } });

// CORRECT
await userEvent.type(input, "hello");
```

### MSW for API mocking

Mock at the network layer, not at the module layer. Reuse handlers across Vitest and Playwright:

```typescript
import { http, HttpResponse } from "msw";

export const handlers = [
  http.get("/api/resources", () => {
    return HttpResponse.json([{ id: "1", name: "Test" }]);
  }),
];
```

### Stop using snapshot tests

Snapshots create noise, break on any DOM change, and discourage TDD:

```tsx
// WRONG
expect(container).toMatchSnapshot();

// CORRECT: explicit assertions on what matters
expect(screen.getByRole("heading")).toHaveTextContent("Dashboard");
expect(screen.getByTestId("item-count")).toHaveTextContent("42");
```

### Playwright best practices

- Use locators (not CSS selectors): `page.getByRole("button", { name: "Submit" })`
- Enable retries for flaky-resilient assertions
- Use `page.waitForResponse` for API-dependent assertions
- Test only critical user flows — unit and component tests cover the rest

---

## 3. Performance

### React Compiler

React Compiler (stable in React 19) automatically memoizes at build time:

- **Remove** `useMemo`, `useCallback`, and `React.memo` from new code
- Keep manual memoization only for identity-critical paths (e.g., callbacks passed to non-React libraries that use reference equality)
- Enable via bundler plugin:

```typescript
// vite.config.ts
import reactCompiler from "babel-plugin-react-compiler";
```

### Code splitting by route

The minimum viable optimization — 40-60% initial bundle reduction:

```tsx
const ResourceDetail = React.lazy(() => import("./routes/resource-detail"));
```

### Bundle analysis

Mandatory for production applications:

```typescript
// vite.config.ts
import { visualizer } from "rollup-plugin-visualizer";

plugins: [visualizer({ open: true, gzipSize: true })]
```

Set size budgets in CI:
```typescript
build: {
  chunkSizeWarningLimit: 250, // KB — fail the build if exceeded
}
```

### Image optimization

- Use `<img loading="lazy">` for below-the-fold images
- Serve WebP/AVIF formats
- Set explicit `width` and `height` to prevent Cumulative Layout Shift (CLS)

### Avoid unnecessary re-renders

- Use selectors with state management: `const theme = useStore((s) => s.theme)`
- Keep state as close to where it's used as possible
- Split large contexts into smaller, focused ones

---

## 4. Security

> For comprehensive browser security (CSRF defense layers, CSP strict policies, cookie hardening,
> session management, OAuth 2.1), see the **Web Security skill** (`/web-security`).

### XSS prevention

React auto-escapes values in JSX curly braces. The risk vectors are:

1. **`dangerouslySetInnerHTML`:** Always sanitize with DOMPurify. Encapsulate in a dedicated `<SafeHTML>` component:
```tsx
import DOMPurify from "dompurify";

function SafeHTML({ html }: { html: string }) {
  return <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} />;
}
```

2. **`href` attributes:** Validate URLs start with `https://` or `/` — `javascript:` URLs bypass escaping.

3. **Server-rendered HTML:** Apply Content Security Policy headers.

### Content Security Policy

Set CSP headers on all responses:
```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;
```

Avoid `'unsafe-inline'` for scripts — use nonces or hashes.

### Dependency scanning

- Run `npm audit` (or `yarn audit`) in CI on every PR
- Use Dependabot or Renovate for automated dependency updates
- Review transitive dependencies for known vulnerabilities

### CSRF protection

For cookie-authenticated, state-changing requests:
- Require an unguessable anti-CSRF token tied to the user/session and validate it on every non-idempotent request (e.g., send via a custom header or request body).
- Use `SameSite=Lax` or `SameSite=Strict` cookies as an additional hardening layer, not as your only CSRF defense.
- You may rely on `SameSite` alone only for requests that are not authenticated via cookies (e.g., pure bearer-token APIs) or are strictly read-only.

See API Design skill section 10 for auth patterns.

---

## 5. Linting & Formatting

### ESLint flat config

Migrate to `eslint.config.js` — the legacy `.eslintrc` format is deprecated in ESLint v9:

```js
import tseslint from "typescript-eslint";

export default tseslint.config(
  tseslint.configs.strictTypeChecked,
  tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
);
```

Type-aware rules catch issues that syntax linting misses: floating promises, unsafe `any` usage, incorrect type assertions.

### Formatting

ESLint is not a formatter — all formatting rules are deprecated. Use:
- **Prettier** with `eslint-config-prettier` to disable conflicting rules
- **Biome** as an alternative (10-25x faster, single binary)

### In CI

Run linters with `--check` (no auto-fix). Auto-fix belongs in local dev and pre-commit hooks.

---

## 6. Module Patterns

### Avoid barrel exports in application code

Barrel files (`index.ts` re-exporting everything) break tree-shaking, hide circular dependencies, and slow down the TypeScript compiler:

```typescript
// WRONG: barrel import pulls in everything
import { Button } from "~/components";

// CORRECT: direct import, tree-shakeable
import { Button } from "~/components/ui/button";
```

Barrel files are acceptable only for public library APIs where you control the export surface.

### Path aliases

Use `~` or `@` aliases to eliminate brittle relative paths:

```typescript
// WRONG
import { Button } from "../../../components/ui/button";

// CORRECT
import { Button } from "~/components/ui/button";
```

### Circular dependency detection

Use `madge` or `eslint-plugin-import` with `no-cycle`. Circular dependencies cause undefined imports at runtime and are extremely hard to debug.

### `verbatimModuleSyntax`

Enable in `tsconfig.json` to ensure TypeScript preserves ES module syntax for bundler tree-shaking. Use `import type` explicitly for type-only imports.

---

## 7. Build Tooling

### Vite configuration

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    chunkSizeWarningLimit: 250,  // KB budget
    sourcemap: true,             // always for production debugging
    target: "es2022",            // modern baseline
  },
});
```

### Bundle analysis

Use `rollup-plugin-visualizer` to identify large dependencies. Set size budgets in CI — fail the build if thresholds are exceeded.

### Dependency management

- Check for duplicate dependencies: `npm ls <package>`
- Prefer packages that support tree-shaking (ESM exports)
- Audit `node_modules` size regularly

### Lightning CSS

Available in Vite as an alternative CSS minifier — faster than esbuild CSS minification.

---

## 8. Pre-Commit Checklist

Before committing TypeScript changes, verify:

```bash
tsc --noEmit                    # Type check (must pass clean)
eslint --max-warnings 0 .       # Lint (zero warnings)
prettier --check .               # Format check
vitest run                       # All unit/component tests pass
```

**Blocking issues — do not commit if any exist:**
- TypeScript errors or `any` types without justification
- ESLint warnings (zero-warning policy)
- Failing tests
- `// @ts-ignore` without `@ts-expect-error` + explanation
- `dangerouslySetInnerHTML` without DOMPurify sanitization
- Snapshot tests (replace with explicit assertions)
- Barrel exports in application code
- `console.log` left in production code
- Unhandled promise rejections in event handlers

---

## 9. Quick Reference

| Task | Command | When |
| --- | --- | --- |
| Type check | `tsc --noEmit` | Before every commit |
| Lint | `eslint .` | Before every commit |
| Format check | `prettier --check .` | Before every commit |
| Run unit tests | `vitest run` | After every change |
| Run E2E tests | `playwright test` | Before PRs |
| Bundle analysis | `npx vite-bundle-visualizer` | When adding dependencies |
| Dep audit | `npm audit` / `yarn audit` | CI, on every PR |
| Update deps | `npx npm-check-updates` | Monthly |
| Check circular deps | `npx madge --circular src/` | Periodically |

---

## Cross-references

- `/react` — React-specific patterns (hooks, state management, data fetching, error boundaries, API client patterns)
- `/ux-design` — Component design, form handling, accessibility
- `/css-responsive` — Tailwind CSS, responsive design patterns
