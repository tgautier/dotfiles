# Precompile the completion dump so the next login sources the compiled
# form. The .zwc must be compiled from the real file in place: zsh only
# uses ~/.zcompdump.zwc when it embeds that exact path, so a temp-copy
# compile would be silently rejected.
#
# Serialize with a non-blocking flock. Multiple login shells starting
# together (tmux panes, session restore) would otherwise race inside
# zcompile's unlink()+open(O_CREAT, 0444) on the shared .zwc, and the loser
# aborts with "can't write zwc file" — a spurious error that leaks into the
# interactive session. The flock is fd-based and auto-releases when this
# background shell exits, so no stale lock can wedge future recompiles.
{
  zcompdump="${HOME}/.zcompdump"
  if [[ -s "$zcompdump" && (! -s "${zcompdump}.zwc" || "$zcompdump" -nt "${zcompdump}.zwc") ]]; then
    zmodload zsh/system 2>/dev/null
    lock="${zcompdump}.zwc.lock"
    : >> "$lock" 2>/dev/null
    if zsystem flock -t 0 "$lock" 2>/dev/null; then
      zcompile "$zcompdump"
    fi
  fi
} &!
