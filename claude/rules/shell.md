# Shell Compatibility

## zsh `!` corruption

zsh history expansion corrupts `!` to `\!` even inside single quotes when commands pass through shell wrappers (including the Claude Code Bash tool). This affects **all** shell contexts — not just commands, but also file content written via Bash heredocs, echo, or piped writes.

### In jq filters

Never use `!=` in jq filters — use `== ... | not`:

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

### In file content

Files written through the Bash tool (heredocs, `cat >`, `echo >>`) will have `!` silently corrupted to `\!`. This breaks code examples containing `!==`, `!important`, `!mounted`, etc.

**Always use the Write or Edit tools** for file creation and modification — they bypass the shell entirely. Reserve the Bash tool for commands that must run in a shell (git, just, docker, etc.), never for writing file content.

If you must write files via Bash (e.g., outside the sandbox allowlist), verify the output:

```sh
# After writing, check for corruption
grep '\\!' path/to/file.md
```
