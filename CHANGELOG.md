# Changelog

All notable changes to this dotfiles repo are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This is a rolling configuration repo with no tagged releases, so entries are
grouped by **date** rather than by semantic version. Newest first.

## [Unreleased]

### Added

- `hermes-agent` via native installer in `just setup`, with cross-references in
  both Brewfiles; document the native-installer pattern (single source of truth
  in the `setup` recipe) in `.claude/rules/brewfile.md`.
- `uv` in `Brewfile` and `Brewfile.linux`.
- `codex-app` and `lm-studio` casks in `Brewfile` (macOS).
- Per-machine macOS Brewfile profiles: `Brewfile.work` and `Brewfile.personal`
  overlays merged into `Brewfile` based on `~/.config/dotfiles/profile`. Set it
  with `just set-profile work|personal` (`just setup` writes it on first run,
  defaulting to `work`); `brew bundle` fails loud when the marker is absent or
  invalid so a forced cleanup can never uninstall the overlay apps.

### Changed

- LM Studio CLI (`lms`) PATH: reverted the installer-written `zshrc` block
  (hardcoded home path) in favor of a guarded, portable line in `zprofile`.
- Bump mise tool versions: deno 2.8.2, elixir 1.20.0-otp-29 + erlang 29.0
  (OTP 28 → 29, bumped as a pair), go 1.26.4, yarn 4.16.0.
- `just setup` is now a full idempotent bootstrap — selects the machine profile,
  then installs packages, links dotfiles, installs mise runtimes, and enables
  git hooks and tools — so a fresh machine is one command after `brew install just`.

## [2026-06-01]

### Changed

- Bump Flutter (`vfox-flutter`) to 3.44.1 ([#175](https://github.com/tgautier/dotfiles/pull/175)).
