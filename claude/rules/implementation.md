# Implementation

## Execution

- When implementing from a plan, mark each task complete in the plan document as you go
- Run verification (typecheck, lint, tests) continuously — after every edit, not batched
- Do not add unnecessary comments, jsdocs, or type annotations to code you didn't change

## Corrections during implementation

- Keep corrections terse — single-sentence when context already exists
- Reference existing code for consistency: "match the pattern in X"
- If an approach isn't working after one fix attempt, revert and re-plan rather than layering patches

## Quality gates

- Never stop mid-implementation with tasks unchecked in the plan
- If blocked, switch back to plan mode and re-plan rather than guessing
