# Changelog

All notable changes to this dotfiles repo are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This is a rolling configuration repo with no tagged releases, so entries are
grouped by **date** rather than by semantic version. Newest first.

## [Unreleased]

### Added

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

- `.roborev.toml` now names `claude-code` directly instead of `copilot`. roborev
  could not invoke `copilot`, so every review silently fell through to
  `backup_agent` — 112 of 112 jobs on record ran `claude-code`. claude-code is the
  only agent with a paid subscription behind it: copilot, codex and
  gemini/antigravity are all installed but have no API credit (codex returns
  `401 Unauthorized`), so a second reviewer is not one install away. The `codex`
  and `copilot-cli` casks stay in the Brewfile for interactive use and are
  deliberately not review agents.
- Bump mise Flutter (`vfox-flutter`) 3.44.7 → 3.44.8.
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

- `docs/homebrew.md`'s cask-recovery runbook drops the bundle check instead of
  dressing it up. It asked the operator to confirm `/Applications/<App>.app` was
  "present and non-empty" while nothing branched on the answer — the prescribed
  action was `brew reinstall --cask` either way — and it sat *after* the
  reinstall was prescribed, so read literally it had you inspecting a bundle the
  forced uninstall had already replaced. Adding a command and an outcome table
  was tried first and rejected on review: every outcome still led to the same
  step, so the check remained decorative. What survives is the one load-bearing
  fact, stated where it matters — the interrupted upgrade may already have
  stripped the live app, so the Caskroom leftover can be the only copy, which is
  why deleting it by hand can lose the app. Separately, the same paragraph
  restated the wedge-persistence fact already given six paragraphs earlier under
  **Cause**; that duplicate is removed and the claim now appears once
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
