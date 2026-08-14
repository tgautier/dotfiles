# Local shipping gate

This repository uses a local exact-tip gate as its shipping authority. GitHub Actions is disabled, so each checkout must wire and use the tracked hooks. GitHub branch protection requires the externally published `local/exact-tip` commit status and requires the branch to be up to date with `main` before squash merge.

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

## Attest and publish the final commit

Create commits through the normal signed flow. The pre-commit hook checks the effective author and committer identity, resolves mise, and runs `just ci`.

When the branch is ready to publish, attest its clean tip:

```sh
just ci-attest
git push
just ci-publish
```

`just ci-attest` removes any prior evidence before it starts. It runs the complete `just ci` recipe, then checks that `HEAD` and the working tree did not change.

After those checks pass, the command writes the full commit SHA atomically under the checkout's Git directory. Linked worktrees therefore keep separate evidence.

Pre-push accepts one checked-out branch tip. It rejects direct pushes to `main` or `master`, dirty state, stale evidence, wrong-tip evidence, pushed commits without Git signature headers, shallow history, and hooks from another checkout.

After the SSH push succeeds, `just ci-publish` verifies the same clean local attestation, canonical SSH fetch and push URLs, the exact remote branch SHA, and current `origin/main` ancestry. It then publishes `local/exact-tip=success` through the GitHub commit-status API and reads that status back. Strict branch protection invalidates merge readiness if `main` advances after publication; update the branch, create a new signed commit, and repeat all three commands.

This repository allows squash merges only. GitHub therefore creates a new one-parent commit whose tree is the tested branch tree; the server-created squash SHA is not the local branch SHA. The required exact-tip status and strict up-to-date rule bind the tested branch input to that squash operation without spending GitHub Actions minutes.

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
| `origin fetch URL must be exactly` or `origin push URL must be exactly` | Restore both sides of `origin` to `git@github.com:tgautier/dotfiles.git`; HTTPS, split, and alternate URLs are rejected |
| `pushed branch ... does not equal local HEAD` | Push the checked-out branch through the normal hook, then rerun `just ci-publish` |
| `branch is not up to date with origin/main` | Merge or rebase current `main`, create and attest the resulting signed tip, push it, then rerun `just ci-publish` |
| `GitHub rejected` or `could not read back` | Check `gh auth status` and network access, then rerun `just ci-publish`; do not synthesize a success status |

Do not use `--no-verify`. A bypass removes the local evidence that replaces hosted CI.

## Upgrade without changing deployed dotfiles

After pulling a branch that contains this change, update that checkout in this order:

```sh
git pull --ff-only
just git-hooks
just test-local-gate
just ci-attest
git push
just ci-publish
```

After the pull, the gate-specific commands change only the checkout's local Git configuration and its private attestation marker. They do not run rcm, chezmoi, `just link`, or `just setup`.

Keep the checkout on its current working branch until its changes are committed. Do not switch or reset over unrelated work to perform this upgrade.

## Roll back through a signed revert

If the local gate must be removed after merge, start from a clean checkout and revert the one-parent squash commit on a dedicated branch. Do not use `git revert -m`: `-m` selects a parent of a merge commit, while this repository allows squash merges only.

```sh
git fetch origin
git switch -c revert/local-shipping-gate origin/main
git revert SQUASH_COMMIT_SHA
just ci
git push -u origin revert/local-shipping-gate
rollback_sha=$(git rev-parse HEAD)
test -z "$(git status --porcelain=v1 --untracked-files=normal)"
test "$(git ls-remote --heads origin refs/heads/revert/local-shipping-gate)" = "$rollback_sha$(printf '\t')refs/heads/revert/local-shipping-gate"
gh api --method POST "repos/tgautier/dotfiles/statuses/$rollback_sha" --field state=success --field context=local/exact-tip --field description='Complete local gate passed for the exact branch tip'
gh api "repos/tgautier/dotfiles/commits/$rollback_sha/status" --jq '[.statuses[] | select(.context == "local/exact-tip")] | first | [.sha, .state, .context] | @tsv'
```

The final command must print the rollback SHA, `success`, and `local/exact-tip`. This manual publication is necessary because the revert intentionally removes `ci-publish`; run it only after `just ci` passes, the checkout is clean, and the rollback SHA has been pushed.

Open and merge the revert pull request. The revert restores the hosted workflow and the earlier pre-commit hook. Then remove the local status requirement, which is repository configuration and therefore is not reverted by Git:

```sh
gh api --method DELETE repos/tgautier/dotfiles/branches/main/protection/required_status_checks
```

Read branch protection back before accepting further pull requests. The old local attestation file may remain under the Git directory because no restored hook reads it.

Rollback does not require an rcm or chezmoi operation. This change never takes ownership of deployed dotfiles or modifies HOME.

## Know the evidence boundary

The gate proves that the complete local repository checks passed for one unchanged clean commit in one checkout, that this commit was the pushed branch tip when its status was published, and that branch protection accepted the status for the latest up-to-date pull-request head. It also requires signature headers on commits introduced after the documented migration cutoff.

The commit-status API trusts the authenticated repository owner, just as local hooks trust the operator not to bypass them; this is enforced workflow evidence, not a cryptographic attestation service. The gate does not prove live HOME state, another clone's state, or remote service behavior. Run the migration-specific inventory and rollback procedures separately when a chezmoi phase changes deployed files.
