# Login shell initialization (runs once for login shells)

# Initialize Homebrew environment (if available)
if [[ $PLATFORM == "macos" ]] && [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ $PLATFORM == "linux" || $PLATFORM == "wsl" ]] && [[ -x /home/linuxbrew/.linuxbrew/bin/brew ]]; then
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

# Add Docker completions to fpath (if available)
[[ -d "${HOME}/.docker/completions" ]] && fpath=(${HOME}/.docker/completions $fpath)

# Day-of-year the completion dump was written, or empty if there is none.
# Consumed twice below: it gates the shadow scan and picks the compinit branch.
#
# Prefer zsh's own builtins: no external command, no platform dialects, and
# no fork at all on this path. Both modules are optional at build time, so an
# external fallback follows.
#
# In the fallback the two stat dialects must NOT be chained on exit status.
# GNU `stat -f` means --file-system: given the BSD format args it treats them
# as filenames, prints terse fs info to *stdout*, and exits 1 — so `a || b`
# glued that output onto the real value and the comparison never matched,
# silently disabling compinit -C on Linux/WSL. Branch on whether the GNU
# spelling produced anything instead. The BSD line is therefore unreachable on
# a GNU system by construction; it is not a recovery path for a working
# `stat -c` paired with a `date` that cannot convert an epoch (busybox). That
# combination yields an empty day and falls back to a full compinit — correct,
# if slower, and it does not arise where zsh/datetime is present.
_zcompdump_day=
_zcompdump_today=
if zmodload -F zsh/stat b:zstat 2>/dev/null && zmodload zsh/datetime 2>/dev/null; then
  zstat -F '%j' -A _zcompdump_a +mtime ~/.zcompdump 2>/dev/null && _zcompdump_day=${_zcompdump_a[1]}
  strftime -s _zcompdump_today '%j' "$EPOCHSECONDS"
else
  _zcompdump_epoch=$(stat -c '%Y' ~/.zcompdump 2>/dev/null)
  if [[ -n $_zcompdump_epoch ]]; then
    _zcompdump_day=$(date -d "@${_zcompdump_epoch}" +'%j' 2>/dev/null)
  else
    _zcompdump_day=$(stat -f '%Sm' -t '%j' ~/.zcompdump 2>/dev/null)
  fi
  _zcompdump_today=$(date +'%j')
fi
_zcompdump_fresh=0
[[ -f ~/.zcompdump && -n $_zcompdump_day && $_zcompdump_today == "$_zcompdump_day" ]] && _zcompdump_fresh=1

# Neutralize dangling completion symlinks before compinit scans fpath.
# Docker Desktop's WSL integration drops a root-owned
# /usr/share/zsh/vendor-completions/_docker symlink into its cli-tools mount;
# when Docker Desktop is stopped the mount disappears and compinit fails with
# "no such file or directory" while reading the file's #compdef tag. We can't
# remove the root-owned symlink, but compinit dedupes completions by basename
# and the EARLIEST fpath entry wins, so an empty shadow file at the front makes
# it skip the broken one. Rebuilt each login, so the shadow stops being created
# once the real target is back — but the shadowed completion only returns when
# the dump is next rebuilt, since the compinit -C below reuses the cached dump
# for the rest of the day. Both halves are needed to force it back sooner:
# `rm ~/.zcompdump` AND then a new login shell. Neither alone works — the dump
# is only consulted at login, and a same-day login still takes the -C branch
# and sources the stale dump it just found.
#
# Mirror compinit's own rule rather than asking "does a valid copy exist
# anywhere": only a basename's FIRST fpath occurrence is ever read, so that is
# the only one that can error. Shadow a name iff its first occurrence dangles.
# A valid copy later in fpath is unreachable either way — compinit marks the
# name seen and skips it — so shadowing costs nothing, while the anywhere-valid
# test wrongly declined to shadow (dangling ~/.docker/completions/_docker
# prepended above, real vendor-completions copy later) and left the error.
#
# The directory is per-shell: concurrent logins (tmux panes, session restore)
# sharing one path would let shell B wipe the dir between shell A prepending it
# to fpath and A's compinit reading it — reintroducing this very error. Prune
# only dirs whose owning shell is gone, plus an age backstop: PIDs recycle, so
# liveness alone can strand a dir forever behind an unrelated process. The
# backstop can prune a live shell's dir out from under it, which only matters
# if that shell re-runs compinit by hand a day later — it would see the
# dangling symlink again. The dump-removal recovery above does not apply here
# (the dump isn't the problem, and a new shell builds a dir under its own PID):
# that one shell is affected until its next login, and new shells are fine.
#
# Only a *symlink* can dangle, so glob symlinks rather than every completion.
# The (@) qualifier still lstats each _* entry, so the syscall count is
# similar; what collapses is the shell loop body — ~45 iterations instead of
# ~2000 on the default fpath here, measured at ~2.3 ms versus ~9 ms.
#
# Gated on the dump being stale, because only the full compinit below walks
# fpath and can therefore hit the dangling symlink — compinit -C sources the
# dump directly and never looks. On the fast path (every login but the first of
# the day) the scan's whole result would be discarded, so skipping it keeps
# this off the common startup path entirely (CLAUDE.md: "Avoid adding slow
# operations to shell init files"). Pruning stays ungated so stale dirs are
# still reclaimed on fast-path logins.
#
# The gate is a trade, not free. The shadow dir stays on fpath for the life of
# the shell, so it also absorbs *autoload*-time failure: with it, invoking a
# dangling completion is a silent no-op; without it, zsh reports "function
# definition file not found". So on a same-day login after the target starts
# dangling, the dump still lists the completion and Tab-completing it errors.
# Accepted: the once-per-login startup error is the noisy one being fixed, this
# one fires only if you invoke that specific completion, and it clears at the
# next dump rebuild.
#
# Linux-family only: the dangling-mount symlink is a WSL/Docker-Desktop (and
# plausibly native-Linux) failure. macOS never hits it, so skip the scan there.
if [[ $PLATFORM == wsl || $PLATFORM == linux ]]; then
  _compinit_root="${HOME}/.cache/zsh"
  for _old in "$_compinit_root"/compinit-shadows.*(N/); do
    kill -0 ${_old:t:e} 2>/dev/null || rm -rf "$_old"
  done
  # Both m+0 and m+1 truncate age to whole days; +n is strictly-greater *after*
  # that truncation, so m+0 fires at ~24 h and m+1 would not until ~48 h.
  for _old in "$_compinit_root"/compinit-shadows.*(Nm+0/); do
    rm -rf "$_old"
  done
  if (( ! _zcompdump_fresh )); then
    _compinit_shadow="${_compinit_root}/compinit-shadows.$$"
    rm -rf "$_compinit_shadow"
    for _d in $fpath; do
      for _f in "$_d"/_*(N@); do
        # compinit ignores backups and compiled siblings (its own glob is
        # ^([^_]*|*~|*.zwc)); match that without needing extendedglob here.
        [[ $_f == *'~' || $_f == *.zwc ]] && continue
        [[ -e "$_f" ]] && continue
        # Shadow only the name's FIRST fpath occurrence — that is the only one
        # compinit reads, so an earlier same-named entry means this one is
        # already unreachable and needs no shadow.
        _n=${_f:t}
        _dup=0
        for _e in $fpath; do
          [[ $_e == "$_d" ]] && break
          [[ -e "$_e/$_n" || -L "$_e/$_n" ]] && { _dup=1; break; }
        done
        (( _dup )) && continue
        [[ -d "$_compinit_shadow" ]] || mkdir -p "$_compinit_shadow"
        : > "$_compinit_shadow/$_n"
      done
    done
    [[ -d "$_compinit_shadow" ]] && fpath=("$_compinit_shadow" $fpath)
  fi
  unset _compinit_root _compinit_shadow _old _d _f _n _e _dup
fi

# Initialize completions (cached daily via zcompdump)
autoload -Uz compinit
if (( _zcompdump_fresh )); then
  compinit -C
else
  compinit
fi
unset _zcompdump_fresh _zcompdump_day _zcompdump_today _zcompdump_epoch _zcompdump_a

# Add mise to PATH (needed by non-interactive shells, e.g. VSCode extensions)
[[ -d "$HOME/.local/bin" ]] && export PATH="$HOME/.local/bin:$PATH"

# Add LM Studio CLI (lms) to PATH (if available)
[[ -d "$HOME/.lmstudio/bin" ]] && export PATH="$PATH:$HOME/.lmstudio/bin"

# Initialize Rust/Cargo environment (if available)
[[ -f "$HOME/.cargo/env" ]] && . "$HOME/.cargo/env"
