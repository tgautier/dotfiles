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

Absent `HOMEBREW_UPGRADE_GREEDY` and `HOMEBREW_UPGRADE_GREEDY_CASKS`,
`brew outdated --cask` runs the same non-greedy predicate as
the `brew bundle install` and `brew upgrade` steps of `update-brew` — so it
previews the update rather than offering a second opinion, and the cask that
fails is listed there too. (Set either variable and it stops being a preview:
`outdated` and `upgrade` honour them, `brew bundle install` does not. A
`greedy: true` option on a Brewfile entry pulls the other way, making `bundle`
greedier than `outdated` for that one cask. If you ever see the three disagree,
those are the two places to look.)

A cask that fails the update while `brew outdated --cask` stays quiet has two
possible causes, and one command tells them apart:

```sh
brew update && brew outdated --cask
```

Still empty means the app self-updated between the two runs — re-run
`just update`. Now listed means the earlier check read a stale tap:
`update-brew` refreshes it with `brew update` first, so a bare `brew outdated`
beforehand answers from whatever the last refresh left behind. The cask really
is outdated and `just update` will fail again on it, so go to the matching
section below — read the artifact word in the error, `App` or `Binary` — rather
than re-running the update.

Add `--greedy` and, for `auto_updates` casks, the list grows by every one whose
bundle is current and whose Homebrew metadata is merely stale. Those are the
ones `just update` leaves alone. (`--greedy` widens other classes too — notably
`version :latest` casks whose downloaded artifact changed — on rules of their
own.) The contrast is only ever between greedy and non-greedy, not between
`outdated` and the update itself.

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

Against a wedged *staging directory* specifically, three properties make it the
default rather than a fallback:

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

**Fix** — clear the leftover link, then install. **Not `brew reinstall --cask`,
which is the App conflict's remedy and the wrong move here**: its uninstall
replays the same recorded artifact list, so the link survives, the install half
fails at the identical point, and the app is gone. That prohibition is about
running it *first*; once the link is cleared it becomes useful again, at the end
of this section.

**Run this only while `just update` is actually failing with the Binary error.**
Everything below assumes that error is on your screen right now. If it is not —
you already ran the fix, or you are reading ahead — there is nothing to clear,
and deleting a healthy link would leave you worse off than when you started:
the install below does not recreate it, because Homebrew skips a cask already
at the tap version. (If you already did delete it, the first bullet under *Read
both confirmations* is the way back.)

Given that, one command decides the whole thing:

```sh
ls -l "$(brew --prefix)/bin/<name>"
```

**Delete it only if the arrow points at the artifact `brew info --cask <cask>`
lists under Artifacts** — for the app-plus-CLI casks this failure applies to,
that is a path inside the app bundle. Compare the two; do not pattern-match the
shape from memory.

Anything else belongs to something other than this cask and stops the recovery:
a regular file, or a symlink pointing anywhere else — another tool's shim, a
hand-made `ln -s`. Homebrew raises this error for any target it does not own,
excepting only one it can attribute to a formula of the same name, which it
warns about and skips instead. So "it is a symlink" is not the test. The arrow
is.

**`No such file or directory` has two causes with opposite answers, and the
error on your screen tells you which.** Homebrew raises only when something
*resolves* at that target, so while the error is live there IS a link and an
empty `ls -l` means you are looking at the wrong path — check the binary's
target name in `brew info --cask <cask>` and re-run the `ls -l`. Going on to
the install would leave the blocker untouched and reproduce the same error.
Only if your own `rm` already landed is there genuinely nothing to delete; skip
to the install.

The same "must resolve" rule means a **dangling** link is not a blocker at all:
Homebrew overwrites it. If the earlier reinstall misstep left one behind — app
gone, arrow pointing at nothing — the install alone is enough, though clearing
it first is harmless.

`readlink` would also answer the arrow question, but it prints nothing for both
a regular file and a missing path — one stops the recovery and the other does
not, and `ls -l` is what separates them.

With the link cleared or absent:

```sh
rm "$(brew --prefix)/bin/<name>"          # skip if there was nothing to delete
brew install --cask <cask>
brew list --cask --versions <cask>        # expect the version update wanted
ls -l "$(brew --prefix)/bin/<name>"       # expect the link back
```

`brew install --cask` is right whether or not the app survived — for a named
cask already installed it routes through the upgrade path, absent
`HOMEBREW_NO_INSTALL_UPGRADE`. An install that prints nothing at all points at
that variable.

**Read both confirmations.** They fail in two different ways:

- **Version right, `ls -l` empty** — you re-entered this fix after it had
  already succeeded, so the cask was already at the tap version and the install
  no-opped (`Not upgrading <cask>, the latest version is already installed`),
  re-linking nothing. The version line looks correct because it reports what is
  installed. This is the state the precondition warns about, and
  `brew reinstall --cask <cask>` is the way out: it recreates the link, and is
  safe here because the blocker is already gone.
- **Version still the old one** — the install ran and failed, and the revert put
  the old version back. The no-op above is not the explanation, so do not
  reinstall: scroll back for the error it printed and work from that.

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
