---
name: code-planning
description: |
  Planning discipline skill for structuring implementation plans.
  Covers: trade-off evaluation, task decomposition, scope management, risk identification,
  complexity signals, plan structure, and planning anti-patterns.
  Use when: designing implementation plans, evaluating competing approaches, decomposing
  features into tasks, or reviewing plan quality before implementation.
version: 1.0.0
date: 2026-02-22
user-invocable: true
---

# Code Planning

Methodology for structuring high-quality implementation plans. This skill governs *how to plan well* — evaluating trade-offs, decomposing work, managing scope, and identifying risks. A good plan eliminates ambiguity before code is written.

> **Scope boundary:** This skill covers plan *quality* — what makes a plan good. For related concerns:
> - Planning *process* (when to plan, annotation cycle, verification-first) → **plan-first rule** (`claude/rules/plan-first.md`)
> - Execution discipline (verification cadence, correction policy) → **implementation rule** (`claude/rules/implementation.md`)
> - Source evaluation for research that informs plans → **Code Research skill** (`/code-research`)
> - Domain-specific decisions are delegated to the relevant skill (see Trade-off Evaluation below)

---

## 1. Planning Philosophy

A plan is a contract between research and implementation. It translates findings into actionable tasks with clear verification criteria.

**Quality dimensions** — evaluate every plan against these, in priority order:

1. **Correctness** — does it solve the right problem? Does it address the root cause, not a symptom?
2. **Simplicity** — is it the minimal solution? Could anything be removed without losing the requested value?
3. **Robustness** — does it handle failure? What happens when inputs are invalid, services are down, or data is missing?
4. **Maintainability** — can it evolve? Will the next person understand the changes six months from now?

---

## 2. Trade-off Evaluation

When multiple approaches exist, structure the comparison rather than picking intuitively.

### Constraints identification

Before comparing approaches, identify what's non-negotiable:

- Standards compliance (RFCs, language specs, framework contracts)
- Existing patterns in the codebase (consistency beats novelty)
- Performance requirements (latency budgets, throughput targets)
- Team capability (patterns the team can maintain)

### Decision matrix

Compare approaches against these dimensions:

| Dimension | Question |
|-----------|----------|
| Correctness | Does it fully solve the problem? Any edge cases it misses? |
| Complexity | How many moving parts? How many files touched? |
| Performance | Does it meet latency/throughput requirements? |
| Operability | Can it be monitored, debugged, and rolled back? |
| Reversibility | How hard is it to undo if the approach is wrong? |

### Domain delegation

Defer domain-specific decisions to the relevant skill:

- API contract decisions → **API Design skill** (`/api-design`)
- Rust implementation patterns → **Rust skill** (`/rust`)
- TypeScript/React patterns → **TypeScript skill** (`/typescript`)
- Security posture → **Web Security skill** (`/web-security`)
- Source evaluation → **Code Research skill** (`/code-research`)

### Decision heuristics

- **Bias toward boring technology** — proven, well-understood approaches over novel ones unless the problem demands novelty
- **Reversibility as tiebreaker** — when two approaches are otherwise equal, pick the one that's easier to undo
- **Consistency over perfection** — match existing codebase patterns even if a "better" pattern exists elsewhere

---

## 3. Task Decomposition

How to break work into plan tasks.

### Atomic tasks

Each task changes one concern. A task that says "add endpoint and update frontend" is two tasks. Test: can you describe the task in one sentence without "and"?

### Dependency ordering

Structure tasks so each builds on the previous:

1. Data model / schema changes
2. Backend handlers / business logic
3. Frontend components / UI
4. Integration wiring
5. Tests alongside each layer (not batched at the end)

### Vertical slices over horizontal layers

Prefer "add asset creation end-to-end" over "add all models, then all handlers, then all frontend." Vertical slices are independently verifiable and shippable.

### File manifest per task

Every task lists the files it touches. If a file appears in more than 2 tasks, the decomposition is likely wrong — the tasks aren't properly separated by concern.

### Verification per task

Every task has a verification step: what command, test, or check proves it works? Tasks without verification are incomplete.

---

## 4. Scope Management

### Explicit exclusions

For every plan, state what's deliberately out of scope and why. Unstated scope is ambiguous scope.

### Scope creep signals

Watch for these during planning:

- "While we're here" additions
- Yak-shaving chains (need X, which needs Y, which needs Z)
- Premature abstractions ("let's make this configurable for later")
- Gold-plating ("it would be nice if...")

### Minimum viable change

What's the smallest set of changes that delivers the requested value? Start there. Additional scope requires explicit justification.

### Future work section

Capture deferred ideas in a "Future work" section rather than expanding the current plan. This acknowledges the idea without blocking the current task.

---

## 5. Risk Identification

### Breaking change detection

Does this change any:

- Public API contract (response shape, status codes, error format)?
- Database schema (column types, constraints, indexes)?
- Configuration format (env vars, config files, feature flags)?
- Cross-reference with the API Design skill for contract stability rules.

### Integration risk

How many systems does this touch? More systems = more risk. A change that only touches backend code is lower risk than one spanning backend + frontend + database + CI.

### Data migration risk

Does this require a schema change? If yes:

- Is the migration reversible?
- Can old and new code coexist during rollout?
- What's the rollback procedure if the migration fails?

### Rollback plan

Can this be reverted with a single revert commit, or does it require data migration, cache invalidation, or coordination across services?

---

## 6. Complexity Signals

When to re-scope or split:

| Signal | Threshold | Action |
|--------|-----------|--------|
| Task count | > 10 tasks | Consider splitting into multiple PRs |
| Files per task | > 5 files | Task is probably multiple tasks |
| Cross-layer changes | Data + API + frontend + tests | Plan each layer explicitly |
| Unknown unknowns | Research gaps ("no Tier 1-3 sources found") | Add a spike task before committing |

---

## 7. Plan Structure

The artifact format for a complete plan:

```markdown
# Plan: [title]

## Context
Why this change exists. Link to issue, conversation, or research.

## Approach
The chosen path. Why alternatives were rejected (brief).

## Tasks
- [ ] Task 1: [description]
  - Files: `path/to/file.rs`, `path/to/other.rs`
  - Verify: `just test`
- [ ] Task 2: [description]
  - Files: `path/to/file.ts`
  - Verify: `just check`

## Risks
[Breaking changes, migration concerns, integration points]

## Verification
[End-to-end proof it works — the final check after all tasks]

## Future work
[Deferred scope with rationale]
```

---

## 8. Anti-patterns

| Anti-pattern | Why it fails | Fix |
|-------------|-------------|-----|
| Plans without verification steps | No way to prove correctness | Every task gets a verification command |
| Monolithic tasks ("implement the feature") | Can't track progress, can't parallelize | Decompose into atomic tasks |
| Missing dependency ordering | Frontend before API exists, tests before code | Order: data model → handlers → frontend → tests |
| Scope without exclusions | Everything is implicitly in scope | State what's out and why |
| Novelty over boring technology | Unproven approaches carry hidden risk | Justify why proven approaches won't work |
| Ignoring project-local rules | Plan violates codebase conventions | Read `.claude/rules/*.md` and match existing patterns |
| Planning without reading code first | Plan based on assumptions, not reality | Research first (plan-first rule) |
| Batching all tests to the end | Errors compound, root cause is obscured | Verify after each task |
| Horizontal decomposition | "All models, then all handlers" prevents incremental verification | Use vertical slices |
