# Zsh-specific ShellCheck codes to ignore (valid zsh syntax that ShellCheck
# doesn't understand when linting with --shell=bash)
zsh_excludes := "SC1036,SC1087,SC1090,SC2128,SC2145,SC2154,SC2155,SC2179,SC2206,SC2211,SC2296"

# Run all CI checks
ci: lint-shell lint-json-yaml lint-markdown lint-brewfile lint-mise

# Enable the pre-commit hook for this repo
setup:
    git config --local core.hooksPath .githooks

# Lint shell scripts with ShellCheck
lint-shell:
    shellcheck --severity=warning bin/op-ssh-sign bin/kshow bin/kseal
    shellcheck --severity=warning claude/statusline-command.sh
    shellcheck --severity=warning --shell=bash --exclude={{zsh_excludes}} zshenv zprofile zshrc zsh/zaliases zsh/zcompletion zsh/functions/*

# Validate JSON and YAML config files
lint-json-yaml:
    yq '.' config/alacritty/alacritty.yml > /dev/null

# Lint markdown files
lint-markdown:
    markdownlint-cli2

# Check Brewfile Ruby syntax
lint-brewfile:
    ruby -c Brewfile
    ruby -c Brewfile.linux

# Validate mise config
lint-mise:
    mise config ls

# Update everything (brew, mac app store, mise, rust)
update: update-brew update-mas update-mise update-rust

# Resolve through symlink so this works when just finds ~/.justfile
dotfiles_dir := parent_directory(canonicalize(justfile()))

# Platform-specific Brewfile
brewfile := dotfiles_dir / if os() == "macos" { "Brewfile" } else { "Brewfile.linux" }

# Update Homebrew packages and clean up
update-brew:
    brew update
    brew bundle install --file={{brewfile}}
    brew upgrade
    brew cleanup --prune=all
    brew bundle cleanup --force --file={{brewfile}}
    -brew doctor

# Update Mac App Store apps (no-op on non-macOS)
update-mas:
    {{ if os() == "macos" { "if command -v mas >/dev/null 2>&1; then mas upgrade; fi" } else { "true" } }}

# Show outdated mise tools and upgrade them
update-mise:
    mise outdated
    mise upgrade --bump

# Update Rust toolchain
update-rust:
    rustup update

# Remove stale symlinks in $HOME that point into dotfiles dirs
cleanup-symlinks:
    #!/usr/bin/env zsh
    # Derive nested dirs from the dotfiles repos themselves
    dotfiles_repos=("$HOME/Workspace/tgautier/dotfiles" "$HOME/Workspace/tgautier/dotfiles-private")
    nested=()
    for repo in "${dotfiles_repos[@]}"; do
        [[ -d "$repo" ]] || continue
        for d in "$repo"/*(N/); do
            name=${d:t}
            # Skip repo-only dirs that rcm doesn't symlink
            [[ "$name" == .* || "$name" == README* || "$name" == CLAUDE* ]] && continue
            candidate="$HOME/.$name"
            [[ -d "$candidate" ]] && nested+=("$candidate")
        done
    done
    stale=()
    # Top-level dotfiles (non-recursive)
    for f in $HOME/.[!.]*(N@); do
        [[ -e "$f" ]] && continue
        target=$(readlink "$f")
        [[ "$target" == *"/dotfiles/"* || "$target" == *"/dotfiles-private/"* ]] && stale+=("$f -> $target")
    done
    # Nested dirs (recursive)
    for dir in "${nested[@]}"; do
        [[ -d "$dir" ]] || continue
        for f in "$dir"/**/*(N@); do
            [[ -e "$f" ]] && continue
            target=$(readlink "$f")
            [[ "$target" == *"/dotfiles/"* || "$target" == *"/dotfiles-private/"* ]] && stale+=("$f -> $target")
        done
    done
    if (( ${#stale} == 0 )); then
        echo "No stale symlinks found."
        exit 0
    fi
    echo "Stale symlinks:"
    printf '  %s\n' "${stale[@]}"
    echo ""
    read -q "reply?Remove ${#stale} stale symlink(s)? [y/N] " || { echo ""; exit 0; }
    echo ""
    for entry in "${stale[@]}"; do
        link="${entry%% ->*}"
        rm "$link" && echo "Removed: $link"
    done
