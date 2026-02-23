#!/usr/bin/env bash
# Claude Code status line — mirrors zsh PROMPT style + Claude context
# Input: JSON from stdin

input=$(cat)

# --- Extract fields ---
cwd=$(echo "$input"        | jq -r '.workspace.current_dir // .cwd // ""')
model_name=$(echo "$input" | jq -r '.model.display_name // .model // ""')
used=$(echo "$input"       | jq -r '.context_window.used_percentage // empty')
version=$(echo "$input"    | jq -r '.version // empty')

# Shorten model name: "Claude 3.5 Sonnet" → "Sonnet 3.5", "Claude Opus 4" → "Opus 4"
if [ -n "$model_name" ] && [ "$model_name" != "null" ]; then
  short_model=$(echo "$model_name" | sed 's/Claude //; s/\([A-Za-z]*\) \([0-9.]*\)/\1 \2/')
else
  short_model=""
fi

# --- Directory: basename only (mirrors %c), replace $HOME with ~ ---
if [ -n "$cwd" ]; then
  home="$HOME"
  full_dir="${cwd/#$home/~}"
  dir=$(basename "$full_dir")
  # Keep ~ as-is when cwd == $HOME
  [ "$cwd" = "$home" ] && dir="~"
else
  dir="?"
fi

# --- Git branch (skip optional lock to avoid conflicts) ---
branch=$(git -C "$cwd" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null \
         || git -C "$cwd" --no-optional-locks rev-parse --short HEAD 2>/dev/null)

# --- Kubernetes context (mirrors _currentKubernetesContextName) ---
kube_ctx=$(kubectl config current-context 2>/dev/null)
if [ -n "$kube_ctx" ] && [ "$kube_ctx" != "docker-desktop" ]; then
  kube_str="$kube_ctx"
else
  kube_str=""
fi

# --- Docker context (show compose project if in a compose directory) ---
docker_compose=""
if [ -n "$cwd" ]; then
  for f in "$cwd/docker-compose.yml" "$cwd/docker-compose.yaml" "$cwd/compose.yml" "$cwd/compose.yaml"; do
    if [ -f "$f" ]; then
      # Count running containers for this project
      project=$(basename "$cwd" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]//g')
      running=$(docker compose -f "$f" ps --status running --format json 2>/dev/null | jq -s 'length' 2>/dev/null)
      total=$(docker compose -f "$f" ps --format json 2>/dev/null | jq -s 'length' 2>/dev/null)
      if [ -n "$total" ] && [ "$total" -gt 0 ] 2>/dev/null; then
        docker_compose="${project} ${running:-0}/${total}"
      else
        docker_compose="${project}"
      fi
      break
    fi
  done
fi

# --- Current environment name (mirrors _currentEnvironmentName) ---
env_str="${CURRENT_ENVIRONMENT_NAME:-}"

# --- Context bar (5 blocks) ---
if [ -n "$used" ] && [ "$used" != "null" ]; then
  filled=$(echo "$used" | awk '{printf "%d", ($1 / 20 + 0.5)}')
  # clamp 0..5
  [ "$filled" -lt 0 ] && filled=0
  [ "$filled" -gt 5 ] && filled=5
  bar=""
  for i in 1 2 3 4 5; do
    if [ "$i" -le "$filled" ]; then
      bar="${bar}█"
    else
      bar="${bar}░"
    fi
  done
  ctx_str="${bar} ${used}%%"
else
  ctx_str=""
fi

# --- Version ---
if [ -n "$version" ] && [ "$version" != "null" ]; then
  ver_str="v${version}"
else
  ver_str=""
fi

# --- Assemble one-liner ---
# Colors (dim — terminal will further dim these)
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[36m'
YELLOW='\033[33m'
BLUE='\033[34m'
GREEN='\033[32m'
RED='\033[31m'
MAGENTA='\033[35m'
GREY='\033[38;5;250m'
sep="${DIM} ｜ ${RESET}"

# Directory segment (bold, mirrors %B%c%b)
printf "${BOLD}${BLUE}📂 ${dir}${RESET}"

# Branch segment
if [ -n "$branch" ]; then
  printf "${sep}${GREEN}🌿 ${branch}${RESET}"
fi

# Kubernetes context segment (red, mirrors _currentKubernetesContextName)
if [ -n "$kube_str" ]; then
  printf "${sep}${RED}⎈ ${kube_str}${RESET}"
fi

# Docker Compose segment (magenta)
if [ -n "$docker_compose" ]; then
  printf "${sep}${MAGENTA}🐳 ${docker_compose}${RESET}"
fi

# Environment name segment (grey, mirrors _currentEnvironmentName)
if [ -n "$env_str" ]; then
  printf "${sep}${GREY}[${env_str}]${RESET}"
fi

# Context segment
if [ -n "$ctx_str" ]; then
  printf "${sep}${YELLOW}📊 ${ctx_str}${RESET}"
fi

# Model segment
if [ -n "$short_model" ]; then
  printf "${sep}${CYAN}🧠 ${short_model}${RESET}"
fi

# Version segment (subtle)
if [ -n "$ver_str" ]; then
  printf "${sep}${DIM}💻 ${ver_str}${RESET}"
fi

printf "\n"
