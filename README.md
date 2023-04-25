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

Install `asdf`:

```sh
git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.9.0
```

⚠️ Check the latest stable version, at the time of this writing it's `0.9.0`

Then install asdf plugins:

```sh
cut -d' ' -f1 .tool-versions | xargs -t -L1 asdf plugin add
```

and finally:

```sh
asdf install
```

### 1Password SSH Agent

```sh
mkdir -p ~/.1password && ln -s ~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock ~/.1password/agent.sock
```

You are now good to go 🚀
