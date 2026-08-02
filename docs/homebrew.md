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

### Why an auto-updating cask is upgraded at all

Both failures below hit casks marked `auto_updates` (`brew info --cask <cask>`
prints it next to the version), which raises the obvious question — those apps
update themselves, so why is Homebrew touching them at all?

Because a non-greedy check skips an `auto_updates` cask *unless* the version
inside the installed app bundle is behind the tap, which Homebrew upgrades by
default (opt out with `HOMEBREW_NO_UPGRADE_AUTO_UPDATES_CASKS`). So one reaches
an upgrade exactly when the app has *not* self-updated.

`brew outdated --cask` runs the same non-greedy predicate as the `brew bundle
install` and `brew upgrade` steps of `update-brew`, so it is a faithful preview
rather than a second opinion: the cask that fails the update is listed there
too. If it is *not* listed, the app self-updated between the two runs — re-run
`just update` rather than hunting a discrepancy that isn't one.

Add `--greedy` and the list grows by every cask whose bundle is current and
whose Homebrew metadata is merely stale. Those are the ones `just update`
leaves alone, and the contrast is only ever between greedy and non-greedy — not
between `outdated` and the update itself.

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
self-updating app racing brew) and left something behind in the Caskroom
staging directory. Before swapping in the new version, Homebrew backs the live
app up into that exact path:

```text
==> Backing up App '<App>.app' to '/opt/homebrew/Caskroom/<cask>/<old-version>/<App>.app'
```

An unforced upgrade refuses to overwrite what is already sitting there, so
every subsequent `just update` fails the same way until the leftover is
cleared.

**Fix** — reinstall the cask:

```sh
brew reinstall --cask <cask>
```

That is the whole remedy **for this symptom**, and not a general fix for a
wedged cask — read the error text before reaching for it. It does *not* resolve
the Binary conflict documented below: there its uninstall leaves the blocker in
place, so it fails at the same point having already removed the app.

Three properties make it the default rather than a fallback here:

- Its internal uninstall is **forced**, so the backup step overwrites the
  wedged staging directory instead of refusing — which is exactly what a plain
  `brew upgrade` cannot do.
- It **fetches before it uninstalls**, so a failed or interrupted download
  leaves the current install untouched.
- It yields a known-good bundle regardless of what the leftover was, and the
  leftover can be any of three shapes: a truncated partial, a *complete* backup
  of the live app, or a wrapper directory holding a nested `<App>.app` from an
  earlier bad move. Inspecting which one you have is exactly the step this
  avoids.

**Do not clear the staging directory by hand.** The interrupted upgrade may
already have stripped the live app — either removing `/Applications/<App>.app`
outright, or leaving the directory in place with its contents gone — so the
Caskroom leftover can be the only copy you have, and deleting it can lose the
app. Reinstall does not need the staging directory cleared — its uninstall is
forced, per the first property above.

**Reinstall lands the current version, and does not preserve the old one.** A
cask tap generally serves only the current version, so once the forced
uninstall runs there is no Homebrew route back to what was installed before.
That is the same version `just update` was trying to install, so it is normally
what you want.

Needing a *different* version is a separate task: pinning or downgrading a cask
has its own constraints and is out of scope here.

Do not improvise a rollback by copying the Caskroom leftover aside. It is one
of the three shapes above, only one of which is a working app, so the copy may
be unlaunchable — and restoring it is not symmetric: Homebrew's metadata would
still record the new version, leaving `brew list --cask --versions` and the
next `just update` disagreeing with what is on disk.

Hand-moving the leftover buys nothing either. `brew upgrade --cask` fetches the
same artifact `brew reinstall --cask` does, and the aborted upgrade already
downloaded it — `brew cleanup --prune=all` never ran, so it is still cached.
The manual route costs the same download and adds every failure mode reinstall
avoids.

**Finish the update.** The failure aborted `update-brew` at its second step, so
`brew upgrade`, both cleanups, and `brew doctor` never ran. Re-run the pipeline
so the direct `brew` call stays a one-off:

```sh
just update
```

### Cask upgrade fails with "there is already a Binary at"

macOS only, and distinct from the App conflict above despite the near-identical
wording — **the remedy above makes this one worse**. Read the artifact word in
the error: `App` or `Binary`.

**Symptom** — `just update` dies in `update-brew`, and the upgrade rolls itself
back first:

```text
==> Moving App '<App>.app' to '/Applications/<App>.app'
Warning: Reverting upgrade for Cask <cask>
==> Removing App '/Applications/<App>.app'
==> Purging files for version <new-version> of Cask <cask>
==> Moving App '<App>.app' to '/Applications/<App>.app'
Error: <cask>: It seems there is already a Binary at '/opt/homebrew/bin/<name>'.
```

The app is back where it started — the revert is the *consequence*, not the
problem. The Binary line is the one that matters.

**Cause** — the cask ships a CLI alongside the app (`brew info --cask <cask>`
lists it under Artifacts as `.../<App>.app/Contents/MacOS/<tool> -> <name>
(Binary)`). Homebrew replays the *installed* version's artifact list to
uninstall it, and that recorded list can be missing the Binary. Re-running with
`--debug` prints the set it loaded; for obsidian 1.12.7 it held only
`Cask::Artifact::App` and `Cask::Artifact::Zap`.

So the upgrade's uninstall half never unlinks `/opt/homebrew/bin/<name>`, and
the new version's install half refuses to overwrite an existing target. Every
subsequent `just update` repeats it, because the failure leaves the same
leftover behind.

**Do not run `brew reinstall --cask` here.** Its uninstall replays the same
recorded artifact list (watch it print `Purging files for version
<old-version>`), so the stale link survives, the install half fails at the same
point — and the app is now uninstalled. Observed on 2026-08-02 with obsidian:
recovering from that took the fix below anyway.

**Fix** — drop the stale link, then install. It is a symlink *into* the app
bundle, not the CLI itself, so removing it loses nothing and the install
recreates it:

```sh
readlink "$(brew --prefix)/bin/<name>"   # expect: .../<App>.app/Contents/MacOS/<tool>
rm "$(brew --prefix)/bin/<name>"
brew install --cask <cask>
```

Confirm what `readlink` prints before deleting — the fix assumes a symlink the
cask owns. A path into the app bundle is that. A real file is not, and is
someone else's install to investigate rather than delete. A path under
`$(brew --cellar)` means a formula owns the name, which Homebrew detects and
warns past instead of failing on, so it cannot be what produced this error.

Use `brew upgrade --cask <cask>` in place of the install if the app is still
there; `brew list --cask --versions <cask>` says which. After the reinstall
misstep above it is gone, and `install` is the right call.

**Finish the update.** As with the App conflict, the rest of `update-brew` never
ran — re-run `just update` so the direct `brew` calls stay a one-off.

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
