# Changelog

All notable changes to this dotfiles repo are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This is a rolling configuration repo with no tagged releases, so entries are
grouped by **date** rather than by semantic version. Newest first.

## [Unreleased]

### Added

- Optional two-source orchestration in the public chezmoi canary. A stdlib Python bridge runs the companion ownership preflight before the first public apply and the companion's isolated source canary after the public second apply is a no-op. It replaces inherited HOME and XDG paths, scrubs Python, virtual-environment, and Git state, withholds all companion output, and performs bounded process-group cleanup after every checker exit. An absent companion reports a generic skip and preserves the complete public-only canary. Rcm remains the live deployment owner, and no command applies chezmoi to the real HOME ([#232](https://github.com/tgautier/dotfiles/issues/232)).
- A digest-bound pre-cutover backup and rcm restoration rehearsal. The operator compares the complete public and effective private manifests with `lsrc`, requires every live target to be its exact absolute rcm symlink, and publishes a private mode-`0600` artifact without replacing an existing destination. Public-only operation distinguishes a genuinely absent private checkout from invalid existing paths, and manifest defaults follow repository overrides. Restore requires the reviewed digest, revalidates the manifests and repository roots, preserves the configured private path even when that checkout is absent, invokes rcm with force replacement, hooks disabled, and non-option source operands only, then verifies every raw link target. Isolated fixtures cover public/private capture, manifest drift, tampering, foreign links, destination reuse, complete restore, and retry after a partial rcm failure. No real HOME apply or cutover occurs in this checkpoint ([#232](https://github.com/tgautier/dotfiles/issues/232)).
- Cross-repository chezmoi ownership validation in the public parity canary. Before its first isolated apply, the canary invokes the private companion's committed target-ownership checker with Python-specific environment overrides and site-package discovery disabled, fails on an incompatible checkout, and reports an explicit public-only skip when it is absent. Behavioral fixtures cover the available, conflicting-package, absent, non-directory, stale, and rejecting-checker paths while rcm and the real HOME remain unchanged ([#232](https://github.com/tgautier/dotfiles/issues/232)).
- A self-contained exact-tip local shipping gate that replaces hosted Actions. `just ci-attest` revokes prior evidence, runs the complete repository checks, and atomically records only an unchanged clean `HEAD`. Pre-push rejects direct protected-branch updates, post-cutoff ancestry without Git signature headers, shallow history, dirty or wrong checkout state, hook ownership mismatches, and missing, malformed, or stale evidence. After the SSH push, `just ci-publish` verifies the exact remote tip and current `main` ancestry, publishes the external `local/exact-tip` status, and reads it back; strict branch protection requires that status and an up-to-date branch before squash merge. `just git-hooks` wires each checkout without requiring the private companion repository, and focused positive and negative fixtures cover the failure boundaries ([#254](https://github.com/tgautier/dotfiles/pull/254)).
- A read-only rcm link ownership inventory that compares exact `lsrc` mappings with current and historical HOME roots, preserves declared dedicated installer links, and distinguishes obsolete links from unclassified collisions before the chezmoi backup rehearsal. Candidate roots include tracked, untracked, and ignored current top-level repository entries, while discovered HOME paths use their stored spelling so case aliases cannot duplicate one physical entry. Digest-bound cleanup and restore commands revalidate the configured repositories, ownership disposition, raw link targets, and real-directory ancestors before changing HOME. Historical discovery is explicitly bounded to each canonical checkout's current `HEAD` ancestry; as a conservative prerequisite, inventory rejects any shallow repository and directs the operator to run `git fetch --unshallow` before retrying ([#249](https://github.com/tgautier/dotfiles/issues/249)).
- A machine-readable complete rcm inventory and exact chezmoi parity guard. The guard verifies every shadow target/source mapping, rendered bytes, executable modes, isolated idempotent apply, and sabotage fixtures while keeping rcm active ([#248](https://github.com/tgautier/dotfiles/issues/248)).
- Chezmoi Phase 1 scaffolding: `.chezmoiroot` reserves `home/` for future
  source state, `docs/chezmoi-targets.tsv` records the pre-migration rcm target
  dispositions, and chezmoi is declared in the macOS/Linux Brewfiles.
  The rcm cutover remains deferred until shadow-apply and rollback evidence is
  complete ([#232](https://github.com/tgautier/dotfiles/issues/232)).
- `brew "cargo-audit"` in `Brewfile` and `Brewfile.linux`. A project's `just pre-push` invokes `cargo audit`; with the tool absent the recipe fails on the missing subcommand — and until that repo wired the recipe in, the audit simply never ran on this machine, letting four RUSTSEC advisories sit invisible. Declaring it in the bundle makes the gate real on every machine. ([#230](https://github.com/tgautier/dotfiles/pull/230))
- `brew "kimi-code"` (Moonshot's terminal coding agent) in `Brewfile.personal`,
  under a new `# CLI Tools & Development` block — the first formula in an
  overlay, which until now carried only `# Applications` and Mac App Store
  entries. It had been installed by hand and was therefore uninstalled by the
  `brew bundle cleanup --force` in `update-brew`, which is the pipeline working
  as designed: undeclared packages do not survive. `.claude/rules/brewfile.md`
  now states where a `brew` entry goes in an overlay, rather than enumerating
  two blocks as if they were the whole set
  ([#226](https://github.com/tgautier/dotfiles/issues/226)).
- `README.md` reference tables for the executable and configuration surface,
  which was previously discoverable only by `ls`: **Scripts (`bin/`)** (4),
  **Shell functions (`zsh/functions/`)** (10), **Aliases (`zsh/zaliases`)**,
  **Git hooks (`.githooks/`)** (3), **Configuration files**, and a **Shell load
  order** block. Every row was enumerated from the tree at authoring time rather
  than from memory — which caught two claims that would have shipped wrong: `bin/`
  reaches `PATH` as `~/.bin` via `zshenv`, not `~/bin`, and the functions are
  autoloaded because `zsh/zcompletion` prepends `~/.zsh/functions` to `fpath`.
  Review of the tables then caught three more: `git_template/` is linked but
  never wired to `init.templateDir`, `load_env_kops` exports AWS credentials
  rather than merely checking a variable, and the load-order block omitted
  `~/.zshrc.local` — the one hook a reader would use for machine-local config,
  which matters more now that `CLAUDE.md` defers here instead of keeping its own
  copy. `~/.zshrc.local`'s position is documented precisely: `zshrc` sources it
  *near* the end, with zsh-syntax-highlighting and `mise activate zsh` after it,
  so mise wins for any runtime it manages while a `PATH` entry for anything else
  survives. Plus the two markdownlint configs, missing from a `Structure` block
  whose commit message had claimed exhaustiveness; the block now states its own
  exclusion rule so the two remaining omissions read as deliberate.
  The `Structure` block is refreshed for everything it had drifted past —
  `zlogin`, `.githooks/`, `.claude/`, `CLAUDE.md`, `Brewfile.work` /
  `Brewfile.personal`, `CHANGELOG.md`, `.roborev.toml`, `gitignore`,
  `git_template/`, `agignore`, `editorconfig`, `psqlrc` and `iterm2/`.
  `CLAUDE.md`'s load-order line gains the missing `zlogin` step and now defers to
  the README section instead of carrying a second partial copy
  ([#219](https://github.com/tgautier/dotfiles/issues/219)).
- `DOTFILES_DIR` / `DOTFILES_PRIVATE_DIR` are now honoured by both remaining
  consumers. `rcrc` reads them for `DOTFILES_DIRS` and `EXCLUDES` (it is sourced
  as shell by rcm, which is exactly why it can), and the stale-symlink scanner
  derives its repo list from them. Documented in `README.md` → Custom checkout
  locations
  ([#215](https://github.com/tgautier/dotfiles/issues/215)).
- `just lint-rcrc`, wired into `just ci` — pins both halves of the override
  contract. For `DOTFILES_DIRS`: defaults with no override, each override alone
  and both together, one *and* several trailing slashes stripped, a root value
  surviving as `/` rather than collapsing to an empty entry (which would make the
  derived prefix match anything), and no helper or temp var leaking into the
  sourcing shell. For `EXCLUDES`: the private `rcm-excludes` file is actually
  sourced from the configured path, comment and blank lines are filtered out
  (including *indented* comments, so the filter's whitespace tolerance is
  exercised), multiple patterns are joined onto one line, and an absent private
  repo leaves the base excludes intact rather than blank. `EXCLUDES` is the half
  that fails silently — its sourcing hides behind a `2>/dev/null`, so a drifted
  path yields a well-formed `DOTFILES_DIRS` and no private patterns at all.
  `rcrc` is also now shellchecked (`--shell=sh`, since rcm sources it as
  POSIX shell), which it never was — `lint-shell` covered `bin/*` and the zsh
  files only. `SC2034` is excluded for that file alone, because setting
  variables for rcm to read is precisely its purpose
  ([#215](https://github.com/tgautier/dotfiles/issues/215)).
- `just lint-cleanup-symlinks`, wired into `just ci` — fixture-tests the
  stale-symlink scanner, which previously had no coverage at all despite ending
  in `rm`. Covers both halves of the predicate, the trailing-slash case, an
  absent configured dir, and — the one that matters most — a **survival** case:
  an unrelated broken symlink must not be swept. Every scan assertion was
  verified to fail when the corresponding logic is sabotaged, so none of them is
  vacuous. The sweep half can't be driven against a fixture tree (it refuses
  `CLEANUP_HOME` by design), so what is covered there is the line parsing that
  decides which path `rm` receives, including a target containing ` -> `
  ([#215](https://github.com/tgautier/dotfiles/issues/215)).
- `just link` — re-applies the rcm symlinks on their own, so an edit to a
  symlinked dotfile (`gitconfig`, `zshrc`, `zshenv`, `tmux.conf`, …) can take
  effect without running the full `just setup` bootstrap. Previously the only
  `rcup` invocation lived inline in `setup`, and the recipe reached for far more
  often — `just update` — does not re-link at all, so the natural "apply my
  changes" command was the wrong one. `setup` now calls `just link` instead of
  repeating the command, so the `RCRC=`-prefixed form exists in exactly one
  place. That form points rcm at the in-tree `rcrc` explicitly, which is what
  makes it work on a machine that has never been bootstrapped — `~/.rcrc` is
  itself one of the symlinks rcm creates, so a bare `rcup` finds the same config
  only after the first run. `README.md` and `CLAUDE.md` now point at `just link`
  rather than a bare `rcup`, and state that `just update` does not re-link
  ([#213](https://github.com/tgautier/dotfiles/issues/213)).
- `just lint-just`, wired into `just ci` — asserts every in-body
  `just <recipe>` call names a recipe that exists. Those calls are opaque shell
  strings to `just`, so nothing caught a typo in one: `just --summary` and
  `just --dry-run setup` both exit 0 on a misspelt call, and `just --fmt
  --check` exits 1 on this file for formatting reasons alone. A typo would have
  surfaced only mid-bootstrap on a fresh machine, after `brew bundle` had
  already run. The recipe list comes from `just --dump` rather than
  `--summary`, which omits the `_`-prefixed recipes — two of which are called
  from bodies. Two negative fixtures run on every invocation (a call to a
  non-existent recipe, and a scan that matches nothing), each asserting the
  failure came from its own guard rather than from any incidental error — the
  convention `.claude/rules/brewfile.md` sets for guard logic. `jq` is now
  installed explicitly in CI rather than assumed present in the runner image
  ([#213](https://github.com/tgautier/dotfiles/issues/213),
  partially [#219](https://github.com/tgautier/dotfiles/issues/219)).
- `!.claude/worktrees/**` to the `markdownlint-cli2` globs, completing the
  worktree hygiene begun in [#212](https://github.com/tgautier/dotfiles/pull/212).
  The path was already gitignored, but `markdownlint-cli2` globs are not
  gitignore-aware, so a nested worktree's Markdown was linted as the working
  branch's content. Measured in this repo with one worktree present: **14 files
  before the exclusion, 7 after** — the repo tracks 7 `.md` files and a nested
  worktree is a full second checkout of them. Markdown is the only exposed lint;
  `lint-shell`, `lint-brewfile` and
  `lint-mise` all use explicit paths that cannot recurse into it. `CLAUDE.md` now
  documents the `.claude/worktrees/<name>` convention, which the global
  `git-conventions.md` rule deliberately leaves to each project
  ([#211](https://github.com/tgautier/dotfiles/issues/211)).
- `libreoffice` in `Brewfile.work` — headless `soffice` is the renderer that
  converts generated `.pptx` decks to PDF for visual verification, so it belongs
  on the work laptop only. It had been installed by hand with `brew install
  --cask`, and `just update-brew` then removed it in two steps: `brew cleanup
  --prune=all` dropped the cached download, and `brew bundle cleanup --force`
  uninstalled the undeclared cask — a direct demonstration of why
  `.claude/rules/brewfile.md` says tools enter a machine through a `brew` entry,
  applied by `just`, never raw `brew install` ([#212](https://github.com/tgautier/dotfiles/pull/212)).
- `.claude/worktrees/` in `.gitignore` — `git worktree add` under `.claude/`
  otherwise leaves the checkout showing as untracked, one `git add .` away from
  committing a whole worktree. `.claude/rules/` stays tracked ([#212](https://github.com/tgautier/dotfiles/pull/212)).
- `opencode` in `Brewfile` and `Brewfile.linux` — terminal AI coding agent from
  homebrew-core. Same shape as the existing `openclaw-cli` entry (npm-tarball
  formula, `node` dependency), so it is brew-managed on both platforms rather
  than a native-installer tool: `just setup` installs it and `just update`
  upgrades it.
- `docs/homebrew.md` — Homebrew update flow plus troubleshooting for the
  recurring `just update` failure where an interrupted cask upgrade leaves
  something behind in the Caskroom staging directory ("It seems there is
  already an App at ..."). The leftover can be a truncated partial, a complete
  backup of the live app, or a wrapper directory holding a nested `.app`; the
  documented remedy is `brew reinstall --cask <cask>` followed by re-running
  `just update`, which handles all three without inspecting which one you have.
  Indexed from `README.md` and `CLAUDE.md`.
- `python@3.13` in `Brewfile` (macOS) — satisfies the `gcloud-cli` cask's
  declared dependency, clearing the `brew missing` warning. macOS-only:
  `gcloud-cli` is a cask, so `Brewfile.linux` (native gcloud installer) is
  unaffected.
- `antigravity` and `cursor` casks in `Brewfile` (macOS, all profiles).
- `antigravity-cli` and `antigravity-ide` casks in `Brewfile` (macOS, all
  profiles).
- `protonvpn` cask in the `Brewfile.personal` overlay (macOS).
- `hermes-agent` via native installer in `just setup`, with cross-references in
  both Brewfiles; document the native-installer pattern (single source of truth
  in the `setup` recipe) in `.claude/rules/brewfile.md`.
- `uv` in `Brewfile` and `Brewfile.linux`.
- `codex-app` and `lm-studio` casks in `Brewfile` (macOS).
- Per-machine macOS Brewfile profiles: `Brewfile.work` and `Brewfile.personal`
  overlays merged into `Brewfile` based on `~/.config/dotfiles/profile`. Set it
  with `just set-profile work|personal` (interactive `just setup` prompts on
  first run, default `work`; non-interactive runs fail instead of guessing);
  `brew bundle` fails loud when the marker is absent or invalid so a forced
  cleanup can never uninstall the overlay apps.

### Changed

- Elixir 1.20.2 → 1.20.3 in `config/mise/config.toml`; OTP-29 suffix unchanged.
- The stale-symlink sweep is split in two: `_scan-stale-symlinks` finds and
  prints stale links, `cleanup-symlinks` confirms and removes them. The scan
  honours a `CLEANUP_HOME` override so fixtures can drive it against a temp
  tree; `cleanup-symlinks` deliberately does **not**, so no environment setting
  can redirect its `rm` at another tree. Its match is now a union — the
  `dotfiles`/`dotfiles-private` path-segment match that catches links into a
  *former* checkout path (rcm records absolute targets, so a moved checkout
  leaves links naming the old location), plus prefixes derived from the
  configured dirs, which catch a checkout whose basename isn't `dotfiles*` at
  all. Neither subsumes the other, which is why
  [#214](https://github.com/tgautier/dotfiles/pull/214) reverted after replacing
  the first with the second. Paths are normalised with zsh's `:a` so a trailing
  slash can't silently produce a prefix that matches nothing, and a failed scan
  now aborts loudly instead of reporting a clean tree
  ([#215](https://github.com/tgautier/dotfiles/issues/215)).
- `.roborev.toml` now uses Codex at medium reasoning as the only reviewer. An empty fallback makes unavailable-reviewer failures explicit and prevents duplicate reviews. This replaces the previous Claude-only setting, which could no longer run in the Roborev worker and produced no code review.
- Bump mise Flutter (`vfox-flutter`) 3.44.7 → 3.44.8.
- Bump mise `yarn` 4.17.1 → 4.18.0.
- Tap trust is now declared in the Brewfiles: `trusted: true` on
  `kenn-io/tap/roborev` and `terror/tap/just-lsp` (formula-level trust, as
  Homebrew recommends), in both `Brewfile` and `Brewfile.linux`. This replaces
  the `_trust-taps` recipe: `brew bundle cleanup --force` (run by
  `just update-brew`) resets the trust store to exactly the Brewfile-declared
  `trusted:` entries, so trust recorded imperatively with `brew trust` was
  wiped on every update and `brew doctor` kept warning about untrusted taps.
  `brew bundle install` applies the declared trust before fetching, so fresh
  bootstraps need no separate trust step either
  ([#199](https://github.com/tgautier/dotfiles/pull/199)).
- Bump mise deno 2.9.3 → 2.9.4 and Flutter (`vfox-flutter`) 3.44.6 → 3.44.7.
- Bump mise deno 2.9.2 → 2.9.3
  ([#198](https://github.com/tgautier/dotfiles/pull/198)).
- Bump mise tool versions: deno 2.9.2, elixir 1.20.2-otp-29, Flutter
  (`vfox-flutter`) 3.44.6, go 1.26.5, helm 4.2.3, ruby 4.0.6, yarn 4.17.1.
- Rename the roborev Homebrew tap `roborev-dev/tap` → `kenn-io/tap` in
  `Brewfile` and `Brewfile.linux` (upstream GitHub org rename; the old name
  now redirects). Stops the "Redirected tap … Not trusted tap" warning on
  `brew update`. Trust for these taps' formulae is declared in the Brewfiles
  via `trusted:` options (see the entry above) — no per-machine `brew trust`
  step is needed.
- Bump mise tool versions: dart 3.12.2, deno 2.8.3, elixir 1.20.1-otp-29,
  Flutter (`vfox-flutter`) 3.44.2, helm 4.2.1, python 3.14.6, yarn 4.17.0,
  yq 4.53.3.
- Rename `linear-linear` cask to `linear` in `Brewfile.personal` (upstream
  Homebrew rename).
- `CLAUDE.md` Key Commands: package installs go through `just setup` /
  `just update-brew` — raw `brew install` / `brew bundle` is bootstrap-only,
  before `just` itself exists.
- `.claude/rules/brewfile.md`: grep all four Brewfiles before adding an entry —
  promoting an overlay package to the base must remove the overlay entry in the
  same change.
- `lint-brewfile` now detects duplicate `brew`/`cask`/`mas` names across the
  merged base + overlay set: the eval harness records entry names and fails on
  a repeat, with a negative fixture test asserting the guard fires
  ([#192](https://github.com/tgautier/dotfiles/issues/192)).
- LM Studio CLI (`lms`) PATH: reverted the installer-written `zshrc` block
  (hardcoded home path) in favor of a guarded, portable line in `zprofile`.
- Bump mise tool versions: deno 2.8.2, elixir 1.20.0-otp-29 + erlang 29.0
  (OTP 28 → 29, bumped as a pair), go 1.26.4, yarn 4.16.0.
- `just setup` is now a full idempotent bootstrap — selects the machine profile,
  then installs packages, links dotfiles, installs mise runtimes, and enables
  git hooks and tools — so a fresh machine is one command after `brew install just`.

### Removed

- The unused `git_template/hooks/gitkeep` placeholder and its rcm target. The effective `init.templateDir` is unset, no repository config include points Git at this directory, and the tracked per-repository `.githooks` mechanism does not use Git's copy-on-init template mechanism. After pulling, run `just link-inventory`; if `.git_template/hooks/gitkeep` is obsolete, use the approval-bound cleanup and restore flow in `docs/rcm-link-reconciliation.md` rather than deleting unreviewed HOME paths ([#224](https://github.com/tgautier/dotfiles/issues/224)).
- The retired private keyword-guard call from `just ci`. The public gate no
  longer depends on a recipe that the companion repository does not provide
  ([#247](https://github.com/tgautier/dotfiles/issues/247)).
- Removed the obsolete iTerm2 cask, preferences plist, rcm inventory entry,
  and documentation references now that Ghostty is the supported terminal.

- `telnet` from `Brewfile.linux`: the Homebrew formula is now source-only
  (`bottle: false`), a Tier 3 config on Linux that `brew bundle` refuses to
  build, which aborted `just setup`. On Linux, install it from the distro
  (`apt install telnet`); documented in the `Brewfile.linux` native-installers
  block.
- `gemini-cli` from `Brewfile` and `Brewfile.linux` — deprecated in
  homebrew-core (unsupported upstream; disable scheduled for 2026-12-18);
  superseded on macOS by the `antigravity-cli` cask already in `Brewfile`.
  Linux/WSL gets no brew replacement (the cask is macOS-only) — the
  `# Native installers` block in `Brewfile.linux` points at Google's own
  install channel ([#199](https://github.com/tgautier/dotfiles/pull/199)).
- `pcre` from `Brewfile` — deprecated in homebrew-core (unmaintained
  upstream); no installed formula depends on it, and `pcre2` arrives as a
  dependency where needed ([#199](https://github.com/tgautier/dotfiles/pull/199)).
- `codex-app` cask from `Brewfile` — discontinued upstream (the Codex desktop
  app merged into the ChatGPT app); the `codex` CLI cask stays
  ([#199](https://github.com/tgautier/dotfiles/pull/199)).
- `_trust-taps` recipe from the `Justfile` — superseded by the Brewfile
  `trusted:` options (see Changed)
  ([#199](https://github.com/tgautier/dotfiles/pull/199)).

### Fixed

- The Linux validation environment now installs `rcm`, whose `lsrc` command is
  the independent rcm-side oracle for the chezmoi target-map parity guard
  ([#248](https://github.com/tgautier/dotfiles/issues/248)).
- The zsh aliases and completion chezmoi source names now render to the paths consumed by `zshrc`. The former names added a second dot and the hand-maintained canary accepted the wrong targets ([#248](https://github.com/tgautier/dotfiles/issues/248)).
- `docs/homebrew.md`'s Caskroom fallback comparison is a membership test rather
  than a versioned path
  ([#227](https://github.com/tgautier/dotfiles/issues/227)). The Binary-conflict
  section is scoped to casks whose CLI ships inside the app bundle; for the other
  shape it pointed at
  `$(brew --prefix)/Caskroom/<cask>/<version>/<source>`, which reintroduced the
  version-lag trap the in-bundle rule exists to survive — the staged path carries
  a version, `brew info` describes the tap version, and the stale link was made
  by whichever version last linked it, so the reader would find no match and stop
  on their own cask's link. It never said which version to substitute either. Now
  `$(brew --caskroom)/<cask>/`, mirroring the in-bundle rule it parallels, which
  is version-agnostic for the same reason.
- `docs/homebrew.md` covers the second `just update` cask failure, "there is
  already a **Binary** at `<prefix>/bin/<name>`" — hit on obsidian 1.12.7 →
  1.13.4 ([#225](https://github.com/tgautier/dotfiles/issues/225)). A cask that
  ships a CLI beside its app carries a Binary artifact in addition to the App,
  and Homebrew replays the *installed* version's recorded artifact list to
  uninstall it; obsidian 1.12.7's held only App and Zap, so it never unlinked
  `/opt/homebrew/bin/obsidian` and the new version refused to overwrite it. The
  fix is to drop the stale symlink and install, not to reinstall. Also corrects
  the existing App-conflict section, which sold `brew reinstall --cask` as the
  near-universal remedy for a wedged cask: its uninstall replays that same
  recorded list, so against this failure it removes the app and *then* fails at
  the identical point — verified the hard way before the real fix landed. A new
  section explains why an `auto_updates` cask — an app that updates itself — is
  upgraded at all: non-greedy checks skip such casks *unless* the installed app
  bundle is behind the tap, which Homebrew upgrades by default.
  `brew outdated --cask` runs that same predicate absent the greedy env vars, so
  it previews the failure rather than disagreeing with it; where it does stay
  quiet, `brew update && brew outdated --cask` separates a self-update from a
  stale tap.
- `lint-rcrc`'s coverage comment now names every flag in the filter it describes.
  It closed the set with `-v` and `-h` but omitted `-E`, which is pinned on the
  same footing as `-v` — drop it and the pattern becomes a BRE where `(`, `)` and
  `|` are literal, so nothing is filtered. The `column-0 comment` table row also
  moved into the boundary prose, since it names a redundant ingredient rather
  than an assertion and was the only row whose `caught by` column didn't answer
  its own header. Verified by sabotage: dropping `-E` or `-v` fails the
  joined-needle assertion, dropping `-h` changes nothing — and the claim that
  *both* assertions fire was itself wrong, since the first one exits, so the
  wording now says which one
  ([#221](https://github.com/tgautier/dotfiles/pull/221) follow-up).
- **`kfw` and `kxec` were silently truncated to bare `kubectl`.** `zsh/zaliases`
  defined them unquoted (`alias kfw=kubectl port-forward`), and zsh's `alias`
  builtin treats each whitespace-separated token as its own `name[=value]`
  argument — so it defined `kfw=kubectl` and then tried to *look up* aliases
  named `port-forward`, `exec` and `-it`. `kfw` therefore ran bare `kubectl`
  (printing help) instead of forwarding a port, and `kxec` likewise. Now quoted,
  matching the already-quoted `ll` / `la` / `ls`. Found by writing the alias
  reference table for [#219](https://github.com/tgautier/dotfiles/issues/219):
  documenting the intended expansion is what exposed that zsh never produced it
  ([#219](https://github.com/tgautier/dotfiles/issues/219)).
- `docs/homebrew.md`'s cask-recovery runbook drops the bundle check instead of
  dressing it up. It asked the operator to confirm `/Applications/<App>.app` was
  "present and non-empty" while nothing branched on the answer — the prescribed
  action was `brew reinstall --cask` either way — and it sat *after* the
  reinstall was prescribed, so read literally it had you inspecting a bundle the
  forced uninstall had already replaced. What survives is the one load-bearing
  fact, stated where it matters — the interrupted upgrade may already have
  stripped the live app, so the Caskroom leftover can be the only copy, which is
  why deleting it by hand can lose the app. Separately, the branch removes two
  restatements of facts already given above: the deleted paragraph repeated the
  wedge-persistence fact from **Cause**, and the do-not-clear paragraph repeated
  the fetch-before-uninstall property from the list. Each claim now appears once
  ([#210](https://github.com/tgautier/dotfiles/issues/210)).
- The `gh` credential helper in `gitconfig` no longer hardcodes an absolute path.
  Both `[credential]` blocks read `!/usr/bin/gh auth git-credential`, which is
  where `gh` lives on Linux but **not** on macOS (Homebrew installs to
  `/opt/homebrew/bin`), so on a Mac every HTTPS git operation invoked a missing
  binary and `git clone` of a private repo failed with `could not read Username`.
  Now `!gh auth git-credential`, resolved via `PATH`, which is correct on all
  three target platforms — this file is symlinked to macOS, Linux and WSL alike
  and carries no `includeIf` guards.
- `lint-via-private` announces a skip instead of passing silently, and derives the
  private repo path from `$HOME` (overridable with `DOTFILES_PRIVATE_DIR`) rather
  than hardcoding one operator's layout. The path is anchored to `$HOME` rather
  than derived from `dotfiles_dir` deliberately: inside a nested worktree
  `dotfiles_dir` is `.claude/worktrees/<name>`, whose sibling is not the private
  repo, so a sibling-derived default would have skipped the guard precisely when
  working on a branch. On a CI runner the private repo is never present, so this
  leg of the keyword guard has never executed there — the enforcing copies are the
  two pre-commit hooks, making a skip a defence-in-depth gap rather than an
  unguarded invariant, but it now says so out loud
  ([#162](https://github.com/tgautier/dotfiles/issues/162)).
  Every interpolation of the path uses `quote()`, so a value containing `$`,
  a backtick, a quote or a backslash stays inert data rather than being expanded
  — matching `set-profile`'s existing precedent. `DOTFILES_PRIVATE_DIR` is scoped
  to this recipe only, tracked in
  [#215](https://github.com/tgautier/dotfiles/issues/215) rather than
  half-applied. `rcrc` is a one-line change left out purely to keep this PR
  scoped; `cleanup-symlinks` is the genuinely hard one, because rcm records
  absolute symlink targets, so links into a *former* checkout path must keep
  matching and a prefix built from current paths cannot see them.
- `_ensure-profile`'s non-interactive error reports the value it actually saw
  (`got '<absent>'` / `got 'Work'`) instead of always claiming no profile is set,
  which conflated a missing marker with an invalid one. Its trim comment no longer
  overstates equivalence with the Brewfile's Ruby `String#strip` — `sed` trims
  per line, so a multi-line marker re-prompts; stricter than the guard, and safe
  in that direction ([#181](https://github.com/tgautier/dotfiles/issues/181)).
- `zlogin` no longer prints `zcompile:4: can't write zwc file:
  ~/.zcompdump.zwc` when several login shells start together (tmux panes,
  session restore). Each backgrounded the same `zcompile ~/.zcompdump`, and
  `zcompile` does `unlink()` + `open(O_CREAT, 0444)` on the shared `.zwc`, so
  the loser reopened the winner's fresh read-only file and aborted. The
  precompile now takes a non-blocking `zsystem flock` before compiling, so
  exactly one shell writes the `.zwc`; the lock auto-releases on process exit.
  Where `zsh/system` isn't built, the precompile still runs unserialized rather
  than being skipped entirely. Either way `zcompile`'s stderr is dropped —
  precompilation is best-effort and the block is a disowned background job, so
  a failure would otherwise surface asynchronously in an unrelated prompt.
- `compinit` no longer prints `no such file or directory:
  /usr/share/zsh/vendor-completions/_docker` on WSL when Docker Desktop is
  stopped. Docker Desktop's integration leaves a root-owned symlink into its
  cli-tools mount, which dangles while it's off. `zprofile` now shadows the
  dangling symlink with an empty file earlier in `fpath` so `compinit` skips
  it, keyed on each completion's *first* `fpath` occurrence to match
  `compinit`'s own earliest-wins dedupe. Shadows live in a per-shell
  `~/.cache/zsh/compinit-shadows.<pid>`, pruned when the owning shell is gone
  or the directory is over a day old; a single shared directory would let one
  login wipe it while another was mid-`compinit`. The shadow stops being
  created on the next login once the real target returns, but the completion
  itself only comes back when the dump is rebuilt (`compinit -C` reuses the
  cached dump for the rest of the day) — to force it sooner, `rm ~/.zcompdump`
  and then start a new login shell; neither step alone is enough. The scan runs
  only when the dump is stale, keeping it off the common startup path, since
  `compinit -C` never walks `fpath` and so cannot hit the dangling symlink.
  The trade: on a same-day login after a target starts dangling, that
  completion is left unshadowed, so invoking it reports `function definition
  file not found` instead of doing nothing. It clears at the next dump rebuild.
  Shadow-directory pruning stays unconditional.
- `compinit -C` now actually engages on Linux/WSL. The daily-cache test
  chained the BSD and GNU `stat` spellings with `||`, but GNU `stat -f` means
  "filesystem status" — it prints fs info to *stdout* and exits 1, so the
  fallback's day-of-year was appended to that output instead of replacing it
  and the comparison never matched. Every login ran a full `compinit` rather
  than sourcing the cached dump. Freshness is now read with zsh's own `zstat`
  and `strftime` builtins (no external command, no fork), falling back to
  external `stat`/`date` where those modules aren't built — and there the two
  dialects are selected on non-empty output rather than exit status. Note the
  now-visible consequence of the daily cache actually working: a completion
  installed today no longer shows up in the next shell on Linux/WSL: it appears
  at the next day's first login, or immediately after `rm ~/.zcompdump` plus a
  new login shell.
- `just update` (and any `brew` command) no longer fails on Linux/WSL with
  `libcrypto.so.3: version OPENSSL_3.4.0 not found`. Homebrew was adopting
  mise's PATH-resident ruby, whose `openssl.so` links a newer OpenSSL than the
  system `libcrypto`, then dying during API JWS verification. `zshenv` now
  exports `HOMEBREW_FORCE_VENDOR_RUBY=1` on Linux/WSL so brew uses its own
  vendored portable ruby (the Linux default anyway); macOS is unaffected. The
  `Justfile` also exports the same variable so `just` recipes don't depend on
  the interactive shell having sourced `zshenv` — otherwise `just update` still
  hit the crash whenever the shell predated the `zshenv` change. Empty (no-op)
  on macOS.
- `just update` now trusts the Brewfile's declared taps before `brew bundle`,
  the same fix `just setup` received: Homebrew 6's trusted-taps gate aborted
  `update-brew` with "Refusing to load formula kenn-io/tap/roborev from
  untrusted tap". The trust logic moved from the `setup` recipe body into a
  shared `_trust-taps` recipe that both `setup` and `update-brew` run.
  Superseded later in this release: trust is now declared in the Brewfiles
  via `trusted:` options and the `_trust-taps` recipe is removed (see
  Changed).
- `just setup` now runs `brew bundle install --no-upgrade`, matching its
  documented "install only" contract (`just update` owns upgrades). Previously
  `brew bundle` upgraded every outdated cask/formula, so a single failing
  upgrade (e.g. `google-chrome` with a stale Caskroom app) aborted the whole
  bootstrap.
- `just setup` now trusts the Brewfile's own declared taps (`brew trust`,
  guarded on Homebrew 6+) before `brew bundle`, so the trusted-taps gate
  ($HOMEBREW_REQUIRE_TAP_TRUST) no longer aborts a fresh-machine bootstrap with
  "Refusing to load formula … from untrusted tap". A no-op on older Homebrew.
  Superseded later in this release by Brewfile-declared `trusted:` options
  (see Changed).
- `just set-default-editor` no longer hijacks the macOS web-browser role. Web
  content types (`html`/`htm`/`xhtml`/`svg`) and the root `public.data` UTI are
  now excluded — registering VS Code as their handler cascaded into the browser
  role and the `http`/`https` URL schemes, sending web links to VS Code instead
  of the browser.
- `rcup` / `just setup` no longer hang for minutes with no output. rcm was
  descending into a large non-dotfile project directory (managed only via
  `dotfiles-private`) and symlinking its tens of thousands of build
  artifacts one by one. That directory is now excluded via a new
  `dotfiles-private/rcm-excludes` list, sourced by `rcrc` at link time so its
  name stays out of this public repo (works for bare `rcup` and `just setup`).
- Exclude the repo `Justfile` and `CHANGELOG.md` from rcm symlinking — they are
  run/used in-repo, not home dotfiles. Excluding `Justfile` also fixes a
  collision with the private repo's `justfile` → `~/.justfile` on
  case-insensitive filesystems (macOS) that made every `rcup` prompt
  `overwrite ~/.Justfile?` (a silent hang when stdin is not a TTY). Brewfiles
  stay linked (`zshenv` exports `HOMEBREW_BUNDLE_FILE=~/.Brewfile[.linux]`).

## [2026-06-01]

### Changed

- Bump Flutter (`vfox-flutter`) to 3.44.1 ([#175](https://github.com/tgautier/dotfiles/pull/175)).
