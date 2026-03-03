#!/usr/bin/env bash
# Cross-platform notification when Claude Code stops.
# macOS: osascript, Linux: notify-send, otherwise: silent no-op.

TITLE="Claude Code"
MESSAGE="Task finished"

if command -v osascript &>/dev/null; then
  osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\"" 2>/dev/null
elif command -v notify-send &>/dev/null; then
  notify-send "$TITLE" "$MESSAGE" 2>/dev/null
fi
