#!/usr/bin/env bash
# PreToolUse hook: block git push and gh pr merge when roborev has unaddressed failures.
# Exit 2 = block with reason on stderr. Exit 0 = allow.

set -eo pipefail

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

# Capture roborev output once; block if roborev itself fails
REVIEW_OUTPUT=$(roborev list 2>&1) || {
  echo "BLOCK: \`roborev list\` failed — cannot verify review status. Start the daemon with \`roborev daemon start\`." >&2
  exit 2
}

# Check for running reviews
RUNNING=$(echo "$REVIEW_OUTPUT" | grep -c "running" || true)
if [ "$RUNNING" -gt 0 ]; then
  echo "BLOCK: Roborev reviews are still running. Run \`roborev list\` to get the job ID, then \`roborev wait <id>\`." >&2
  exit 2
fi

# Check for failed/unaddressed reviews
FAILED=$(echo "$REVIEW_OUTPUT" | grep -c "failed\|error" || true)
if [ "$FAILED" -gt 0 ]; then
  echo "BLOCK: Roborev has unaddressed failures. Run \`roborev list\` to see findings, then \`roborev fix\` or \`roborev refine\`." >&2
  exit 2
fi

exit 0
