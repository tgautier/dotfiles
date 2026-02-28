---
name: react
description: |
  React 19 development patterns for production web applications.
  Covers: React 19 features, data fetching, mutations, error handling, state management,
  and API client integration patterns.
  Use when: writing React components, hooks, route loaders/actions, managing state,
  or integrating with API clients.
version: 2.0.0
date: 2026-02-28
user-invocable: true
---

# React Development

Server-first React patterns for production applications using React Router v7. Covers the framework layer — loaders, actions, mutations, state, error handling, and API client integration. All patterns assume server-side rendering with route loaders and actions — not SPA-era client-side data fetching.

For TypeScript strictness, testing, and build tooling, see `/typescript`. For component design, form UX, and accessibility, see `/ux-design`. For CSS and responsive patterns, see `/css-responsive`.

---

## 1. React 19 Patterns

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

---

## 2. Data Fetching

### Route loaders are the cache

Loaders run on the server before render. They are the single source of server data — no SPA-era client-side caching layer is needed on top.

```tsx
export async function loader({ request, params }: LoaderFunctionArgs) {
  const resource = await api.getResource(params.id);
  return { resource };
}

export default function ResourcePage() {
  const { resource } = useLoaderData<typeof loader>();
  return <ResourceDetail resource={resource} />;
}
```

### Key rules

- **Loaders are the cache** — data is available when the page renders, no loading spinners for initial data
- **Never copy server data into `useState`** — `useLoaderData` owns it
- Loaders auto-rerun after successful actions — no manual cache invalidation
- Use `parsePaginationParams()` or similar helpers for URL-driven data (filters, sort, pagination)
- Throw `Response` on error to trigger the route's `ErrorBoundary`
- Return plain objects for success — access via `useLoaderData<typeof loader>()`

---

## 3. Mutations

### `<Form>` for all mutations

All mutations flow through route actions via `<Form method="post">` — never `onClick` + `fetch()`:

```tsx
<Form method="post">
  <input type="hidden" name="_intent" value="create" />
  <input name="name" defaultValue="" required />
  <button type="submit">Create</button>
</Form>
```

`Form` is from `react-router`, not HTML — it handles serialization and triggers loader revalidation after the action completes.

### Intent pattern

Multi-action routes use a hidden `_intent` field to discriminate:

```typescript
export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  const intent = String(formData.get("_intent") ?? "create");

  if (intent === "delete") {
    const id = String(formData.get("id") ?? "");
    try {
      await api.deleteResource(id);
      return Response.json({ success: true, intent: "delete" });
    } catch (error) {
      const status = extractErrorStatus(error);
      return Response.json({ error: "Failed to delete", intent: "delete" }, { status });
    }
  }
  // handle create, update...
}
```

### Action return shape

```typescript
type ActionResult = { error?: string; success?: boolean; intent?: string };
```

- Always include `intent` so the UI can scope error display to the correct form
- Use `Response.json()` for both success and error — never throw for expected errors
- Access via `useActionData<typeof action>()` — validate with a type guard since it returns `unknown`

### `useFetcher` for non-navigation mutations

Use `useFetcher` when the mutation should not trigger a full-page navigation:

```tsx
const fetcher = useFetcher();
<fetcher.Form method="post">
  <input type="hidden" name="_intent" value="toggle" />
  <button type="submit">Toggle</button>
</fetcher.Form>
```

Use cases: inline toggles, background saves, actions in list items that should not scroll to top.

### Submission state

```tsx
const navigation = useNavigation();
const isSubmitting = navigation.state === "submitting";

<button type="submit" disabled={isSubmitting}>
  {isSubmitting ? "Saving..." : "Save"}
</button>
```

For fetcher-driven mutations, use `fetcher.state` instead.

### Form inputs

- Use `defaultValue` for form fields (uncontrolled inputs) — the browser manages form state
- Never use `useState` + `value` for fields that will be submitted via `<Form>`
- Extract FormData parsing into named functions to keep actions focused

---

## 4. Error Handling

### Layered error boundaries

1. **Root boundary:** Catches catastrophic errors, shows a full-page error screen
2. **Route boundary:** Catches loader/action errors per route (framework-provided `ErrorBoundary` export)
3. **Feature boundary:** Wraps individual widgets so a single failure doesn't take down the page

```tsx
import { ErrorBoundary } from "react-error-boundary";

<ErrorBoundary
  FallbackComponent={ErrorFallback}
  onReset={() => window.location.reload()}
  resetKeys={[resourceId]}
>
  <ResourceDetail />
</ErrorBoundary>
```

### What error boundaries do NOT catch

- Errors in event handlers (use try/catch)
- Async errors outside React rendering (handle in promise chains)
- Errors in the error boundary itself

### Retry pattern

Offer a "Try again" button that calls `resetErrorBoundary()`. For route-level errors, a page reload retriggers the loader.

### Toast notifications

Use for non-blocking errors (e.g., "Failed to save, retrying..."). Libraries: `sonner`, `react-hot-toast`. Never use toasts as the sole error indicator for form validation.

---

## 5. State Management

### Decision framework

| State type | Tool | Example |
| --- | --- | --- |
| Server data | `useLoaderData` / `useActionData` | Fetched resources, lists, action results |
| URL state | `useSearchParams` | Filters, pagination, search, sort |
| Form data | Uncontrolled DOM inputs (`defaultValue`) | Input values in `<Form>` |
| Transient UI | `useState` | Sheet open/close, delete confirm, mount guard |

### Key rules

- **No client-side data layer** — loaders and actions own all server data. SPA-era caching libraries (TanStack Query, SWR, Zustand for server state) are unnecessary and fight the framework
- **Never copy server data into `useState`** — `useLoaderData` is the source of truth
- **URL state is the most underused location** — filters, sort order, and pagination belong in the URL via `useSearchParams`
- `useState` is for transient UI only: modal open/close, delete confirmation toggle, client-only-lib mount guards
- Derive state during render with `useMemo` — never use `useEffect` to sync derived values

---

## 6. API Client Patterns

### Generated clients from OpenAPI

Use generated clients (e.g., `@hey-api/openapi-ts`) for type-safe API calls:

- Generates type-safe functions from OpenAPI spec
- Called in loaders and actions only — never in components
- Error handling: actions catch errors and return `Response.json({ error }, { status })`

### Where to call the API client

```typescript
// CORRECT — in a loader (server-side)
export async function loader({ request }: LoaderFunctionArgs) {
  const data = await apiClient.getResources();
  return { data };
}

// CORRECT — in an action (server-side)
export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  await apiClient.createResource(parseFormData(formData));
  return Response.json({ success: true });
}
```

Never import or call the API client directly in React components. Components read data exclusively from `useLoaderData` and `useActionData`.

---

## 7. Hooks & Composition

### When to extract a custom hook

Extract a hook when:
- Logic is shared between 2+ components
- A component has complex state management that obscures its rendering intent
- You need to test the logic independently from the UI

Don't extract when:
- The logic is used in only one component and is simple
- The "hook" would just be a thin wrapper around a single `useState`

### Naming conventions

- `use` prefix is mandatory (React enforces this)
- Name describes what the hook provides, not how: `useAssets()` not `useFetchAssets()`
- Return an object for 3+ values, a tuple for 1-2: `const [value, setValue] = useToggle()`

### Hook composition

Build complex hooks from simpler ones:

```tsx
function useAssetFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => parseFilters(searchParams), [searchParams]);
  const setFilter = useCallback((key: string, value: string) => {
    setSearchParams(prev => { prev.set(key, value); return prev; });
  }, [setSearchParams]);
  return { filters, setFilter };
}
```

### Hook testing

Test hooks with `renderHook` from Testing Library:

```tsx
import { renderHook, act } from "@testing-library/react";

test("useToggle toggles value", () => {
  const { result } = renderHook(() => useToggle(false));
  expect(result.current[0]).toBe(false);
  act(() => result.current[1]());
  expect(result.current[0]).toBe(true);
});
```

Wrap hooks that need providers (Router) in a wrapper:

```tsx
const wrapper = ({ children }: { children: ReactNode }) => (
  <MemoryRouter>{children}</MemoryRouter>
);

const { result } = renderHook(() => useAssetFilters(), { wrapper });
```

---

## 8. Anti-Patterns

### SPA-era patterns (never use with React Router v7)

These patterns belong to the SPA era where the client managed its own data. In a server-first architecture with loaders and actions, they add complexity, fight the framework, and break progressive enhancement.

| SPA anti-pattern | Problem | Server-first alternative |
| --- | --- | --- |
| `useEffect` for data fetching | Waterfalls, race conditions, no SSR | Route loaders |
| `onClick` + `fetch` for mutations | No progressive enhancement, no revalidation | `<Form method="post">` |
| Client-side `fetch` in components | Bypasses loader caching, invisible to framework | Move to loader or action |
| TanStack Query / SWR for route data | Duplicate cache layer, fights revalidation | `useLoaderData` is the cache |
| `useState` for form fields | Extra state, out of sync with DOM | `defaultValue` + uncontrolled inputs |
| `useReducer` for form state | Over-engineering what the DOM already does | `<Form>` + `FormData` |
| Client-side form validation libraries | Duplicates server logic, false sense of security | HTML5 attributes + server validation in action |
| `useEffect` to sync action results | Extra render cycle, stale values | `useActionData()` directly |
| Zustand/Redux for server data | Wrong tool — these are for client-only state | Loaders own server data |
| Throwing from actions for user errors | Triggers ErrorBoundary, loses form state | `Response.json({ error })` |

### General React anti-patterns

| Anti-pattern | Problem | Fix |
| --- | --- | --- |
| Prop drilling through 4+ levels | Fragile, hard to refactor | Context or composition |
| `useLayoutEffect` without SSR guard | Server warning, runs as `useEffect` on server | `useEffect` or `useIsomorphicLayoutEffect` |
| `useEffect` for derived state | Extra render cycle, stale values | Compute during render with `useMemo` |
| Manual `useMemo`/`useCallback` everywhere | Noise, premature optimization | React Compiler handles memoization |

---

## Cross-references

- `/typescript` — TypeScript strictness, route type safety, testing (Vitest/Playwright), modules, build tooling
- `/ux-design` — component API design, server-validated form UX, accessibility
- `/css-responsive` — responsive rendering, Tailwind CSS patterns
