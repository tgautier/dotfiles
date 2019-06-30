PATH="./bin:${PATH}"
PATH="${HOME}/.asdf/shims:${PATH}"
PATH="/usr/local/bin:${PATH}"
PATH="/usr/local/sbin:${PATH}"
PATH="${HOME}/.bin.local:${PATH}"
PATH="${HOME}/.bin:${PATH}"

export CDPATH="${CDPATH}:${HOME}/Workspace"
export DISABLE_AUTO_TITLE="true"
export DISPLAY=:1
export EDITOR="code -w"
export GIT_EDITOR="code -w"
export GOPATH=~/Workspace/go
PATH="${PATH}:${GOPATH}/bin"
export GPG_TTY=$(tty)
export HOMEBREW_BREWFILE=${HOME}/.brewfile
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
setopt EXTENDED_HISTORY
setopt INC_APPEND_HISTORY
setopt SHARE_HISTORY

bindkey -e
bindkey '^[[1;9D' backward-word # Alt-Left
bindkey '^[[1;9C' forward-word # Alt-Right
bindkey '^[[3~' delete-char # Delete
bindkey '^[[Z' reverse-menu-complete # Ctrl-r
bindkey '^[[A' up-line-or-search # Arrow up
bindkey '^[[B' down-line-or-search # Arrow down

_currentKubernetesContextName() {
  local context=$(kubectl config current-context 2> /dev/null);

  if [ -z "${context}" -o "${context}" = "docker-desktop" ]; then
    echo ""
  else
    echo "%{%F{198}%} ${context}%{%f%} "
  fi
}

_currentEnvironmentName() {
  if [ -z "${CURRENT_ENVIRONMENT_NAME}" ]; then
    echo ""
  else
    echo "%{\e[38;5;250m%}[${CURRENT_ENVIRONMENT_NAME}]%{\e[39m%} "
  fi
}
setopt PROMPT_SUBST
export PROMPT='%F{235}%B%c%b%f$(_currentKubernetesContextName)$(_currentEnvironmentName)%(?.(%F{198}♥%f‿%F{198}♥%f.(%F{75}ಥ%f_%F{75}ಥ%f)) '

[[ -r ${HOME}/.zshrc.local ]] && source ${HOME}/.zshrc.local
[[ -r ${HOME}/.asdf/asdf.sh ]] && source ${HOME}/.asdf/asdf.sh
[[ -r ${HOME}/.zcompletion ]] && source ${HOME}/.zcompletion
[[ -r ${HOME}/.config/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && source ${HOME}/.config/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

alias kxec=kubectl exec -it
alias kforward=kubectl port-forward
alias kns=kubens
alias kctx=kubectx
alias la='ls -lah'
alias ll='ls -lh'
alias ls='ls -G'
alias serve="ruby -run -e httpd . -p 8000"

cdroot() {
  cd $(git root)
}

color_preferences() {
cat <<EOF | column -t -s';'
color;normal;bright
black;1a1a1a;616161
red;c91b00;ff6d67
green;03aa03;00bf0a
yellow;b0ae01;dbd800
blue;011ea6;0062d9
magenta;c930c7;ff76ff
cyan;029899;00c6c9
white;ffffff;ffffff
EOF
}

current_tt() {
  tt $(basename $(pwd))
}

helm_autocomplete() {
  source <($commands[helm] completion zsh);
}

kubectl_autocomplete() {
  source <($commands[kubectl] completion zsh);
}

load_kubectl_env() {
  export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
  export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
  export KOPS_STATE_STORE=s3://fewlines-co-state-store
}

hexopen() {
  open https://hex.pm/packages/${1}
}

port_in_use() {
  lsof -n -i:${1} | grep LISTEN
}

tt() {
  echo -ne "\033];$@\007"
}

api_key() {
  size=${1:-16}
  # remove characters looking similar and same character following each other
  base64 /dev/urandom  | tr -d '/+oO0iIl' | tr -s '[:alnum:]' | head -c ${size}
}

uuid() {
  uuidgen | tr '[:upper:]' '[:lower:]' | tr -d '\n'
}

kload() {
  export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
  export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
  export KOPS_STATE_STORE=s3://fewlines-co-state-store
}

current_tt
