---
name: react
description: |
  React 19 development patterns for production web applications.
  Covers: React 19 features, data fetching, error handling, state management,
  and API client integration patterns.
  Use when: writing React components, hooks, route loaders/actions, managing state,
  or integrating with API clients.
version: 1.0.0
date: 2026-02-23
user-invocable: true
---

# React Development

React 19 patterns for production applications. Covers the framework layer — hooks, state, data fetching, error handling, and API client integration.

For TypeScript strictness, testing, and build tooling, see `/typescript`. For component design, form UX, and accessibility, see `/ux-design`. For CSS and responsive patterns, see `/css-responsive`.

---

## 1. React 19 Patterns

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

## 2. Data Fetching

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
// Query key factory — consistent cache keys
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

## 3. Error Handling

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

## 4. State Management

### Decision framework

Choose the right tool for each type of state:

| State type | Tool | Example |
| --- | --- | --- |
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

## 5. API Client Patterns

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

Retry only on 429 and 503. Respect `Retry-After` headers. TanStack Query's default `retry` option retries all failures — customize it:

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (failureCount >= 3) return false;
        const status = error instanceof ApiError ? error.status : 0;
        return status === 429 || status === 503;
      },
    },
  },
});
```

---

## 6. Hooks & Composition

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

function useAssets() {
  const { filters } = useAssetFilters();
  return useSuspenseQuery(assetQueryOptions(filters));
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

Wrap hooks that need providers (Router, Query Client) in a wrapper:

```tsx
const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

const { result } = renderHook(() => useAssets(), { wrapper });
```

---

## 7. Anti-Patterns

| Anti-pattern | Problem | Fix |
| --- | --- | --- |
| Copy server data into `useState` | Stale data, double source of truth | Let TanStack Query / loaders own it |
| `useEffect` for data fetching | Waterfalls, race conditions, no caching | Route loaders or TanStack Query |
| Manual `useMemo`/`useCallback` everywhere | Noise, premature optimization | React Compiler handles memoization |
| Prop drilling through 4+ levels | Fragile, hard to refactor | Context, composition, or state library |
| `useEffect` for derived state | Extra render cycle, stale values | Compute during render with `useMemo` |
| One giant Context for all state | Every consumer re-renders on any change | Split into focused contexts or use Zustand |
| `useLayoutEffect` without SSR guard | Server warning, runs as `useEffect` on server | `useEffect` or `useIsomorphicLayoutEffect` |
| Catching errors in event handlers with boundaries | Boundaries only catch render/lifecycle errors | try/catch in the handler |
| Fetching in `useEffect` with no cleanup | Race conditions, memory leaks | AbortController or TanStack Query |
| Storing form values in global state | Unnecessary complexity | React Hook Form or `useActionState` |

---

## Cross-references

- `/typescript` — TypeScript strictness, testing (Vitest/Playwright), modules, build tooling
- `/ux-design` — component API design, form UX, accessibility
- `/css-responsive` — responsive rendering, Tailwind CSS patterns
