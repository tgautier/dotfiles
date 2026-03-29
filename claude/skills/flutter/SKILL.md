---
name: flutter
description: |
  Production Flutter development skill for native mobile applications.
  Covers: MVVM architecture, Riverpod state management, go_router navigation,
  Freezed models, widget composition, theming (Material 3), testing methodology,
  performance optimization, and platform channels.
  Use when: writing widgets, providers, screens, models, tests, or reviewing Flutter code quality.
version: 1.0.0
date: 2026-03-27
user-invocable: true
---

# Flutter Development

Production guidance for Flutter native mobile applications. Based on the Flutter team's official architecture guide (2024), Riverpod documentation, Very Good Ventures patterns, and Andrea Bizzotto's architecture series.

For API contract design and HTTP semantics, see `/api-design`. For domain modeling, see `/domain-design`. For design system and accessibility, see `/ux-design`. For observability, see `/observability`.

---

## 1. Architecture — MVVM with Layered Data

Two mandatory layers, one optional. Based on the Flutter team's official architecture guide.

```
UI Layer                          Data Layer
  View (Widget)                     Repository (single source of truth per data type)
  ViewModel (Notifier/Cubit)        Service (wraps external API/DB — no business logic)
```

Optional **Domain Layer** (use cases) only for large apps with shared cross-ViewModel logic.

### Layer rules

- **Views**: stateless rendering only. No business logic, no async, no API calls, no `BuildContext` leaking into ViewModels.
- **ViewModels**: one per View. Transform data for display, hold UI state, expose commands. No widget references, no navigation calls, no platform APIs.
- **Repositories**: single source of truth per data type. Abstract data sources, handle caching, offline-first. Repositories never know about other repositories.
- **Services**: thin wrappers around APIs/databases. No business logic — that belongs in ViewModels or use cases.

### Data flow (unidirectional)

```
User taps → View → ViewModel.command() → Repository → Service → API
                                                        ↓
View rebuilds ← ViewModel notifies ← Repository emits new state
```

State flows down, events flow up. Never the reverse.

### Generated API clients

When a project has an OpenAPI spec, generate the API client — never hand-write it:
- Use a Dart-native generator (e.g., Tonik, swagger_parser) that produces clean Dart code
- The generated client IS the Service layer — create Repositories that wrap it
- Generated code goes in a `packages/` directory, treated as immutable
- Wire into the project's `just gen` pipeline so it regenerates with the spec
- Check the project's `CLAUDE.md` for the specific generator and pipeline commands

### Official design patterns

- **Command pattern** — wraps ViewModel methods, handles running/complete/error states
- **Result<T>** — return type instead of throwing exceptions (explicit error handling)
- **Repository pattern** — offline-first, abstract data sources, caching
- **Optimistic state** — update UI immediately, rollback on failure

---

## 2. Project Structure — Feature-First

Organize around what the user does, not what the code is.

```
lib/
  src/
    common_widgets/           # Truly shared UI components
    constants/                # App-wide constants
    exceptions/               # Error types
    features/
      authentication/
        presentation/         # Widgets + ViewModels
        domain/               # Models
        data/                 # Repositories + Services + DTOs
      budgets/
        presentation/
        domain/
        data/
    localization/
    routing/
    utils/
```

A feature is **what the user does** (authenticate, manage_budgets), not a screen name. Each feature owns its own layers.

---

## 3. State Management — Riverpod

Riverpod is the modern standard. Use `flutter_riverpod` + `riverpod_generator`.

### Core rules

- `ref.watch` inside `build()` — reactive, triggers rebuild
- `ref.read` outside `build()` — one-shot, for event handlers
- **Never cross these** — `ref.read` in `build()` causes stale data, `ref.watch` outside `build()` causes unnecessary rebuilds
- All generated providers `autoDispose` by default — prevents memory leaks
- Initialize state in `build()`, not in Notifier constructors
- No public properties on Notifiers — bypasses tracking
- No side effects in Notifier `build()`
- No `ref` usage after async gaps without checking `mounted`
- No unstable provider arguments (lists, functions, non-const objects)

### Provider selection

Let `riverpod_generator` choose automatically via annotations:

```dart
@riverpod
class BudgetList extends _$BudgetList {
  @override
  Future<List<Budget>> build() async {
    return ref.read(budgetRepositoryProvider).getAll();
  }
}
```

### When to use BLoC instead

Only if regulatory compliance demands event-driven audit trails (financial apps with strict logging requirements). The explicit Event → State pipeline is heavier but provides maximum traceability.

---

## 4. Navigation — go_router

Official Flutter team recommendation. Declarative, URL-based, supports deep linking.

```dart
final router = GoRouter(
  routes: [
    GoRoute(path: '/', builder: (_, __) => const HomeScreen()),
    GoRoute(path: '/budgets/:id', builder: (_, state) => BudgetScreen(id: state.pathParameters['id']!)),
    StatefulShellRoute.indexedStack(
      builder: (_, __, child) => MainShell(child: child),
      branches: [
        StatefulShellBranch(routes: [/* dashboard routes */]),
        StatefulShellBranch(routes: [/* assets routes */]),
        StatefulShellBranch(routes: [/* settings routes */]),
      ],
    ),
  ],
  redirect: (context, state) {
    final isLoggedIn = /* check auth state */;
    if (!isLoggedIn) return '/login';
    return null;
  },
);
```

### Key patterns

- **Auth guards**: `redirect` parameter (must be synchronous — async auth checks need workarounds)
- **Bottom nav**: `StatefulShellRoute` with independent navigator stacks per tab
- **Deep linking**: define URL patterns, go_router handles `myapp://budgets/123` automatically
- **Type-safe params**: use `state.pathParameters['id']` with null checks

---

## 5. Models — Freezed

Immutable domain models with code generation. Required for Riverpod state correctness.

```dart
@freezed
class Budget with _$Budget {
  const factory Budget({
    required String id,
    required String name,
    required String limitAmount,  // BigDecimal as string — never double
    required String currency,
    required BudgetPeriod period,
  }) = _Budget;

  factory Budget.fromJson(Map<String, dynamic> json) => _$BudgetFromJson(json);
}
```

Generates: `copyWith`, `==`, `hashCode`, `toString`, JSON serialization, union types.

### Generated vs hand-written models

If the project generates models from an OpenAPI spec, use those directly.
Only create hand-written Freezed models for:
- Local-only domain objects (not in the API)
- Drift database companions (mapping generated API models to local storage)
- View-specific state objects

### Rules

- Run `dart run build_runner build` after model changes (or the project's equivalent `just` recipe)
- Never hand-edit `*.g.dart` or `*.freezed.dart` files
- Monetary values as `String` — never `double`. Match the backend's BigDecimal/Numeric contract.
- All domain models get Freezed. DTOs for API responses get `json_serializable` only (lighter).

---

## 6. Widget Composition

### Build method discipline

- Keep `build()` cheap — it is called frequently (every frame during animations)
- `const` constructors aggressively — 30-40% rebuild reduction
- Prefer `StatelessWidget` over helper methods for reusable UI
- Localize `setState()` to the smallest subtree possible
- Split widgets by **change pattern**, not just size — if two parts of a widget rebuild at different rates, extract the fast one

### Anti-patterns

- `Opacity` widget in animations → use `AnimatedOpacity` or `FadeInImage`
- Building large concrete child lists → use builder callbacks (`ListView.builder`)
- `saveLayer()` is extremely expensive → avoid `ShaderMask`, `ColorFilter` in animations
- Helper functions instead of widgets → lose framework optimizations (key diffing, const, rebuild isolation)
- Overriding `operator==` on Widgets → causes O(N^2) framework behavior

### Performance tools

- `RepaintBoundary` for frequently-updating components (20-30% paint time reduction)
- `ListView.builder` / `GridView.builder` for lazy loading (70-80% memory reduction for 100+ items)
- `Isolate.run()` or `compute()` for CPU-bound tasks (JSON parsing, heavy math)
- Frame budget: 16ms at 60Hz, 8ms at 120Hz
- **Always profile in release mode** — `flutter run --release`. Debug mode is 10x slower.

---

## 7. Theming — Material 3

M3 is the default since Flutter 3.16.

### Seed-based color system

```dart
ThemeData(
  useMaterial3: true,
  colorScheme: ColorScheme.fromSeed(
    seedColor: Colors.blue,
    brightness: Brightness.light,
  ),
)
```

- **Same seed color** for light and dark themes — Flutter generates harmonized palettes
- **Never override individual `ColorScheme` colors** unless you have a specific reason — breaks seed algorithm harmony
- Access colors via `Theme.of(context).colorScheme.primary`, never hardcode hex values

### Three-level override hierarchy

1. **ColorScheme** (seed) — recommended, generates everything
2. **Component theme** — `elevatedButtonTheme`, `cardTheme` for category-wide overrides
3. **Widget-level** — `ElevatedButton.styleFrom(...)` for one-offs

### Custom design tokens via ThemeExtension

For tokens that don't exist in Material 3 (spacing, brand colors):

```dart
@immutable
class AppSpacing extends ThemeExtension<AppSpacing> {
  final double small;
  final double medium;
  final double large;

  const AppSpacing({this.small = 8, this.medium = 16, this.large = 24});

  @override
  AppSpacing copyWith({double? small, double? medium, double? large}) =>
      AppSpacing(small: small ?? this.small, medium: medium ?? this.medium, large: large ?? this.large);

  @override
  AppSpacing lerp(AppSpacing? other, double t) => /* interpolation for animations */;
}
```

Register on `ThemeData(extensions: [AppSpacing()])`, consume via `Theme.of(context).extension<AppSpacing>()!`.

### Dark mode

```dart
MaterialApp(
  theme: lightTheme,
  darkTheme: darkTheme,
  themeMode: ThemeMode.system,  // auto-switch with OS
)
```

---

## 8. Testing

### Trophy-shaped test distribution

| Layer | Tool | Proportion | Purpose |
|---|---|---|---|
| Widget tests | `flutter_test` | ~50% | UI components, user interaction |
| Unit tests | `test` | ~30% | ViewModels, repositories, services |
| Golden tests | `alchemist` | ~10% | Visual regression for stable components |
| E2E | `patrol` | ~10% | Critical user journeys, native interactions |

### Principles

- **Fakes over mocks** (official recommendation) — write fake repositories with deterministic behavior
- **Push tests down** — if a widget test gives the same confidence as E2E, write the widget test
- **No duplication across layers** — higher-level failure without lower-level failure signals a missing lower test
- **Test the behavior, not the implementation** — pump, tap, verify text/widget presence

### Mocking

- **Mocktail** (no codegen, null-safe) — recommended for most projects
- **Mockito** (codegen, strict typing) — for large codebases with verification needs
- Create abstract repository interfaces to facilitate testing with fakes

### Widget test pattern

```dart
testWidgets('displays budget amount', (tester) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [budgetProvider.overrideWith(() => FakeBudgetNotifier())],
      child: const MaterialApp(home: BudgetScreen()),
    ),
  );

  expect(find.text('500.00 EUR'), findsOneWidget);
});
```

### Golden tests with Alchemist

For visual regression on stable, reusable components. Gate PRs on pass/fail. Run headless in CI.

### E2E with Patrol

Patrol handles native interactions that `integration_test` cannot: system dialogs, permissions, biometrics, cross-app testing.

---

## 9. Platform Channels

For native iOS/Android code integration (biometrics, push notifications, file system):

```dart
const platform = MethodChannel('com.example.app/native');

Future<String?> getBiometricType() async {
  try {
    return await platform.invokeMethod<String>('getBiometricType');
  } on PlatformException catch (e) {
    debugPrint('Platform channel error: ${e.message}');
    return null;
  }
}
```

- Always handle `PlatformException` — the native side may not implement the method
- Use `EventChannel` for streams (sensor data, location updates)
- Prefer existing plugins (`local_auth`, `firebase_messaging`) over custom channels

---

## 10. Code Generation Workflow

Flutter relies heavily on code generation. The build sequence matters.

```bash
# After model/provider changes
dart run build_runner build --delete-conflicting-outputs

# Watch mode during development
dart run build_runner watch --delete-conflicting-outputs
```

### Generated files (never hand-edit)

- `*.freezed.dart` — Freezed model implementations
- `*.g.dart` — JSON serialization + Riverpod providers
- `*.gen.dart` — other generators (theme_tailor, etc.)

Add to `.gitignore` or commit them — project choice, but be consistent. Committing avoids build_runner in CI; gitignoring keeps diffs clean.

---

## 11. Key Packages

| Category | Package | Notes |
|---|---|---|
| State | `flutter_riverpod` + `riverpod_generator` | Modern standard |
| Navigation | `go_router` | Official recommendation |
| Models | `freezed` + `json_serializable` | Immutable + JSON |
| Codegen runner | `build_runner` | Required for freezed/riverpod |
| HTTP | `dio` | Interceptors, retry, logging |
| Local storage | `drift` (SQL) or `shared_preferences` (KV) | Per use case |
| Linting | `flutter_lints` + `custom_lint` | Both recommended |
| Testing (mock) | `mocktail` | No codegen, null-safe |
| Testing (E2E) | `patrol` | Native interactions |
| Testing (golden) | `alchemist` | Visual regression |
| Theming codegen | `theme_tailor` | ThemeExtension boilerplate |

---

## 12. Anti-patterns Summary

| Anti-pattern | Why it fails | Fix |
|---|---|---|
| `ref.read` in `build()` | Stale data, misses updates | Use `ref.watch` |
| `ref.watch` outside `build()` | Unnecessary rebuilds | Use `ref.read` |
| Business logic in Views | Untestable, violates MVVM | Move to ViewModel |
| `double` for money | Precision loss | `String` end-to-end (BigDecimal on server) |
| Helper functions for reusable UI | Loses framework optimizations | Extract to `StatelessWidget` |
| Profiling in debug mode | 10x slower, misleading results | `flutter run --release` |
| `Opacity` in animations | Expensive `saveLayer` call | `AnimatedOpacity` |
| Repositories knowing each other | Circular deps, testing nightmare | Combine in ViewModel or use case |
| Logic in Notifier constructor | Runs before provider is tracked | Initialize in `build()` |
| `GetX` | Maintenance-mode, magic globals | Riverpod or BLoC |

---

## 13. Shared Resources

### Translations

When web and mobile share the same API, share translations too:
- Web locale files (JSON/i18next) are the source of truth
- Generate mobile ARB files from web JSON via a conversion script
- Wire into the project's build pipeline so translations stay in sync
- Never duplicate translation keys manually across platforms

### API Clients

When an OpenAPI spec exists:
- Generate clients for ALL platforms from the same spec
- The derivation chain flows: API code → OpenAPI spec → generated clients
- Check the project's `generated-code` rule for the specific pipeline
