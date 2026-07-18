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
# with the earliest fpath entry winning, so an empty shadow file earlier in
# fpath makes it skip the broken one. Rebuilt each login so shadows vanish once
# the real target is back.
#
# The shadow is basename-keyed and sits at the front of fpath, so it masks
# *every* completion of that name — including a valid same-named one elsewhere
# in fpath (e.g. a working ~/.docker/completions/_docker prepended above). Only
# shadow a name that has no valid completion anywhere, so we suppress the broken
# symlink without disabling a good copy.
#
# Linux-family only: the dangling-mount symlink is a WSL/Docker-Desktop (and
# plausibly native-Linux) failure. macOS never hits it, so skip the two fpath
# scans there — a login shell runs per terminal tab and the scan stats every
# _* file in the default system fpath.
if [[ $PLATFORM == wsl || $PLATFORM == linux ]]; then
  _compinit_shadow="${HOME}/.cache/zsh/compinit-shadows"
  rm -rf "$_compinit_shadow"
  # Pass 1: record every completion basename that resolves to a real file
  # (regular file or non-dangling symlink) somewhere in fpath.
  typeset -A _compinit_valid
  for _d in $fpath; do
    for _f in "$_d"/_*(N); do
      [[ -e "$_f" ]] && _compinit_valid[${_f:t}]=1
    done
  done
  # Pass 2: shadow a dangling completion symlink only when no valid completion of
  # the same basename exists — otherwise the shadow would mask the working copy.
  for _d in $fpath; do
    for _l in "$_d"/_*(N@); do
      [[ -e "$_l" ]] && continue
      [[ -n "${_compinit_valid[${_l:t}]}" ]] && continue
      [[ -d "$_compinit_shadow" ]] || mkdir -p "$_compinit_shadow"
      : > "$_compinit_shadow/${_l:t}"
    done
  done
  [[ -d "$_compinit_shadow" ]] && fpath=("$_compinit_shadow" $fpath)
  unset _compinit_shadow _d _l _f _compinit_valid
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
