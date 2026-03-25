---
name: react
description: |
  React 19 development patterns for production web applications.
  Covers: React 19 features, hooks, component composition, state management,
  error handling, and testing methodology.
  Use when: writing React components, managing component state, handling errors,
  testing components, or designing component APIs.
version: 2.1.0
date: 2026-03-25
user-invocable: true
---

# React 19 Development

React 19 component patterns, hooks, and testing methodology for production applications. This covers the component and composition layer — component design, hooks, state management, error handling within components, and testing strategies.

For React Router loaders, actions, mutations, and data patterns, see `/react-router`. For TypeScript strictness, testing, and build tooling, see `/typescript`. For component design, form UX, and accessibility, see `/ux-design`. For CSS and responsive patterns, see `/css-responsive`.

---

## 1. React 19 Core Features

### `use()` hook

Reads promises and context inside conditionals and loops (unlike other hooks):

```tsx
function ResourceDetail({
  resourcePromise,
}: {
  resourcePromise: Promise<Resource>;
}) {
  const resource = use(resourcePromise); // suspends until resolved
  return <h1>{resource.name}</h1>;
}
```

---

## 2. Hooks & Composition

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
function useAssetToggle(initialValue: boolean) {
  const [isOpen, setIsOpen] = useState(initialValue);
  const toggle = useCallback(() => setIsOpen((v) => !v), []);
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  return { isOpen, toggle, open, close };
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

Wrap hooks that need providers in a wrapper:

```tsx
const wrapper = ({ children }: { children: ReactNode }) => (
  <MyContextProvider>{children}</MyContextProvider>
);

const { result } = renderHook(() => useMyHook(), { wrapper });
```

---

## 3. Error Handling in Components

### Error boundaries for feature isolation

Error boundaries catch rendering errors and prevent entire page crashes:

```tsx
import { ErrorBoundary } from "react-error-boundary";

<ErrorBoundary
  FallbackComponent={ErrorFallback}
  onReset={() => {
    /* reset state or retry */
  }}
  resetKeys={[itemId]}
>
  <FeatureWidget />
</ErrorBoundary>;
```

### What error boundaries do NOT catch

- Errors in event handlers (use try/catch)
- Async errors outside React rendering (handle in promise chains)
- Errors in the error boundary itself

### Toast notifications

Use for non-blocking errors (e.g., "Failed to save"). Libraries: `sonner`, `react-hot-toast`. Never use toasts as the sole error indicator for validation feedback.

---

## 4. Component State Management

### Decision framework for state location

| State type   | Location           | Example                              |
| ------------ | ------------------ | ------------------------------------ |
| Transient UI | `useState`         | Modal open/close, delete confirm     |
| Derived      | `useMemo`          | Computed values, derived from props  |
| Form data    | DOM inputs         | Uncontrolled inputs with defaultValue |
| Shared UI    | Context + useState | Theme, notifications, user prefs     |

### Key rules

- `useState` is for transient UI only — things that don't affect the render tree when lost
- Never copy props into state — compute during render with `useMemo`
- Keep state as close to where it's used as possible
- Split large contexts into smaller, focused ones
- Never use `useEffect` to sync derived values — compute them during render

---

## 5. Anti-Patterns

| Anti-pattern                              | Problem                                       | Fix                                        |
| ----------------------------------------- | --------------------------------------------- | ------------------------------------------ |
| Prop drilling through 4+ levels           | Fragile, hard to refactor                     | Context or composition                     |
| `useLayoutEffect` without SSR guard       | Server warning, runs as `useEffect` on server | `useEffect` or `useIsomorphicLayoutEffect` |
| `useEffect` for derived state             | Extra render cycle, stale values              | Compute during render with `useMemo`       |
| Manual `useMemo`/`useCallback` everywhere | Noise, premature optimization                 | React Compiler handles memoization         |
| `useState` for form field values          | Duplicate state, out of sync with DOM         | Uncontrolled inputs + `defaultValue`       |

---

## Cross-references

- `/react-router` — Data loading, mutations, routing, URL state management
- `/typescript` — TypeScript strictness, testing (Vitest/Playwright), modules, build tooling
- `/ux-design` — component API design, form UX, accessibility
- `/css-responsive` — responsive rendering, Tailwind CSS patterns
