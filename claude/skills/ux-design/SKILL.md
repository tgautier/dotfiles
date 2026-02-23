---
name: ux-design
description: |
  Design system methodology and UX engineering for production applications.
  Covers: design token architecture, visual hierarchy, component API design,
  form UX depth, ARIA widget patterns, motion/animation, dark mode strategy,
  theming, icon systems, and data visualization UX.
  Use when: building design systems, implementing complex form flows,
  adding animation, designing data visualizations, or auditing accessibility.
version: 1.0.0
date: 2026-02-23
user-invocable: true
---

# UX Design & Design Systems

Canonical reference for design system engineering, accessibility, and UX patterns. This skill absorbs and expands component design, form handling, and accessibility guidance — these topics live here, not in language-specific skills.

For responsive CSS and Tailwind patterns, see `/css-responsive`. For SaaS-specific product patterns, see `/saas-product`. For React hooks and state, see `/react`.

---

## 1. Design Philosophy

| Principle | Application |
| --- | --- |
| **Consistency > aesthetics** | A consistent but plain UI outperforms an inconsistent beautiful one |
| **Constraints enable creativity** | Tokens and scales prevent visual entropy and speed up decisions |
| **Accessibility is design** | A11y isn't a bolt-on — it shapes hierarchy, contrast, spacing, and interaction |
| **Composable over configurable** | Combine small, focused components instead of building mega-components with 30 props |
| **Content drives layout** | Design components around real data lengths and edge cases, not lorem ipsum |

---

## 2. Design Token Architecture

### Token layers

Tokens flow through three layers: **primitive** → **semantic** → **component**.

```css
/* Primitive: raw values, never used directly in components */
:root {
  --color-gray-50: #f9fafb;
  --color-gray-900: #111827;
  --color-blue-600: #2563eb;
  --space-1: 0.25rem;
  --space-4: 1rem;
  --radius-md: 0.375rem;
}

/* Semantic: purpose-based, theme-switchable */
:root {
  --color-bg-primary: var(--color-gray-50);
  --color-text-primary: var(--color-gray-900);
  --color-interactive: var(--color-blue-600);
  --space-component-gap: var(--space-4);
  --radius-default: var(--radius-md);
}

/* Component: scoped to specific components */
.button {
  --button-bg: var(--color-interactive);
  --button-radius: var(--radius-default);
  --button-padding: var(--space-1) var(--space-4);
}
```

### Token categories

| Category | Examples | Scale |
| --- | --- | --- |
| **Color** | `bg-primary`, `text-muted`, `border-default` | Semantic names, not color names |
| **Spacing** | `space-1` through `space-16` | 4px base scale (0.25rem increments) |
| **Typography** | `text-sm`, `text-base`, `text-xl` | Modular scale (1.25 ratio) |
| **Radius** | `radius-sm`, `radius-md`, `radius-lg` | 3-4 values max |
| **Elevation** | `shadow-sm`, `shadow-md`, `shadow-lg` | 3-4 levels, tied to z-index |
| **Duration** | `duration-fast`, `duration-normal`, `duration-slow` | 100ms / 200ms / 300ms |

Rules:
- Components reference only semantic tokens, never primitives
- Semantic tokens reference primitives — this is the only place primitives appear
- New tokens need a clear semantic purpose — don't add tokens speculatively

---

## 3. Visual Hierarchy

### Typography scale

Use a modular scale (ratio 1.25) anchored at 16px base:

| Token | Size | Use |
| --- | --- | --- |
| `text-xs` | 12px | Captions, labels, timestamps |
| `text-sm` | 14px | Secondary text, descriptions |
| `text-base` | 16px | Body text (minimum for readability) |
| `text-lg` | 18px | Subheadings, card titles |
| `text-xl` | 20px | Section headings |
| `text-2xl` | 24px | Page titles |
| `text-3xl` | 30px | Hero headings |

### Whitespace rhythm

Consistent spacing creates visual rhythm. Use the 4px grid:

- **Within components**: `gap-2` (8px) between related elements
- **Between components**: `gap-4` (16px) between sibling components
- **Between sections**: `gap-8` (32px) between page sections
- **Page padding**: `p-4` mobile, `p-6` tablet, `p-8` desktop

### Color as hierarchy

| Level | Treatment | Example |
| --- | --- | --- |
| **Primary** | Full contrast (`text-foreground`) | Headlines, primary actions |
| **Secondary** | Reduced contrast (`text-muted-foreground`) | Descriptions, labels |
| **Tertiary** | Lowest contrast (`text-muted-foreground/60`) | Timestamps, metadata |
| **Interactive** | Accent color (`text-primary`) | Links, active states |
| **Danger** | Red (`text-destructive`) | Errors, delete actions |

---

## 4. Component API Design

### Composition over prop drilling

```tsx
// WRONG: drilling user through 4 levels
<Layout user={user}><Sidebar user={user}><Nav user={user} /></Sidebar></Layout>

// CORRECT: compose with children, read from context/hooks
<Layout><Sidebar><Nav /></Sidebar></Layout>
```

### Compound components

Use React Context to share implicit state between a parent and its children:

```tsx
<Select>
  <Select.Trigger>Choose...</Select.Trigger>
  <Select.Content>
    <Select.Item value="a">Option A</Select.Item>
  </Select.Content>
</Select>
```

Each child renders itself; the parent manages shared state. This is the Radix UI / shadcn/ui pattern.

### Headless component libraries

Prefer accessible behavior primitives with zero styling opinions:

- **Radix UI** — shadcn/ui foundation, comprehensive
- **React Aria** (Adobe) — extensive accessibility primitives
- **ARIAKit** — lightweight alternative

These handle keyboard navigation, focus trapping, ARIA attributes, and screen reader announcements automatically.

### Props interface rules

- Use `interface` for component props (supports declaration merging)
- Use explicit prop types — never `React.FC` (it adds implicit `children`)
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

### Polymorphic `as` prop

Allow consumers to change the rendered element:

```tsx
interface BoxProps<T extends ElementType = "div"> {
  as?: T;
  children: ReactNode;
}

function Box<T extends ElementType = "div">({ as, children, ...props }: BoxProps<T> & ComponentPropsWithoutRef<T>) {
  const Component = as ?? "div";
  return <Component {...props}>{children}</Component>;
}

// Usage
<Box as="section" className="p-4">Content</Box>
<Box as="article" className="p-4">Content</Box>
```

### Variant systems with CVA

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
```

### Single responsibility

A component should do one thing. If a component fetches data, transforms it, validates it, and renders a form, break it into:
- A route loader for data fetching
- A custom hook for transformation logic
- A form component for rendering and validation

### Composability test

A component is well-designed if it can be:
1. Used in isolation (storybook, test)
2. Composed with siblings without knowing about them
3. Extended without modifying its source

---

## 5. Form UX

### Zod as single source of truth

Define validation schemas once, infer types:

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

  return <form onSubmit={form.handleSubmit(onSubmit)}>{/* fields */}</form>;
}
```

### Cross-field validation

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

Client-side validation is a UX convenience. The API must always validate independently. Never trust client-submitted data. When the server returns validation errors, map them back to form fields using `setError`.

### Validation timing

| Strategy | When | UX tradeoff |
| --- | --- | --- |
| `onBlur` | Default for most fields | Low noise, feedback after user finishes |
| `onChange` | After first error shown | Re-validate immediately so user sees fix |
| `onSubmit` | Expensive checks (uniqueness) | Avoid per-keystroke API calls |
| Debounced `onChange` | Username/email availability | 300ms debounce, inline spinner |

### Error placement

- Display errors **below** the field, not above or in a summary at the top
- Use `aria-describedby` to associate the error with the input
- Use `role="alert"` on the error container
- Never clear an error until the user corrects it

```tsx
<div>
  <label htmlFor="email">Email</label>
  <input
    id="email"
    aria-invalid={!!errors.email}
    aria-describedby={errors.email ? "email-error" : undefined}
    {...register("email")}
  />
  {errors.email && (
    <p id="email-error" role="alert" className="text-sm text-red-600 mt-1">
      {errors.email.message}
    </p>
  )}
</div>
```

### Multi-step forms

For wizard-style forms with 3+ steps:
- Validate each step independently before allowing the user to proceed
- Allow backward navigation without losing data
- Show a progress indicator (step 2 of 4)
- Submit all data in a single API call at the end, not per-step

### Disabled vs read-only

- **Disabled** — user cannot interact AND the value is not submitted. Use for actions not currently available
- **Read-only** — user cannot edit BUT the value IS submitted. Use for pre-filled fields the user should see but not change
- Never disable a field to "prevent errors" — use validation instead

### Auto-save patterns

- Debounce saves (500ms minimum)
- Show subtle "Saving..." / "Saved" indicator — never a blocking spinner
- Handle conflicts: if the server rejects a stale save, show a merge/overwrite choice
- Use `onBlur` as the primary save trigger for inline editing

---

## 6. Accessibility

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
- Escape closes modals, popovers, and dropdowns

### ARIA widget patterns

**Dialog (modal):**
```tsx
<div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Confirm deletion</h2>
  <button>Cancel</button>
  <button>Delete</button>
</div>
```
Keyboard: Tab cycles within dialog. Escape closes. Focus trapped.

**Combobox (autocomplete):**
```tsx
<input
  role="combobox"
  aria-expanded={isOpen}
  aria-controls="listbox-id"
  aria-activedescendant={activeOptionId}
/>
<ul id="listbox-id" role="listbox">
  <li role="option" id="opt-1" aria-selected={selected === "opt-1"}>Option 1</li>
</ul>
```
Keyboard: Arrow keys navigate. Enter selects. Escape closes.

**Tabs:**
```tsx
<div role="tablist" aria-label="Settings">
  <button role="tab" aria-selected={active === 0} aria-controls="panel-0">General</button>
  <button role="tab" aria-selected={active === 1} aria-controls="panel-1">Security</button>
</div>
<div role="tabpanel" id="panel-0">General content</div>
```
Keyboard: Arrow keys move between tabs. Home/End jump to first/last.

**Menu:**
```tsx
<button aria-haspopup="true" aria-expanded={isOpen}>Actions</button>
<ul role="menu">
  <li role="menuitem">Edit</li>
  <li role="menuitem">Delete</li>
</ul>
```
Keyboard: Arrow keys navigate. Enter activates. Escape closes.

### Live regions

```tsx
// Polite: announced after current speech finishes
<div aria-live="polite" aria-atomic="true">
  {status === "saving" ? "Saving..." : "All changes saved"}
</div>

// Assertive: interrupts current speech
<div aria-live="assertive" role="alert">
  {error && `Error: ${error.message}`}
</div>
```

### Color contrast

| Content type | Minimum ratio (WCAG AA) |
| --- | --- |
| Body text | 4.5:1 |
| Large text (18px+ or 14px+ bold) | 3:1 |
| UI components & graphical objects | 3:1 |

Never rely on color alone to convey meaning — pair with icons, text, or patterns.

### Testing accessibility

1. **Automated (axe-core):** Run in Vitest and Playwright for WCAG violations
2. **Keyboard-only:** Tab through every flow without a mouse
3. **Screen reader:** Test with VoiceOver (macOS) or NVDA (Windows)
4. **Zoom:** Verify layout at 200% and 400% zoom
5. **Color:** Check with simulated color blindness

```tsx
import { axe, toHaveNoViolations } from "jest-axe";
expect.extend(toHaveNoViolations);

it("has no accessibility violations", async () => {
  const { container } = render(<MyComponent />);
  expect(await axe(container)).toHaveNoViolations();
});
```

---

## 7. Motion & Animation

### Purpose-driven motion

| Purpose | Example | Duration |
| --- | --- | --- |
| **Orient** | Page transitions, element repositioning | 200-300ms |
| **Inform** | Loading spinners, progress bars | 100-500ms |
| **Delight** | Micro-interactions, hover effects | 100-200ms |

If an animation serves none of these purposes, remove it.

### Duration scale

```css
:root {
  --duration-instant: 50ms;   /* Opacity toggles */
  --duration-fast: 100ms;     /* Hover effects */
  --duration-normal: 200ms;   /* Dropdowns, tooltips */
  --duration-slow: 300ms;     /* Modal enter, page transitions */
  --duration-slower: 500ms;   /* Complex layout animations */
}
```

### Easing

- **Entering elements**: ease-out (start fast, decelerate)
- **Exiting elements**: ease-in (start slow, accelerate)
- Never use `linear` for UI motion

### `prefers-reduced-motion`

Respect the user's system preference:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

In Tailwind: `motion-safe:animate-fade-in motion-reduce:opacity-100`

---

## 8. Dark Mode Strategy

### Token inversion

Dark mode remaps semantic tokens, not individual components:

```css
:root { --color-bg-primary: var(--color-gray-50); }
[data-theme="dark"] { --color-bg-primary: var(--color-gray-900); }
```

### Rules

- Test every component in both light and dark
- Never hardcode `white`, `black`, `#fff`, or `#000` — use semantic tokens
- Use `filter: brightness(0.9)` on images in dark mode to reduce glare
- Replace shadows with subtle borders on dark backgrounds
- Prevent white flash with a blocking `<script>` in `<head>` that reads the stored theme

---

## 9. Theming & Runtime Switching

### CSS custom property architecture

All theming flows through CSS custom properties:

```css
[data-theme="light"] {
  --color-bg-primary: #ffffff;
  --color-text-primary: #111827;
}
[data-theme="dark"] {
  --color-bg-primary: #0f172a;
  --color-text-primary: #f1f5f9;
}
```

### ThemeProvider

```tsx
type Theme = "light" | "dark" | "system";

function ThemeProvider({ children, defaultTheme = "system" }: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(defaultTheme);
  const resolvedTheme = useMemo(() => {
    if (theme !== "system") return theme;
    if (typeof window === "undefined") return "light"; // SSR fallback
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }, [theme]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", resolvedTheme);
    localStorage.setItem("theme", theme);
  }, [theme, resolvedTheme]);

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
```

### Theme inheritance

Nested `data-theme` attributes override the parent — CSS custom properties inherit down the DOM tree. Use this for forced-dark regions (e.g., a dark sidebar in a light app).

---

## 10. Icon & Illustration Systems

### Consistent library

Choose one icon library and use it everywhere:

| Library | Style | Notes |
| --- | --- | --- |
| Lucide | Outlined, consistent stroke | Tree-shakeable React components |
| Heroicons | Outline + solid variants | From the Tailwind team |
| Phosphor | 6 weight variants | Most flexible |

### Accessibility

**Decorative icons** (next to a text label) — hide from screen readers:
```tsx
<button><TrashIcon aria-hidden="true" /> Delete</button>
```

**Meaningful icons** (standalone) — provide an accessible name:
```tsx
<button aria-label="Delete item"><TrashIcon aria-hidden="true" /></button>
```

### SVG approach

- Use inline SVGs (React components) for icons that need `currentColor` styling
- Set `fill="currentColor"` or `stroke="currentColor"` to inherit text color
- Never use icon fonts — they fail when fonts fail to load

---

## 11. Data Visualization UX

### Chart type by data relationship

| Relationship | Chart type | Rule |
| --- | --- | --- |
| Part-to-whole | Donut (max 5 segments) | Never pie with 6+ segments |
| Change over time | Line / area | Continuous x-axis required |
| Comparison | Horizontal bar | Best for ranked categories |
| Distribution | Histogram | Value ranges, outliers |

### Color accessibility

- 3:1 contrast between adjacent data series
- Never rely on color alone — add patterns, labels, or markers
- Limit to 6-8 colors per chart

### Responsive charts

- Use `ResizeObserver` for container width, not window width
- Below 480px: simplify (hide legend, rotate labels)
- Below 320px: replace chart with summary number or sparkline
- Always set minimum height (200px)

### Empty and loading states

Every chart needs three states: loading (skeleton), empty (illustration + CTA), error (message + retry). Never a blank space.

---

## 12. Anti-Patterns

| Anti-pattern | Problem | Fix |
| --- | --- | --- |
| Magic numbers (`padding: 13px`) | Breaks consistency | Use spacing tokens |
| Color by hex everywhere | Impossible to theme | Use semantic tokens |
| `div` with click handler | No keyboard/a11y support | Use `<button>` or `<a>` |
| Hiding focus outlines | Keyboard users lost | Style `:focus-visible` |
| Toast-only form errors | Users miss them | Inline errors with `aria-describedby` |
| Disabled submit without explanation | User doesn't know what to fix | Show validation errors |
| Icon-only buttons without labels | Invisible to screen readers | `aria-label` or hidden text |
| `z-index: 9999` | Arms race, layering bugs | Managed stacking context |
| Animation without reduced-motion | Motion sickness | `motion-safe:` or media query |
| Hardcoded light/dark colors | Breaks theming | CSS custom property tokens |
| Client-side only validation | Security risk | Always validate on server |
| Pixel font sizes | Breaks user zoom | Use `rem` exclusively |

---

## Cross-references

- `/css-responsive` — layout, breakpoints, touch targets, Tailwind CSS v4
- `/saas-product` — dashboards, empty states, notifications, onboarding
- `/react` — hooks, state management, component rendering patterns
