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
    jq empty claude/settings.json
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

# Platform-specific Brewfile
brewfile := if os() == "macos" { "Brewfile" } else { "Brewfile.linux" }

# Update Homebrew packages and clean up
update-brew:
    brew update
    brew bundle install --file={{brewfile}}
    brew upgrade
    brew cleanup --prune=all
    brew bundle cleanup --force --file={{brewfile}}
    -brew doctor

# Update Mac App Store apps (skipped if mas not installed)
update-mas:
    command -v mas > /dev/null || exit 0
    mas upgrade

# Show outdated mise tools and upgrade them
update-mise:
    mise outdated
    mise upgrade --bump

# Update Rust toolchain
update-rust:
    rustup update
