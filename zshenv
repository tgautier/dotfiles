# Environment variables (loaded for all shells)
export CDPATH="${CDPATH}:${HOME}/Workspace"
export DISABLE_AUTO_TITLE="true"
export DISPLAY=:1
export EDITOR=vim
export GIT_EDITOR=vim
export GOPATH=~/Workspace/go
export HOMEBREW_BUNDLE_FILE=${HOME}/.Brewfile
export HOMEBREW_BUNDLE_NO_LOCK=true
export HOMEBREW_NO_ENV_HINTS=true
export KERL_BUILD_DOCS=yes
export KERL_CONFIGURE_OPTIONS="--disable-debug --without-javac --with-wx"
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export OP_BIOMETRIC_UNLOCK_ENABLED=true
export TERM=xterm-256color
export WORDCHARS='*?.[]~=&;!#$%^(){}<>'
export SSH_AUTH_SOCK=~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock
export HISTFILE=${HOME}/.zhistory
export HISTSIZE=50000
export SAVEHIST=50000

# Optimized PATH construction
typeset -U path  # Remove duplicates automatically
path=(
  ./bin
  ${HOME}/.bin.local
  ${HOME}/.bin
  /opt/homebrew/bin
  /opt/homebrew/opt/openjdk/bin
  /opt/homebrew/opt/sqlite/bin
  /usr/local/bin
  /usr/local/sbin
  ${HOME}/.dapr/bin
  ${HOME}/Workspace/tgautier/dotfiles
  /Users/tgautier/.antigravity/antigravity/bin
  ${GOPATH}/bin
  $path
)
export PATH
