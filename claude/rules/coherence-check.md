# Coherence Check

Mandatory evaluation protocol when questioned about code — prevents sunk-cost defense and ensures consistency with the rest of the codebase.

## When to run

- The user questions whether code you wrote should exist
- You're deciding whether to keep, modify, or remove something you created
- You're about to argue for keeping code — stop and run this first

## Protocol

1. **Find precedent** — grep the codebase for the same pattern. How many other places do this?
2. **Present evidence** — show the grep results to the user
3. **Recommend, don't decide** — state your recommendation with reasoning, then ask the user. Never autonomously delete or keep without confirmation
4. **Never generate "reasons to keep" before completing the search**

## Rules

- Never defend code because you wrote it — evaluate as if reviewing someone else's work
- "It's cheap" and "it's harmless" are not arguments for inconsistency
- One-off patterns that no other entity follows are a code smell, not a feature
- If a pattern is worth having, it's worth having everywhere. If it's not worth having everywhere, it's not worth having here

## Anti-patterns

- Generating technical justifications before checking precedent
- Arguing "it catches a real bug class" without checking if the same bug class is tested elsewhere
- Treating "I already wrote it" as evidence it should stay
- Rationalizing inconsistency instead of resolving it
