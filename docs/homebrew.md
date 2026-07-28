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

Paths below are shown for the Apple Silicon prefix `/opt/homebrew`; Intel Macs
use `/usr/local`. The commands all derive it via `$(brew --prefix)`.

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

**Which branch you are in** turns on one question: does the live app still
exist? Homebrew stages the *live* app into this same path when it backs one up,
so the Caskroom copy is only disposable while `/Applications` still has its
own.

```sh
CASKROOM="$(brew --prefix)/Caskroom/<cask>/<old-version>"
ls -d "$CASKROOM/<App>.app" "/Applications/<App>.app"
```

Everything else — a missing `Contents/Info.plist`, a much smaller `du -sh` — is
corroboration that the leftover is a partial, not the decision itself.

**Branch A — `/Applications/<App>.app` exists.** The usual case, and the live
app is intact, so the Caskroom copy is disposable whether it is a partial or a
completed backup. Move it aside rather than deleting it, then re-run the
upgrade. The timestamped destination keeps a second occurrence from nesting
inside the first, and `${CASKROOM:?}` aborts loudly rather than building a path
rooted at `/` if the variable is unset:

```sh
CASKROOM="$(brew --prefix)/Caskroom/<cask>/<old-version>"   # repeated: do not rely on the block above
STALE="$HOME/Desktop/stale-<cask>-$(date +%Y%m%d%H%M%S).app"
mv "${CASKROOM:?set CASKROOM first}/<App>.app" "$STALE"
brew upgrade --cask <cask>
```

Once the upgrade succeeds, delete `$STALE`. If it fails instead, restore with:

```sh
mkdir -p "${CASKROOM:?set CASKROOM first}"   # a partial upgrade may have purged it
mv "$STALE" "${CASKROOM:?set CASKROOM first}/<App>.app"
```

Or skip the hand-move entirely: `brew reinstall --cask <cask>` clears the
leftover on its own, because reinstall always *forces* its internal uninstall
and a forced backup overwrites the staging directory instead of refusing. It
re-downloads the whole cask, so prefer the move above when the download is
large. Branch A only — if the live app is missing, use Branch B instead, which
recovers it without a download.

**Branch B — `/Applications/<App>.app` is missing.** The interruption landed
after the backup, so the Caskroom copy is the only app you have. Do **not**
move it to the Desktop. Put it back where it belongs:

```sh
mv "${CASKROOM:?set CASKROOM first}/<App>.app" "/Applications/<App>.app"
```

Never run that `mv` when `/Applications/<App>.app` already exists — `mv` onto
an existing bundle nests the copy *inside* it and corrupts the working app.
That is why the branch is gated on absence.

**Finish the update either way.** The failure aborted `update-brew` at its
second step, so `brew upgrade`, both cleanups, and `brew doctor` never ran.
Re-run the pipeline so the direct `brew` call stays a one-off:

```sh
just update
```

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
