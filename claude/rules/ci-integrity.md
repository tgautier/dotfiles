# CI Integrity

CI must reflect reality. Green means it works — no exceptions.

## Rules

- Never use `continue-on-error: true` to silence failing tests or checks
- Never append `|| true`, `|| exit 0`, or `set +e` to test/lint/check commands
- Never skip, disable, or comment out test suites to work around missing infrastructure
- Never mark a failing CI step as non-blocking to "unblock the PR"
- If tests cannot run (missing DB, missing service, auth not configured), fix the infrastructure — do not hide the failure
- If a pre-existing test fails, it is still a blocker — investigate before proceeding

## When tests legitimately cannot run

- Add the infrastructure (Docker service, test fixture, config) so they can run
- If the fix is out of scope, create a GitHub issue and inform the user — do not merge with broken tests
- Temporarily removing a test suite requires explicit user approval and a tracking issue

## Audit entries

When auditing CI configuration, flag:

- `continue-on-error` on any test/lint/check step
- `|| true` or `|| exit 0` after test commands
- `if: false` on test/check steps (disabling them)
- `if: always()` on test/check steps (forcing them to "pass" regardless of prior failures — legitimate only on artifact-upload steps)
- `set +e` in shell blocks that run tests
- Commented-out test steps with no tracking issue
