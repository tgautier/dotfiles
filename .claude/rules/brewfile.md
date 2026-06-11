---
paths:
  - Brewfile
  - Brewfile.work
  - Brewfile.personal
  - Brewfile.linux
  - Justfile
---

# Brewfile Conventions

The Brewfiles must stay in sync and sorted. Tools enter a machine through exactly one of two channels: a `brew` entry, or the native-installer pattern below — never both.

## Files

- `Brewfile` — macOS **shared base**: every package common to all Macs, plus a profile-overlay tail that merges the machine-specific overlay via `instance_eval`
- `Brewfile.work` / `Brewfile.personal` — macOS **per-machine overlays**: casks/mas/brew that belong on only that profile. Each Mac picks one via the marker at `~/.config/dotfiles/profile` (set with `just set-profile work|personal`; `just setup` writes it on first run, defaulting to `work`). An absent/empty/unknown marker makes `brew bundle` fail loud — never silently merge the wrong overlay, since `brew bundle cleanup --force` would then uninstall every overlay app
- `Brewfile.linux` — Linux base (no casks/mas)

Because the overlay is merged into the same `brew bundle` evaluation, both `brew bundle install` and `brew bundle cleanup` operate on the full per-machine set — cleanup never uninstalls a sibling profile's apps on that machine.

## Rules

- A package shared by **all** machines goes in the base (`Brewfile` for macOS, and also `Brewfile.linux` unless it's a cask/mas or platform-specific tool)
- A package for **one Mac profile only** goes in `Brewfile.work` or `Brewfile.personal` — never in the shared `Brewfile` base
- Casks (`cask`) and Mac App Store (`mas`) entries never appear in `Brewfile.linux` — they are not available on Linux
- The macOS `Brewfile` base is organized into comment-delimited blocks: `# CLI Tools & Development`, `# Applications`, `# Fonts`, `# Mac App Store Applications`. The overlays use `# Applications` and `# Mac App Store Applications` blocks
- `Brewfile.linux` is organized into a `# CLI Tools & Development` block
- Within each block in each file, entries are sorted alphabetically (a-z) by package name
- Tap entries (`tap`) come before all blocks
- For tap-prefixed formulae (e.g., `brew "terror/tap/just-lsp"`), sort by the full string including the tap prefix
- Keep `lint-brewfile` in the `Justfile` in sync with this file set — every Brewfile gets a `ruby -c` check, and the overlay-merge harness must keep evaluating every profile plus the absent-marker failure

## Native-installer tools

Some tools are installed via their official installer script instead of brew, because the tool self-updates through its own channel (`claude update`, `hermes update`) and a brew-managed copy would fight it or lag behind. Current examples: claude-code, hermes-agent.

Adding one requires **all three** parts:

1. **Idempotent line in the `setup` recipe** of the `Justfile`: `command -v <tool> >/dev/null 2>&1 || curl -fsSL <installer-url> | bash`. The recipe is the **single source of truth** for the install command — it is the only place the installer URL appears in the repo
2. **Brewfile comment** at the tool's alphabetical slot in `Brewfile` — a `##` comment of the form `<tool>: native installer via just setup`. In `Brewfile.linux`, add an `installed by just setup` line for the tool to the `# Native installers` block at the bottom. Comments reference the recipe, **never** duplicate the install command — duplicated commands drift
3. **PATH stays dotfiles-owned** — `~/.local/bin` is already exported in `zprofile`, which is why well-behaved installers skip their "append PATH to rc file" branch. Never let an installer mutate `~/.zshrc` / `~/.zprofile` / `~/.profile`: they are rcm symlinks into this repo, so the mutation lands in the working tree. After running an installer, verify `git status` shows no rc-file changes; if it does, revert them and put the PATH line in `zprofile` deliberately

Before running an unfamiliar installer, download it and read it (PATH handling, rc-file writes, sudo use) — don't pipe straight to bash.
