PATH="./bin:${PATH}"
PATH="${HOME}/.asdf/shims:${PATH}"
PATH="/opt/homebrew/bin:${PATH}"
PATH="/usr/local/bin:${PATH}"
PATH="/usr/local/sbin:${PATH}"
PATH="${HOME}/.bin.local:${PATH}"
PATH="${HOME}/.bin:${PATH}"
PATH="${HOME}/Developer/tgautier/dotfiles:${PATH}"

export CDPATH="${CDPATH}:${HOME}/Developer"
export DISABLE_AUTO_TITLE="true"
export DISPLAY=:1
export EDITOR=vim
export FPATH
export GIT_EDITOR=vim
export GOPATH=~/Developer/go
PATH="${PATH}:${GOPATH}/bin"
export HOMEBREW_BUNDLE_FILE=${HOME}/.Brewfile
export HOMEBREW_BUNDLE_NO_LOCK
export KERL_CONFIGURE_OPTIONS="--disable-debug --without-javac --with-wx" # In order to not install Erlang with Java
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PATH
export TERM=xterm-256color
export WORDCHARS='*?.[]~=&;!#$%^(){}<>'
export TILLER_NAMESPACE=tiller
export HELM_TLS_ENABLE=true

export HISTFILE=${HOME}/.zhistory
export HISTSIZE=5000
export SAVEHIST=5000

eval "$(/opt/homebrew/bin/brew shellenv)"
