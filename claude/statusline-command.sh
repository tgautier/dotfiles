#!/usr/bin/env bash
# Claude Code status line — beautiful one-liner with nerd font icons
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

# --- Directory: replace $HOME with ~ ---
if [ -n "$cwd" ]; then
  home="$HOME"
  dir="${cwd/#$home/\~}"
else
  dir="?"
fi

# --- Git branch ---
branch=$(git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null || git -C "$cwd" rev-parse --short HEAD 2>/dev/null)

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
  ctx_str="${bar} ${used}%"
else
  ctx_str=""
fi

# --- Model + Version (combined) ---
if [ -n "$short_model" ] && [ -n "$version" ] && [ "$version" != "null" ]; then
  model_ver_str="${short_model} v${version}"
elif [ -n "$short_model" ]; then
  model_ver_str="${short_model}"
elif [ -n "$version" ] && [ "$version" != "null" ]; then
  model_ver_str="v${version}"
else
  model_ver_str=""
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
MAGENTA='\033[35m'

sep="${DIM} ｜ ${RESET}"

# Directory segment
printf "${BOLD}${BLUE} ${dir}${RESET}"

# Branch segment
if [ -n "$branch" ]; then
  printf "${sep}${GREEN} ${branch}${RESET}"
fi

# Model segment
if [ -n "$short_model" ]; then
  printf "${sep}${CYAN}󰧑 ${short_model}${RESET}"
fi

# Context segment
if [ -n "$ctx_str" ]; then
  printf "${sep}${YELLOW}󰾆 ${ctx_str}${RESET}"
fi

# Model + Version segment (subtle)
if [ -n "$model_ver_str" ]; then
  printf "${sep}${DIM}${model_ver_str}${RESET}"
fi

printf "\n"
