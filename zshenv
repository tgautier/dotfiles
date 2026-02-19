# Environment variables (loaded for all shells)

# Platform detection
if [[ "$OSTYPE" == "darwin"* ]]; then
  export PLATFORM="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]] && grep -qi microsoft /proc/version 2>/dev/null; then
  export PLATFORM="wsl"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  export PLATFORM="linux"
else
  export PLATFORM="unknown"
fi

# Common environment variables
export CDPATH="${CDPATH}:${HOME}/Workspace"
export DISABLE_AUTO_TITLE="true"
export EDITOR=vim
export GIT_EDITOR=vim
export GOPATH=~/Workspace/go
export HOMEBREW_BUNDLE_NO_LOCK=true
export HOMEBREW_NO_ENV_HINTS=true
export KERL_BUILD_DOCS=yes
export KERL_CONFIGURE_OPTIONS="--disable-debug --without-javac --with-wx"
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export OP_BIOMETRIC_UNLOCK_ENABLED=true
export TERM=xterm-256color
export WORDCHARS='*?.[]~=&;!#$%^(){}<>'
export HISTFILE=${HOME}/.zhistory
export HISTSIZE=50000
export SAVEHIST=50000

# Platform-specific environment variables
case $PLATFORM in
  macos)
    export DISPLAY=:1
    export SSH_AUTH_SOCK=~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock
    export HOMEBREW_BUNDLE_FILE=${HOME}/.Brewfile
    ;;
  wsl)
    # WSL-specific: Use Windows host for X11
    export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
    export SSH_AUTH_SOCK=~/.1password/agent.sock
    export HOMEBREW_BUNDLE_FILE=${HOME}/.Brewfile.linux
    ;;
  linux)
    export DISPLAY=:0
    export SSH_AUTH_SOCK=~/.1password/agent.sock
    export HOMEBREW_BUNDLE_FILE=${HOME}/.Brewfile.linux
    ;;
esac

# Optimized PATH construction
typeset -U path  # Remove duplicates automatically

# Build path array based on platform
path=(./bin)

# User-specific paths (common)
[[ -d "${HOME}/.bin.local" ]] && path+="${HOME}/.bin.local"
[[ -d "${HOME}/.bin" ]] && path+="${HOME}/.bin"

# Platform-specific package manager paths
if [[ $PLATFORM == "macos" ]]; then
  [[ -d "/opt/homebrew/bin" ]] && path+="/opt/homebrew/bin"
  [[ -d "/opt/homebrew/opt/openjdk/bin" ]] && path+="/opt/homebrew/opt/openjdk/bin"
  [[ -d "/opt/homebrew/opt/sqlite/bin" ]] && path+="/opt/homebrew/opt/sqlite/bin"
elif [[ $PLATFORM == "linux" ]] || [[ $PLATFORM == "wsl" ]]; then
  # Homebrew on Linux (optional)
  [[ -d "/home/linuxbrew/.linuxbrew/bin" ]] && path+="/home/linuxbrew/.linuxbrew/bin"
fi

# WSL: Add Windows interop paths
if [[ $PLATFORM == "wsl" ]]; then
  # VS Code (detect Windows user dynamically)
  _vscode=(/mnt/c/Users/*/AppData/Local/Programs/Microsoft\ VS\ Code/bin(NY1))
  (( ${#_vscode} )) && path+="$_vscode[1]"
  # Windows system utilities (clip.exe, explorer.exe, cmd.exe, pwsh.exe)
  [[ -d "/mnt/c/Windows/System32" ]] && path+="/mnt/c/Windows/System32"
  [[ -d "/mnt/c/Windows" ]] && path+="/mnt/c/Windows"
  [[ -d "/mnt/c/Program Files/PowerShell/7" ]] && path+="/mnt/c/Program Files/PowerShell/7"
  unset _vscode
fi

# Common paths (including standard system paths)
path+=(
  /usr/local/bin
  /usr/local/sbin
  /usr/bin
  /usr/sbin
  /bin
  /sbin
)

# Tool-specific paths (check if they exist)
[[ -d "${HOME}/.dapr/bin" ]] && path+="${HOME}/.dapr/bin"
[[ -d "${HOME}/Workspace/tgautier/dotfiles" ]] && path+="${HOME}/Workspace/tgautier/dotfiles"
[[ -d "${HOME}/.antigravity/antigravity/bin" ]] && path+="${HOME}/.antigravity/antigravity/bin"
[[ -d "${GOPATH}/bin" ]] && path+="${GOPATH}/bin"

export PATH
