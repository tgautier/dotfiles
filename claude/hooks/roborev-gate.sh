#!/usr/bin/env bash
# PreToolUse hook: block git push and gh pr merge when roborev reviews are missing or in progress.
# Exit 2 = block with reason on stderr. Exit 0 = allow.
#
# Roborev statuses: queued, running, done, failed.
#
# Allows through ONLY when:
# - At least one review is "done" (real review coverage required)
# - All remaining reviews are "done" or "failed"
#
# Blocks on: missing reviews, zero "done" reviews, running, queued, etc.

set -euo pipefail

# Skip early if dependencies are missing
command -v jq >/dev/null 2>&1 || exit 0
command -v roborev >/dev/null 2>&1 || exit 0

# Extract the command from Bash tool input (|| true: invalid/missing JSON → empty command → exit 0)
COMMAND=$(echo "${TOOL_INPUT:-}" | jq -r '.command // empty' 2>/dev/null) || true
[ -z "$COMMAND" ] && exit 0

# Only gate push and merge commands
case "$COMMAND" in
  git\ push*|gh\ pr\ merge*)
    ;;
  *)
    exit 0
    ;;
esac

# Skip if no .roborev.toml in current repo
[ -f .roborev.toml ] || exit 0

# Query roborev via JSON for structured status detection.
# Verified: `roborev list --json` exits 0 with `[]` when no reviews exist.
REVIEW_JSON=$(roborev list --json) || {
  echo "BLOCK: \`roborev list --json\` failed — cannot verify review status. Start the daemon with \`roborev daemon start\`." >&2
  exit 2
}

# Determine the branch to check.
# For `gh pr merge`, resolve the PR's head branch — the command can be run from any local branch.
# For `git push`, use the current local branch.
case "$COMMAND" in
  gh\ pr\ merge*)
    # Extract PR number from command (e.g., "gh pr merge 146 --squash")
    PR_NUMBER=$(echo "$COMMAND" | sed -n 's/gh pr merge *\([0-9]*\).*/\1/p')
    if [ -n "$PR_NUMBER" ]; then
      CURRENT_BRANCH=$(gh pr view "$PR_NUMBER" --json headRefName --jq '.headRefName' 2>/dev/null) || exit 0
    else
      CURRENT_BRANCH=$(git branch --show-current 2>/dev/null) || exit 0
    fi
    ;;
  *)
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null) || exit 0
    ;;
esac
[ -z "$CURRENT_BRANCH" ] && exit 0  # detached HEAD or unresolvable — nothing to gate

# Skip excluded branches (e.g., main) — read from .roborev.toml
if command -v toml >/dev/null 2>&1; then
  EXCLUDED=$(toml get .roborev.toml excluded_branches 2>/dev/null) || true
else
  # Fallback: parse simple TOML array with sed
  EXCLUDED=$(sed -n 's/^excluded_branches *= *\[//p' .roborev.toml | tr -d '"]' | tr ',' '\n' | tr -d ' ') || true
fi
for branch in $EXCLUDED; do
  [ "$CURRENT_BRANCH" = "$branch" ] && exit 0
done

# Filter to reviews for the current branch
BRANCH_REVIEWS=$(echo "$REVIEW_JSON" | jq --arg b "$CURRENT_BRANCH" '[.[] | select(.branch == $b)]' 2>/dev/null) || {
  echo "BLOCK: Failed to parse roborev JSON output." >&2
  exit 2
}

BRANCH_COUNT=$(echo "$BRANCH_REVIEWS" | jq 'length' 2>/dev/null) || {
  echo "BLOCK: Failed to parse roborev JSON output." >&2
  exit 2
}

# Block if current branch has no reviews at all (first push without roborev)
if [ "$BRANCH_COUNT" -eq 0 ]; then
  echo "BLOCK: No roborev reviews found for branch '$CURRENT_BRANCH'. Run \`roborev review --branch\` before pushing." >&2
  exit 2
fi

# Check every review on this branch — only "done" and "failed" are terminal.
# "failed" = infrastructure failure (agent crashed, no review produced) — not actionable.
# Everything else (running, queued) blocks.
BLOCKING=$(echo "$BRANCH_REVIEWS" | jq '[.[] | select(.status == "done" or .status == "failed" | not)] | length' 2>/dev/null) || {
  echo "BLOCK: Failed to parse roborev JSON output." >&2
  exit 2
}

if [ "$BLOCKING" -gt 0 ]; then
  STATUSES=$(echo "$BRANCH_REVIEWS" | jq -r '[.[] | select(.status == "done" or .status == "failed" | not) | "\(.agent): \(.status)"] | join(", ")' 2>/dev/null) || true
  echo "BLOCK: $BLOCKING roborev review(s) not complete: $STATUSES. Run \`roborev list\` to check status." >&2
  exit 2
fi

# At least one review must have completed successfully — all failed means zero coverage
DONE_COUNT=$(echo "$BRANCH_REVIEWS" | jq '[.[] | select(.status == "done")] | length' 2>/dev/null) || {
  echo "BLOCK: Failed to parse roborev JSON output." >&2
  exit 2
}

if [ "$DONE_COUNT" -eq 0 ]; then
  echo "BLOCK: All roborev reviews failed — no actual review coverage. Re-run with \`roborev review --branch\`." >&2
  exit 2
fi

exit 0
