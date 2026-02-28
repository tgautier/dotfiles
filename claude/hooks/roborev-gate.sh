#!/usr/bin/env bash
# PreToolUse hook: block git push and gh pr merge when roborev has unaddressed failures.
# Exit 2 = block with reason on stderr. Exit 0 = allow.

set -euo pipefail

# Extract the command from Bash tool input
COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null)
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

# Check for running reviews — wait for them first
RUNNING=$(roborev list 2>/dev/null | grep -c "running" || true)
if [ "$RUNNING" -gt 0 ]; then
  echo "BLOCK: Roborev reviews are still running. Run \`roborev list\` and \`roborev wait <job-id>\` before proceeding." >&2
  exit 2
fi

# Check for failed/unaddressed reviews
FAILED=$(roborev list 2>/dev/null | grep -c "failed\|error" || true)
if [ "$FAILED" -gt 0 ]; then
  echo "BLOCK: Roborev has unaddressed failures. Run \`roborev list\` to see findings, then \`roborev fix\` or \`roborev refine\` before proceeding." >&2
  exit 2
fi

exit 0
