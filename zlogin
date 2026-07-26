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
#
# zsh/system is optional at build time. When it is missing we still compile —
# unserialized, with stderr dropped — rather than skip precompilation forever:
# the race is cosmetic, losing the .zwc entirely is a permanent startup cost.
{
  zcompdump="${HOME}/.zcompdump"
  if [[ -s "$zcompdump" && (! -s "${zcompdump}.zwc" || "$zcompdump" -nt "${zcompdump}.zwc") ]]; then
    if zmodload zsh/system 2>/dev/null; then
      lock="${zcompdump}.zwc.lock"
      : >> "$lock" 2>/dev/null
      zsystem flock -t 0 "$lock" 2>/dev/null && zcompile "$zcompdump"
    else
      zcompile "$zcompdump" 2>/dev/null
    fi
  fi
} &!
