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

### Changed

- LM Studio CLI (`lms`) PATH: reverted the installer-written `zshrc` block
  (hardcoded home path) in favor of a guarded, portable line in `zprofile`.

## [2026-06-01]

### Changed

- Bump Flutter (`vfox-flutter`) to 3.44.1 ([#175](https://github.com/tgautier/dotfiles/pull/175)).
