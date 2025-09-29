# Dotfiles

Just a basic dotfiles repository

## Usage

Install Homebrew

```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install packages from Brewfile:

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

Install mise:

```sh
curl https://mise.run | sh
```

and finally:

```sh
mise install
```

You are now good to go 🚀
