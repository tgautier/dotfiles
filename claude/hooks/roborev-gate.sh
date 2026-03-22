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

# Determine the branch to check.
# For `gh pr merge`, resolve the PR's head branch — the command can be run from any local branch.
# For `git push`, parse the refspec to find the target branch.
CURRENT_BRANCH=""
case "$COMMAND" in
  gh\ pr\ merge*)
    # Extract PR selector (number/URL/branch) — first non-flag token after "gh pr merge".
    # Flags (--squash, --delete-branch, etc.) are stripped; gh pr view only needs the selector.
    PR_SELECTOR=$(echo "$COMMAND" | sed 's/^gh pr merge//' | tr ' ' '\n' | grep -vE '^-|^$' | head -1) || true
    if [ -n "$PR_SELECTOR" ]; then
      CURRENT_BRANCH=$(gh pr view "$PR_SELECTOR" --json headRefName --jq '.headRefName' 2>/dev/null) || {
        echo "BLOCK: Could not resolve PR head branch from '$PR_SELECTOR'. Check \`gh auth status\`." >&2
        exit 2
      }
    else
      # No selector — gh pr merge targets the current branch's PR
      CURRENT_BRANCH=$(gh pr view --json headRefName --jq '.headRefName' 2>/dev/null) || {
        echo "BLOCK: Could not resolve PR for current branch. Check \`gh auth status\`." >&2
        exit 2
      }
    fi
    ;;
  git\ push*--delete*|git\ push*-d\ *)
    # Branch deletion — nothing to gate
    exit 0
    ;;
  git\ push*)
    # Parse the push target branch from the refspec.
    # Forms: `git push`, `git push origin`, `git push origin branch`,
    #        `git push origin HEAD:branch`, `git push -u origin branch`
    # Extract the last non-flag argument after stripping `git push`.
    PUSH_TARGET=$(echo "$COMMAND" | sed 's/^git push//' | tr ' ' '\n' | grep -vE '^-|^$' | tail -1) || true
    if [ -z "$PUSH_TARGET" ]; then
      # No args — pushing current branch
      CURRENT_BRANCH=$(git branch --show-current 2>/dev/null) || exit 0
    elif echo "$PUSH_TARGET" | grep -q '^:'; then
      # Delete-by-refspec (:branch) — nothing to gate
      exit 0
    elif echo "$PUSH_TARGET" | grep -q ':'; then
      # src:dst refspec — use the destination (after colon), resolve HEAD
      DST=$(echo "$PUSH_TARGET" | sed 's/.*://')
      CURRENT_BRANCH=$([ "$DST" = "HEAD" ] && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "$DST")
    elif git remote 2>/dev/null | grep -qx "$PUSH_TARGET"; then
      # Token is a remote name, not a branch — fall back to current branch
      CURRENT_BRANCH=$(git branch --show-current 2>/dev/null) || exit 0
    elif [ "$PUSH_TARGET" = "HEAD" ]; then
      # Resolve HEAD to actual branch name
      CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
    else
      # Explicit branch name
      CURRENT_BRANCH="$PUSH_TARGET"
    fi
    ;;
esac
[ -z "$CURRENT_BRANCH" ] && exit 0  # detached HEAD — nothing to gate

# Skip excluded branches (e.g., main) — read from .roborev.toml
# Expects a single-line TOML array: excluded_branches = ["main", "wip"]
EXCLUDED=$(sed -n 's/^excluded_branches *= *\[//p' .roborev.toml | tr -d '"]' | tr ',' '\n' | tr -d ' ') || true
for branch in $EXCLUDED; do
  [ "$CURRENT_BRANCH" = "$branch" ] && exit 0
done

# Query roborev for the resolved branch — explicit --branch avoids relying on the local branch default.
REVIEW_JSON=$(roborev list --json --branch "$CURRENT_BRANCH") || {
  echo "BLOCK: \`roborev list --json\` failed — cannot verify review status. Start the daemon with \`roborev daemon start\`." >&2
  exit 2
}

BRANCH_COUNT=$(echo "$REVIEW_JSON" | jq 'length' 2>/dev/null) || {
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
BLOCKING=$(echo "$REVIEW_JSON" | jq '[.[] | select((.status == "done" or .status == "failed") | not)] | length' 2>/dev/null) || {
  echo "BLOCK: Failed to parse roborev JSON output." >&2
  exit 2
}

if [ "$BLOCKING" -gt 0 ]; then
  STATUSES=$(echo "$REVIEW_JSON" | jq -r '[.[] | select((.status == "done" or .status == "failed") | not) | "\(.agent): \(.status)"] | join(", ")' 2>/dev/null) || true
  echo "BLOCK: $BLOCKING roborev review(s) not complete: $STATUSES. Run \`roborev list\` to check status." >&2
  exit 2
fi

# At least one review must have completed successfully — all failed means zero coverage
DONE_COUNT=$(echo "$REVIEW_JSON" | jq '[.[] | select(.status == "done")] | length' 2>/dev/null) || {
  echo "BLOCK: Failed to parse roborev JSON output." >&2
  exit 2
}

if [ "$DONE_COUNT" -eq 0 ]; then
  echo "BLOCK: All roborev reviews failed — no actual review coverage. Re-run with \`roborev review --branch\`." >&2
  exit 2
fi

exit 0
