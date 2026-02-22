# Dotfiles

Cross-platform dotfiles for macOS and Linux/WSL2 Ubuntu, managed with
[rcm](https://github.com/thoughtbot/rcm).

## Features

- Cross-platform support for macOS, Linux, and WSL2
- Platform detection (`$PLATFORM`) with automatic path configuration
- Homebrew integration with platform-specific Brewfiles
- Runtime version management via [mise](https://mise.jdx.dev/)
- Optimized shell startup with intelligent caching
- CI with [just](https://just.systems/) + GitHub Actions
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
   ```

3. **Install packages from Brewfile** (includes rcm, just, rustup, 1Password, and everything else):

   ```sh
   brew bundle --file=~/Workspace/tgautier/dotfiles/Brewfile
   ```

4. **Link dotfiles** (rcm was installed in step 3):

   ```sh
   rcup -d ~/Workspace/tgautier/dotfiles
   ```

5. **Set up 1Password SSH agent:**
   Open 1Password, sign in, and enable the SSH agent under
   Settings > Developer > SSH Agent.

6. **Switch git remote to SSH** (now that 1Password SSH is configured):

   ```sh
   git -C ~/Workspace/tgautier/dotfiles remote set-url origin git@github.com:tgautier/dotfiles.git
   ```

7. **Install mise:**

   ```sh
   curl https://mise.run | sh
   mise install
   ```

8. **Update everything:**

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
   ```

6. **Install packages from Brewfile** (includes rcm, just, rustup, and other tools):

   ```sh
   brew bundle --file=~/Workspace/tgautier/dotfiles/Brewfile.linux
   ```

7. **Link dotfiles** (rcm was installed in step 6):

   ```sh
   rcup -d ~/Workspace/tgautier/dotfiles
   ```

8. **Change shell to zsh:**

   ```sh
   chsh -s $(which zsh)
   ```

   Log out and log back in for the shell change to take effect.

9. **Switch git remote to SSH** (1Password SSH agent was set up on the Windows side):

   ```sh
   git -C ~/Workspace/tgautier/dotfiles remote set-url origin git@github.com:tgautier/dotfiles.git
   ```

10. **Install mise:**

    ```sh
    curl https://mise.run | sh
    mise install
    ```

11. **Update everything:**

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

## Structure

```text
zshenv                  # Platform detection, environment variables, PATH
zprofile                # Homebrew init, compinit
zshrc                   # Prompt, keybindings, mise activation, sources aliases/completions
zsh/
  zaliases              # Shell aliases
  zcompletion           # Completion paths, autoloads functions
  functions/            # Autoloaded zsh functions
bin/                    # Scripts added to PATH
config/
  mise/config.toml      # Pinned tool versions (node, python, ruby, go, etc.)
  alacritty/alacritty.yml
gitconfig               # SSH signing via 1Password, rebase-based pulls
rcrc                    # rcm config (DOTFILES_DIRS, EXCLUDES)
Brewfile                # macOS Homebrew packages
Brewfile.linux          # Linux Homebrew packages
justfile                # CI and update recipes
.github/workflows/ci.yml
```

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

| Target                 | Description                                          |
| ---------------------- | ---------------------------------------------------- |
| `just lint-shell`      | ShellCheck on `bin/*` and zsh files                  |
| `just lint-json-yaml`  | Validate `claude/settings.json` and `alacritty.yml`  |
| `just lint-markdown`   | markdownlint-cli2                                    |
| `just lint-brewfile`   | Ruby syntax check on Brewfiles                       |
| `just lint-mise`       | Validate mise config                                 |

Enable the pre-commit hook:

```sh
just setup
```

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
