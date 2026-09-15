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

### Auto-updating casks are left to their own updaters

Every cask failure recorded in this doc happened on a cask marked `auto_updates` (`brew info --cask <cask>` prints it next to the version). Such an app rewrites its own bundle between Homebrew runs. Homebrew's default is to upgrade it anyway whenever the version inside the bundle lags the tap, so two updaters end up managing one bundle, and the interrupted or contested swaps behind the App conflict below are the result. Google Chrome goes further: its updater runs as root through a privileged helper, which leaves the bundle owned by `root:wheel`, and Homebrew then cannot remove it from a terminal without the App Management permission. That failure has its own section below, and the auto-recovery in `update-brew` cannot reach it.

`HOMEBREW_NO_UPGRADE_AUTO_UPDATES_CASKS=1` turns that default off. `zshenv` exports it for interactive `brew` and the Justfile exports it for recipes, so the two never disagree. `brew bundle install`, `brew upgrade`, and `brew outdated --cask` share one non-greedy check, and with the variable set that check skips every `auto_updates` cask. Homebrew still installs those casks on a fresh machine, and `brew bundle cleanup --force` still removes one that leaves the Brewfile.

Two things follow:

- `brew list --cask --versions` reports the version Homebrew installed, not the one the app updated itself to. Read the running version from the app: `defaults read "/Applications/<App>.app/Contents/Info.plist" CFBundleShortVersionString`.
- Homebrew upgrades such an app only when asked by name. `brew upgrade --cask <cask>` checks a named cask greedily and ignores the variable, so it upgrades the cask whenever the tap is ahead of Homebrew's record. `--greedy` on the bare `brew upgrade` does the same for all of them, and `greedy: true` on a Brewfile entry does it for that cask inside `brew bundle install`. A root-owned app still needs the App Management permission first.

## Download stall detection

Homebrew passes `--retry 3` to curl, but no stall timeout. A connection that
dies mid-transfer without returning an error leaves curl waiting indefinitely,
and the whole `just update` chain blocks behind it.

`HOMEBREW_CURLRC` points Homebrew at `~/.config/homebrew/curlrc`, which sets
`speed-limit` and `speed-time`. Curl aborts a transfer that stays below
1000 bytes/s for 60 consecutive seconds, and `--retry` reconnects and resumes
from the partial file. The curlrc is deployed by chezmoi from
`config/homebrew/curlrc`.

Homebrew reads the variable and passes `--disable --config <path>`, which keeps
the default `~/.curlrc` disabled while loading the named file. Only Homebrew's
own curl invocations are affected.

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

**Automatic recovery** — `update-brew` detects this error, runs
`brew reinstall --cask` on the wedged cask, and retries `brew bundle install`.
Up to 3 casks are recovered per run. If the retry succeeds, the update
continues without manual intervention.

The auto-recovery handles only the App conflict. The Binary conflict below
requires manual inspection and is not retried automatically.

**Manual fix** — if auto-recovery fails or you hit this outside `just update`,
reinstall the cask:

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

Scope: the recovery below is written for a CLI that ships *inside* the app
bundle — meaning the source path `brew info --cask <cask>` lists under Artifacts
sits within `<App>.app`. Anything else links out of the Caskroom instead,
whether it prints as a bare relative string or as an absolute path under
`$(brew --caskroom)`. Only the comparison changes for those: check that the
`ls -l` arrow points inside `$(brew --caskroom)/<cask>/`, the same membership
test with the cask's Caskroom directory standing in for the app bundle, and the
rest of the section applies unaltered. Membership rather than a full path for
the same reason the rule below uses it: the staged path carries a version, and
the stale link was made by whichever version last linked it, not the one
`brew info` describes.

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

**Run this only while the Binary error is live** — from `just update`, or from a
`brew reinstall --cask` you already tried. Everything below assumes that error
is on your screen right now, and the link you would delete is a healthy one if
it is not. Having already run the fix, that link is the one the fix created, and
deleting it leaves you worse off than when you started: the install below will
not recreate it, because Homebrew skips a cask already at the tap version. Only
reading ahead, it is the healthy link for the version you have, and there is
nothing here to fix yet. (If you already did delete it, the first bullet under
*Read both confirmations* is the way back.)

Given that, one command decides the whole thing. Run it on the path the error
printed, not a rebuilt one: that is usually `$(brew --prefix)/bin/<name>`, but a
cask's `binary` stanza can name an absolute or `~`-rooted `target:`, which
Homebrew honours as written (expanding `~`) instead of placing it under `bin/`.

```sh
ls -l "<the path the error printed>"     # usually $(brew --prefix)/bin/<name>
```

**Delete it only if the arrow points inside the cask's own app bundle** —
normally the exact path `brew info --cask <cask>` lists under Artifacts, which
is what to compare against rather than pattern-matching the shape from memory.
Normally, because `brew info` describes the *tap* version while the stale link
was made by whichever version last linked it: a cask that moved its binary
between versions shows the old path in `ls -l` and the new one in `brew info`,
and the bundle test is the one that survives that. Mind that the two print in
opposite senses:

```text
ls -l      <prefix>/bin/<name> -> /Applications/<App>.app/.../<tool>
brew info  /Applications/<App>.app/.../<tool> -> <name> (Binary)
```

`ls -l` runs link → source; `brew info` runs source → link name. So the path
your `ls -l` arrow points *at* is the one on the **left** of the `brew info`
arrow. Comparing the two right-hand sides gives you a path against a bare token
and reads a perfectly good cask link as foreign.

At a path that exists, whatever the rule does not select stops the recovery — a
regular file, another tool's shim, a hand-made `ln -s`. Do not look for a second
test to settle those: the error cannot, because Homebrew raises for anything
that *resolves* at that path, the cask's own stale link included — which is why
you are here — excepting only a target resolving inside `$(brew --cellar)`,
which it attributes to a formula, warns about, and skips. Nor can "is it a
symlink". For a path that exists, the arrow is the only test. An empty `ls -l`
is a different question, read further down.

A **dangling** arrow does not change it either. `ls -l` never follows the arrow,
so it prints the same line whether or not the target exists — read where the
arrow points and apply the rule unchanged.

Danglingness is worth naming only because it is tempting to think it makes the
link harmless. It does not. It is what the earlier reinstall misstep leaves —
app deleted, arrow pointing at nothing — and the App artifact is installed
before the Binary one, so the bundle is back in place before the link is tested,
the arrow resolves again, and you get the identical error.

**`No such file or directory` has two causes with opposite answers.** Both look
the same on screen — the failed `just update` is still in your scrollback either
way — so the discriminator is where you are in this fix, not what you can see.
**Before** you have run the `rm` below, an empty `ls -l` means you are on the
wrong path: Homebrew raises only when something resolves at that target, so
while the error stands there is something there. Copy the path out of the error
itself, which prints it verbatim, and re-run the `ls -l` on that. Going on to
the install would leave the blocker untouched and reproduce the error. **After**
your own `rm` has landed, there is genuinely nothing to delete — skip to the
install.

`readlink` would also answer the arrow question, but it prints nothing for both
a regular file and a missing path. The first stops the recovery outright; the
second needs the reading above. `ls -l` at least tells those two apart.

With the link cleared or absent:

```sh
rm "<the path the error printed>"         # skip if there was nothing to delete
brew install --cask <cask>
brew list --cask --versions <cask>        # expect the version the update wanted
ls -l "<the path the error printed>"      # expect the link back
```

Same path as the inspect command above — the one the error named.

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
- **Version still the old one** — the no-op above is not the explanation, and
  what the install printed tells you which case you are in. An error means it
  ran and failed, and the revert put the old version back: work from that error,
  do not reinstall. *Nothing at all* printed means `HOMEBREW_NO_INSTALL_UPGRADE`,
  named above — there is no error to hunt, the upgrade was never attempted, and
  the link is still missing. Finish with `brew reinstall --cask <cask>`, which
  does not consult that variable, or unset it and re-run the install.

**Finish the update.** As with the App conflict, the rest of `update-brew` never
ran — re-run `just update` so the direct `brew` calls stay a one-off.

### Cask upgrade fails with `Operation not permitted` on `chown`

macOS only.

**Symptom**: `just update` dies in `update-brew` while removing the old app. Homebrew asks for your password, then prints one `chown` line per file in the bundle:

```text
==> Removing App '/Applications/<App>.app'
Password:
==> Using sudo to gain ownership of path '/Applications/<App>.app'
chown: /Applications/<App>.app/Contents/Info.plist: Operation not permitted
...
Error: <cask>: Permission denied @ apply2files - /Applications/<App>.app/Contents/CodeResources
```

It usually arrives wrapped in the App conflict: the first attempt left a backup in the Caskroom, so the next run fails on "already an App at", the auto-recovery reinstalls, and the reinstall fails here.

**Cause**: the bundle is owned by root. `ls -ld "/Applications/<App>.app"` shows `root wheel`, because the app's own updater installed the last version through a privileged helper. Homebrew installed the app as you and needs to move it, so it runs `sudo chown -R` to take ownership back. Since macOS Ventura, changing another developer's app in `/Applications` requires the calling terminal to hold the App Management permission (Full Disk Access also works), and `sudo` does not bypass that check. Every `chown` fails. As long as the whole bundle is root-owned, Homebrew aborts before it deletes anything, and the app keeps working.

With `HOMEBREW_NO_UPGRADE_AUTO_UPDATES_CASKS` set (see the section above), `just update` no longer upgrades the cask, so the failure stops recurring on its own. What remains is a stale Homebrew record and a leftover backup in the Caskroom.

**Fix**: grant the permission, then let Homebrew realign itself.

1. Open System Settings > Privacy & Security > App Management and enable your terminal (Ghostty in this Brewfile). Open a new terminal window afterwards.
1. Reinstall the cask. The forced uninstall now succeeds and clears the Caskroom leftover, and Homebrew's record moves to the tap version. Homebrew asks for your password for the `chown`.

   ```sh
   brew reinstall --cask <cask>
   ```

The permission is also what lets `brew bundle cleanup --force` remove such an app when it leaves the Brewfile, so grant it once per machine rather than per incident. Do not delete the Caskroom leftover by hand; the App conflict section explains why.

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
