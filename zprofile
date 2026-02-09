# Login shell initialization (runs once for login shells)

# Initialize Homebrew environment (if available)
if [[ $PLATFORM == "macos" ]] && [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ $PLATFORM == "linux" || $PLATFORM == "wsl" ]] && [[ -x /home/linuxbrew/.linuxbrew/bin/brew ]]; then
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

# Add Docker completions to fpath (if available)
[[ -d "${HOME}/.docker/completions" ]] && fpath=(${HOME}/.docker/completions $fpath)

# Initialize completions
autoload -Uz compinit
compinit

# Initialize Rust/Cargo environment (if available)
[[ -f "$HOME/.cargo/env" ]] && . "$HOME/.cargo/env"
