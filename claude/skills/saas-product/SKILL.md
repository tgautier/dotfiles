---
name: saas-product
description: |
  SaaS product design methodology for building user-facing application features.
  Covers: onboarding, empty states, billing UX, feature gating, dashboard design,
  notification patterns, settings/admin UX, audit trails, loading states, multi-tenancy.
  Use when: designing new SaaS features, creating dashboards, planning onboarding flows,
  or reviewing product-level UX decisions.
version: 1.0.0
date: 2026-02-23
user-invocable: true
---

# SaaS Product Design

Methodology for building production SaaS features that drive user adoption and retention. Focused on patterns that reduce time-to-value and handle the complexity of multi-tenant, subscription-based applications.

For design system tokens and accessibility, see `/ux-design`. For React component patterns, see `/react`. For API contracts behind features, see `/api-design`. For domain modeling, see `/domain-design`.

---

## 1. Design Philosophy

### Progressive complexity

Start simple, reveal complexity as the user needs it. A new user should reach their first moment of value within 60 seconds. Advanced features unlock progressively.

| Principle | Application |
| --- | --- |
| **Time-to-value** | Minimize steps between signup and first meaningful action |
| **Progressive disclosure** | Hide advanced options behind "Advanced" toggles or secondary menus |
| **Jobs-to-be-done** | Design around what the user is trying to accomplish, not around data entities |
| **Sensible defaults** | Pre-fill settings with the most common choices; make the default path correct |
| **Undo over confirm** | Prefer reversible actions with undo over confirmation dialogs that interrupt flow |

### Product hierarchy

```
Feature → Page → Section → Component
```

Each level has a clear responsibility:
- **Feature**: A complete capability (e.g., "Asset Tracking")
- **Page**: A view within a feature (e.g., "Asset List", "Asset Detail")
- **Section**: A logical grouping within a page (e.g., "Performance Chart", "Transaction History")
- **Component**: A reusable UI element (e.g., "Currency Badge", "Date Picker")

---

## 2. Onboarding & First-Run

### Activation metrics

Define what "activated" means before building onboarding:

| Metric | Example |
| --- | --- |
| **Setup complete** | User has connected at least one data source |
| **First value** | User has viewed their first dashboard with real data |
| **Habit formed** | User returns 3 times in the first 7 days |

### Progressive onboarding patterns

**Setup wizard** — for products requiring initial configuration:

```tsx
function SetupWizard() {
  const [step, setStep] = useState(0);
  const steps = [
    { title: "Connect account", component: ConnectAccountStep },
    { title: "Import data", component: ImportDataStep },
    { title: "Set preferences", component: PreferencesStep },
  ];

  return (
    <div>
      <StepIndicator steps={steps} current={step} />
      <CurrentStep onNext={() => setStep(step + 1)} />
      <SkipLink onClick={skipToApp}>Skip setup — I'll do this later</SkipLink>
    </div>
  );
}
```

Rules:
- Always allow skipping — never force completion of all steps
- Save progress — if the user leaves, resume where they stopped
- Max 3-5 steps — more than that and users abandon
- Show progress clearly (step 2 of 4)

**Checklist pattern** — for products where setup is gradual:

```tsx
function OnboardingChecklist({ tasks }: { tasks: OnboardingTask[] }) {
  const completed = tasks.filter(t => t.done).length;
  return (
    <Card>
      <Progress value={completed} max={tasks.length} />
      <p>{completed} of {tasks.length} complete</p>
      {tasks.map(task => (
        <ChecklistItem key={task.id} task={task} />
      ))}
      {completed === tasks.length && <DismissButton />}
    </Card>
  );
}
```

**Contextual tooltips** — for feature discovery after initial setup:
- Show once per user, track dismissal in user preferences
- Point to the specific UI element, not a general area
- Include a single clear CTA ("Try it now" / "Got it")

### Anti-patterns

- Forced video tours (users skip them)
- Tooltips on every element simultaneously (overwhelming)
- Blocking the app until onboarding is complete (drives abandonment)
- Showing onboarding to returning users who already completed it

---

## 3. Empty States

Every data-driven view must handle four empty conditions:

| Type | When | Content |
| --- | --- | --- |
| **First-use** | User hasn't created any data yet | Illustration + explanation + primary CTA |
| **No results** | Search or filter returned nothing | "No results for X" + suggestion to broaden search |
| **Error** | Data failed to load | Error message + retry button |
| **Filtered empty** | Applied filters exclude all results | Show active filters + "Clear filters" button |

### First-use empty state pattern

```tsx
function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 text-muted-foreground">{icon}</div>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
      {action && <Button className="mt-4" onClick={action.onClick}>{action.label}</Button>}
    </div>
  );
}

// Usage
<EmptyState
  icon={<WalletIcon size={48} />}
  title="No assets yet"
  description="Add your first asset to start tracking your portfolio performance."
  action={{ label: "Add Asset", onClick: openAddAssetDialog }}
/>
```

Rules:
- First-use empty states must have a CTA that leads to creating the first item
- Never show a blank page or a lonely "No data" message
- Use illustrations or icons to make the empty state feel intentional, not broken
- Reduce the CTA to a single clear action — don't offer multiple paths

---

## 4. Dashboard Design

### KPI card anatomy

A well-designed KPI card shows: current value, trend indicator, comparison period, and optional sparkline.

```tsx
interface KPICardProps {
  label: string;
  value: string;
  change: number;      // percentage change
  period: string;      // "vs last month"
  sparklineData?: number[];
}

function KPICard({ label, value, change, period, sparklineData }: KPICardProps) {
  const isPositive = change >= 0;
  return (
    <Card>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
      <div className="flex items-center gap-1 text-sm">
        <TrendIcon direction={isPositive ? "up" : "down"} />
        <span className={isPositive ? "text-green-600" : "text-red-600"}>
          {Math.abs(change)}%
        </span>
        <span className="text-muted-foreground">{period}</span>
      </div>
      {sparklineData && <Sparkline data={sparklineData} />}
    </Card>
  );
}
```

### Chart selection guide

| Data relationship | Chart type | When to use |
| --- | --- | --- |
| Part-to-whole | Donut (max 5 segments) | Budget allocation, portfolio mix |
| Change over time | Line / area | Revenue trends, growth metrics |
| Comparison | Horizontal bar | Category comparison, rankings |
| Distribution | Histogram | Value ranges, frequency |
| Composition over time | Stacked area | Revenue by segment over time |

Rules:
- Never use pie charts for more than 5 segments — switch to horizontal bar
- Never use 3D charts
- Line charts require a continuous x-axis (time, sequence)
- Always label axes and include units

### Dashboard layout

- Top row: 3-4 KPI cards summarizing the most important metrics
- Middle: Primary chart (full width or 2/3 width)
- Bottom: Secondary data tables or detail views
- Use CSS Grid for the layout: `grid-cols-1 md:grid-cols-2 lg:grid-cols-4` for KPI row

### Data density

- Dense displays for power users (tables with many columns, compact spacing)
- Summary views for casual users (KPI cards, sparklines, simplified charts)
- Let users toggle between views or remember their preference

---

## 5. Loading & Transition States

### Skeleton screens

Match the skeleton shape to the actual content layout. Users perceive skeleton screens as faster than spinners:

```tsx
function AssetListSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-3 w-32" />
          </div>
          <Skeleton className="ml-auto h-4 w-20" />
        </div>
      ))}
    </div>
  );
}
```

### Loading state decision framework

| Duration | Pattern |
| --- | --- |
| < 100ms | No indicator needed |
| 100-300ms | Subtle inline indicator (button spinner) |
| 300ms-2s | Skeleton screen |
| 2-10s | Progress bar or skeleton with message |
| > 10s | Background task with notification on completion |

### Optimistic UI

For mutations where failure is rare, update the UI immediately and revert on error:

```tsx
const [optimisticAssets, addOptimistic] = useOptimistic(
  assets,
  (current, newAsset: Asset) => [...current, newAsset],
);

async function handleCreate(data: CreateAssetInput) {
  addOptimistic({ ...data, id: crypto.randomUUID() });
  const result = await createAsset(data);
  if (!result.ok) {
    showToast("Failed to create asset. Please try again.", "error");
  }
}
```

### Streaming SSR

For pages with mixed fast/slow data sources:
- Fast data (navigation, layout) renders immediately in the shell
- Slow data (analytics, external APIs) streams in via Suspense boundaries
- Each Suspense boundary shows its own skeleton while loading

---

## 6. Notification Design

### Notification channels

| Channel | Use for | Urgency |
| --- | --- | --- |
| **In-app toast** | Action confirmation, minor errors | Low — auto-dismiss 5s |
| **In-app bell** | New activity, status changes | Medium — persists until read |
| **Email** | Transactional (receipts, invites), digests | Low — batched where possible |
| **Browser push** | Time-sensitive alerts only | High — interrupts |

### Toast best practices

```tsx
// Success toast with undo
showToast("Asset deleted", {
  action: { label: "Undo", onClick: undoDelete },
  duration: 5000,
});

// Error toast — persists until dismissed
showToast("Failed to save changes. Please try again.", {
  variant: "error",
  duration: Infinity,
  action: { label: "Retry", onClick: retryAction },
});
```

Rules:
- Auto-dismiss success toasts after 5 seconds
- Never auto-dismiss error toasts — the user may not notice them
- Provide an undo action for destructive operations
- Stack multiple toasts vertically, limit to 3 visible simultaneously
- Never use toasts as the sole error indicator for form validation

### Notification preferences

Implement as a channel-by-event matrix:

| Event | In-App | Email | Push |
| --- | --- | --- | --- |
| New team member | Default on | Default on | Default off |
| Weekly digest | N/A | Default on | N/A |
| Payment failed | Default on | Default on | Default on |
| Feature update | Default on | Default off | Default off |

Let users control each cell independently.

---

## 7. Billing & Subscription UX

### Plan comparison

```tsx
function PlanComparison({ plans }: { plans: Plan[] }) {
  return (
    <div className="grid gap-6 md:grid-cols-3">
      {plans.map(plan => (
        <PlanCard
          key={plan.id}
          name={plan.name}
          price={plan.price}
          period={plan.period}
          features={plan.features}
          recommended={plan.recommended}
          current={plan.current}
        />
      ))}
    </div>
  );
}
```

Rules:
- Highlight the recommended plan visually (border, badge, "Most Popular")
- Show the current plan clearly so the user knows where they are
- List features as checkmarks per plan — show what's included AND what's not
- Annual pricing should show the monthly equivalent and savings percentage

### Upgrade prompts

Contextual prompts are 3x more effective than generic upsell banners:

```tsx
// GOOD — contextual, shown when the user hits a limit
function FeatureLimitPrompt({ feature, limit, current }: LimitPromptProps) {
  return (
    <Alert>
      <p>You've used {current} of {limit} {feature}.</p>
      <Button variant="link" asChild>
        <Link to="/settings/billing">Upgrade for unlimited {feature}</Link>
      </Button>
    </Alert>
  );
}

// BAD — generic banner shown on every page
<Banner>Upgrade to Pro for more features!</Banner>
```

### Trial and downgrade

- Show trial days remaining in a subtle, persistent indicator (not a popup)
- Before downgrade: show what the user will lose, not just the features list
- After downgrade: gracefully degrade features (read-only, not deleted)
- Never delete user data on downgrade — mark it as inaccessible and allow re-upgrade

---

## 8. Feature Gating

### Implementation patterns

| Pattern | Use when |
| --- | --- |
| **Feature flag** | Rolling out new features gradually (% of users) |
| **Plan gating** | Feature is available only on certain subscription tiers |
| **Role gating** | Feature is restricted to certain user roles (admin, member) |
| **Usage limit** | Feature has a quota per billing period |

### Graceful degradation

When a feature is gated, show the user what they're missing and how to get it:

```tsx
function GatedFeature({ feature, children }: GatedFeatureProps) {
  const { hasAccess, requiredPlan } = useFeatureAccess(feature);

  if (hasAccess) return <>{children}</>;

  return (
    <div className="relative">
      <div className="pointer-events-none opacity-40 blur-[1px]">{children}</div>
      <UpgradeOverlay feature={feature} requiredPlan={requiredPlan} />
    </div>
  );
}
```

Rules:
- Never show a blank space where a gated feature should be — show a teaser
- Don't hide gated features entirely — discovery drives upgrades
- Use blurred previews or locked icons, not error messages
- Role-gated features should show a "Contact your admin" message, not an upgrade prompt

---

## 9. Settings & Admin UX

### Settings organization

| Section | Contents |
| --- | --- |
| **Account** | Profile, email, password, 2FA |
| **Team** | Members, invitations, roles |
| **Billing** | Plan, payment method, invoices |
| **Preferences** | Theme, language, notification settings |
| **Integrations** | Connected services, API keys |
| **Danger zone** | Delete account, export data |

### Danger zone

Destructive settings must be visually distinct and require confirmation:

```tsx
function DangerZone() {
  return (
    <Card className="border-red-200 bg-red-50">
      <h3 className="text-red-900">Danger Zone</h3>
      <div className="space-y-4">
        <DangerAction
          title="Delete account"
          description="Permanently delete your account and all data. This cannot be undone."
          confirmText="delete my account"
          onConfirm={deleteAccount}
        />
      </div>
    </Card>
  );
}
```

Rules:
- Red border/background for the danger zone section
- Require typing a confirmation phrase for irreversible actions
- Show a clear description of what will be deleted/lost
- Offer data export before account deletion

---

## 10. Audit Trails & Activity Feeds

### Feed structure

Every audit entry answers: **who** did **what** to **which resource** and **when**.

```typescript
interface AuditEntry {
  id: string;
  actor: { id: string; name: string; avatar?: string };
  action: string;         // "created" | "updated" | "deleted" | "exported"
  resource: { type: string; id: string; name: string };
  changes?: FieldChange[];
  timestamp: string;      // ISO 8601
}

interface FieldChange {
  field: string;
  from: string | null;
  to: string | null;
}
```

### Display patterns

- Group entries by day with date headers
- Show the most recent activity first
- Paginate with "Load more" (not page numbers) for chronological feeds
- Filter by: actor, action type, resource type, date range
- For field changes, show a diff view: ~~old value~~ → new value

---

## 11. Multi-Tenancy Awareness

### Tenant context in UI

- Always show the current organization/workspace name in the sidebar or header
- Org switcher should be prominent and always accessible
- After switching orgs, redirect to the new org's dashboard (not the same page, which may not exist)

### Data isolation

- Every API request must include tenant context (header, path param, or session)
- Never show data from other tenants — even in error messages
- Search results must be scoped to the current tenant
- URL paths should include the tenant identifier for shareable links: `/org/{org-id}/assets`

### Shared resources

Some resources span tenants (billing admin, super admin views). Clearly distinguish:
- Tenant-scoped views: normal styling
- Cross-tenant views: distinct visual treatment (different background, admin badge)

---

## 12. Anti-Patterns

| Anti-pattern | Why it fails | Better approach |
| --- | --- | --- |
| Blocking modal on first visit | Users close it immediately, miss the content | Inline checklist or contextual hints |
| "No data" as empty state | Feels broken, gives no guidance | First-use empty state with CTA |
| Spinner for every load | Users perceive it as slow | Skeleton screens matching content shape |
| Generic upgrade banner | Banner blindness, users ignore it | Contextual prompts when hitting limits |
| Settings as a flat list | Overwhelming, hard to find things | Grouped sections with clear hierarchy |
| Hiding features behind menus | Low discoverability | Progressive disclosure with visual cues |
| Confirmation dialog for every action | Dialog fatigue, users click without reading | Undo pattern for reversible actions |
| Email-only notifications | Users miss them, no in-app awareness | In-app notification center + email fallback |
| All-or-nothing free plan | High barrier to conversion | Generous free tier with usage-based limits |
| Instant data deletion on downgrade | Users fear committing to plans | Grace period + read-only access |
| Activity feed without filters | Noise drowns signal for active orgs | Filter by actor, action, resource, date |
| No tenant indicator in UI | Users accidentally modify wrong org | Always show current org + easy switching |

---

## Cross-references

- `/ux-design` — design tokens, accessibility, component API design, form UX
- `/react` — React component patterns, hooks, state management
- `/api-design` — REST contracts, pagination, error formats behind features
- `/domain-design` — aggregate boundaries, entity vs value object, domain events
