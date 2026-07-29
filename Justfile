# Zsh-specific ShellCheck codes to ignore (valid zsh syntax that ShellCheck
# doesn't understand when linting with --shell=bash)
zsh_excludes := "SC1036,SC1087,SC1090,SC2128,SC2145,SC2154,SC2155,SC2168,SC2179,SC2206,SC2211,SC2296"

# Run all CI checks
ci: lint-shell lint-markdown lint-brewfile lint-mise lint-just lint-via-private

# Assert every in-body `just <recipe>` call names a recipe that exists here.
# Those calls are opaque shell strings to just, so nothing else catches a typo:
# `just --summary` and `just --dry-run setup` both exit 0 with a misspelt one,
# and it would surface only mid-bootstrap on a fresh machine, after `brew
# bundle` has already run. (`just --fmt --check` is no help either — it exits 1
# on this file for formatting reasons alone.) The recipe list comes from
# --dump rather than --summary because --summary omits `_`-prefixed recipes,
# two of which are called from bodies. Calls carrying `-f` target another
# justfile and are skipped by the pattern, which requires a recipe name
# directly after `just`. Two negative fixtures run on every invocation, per the
# guard-testing convention in .claude/rules/brewfile.md.
[doc("Check that in-body `just <recipe>` calls name recipes that exist")]
lint-just:
    #!/usr/bin/env bash
    set -euo pipefail
    known=" $(just --dump --dump-format json | jq -r '.recipes | keys[]' | tr '\n' ' ')"

    # Recipe bodies only: indented, and not a comment line. Prose in comments
    # ("so this works when just finds ~/.justfile") would otherwise match.
    scan() {
        grep -E '^[[:space:]]' "$1" | grep -vE '^[[:space:]]*#' \
            | grep -oE '(^|[^-[:alnum:]_])just +[a-z_][a-z0-9_-]*' \
            | grep -oE '[a-z_][a-z0-9_-]*$' | sort -u
    }

    # Factored out so the negative fixtures below exercise this exact logic
    # rather than a copy of it.
    check() {
        local file=$1 called status=0 name
        # Keeps the guard below reachable if `check` is ever called outside a
        # condition context. Today's call sites (`check … || exit 1`, and the
        # fixtures' `if check …`) already suppress `-e` for this whole body, so
        # a plain assignment would fall through on its own — but a refactor to a
        # bare `check Justfile` would restore `-e` here, and the no-match
        # pipeline under `pipefail` would abort before the guard could report.
        if ! called=$(scan "$file"); then called=""; fi
        # An empty result means the regex broke, not that the file is clean:
        # `setup` alone makes three such calls. Without this the lint would
        # silently pass forever.
        if [ -z "$called" ]; then
            echo "lint-just: no \`just <recipe>\` call matched in $file — the pattern is broken" >&2
            return 1
        fi
        for name in $called; do
            case "$known" in
                *" $name "*) ;;
                *) echo "lint-just: $file calls \`just $name\`, which is not a recipe here" >&2
                   status=1 ;;
            esac
        done
        if [ "$status" -eq 0 ]; then
            echo "Justfile recipe calls OK ($(printf '%s\n' "$called" | wc -l | tr -d ' ') checked)"
        fi
        return "$status"
    }

    check Justfile || exit 1

    # Negative fixtures, mirroring `lint-brewfile`: assert each guard fires on
    # known-bad input AND that the failure came from that guard, not from any
    # incidental error. A guard that never fires is worse than no guard.
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT

    # The recipe names go through printf ARGUMENTS, never as literal text on
    # these lines: this file is itself scanned, so an inline `just <name>` here
    # would be picked up as a real call by the check under test.
    printf 'real:\n    echo hi\n\ncaller:\n    just %s\n' nosuchrecipe > "$tmp/unknown"
    if out=$(check "$tmp/unknown" 2>&1); then
        echo "ERROR: lint-just did not fire on a call to a non-existent recipe" >&2
        exit 1
    fi
    if ! grep -q 'is not a recipe here' <<<"$out"; then
        echo "ERROR: unknown-recipe case did not come from the unknown-recipe guard:" >&2
        echo "$out" >&2
        exit 1
    fi
    echo "lint-just unknown-recipe detection OK"

    # The comment is INDENTED so the emptiness comes from the comment filter
    # rather than the indent filter — a column-0 comment would be dropped by the
    # first filter and leave the comment-exclusion branch untested.
    printf 'nothing:\n    # just %s in a comment must not match\n    echo hi\n' link > "$tmp/empty"
    if out=$(check "$tmp/empty" 2>&1); then
        echo "ERROR: lint-just did not fire when the pattern matched nothing" >&2
        exit 1
    fi
    if ! grep -q 'the pattern is broken' <<<"$out"; then
        echo "ERROR: empty-match case did not come from the empty-match guard:" >&2
        echo "$out" >&2
        exit 1
    fi
    echo "lint-just empty-match detection OK"

# Delegate to the private repo's justfile for checks that must not be defined
# here (keyword lists etc.). Skips loudly when the private repo is absent —
# notably on a CI runner, where it is never present, so this leg of the keyword
# guard has never executed there. The enforcing copies are the two pre-commit
# hooks (this repo's runs `just ci` with the private repo present; the private
# repo's `ci-lint` includes `lint-public-no-arr`), so a skip here is a
# defence-in-depth gap, not an unguarded invariant. Announce it either way: a
# silent no-op reads as a pass.
lint-via-private:
    @if [ -f {{ quote(private_justfile) }} ]; then \
        just -f {{ quote(private_justfile) }} lint-public-no-arr; \
    else \
        echo "⚠ lint-via-private: keyword guard SKIPPED — no private justfile at" {{ quote(private_justfile) }}; \
    fi

# Bootstrap this machine: profile, packages, symlinks, runtimes, hooks, tools (idempotent)
setup: _ensure-profile
    #!/usr/bin/env bash
    set -euo pipefail
    # Prerequisites (just does not exist before them): install Homebrew, clone
    # this repo (+ dotfiles-private if used), run `brew bundle` once to get `just`.
    cd "{{dotfiles_dir}}"

    # 1. Packages for this machine's profile (install only; `just update`
    #    upgrades). Homebrew's trusted-taps gate ($HOMEBREW_REQUIRE_TAP_TRUST,
    #    Homebrew 6+) is satisfied by the `trusted: true` options on the
    #    tap-prefixed formulae in the Brewfile — `brew bundle` records that
    #    formula-level trust before fetching anything. Trust must live in the
    #    Brewfile, not in an imperative `brew trust` step: `brew bundle cleanup
    #    --force` (in update-brew) resets the trust store to exactly the
    #    Brewfile-declared `trusted:` entries, wiping anything trusted by hand.
    #    `--no-upgrade` keeps this install-only: bootstrap should not try to
    #    upgrade already-installed packages (`just update` owns upgrades). Without
    #    it, `brew bundle install` upgrades every outdated cask/formula, so a
    #    single failing upgrade (e.g. a cask with a stale Caskroom app) aborts the
    #    whole bootstrap — a fresh-machine step must not depend on every existing
    #    package upgrading cleanly.
    brew bundle install --no-upgrade --file="{{brewfile}}"

    # 2. Symlink dotfiles. Delegated to `link` so the RCRC-prefixed invocation
    #    lives in exactly one place. Called here rather than declared as a
    #    dependency because dependencies run before the recipe body, and rcm
    #    itself comes from the `brew bundle` in step 1.
    just link

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

# Run this after editing any dotfile rcm links into $HOME (gitconfig, zshrc,
# zshenv, tmux.conf, …) — the edit lands in this repo, but the running machine
# only picks it up once the links are re-applied. `just update` does NOT
# re-link: it upgrades installed software, not local config. RCRC points rcm at
# this repo's in-tree config, so every DOTFILES_DIRS entry is linked even on a
# machine that has never been bootstrapped — `~/.rcrc` is itself one of the
# symlinks rcm creates, so a bare `rcup` only finds the same config after the
# first run. That makes this the authoritative invocation, and `setup` calls it
# rather than repeating it. An absent private repo is skipped, not fatal.
#
# Must be run from this checkout: `~/.justfile` is a symlink to the PRIVATE
# repo's justfile, so `just link` from $HOME resolves there and fails with an
# unknown-recipe error. The [doc] attribute carries the summary because `just
# --list` would otherwise show only the last line of this comment.
[doc("Re-apply the rcm symlinks (run after editing a symlinked dotfile)")]
link:
    RCRC="{{dotfiles_dir}}/rcrc" rcup

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
    # Trim-only (ends), approximating the Brewfile's String#strip (sed is
    # per-line, so a multi-line marker re-prompts — stricter than the guard, safe).
    [[ -f "$marker" ]] && current="$(sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' "$marker")"
    if [[ "$current" == "work" || "$current" == "personal" ]]; then
        echo "Machine profile already set: $current"
        exit 0
    fi
    if [[ ! -t 0 ]]; then
        # Distinguish a missing marker from one that exists but is empty or
        # invalid — reporting both as "<absent>" is the conflation this message
        # exists to avoid.
        if [[ -f "$marker" ]]; then got="'$current'"; else got="<absent>"; fi
        echo "No valid machine profile (got $got) and stdin is not a terminal." >&2
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

# Private companion repo, for `lint-via-private`. Anchored to $HOME rather than
# derived from dotfiles_dir on purpose: inside a nested worktree dotfiles_dir is
# .claude/worktrees/<name>, whose sibling is not the private repo, so a
# sibling-derived path would silently skip the guard exactly when working on a
# branch. Override per machine with DOTFILES_PRIVATE_DIR.
#
# Scope: `lint-via-private` only — see #215 before widening it. `rcrc` and
# `cleanup-symlinks` still hardcode the paths, for two unrelated reasons:
#   - `rcrc` is a one-liner. rcm sources it as shell, so it can read the env var
#     directly. It is unwired only to keep #214 scoped, so until then setting the
#     override points the keyword guard at a private repo `rcup` never merges.
#   - `cleanup-symlinks` is the hard one: rcm records absolute symlink targets, so
#     links into a *former* checkout path must keep matching, and a prefix built
#     from the current paths cannot see them.
private_dir := env("DOTFILES_PRIVATE_DIR", env("HOME") / "Workspace/tgautier/dotfiles-private")
private_justfile := private_dir / "justfile"

# Platform-specific Brewfile
brewfile := dotfiles_dir / if os() == "macos" { "Brewfile" } else { "Brewfile.linux" }

# On Linux/WSL, mise's ruby sits ahead of Homebrew on PATH and its openssl.so
# links a newer OpenSSL than the system libcrypto; Homebrew would otherwise adopt
# that ruby and die loading openssl (e.g. during `brew bundle cleanup`). zshenv
# exports this for interactive `brew`, but `just` recipes must not depend on the
# interactive shell having sourced it — so force the vendored portable ruby here
# too. Empty (and thus a no-op) on macOS, where vendored ruby is already default.
export HOMEBREW_FORCE_VENDOR_RUBY := if os() == "macos" { "" } else { "1" }

# Update Homebrew packages and clean up. Tap trust is declared in the
# Brewfile (`trusted: true` on tap-prefixed formulae), never via an
# imperative `brew trust` step: `brew bundle cleanup --force` resets the
# trust store to exactly the Brewfile-declared `trusted:` entries, so
# hand-recorded trust is wiped on every run of this recipe. If the store
# lacks the entries (fresh tap clone, manual untrust), the first `brew
# update` may warn "Not trusted tap" once — harmless, and self-healing when
# `brew bundle install` applies the declared trust in the next step.
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
