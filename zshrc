export GPG_TTY=$(tty)

setopt EXTENDED_HISTORY
setopt INC_APPEND_HISTORY
setopt SHARE_HISTORY

bindkey -e
autoload -U edit-command-line;
zle -N edit-command-line;
bindkey '^F' edit-command-line # Edit current line with C-f
bindkey '^[[1;9D' backward-word # Alt-Left
bindkey '^[[1;9C' forward-word # Alt-Right
bindkey '^[[3~' delete-char # Delete
bindkey '^[[Z' reverse-menu-complete # Ctrl-r
bindkey '^[[A' up-line-or-search # Arrow up
bindkey '^[[B' down-line-or-search # Arrow down

_currentEnvironmentName() {
  if [ -z "${CURRENT_ENVIRONMENT_NAME}" ]; then
    echo ""
  else
    echo "%{\e[38;5;250m%}[${CURRENT_ENVIRONMENT_NAME}]%{\e[39m%} "
  fi
}

_currentKubernetesContextName() {
  local context=$(kubectl config current-context 2> /dev/null);

  if [ -z "${context}" -o "${context}" = "docker-desktop" ]; then
    echo ""
  else
    echo "%{%F{1}%} ${context}%{%f%} "
  fi
}

setopt PROMPT_SUBST
export PROMPT='%B%c%b%f$(_currentKubernetesContextName)$(_currentEnvironmentName) %(?.%F{24}❯%f.%F{198}❯%f) '

source ${HOME}/.zsh/zaliases
source ${HOME}/.zsh/zcompletion

[[ -r ${HOME}/.zshrc.local ]] && source ${HOME}/.zshrc.local
[[ -r ${HOME}/.asdf/asdf.sh ]] && source ${HOME}/.asdf/asdf.sh
[[ -r ${HOME}/.config/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && source ${HOME}/.config/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

current_tt
