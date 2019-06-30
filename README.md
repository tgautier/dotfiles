# Dotfiles

Just a basic dotfiles repository

## Usage

Install Homebrew then run:

```sh
brew bundle --file=~/Workspace/tgautier/dotfiles/Brewfile
```

Link dotfiles:

```sh
rcup -d ~/Workspace/tgautier/dotfiles
```

If you run into a warning with `compaudit`, fix permissions with:

```sh
compaudit | xargs chown -R "$(whoami)"
compaudit | xargs chmod go-w
```
