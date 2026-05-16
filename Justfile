# Zsh-specific ShellCheck codes to ignore (valid zsh syntax that ShellCheck
# doesn't understand when linting with --shell=bash)
zsh_excludes := "SC1036,SC1087,SC1090,SC2128,SC2145,SC2154,SC2155,SC2168,SC2179,SC2206,SC2211,SC2296"

# Run all CI checks
ci: lint-shell lint-markdown lint-brewfile lint-mise lint-via-private

# Delegate to the private repo's justfile for checks that must not be
# defined here (keyword lists etc.). No-op when private repo is absent.
lint-via-private:
    if [ -f ~/Workspace/tgautier/dotfiles-private/justfile ]; then \
        just -f ~/Workspace/tgautier/dotfiles-private/justfile lint-public-no-arr; \
    fi

# Enable the pre-commit hook and install native tools
setup:
    git config --local core.hooksPath .githooks
    if command -v roborev >/dev/null 2>&1; then roborev install-hook; fi
    command -v claude >/dev/null 2>&1 || curl -fsSL https://claude.ai/install.sh | bash

# Lint shell scripts with ShellCheck
lint-shell:
    shellcheck --severity=warning bin/op-ssh-sign bin/kshow bin/kseal
    shellcheck --severity=warning --shell=bash --exclude={{zsh_excludes}} zshenv zprofile zshrc zsh/zaliases zsh/zcompletion zsh/functions/*

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

# Register VS Code as default opener for text/code/data files (macOS only).
# Word and Pages documents are deliberately excluded.
set-default-editor:
    #!/usr/bin/env zsh
    if [[ "$(uname -s)" != "Darwin" ]]; then
        echo "set-default-editor: macOS only — skipping."
        exit 0
    fi
    if ! command -v duti >/dev/null 2>&1; then
        echo "duti not installed — run 'brew bundle install --file=Brewfile'"
        exit 1
    fi
    bundle="com.microsoft.VSCode"
    # Generic UTIs covering broad file categories
    utis=(
        public.plain-text
        public.text
        public.source-code
        public.script
        public.shell-script
        public.python-script
        public.ruby-script
        public.perl-script
        public.php-script
        public.json
        public.xml
        public.yaml
        public.comma-separated-values-text
        public.tab-separated-values-text
        public.log
        public.data
    )
    for uti in "${utis[@]}"; do
        duti -s "$bundle" "$uti" all 2>/dev/null || true
    done
    # Extension-level associations (catches files without a registered UTI).
    # Excludes Word (.doc, .docx) and Pages (.pages) by design.
    exts=(
        txt md markdown rst adoc org tex log csv tsv
        json yaml yml toml xml ini conf cfg env properties plist
        sh bash zsh fish ps1 bat cmd
        js mjs cjs jsx ts tsx vue svelte astro
        py rb php pl lua tcl r jl nim zig v
        go rs swift kt kts java scala clj cljs cljc edn
        c cc cpp cxx h hh hpp hxx m mm
        cs fs fsx vb
        ex exs erl hrl hs lhs ml mli ocaml
        sol move
        css scss sass less styl html htm xhtml svg
        sql graphql gql proto thrift avsc
        dart
        tf hcl tfvars
        dockerfile containerfile
        gitignore gitattributes editorconfig nvmrc tool-versions
        diff patch
    )
    for ext in "${exts[@]}"; do
        duti -s "$bundle" ".$ext" all 2>/dev/null || true
    done
    echo "VS Code registered as default for text/code/data files."
    echo "Word (.doc/.docx) and Pages (.pages) intentionally left untouched."

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
