#!/usr/bin/env bash
# PostToolUse hook: after reading roborev findings, remind to use AskUserQuestion.
# Fires after any Bash command that runs `roborev show`.
# Exit 0 with message on stdout = non-blocking reminder injected into context.

set -euo pipefail

COMMAND=$(echo "${TOOL_INPUT:-}" | jq -r '.command // empty' 2>/dev/null) || true
[ -z "$COMMAND" ] && exit 0

case "$COMMAND" in
  roborev\ show*)
    echo "REMINDER: Follow /roborev interactive mode. Present each finding individually via AskUserQuestion with your recommendation. Never auto-dismiss or batch-resolve. The user decides: Fix, Dismiss, Discuss, or Skip."
    ;;
esac

exit 0
