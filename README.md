# Dotfiles

Cross-platform dotfiles for macOS and Linux/WSL2 Ubuntu.

## Features

- 🚀 **Optimized shell startup** with intelligent caching
- 🔄 **Cross-platform support** for macOS and Linux/WSL
- 🎯 **Platform detection** with automatic path configuration
- 📦 **Homebrew integration** with platform-specific Brewfiles
- ⚡ **Performance optimizations** for faster shell experience

## Quick Start

### macOS

1. **Install Homebrew:**
   ```sh
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install packages from Brewfile:**
   ```sh
   brew bundle --file=~/Workspace/tgautier/dotfiles/Brewfile
   ```

3. **Link dotfiles:**
   ```sh
   rcup -d ~/Workspace/tgautier/dotfiles
   ```

4. **Install mise:**
   ```sh
   curl https://mise.run | sh
   mise install
   ```

### Linux / WSL2 Ubuntu

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
   sudo apt install -y coreutils zsh git curl build-essential
   ```

4. **Install Homebrew (optional but recommended):**
   ```sh
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

   Then add Homebrew to your PATH:
   ```sh
   echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
   eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
   ```

5. **Install packages:**
   ```sh
   # If using Homebrew:
   brew bundle --file=~/Workspace/tgautier/dotfiles/Brewfile.linux

   # Or install tools via apt:
   sudo apt install -y gh jq htop httpie docker.io
   ```

6. **Link dotfiles:**
   ```sh
   # Install rcm if using Homebrew:
   brew install rcm

   # Or via apt:
   sudo add-apt-repository ppa:martin-frost/thoughtbot-rcm
   sudo apt install rcm

   rcup -d ~/Workspace/tgautier/dotfiles
   ```

7. **Change shell to zsh:**
   ```sh
   chsh -s $(which zsh)
   ```

   Log out and log back in for the shell change to take effect.

8. **Install mise:**
   ```sh
   curl https://mise.run | sh
   mise install
   ```

9. **(WSL only) Install 1Password for SSH:**
   Follow: https://developer.1password.com/docs/ssh/get-started#step-3-turn-on-the-1password-ssh-agent

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

You are now good to go 🚀
