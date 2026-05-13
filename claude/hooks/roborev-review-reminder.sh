#!/usr/bin/env bash
# PostToolUse hook: after reading roborev findings, remind to use AskUserQuestion.
# Fires after any Bash command that runs `roborev show`.
# Claude Code passes the tool payload as JSON on stdin (the field path is
# .tool_input.command). The reminder is injected via
# hookSpecificOutput.additionalContext — plain stdout is not reliably surfaced.

set -euo pipefail

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat 2>/dev/null) || exit 0
COMMAND=$(echo "$input" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
[ -z "$COMMAND" ] && exit 0

case "$COMMAND" in
  roborev\ show*)
    msg="REMINDER: Follow /roborev interactive mode. Present each finding individually via AskUserQuestion with your recommendation. Never auto-dismiss or batch-resolve. The user decides: Fix, Dismiss, Discuss, or Skip."
    jq -n --arg msg "$msg" '{ hookSpecificOutput: { hookEventName: "PostToolUse", additionalContext: $msg } }' || exit 0
    ;;
esac

exit 0
