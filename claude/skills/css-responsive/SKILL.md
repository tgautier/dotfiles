---
name: css-responsive
description: |
  Mobile-first CSS architecture and Tailwind CSS v4 strategy for responsive web applications.
  Covers: breakpoint strategy, touch interaction, viewport handling, Tailwind v4 patterns,
  responsive typography, container queries, layout patterns, navigation patterns, performance.
  Use when: building responsive layouts, implementing mobile-first designs, configuring
  Tailwind v4, or auditing responsive behavior across breakpoints.
version: 1.0.0
date: 2026-02-23
user-invocable: true
---

# CSS & Responsive Design

Mobile-first CSS architecture for production web applications. Covers responsive strategy, Tailwind CSS v4 patterns, and performance optimization.

For design tokens and visual hierarchy, see `/ux-design`. For React component patterns, see `/react`. For project-specific breakpoints and Tailwind configuration, check the project's `CLAUDE.md`.

---

## 1. Mobile-First Philosophy

Base styles target mobile (the smallest viewport). Layer complexity upward with `min-width` breakpoints:

```css
/* Base: mobile */
.card { padding: 1rem; }

/* Tablet: md */
@media (min-width: 768px) {
  .card { padding: 1.5rem; }
}

/* Desktop: lg */
@media (min-width: 1024px) {
  .card { padding: 2rem; }
}
```

Rules:
- **Content dictates breakpoints** — don't add a breakpoint because a device exists; add one because the content breaks
- Start with a single column layout for everything, add columns at wider viewports
- Test on real devices, not just browser resize — touch behavior, keyboard avoidance, and safe areas only show on devices

---

## 2. Breakpoint Strategy

### min-width only

Never use `max-width` media queries. They create overlapping ranges, specificity conflicts, and are harder to reason about:

```css
/* WRONG — desktop-first, subtractive */
@media (max-width: 767px) { .sidebar { display: none; } }

/* CORRECT — mobile-first, additive */
.sidebar { display: none; }
@media (min-width: 768px) { .sidebar { display: block; } }
```

### Class ordering in Tailwind

Always order responsive classes from base to widest:

```html
<!-- CORRECT: base → sm → md → lg → xl -->
<div class="p-4 sm:p-6 md:p-8 lg:p-12">

<!-- WRONG: random order -->
<div class="lg:p-12 p-4 md:p-8 sm:p-6">
```

Use `prettier-plugin-tailwindcss` to enforce this automatically.

### Two-breakpoint rule

Most layouts need only two breakpoints:

| Breakpoint | Viewport | Typical layout change |
|---|---|---|
| `md:` (768px) | Tablet | Single column → two columns, show sidebar |
| `lg:` (1024px) | Desktop | Expand sidebar, widen content area |

Add `sm:` or `xl:` only when content genuinely breaks at those widths.

---

## 3. Touch Interaction

### Minimum target size

All interactive elements must be at least 44x44px (WCAG 2.5.8):

```html
<button class="min-h-11 min-w-11 p-2">
  <TrashIcon class="h-5 w-5" />
</button>
```

### Spacing between targets

Adjacent interactive elements need at least 8px gap to prevent mis-taps:

```html
<div class="flex gap-2">
  <button>Edit</button>
  <button>Delete</button>
</div>
```

### Touch-friendly patterns

| Pattern | Mobile | Desktop |
|---|---|---|
| Hover tooltip | Tap to reveal / long-press | Hover |
| Right-click menu | Long-press or explicit menu button | Right-click |
| Drag and drop | Touch-and-hold + drag | Mouse drag |
| Text selection | Long-press to select | Click and drag |

Rule: Never create interactions that only work with hover. Every hover interaction must have a touch/click equivalent.

---

## 4. Viewport Handling

### Dynamic viewport units

Use `dvh` instead of `vh` to account for mobile browser chrome (URL bar, bottom bar):

```css
.full-height { min-height: 100dvh; }
```

In Tailwind v4, `min-h-screen` maps to `100dvh` automatically.

### Safe area insets

For devices with notches or rounded corners:

```css
.bottom-bar {
  padding-bottom: env(safe-area-inset-bottom, 0);
}
```

### Keyboard avoidance

On mobile, the virtual keyboard pushes content up. Avoid:
- Fixed-position elements at the bottom (they cover the keyboard or get pushed off-screen)
- `100vh` layouts (the keyboard changes the viewport height)

Use `visualViewport` API for keyboard-aware positioning:

```typescript
window.visualViewport?.addEventListener("resize", () => {
  const keyboardHeight = window.innerHeight - (window.visualViewport?.height ?? 0);
  // Adjust layout based on keyboardHeight
});
```

### Meta viewport

Every page needs:

```html
<meta name="viewport" content="width=device-width, initial-scale=1" />
```

Never set `maximum-scale=1` or `user-scalable=no` — it breaks accessibility (users who need to zoom).

---

## 5. Tailwind v4 Patterns

### New v4 features

Tailwind v4 replaces `tailwind.config.ts` with CSS-first configuration:

```css
@import "tailwindcss";

/* Theme tokens — replaces theme.extend */
@theme inline {
  --color-brand: #2563eb;
  --color-brand-hover: #1d4ed8;
  --font-display: "Cal Sans", sans-serif;
  --breakpoint-3xl: 1920px;
}

/* Custom variants — replaces plugins */
@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));

/* Custom utilities */
@utility scrollbar-hide {
  &::-webkit-scrollbar { display: none; }
  scrollbar-width: none;
}
```

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

Reserve `@apply` only for cases where component extraction is impractical (e.g., styling CMS markdown output).

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

Wrap CVA with `twMerge` to resolve conflicting utilities:

```typescript
import { twMerge } from "tailwind-merge";
import { clsx, type ClassValue } from "clsx";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### Class ordering

Use `prettier-plugin-tailwindcss` for automatic class sorting.

---

## 6. Responsive Typography

### Fluid type with `clamp()`

Smoothly scale font sizes between breakpoints:

```css
h1 {
  font-size: clamp(1.5rem, 1rem + 2vw, 3rem);
  /* 24px minimum, scales with viewport, 48px maximum */
}
```

### Line length constraint

Optimal reading line length is 45-75 characters:

```html
<p class="max-w-prose">Long paragraph text...</p>
<!-- max-w-prose = 65ch -->
```

### Base font minimums

- Body text: never below 16px (`text-base`)
- Secondary text: never below 14px (`text-sm`)
- Captions/labels: never below 12px (`text-xs`) and only sparingly

### Heading scale

Use consistent Tailwind text sizes, not arbitrary values:

```html
<h1 class="text-2xl md:text-3xl">Page Title</h1>
<h2 class="text-xl md:text-2xl">Section Title</h2>
<h3 class="text-lg md:text-xl">Subsection</h3>
```

---

## 7. Container Queries

### Component-level responsiveness

Container queries let components respond to their container width, not the viewport:

```css
.card-container {
  container-type: inline-size;
}

@container (min-width: 400px) {
  .card { display: grid; grid-template-columns: 1fr 2fr; }
}
```

### Tailwind `@container` variants

```html
<div class="@container">
  <div class="flex flex-col @md:flex-row @md:gap-4">
    <img class="w-full @md:w-48" />
    <div>Content</div>
  </div>
</div>
```

### When to use container queries vs media queries

| Use container queries when | Use media queries when |
|---|---|
| Component is reused at different widths | Layout change affects the entire page |
| Component is in a sidebar AND main content | Navigation pattern changes (sidebar → sheet) |
| Widget is embedded in different contexts | Global typography or spacing changes |

---

## 8. Layout Patterns

### Responsive grid

```html
<!-- 1 column → 2 columns → 3 columns -->
<div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
  <Card /><Card /><Card />
</div>
```

### Sidebar collapse

```html
<!-- Desktop: sidebar + content. Mobile: content only -->
<div class="grid md:grid-cols-[220px_1fr]">
  <aside class="hidden md:block">Sidebar</aside>
  <main>Content</main>
</div>
```

### Sticky elements

```html
<header class="sticky top-0 z-10 bg-background/95 backdrop-blur">
  Navigation
</header>
```

Rules:
- Sticky headers should be thin (48-56px) to preserve vertical space on mobile
- Use `backdrop-blur` so content scrolling underneath is visible but muted
- Set appropriate `z-index` (use a managed scale, not arbitrary numbers)

### Flexbox vs Grid

| Use Flexbox when | Use Grid when |
|---|---|
| Single axis alignment (row or column) | Two-dimensional layout |
| Content determines size | Layout determines size |
| Wrapping items of varying sizes | Strict column/row alignment |
| Component-level layout | Page-level layout |

### Gap utilities

Always use `gap-*` instead of margins on children:

```html
<!-- CORRECT -->
<div class="flex gap-4"><Child /><Child /></div>

<!-- WRONG -->
<div class="flex"><Child class="mr-4" /><Child /></div>
```

---

## 9. Navigation Patterns

### Desktop sidebar → mobile sheet

The standard responsive navigation pattern:

```tsx
function Navigation() {
  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:block w-[220px] border-r">
        <NavLinks />
      </aside>

      {/* Mobile hamburger + sheet */}
      <Sheet>
        <SheetTrigger className="md:hidden">
          <MenuIcon />
        </SheetTrigger>
        <SheetContent side="left">
          <NavLinks />
        </SheetContent>
      </Sheet>
    </>
  );
}
```

### Bottom navigation (mobile apps)

For PWAs or mobile-heavy apps, bottom nav is more thumb-friendly:

```html
<nav class="fixed bottom-0 left-0 right-0 flex justify-around border-t bg-background pb-safe md:hidden">
  <NavItem icon={HomeIcon} label="Home" />
  <NavItem icon={SearchIcon} label="Search" />
  <NavItem icon={ProfileIcon} label="Profile" />
</nav>
```

Rules:
- Max 5 items in bottom nav
- Use `pb-safe` (safe-area-inset-bottom) for devices with home indicators
- Only show on mobile (`md:hidden`)

### Breadcrumbs

Show breadcrumbs for hierarchical navigation, truncate on mobile:

```html
<nav aria-label="Breadcrumb" class="flex items-center gap-1 text-sm">
  <a href="/">Home</a>
  <span class="hidden sm:inline"> / <a href="/assets">Assets</a></span>
  <span> / <span aria-current="page">Asset Detail</span></span>
</nav>
```

---

## 10. Performance

### CLS prevention

Layout shifts are the #1 performance complaint. Prevent them:

```html
<!-- CORRECT: explicit dimensions prevent shift -->
<img src="photo.jpg" width="800" height="600" class="w-full h-auto" />

<!-- CORRECT: aspect-ratio for responsive media -->
<div class="aspect-video">
  <iframe src="..." class="h-full w-full" />
</div>
```

### `content-visibility`

Skip rendering off-screen content:

```css
.long-list-item {
  content-visibility: auto;
  contain-intrinsic-size: 0 80px; /* estimated height */
}
```

### Font loading

```css
@font-face {
  font-family: "Inter";
  src: url("/fonts/inter.woff2") format("woff2");
  font-display: swap;  /* Show fallback immediately, swap when loaded */
}
```

Rules:
- Use `font-display: swap` for body text, `optional` for decorative fonts
- Preload critical fonts: `<link rel="preload" href="/fonts/inter.woff2" as="font" crossorigin>`
- Subset fonts to include only needed characters

### Image optimization

- Use `loading="lazy"` for below-the-fold images
- Serve WebP/AVIF formats with `<picture>` fallback
- Set explicit `width` and `height` to prevent CLS
- Use responsive `srcset` for different viewport widths

### Lazy loading

```html
<img
  src="photo.webp"
  loading="lazy"
  decoding="async"
  width="800"
  height="600"
  alt="Description"
/>
```

---

## 11. Anti-Patterns

| Anti-pattern | Problem | Fix |
|---|---|---|
| `max-width` breakpoints | Desktop-first, overlapping ranges | `min-width` only (mobile-first) |
| `h-screen` or `100vh` | Broken on iOS (URL bar) | `min-h-screen` (100dvh) |
| Fixed `w-[400px]` containers | Breaks on mobile | `max-w-sm` or percentage widths |
| Touch targets under 44px | WCAG 2.5.8 failure | `min-h-11 min-w-11` |
| `!important` overrides | Specificity war | Fix the cascade, use CVA variants |
| Hover-only interactions | Inaccessible on touch | Tap/click alternatives |
| `user-scalable=no` | Blocks zoom accessibility | Remove it, always allow zoom |
| Inline styles for responsive | Can't use media queries | Tailwind responsive variants |
| Margin on children for spacing | Inconsistent, breaks with flex | `gap-*` on the container |
| Arbitrary breakpoints (`max-w-[847px]`) | Unmaintainable | Use Tailwind's standard breakpoints |

---

## Cross-references

- `/ux-design` — design tokens, visual hierarchy, motion, dark mode
- `/react` — component rendering, hooks, state management
- Check the project's `CLAUDE.md` for project-specific breakpoints and Tailwind configuration
