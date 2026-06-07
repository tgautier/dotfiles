---
paths:
  - Brewfile
  - Brewfile.linux
  - Justfile
---

# Brewfile Conventions

Both Brewfiles must stay in sync and sorted. Tools enter a machine through exactly one of two channels: a `brew` entry, or the native-installer pattern below — never both.

## Rules

- When adding or removing a package, apply the change to **both** `Brewfile` and `Brewfile.linux` unless the package is platform-specific (casks, Mac App Store apps, or Linux-only tools)
- Casks (`cask`) and Mac App Store (`mas`) entries only exist in `Brewfile` — they are not available on Linux
- The macOS `Brewfile` is organized into comment-delimited blocks: `# CLI Tools & Development`, `# Applications`, `# Fonts`, `# Mac App Store Applications`
- The `Brewfile.linux` is organized into a `# CLI Tools & Development` block (casks and Mac App Store apps are not supported on Linux)
- Within each block in each Brewfile, entries are sorted alphabetically (a-z) by the package name
- Tap entries (`tap`) come before all blocks
- For tap-prefixed formulae (e.g., `brew "terror/tap/just-lsp"`), sort by the full string including the tap prefix

## Native-installer tools

Some tools are installed via their official installer script instead of brew, because the tool self-updates through its own channel (`claude update`, `hermes update`) and a brew-managed copy would fight it or lag behind. Current examples: claude-code, hermes-agent.

Adding one requires **all three** parts:

1. **Idempotent line in the `setup` recipe** of the `Justfile`: `command -v <tool> >/dev/null 2>&1 || curl -fsSL <installer-url> | bash`. The recipe is the **single source of truth** for the install command — it is the only place the installer URL appears in the repo
2. **Brewfile comment** at the tool's alphabetical slot in `Brewfile` — a `##` comment of the form `<tool>: native installer via just setup`. In `Brewfile.linux`, add an `installed by just setup` line for the tool to the `# Native installers` block at the bottom. Comments reference the recipe, **never** duplicate the install command — duplicated commands drift
3. **PATH stays dotfiles-owned** — `~/.local/bin` is already exported in `zprofile`, which is why well-behaved installers skip their "append PATH to rc file" branch. Never let an installer mutate `~/.zshrc` / `~/.zprofile` / `~/.profile`: they are rcm symlinks into this repo, so the mutation lands in the working tree. After running an installer, verify `git status` shows no rc-file changes; if it does, revert them and put the PATH line in `zprofile` deliberately

Before running an unfamiliar installer, download it and read it (PATH handling, rc-file writes, sudo use) — don't pipe straight to bash.
