---
name: react-router
description: |
  React Router v7 framework patterns for data loading, mutations, error handling, and routing.
  Covers: loaders, actions, data revalidation, Form patterns, route error boundaries,
  type-safe loader/action data, and progressive enhancement.
  Use when: building server-first applications, handling route-level data fetching,
  processing form mutations, managing URL state, or implementing error handling.
version: 1.1.0
date: 2026-03-25
user-invocable: true
---

# React Router v7 Framework Patterns

Server-first data and mutation patterns for React Router v7. React Router v7 combines client-side routing with server-side data loading and mutation handling — eliminating the need for SPA-era client-side data layers.

For general React patterns (hooks, state, composition), see `/react`. For TypeScript language patterns and build tooling, see `/typescript`. For component design and accessibility, see `/ux-design`.

---

## 1. Route Loaders & Type Safety

### Loaders are the data cache

Loaders run on the server before render. They are the single source of server data — no SPA-era client-side caching layer is needed on top.

```tsx
export async function loader({ request, params }: LoaderFunctionArgs) {
  const id = params.id;
  if (!id) throw new Response("Not Found", { status: 404 });
  const resource = await api.getResource(id);
  return { resource };
}

export default function ResourcePage() {
  const { resource } = useLoaderData<typeof loader>();
  return <ResourceDetail resource={resource} />;
}
```

### Loader type safety

Type loaders with framework-provided generics. `useLoaderData<typeof loader>()` infers the return type automatically:

```typescript
// Typed loader — useLoaderData infers the return type
export async function loader({ request, params }: LoaderFunctionArgs) {
  const resources = await apiClient.getResources();
  return { resources }; // useLoaderData<typeof loader> infers { resources: Resource[] }
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

## 2. Route Actions & Mutations

### Form for all mutations

All mutations flow through route actions via `<Form method="post">` — never `onClick` + `fetch()`:

```tsx
<Form method="post">
  <input type="hidden" name="_intent" value="create" />
  <input name="name" defaultValue="" required />
  <button type="submit">Create</button>
</Form>
```

`Form` is from `react-router`, not HTML — it handles serialization and triggers loader revalidation after the action completes.

### Intent pattern for multi-action routes

Multi-action routes use a hidden `_intent` field to discriminate:

```typescript
export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  const intent = String(formData.get("_intent") ?? "create");

  if (intent === "delete") {
    const id = String(formData.get("id") ?? "");
    if (!id)
      return Response.json(
        { error: "Missing id", intent: "delete" },
        { status: 400 },
      );
    try {
      await api.deleteResource(id);
      return Response.json({ success: true, intent: "delete" });
    } catch (error) {
      const status = extractErrorStatus(error);
      return Response.json(
        { error: "Failed to delete", intent: "delete" },
        { status },
      );
    }
  }
  // handle create, update...
}
```

### Action return shape & type safety

```typescript
type ActionResult = { intent: string; error?: string; success?: boolean };
```

- Always include `intent` so the UI can scope error display to the correct form
- Use `Response.json()` for both success and error — never throw for expected errors
- Access via `useActionData<typeof action>()` — validate with a type guard since it returns `unknown`

```typescript
function isActionResult(data: unknown): data is ActionResult {
  if (typeof data !== "object" || data === null) {
    return false;
  }
  const d = data as Record<string, unknown>;
  if (typeof d.intent !== "string") {
    return false;
  }
  if ("error" in d && typeof d.error !== "string") {
    return false;
  }
  if ("success" in d && typeof d.success !== "boolean") {
    return false;
  }
  return true;
}
```

### Form inputs

- Use `defaultValue` for form fields (uncontrolled inputs) — the browser manages form state
- Never use `useState` + `value` for fields that will be submitted via `<Form>`
- Extract FormData parsing into named functions to keep actions focused

```typescript
function parseFormData(formData: FormData) {
  return {
    name: String(formData.get("name") ?? ""),
    value: String(formData.get("value") ?? ""),
    kind: String(formData.get("kind") ?? ""),
  };
}
```

### Submission state

```tsx
const navigation = useNavigation();
const isSubmitting = navigation.state === "submitting";

<button type="submit" disabled={isSubmitting}>
  {isSubmitting ? "Saving..." : "Save"}
</button>;
```

For fetcher-driven mutations, use `fetcher.state` instead.

---

## 3. Non-Navigation Mutations with `useFetcher`

### When to use fetcher

Use `useFetcher` when the mutation should not trigger a full-page navigation:

```tsx
const fetcher = useFetcher();
<fetcher.Form method="post">
  <input type="hidden" name="_intent" value="toggle" />
  <button type="submit">Toggle</button>
</fetcher.Form>;
```

Use cases: inline toggles, background saves, actions in list items that should not scroll to top.

### Optimistic UI via `fetcher.formData`

Derive optimistic state from `fetcher.formData` — the pending submission data:

```tsx
const fetcher = useFetcher();

return (
  <>
    <ul>
      {items.map((item) => (
        <li key={item.id}>{item.name}</li>
      ))}
      {fetcher.formData && (
        <li className="opacity-50">
          {String(fetcher.formData.get("name") ?? "")}
        </li>
      )}
    </ul>
    <fetcher.Form method="post">
      <input type="hidden" name="_intent" value="create" />
      <input name="name" required />
      <button type="submit">Add</button>
    </fetcher.Form>
  </>
);
```

`fetcher.formData` is non-null while the submission is in flight. When the action completes, loaders revalidate, the real item (with its server-assigned ID) appears in `items`, and `fetcher.formData` resets to null — the optimistic element disappears automatically. For multiple concurrent submissions, use `useFetchers()` to render all pending items.

---

## 4. Route Error Boundaries

### Layered error boundaries

1. **Root boundary:** Catches catastrophic errors, shows a full-page error screen
2. **Route boundary:** Catches loader/action errors per route (framework-provided `ErrorBoundary` export)
3. **Feature boundary:** Wraps individual widgets so a single failure doesn't take down the page

```tsx
import { ErrorBoundary } from "react-error-boundary";

<ErrorBoundary
  FallbackComponent={ErrorFallback}
  onReset={() => {
    /* revalidate loaders or navigate to same route */
  }}
  resetKeys={[resourceId]}
>
  <ResourceDetail />
</ErrorBoundary>;
```

### Route-level error handling

React Router automatically catches loader and action errors:

```tsx
export function ErrorBoundary() {
  const error = useRouteError();

  if (isRouteErrorResponse(error)) {
    return (
      <div>
        <h1>{error.status}</h1>
        <p>{error.statusText}</p>
      </div>
    );
  }

  return <h1>Unexpected Error</h1>;
}
```

### What error boundaries do NOT catch

- Errors in event handlers (use try/catch)
- Async errors outside React rendering (handle in promise chains)
- Errors in the error boundary itself

### Retry pattern

Offer a "Try again" button that calls `resetErrorBoundary()`. For route-level errors, a page reload retriggers the loader.

---

## 5. URL State Management

### useSearchParams for filters, sort, pagination

URL state is the most underused state location — filters, sort order, and pagination belong in the URL:

```tsx
const [searchParams, setSearchParams] = useSearchParams();
const sort = searchParams.get("sort") ?? "name";
const page = Number(searchParams.get("page") ?? "1");

const setSort = (value: string) => {
  setSearchParams((prev) => {
    prev.set("sort", value);
    prev.delete("page"); // reset to page 1
    return prev;
  });
};
```

**Benefits:**
- URLs are bookmarkable and shareable
- Browser back/forward work automatically
- State persists across page reloads
- No state synchronization code needed

### URL-driven loader data

Loaders receive the URL as part of the request and can parse it for data:

```typescript
export async function loader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url);
  const page = Number(url.searchParams.get("page") ?? "1");
  const sort = url.searchParams.get("sort") ?? "name";

  const resources = await api.getResources({ page, sort });
  return { resources, page, sort };
}
```

---

## 6. API Client Patterns in Loaders & Actions

### Generated clients from OpenAPI

Use generated clients (e.g., `@hey-api/openapi-ts`) for type-safe API calls in loaders and actions only:

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

### Where NOT to call the API client

Never import or call the API client directly in React components. Components read data exclusively from `useLoaderData` and `useActionData`.

```typescript
// WRONG — in a component
function ResourceList() {
  const [data, setData] = useState(null);
  useEffect(() => {
    apiClient.getResources().then(setData); // ❌ waterfalls, race conditions
  }, []);
}
```

---

## 7. Data Revalidation After Actions

### Automatic loader revalidation

When an action completes successfully, React Router automatically reruns all loaders on the page to keep UI in sync:

```typescript
export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  await api.deleteResource(String(formData.get("id")));
  // Loaders rerun automatically — no manual cache invalidation needed
  return Response.json({ success: true });
}
```

### Revalidator for cross-route updates

For actions that affect loaders on other routes, use `revalidator`:

```typescript
import { useRevalidator } from "react-router";

function SidePanel() {
  const revalidator = useRevalidator();
  return (
    <button
      onClick={() => {
        // do something
        revalidator.revalidate();
      }}
    >
      Sync
    </button>
  );
}
```

---

## 8. Anti-Patterns: SPA-Era Data Patterns

Never use these patterns in React Router v7 — they fight the framework:

| SPA anti-pattern                      | Problem                                          | React Router solution                  |
| ------------------------------------- | ------------------------------------------------ | -------------------------------------- |
| `useEffect` for data fetching         | Waterfalls, race conditions, no SSR              | Route loaders                          |
| `onClick` + `fetch` for mutations     | No progressive enhancement, no revalidation      | `<Form method="post">`                 |
| Client-side `fetch` in components     | Bypasses loader caching, invisible to framework  | Move to loader or action               |
| TanStack Query / SWR for route data   | Duplicate cache layer, fights revalidation       | `useLoaderData` is the cache           |
| `useState` for form fields            | Extra state, out of sync with DOM                | `defaultValue` + uncontrolled inputs   |
| `useReducer` for form state           | Over-engineering what the DOM already does       | `<Form>` + `FormData`                  |
| Client-side form validation libraries | Duplicates server logic, false sense of security | HTML5 attributes + server validation   |
| Zustand/Redux for server data         | Wrong tool — these are for client-only state     | Loaders own server data                |
| Throwing from actions for user errors | Triggers ErrorBoundary, loses form state         | `Response.json({ error })`             |

---

## 9. SSR Entry Points

### React Router v7 entry point lifecycle

React Router v7 SSR uses three coordinating files:

- **`entry.server.tsx`** — called once per HTTP request. Receives the request, renders `<ServerRouter>` to a stream. This is where per-request providers wrap the render tree. Runs concurrently for parallel requests
- **`entry.client.tsx`** — runs once in the browser. Hydrates the server-rendered HTML by calling `hydrateRoot` with `<HydratedRouter>`. Must mirror the server's provider tree exactly
- **`root.tsx`** — the root route. Its loader provides shared data (locale, theme, config) that both entry points consume. The `Layout` export renders `<html>`, `<head>`, `<body>`

### Provider symmetry pattern

Every provider wrapping `<ServerRouter>` in `entry.server.tsx` must also wrap `<HydratedRouter>` in `entry.client.tsx`, in the same order. Violations cause hydration mismatches or missing context.

```tsx
// entry.server.tsx
<ProviderA value={serverValueA}>
  <ProviderB value={serverValueB}>
    <ServerRouter context={reactRouterContext} url={request.url} />
  </ProviderB>
</ProviderA>

// entry.client.tsx — same shape
<ProviderA value={clientValueA}>
  <ProviderB value={clientValueB}>
    <HydratedRouter />
  </ProviderB>
</ProviderA>
```

### Third-party SSR integration recipe

When integrating a library that needs per-request state in SSR (i18n, feature flags, A/B testing, styled-components):

1. **Create a per-request instance** in `entry.server.tsx` — never reuse a module singleton
2. **Wrap with the library's React provider** around `<ServerRouter>`
3. **Mirror in `entry.client.tsx`** — create or initialize the client instance, wrap `<HydratedRouter>` with the same provider
4. **Bridge data via `root.tsx`** — if the client needs server-determined values (e.g., detected locale), pass them through the root loader and serialize into the HTML (e.g., `<html lang={locale}>`)

**The singleton trap:** many libraries default to a global instance (`i18next`, feature flag clients). In SSR, concurrent requests share the Node.js process. Writing to a global then awaiting before reading it back is a race condition. Always use a factory function or `createInstance()` pattern.

### i18next reference implementation

```tsx
// entry.server.tsx — per-request instance
const locale = getLocale(request);
const i18n = await initI18nForRequest(locale);
// ...
<I18nextProvider i18n={i18n}>
  <ServerRouter context={reactRouterContext} url={request.url} />
</I18nextProvider>
```

---

## 10. State Management in React Router

### Decision framework: where does each kind of state live?

React Router v7 has distinct locations for different state types. Choosing the wrong location couples components unnecessarily or creates synchronization bugs.

| State type | Location | Hook | Lifetime | Synchronize with | Example |
| --- | --- | --- | --- | --- | --- |
| **Server data** | Loader return | `useLoaderData<typeof loader>()` | One request cycle | Automatic after actions | API responses, database queries |
| **Action results** | Action return | `useActionData<typeof action>()` | Until next action | Manual, typically short-lived | Form errors, success messages |
| **URL state** | `?key=value` in URL | `useSearchParams()` | Until user navigates or clears | Browser history, bookmarks | Filters, pagination, sort order, tab state |
| **Transient UI state** | `useState()` in component | `useState()` | Component lifetime | Manual if needed | Collapsed/expanded sections, modal open/close, focus |
| **Form input data** | DOM (uncontrolled) | `FormData` in action | Form submission | Server via action | Text inputs, select values, checkboxes |
| **Client-only state** | Client context or Zustand | `useContext()` or selector | Browser session | Manual | Theme preference, logged-in user, notifications |

### Anti-pattern: mixing state locations

Never store server data in `useState` — it creates a synchronization problem:

```tsx
// ❌ WRONG — creates a sync bug
function ResourceList() {
  const loader = useLoaderData<typeof loader>();
  const [items, setItems] = useState(loader.items); // why copy?
  // Now you have two sources of truth
  // Updating one doesn't update the other
}

// ✅ RIGHT — server data lives in loader
function ResourceList() {
  const { items } = useLoaderData<typeof loader>();
  return items.map(item => <Item key={item.id} item={item} />);
}
```

Never use Zustand or Redux for server data — loaders are the cache:

```tsx
// ❌ WRONG
export async function loader() {
  const items = await api.getItems();
  store.setItems(items); // don't do this
  return { items };
}

// ✅ RIGHT — loader data is the cache
export async function loader() {
  const items = await api.getItems();
  return { items }; // access via useLoaderData
}
```

### Combining multiple state sources

Components often need data from multiple locations. Combine them cleanly:

```tsx
export default function ResourcePage() {
  // Server data
  const { resources } = useLoaderData<typeof loader>();

  // URL filters
  const [searchParams, setSearchParams] = useSearchParams();
  const filterBy = searchParams.get("filter") ?? "all";

  // Transient UI state
  const [isExpanded, setIsExpanded] = useState(false);

  // Action feedback
  const actionData = useActionData<typeof action>();

  return (
    <>
      {actionData?.error && <ErrorMessage>{actionData.error}</ErrorMessage>}
      <input
        value={filterBy}
        onChange={(e) => setSearchParams({ filter: e.target.value })}
      />
      <button onClick={() => setIsExpanded(!isExpanded)}>
        {isExpanded ? "Hide" : "Show"} Details
      </button>
      {resources
        .filter(r => filterBy === "all" || r.type === filterBy)
        .map(resource => (
          <ResourceItem key={resource.id} resource={resource} />
        ))}
    </>
  );
}
```

---

## 11. Quick Reference

| Task                       | Hook/API              | When                                    |
| -------------------------- | --------------------- | --------------------------------------- |
| Load initial page data     | `loader` export       | Before route renders                    |
| Handle mutations           | `action` export       | `<Form method="post">` submission       |
| Access loader data         | `useLoaderData()`     | In route components                     |
| Access action result       | `useActionData()`     | After form submission                   |
| Manage URL state           | `useSearchParams()`   | Filters, pagination, sort               |
| Non-navigating mutations   | `useFetcher()`        | Toggles, background saves               |
| Navigation state           | `useNavigation()`     | Submit button disabled states           |
| Catch route errors         | `ErrorBoundary` fn    | Route exports                           |
| Type-safe loader data      | `<typeof loader>`     | In TypeScript with `useLoaderData`      |
| Type-safe action data      | Type guard + `<typeof action>` | In TypeScript with `useActionData` |
| Revalidate loaders         | `revalidator`         | After cross-route action                |

---

## Cross-references

- `/react` — General React 19 patterns, hooks, component state management, composition, testing
- `/typescript` — TypeScript strictness, testing, build tooling
- `/ux-design` — Form UX, accessibility, component API design
