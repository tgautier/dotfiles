#!/usr/bin/env bash
# PreToolUse hook: block git push and gh pr merge when roborev reviews are in progress.
# Exit 2 = block with reason on stderr. Exit 0 = allow.
#
# Only blocks on "running" reviews (wait for completion). Does NOT block on:
# - "failed" jobs (infrastructure failure — agent crashed, no review produced)
# - "done" jobs (completed — findings handled by roborev fix/refine workflow)

set -euo pipefail

# Extract the command from Bash tool input
COMMAND=$(echo "${TOOL_INPUT:-}" | jq -r '.command // empty' 2>/dev/null)
[ -z "$COMMAND" ] && exit 0

# Only gate push and merge commands
case "$COMMAND" in
  git\ push*|gh\ pr\ merge*)
    ;;
  *)
    exit 0
    ;;
esac

# Skip if roborev is not installed
command -v roborev >/dev/null 2>&1 || exit 0

# Skip if no .roborev.toml in current repo
[ -f .roborev.toml ] || exit 0

# Query roborev via JSON for structured status detection.
# Verified: `roborev list --json` exits 0 with `[]` when no reviews exist.
REVIEW_JSON=$(roborev list --json 2>&1) || {
  echo "BLOCK: \`roborev list --json\` failed — cannot verify review status. Start the daemon with \`roborev daemon start\`." >&2
  exit 2
}

# Count running reviews via jq — structured check avoids false positives from text grep
RUNNING_COUNT=$(echo "$REVIEW_JSON" | jq '[.[] | select(.status == "running")] | length' 2>/dev/null) || {
  echo "BLOCK: Failed to parse roborev JSON output." >&2
  exit 2
}

if [ "$RUNNING_COUNT" -gt 0 ]; then
  echo "BLOCK: $RUNNING_COUNT roborev review(s) still running. Run \`roborev list\` to check status, then \`roborev wait <id>\` or wait for completion." >&2
  exit 2
fi

exit 0
