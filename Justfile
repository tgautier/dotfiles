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

# Bootstrap this machine: profile, packages, symlinks, runtimes, hooks, tools (idempotent)
setup: _ensure-profile
    #!/usr/bin/env bash
    set -euo pipefail
    # Prerequisites (just does not exist before them): install Homebrew, clone
    # this repo (+ dotfiles-private if used), run `brew bundle` once to get `just`.
    cd "{{dotfiles_dir}}"

    # 1. Packages for this machine's profile (install only; `just update` upgrades).
    brew bundle install --file="{{brewfile}}"

    # 2. Symlink dotfiles. RCRC points rcm at the repo config so a fresh machine
    #    (no ~/.rcrc yet) links every DOTFILES_DIRS entry; a missing private repo
    #    is skipped, not fatal.
    RCRC="{{dotfiles_dir}}/rcrc" rcup

    # 3. Language runtimes from the pinned mise config. Install mise first if the
    #    machine doesn't have it yet (matches the README curl bootstrap).
    if ! command -v mise >/dev/null 2>&1 && [ ! -x "${HOME}/.local/bin/mise" ]; then
        curl -fsSL https://mise.run | sh
    fi
    mise_bin="$(command -v mise || true)"
    [ -z "$mise_bin" ] && [ -x "${HOME}/.local/bin/mise" ] && mise_bin="${HOME}/.local/bin/mise"
    if [ -n "$mise_bin" ]; then
        "$mise_bin" install
    else
        echo "mise not found on PATH or at ~/.local/bin/mise after the install attempt — aborting." >&2
        exit 1
    fi

    # 4. Git hooks + review tooling.
    git config --local core.hooksPath .githooks
    if command -v roborev >/dev/null 2>&1; then roborev install-hook; fi

    # 5. Native-installer tools (self-update through their own channels).
    command -v claude >/dev/null 2>&1 || curl -fsSL https://claude.ai/install.sh | bash
    command -v hermes >/dev/null 2>&1 || curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

    # 6. Default editor associations (macOS only; no-ops elsewhere).
    just set-default-editor

    # 7. Linux/WSL: symlink libsqlite3 for Dart/Flutter FFI (no-op on macOS).
    {{ if os() == "macos" { "true" } else { "just _link-libsqlite3" } }}

# Symlink the system libsqlite3 into a dedicated ~/.local/lib/flutter-ffi dir for
# Dart/Flutter (Drift) FFI, which dlopen()s the unversioned 'libsqlite3.so' the
# distro doesn't ship. Dedicated dir so only this symlink is ever on the loader
# path (see zshenv). Linux/WSL only; resolves the real path via ldconfig, preferring
# the entry matching the native arch so a multiarch box (e.g. amd64 + i386) can't
# select a wrong-arch lib. Falls back to the first match on unrecognized arches.
_link-libsqlite3:
    #!/usr/bin/env sh
    set -eu
    # ldconfig usually lives in /sbin, which isn't always on a non-root PATH.
    ldconfig_bin=$(command -v ldconfig || echo /sbin/ldconfig)
    if [ ! -x "$ldconfig_bin" ]; then
        echo "ldconfig not found (looked on PATH and /sbin) — cannot locate libsqlite3.so.0" >&2
        exit 0
    fi
    # ldconfig -p tags each entry with its ABI, e.g. '(libc6,x86-64)'. Prefer the
    # entry matching this machine's arch; fall back to the first match otherwise.
    case "$(uname -m)" in
        x86_64)  abi='x86-64' ;;
        aarch64) abi='AArch64' ;;
        *)       abi='' ;;
    esac
    src=$("$ldconfig_bin" -p | awk -v abi="$abi" '
        /libsqlite3\.so\.0/ {
            if (first == "") first = $NF
            if (abi != "" && index($0, "(libc6," abi)) { print $NF; found = 1; exit }
        }
        END { if (!found) print first }')
    if [ -z "$src" ]; then
        echo "libsqlite3.so.0 not in ldconfig cache — install it (e.g. apt install libsqlite3-0) for Flutter Drift FFI" >&2
        exit 0
    fi
    mkdir -p "$HOME/.local/lib/flutter-ffi"
    ln -sf "$src" "$HOME/.local/lib/flutter-ffi/libsqlite3.so"
    echo "linked $src -> $HOME/.local/lib/flutter-ffi/libsqlite3.so"

# Ensure a valid Brewfile profile marker exists (macOS only — Brewfile.linux
# never reads it); prompt on first interactive setup (default: work). A
# non-interactive run fails instead of defaulting: silently minting a
# valid-but-wrong marker on an unmigrated personal Mac would let
# `brew bundle cleanup --force` uninstall every personal app — the exact
# disaster the Brewfile marker guard exists to prevent.
# No-op when the marker already holds a valid profile.
_ensure-profile:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ "$(uname -s)" != "Darwin" ]]; then
        exit 0
    fi
    marker="${HOME}/.config/dotfiles/profile"
    current=""
    # Trim-only (ends), mirroring the Brewfile's String#strip on the same file.
    [[ -f "$marker" ]] && current="$(sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' "$marker")"
    if [[ "$current" == "work" || "$current" == "personal" ]]; then
        echo "Machine profile already set: $current"
        exit 0
    fi
    if [[ ! -t 0 ]]; then
        echo "No machine profile set and stdin is not a terminal." >&2
        echo "Run 'just set-profile work|personal' first, then re-run 'just setup'." >&2
        exit 1
    fi
    printf 'Select machine profile [work/personal] (default: work): '
    read -r reply
    just set-profile "${reply:-work}"

# Lint shell scripts with ShellCheck
lint-shell:
    shellcheck --severity=warning bin/op-ssh-sign bin/kshow bin/kseal
    shellcheck --severity=warning --shell=bash --exclude={{zsh_excludes}} zshenv zprofile zshrc zsh/zaliases zsh/zcompletion zsh/functions/*

# Lint markdown files
lint-markdown:
    markdownlint-cli2

# Set this machine's Brewfile profile (work|personal). Writes the marker the
# Brewfile reads to pick Brewfile.work / Brewfile.personal — the Brewfile
# fails loud when the marker is absent; interactive `just setup` prompts
# for it (default: work).
set-profile profile:
    #!/usr/bin/env bash
    set -euo pipefail
    # quote() interpolates once as a shell-safe literal; metacharacters in the
    # argument (e.g. typed at the _ensure-profile prompt) stay inert data.
    profile={{quote(profile)}}
    if [[ "$profile" != "work" && "$profile" != "personal" ]]; then
        echo "Error: profile must be 'work' or 'personal', got '$profile'" >&2
        exit 1
    fi
    mkdir -p "${HOME}/.config/dotfiles"
    printf '%s\n' "$profile" > "${HOME}/.config/dotfiles/profile"
    echo "Machine profile set to '$profile' (${HOME}/.config/dotfiles/profile)."
    echo "Run 'just update-brew' to sync packages for this profile."

# Check Brewfile Ruby syntax + evaluate the profile-overlay merge logic
lint-brewfile:
    #!/usr/bin/env bash
    set -euo pipefail
    ruby -c Brewfile
    ruby -c Brewfile.work
    ruby -c Brewfile.personal
    ruby -c Brewfile.linux
    # Evaluate the merged Brewfile for each profile from a non-repo cwd with
    # stubbed DSL methods — catches overlay-resolution and fail-loud regressions
    # that `ruby -c` (syntax only) cannot see. The stubs also record each
    # brew/cask/mas entry name so a package present in BOTH the base and an
    # overlay (a duplicate in the merged bundle, which `ruby -c` cannot see and
    # `brew bundle` may error on) fails the lint — issue #192.
    brewfile="$PWD/Brewfile"
    harness='
      seen = Hash.new(0)
      dups = []
      dsl = Object.new
      %i[brew cask mas].each do |m|
        dsl.define_singleton_method(m) do |name, *a, **k|
          key = [m, name]
          seen[key] += 1
          dups << key if seen[key] == 2
        end
      end
      dsl.define_singleton_method(:tap) { |*a, **k| }
      dsl.instance_eval(File.read(ARGV[0]), ARGV[0])
      unless dups.empty?
        STDERR.puts "DUPLICATE Brewfile entries in merged bundle:"
        dups.each { |m, n| STDERR.puts %(  #{m} "#{n}") }
        exit 1
      end
    '
    tmp_root="$(mktemp -d)"
    trap 'rm -rf "$tmp_root"' EXIT
    for profile in work personal; do
        home_dir="$tmp_root/$profile"
        mkdir -p "$home_dir/.config/dotfiles"
        printf '%s\n' "$profile" > "$home_dir/.config/dotfiles/profile"
        (cd /tmp && HOME="$home_dir" ruby -e "$harness" "$brewfile")
        echo "Brewfile merge OK: $profile"
    done
    # An absent marker must trip the marker guard, never silently bundle the
    # base-only set — assert the guard's own message, not just any failure.
    mkdir -p "$tmp_root/absent"
    if out="$(cd /tmp && HOME="$tmp_root/absent" ruby -e "$harness" "$brewfile" 2>&1)"; then
        echo "ERROR: Brewfile must raise when the profile marker is absent" >&2
        exit 1
    fi
    if ! grep -q 'No valid machine profile' <<<"$out"; then
        echo "ERROR: absent-marker failure did not come from the marker guard:" >&2
        echo "$out" >&2
        exit 1
    fi
    echo "Brewfile absent-marker raise OK"
    # A duplicate brew/cask/mas name (here within one file; the same guard
    # catches a base+overlay duplicate) must fail loud — assert the dup guard
    # fires on a known duplicate, not just any error.
    dup_brewfile="$tmp_root/dup-Brewfile"
    printf 'cask "vlc"\ncask "vlc"\n' > "$dup_brewfile"
    if dout="$(cd /tmp && ruby -e "$harness" "$dup_brewfile" 2>&1)"; then
        echo "ERROR: duplicate detection did not fire on a known duplicate" >&2
        exit 1
    fi
    if ! grep -q 'DUPLICATE' <<<"$dout"; then
        echo "ERROR: duplicate-case failure did not come from the dup guard:" >&2
        echo "$dout" >&2
        exit 1
    fi
    echo "Brewfile duplicate-detection OK"

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
# Word and Pages documents are deliberately excluded. Web-content types
# (html/htm/xhtml/svg) and the root public.data UTI are ALSO excluded: making
# VS Code the default HTML handler cascades into the macOS web-browser role and
# the http/https URL schemes, hijacking web links away from the browser.
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
    )
    for uti in "${utis[@]}"; do
        duti -s "$bundle" "$uti" all 2>/dev/null || true
    done
    # Extension-level associations (catches files without a registered UTI).
    # Excludes Word (.doc, .docx), Pages (.pages), and web content
    # (.html/.htm/.xhtml/.svg) by design — see the recipe header above.
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
        css scss sass less styl
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
    echo "Word (.doc/.docx), Pages (.pages), and web content (.html/.svg)"
    echo "intentionally left untouched so the browser keeps http/https links."

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
