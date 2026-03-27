# Flutter Production Patterns — Research Findings

Research for creating Claude Code skills and rules for Flutter native app development.

## Summary

Clear consensus across authoritative sources (Flutter team official guide, Very Good Ventures, Andrea Bizzotto, DCM):

| Area | Recommendation | Confidence |
|---|---|---|
| Architecture | MVVM with 2-3 layers (official guide) | High — Tier 1 |
| Project structure | Feature-first (vertical slicing) | High — Tier 1+2 |
| State management | Riverpod 3 (modern default), BLoC (enterprise) | High — Tier 1+2 |
| Navigation | go_router (official recommendation) | High — Tier 1 |
| Models | Freezed + json_serializable (codegen) | High — Tier 1+2 |
| Testing | Trophy-shaped: widget tests dominant, Patrol E2E | High — Tier 1+2 |
| Performance | const constructors, lazy builders, Isolates | High — Tier 1 |
| CI/CD | GitHub Actions + Fastlane (iOS) | Medium — Tier 2 |
| Design system | Material 3 seed colors + ThemeExtension | High — Tier 1 |

## Stack

### Core
- **Framework:** Flutter 3.x / Dart 3.x
- **Architecture:** MVVM (View + ViewModel + Repository + Service)
- **State:** `flutter_riverpod` + `riverpod_generator` (modern) or `flutter_bloc` (enterprise)
- **Navigation:** `go_router` (official, declarative, URL-based)
- **Models:** `freezed` + `json_serializable` + `build_runner`
- **HTTP:** `dio` (interceptors, retry) or `http` (simpler)

### Testing
- **Unit/Widget:** `flutter_test` + `mocktail`
- **Golden:** `alchemist` (replaced `golden_toolkit`)
- **E2E:** `patrol` (handles native dialogs, permissions)
- **Coverage:** enforced in CI with `flutter test --coverage`

### CI/CD
- **Pipeline:** GitHub Actions (3 workflows: PR gate, Android release, iOS release)
- **iOS signing:** Fastlane `match` (certificate management)
- **Quality gate:** `dart format --set-exit-if-changed . && flutter analyze --fatal-warnings && flutter test --coverage`

### Design
- **Theme:** Material 3 with `ColorScheme.fromSeed()`
- **Custom tokens:** `ThemeExtension<T>` for spacing, brand colors
- **Codegen:** `theme_tailor` for ThemeExtension boilerplate

## Existing Patterns (from official architecture guide)

### MVVM layers

```
UI Layer                    Data Layer
  View (Widget)              Repository (single source of truth per data type)
  ViewModel (ChangeNotifier)  Service (wraps external API/DB)
```

- **Views:** stateless rendering, no business logic, no async
- **ViewModels:** one per View, transforms data for display, holds UI state
- **Repositories:** single source of truth, offline-first caching, abstracts data sources
- **Services:** thin wrappers around APIs/DBs, no business logic

Optional **Domain Layer** (use cases/interactors) only for large apps with shared cross-ViewModel logic.

### Data flow

```
User taps → View captures event → ViewModel.command() → Repository.update() → Service.post()
                                                                    ↓
View rebuilds ← ViewModel notifies ← Repository emits new state ← API response
```

Unidirectional: state flows down, events flow up.

### Official design patterns

1. **Command pattern** — wraps ViewModel methods, handles running/complete/error states
2. **Result<T>** — return type instead of throwing exceptions (explicit error handling)
3. **Repository pattern** — offline-first, abstract data sources, caching
4. **Optimistic state** — update UI immediately, rollback on failure

## Integration Points

### Riverpod 3 key patterns

- All providers `autoDispose` by default (prevents memory leaks)
- `riverpod_generator` determines optimal provider type automatically
- `ref.watch` in `build()`, `ref.read` outside `build()` (never cross these)
- Native offline persistence, Mutations API, automatic retry with backoff

### go_router key patterns

- Declarative route tree with `GoRoute` and `StatefulShellRoute`
- Auth guards via `redirect` parameter (must be synchronous)
- Deep linking automatic from URL patterns
- `StatefulShellRoute` for bottom-nav with independent navigator stacks per tab

### Freezed key patterns

```dart
@freezed
class User with _$User {
  const factory User({
    required String id,
    required String name,
    String? email,
  }) = _User;

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
}
```

Generates: `copyWith`, `==`, `hashCode`, `toString`, JSON serialization, union types.

## Gotchas

### State management
- `ref.read` inside `build()` — causes stale data (use `ref.watch`)
- `ref.watch` outside `build()` — causes unnecessary rebuilds (use `ref.read`)
- Using `ref` after async gaps without checking `mounted`
- Logic in Notifier constructors — initialize in `build()`
- Public properties on Notifiers — bypasses tracking
- Unstable provider arguments (lists, functions, non-const objects)

### Performance
- `Opacity` widget in animations — use `AnimatedOpacity` instead
- `saveLayer()` is extremely expensive (avoid `ShaderMask`, `ColorFilter` in animations)
- Building large concrete child lists — use builder callbacks (`ListView.builder`)
- Profiling in debug mode — always profile in release (`flutter run --release`)
- `operator==` on Widgets — causes O(N^2) framework behavior
- Intrinsic layout passes — use fixed sizes or anchor-cell pattern
- Frame budget: 16ms at 60Hz, 8ms at 120Hz

### Navigation
- go_router `redirect` must be synchronous — async auth checks need workarounds
- Navigator stack implicit behavior in large route trees can be hard to debug

### Design
- Overriding individual `ColorScheme` colors breaks seed algorithm harmony
- Different seed colors for light/dark themes — use the same seed, let Flutter generate both palettes

### CI/CD
- macOS GitHub Actions runners cost 10x Linux minutes
- iOS code signing requires temporary keychain setup in CI
- Never commit keystores or certificates to repository

## Testing

### Trophy-shaped test distribution

| Layer | Proportion | Rationale |
|---|---|---|
| Widget tests | ~50% | UI is Flutter's core complexity; test user-facing behavior |
| Unit tests | ~30% | Services, repositories, ViewModels — pure logic |
| Golden tests | ~10% | Visual regression for stable, reusable components |
| E2E (Patrol) | ~10% | Critical user journeys only |

### Key principles
- **Fakes over mocks** (official recommendation) — write fake repositories with deterministic behavior
- **Widget test = user interaction simulation** — pump, tap, verify text/widget presence
- **Golden tests = visual regression** — gate PRs on pass/fail, run headless in CI
- **Patrol for native interactions** — permission dialogs, biometrics, cross-app testing

### Mocking
- **Mocktail** (no codegen, null-safe) — recommended for most projects
- **Mockito** (codegen, strict typing) — for large codebases with verification needs
- Create abstract repository interfaces to facilitate testing with fakes

## Open Questions

1. **Riverpod vs BLoC** — depends on team background and audit requirements. Riverpod for most apps, BLoC only if regulatory compliance demands event-driven audit trails.
2. **Drift vs sqflite** — Drift (reactive, type-safe SQL) is the modern choice for complex local storage; sqflite for simpler key-value + basic queries.
3. **Patrol adoption** — still maturing; `integration_test` is the fallback if Patrol doesn't cover your platform.
4. **Signals** — emerging alternative (v6.0) for high-frequency UI updates (trading dashboards). Too new for production recommendation.

## Sources

### Tier 1 — Official documentation
- [Flutter Architecture Guide](https://docs.flutter.dev/app-architecture) (2024)
- [Flutter Architecture Concepts](https://docs.flutter.dev/app-architecture/concepts)
- [Flutter Architecture Recommendations](https://docs.flutter.dev/app-architecture/recommendations)
- [Flutter Performance Best Practices](https://docs.flutter.dev/perf/best-practices)
- [Flutter Testing Cookbook](https://docs.flutter.dev/cookbook/testing)
- [Flutter Themes](https://docs.flutter.dev/cookbook/design/themes)
- [Material 3 Default Change](https://docs.flutter.dev/release/breaking-changes/material-3-default)
- [go_router (Official)](https://pub.dev/packages/go_router)

### Tier 2 — Domain experts
- [Andrea Bizzotto — Flutter App Architecture with Riverpod](https://codewithandrea.com/articles/flutter-app-architecture-riverpod-introduction/)
- [Andrea Bizzotto — Feature-first Project Structure](https://codewithandrea.com/articles/flutter-project-structure/)
- [Christian Findlay — Mastering Material Design 3](https://www.christianfindlay.com/blog/flutter-mastering-material-design3)
- [Very Good Ventures — Core Template](https://cli.vgv.dev/docs/templates/core)
- [DCM — Riverpod Best Practices and Lint Rules](https://dcm.dev/blog/2026/03/25/inside-riverpod-source-code-guide-dcm-rules)
- [8th Light — Is GoRouter Still The Best Choice?](https://8thlight.com/insights/flutter-navigation-is-gorouter-still-the-best-choice)
- [FreeCodeCamp — Production Flutter CI/CD Pipeline](https://www.freecodecamp.org/news/how-to-build-a-production-ready-flutter-ci-cd-pipeline-with-github-actions-quality-gates-environments-and-store-deployment/)
- [LeanCode — Patrol E2E Framework](https://patrol.leancode.co/)

### Tier 5 — Community (verified against higher tiers)
- [Foresight Mobile — State Management Libraries 2026](https://foresightmobile.com/blog/best-flutter-state-management)
- [F22 Labs — Performance Optimization Techniques](https://www.f22labs.com/blogs/13-flutter-performance-optimization-techniques-in-2025/)
