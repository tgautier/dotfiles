# tmux

Terminal multiplexer configuration for macOS, Linux, and WSL2. Provides
persistent sessions, split panes, and window management from a single
terminal.

## Configuration overview

The config lives in `tmux.conf` (symlinked to `~/.tmux.conf` by rcm).

### Prefix

The prefix is `C-a` (Ctrl-a) instead of the default `C-b`. All shortcuts
below are written as `prefix + key`, meaning press `C-a`, release, then
press the key.

### Platform-aware clipboard

Copy mode (`prefix + [`) uses vi keybindings. Yanking (`y`) copies to
the system clipboard using the right tool for the platform:

| Platform | Clipboard tool |
| --- | --- |
| macOS | `pbcopy` |
| WSL | `clip.exe` |
| Linux | `xclip -in -selection clipboard` |

This is handled via `if-shell` platform detection in the config — no
manual setup needed.

### Status bar

Minimal top-positioned status bar:

- **Left**: session name in blue
- **Right**: current git branch (dimmed) + time
- **Active window**: cyan, bold
- **Inactive windows**: dimmed gray
- **Activity**: yellow highlight on windows with new output

### Pane styling

- Heavy border lines with blue for the active pane
- Inactive panes are slightly dimmed to make the active pane obvious

### Popups

- `prefix + t` — scratch terminal popup (80% of screen)
- `prefix + g` — lazygit popup (90% of screen)

## Cheat sheet

### Sessions

| Shortcut | Action |
| --- | --- |
| `prefix + s` | Switch session (tree view) |
| `prefix + d` | Detach from session |
| `prefix + $` | Rename session |

```sh
tmux                    # New session
tmux new -s name        # New named session
tmux ls                 # List sessions
tmux attach -t name     # Attach to session
tmux kill-session -t name
```

### Windows (tabs)

| Shortcut | Action |
| --- | --- |
| `prefix + c` | New window |
| `prefix + ,` | Rename window |
| `prefix + &` | Close window |
| `prefix + 1-9` | Switch to window by number |
| `prefix + C-h` | Previous window |
| `prefix + C-l` | Next window |
| `prefix + <` | Move window left |
| `prefix + >` | Move window right |

### Panes (splits)

| Shortcut | Action |
| --- | --- |
| `prefix + \|` | Split vertically (side by side) |
| `prefix + -` | Split horizontally (top/bottom) |
| `prefix + x` | Close pane |
| `prefix + z` | Toggle zoom (fullscreen pane) |
| `prefix + h/j/k/l` | Navigate panes (vi-style) |
| `prefix + H/J/K/L` | Resize pane (5 cells, repeatable) |
| `prefix + B` | Break pane to new window |
| `prefix + M` | Join pane from another window |
| `prefix + S` | Sync panes (type in all at once) |

### Copy mode

| Shortcut | Action |
| --- | --- |
| `prefix + [` | Enter copy mode |
| `v` | Start selection |
| `C-v` | Toggle rectangle selection |
| `y` | Copy to system clipboard |
| `q` | Exit copy mode |

### Other

| Shortcut | Action |
| --- | --- |
| `prefix + r` | Reload config |
| `prefix + t` | Popup scratch terminal |
| `prefix + g` | Popup lazygit |

## Troubleshooting

### Colors look wrong

Make sure your terminal reports as `xterm-256color`. The config sets
`default-terminal` to `tmux-256color` (falling back to `screen-256color`
if the terminfo is missing) and adds an RGB `terminal-overrides` entry
for `xterm-256color`, so your terminal emulator should use that terminfo
name.

### Clipboard not working on Linux

Install `xclip`:

```sh
sudo apt install -y xclip
```

### Clipboard not working on WSL

Ensure `clip.exe` is in PATH. The dotfiles add `/mnt/c/Windows/System32`
to PATH automatically for WSL.

### Mouse scroll enters copy mode

This is expected behavior. Scroll up enters copy mode, press `q` to exit.
