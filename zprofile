# Login shell initialization (runs once for login shells)

# Initialize Homebrew environment (if available)
if [[ $PLATFORM == "macos" ]] && [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ $PLATFORM == "linux" || $PLATFORM == "wsl" ]] && [[ -x /home/linuxbrew/.linuxbrew/bin/brew ]]; then
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

# Add Docker completions to fpath (if available)
[[ -d "${HOME}/.docker/completions" ]] && fpath=(${HOME}/.docker/completions $fpath)

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
# for the rest of the day. `rm ~/.zcompdump` forces it back immediately.
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
# only dirs whose owning shell is gone; a live shell's fpath still points at its
# own.
#
# Linux-family only: the dangling-mount symlink is a WSL/Docker-Desktop (and
# plausibly native-Linux) failure. macOS never hits it, so skip the fpath scan
# there — a login shell runs per terminal tab and the scan stats every _* file
# in the default system fpath.
if [[ $PLATFORM == wsl || $PLATFORM == linux ]]; then
  _compinit_root="${HOME}/.cache/zsh"
  for _old in "$_compinit_root"/compinit-shadows.*(N/); do
    kill -0 ${_old:t:e} 2>/dev/null || rm -rf "$_old"
  done
  _compinit_shadow="${_compinit_root}/compinit-shadows.$$"
  rm -rf "$_compinit_shadow"
  # Walk fpath in order, keeping only each basename's first occurrence — the
  # one compinit will actually read.
  typeset -A _compinit_first
  for _d in $fpath; do
    for _f in "$_d"/_*(N); do
      [[ -n "${_compinit_first[${_f:t}]}" ]] || _compinit_first[${_f:t}]="$_f"
    done
  done
  for _n in ${(k)_compinit_first}; do
    [[ -e "${_compinit_first[$_n]}" ]] && continue
    [[ -d "$_compinit_shadow" ]] || mkdir -p "$_compinit_shadow"
    : > "$_compinit_shadow/$_n"
  done
  [[ -d "$_compinit_shadow" ]] && fpath=("$_compinit_shadow" $fpath)
  unset _compinit_root _compinit_shadow _old _d _f _n _compinit_first
fi

# Initialize completions (cached daily via zcompdump)
autoload -Uz compinit
if [[ -f ~/.zcompdump && $(date +'%j') == $(stat -f '%Sm' -t '%j' ~/.zcompdump 2>/dev/null || stat -c '%Y' ~/.zcompdump 2>/dev/null | xargs -I{} date -d @{} +'%j' 2>/dev/null) ]]; then
  compinit -C
else
  compinit
fi

# Add mise to PATH (needed by non-interactive shells, e.g. VSCode extensions)
[[ -d "$HOME/.local/bin" ]] && export PATH="$HOME/.local/bin:$PATH"

# Add LM Studio CLI (lms) to PATH (if available)
[[ -d "$HOME/.lmstudio/bin" ]] && export PATH="$PATH:$HOME/.lmstudio/bin"

# Initialize Rust/Cargo environment (if available)
[[ -f "$HOME/.cargo/env" ]] && . "$HOME/.cargo/env"
