#!/usr/bin/env bash
# PreToolUse hook on Edit/Write: emits a reminder when the target path
# matches a file-pattern trigger in ~/.claude/rules/skill-triggers.md.
#
# Keep the pattern list in sync with the "File-pattern triggers" table in
# skill-triggers.md.

set -euo pipefail

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat 2>/dev/null) || exit 0
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
[ -z "$file_path" ] && exit 0

base=$(basename "$file_path")
matched=""

# Each rule below is independent — multiple skills can match a single path.
[[ "$base" == "Justfile" || "$base" == "justfile" || "$base" == *.just ]] && matched+=" /just"
[[ "$base" == "CLAUDE.md" ]] && matched+=" /claude-authoring"
[[ "$base" == *.md ]] && matched+=" /markdown"
[[ "$file_path" == */.claude/* || "$file_path" == */claude/* || "$file_path" == */memory/* ]] && matched+=" /claude-authoring"
[[ "$file_path" == */docs/* ]] && matched+=" /documentation"
[[ "$base" == "Cargo.toml" || "$base" == *.rs ]] && matched+=" /rust"
[[ "$base" == *.tsx || "$base" == *.jsx ]] && matched+=" /react"
[[ "$base" == "tsconfig.json" || "$base" == *.ts || "$base" == *.mts || "$base" == *.cts ]] && matched+=" /typescript"
[[ "$base" == *.css || "$base" == tailwind.config.* ]] && matched+=" /css-responsive"
[[ "$base" == *.ex || "$base" == *.exs ]] && matched+=" /phoenix"
[[ "$base" == *.dart || "$base" == "pubspec.yaml" || "$base" == "pubspec.lock" ]] && matched+=" /flutter"
[[ "$base" == "openapi.yaml" || "$base" == "openapi.yml" || "$base" == *.openapi.yaml || "$base" == *.openapi.yml ]] && matched+=" /api-design"

[ -z "$matched" ] && exit 0

# `|| exit 0` guards: under `set -euo pipefail`, any unexpected failure in the
# pipeline or `jq -n` would propagate as exit 1, which for a PreToolUse hook is
# unspecified and could block edits. Degrade gracefully to "allow" instead.
unique=$(echo "$matched" | tr ' ' '\n' | awk 'NF && !seen[$0]++' | tr '\n' ' ' | sed 's/ *$//') || exit 0

msg="[skill-trigger] About to modify \`$file_path\`. Per ~/.claude/rules/skill-triggers.md (File-pattern triggers), load before continuing if not already loaded: $unique"

# PreToolUse stdout is not injected into context — emit JSON with
# hookSpecificOutput.additionalContext so the model actually sees the reminder.
jq -n --arg msg "$msg" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    additionalContext: $msg
  }
}' || exit 0
exit 0
