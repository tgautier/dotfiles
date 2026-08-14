# Local shipping gate

This repository uses a local exact-tip gate as its shipping authority. GitHub Actions is disabled, so each checkout must wire and use the tracked hooks.

The gate is self-contained. It does not read the private companion repository or change files in HOME.

## Install hooks in each checkout

Run the dedicated setup after cloning, adding a worktree, or pulling a hook change:

```sh
just git-hooks
```

The command sets `core.hooksPath` to `.githooks` in the repository's local Git config. The full machine bootstrap also runs this command.

Verify the result:

```sh
git config --local --get core.hooksPath
```

The command must print `.githooks`.

## Attest the final commit before push

Create commits through the normal signed flow. The pre-commit hook checks the effective author and committer identity, resolves mise, and runs `just ci`.

When the branch is ready to publish, attest its clean tip:

```sh
just ci-attest
git push
```

`just ci-attest` removes any prior evidence before it starts. It runs the complete `just ci` recipe, then checks that `HEAD` and the working tree did not change.

After those checks pass, the command writes the full commit SHA atomically under the checkout's Git directory. Linked worktrees therefore keep separate evidence.

Pre-push accepts one checked-out branch tip. It rejects direct pushes to `main` or `master`, dirty state, stale evidence, wrong-tip evidence, pushed commits without Git signature headers, shallow history, and hooks from another checkout.

Any new commit makes the recorded SHA stale. Any tracked or untracked working-tree change blocks its use. Run `just ci-attest` again only after the final state is clean.

## Recover from a blocked push

Use the diagnostic printed by the hook:

| Diagnostic | Recovery |
| --- | --- |
| `mise not found` | Restore mise on `PATH`, or install it under `~/.local/bin`, then run `just ci-attest` |
| `checkout is dirty` | Inspect `git status`, finish or remove only your own changes, then run `just ci-attest` |
| `no trusted attestation` or `attestation covers` | Run `just ci-attest` for the current clean `HEAD` |
| `malformed attestation` | Remove only the marker path printed by the diagnostic, then run `just ci-attest` |
| `commit ... has no Git signature header` | Restore the configured SSH signer, recreate the unsigned commit through the normal signed flow, then attest the new tip |
| `repository history is shallow` | Confirm with `git rev-parse --is-shallow-repository`, run `git fetch --unshallow`, then attest again |
| `hook root does not match` | Run `just git-hooks` in the checkout being pushed |

Do not use `--no-verify`. A bypass removes the local evidence that replaces hosted CI.

## Upgrade without changing deployed dotfiles

After pulling a branch that contains this change, update that checkout in this order:

```sh
git pull --ff-only
just git-hooks
just test-local-gate
just ci-attest
```

After the pull, the gate-specific commands change only the checkout's local Git configuration and its private attestation marker. They do not run rcm, chezmoi, `just link`, or `just setup`.

Keep the checkout on its current working branch until its changes are committed. Do not switch or reset over unrelated work to perform this upgrade.

## Roll back through a signed revert

If the local gate must be removed after merge, start from a clean checkout and revert its merge commit on a dedicated branch:

```sh
git fetch origin
git switch -c revert/local-shipping-gate origin/main
git revert MERGE_COMMIT_SHA
just ci
git push -u origin revert/local-shipping-gate
```

Open and merge the revert pull request. The revert restores the hosted workflow and the earlier pre-commit hook. The old local attestation file may remain under the Git directory because no restored hook reads it.

Rollback does not require an rcm or chezmoi operation. This change never takes ownership of deployed dotfiles or modifies HOME.

## Know the evidence boundary

The gate proves that the complete local repository checks passed for one unchanged clean commit in one checkout. It also requires signature headers on commits introduced after the documented migration cutoff.

The gate does not prove live HOME state, another clone's state, or remote service behavior. Run the migration-specific inventory and rollback procedures separately when a chezmoi phase changes deployed files.
