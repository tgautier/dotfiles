# Homebrew

Operating notes for the `just update` pipeline, which is dominated by
Homebrew. Packages are declared in the Brewfiles and applied through `just`
recipes — never through raw `brew install`.

For Brewfile authoring conventions (file set, profile overlays, sorting, the
native-installer pattern), see `.claude/rules/brewfile.md`. This doc covers
*operating* the toolchain: the update flow and recovery from a wedged state.

## Update flow

`just update` runs `update-brew` first, which is the step most likely to fail
because it touches the network and mutates installed apps:

```sh
brew update                     # refresh formula/cask definitions
brew bundle install --file=...  # install missing AND upgrade outdated
brew upgrade                    # upgrade whatever the Brewfile pass left
brew cleanup --prune=all
brew bundle cleanup --force --file=...
brew doctor                     # non-fatal: prefixed with `-` in the Justfile
```

Note the asymmetry with `just setup`, which runs `brew bundle install` **with**
`--no-upgrade`. Bootstrap is deliberately install-only, so a fresh machine does
not depend on every pre-existing package upgrading cleanly. `update-brew` omits
the flag because upgrading is the point — which is also why a single wedged
cask takes the whole update down, and why the failure below surfaces during
`brew bundle install` rather than during `brew upgrade`.

A failure in `brew bundle install` aborts the whole recipe by design. Do not
paper over it with `|| true` or `continue-on-error` — a red `just update` means
a package really is broken, and silencing it hides a half-installed app until
something else breaks.

## Troubleshooting

### Cask upgrade fails with "there is already an App at"

macOS only — `Brewfile.linux` declares no casks, so there is no Caskroom
staging directory to wedge.

**Symptom** — `just update` dies in `update-brew` with a single failed cask:

```text
Error: <cask>: It seems there is already an App at
'/opt/homebrew/Caskroom/<cask>/<old-version>/<App>.app'.
==> Purging files for version <new-version> of Cask <cask>
`brew bundle` failed! 1 Brewfile dependency failed to install
```

**Cause** — an earlier cask upgrade was interrupted (Ctrl-C, sleep, crash, or a
self-updating app racing brew) and left a partial app bundle in the Caskroom
staging directory. Before swapping in the new version, Homebrew backs the live
app up into that exact path:

```text
==> Backing up App '<App>.app' to '/opt/homebrew/Caskroom/<cask>/<old-version>/<App>.app'
```

An unforced upgrade refuses to overwrite what is already sitting there, so
every subsequent `just update` fails the same way until the leftover is
cleared.

**Confirm it is a stale partial** — compare it against the live app. The
leftover is typically missing `Contents/Info.plist` and is much smaller than
the installed copy:

```sh
CASKROOM="$(brew --prefix)/Caskroom/<cask>/<old-version>"
ls -la "$CASKROOM/<App>.app/Contents/"
du -sh "$CASKROOM/<App>.app" "/Applications/<App>.app"
```

**Fix** — move the leftover aside rather than deleting it outright, so the step
is reversible, then re-run the upgrade. The timestamped destination keeps a
second occurrence from nesting inside the first:

```sh
CASKROOM="$(brew --prefix)/Caskroom/<cask>/<old-version>"   # repeated: do not rely on the block above
STALE="$HOME/Desktop/stale-<cask>-$(date +%Y%m%d%H%M%S).app"
mv "$CASKROOM/<App>.app" "$STALE"
brew upgrade --cask <cask>
brew list --cask --versions <cask>   # verify the new version landed
```

Once the upgrade succeeds, delete `$STALE`. If the upgrade fails instead,
restore with `mv "$STALE" "$CASKROOM/<App>.app"` — run it in the same shell, or
re-assign `CASKROOM` first. With `CASKROOM` unset that command expands to the
volume root, so never run the restore against a bare `/<App>.app`.

`brew reinstall --cask <cask>` also clears the leftover, because reinstall
always *forces* its internal uninstall and a forced backup overwrites the
staging directory instead of refusing. It re-downloads the entire cask, so
prefer clearing the directory when the download is large.

### `brew bundle` fails on a missing profile marker

macOS only — `Brewfile.linux` has no profile overlay and never reads the
marker.

`brew bundle` fails loud when `~/.config/dotfiles/profile` is absent, empty, or
unknown, because merging the wrong overlay would make `brew bundle cleanup
--force` uninstall the other profile's apps. Set it:

```sh
just set-profile work    # or: personal
```

### mise warns about the python-build repo

A warning like `failed to update python-build repo ... 'origin' does not
appear to be a git repository` in `update-mise` is self-healing — mise reclones
the cached pyenv checkout in the same run and continues.

To confirm, re-run `mise outdated` on its own and check that the warning does
not recur. Use `mise outdated`, not `just update-mise`: the recipe also runs
`mise upgrade --bump`, which upgrades tools and rewrites the version pins — far
more than a diagnostic should do. Judge by the warning text, not the exit
code: `mise outdated` exits 0 whether or not tools are outdated, which is
exactly why the recipe can run it first under just's fail-fast.
