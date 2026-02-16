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

# Cache kubectl context to avoid expensive checks on every prompt render
_kube_context_cache=""
_kube_context_cache_time=0

_currentKubernetesContextName() {
  local current_time=$(date +%s)
  local cache_age=$((current_time - _kube_context_cache_time))

  # Refresh cache every 30 seconds
  if [[ $cache_age -gt 30 ]]; then
    _kube_context_cache=$(kubectl config current-context 2> /dev/null)
    _kube_context_cache_time=$current_time
  fi

  if [ -z "${_kube_context_cache}" -o "${_kube_context_cache}" = "docker-desktop" ]; then
    echo ""
  else
    echo "%{%F{1}%} ${_kube_context_cache}%{%f%} "
  fi
}

setopt PROMPT_SUBST
export PROMPT='%B%c%b%f$(_currentKubernetesContextName)$(_currentEnvironmentName) %(?.%F{24}❯%f.%F{198}❯%f) '

source ${HOME}/.zsh/zaliases
source ${HOME}/.zsh/zcompletion

# WSL-specific optimizations
if [[ $PLATFORM == "wsl" ]]; then
  # Disable Windows PATH pollution (optional - uncomment if needed)
  # This can significantly speed up shell startup in WSL
  # export PATH=$(echo $PATH | tr ':' '\n' | grep -v "/mnt/" | tr '\n' ':' | sed 's/:$//')

  # Set umask for better Windows interop
  umask 022
fi

[[ -r ${HOME}/.zshrc.local ]] && source ${HOME}/.zshrc.local
[[ -r ${HOME}/.config/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && source ${HOME}/.config/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

# Initialize mise (version manager) if available
if command -v mise &> /dev/null; then
  eval "$(mise activate zsh)"
elif [[ -x "${HOME}/.local/bin/mise" ]]; then
  eval "$($HOME/.local/bin/mise activate zsh)"
fi
