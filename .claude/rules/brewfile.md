---
paths:
  - Brewfile
  - Brewfile.linux
---

# Brewfile Conventions

Both Brewfiles must stay in sync and sorted.

## Rules

- When adding or removing a package, apply the change to **both** `Brewfile` and `Brewfile.linux` unless the package is platform-specific (casks, Mac App Store apps, or Linux-only tools)
- Casks (`cask`) and Mac App Store (`mas`) entries only exist in `Brewfile` — they are not available on Linux
- Each Brewfile is organized into comment-delimited blocks: `# CLI Tools & Development`, `# Applications`, `# Fonts`, `# Mac App Store Applications`
- Within each block, entries are sorted alphabetically (a-z) by the package name
- Tap entries (`tap`) come before all blocks
- For tap-prefixed formulae (e.g., `brew "terror/tap/just-lsp"`), sort by the full string including the tap prefix
