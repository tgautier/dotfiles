# Zsh-specific ShellCheck codes to ignore (valid zsh syntax that ShellCheck
# doesn't understand when linting with --shell=bash)
zsh_excludes := "SC1036,SC1087,SC1090,SC2128,SC2145,SC2154,SC2155,SC2168,SC2179,SC2206,SC2211,SC2296"

# Run all CI checks
ci: lint-shell lint-python lint-markdown lint-brewfile lint-mise lint-just lint-rcrc lint-cleanup-symlinks test-rcm-links test-chezmoi-canary test-local-gate

[doc("Run the complete local gate and attest the exact clean HEAD")]
ci-attest:
    @bash .githooks/ci-attest

[doc("Fixture-test identity, pushed signatures, and exact-tip local CI evidence")]
test-local-gate:
    ./tests/test-local-gate

[doc("Compile tracked Python helpers with warnings promoted to errors")]
lint-python:
    PYTHONWARNINGS=error python3 -c 'from pathlib import Path; [compile(Path(path).read_text(encoding="utf-8"), path, "exec") for path in ("bin/rcm-links", "tests/test_rcm_links.py")]'

[doc("Fixture-test the read-only rcm link ownership inventory")]
test-rcm-links:
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_rcm_links.py' -v

[doc("Print the read-only ownership inventory for current and historical rcm HOME targets")]
link-inventory:
    python3 bin/rcm-links inventory --public-dir {{quote(public_dir)}} --private-dir {{quote(private_dir)}}

[doc("Print a digest-bound cleanup plan containing only current obsolete rcm links")]
link-cleanup-plan:
    python3 bin/rcm-links plan --public-dir {{quote(public_dir)}} --private-dir {{quote(private_dir)}}

[doc("Remove only obsolete links matching an explicitly approved cleanup plan and digest")]
link-cleanup plan confirm:
    python3 bin/rcm-links cleanup --public-dir {{quote(public_dir)}} --private-dir {{quote(private_dir)}} --plan {{quote(plan)}} --confirm {{quote(confirm)}}

[doc("Restore absent links from the same explicitly approved cleanup plan and digest")]
link-restore plan confirm:
    python3 bin/rcm-links restore --public-dir {{quote(public_dir)}} --private-dir {{quote(private_dir)}} --plan {{quote(plan)}} --confirm {{quote(confirm)}}

# Assert `rcrc` resolves the way README documents, on both halves of the
# override contract: DOTFILES_DIRS, which reaches the operator's real $HOME
# through rcm (a stray trailing slash becomes a doubled separator and rcm derives
# a wrongly-named link from it), and EXCLUDES, whose private sourcing fails
# silently behind a `2>/dev/null` when PRIVATE_DIR drifts. Both are pinned rather
# than asserted. Sourcing rcrc is side-effect-free: it only assigns, and its one
# external touch is that guarded grep.
[doc("Check rcrc resolves DOTFILES_DIRS + EXCLUDES and normalises the paths")]
lint-rcrc:
    #!/usr/bin/env bash
    set -euo pipefail
    # One place that sources rcrc under a clean environment. `var` picks which
    # resolved variable to read, so the DOTFILES_DIRS and EXCLUDES cases share
    # this rather than each hand-rolling its own `env -u … sh -c`.
    #
    # The `-u` pair is a clean-slate default, not a contradiction with a caller's
    # `NAME=value` operand: env processes options before operands, so an operand
    # deliberately re-supplies what `-u` cleared.
    read_var() {
        local var=$1; shift
        env -u DOTFILES_DIR -u DOTFILES_PRIVATE_DIR ${1:+"$@"} \
            sh -c 'set -e; . ./rcrc; eval "printf %s \"\${$1}\""' sh "$var"
    }
    resolve() { read_var DOTFILES_DIRS ${1:+"$@"}; }
    expect() {
        local label=$1 want=$2 got=$3
        if [[ "$got" != "$want" ]]; then
            echo "ERROR [$label]: want [$want] got [$got]" >&2
            exit 1
        fi
    }
    expect_has() {
        local label=$1 needle=$2 got=$3
        if [[ "$got" != *"$needle"* ]]; then
            echo "ERROR [$label]: expected to contain [$needle], got [$got]" >&2
            exit 1
        fi
    }
    expect_lacks() {
        local label=$1 needle=$2 got=$3
        if [[ "$got" == *"$needle"* ]]; then
            echo "ERROR [$label]: expected NOT to contain [$needle], got [$got]" >&2
            exit 1
        fi
    }

    home_default="$HOME/Workspace/tgautier/dotfiles"
    priv_default="$HOME/Workspace/tgautier/dotfiles-private"

    expect "no override" \
        "$home_default $priv_default" "$(resolve)"
    expect "both overridden" \
        "/tmp/pub /tmp/priv" "$(resolve DOTFILES_DIR=/tmp/pub DOTFILES_PRIVATE_DIR=/tmp/priv)"
    expect "private only" \
        "$home_default /tmp/priv" "$(resolve DOTFILES_PRIVATE_DIR=/tmp/priv)"
    # One trailing slash, and several — `${VAR%/}` alone strips only one, which
    # is why rcrc loops.
    expect "single trailing slash" \
        "/tmp/pub $priv_default" "$(resolve DOTFILES_DIR=/tmp/pub/)"
    expect "multiple trailing slashes" \
        "/tmp/pub $priv_default" "$(resolve DOTFILES_DIR=/tmp/pub///)"
    # A root value must survive as `/`, never collapse to empty — an empty entry
    # in DOTFILES_DIRS would make the derived prefix match anything.
    expect "root value not emptied" \
        "$home_default /" "$(resolve DOTFILES_PRIVATE_DIR=/)"

    # EXCLUDES is the other half of the contract, and the one rcrc's own header
    # names as the silent-failure path: if PRIVATE_DIR drifts, the exclude
    # sourcing no-ops behind `2>/dev/null` and rcup resumes hanging on the
    # excluded directory — a well-formed DOTFILES_DIRS with an EXCLUDES quietly
    # missing every private pattern. Pin the path derivation and the
    # comment/blank-line filter together.
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    # The regex's two alternatives, its `[[:space:]]*` tolerance and the `tr` join
    # are each pinned, but by DIFFERENT assertions — don't delete either one
    # believing the other covers it:
    #
    #   fixture ingredient      pins                      caught by
    #   ----------------------  ------------------------  ---------------------------
    #   two patterns            the `tr` join             expect_has (joined needle)
    #   blank line, mid-list    the `$` alternative       expect_has (joined needle)
    #   indented comment        `#` alt + `[[:space:]]*`  expect_lacks "comment"
    #
    # Boundary, so the table isn't read as totality over the whole pipeline.
    # `-v` and `-E` are pinned incidentally — drop either and the joined-needle
    # assertion fails (it runs first and exits, so the expect_lacks case is never
    # reached): without `-v` only the comment and blank lines survive, and without
    # `-E` the pattern is a BRE where `(`, `)` and `|` are literal, so nothing
    # matches and every line survives. `-h` is NOT pinned and cannot be here:
    # grep only prefixes filenames for multiple inputs or `-H`, and rcrc passes
    # exactly one file, so dropping it changes nothing observable.
    #
    # The fixture's column-0 comment pins nothing on its own — drop the `#`
    # alternative and the INDENTED comment still survives `^[[:space:]]*$`, so
    # expect_lacks fires from it alone. It stays as belt and braces.
    #
    # The blank line sits BETWEEN the patterns on purpose: a leaked blank then
    # breaks the contiguity of "sentinel-pattern second-pattern". Before the first
    # pattern it would only add a space outside the needle and slip through.
    # A leaked comment, by contrast, survives as leading tokens that don't break
    # that contiguity, which is why it needs expect_lacks rather than the needle.
    printf '# a comment line\n\t  # indented comment\nsentinel-pattern\n\nsecond-pattern\n' \
        > "$tmp/rcm-excludes"
    excludes=$(read_var EXCLUDES DOTFILES_PRIVATE_DIR="$tmp")
    expect_has   "EXCLUDES sources the private file" "sentinel-pattern second-pattern" "$excludes"
    expect_lacks "EXCLUDES drops comment lines"      "comment"                         "$excludes"
    # An absent private repo must leave the base excludes intact, not blank.
    excludes=$(read_var EXCLUDES DOTFILES_PRIVATE_DIR="$tmp/nope")
    expect_has   "absent private repo keeps base EXCLUDES" "CHANGELOG.md" "$excludes"
    expect_has   "base EXCLUDES keeps chezmoi metadata private" ".chezmoiroot" "$excludes"
    expect_has   "base EXCLUDES keeps test harnesses private" "tests" "$excludes"

    # The strip helper and its temp var must not leak into the sourcing shell.
    leaked=$(sh -c '. ./rcrc; printf "%s" "${_v-unset}"')
    if [[ "$leaked" != "unset" ]]; then
        echo "ERROR: rcrc leaked \$_v into the sourcing shell as [$leaked]" >&2
        exit 1
    fi
    if sh -c '. ./rcrc; command -v _rcrc_strip_slashes' >/dev/null 2>&1; then
        echo "ERROR: rcrc left _rcrc_strip_slashes defined in the sourcing shell" >&2
        exit 1
    fi
    echo "rcrc OK (defaults, both overrides, slash normalisation, root value, EXCLUDES sourcing, no leaks)"

[doc("Render the chezmoi canary in an isolated HOME and verify source equivalence plus idempotence")]
test-chezmoi-canary:
    ./tests/test-chezmoi-canary

[doc("Remove the retired iTerm2 symlink after migrating to Ghostty")]
cleanup-retired-iterm:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "${PLATFORM:-}" != "macos" ] && [ "$(uname -s)" != "Darwin" ]; then
        echo "retired iTerm2 cleanup is macOS-only" >&2
        exit 1
    fi
    target="$HOME/.iterm2/com.googlecode.iterm2.plist"
    if [ -L "$target" ]; then
        link=$(readlink "$target")
        case "$link" in
            */iterm2/com.googlecode.iterm2.plist)
                rm "$target"
                echo "removed retired iTerm2 symlink: $target"
                ;;
            *)
                echo "refusing to remove non-rcm symlink: $target -> $link" >&2
                exit 1
                ;;
        esac
    else
        echo "retired iTerm2 symlink absent: $target"
    fi

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
        # `|| true` so a no-match pipeline yields an empty string instead of
        # aborting under `pipefail`, in any caller's `-e` context.
        called=$(scan "$file" || true)
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
    just git-hooks
    if command -v roborev >/dev/null 2>&1; then roborev install-hook; fi

    # 5. Native-installer tools (self-update through their own channels).
    command -v claude >/dev/null 2>&1 || curl -fsSL https://claude.ai/install.sh | bash
    command -v hermes >/dev/null 2>&1 || curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

    # 6. Default editor associations (macOS only; no-ops elsewhere).
    just set-default-editor

    # 7. Linux/WSL: symlink libsqlite3 for Dart/Flutter FFI (no-op on macOS).
    {{ if os() == "macos" { "true" } else { "just _link-libsqlite3" } }}

[doc("Wire the tracked Git hooks in this checkout or worktree")]
git-hooks:
    git config --local core.hooksPath .githooks
    @echo "Git hooks wired for this checkout"

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

# Lint shell scripts with ShellCheck.
#
# Rationale lives here rather than in the body: this is a LINEWISE recipe, so
# every indented line — comments included — is echoed and handed to a shell.
#
# `rcrc` is checked with --shell=sh, not in the zsh group below, because rcm
# sources it and it must stay portable to whatever shell rcm uses. SC2034
# (appears unused) is excluded for that file ONLY: setting variables for rcm to
# read IS its purpose, so every assignment is consumed externally. Scoped to the
# file rather than added to the shared zsh_excludes list.
[doc("Lint shell scripts with ShellCheck")]
lint-shell:
    shellcheck --severity=warning bin/op-ssh-sign bin/kshow bin/kseal
    shellcheck --severity=warning tests/check-chezmoi-targets tests/test-chezmoi-canary tests/test-local-gate
    shellcheck --severity=warning .githooks/pre-commit .githooks/pre-push .githooks/ci-attest .githooks/lib/*.sh
    shellcheck --severity=warning --shell=sh --exclude=SC2034 rcrc
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

# Companion repo paths. Anchor them to $HOME rather than deriving them from
# dotfiles_dir. Inside a nested worktree, dotfiles_dir points at the worktree;
# its sibling is not the configured private checkout.
#
# DOTFILES_DIR / DOTFILES_PRIVATE_DIR are the shared contract across the two
# remaining consumers: `DOTFILES_DIRS` + `EXCLUDES` in `rcrc`, and the repo list
# in `_scan-stale-symlinks`.
#
# The two defaults below live in three places on purpose — here, `rcrc`, and
# `lint-rcrc`'s expected values (which run under `env -u`, so they cannot
# inherit these). Change one, change all three; see the note in `rcrc`.
public_dir := env("DOTFILES_DIR", env("HOME") / "Workspace/tgautier/dotfiles")
private_dir := env("DOTFILES_PRIVATE_DIR", env("HOME") / "Workspace/tgautier/dotfiles-private")

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

# Exercise `_scan-stale-symlinks` against a fixture tree. The recipe it tests
# ends in `rm` (via `cleanup-symlinks`), so both halves of the union predicate
# and — critically — the SURVIVAL case get pinned: a broken symlink that points
# nowhere near a dotfiles checkout must NOT be reported. A deletion test without
# a survival case only proves the sweeper deletes something.
#
# Each case re-invokes `just` as a subprocess because public_dir/private_dir are
# `env()` variables resolved at justfile load, so varying them requires a fresh
# process rather than an in-recipe assignment.
[doc("Test the stale-symlink scanner against fixtures (positive and negative)")]
lint-cleanup-symlinks:
    #!/usr/bin/env zsh
    set -eu
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    fake_home="$tmp/home"
    # An override whose basename is deliberately NOT `dotfiles*`, which is the
    # case the segment predicate alone cannot see.
    override="$tmp/dots-private"
    mkdir -p "$fake_home" "$override" "$tmp/public"

    # 1. broken link into the override checkout -> prefix predicate must fire
    ln -s "$override/zshrc" "$fake_home/.zshrc"
    # 2. broken link into a FORMER checkout path -> segment predicate must fire.
    #    Nothing configured points here; only `*/dotfiles/*` matches it.
    ln -s "$tmp/former/checkout/dotfiles/gitconfig" "$fake_home/.gitconfig"
    # 3. an unrelated broken link -> must SURVIVE (the boundary case)
    ln -s "$tmp/somewhere-else/thing" "$fake_home/.unrelated"

    scan() {
        DOTFILES_DIR="$tmp/public" DOTFILES_PRIVATE_DIR="$1" \
            CLEANUP_HOME="$fake_home" just _scan-stale-symlinks
    }

    assert_scan() {
        local label=$1 out=$2
        if ! grep -q '/.zshrc ->' <<<"$out"; then
            echo "ERROR [$label]: prefix predicate missed a link into a non-dotfiles-named override" >&2
            echo "$out" >&2; exit 1
        fi
        if ! grep -q '/.gitconfig ->' <<<"$out"; then
            echo "ERROR [$label]: segment predicate missed a link into a former checkout path" >&2
            echo "$out" >&2; exit 1
        fi
        if grep -q '/.unrelated ->' <<<"$out"; then
            echo "ERROR [$label]: swept an unrelated broken symlink — the survival case failed" >&2
            echo "$out" >&2; exit 1
        fi
    }

    assert_scan "plain override" "$(scan "$override")"
    # Shell completion appends a trailing slash routinely; `:a` must absorb it,
    # or the derived prefix becomes `…//*` and matches no single-slash target.
    assert_scan "trailing-slash override" "$(scan "$override/")"

    # An absent configured dir must be a no-op, not fatal — `rcrc` already
    # treats a missing private repo that way. Dropping `(N)` from the repos glob
    # makes zsh abort the scan with "no matches found" instead, which this case
    # catches: the scan must still run, still fire the segment predicate, and
    # still spare the unrelated link.
    out=$(scan "$tmp/nonexistent-private")
    if ! grep -q '/.gitconfig ->' <<<"$out"; then
        echo "ERROR: an absent configured dir broke the scan or the segment predicate" >&2
        echo "$out" >&2; exit 1
    fi
    if grep -q '/.unrelated ->' <<<"$out"; then
        echo "ERROR: an absent configured dir widened the predicate past the survival case" >&2
        echo "$out" >&2; exit 1
    fi
    # The sweep half can't be driven against a fixture tree — it deliberately
    # refuses CLEANUP_HOME so nothing can redirect its `rm`. So bind the
    # assertion to `cleanup-symlinks`' ACTUAL body instead: the two behaviour
    # cases below would otherwise only prove a fact about zsh expansion, leaving
    # a weakened `%%` in the real recipe green. Same convention as `lint-just`'s
    # `check()` — exercise the real logic, never a copy of it.
    #
    # Comment lines are stripped first so the match can't be satisfied by a
    # comment that merely mentions the expansion.
    body=$(just --dump --dump-format json \
              | jq -r '.recipes["cleanup-symlinks"].body | flatten | .[]' \
              | grep -vE '^[[:space:]]*#')
    if ! grep -qF 'link="${entry%% ->*}"' <<<"$body"; then
        echo "ERROR: cleanup-symlinks no longer extracts the link with \${entry%% ->*}." >&2
        echo "       A single % strips the SHORTEST match, so a target containing ' -> '" >&2
        echo "       would feed rm a path that does not exist. Update this lint only if" >&2
        echo "       the replacement is equivalent." >&2
        exit 1
    fi
    extract() { local entry=$1; printf '%s' "${entry%% ->*}"; }
    got=$(extract "$fake_home/.zshrc -> $override/zshrc")
    if [[ "$got" != "$fake_home/.zshrc" ]]; then
        echo "ERROR: link extraction returned '$got'" >&2; exit 1
    fi
    # A target may itself contain ' -> ' (a link to a link's printed form).
    # `%%` strips the LONGEST match, so the link must survive intact; `%` would
    # have kept part of the target and fed `rm` a path that does not exist.
    got=$(extract "$fake_home/.zshrc -> $override/a -> b")
    if [[ "$got" != "$fake_home/.zshrc" ]]; then
        echo "ERROR: link extraction broke on a target containing ' -> ': '$got'" >&2; exit 1
    fi
    echo "cleanup-symlinks scanner OK (union predicate, trailing slash, absent dir, survival case, link parsing)"

# Print every stale symlink (broken, and pointing into a dotfiles checkout) as
# a `link -> target` line. No removal — `cleanup-symlinks` owns that, so this
# recipe is safe to drive from the fixtures in `lint-cleanup-symlinks`.
#
# CLEANUP_HOME overrides the tree to scan (default $HOME). It is honoured HERE
# ONLY, never by `cleanup-symlinks`: a stray export must not be able to redirect
# an `rm` into an unexpected tree.
#
# The predicate is a UNION of two matches, because neither subsumes the other:
#
#   1. Basename-segment match on the literal `dotfiles` / `dotfiles-private`
#      path components. rcm records ABSOLUTE targets, so after a checkout is
#      moved or renamed the leftover links still name the OLD path — which is
#      the main thing a stale sweeper is for. A prefix built from the CURRENT
#      paths cannot see those, and setting the override to the new location
#      does not help, because the stale targets name the old one.
#   2. Prefix match against the configured dirs, which is what catches a
#      checkout whose basename is not `dotfiles*` at all (DOTFILES_PRIVATE_DIR
#      pointed at e.g. ~/dev/dots-private).
#
# #214 replaced (1) with (2) and lost the moved-checkout case; this keeps both.
[doc("Print stale $HOME symlinks pointing into a dotfiles checkout (no removal)")]
_scan-stale-symlinks:
    #!/usr/bin/env zsh
    set -u
    scan_home="${CLEANUP_HOME:-$HOME}"

    # `:a` absolutises and cleans, so a trailing slash (shell completion adds
    # one routinely), a doubled slash, or a `..` segment can't produce a prefix
    # that matches nothing while glob-based discovery still succeeds. NOT `:A`,
    # which also resolves symlinks: rcm recorded whatever DOTFILES_DIRS said, so
    # resolving could stop matching the targets actually on disk.
    # quote() not "…": double quotes protect spaces but not `$`, backtick or
    # backslash, and this value gates an `rm`. Matches the convention already
    # used for set-profile's argument. A glob qualifier after a single-quoted
    # word is valid zsh.
    repos=({{ quote(public_dir) }}(N:a) {{ quote(private_dir) }}(N:a))
    # (N) above drops a configured dir that doesn't exist on this machine, so an
    # absent private repo contributes no prefix. Without it zsh aborts the whole
    # scan with "no matches found" (verified), making an absent private repo
    # fatal rather than the no-op `rcrc` already treats it as.

    # Discovery of nested link dirs needs the repos to exist; the prefix
    # predicate does not. Keep them independent so a moved checkout is still
    # swept even when no configured dir is present.
    nested=()
    for repo in "${repos[@]}"; do
        for d in "$repo"/*(N/); do
            name=${d:t}
            # Skip repo-only dirs that rcm doesn't symlink
            [[ "$name" == .* || "$name" == README* || "$name" == CLAUDE* ]] && continue
            candidate="$scan_home/.$name"
            [[ -d "$candidate" ]] && nested+=("$candidate")
        done
    done

    is_stale() {
        local target=$1 repo
        # (1) former-or-current checkout, matched by path segment
        [[ "$target" == */dotfiles/* || "$target" == */dotfiles-private/* ]] && return 0
        # (2) configured checkout under any basename
        for repo in "${repos[@]}"; do
            [[ "$target" == "$repo"/* ]] && return 0
        done
        return 1
    }

    stale=()
    # Top-level dotfiles (non-recursive)
    for f in $scan_home/.[^.]*(N@); do
        [[ -e "$f" ]] && continue
        target=$(readlink "$f")
        is_stale "$target" && stale+=("$f -> $target")
    done
    # Nested dirs (recursive)
    for dir in "${nested[@]}"; do
        [[ -d "$dir" ]] || continue
        for f in "$dir"/**/*(N@); do
            [[ -e "$f" ]] && continue
            target=$(readlink "$f")
            is_stale "$target" && stale+=("$f -> $target")
        done
    done
    (( ${#stale} == 0 )) && exit 0
    printf '%s\n' "${stale[@]}"

# Remove stale symlinks in $HOME that point into dotfiles dirs
[doc("Remove stale $HOME symlinks pointing into a dotfiles checkout")]
cleanup-symlinks:
    #!/usr/bin/env zsh
    set -u
    # Always the real $HOME: CLEANUP_HOME is deliberately not forwarded, so no
    # environment setting can point this recipe's `rm` at another tree.
    #
    # Check the scan's status explicitly. A bare `stale=("${(@f)$(scan)}")` would
    # turn a failed scan into empty output and then report "No stale symlinks
    # found" — announcing a clean tree on the strength of a crash.
    if ! out=$(CLEANUP_HOME= just _scan-stale-symlinks); then
        echo "cleanup-symlinks: the stale-symlink scan failed; nothing removed." >&2
        exit 1
    fi
    stale=("${(@f)out}")
    # A single empty element is what $(…) yields for no output; treat as none.
    [[ ${#stale} -eq 1 && -z "${stale[1]}" ]] && stale=()
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
