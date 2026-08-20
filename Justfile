# Zsh-specific ShellCheck codes to ignore (valid zsh syntax that ShellCheck
# doesn't understand when linting with --shell=bash)
zsh_excludes := "SC1036,SC1087,SC1090,SC2128,SC2145,SC2154,SC2155,SC2168,SC2179,SC2206,SC2211,SC2296"

# Run all CI checks
ci: lint-shell lint-python lint-markdown lint-brewfile lint-mise lint-mise-config-hygiene lint-just lint-cleanup-symlinks test-private-chezmoi-bridge test-chezmoi-operator test-setup-helpers test-chezmoi-canary test-local-gate

[doc("Run the complete local gate and attest the exact clean HEAD")]
ci-attest:
    @bash .githooks/ci-attest

[doc("Publish the pushed exact-tip attestation for GitHub branch protection")]
ci-publish:
    @bash .githooks/ci-publish

[doc("Fixture-test identity, pushed signature headers, and exact-tip local CI evidence")]
test-local-gate:
    ./tests/test-local-gate

[doc("Compile tracked Python helpers with warnings promoted to errors")]
lint-python:
    PYTHONWARNINGS=error python3 -c 'from pathlib import Path; [compile(Path(path).read_text(encoding="utf-8"), path, "exec") for path in ("bin/chezmoi-cutover", "tests/private_chezmoi_bridge.py", "tests/setup_acceptance.py", "tests/test_chezmoi_cutover.py", "tests/test_private_chezmoi_bridge.py", "tests/test_setup_helpers.py")]'

[doc("Fixture-test bounded, output-withholding private chezmoi orchestration")]
test-private-chezmoi-bridge:
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_private_chezmoi_bridge.py' -v

[doc("Fixture-test guarded public/private chezmoi operation and recovery")]
test-chezmoi-operator:
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_chezmoi_cutover.py' -v

[doc("Run setup twice from a fresh public checkout into an isolated HOME")]
test-setup-acceptance:
    PYTHONDONTWRITEBYTECODE=1 python3 tests/setup_acceptance.py

[doc("Run fresh setup acceptance with and without the private companion")]
test-setup-acceptance-private:
    PYTHONDONTWRITEBYTECODE=1 python3 tests/setup_acceptance.py --private-source {{quote(private_dir)}}

[doc("Fixture-test setup-owned platform compatibility links")]
test-setup-helpers:
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_setup_helpers.py' -v

[doc("Show how managed public and private targets differ from their source state")]
chezmoi-status:
    python3 bin/chezmoi-cutover status --public-dir {{quote(public_dir)}} --private-dir {{quote(private_dir)}}

[doc("Print the public and private target-state diff without applying it")]
chezmoi-diff:
    python3 bin/chezmoi-cutover diff --public-dir {{quote(public_dir)}} --private-dir {{quote(private_dir)}}

[doc("Preview the public and private apply without changing managed targets")]
chezmoi-apply-dry-run:
    python3 bin/chezmoi-cutover dry-run --public-dir {{quote(public_dir)}} --private-dir {{quote(private_dir)}}

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
                echo "refusing to remove unrecognized symlink: $target -> $link" >&2
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

# Bootstrap this machine: profile, packages, dotfiles, runtimes, hooks, tools (idempotent)
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

    # 2. Refresh dotfiles through their manifest-declared owners. Called here
    #    rather than declared as a dependency because dependencies run before
    #    the recipe body, and chezmoi comes from the bundle in step 1.
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

# Run this after editing managed config. The operator validates public/private
# ownership in isolation, applies the public and private chezmoi sources without
# force, and runs the private dedicated owners when that checkout exists. Both
# apply passes must finish settled. An absent private repo is skipped, not fatal.
#
# Must be run from this checkout: `~/.justfile` is a symlink to the PRIVATE
# repo's justfile, so `just link` from $HOME resolves there and fails with an
# unknown-recipe error. The [doc] attribute carries the summary because `just
# --list` would otherwise show only the last line of this comment.
[doc("Refresh dotfiles through their manifest-declared owners")]
link:
    python3 bin/chezmoi-cutover link --public-dir {{quote(public_dir)}} --private-dir {{quote(private_dir)}}

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
    target="$HOME/.local/lib/flutter-ffi/libsqlite3.so"
    mkdir -p "$(dirname "$target")"
    if [ -L "$target" ]; then
        current=$(readlink "$target")
        if [ "$current" = "$src" ]; then
            echo "link already current: $target -> $src"
            exit 0
        fi
        echo "refusing to replace foreign symlink: $target -> $current" >&2
        exit 1
    fi
    if [ -e "$target" ]; then
        echo "refusing to replace non-symlink target: $target" >&2
        exit 1
    fi
    ln -s "$src" "$target"
    echo "linked $src -> $target"

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
[doc("Lint shell scripts with ShellCheck")]
lint-shell:
    shellcheck --severity=warning bin/op-ssh-sign bin/kshow bin/kseal
    shellcheck --severity=warning tests/check-chezmoi-targets tests/test-chezmoi-canary tests/test-local-gate
    shellcheck --severity=warning .githooks/pre-commit .githooks/pre-push .githooks/ci-attest .githooks/ci-publish .githooks/lib/*.sh
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

# Reject secret-shaped content in the mise config. This file is deployed as a
# SYMLINK into this public checkout (see docs/chezmoi-targets.tsv), so mise
# writes straight through to a tracked, public file: `mise use`, `mise settings
# set` and `mise upgrade --bump` all edit it in place. Tool pins are fine, but
# an `[env]` table or a credential-shaped key would be committed to a public
# repo by a tool the operator never asked to review. Blocked outright rather
# than reviewed by eye, per claude/rules/public-repo-hygiene.md: the operator
# should not have to notice.
#
# The fixtures below are not decorative. A detector whose only evidence is a
# clean run on a clean file is indistinguishable from a dead one, so each
# planted secret must be caught AND each legitimate line must survive. The
# `dartsdk-` case is the near miss that motivated anchoring the OpenAI-key arm
# to a length: an unanchored `sk-` matches nothing in `dartsdk-`, but the arm
# is one careless edit away from doing so.
lint-mise-config-hygiene:
    #!/usr/bin/env bash
    set -euo pipefail
    config="config/mise/config.toml"
    [[ -f "$config" ]] || { echo "ERROR: missing $config" >&2; exit 1; }

    pattern='^[[:space:]]*\[env([].]|$)|^[[:space:]]*[A-Za-z0-9_]*(token|secret|password|passwd|credential|api_?key)[A-Za-z0-9_]*[[:space:]]*=|ghp_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}|sk-[A-Za-z0-9]{16,}|AKIA[A-Z0-9]{12,}|xoxb-[A-Za-z0-9-]{10,}'

    # Redirect to /dev/null rather than using `grep -q`: under `set -o pipefail`
    # an early-exiting consumer SIGPIPEs the producer and inverts the verdict
    # (see claude/rules/shell.md). Here the input is a file, not a pipe, but the
    # habit is what keeps the next edit safe.
    scan() { grep -niE "$pattern" "$1" > /dev/null; }

    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT

    # Every planted secret must be caught.
    caught=0
    while IFS= read -r probe; do
        [[ -n "$probe" ]] || continue
        printf '%s\n' "$probe" > "$tmp/probe.toml"
        if ! scan "$tmp/probe.toml"; then
            echo "ERROR: mise hygiene guard missed a planted secret: $probe" >&2
            exit 1
        fi
        caught=$((caught + 1))
    done <<'PROBES'
    [env]
    [env.PATH]
    GITHUB_TOKEN = "x"
    api_key = "y"
    MY_SECRET="z"
    x = "ghp_abcdefghijklmnopqrst"
    k = "sk-abcdefghijklmnopqrstuvwx"
    a = "AKIAABCDEFGHIJKLMN"
    PROBES
    [[ "$caught" -eq 8 ]] || { echo "ERROR: expected 8 planted secrets, scanned $caught" >&2; exit 1; }

    # Every legitimate line must survive, or the guard blocks real config.
    survived=0
    while IFS= read -r probe; do
        [[ -n "$probe" ]] || continue
        printf '%s\n' "$probe" > "$tmp/probe.toml"
        if scan "$tmp/probe.toml"; then
            echo "ERROR: mise hygiene guard false-positived on: $probe" >&2
            exit 1
        fi
        survived=$((survived + 1))
    done <<'ALLOWED'
    dart = { url = "https://x/dartsdk-macos-arm64-release.zip" }
    trusted_config_paths = ["~/Workspace/tgautier"]
    node = "26"
    not_found_auto_install = true
    ALLOWED
    [[ "$survived" -eq 4 ]] || { echo "ERROR: expected 4 allowed lines, scanned $survived" >&2; exit 1; }

    # The real file, last: the fixtures above prove the verdict means something.
    if scan "$config"; then
        echo "ERROR: secret-shaped content in $config, which is a PUBLIC tracked file:" >&2
        grep -niE "$pattern" "$config" >&2
        echo "Route the value to dotfiles-private instead. See claude/rules/public-repo-hygiene.md." >&2
        exit 1
    fi
    echo "mise config hygiene OK ($caught planted secrets caught, $survived allowed lines survived)"

# Update everything (brew, mac app store, mise, rust)
update: update-brew update-mas update-mise update-rust

# Resolve through symlink so this works when just finds ~/.justfile
dotfiles_dir := parent_directory(canonicalize(justfile()))

# Companion repo paths. Anchor them to $HOME rather than deriving them from
# dotfiles_dir. Inside a nested worktree, dotfiles_dir points at the worktree;
# its sibling is not the configured private checkout.
#
# DOTFILES_DIR / DOTFILES_PRIVATE_DIR are the shared contract with the stale
# symlink scanner (_scan-stale-symlinks).
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

    # An absent configured dir must be a no-op, not fatal. Dropping `(N)` from
    # the repos glob
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
#      path components. After a checkout is moved or renamed the leftover
#      symlinks still name the OLD path — which is
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
    # which also resolves symlinks: targets were recorded as whatever DOTFILES_DIRS
    # said, so resolving could stop matching the targets actually on disk.
    # quote() not "…": double quotes protect spaces but not `$`, backtick or
    # backslash, and this value gates an `rm`. Matches the convention already
    # used for set-profile's argument. A glob qualifier after a single-quoted
    # word is valid zsh.
    repos=({{ quote(public_dir) }}(N:a) {{ quote(private_dir) }}(N:a))
    # (N) above drops a configured dir that doesn't exist on this machine, so an
    # absent private repo contributes no prefix. Without it zsh aborts the whole
    # scan with "no matches found" (verified), making an absent private repo
    # fatal rather than a no-op.

    # Discovery of nested link dirs needs the repos to exist; the prefix
    # predicate does not. Keep them independent so a moved checkout is still
    # swept even when no configured dir is present.
    nested=()
    for repo in "${repos[@]}"; do
        for d in "$repo"/*(N/); do
            name=${d:t}
            # Skip repo-only dirs that aren't deployed to HOME
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

[doc("Run setup acceptance in a Linux container (public-only)")]
test-setup-acceptance-linux:
    bash tests/run-linux-acceptance.sh

[doc("Run setup acceptance in a Linux container with private companion")]
test-setup-acceptance-linux-private:
    bash tests/run-linux-acceptance.sh {{quote(private_dir)}}
