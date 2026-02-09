# Login shell initialization (runs once for login shells)

# Initialize Homebrew environment
eval "$(/opt/homebrew/bin/brew shellenv)"

# Add Docker completions to fpath
fpath=(/Users/tgautier/.docker/completions $fpath)

# Initialize completions
autoload -Uz compinit
compinit

# Initialize Rust/Cargo environment
. "$HOME/.cargo/env"
