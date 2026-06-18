# Changelog

All notable changes to this dotfiles repo are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This is a rolling configuration repo with no tagged releases, so entries are
grouped by **date** rather than by semantic version. Newest first.

## [Unreleased]

### Added

- `antigravity` and `cursor` casks in `Brewfile` (macOS, all profiles).
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

- Rename the roborev Homebrew tap `roborev-dev/tap` → `kenn-io/tap` in
  `Brewfile` and `Brewfile.linux` (upstream GitHub org rename; the old name
  now redirects). Stops the "Redirected tap … Not trusted tap" warning on
  `brew update`. Homebrew 6's trusted-taps gate still needs a one-time
  `brew trust kenn-io/tap` (and `brew trust terror/tap`) per machine.
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
  same change; `lint-brewfile` can't catch duplicates
  ([#192](https://github.com/tgautier/dotfiles/issues/192) tracks lint support).
- LM Studio CLI (`lms`) PATH: reverted the installer-written `zshrc` block
  (hardcoded home path) in favor of a guarded, portable line in `zprofile`.
- Bump mise tool versions: deno 2.8.2, elixir 1.20.0-otp-29 + erlang 29.0
  (OTP 28 → 29, bumped as a pair), go 1.26.4, yarn 4.16.0.
- `just setup` is now a full idempotent bootstrap — selects the machine profile,
  then installs packages, links dotfiles, installs mise runtimes, and enables
  git hooks and tools — so a fresh machine is one command after `brew install just`.

### Fixed

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
