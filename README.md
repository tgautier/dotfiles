# Dotfiles

Cross-platform dotfiles for macOS and Linux/WSL2 Ubuntu, deployed with [chezmoi](https://www.chezmoi.io/).

## Features

- Cross-platform support for macOS, Linux, and WSL2
- Platform detection (`$PLATFORM`) with automatic path configuration
- Homebrew integration with platform-specific Brewfiles
- Runtime version management via [mise](https://mise.jdx.dev/)
- Conflict-refusing public/private chezmoi deployment through `just link`
- Optimized shell startup with intelligent caching
- [tmux](docs/tmux.md) with vi-style bindings and platform-aware clipboard
- Exact-tip local shipping gate with [just](https://just.systems/), commit signature-header checks, and no hosted CI minutes
- One-command system updates via `just update`

## Quick Start

### macOS (clean machine)

1. **Install Homebrew:**

   ```sh
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Clone this repo** (HTTPS — no SSH keys yet on a clean machine):

   ```sh
   mkdir -p ~/Workspace/tgautier
   git clone https://github.com/tgautier/dotfiles.git ~/Workspace/tgautier/dotfiles
   # Optional: clone the private companion repo alongside it. If absent,
   # setup deploys the public source only.
   ```

3. **Sign in to the App Store** (the Brewfile's `mas` entries fail without
   it, which aborts the bootstrap — `just setup` is rerunnable after signing
   in).

4. **Bootstrap and run setup:**

   ```sh
   brew install just                       # the only package needed by hand
   cd ~/Workspace/tgautier/dotfiles
   just setup
   ```

   `just setup` prompts for the machine profile (work/personal) on first run,
   then installs all packages for that profile, deploys the selected sources,
   installs mise and the pinned runtimes, and enables git hooks and tools.
   It is idempotent — re-run it anytime.

5. **Set up 1Password SSH agent:**
   Open 1Password, sign in, and enable the SSH agent under
   Settings > Developer > SSH Agent.

6. **Switch git remote to SSH** (now that 1Password SSH is configured):

   ```sh
   git -C ~/Workspace/tgautier/dotfiles remote set-url origin git@github.com:tgautier/dotfiles.git
   ```

7. **Keep everything current** (later, for maintenance):

   ```sh
   just update
   ```

### Windows + WSL2 Ubuntu

#### Windows side (do this first)

1. **Install WSL2 and Ubuntu** from the Microsoft Store or via PowerShell:

   ```powershell
   wsl --install -d Ubuntu
   ```

2. **Install 1Password for Windows** and enable the SSH agent:
   Settings > Developer > SSH Agent. This provides `op-ssh-sign-wsl`
   which the dotfiles use for git commit signing inside WSL.

#### WSL side

1. **Update system packages:**

   ```sh
   sudo apt update && sudo apt upgrade -y
   ```

2. **Configure locales:**

   ```sh
   sudo apt install -y locales
   sudo locale-gen en_US.UTF-8
   sudo update-locale LANG=en_US.UTF-8
   ```

3. **Install essential tools:**

   ```sh
   sudo apt install -y coreutils zsh git curl build-essential libffi-dev libyaml-dev zlib1g-dev
   ```

4. **Install Homebrew:**

   ```sh
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

   Then add Homebrew to your PATH:

   ```sh
   echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
   eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
   ```

5. **Clone this repo** (HTTPS — no SSH keys yet on a clean machine):

   ```sh
   mkdir -p ~/Workspace/tgautier
   git clone https://github.com/tgautier/dotfiles.git ~/Workspace/tgautier/dotfiles
   # Optional: clone the private companion repo alongside it. If absent,
   # setup deploys the public source only.
   ```

6. **Bootstrap and run setup** (uses `Brewfile.linux` automatically):

   ```sh
   brew install just                       # the only package needed by hand
   cd ~/Workspace/tgautier/dotfiles
   just setup
   ```

   `just setup` installs all packages, deploys the selected sources, installs
   mise and the pinned runtimes, and enables git hooks and tools (the
   work/personal machine profile is macOS-only — Linux has no overlay).
   It is idempotent — re-run it anytime.

7. **Change shell to zsh:**

   ```sh
   chsh -s $(which zsh)
   ```

   Log out and log back in for the shell change to take effect.

8. **Switch git remote to SSH** (1Password SSH agent was set up on the Windows side):

   ```sh
   git -C ~/Workspace/tgautier/dotfiles remote set-url origin git@github.com:tgautier/dotfiles.git
   ```

9. **Keep everything current** (later, for maintenance):

   ```sh
   just update
   ```

## Day-to-Day Updates

Keep everything up to date with a single command:

```sh
just update
```

Or run individual update steps:

| Recipe             | Description                                       |
| ------------------ | ------------------------------------------------- |
| `just update`      | Run all update steps below                        |
| `just update-brew` | Update Homebrew packages and clean up             |
| `just update-mas`  | Update Mac App Store apps (skipped if no `mas`)   |
| `just update-mise` | Show outdated mise tools and upgrade them         |
| `just update-rust` | Update Rust toolchain                             |

### Applying config changes

`just update` upgrades installed software; it does not deploy local config changes. After editing managed config, refresh the running machine through the declared owners:

```sh
cd ~/Workspace/tgautier/dotfiles
just link
```

The `cd` matters: `~/.justfile` is a symlink to the private repo's justfile, so
`just link` from `$HOME` resolves there and fails with an unknown-recipe error.

`just setup` also runs the same refresh, but it is the whole bootstrap. Use `just link` for config deployment alone.

One target needs no refresh at all. `~/.config/mise/config.toml` is deployed as a symlink to the tracked `config/mise/config.toml`, because mise rewrites its own config: `just update-mise` runs `mise upgrade --bump`, and `mise use` and `mise settings set` write there too. Those edits land in the checkout, so `git status` shows them and the only step is to commit. Deploying it as a copy is what broke `just setup` in #267.

The recipe first runs the public/private ownership and source parity check in isolation, then applies the public and private chezmoi sources twice and invokes the private dedicated-owner aggregate when that checkout exists. Chezmoi enables conflict errors, so a modified or pre-existing managed file stops the refresh instead of being overwritten. Empty status, diff, and dry-run state after each pass proves idempotence.

### Custom checkout locations

Both repos default to `~/Workspace/tgautier/`. Override per machine with two
environment variables, which are a single shared contract — set one and every
consumer moves together:

| Variable               | Default                                 | Used by                                                            |
| ---------------------- | --------------------------------------- | ------------------------------------------------------------------ |
| `DOTFILES_DIR`         | `~/Workspace/tgautier/dotfiles`         | chezmoi orchestration and stale-symlink scanner                    |
| `DOTFILES_PRIVATE_DIR` | `~/Workspace/tgautier/dotfiles-private` | optional private chezmoi source and dedicated owners               |

Export them before `just link` or `just setup`. The operator passes the same paths to chezmoi and the optional private dedicated owners. A trailing slash is normalized. An absent private repository is skipped, not fatal.

## Documentation

Detailed guides live in the `docs/` folder:

- [Homebrew](docs/homebrew.md) — update flow, cask-upgrade recovery, and `just update` troubleshooting
- [Chezmoi target inventory](docs/chezmoi-inventory.md) — public target manifest, dispositions, parity guard, and private companion ownership
- [Local shipping gate](docs/local-shipping-gate.md) — per-checkout setup, exact-tip operation, recovery, upgrade, and rollback
- [tmux](docs/tmux.md) — configuration overview, cheat sheet, and troubleshooting

## Structure

```text
zshenv                  # Platform detection ($PLATFORM), environment variables, PATH
zprofile                # Homebrew init, completion cache, ~/.local/bin, Rust/cargo
zshrc                   # Prompt, keybindings, history, mise activation, sources aliases/completions
zlogin                  # Async zcompdump precompilation (see Shell load order)
zsh/
  zaliases              # Shell aliases
  zcompletion           # Completion paths, autoloads functions
  functions/            # Autoloaded zsh functions
bin/                    # Scripts added to PATH
config/
  mise/config.toml      # Pinned tool versions (node, python, ruby, go, etc.)
  ghostty/config        # Ghostty terminal config
tmux.conf               # tmux config (C-a prefix, vi mode, platform clipboard)
chezmoi.toml            # chezmoi umask configuration
gitconfig               # SSH signing via 1Password, rebase-based pulls
gitignore               # Global gitignore (OS, editor, build noise)
agignore                # ack/ag ignore patterns
editorconfig            # Cross-editor whitespace defaults
psqlrc                  # psql prompt and output defaults
Brewfile                # macOS shared base + profile-overlay tail
Brewfile.work           # macOS work-only casks/apps
Brewfile.personal       # macOS personal-only casks/apps
Brewfile.linux          # Linux Homebrew packages
.chezmoiroot            # Selects home/ as the chezmoi source state
home/                   # Active public chezmoi source state
tests/                  # Isolated parity checker and sabotage fixtures
Justfile                # Bootstrap, CI and update recipes
.githooks/              # Local identity, complete-CI, signature, and exact-tip push gate
CLAUDE.md               # Repo guidance for Claude Code (see Project-Local Rules)
.claude/                # Repo-local Claude Code rules
.roborev.toml           # Review-tool scope context
.markdownlint.yml       # markdownlint rules (used by just lint-markdown)
.markdownlint-cli2.yaml # markdownlint file globs
docs/                   # Detailed guides, migration inventory, and target manifest
CHANGELOG.md            # Date-based rolling changelog
```

Every tracked top-level entry appears above except `README.md` and `.gitignore`,
which are self-describing.

## Scripts (`bin/`)

Chezmoi installs each managed script into `~/.bin`, which `zshenv` adds to `PATH` alongside `~/.bin.local` for machine-local scripts that stay out of this repository.

| Script             | Description                                                                |
| ------------------ | -------------------------------------------------------------------------- |
| `chezmoi-cutover`  | Inspect and deploy the public and optional private dotfile sources         |
| `op-ssh-sign`      | Cross-platform 1Password SSH signing (WSL delegates to `op-ssh-sign-wsl`)  |

Additional scripts (`kseal`, `kshow`, `obsidian`) live in the private companion repository.

## Shell functions (`zsh/functions/`)

`zsh/zcompletion` prepends `~/.zsh/functions` to `fpath` and autoloads each
file, so every one is available as a command.

| Function            | Description                                                          |
| ------------------- | -------------------------------------------------------------------- |
| `api_key`           | Random hex key via `openssl rand`, default 16 bytes                  |
| `b64_decode`        | Base64-decode arguments (GNU and BSD compatible)                     |
| `b64_encode`        | Base64-encode arguments                                              |
| `cdroot`            | `cd` to the repository root (`git root`)                             |
| `current_tt`        | Set the terminal title to the current directory's name               |
| `tt`                | Set the terminal title to an arbitrary string                        |
| `uuid`              | Lowercase UUID via `uuidgen`, with a fallback                        |

## Aliases (`zsh/zaliases`)

| Alias  | Expands to                | Notes                            |
| ------ | ------------------------- | -------------------------------- |
| `k`    | `kubectl`                 |                                  |
| `kctx` | `kubectx`                 |                                  |
| `kns`  | `kubens`                  |                                  |
| `kxec` | `kubectl exec -it`        |                                  |
| `kfw`  | `kubectl port-forward`    |                                  |
| `ll`   | `ls -lh`                  |                                  |
| `la`   | `ls -lah`                 |                                  |
| `ls`   | `ls -G` / `ls --color`    | BSD flag on macOS, GNU elsewhere |
| `ts`   | Tailscale.app CLI binary  | macOS only                       |

## Local shipping gate (`.githooks/`)

Run `just git-hooks` once in each checkout or worktree. The full machine bootstrap also wires these tracked hooks.

| Entry | Runs |
| --- | --- |
| `pre-commit` | Checks the effective Git identity and runs the complete `mise x -- just ci` gate |
| `pre-push` | Rejects direct protected-branch pushes, ancestry without signature headers, dirty or wrong checkout state, and missing or stale exact-tip evidence |
| `ci-attest` | Runs the complete gate and atomically records the unchanged clean `HEAD` under the checkout's Git directory |
| `ci-publish` | Verifies the exact pushed SSH branch tip and current `main` ancestry, then publishes and reads back the required GitHub commit status |
| `post-commit` | Triggers roborev per-commit review on feature branches |
| `post-rewrite` | Triggers roborev review after rebase or amend on feature branches |
| `lib/git-integrity.sh` | Shares identity, signature, mise, and attestation validation across the executables |

## Fresh-machine acceptance

The acceptance harness proves `just setup` works from a fresh checkout into an empty HOME, then proves a second run is a no-op.

### macOS

```sh
just test-setup-acceptance                  # public-only
just test-setup-acceptance-private          # with private companion
```

The harness clones the committed public tree (and optionally the private companion) into a temporary directory, sets `HOME` to a fresh temporary location, stubs external provisioning commands (`brew`, `mas`, `mise`), and runs `just setup` twice. It verifies target bytes, modes, symlink destinations, Git hooks, companion ownership, and second-run idempotence. Which profile runs (work or personal) depends on the active Homebrew Brewfile overlay on the host.

### Linux container

```sh
just test-setup-acceptance-linux            # public-only
just test-setup-acceptance-linux-private    # with private companion
```

Builds a digest-pinned Ubuntu image with just 1.58.0, chezmoi 2.72.0, Python 3, and zsh. Source trees enter the container as `git archive` tarballs mounted at runtime; nothing private is baked into an image layer. The container runs on a tmpfs HOME. Docker is the only host dependency.

### Evidence boundaries

- macOS acceptance runs on the host kernel and filesystem. HFS+ is case-insensitive; Linux is not. Both platforms must pass.
- The Linux container is not WSL2. WSL2 acceptance requires a real Windows host and is deferred until one is available. The container proves the full `just setup` chain on a case-sensitive ext4 filesystem under a real Linux kernel.
- External provisioning commands are stubbed. The harness does not install real Homebrew packages, mise runtimes, or Mac App Store apps. It proves the setup orchestration, chezmoi rendering, Git hooks, and companion ownership paths.

## Configuration files

| File                      | Configures | Highlights                                                        |
| ------------------------- | ---------- | ----------------------------------------------------------------- |
| `gitconfig`               | Git        | SSH signing via 1Password, `pull.ff=only`, `gh` credential helper |
| `gitignore`               | Git        | Global ignores — OS, editor and build noise                       |
| `tmux.conf`               | tmux       | `C-a` prefix, vi copy mode, platform-aware clipboard              |
| `editorconfig`            | Editors    | UTF-8, LF, 2-space indent; tabs for `Makefile`                    |
| `psqlrc`                  | psql       | Unicode borders, timing, `¤` for null, coloured prompt            |
| `agignore`                | ack/ag     | Skip `.git`, `node_modules`, build output                         |
| `config/mise/config.toml` | mise       | Pinned runtimes — node, python, ruby, go, erlang, elixir, …       |
| `config/ghostty/config`   | Ghostty    | Font, auto light/dark theme, window size                          |

## Shell load order

```text
zshenv          # always — $PLATFORM, env vars, PATH, SSH agent
zprofile        # login — Homebrew init, completion cache, ~/.local/bin, cargo
zshrc           # interactive — prompt, keybindings, history, mise; sources
                #   zsh/zaliases and zsh/zcompletion
~/.zshrc.local  # sourced near the end of zshrc, if present — machine-local
                #   overrides, kept in dotfiles-private rather than here
                #   NB: zsh-syntax-highlighting and `mise activate` run AFTER
                #   it — mise wins for what it manages, other PATH entries stay
zlogin          # login, after zshrc — precompiles ~/.zcompdump in the background
```

`~/.zshrc.local` is the hook for anything machine-specific or private: `zshrc`
sources it when readable, and this repo never tracks it. It is *not* the last
thing to run — zsh-syntax-highlighting and `mise activate zsh` follow it. `mise
activate` prepends the bin directories of every runtime it manages, so mise's
version wins over a `PATH` entry added there for those tools; entries for
anything mise doesn't manage survive and still take effect. Which runtimes those
are is mise's business, not this repo's: `config/mise/config.toml` plus whatever
project-level config is in scope.

`zlogin` runs last and is a pure optimisation: it compiles the completion dump
so the *next* login sources the compiled form. Guard platform-specific code with
`$PLATFORM` in any of these files.

## Platform Detection

The dotfiles automatically detect your platform and configure accordingly:

- **macOS**: `$PLATFORM = "macos"`
- **WSL**: `$PLATFORM = "wsl"`
- **Linux**: `$PLATFORM = "linux"`

Platform-specific configurations are handled automatically in:

- `zshenv` - Environment variables and PATH
- `zprofile` - Homebrew initialization
- `zsh/zcompletion` - Completion paths
- `zshrc` - WSL-specific optimizations

## CI / Linting

Run all checks locally with [just](https://just.systems/):

```sh
just ci
```

Individual targets:

| Target | Description |
| --- | --- |
| `just lint-shell` | ShellCheck on scripts, tests, and zsh |
| `just lint-python` | Compile Python helpers with warnings as errors |
| `just lint-markdown` | markdownlint-cli2 |
| `just lint-changelog` | Reject duplicate subheadings within any CHANGELOG date section |
| `just lint-brewfile` | Ruby syntax check on Brewfiles |
| `just lint-mise` | Validate mise config |
| `just lint-just` | Check in-body `just <recipe>` calls resolve |
| `just lint-cleanup-symlinks` | Fixture-test the stale-symlink scanner |
| `just test-private-chezmoi-bridge` | Fixture-test bounded companion checks and output withholding |
| `just test-chezmoi-operator` | Fixture-test guarded public/private operation, approval, idempotence, and recovery |
| `just test-chezmoi-canary` | Run public parity plus optional private ownership and source canaries in isolation |
| `just test-local-gate` | Fixture-test identity, signature-header ancestry, and exact-tip evidence |
| `just test-setup-acceptance` | Run `just setup` twice from a fresh public checkout into an isolated HOME |
| `just test-setup-acceptance-private` | Fresh setup acceptance with and without the private companion |
| `just test-setup-acceptance-linux` | Run the same harness inside a pinned Linux container (public-only) |
| `just test-setup-acceptance-linux-private` | Linux container acceptance with the private companion |
| `just ci-publish` | Publish the pushed exact-tip attestation for strict GitHub branch protection |
| `just link` | Refresh public/private chezmoi sources and private dedicated targets |
| `just chezmoi-status` | Inspect public/private chezmoi status without changing managed targets |
| `just chezmoi-diff` | Print the local public/private target-state diff |
| `just chezmoi-apply-dry-run` | Preview both applies without changing managed targets |

Wire the hooks after cloning, adding a worktree, or pulling hook changes:

```sh
just git-hooks
```

Before each push, attest the final clean commit:

```sh
just ci-attest
git push
just ci-publish
```

GitHub Actions remains disabled. The required external status and strict up-to-date rule block squash merge when the exact branch tip has not completed this flow. See [Local shipping gate](docs/local-shipping-gate.md) for normal operation, recovery, upgrade, rollback, and evidence limits.

## Troubleshooting

### Linux/WSL: Locale errors

If you see `setlocale: LC_ALL: cannot change locale` errors:

```sh
sudo apt install -y locales
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8
# Then log out and log back in
```

### Linux/WSL: Command not found (readlink, dirname, tty, date)

Install coreutils package:

```sh
sudo apt install -y coreutils
```

### Linux/WSL: Homebrew not found after installation

Add Homebrew to your current shell session:

```sh
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
```

### Completion warnings

If you run into warnings with `compaudit`, fix permissions:

```sh
compaudit | xargs chown -R "$(whoami)"
compaudit | xargs chmod go-w
```

### WSL: Slow shell startup

Uncomment the Windows PATH filter in `zshrc` to speed up startup:

```sh
export PATH=$(echo $PATH | tr ':' '\n' | grep -v "/mnt/" | tr '\n' ':' | sed 's/:$//')
```

### Missing tools

Check if required tools are installed:

```sh
which brew mise git zsh
```
