# Chezmoi operator cutover

This runbook records the approval-bound first live apply of the public and optional private chezmoi sources. Rcm remains installed and the retained link backup remains the recovery authority throughout migration acceptance. Routine deployment now uses the guarded `just link` ownership refresh documented below.

## Prepare a current recovery point

Stop every other dotfile installer and do not edit managed HOME targets during the sequence. The operator commands share a nonblocking file lock, but that lock cannot contain a bare `chezmoi`, `rcup`, editor, or another process writing HOME.

Pull the private checkout first when it is installed, then pull the canonical public checkout. Run the isolated source and ownership gate:

```sh
just test-chezmoi-canary
just link-inventory
```

Resolve every non-clean inventory record. Create a fresh backup by following [Chezmoi cutover backup and rcm restore](chezmoi-cutover-backup.md), then retain its path and reviewed digest:

```sh
test -f "${backup_file:?set backup_file to the retained backup}"
test -n "${BACKUP_DIGEST:?set BACKUP_DIGEST to the reviewed backup digest}"
```

Do not reuse approval evidence from another HOME, repository path, source revision, backup, selected executable, or inspection run.

## Review and bind the exact apply

Run the approval plan in the local terminal:

```sh
just chezmoi-apply-plan "$backup_file" "$BACKUP_DIGEST"
```

The command verifies the current rcm links against the backup, runs the isolated public/private canary with the exact selected chezmoi and `lsrc` executables, then prints each source's status, diff, and verbose dry run. Diff and dry-run output can contain complete private values. Review it locally and never redirect, paste, or publish it.

The final line prints `approval_sha256`. This digest binds the HOME and repository paths, the backup path and reviewed digest, both source trees and ownership contracts, the canonical operator helper path and bytes, the canary, the recovery helper and rcm configuration, the resolved paths and bytes of the selected chezmoi, `lsrc`, and `rcup` executables, and the exact status, diff, and dry-run bytes. Copy only that digest:

```sh
APPLY_DIGEST='paste the final approval_sha256 here'
```

Any relevant source, executable, HOME, backup, or rendered-output change invalidates the approval before mutation.

## Apply with automatic rcm recovery

Keep the reviewed terminal output visible and run:

```sh
just chezmoi-apply "$backup_file" "$BACKUP_DIGEST" "$APPLY_DIGEST"
```

The command reruns the isolated canary, recomputes the approval without reprinting inspection output, verifies the backup again immediately before mutation, and applies the public source before the private source. Every subprocess invocation is time-bounded and runs in a dedicated process group. Captured output is consumed incrementally, and crossing the 16 MiB limit terminates that group immediately. A timeout, interruption, command failure, output overflow, or unexpectedly lingering descendant triggers bounded group-wide termination, escalation when needed, and leader reaping before recovery or the next phase. Every chezmoi invocation is config-bound, noninteractive, external-refresh-disabled, and limited to file entries. The mutating command uses `--force` only after the exact rcm link baseline, reviewed rendered output, source state, and recovery artifact have been revalidated, so no interactive prompt can weaken the approval boundary. It requires empty status, diff, and dry-run output after the first apply, applies both sources a second time, then requires the same empty state again.

If either source apply, either settled-state check, or the second apply fails or is interrupted, the command first stops its complete subprocess group, then invokes the digest-bound complete rcm restore. The first `SIGHUP`, `SIGINT`, or `SIGTERM` starts that cleanup after mutation begins; signals received while recovery is already running are recorded without interrupting the restore, then reported with their conventional signal exit status after recovery completes. Once the final settled state passes, the command blocks handled signals while atomically committing success. The one-shot operator retains its committed handlers until process exit, so a later handled signal is recorded without turning that completed cutover into an ambiguous failure. Other exits restore all prior handlers while those signals are blocked. A successful automatic restore still returns failure so the cutover cannot look complete.

The operator hashes the approved source trees and executable paths and bytes into a separate execution contract. Apply verifies that contract around preflight and immediately before every later chezmoi invocation. Drift before the first mutation aborts cleanly; drift after mutation starts invokes the complete rcm restore.

The sequence is not an operating-system transaction across HOME. The shared lock serializes these recipes only, and there is still a narrow race with unrelated writers after the final backup verification. Keep other installers and edits stopped until apply or recovery finishes.

## Recover after an unhandled interruption

`SIGKILL`, power loss, kernel failure, or a second failure inside automatic recovery can stop the process before it restores rcm. Do not rerun apply or delete the backup. Restore from the canonical public checkout:

```sh
just chezmoi-recover "$backup_file" "$BACKUP_DIGEST"
just link-inventory
just ci
```

The recovery recipe delegates to the same tested rcm restore used automatically. It accepts a mixed partial state, restores every backed-up target through rcm, and verifies the complete raw link set. If it fails, keep the artifact unchanged, stop all HOME writers, resolve the reported collision or rcm error, and rerun the same command.

The dedicated chezmoi cache, state databases, and lock file can remain. A later plan reads that state and produces a new approval from the restored HOME.

## Preserve a working state after success

After a successful first apply, the migrated targets are regular chezmoi-managed files while deferred targets remain rcm links. Keep rcm and the backup. `just link` and `just setup` now preserve that ownership split: the operator runs isolated parity checks, refreshes only manifest-deferred public rcm links, invokes the optional private dedicated-owner aggregate, and applies both chezmoi sources without force. It applies twice and requires empty status, diff, and dry-run state after each pass.

A regular file or foreign link at a retained rcm target fails before `rcup`. A changed or pre-existing chezmoi target fails through `--error-on-conflict` instead of being overwritten. A failure after an earlier owner succeeds does not automatically restore the full rcm graph because that would undo the successful cutover. Resolve the conflict or tool failure and rerun `just link`; use the retained backup and `just chezmoi-recover` only when intentionally rolling the complete migration back.

Run the nonmutating checks:

```sh
just chezmoi-status
just chezmoi-diff
just link
just ci
```

Status and diff must remain empty for both sources before and after the routine refresh. Perform the separately reviewed shell, dedicated-installer, fresh-machine, and supported-profile acceptance checks before retiring rcm or deleting the backup.

To end the trial or roll back this operator checkpoint, restore rcm before reverting repository code:

```sh
just chezmoi-recover "$backup_file" "$BACKUP_DIGEST"
just link-inventory
just ci
```

Only after all expected links are restored should the earlier repository revision be checked out. A code revert alone cannot restore HOME targets already converted to regular files.
