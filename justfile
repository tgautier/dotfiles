# Zsh-specific ShellCheck codes to ignore (valid zsh syntax that ShellCheck
# doesn't understand when linting with --shell=bash)
zsh_excludes := "SC1036,SC1087,SC1090,SC2128,SC2145,SC2154,SC2155,SC2179,SC2206,SC2211,SC2296"

# Run all CI checks
ci: lint-shell lint-json-yaml lint-markdown lint-brewfile

# Enable the pre-commit hook for this repo
setup:
    git config --local core.hooksPath .githooks

# Lint shell scripts with ShellCheck
lint-shell:
    shellcheck --severity=warning bin/op-ssh-sign bin/stack-update bin/kshow bin/kseal
    shellcheck --severity=warning claude/statusline-command.sh
    shellcheck --severity=warning --shell=bash --exclude={{zsh_excludes}} zshenv zprofile zshrc zsh/zaliases zsh/zcompletion zsh/functions/*

# Validate JSON and YAML config files
lint-json-yaml:
    jq empty claude/settings.json
    python3 -c "import yaml; yaml.safe_load(open('config/alacritty/alacritty.yml'))"

# Lint markdown files
lint-markdown:
    markdownlint-cli2

# Check Brewfile Ruby syntax
lint-brewfile:
    ruby -c Brewfile
    ruby -c Brewfile.linux
