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

**Do not run `brew reinstall --cask` here.** Its uninstall replays the same
recorded artifact list (watch it print `Purging files for version
<old-version>`), so the stale link survives, the install half fails at the same
point — and the app is now uninstalled, leaving the link dangling. Observed on
2026-08-02 with obsidian: recovering from that took the fix below anyway.

The prohibition is about running it *now*, while the link is still there.
Reinstall becomes the right verb once the `rm` has cleared it — see the end of
this section.

**Fix** — drop the stale link, then install. It is a symlink *into* the app
bundle, not the CLI itself, so removing it loses nothing and the install
recreates it:

Inspect first — this step is deliberately its own block, because the next one
deletes:

```sh
ls -l "$(brew --prefix)/bin/<name>"
```

**Delete it only if the arrow points into the cask's own app bundle** — the
exact path `brew info --cask <cask>` prints under Artifacts, of the form
`/Applications/<App>.app/Contents/MacOS/<tool>`. That is the whole rule. It is
stated as one condition rather than a list of outputs on purpose: this error
fires for *any* resolving target Homebrew does not recognise as its own, so a
list of the shapes you might see will always be missing one, and the shapes are
easy to confuse at a glance.

Anything else is someone else's file and stops the recovery — a regular file, or
a symlink whose arrow points somewhere other than that bundle (another tool's
shim, a hand-made `ln -s`). Both are as capable of producing this error as the
stale cask link is, and only the arrow tells them apart.

Two readings are not "something else", though, and neither changes the rule:

- **A dangling arrow still counts as the cask's link.** The reinstall misstep
  above removes the app while leaving the link behind. `ls -l` never follows the
  arrow, so it prints the same line whether or not the target exists — judge by
  where the arrow points, not by whether it resolves.
- **`No such file or directory` means there is nothing to delete.** On a first
  attempt the path is wrong — stop and re-read the error. On a resumed run your
  earlier `rm` landed and the install did not: skip the `rm` and run the rest.

One more stop condition, unrelated to the output: if you are re-entering this
block after a run whose two confirmations already passed, the link is the
healthy one the fix just created. Deleting it now would not be undone by the
install below, which no-ops on a cask already at the tap version.

`ls -l` rather than `readlink` on purpose. `readlink` would answer the delete
question — it prints the arrow target for a symlink and nothing for anything
else — but the two "anything else" cases have *different* next steps here, and
it renders them identically: a regular file and a missing path both print
nothing and exit 1. `ls -l` separates them, which is what lets the two readings
above be two readings rather than one shrug.

A target under `$(brew --cellar)` is the one foreign shape this error cannot
produce: a formula owning the name makes Homebrew warn and skip the link rather
than fail. Stop for it anyway — the rule above is what you follow, not this
footnote.

Once the `ls -l` says the link is the cask's own, the rest runs together:

```sh
rm "$(brew --prefix)/bin/<name>"
brew install --cask <cask>
brew list --cask --versions <cask>       # confirm the new version landed
ls -l "$(brew --prefix)/bin/<name>"      # confirm the link came back
```

`brew install --cask` is correct whether or not the app survived the failure —
for an explicitly named cask that is already installed, it routes through the
upgrade path — so there is no need to check first and pick a different verb.

**Read the two confirmations; they can fail quietly.** The version line should
show the version the update was trying to install, and the `ls -l` should show
the link again. They fail in two different ways, and the pair tells you which:

- **Version right, `ls -l` prints nothing** — the install no-opped. Homebrew
  skips a cask already at the tap version (`Not upgrading <cask>, the latest
  version is already installed`), and skipping means nothing was re-linked. The
  version line still looks correct because it reports what is installed, which
  in this state already equals the tap version.
- **Version still the old one** — the install did not run at all, so the no-op
  above is not the explanation. Scroll back through its output for the real
  error before doing anything else.

Either way, the link is recreated with:

```sh
brew reinstall --cask <cask>
```

Which is safe *here*, and only here. The prohibition further up applies before
the `rm`, while the stale link is still blocking; once it is gone, reinstall has
nothing to trip over.

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
