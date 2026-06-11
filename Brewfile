tap "roborev-dev/tap"
tap "terror/tap"

# CLI Tools & Development
brew "act"
brew "argocd"
brew "autoconf"
brew "automake"
brew "awscli"
brew "biome"
brew "caddy"
brew "cairo"
brew "calicoctl"
brew "cmake"
brew "cocoapods"
brew "confuse"
brew "coreutils"
brew "ctags"
brew "curl"
brew "doctl"
brew "duti"
brew "eksctl"
brew "ethereum"
brew "ffmpeg"
brew "flux"
brew "flyctl"
brew "fontconfig"
brew "freetype"
brew "gdbm"
brew "gemini-cli"
brew "gettext"
brew "gh"
brew "git"
brew "glab"
brew "glib"
brew "gnupg"
## hermes-agent: native installer via `just setup` (self-updates via `hermes update`)
brew "hivemind"
brew "htop"
brew "httpie"
brew "hyperfine"
brew "iftop"
brew "imagemagick"
brew "iperf3"
brew "jpeg"
brew "jpegoptim"
brew "jq"
brew "just"
brew "k6"
brew "kind"
brew "kops"
brew "kubectx"
brew "kubeseal"
brew "kubie"
brew "kustomize"
brew "libevent"
brew "libffi"
brew "libpng"
brew "libpq"
brew "librsvg"
brew "libtiff"
brew "libtool"
brew "libyaml"
brew "linkerd"
brew "markdownlint-cli2"
brew "mas"
brew "minikube"
brew "mkcert"
brew "nats-server"
brew "nginx"
brew "nss"
brew "openclaw-cli"
brew "openconnect"
brew "openssl"
brew "optipng"
brew "overmind"
brew "pango"
brew "pcre"
brew "perl"
brew "pixman"
brew "pkg-config"
brew "pnpm"
brew "podman"
brew "poppler"
brew "rcm"
brew "redis"
brew "roborev-dev/tap/roborev"
brew "rustup"
brew "shellcheck"
brew "sops"
brew "sox"
brew "sqlite"
brew "step"
brew "stern"
brew "svn"
brew "telnet"
brew "terror/tap/just-lsp"
brew "tmux"
brew "tree"
brew "unixodbc"
brew "unzip"
brew "urlview"
brew "uv"
brew "watch"
brew "wget"
brew "wxwidgets"
brew "yt-dlp"
brew "ytt"
brew "zsh-completions"

# Applications
cask "1password"
cask "1password-cli"
cask "android-studio"
cask "claude"
## claude-code: native installer via `just setup` (auto-updates, no deps)
cask "codex"
cask "codex-app"
cask "copilot-cli"
cask "docker-desktop"
cask "firefox"
cask "gcloud-cli"
cask "ghostty"
cask "google-chrome"
cask "iterm2"
cask "lm-studio"
cask "obsidian"
cask "parsec"
cask "postman"
cask "signal"
cask "slack"
cask "spotify"
cask "visual-studio-code"
cask "vlc"
cask "whatsapp"

# Fonts
cask "font-fira-code"
cask "font-source-code-pro"

# Mac App Store Applications
mas "1Password for Safari", id: 1569813296
mas "Keynote", id: 361285480
mas "Numbers", id: 361304891
mas "Pages", id: 361309726
mas "Xcode", id: 497799835

# Profile overlay
# Everything above is shared by every macOS machine. Machine-specific entries
# live in Brewfile.work / Brewfile.personal and are merged in here so that
# `brew bundle` AND `brew bundle cleanup` operate on the full per-machine set.
# The profile is read from ~/.config/dotfiles/profile (set it with
# `just set-profile work|personal`; interactive `just setup` prompts for it
# on first run, defaulting the answer to "work" so a fresh machine never
# installs personal apps by accident — non-interactive runs fail instead of
# guessing). An absent, empty, or unknown marker fails loud: silently merging
# the wrong overlay would let `brew bundle cleanup --force` (in `just
# update-brew`) uninstall every overlay app on the machine.
profile_path = File.expand_path("~/.config/dotfiles/profile")
profile = File.exist?(profile_path) ? File.read(profile_path).strip : ""
unless %w[work personal].include?(profile)
  raise "No valid machine profile in #{profile_path} (got #{profile.inspect}) — run 'just set-profile work|personal'"
end
overlay = File.expand_path("Brewfile.#{profile}", __dir__)
raise "Missing overlay #{overlay}" unless File.exist?(overlay)
instance_eval(File.read(overlay), overlay)
