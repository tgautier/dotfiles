---
name: typescript
description: |
  Industrial-grade TypeScript and React development skill for production web applications.
  Covers: type safety, React 19 patterns, component design, data fetching, form validation,
  testing (Vitest/Playwright), performance, accessibility, error handling, Tailwind CSS,
  security, linting, state management, build tooling, and API client patterns.
  Use when: writing components, hooks, routes, tests, or reviewing frontend code quality.
version: 1.0.0
date: 2026-02-21
user-invocable: true
---

# TypeScript & React Industrial-Grade Development

For API contract conventions (error formats, pagination, status codes, auth patterns), see the API Design skill.

Comprehensive guidance for building production-quality TypeScript and React applications. Based on industry best practices from the React team, Matt Pocock, Kent C. Dodds, TkDodo, and companies running React at scale.

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

## 2. React 19 Patterns

### Actions and `useActionState`

Replace manual `useState` + `try/catch` + `setLoading` with built-in action support:

```tsx
function CreateForm() {
  const [state, submitAction, isPending] = useActionState(
    async (_prev: FormState, formData: FormData) => {
      const result = await createResource(formData);
      if (!result.ok) return { error: result.error };
      return { error: null };
    },
    { error: null },
  );

  return (
    <form action={submitAction}>
      <input name="name" />
      <button disabled={isPending}>Create</button>
      {state.error && <p role="alert">{state.error}</p>}
    </form>
  );
}
```

### `useOptimistic` for perceived performance

Apply optimistic updates on mutations — React reverts automatically on error:

```tsx
const [optimisticItems, addOptimistic] = useOptimistic(
  items,
  (current, newItem: Item) => [...current, newItem],
);
```

### `use()` hook

Reads promises and context inside conditionals and loops (unlike other hooks):

```tsx
function ResourceDetail({ resourcePromise }: { resourcePromise: Promise<Resource> }) {
  const resource = use(resourcePromise); // suspends until resolved
  return <h1>{resource.name}</h1>;
}
```

### Server Components

Move data-fetching and heavy logic to Server Components. Only add `"use client"` to components that need interactivity (event handlers, state, effects). Server Components reduce client bundle by 30-50%.

---

## 3. Component Design

### Composition over prop drilling

```tsx
// WRONG: drilling user through 4 levels
<Layout user={user}><Sidebar user={user}><Nav user={user} /></Sidebar></Layout>

// CORRECT: compose with children, read from context/hooks
<Layout><Sidebar><Nav /></Sidebar></Layout>
```

### Compound components for complex UI

Use React Context to share implicit state between a parent and its children:

```tsx
<Select>
  <Select.Trigger>Choose...</Select.Trigger>
  <Select.Content>
    <Select.Item value="a">Option A</Select.Item>
  </Select.Content>
</Select>
```

Each child is responsible for its own rendering; the parent manages shared state. This is the pattern Radix UI and shadcn/ui use.

### Headless component libraries

Prefer accessible behavior primitives with zero styling opinions:
- **Radix UI** — shadcn/ui foundation
- **React Aria** (Adobe) — comprehensive accessibility primitives
- **ARIAKit** — lightweight alternative

These handle keyboard navigation, focus trapping, ARIA attributes, and screen reader announcements automatically.

### Single responsibility

A component should do one thing. If a component fetches data, transforms it, validates it, and renders a form, break it into:
- A route loader for data fetching
- A custom hook for transformation logic
- A form component for rendering and validation

### Props interface rules

- Use `interface` for component props (supports declaration merging)
- Use explicit prop types, never `React.FC` (it adds implicit `children`)
- Destructure props in the function signature
- Use `ComponentPropsWithoutRef<"button">` when extending native elements

```tsx
interface ButtonProps extends ComponentPropsWithoutRef<"button"> {
  variant?: "primary" | "secondary";
  isLoading?: boolean;
}

function Button({ variant = "primary", isLoading, children, ...rest }: ButtonProps) {
  return <button {...rest}>{isLoading ? <Spinner /> : children}</button>;
}
```

---

## 4. Data Fetching

### Route loaders as the primary mechanism

Loaders run before render, eliminating loading spinners on navigation:

```tsx
export async function loader({ params }: LoaderFunctionArgs) {
  const resource = await api.getResource(params.id);
  return { resource };
}

export default function ResourcePage() {
  const { resource } = useLoaderData<typeof loader>();
  return <ResourceDetail resource={resource} />;
}
```

### TanStack Query for cache + background refetch

Layer TanStack Query on top of loaders for stale-while-revalidate, retry logic, and cache management:

```tsx
// Query key factory
const resourceKeys = {
  all: ["resources"] as const,
  list: (filters: Filters) => [...resourceKeys.all, "list", filters] as const,
  detail: (id: string) => [...resourceKeys.all, "detail", id] as const,
};

// In loader: prefetch and seed the cache
export async function loader({ params }: LoaderFunctionArgs) {
  await queryClient.ensureQueryData(resourceQueryOptions(params.id));
  return null;
}

// In component: read from cache + subscribe to updates
function ResourceDetail() {
  const { data } = useSuspenseQuery(resourceQueryOptions(useParams().id!));
  return <h1>{data.name}</h1>;
}
```

### Key rules

- Set a global `staleTime` (e.g., 60 seconds) — the default of 0 causes excessive refetches
- **Never copy server data into `useState`** — let TanStack Query own it
- Use `useSuspenseQuery` with Suspense boundaries instead of checking `isLoading`/`isError`
- Wrap route segments in `Suspense` + `ErrorBoundary` pairs:

```tsx
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <Suspense fallback={<Skeleton />}>
    <ResourceList />
  </Suspense>
</ErrorBoundary>
```

---

## 5. Form Handling & Validation

### Zod as the single source of truth

Define validation schemas once, infer types from them:

```typescript
import { z } from "zod";

const createResourceSchema = z.object({
  name: z.string().min(1, "Required").max(255),
  email: z.string().email("Invalid email"),
  quantity: z.number().int().positive("Must be positive"),
});

type CreateResource = z.infer<typeof createResourceSchema>;
```

### React Hook Form + Zod

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

function CreateResourceForm() {
  const form = useForm<CreateResource>({
    resolver: zodResolver(createResourceSchema),
    defaultValues: { name: "", email: "", quantity: 1 },
  });

  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      {/* fields */}
    </form>
  );
}
```

### Cross-field validation

Use `refine` and `superRefine` for rules that span multiple fields:

```typescript
const dateRangeSchema = z.object({
  startDate: z.date(),
  endDate: z.date(),
}).refine(
  (data) => data.endDate > data.startDate,
  { message: "End date must be after start date", path: ["endDate"] },
);
```

### Server-side validation is non-negotiable

Client-side validation is a UX convenience. The API must always validate independently. Never trust client-submitted data.

---

## 6. Testing

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

## 7. Performance

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

## 8. Accessibility

### Semantic HTML first, ARIA second

If a native HTML element provides the behavior, use it:

```tsx
// WRONG
<div role="button" onClick={handleClick} tabIndex={0}>Submit</div>

// CORRECT
<button onClick={handleClick}>Submit</button>
```

### Focus management

- **Modals:** Trap focus inside, return focus to trigger on close
- **Route changes:** Move focus to the main content heading
- **Dynamic content:** Use `aria-live` regions for toast notifications
- **Error messages:** Associate with inputs via `aria-describedby`

```tsx
<input aria-describedby="name-error" />
{error && <p id="name-error" role="alert">{error}</p>}
```

### Keyboard navigation

- All interactive elements reachable via Tab
- Custom widgets implement arrow key navigation per WAI-ARIA patterns
- Visible focus indicators — never remove `:focus-visible` outlines

### Testing accessibility

- Use `axe-core` in Vitest/Playwright for automated WCAG checks
- Test with VoiceOver/NVDA for real screen reader behavior
- Color contrast: minimum 4.5:1 for body text, 3:1 for large text

---

## 9. Error Handling

### Layered error boundaries

1. **Root boundary:** Catches catastrophic errors, shows a full-page error screen
2. **Route boundary:** Catches loader/action errors per route (framework-provided `errorElement`)
3. **Feature boundary:** Wraps individual widgets so a single failure doesn't take down the page

```tsx
import { ErrorBoundary } from "react-error-boundary";

<ErrorBoundary
  FallbackComponent={ErrorFallback}
  onReset={() => queryClient.invalidateQueries()}
  resetKeys={[resourceId]}
>
  <ResourceDetail />
</ErrorBoundary>
```

### What error boundaries do NOT catch

- Errors in event handlers (use try/catch)
- Async errors outside React rendering (handle in promise chains or TanStack Query)
- Errors in the error boundary itself

### Retry pattern

Offer a "Try again" button that calls `resetErrorBoundary()`. For API calls, TanStack Query provides built-in exponential backoff via the `retry` option.

### Toast notifications

Use for non-blocking errors (e.g., "Failed to save, retrying..."). Libraries: `sonner`, `react-hot-toast`. Never use toasts as the sole error indicator for form validation.

---

## 10. Tailwind CSS

### Avoid `@apply`

Use React component abstractions instead:

```tsx
// WRONG: @apply in CSS
.btn-primary { @apply rounded bg-blue-600 text-white px-4 py-2; }

// CORRECT: React component
function Button({ children, ...props }: ButtonProps) {
  return <button className="rounded bg-blue-600 text-white px-4 py-2" {...props}>{children}</button>;
}
```

Reserve `@apply` only for cases where component extraction is impractical (e.g., styling CMS markdown).

### CVA for component variants

Use `class-variance-authority` for type-safe variant management:

```tsx
import { cva, type VariantProps } from "class-variance-authority";

const button = cva("rounded font-medium transition-colors", {
  variants: {
    intent: {
      primary: "bg-blue-600 text-white hover:bg-blue-700",
      secondary: "bg-gray-200 text-gray-900 hover:bg-gray-300",
      danger: "bg-red-600 text-white hover:bg-red-700",
    },
    size: {
      sm: "px-3 py-1.5 text-sm",
      md: "px-4 py-2 text-base",
      lg: "px-6 py-3 text-lg",
    },
  },
  defaultVariants: { intent: "primary", size: "md" },
});

type ButtonProps = VariantProps<typeof button> & ComponentPropsWithoutRef<"button">;
```

### Always use `tailwind-merge`

Wrap CVA with `twMerge` to resolve conflicting utilities when consumers override classes:

```typescript
import { twMerge } from "tailwind-merge";
import { clsx, type ClassValue } from "clsx";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### Consistent class ordering

Use the Prettier plugin (`prettier-plugin-tailwindcss`) for automatic class sorting.

---

## 11. Security

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

## 12. Linting & Formatting

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

## 13. Module Patterns

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

## 14. State Management

### Decision framework

Choose the right tool for each type of state:

| State type | Tool | Example |
|---|---|---|
| Server data | TanStack Query / route loaders | Fetched resources, lists |
| URL state | `useSearchParams` | Filters, pagination, search |
| Form state | React Hook Form / `useActionState` | Input values, validation |
| Global UI state | Zustand | Theme, sidebar, preferences |
| Fine-grained reactivity | Jotai | Dependent atoms, derived state |
| Complex workflows | XState | Multi-step forms, state machines |

### Key rules

- **Never copy server data into `useState`** — let TanStack Query or loaders own it
- **URL state is the most underused location** — filters, sort order, and pagination belong in the URL
- Use selectors to prevent unnecessary re-renders:

```typescript
// WRONG: subscribes to entire store
const store = useStore();

// CORRECT: subscribes only to theme
const theme = useStore((s) => s.theme);
```

### When Redux is appropriate

Only when: you need time-travel debugging, have very complex state interactions, or have a large team that benefits from strict conventions. For most applications, Zustand or Jotai are simpler and sufficient.

---

## 15. Build Tooling

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

## 16. API Client Patterns

### Generated clients from OpenAPI

Use `@hey-api/openapi-ts` (actively maintained) over `openapi-typescript-codegen` (unmaintained):

- Generates type-safe fetch functions from OpenAPI spec
- Supports Zod schema generation for runtime validation
- TanStack Query plugin for automatic query hooks

### Request cancellation

```typescript
const controller = new AbortController();
const response = await fetch("/api/resources", { signal: controller.signal });

// On unmount or navigation:
controller.abort();
```

AbortController instances are single-use — create a new one per request. Handle `AbortError` separately from network errors.

### Type-safe error mapping

Map API error responses to discriminated unions:

```typescript
type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: { code: "validation"; fields: Record<string, string> } }
  | { ok: false; error: { code: "not_found" } }
  | { ok: false; error: { code: "server_error" } };
```

### Retry with exponential backoff

Retry only on 429 and 503 (see API Design skill section 15). Respect `Retry-After` headers. TanStack Query's default `retry` option retries all failures — customize it to only retry 429/503 and honor `Retry-After`.

---

## 17. Pre-Commit Checklist

Before committing frontend changes, verify:

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
- Missing error boundaries on route segments
- Snapshot tests (replace with explicit assertions)
- Barrel exports in application code
- `console.log` left in production code
- Inline styles when Tailwind utilities exist
- Missing `key` prop on list items
- `useEffect` for data fetching (use loaders or TanStack Query)
- Manual `useMemo`/`useCallback` with React Compiler enabled
- Unhandled promise rejections in event handlers

---

## Quick Reference

| Task | Command | When |
|---|---|---|
| Type check | `tsc --noEmit` | Before every commit |
| Lint | `eslint .` | Before every commit |
| Format check | `prettier --check .` | Before every commit |
| Run unit tests | `vitest run` | After every change |
| Run E2E tests | `playwright test` | Before PRs |
| Bundle analysis | `npx vite-bundle-visualizer` | When adding dependencies |
| Dep audit | `npm audit` / `yarn audit` | CI, on every PR |
| Update deps | `npx npm-check-updates` | Monthly |
| Check circular deps | `npx madge --circular src/` | Periodically |
