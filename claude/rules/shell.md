# Shell Compatibility

## jq and zsh

**Never use `!=` in jq filters.** zsh history expansion corrupts `!` to `\!` even inside single quotes when the command passes through shell wrappers (including the Claude Code Bash tool). This causes silent jq parse failures — the filter errors out, variables stay empty, and loops run forever.

Use `== ... | not` instead:

```sh
# BROKEN — zsh corrupts != to \!=
jq 'select(.id != 5)'

# CORRECT — works in all shells
jq 'select((.id == 5) | not)'
```

This also applies to `null` checks:

```sh
# BROKEN
jq 'select(.field != null)'

# CORRECT
jq 'select((.field == null) | not)'
```
