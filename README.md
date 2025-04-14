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

Change shell to use `zsh`:

```sh
chsh -s /bin/zsh
```

If you run into a warning with `compaudit`, fix permissions with:

```sh
compaudit | xargs chown -R "$(whoami)"
compaudit | xargs chmod go-w
```

Install asdf plugins:

```sh
cut -d' ' -f1 .tool-versions | xargs -t -L1 asdf plugin add
```

and finally:

```sh
asdf install
```

You are now good to go 🚀
