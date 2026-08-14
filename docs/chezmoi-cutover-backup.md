# Chezmoi cutover backup and rcm restore

Create and verify this backup before the first real chezmoi apply. The backup records every public and effective private rcm target from the committed manifests.

## Prepare the exact live baseline

Pull the private repository first when it is installed. Pull the canonical public checkout next.

Run the migration guards from the canonical public checkout:

```sh
just test-chezmoi-canary
just link-inventory
```

Resolve each `obsolete`, `unclassified`, `missing`, `changed`, or `collision` record before continuing. The backup command also compares the complete `lsrc` map with both committed target manifests. It rejects a missing target, an unmanifested target, a changed source, a non-symlink target, or a non-canonical raw link.

Keep rcm installed through the rollback window. The restore command uses rcm's force-relink operation with hooks disabled and the exact source operands stored in the manifests.

## Create the private backup

Create a fresh destination for each attempt:

```sh
backup_dir=$(mktemp -d "${TMPDIR:-/tmp}/dotfiles-cutover.XXXXXX")
chmod 700 "$backup_dir"
backup_file="$backup_dir/rcm-links.json"
just link-cutover-backup "$backup_file"
BACKUP_DIGEST=$(jq -er '.approval_sha256 | select(type == "string" and test("^[0-9a-f]{64}$"))' "$backup_file")
just link-cutover-backup-verify "$backup_file"
```

The backup command creates one regular file with mode `0600`. It refuses an existing destination and publishes the completed file atomically. The artifact records rcm's exact link ownership state; repository content remains in the public and private source checkouts. The file contains local absolute paths. Keep it outside both repositories and public issue or pull-request text.

Review the target list and keep the printed SHA-256 digest with the file. The digest confirms the reviewed artifact during restore. It does not replace local review of the target list.

`just link-cutover-backup` and `just link-cutover-backup-verify` do not change HOME. Keep using `just link` while rcm owns deployment.

## Rehearse restore in isolation

Run `just test-rcm-links`. Its cutover fixtures replace backed-up links with rendered files inside a temporary HOME. They restore the exact public and private link set through `rcup`, then verify every raw target.

The fixtures also cover manifest drift, backup tampering, foreign symlinks, destination reuse, and a partial rcm failure. The partial-failure fixture keeps the backup unchanged and completes through the same command on retry.

## Restore rcm after a cutover failure

Keep the backup file and its reviewed digest available. Run the restore from the canonical public checkout:

```sh
test -f "${backup_file:?set backup_file to the retained backup}"
test -n "${BACKUP_DIGEST:?set BACKUP_DIGEST to the retained digest}"
just link-cutover-restore "$backup_file" "$BACKUP_DIGEST"
just link-inventory
```

Restore validates the backup schema, ownership, mode, digest, repository roots, current manifests, and complete rcm map before mutation. Its preflight refuses a foreign symlink, a special file, or a non-directory ancestor. It allows an absent target, an exact saved link, or a regular file or directory that the cutover must replace. The subsequent replacement uses rcm's standard force-relink operation; the preflight does not claim to lock HOME against concurrent changes, so stop other dotfile installers while restoring.

Rcm processes targets sequentially. If rcm stops after changing some targets, keep the backup and run the same restore command again. The command treats exact restored links as complete and verifies the full set after rcm exits successfully.

## Upgrade and rollback boundary

Pull this checkpoint and run `just ci` before creating a live backup. Do not run a real chezmoi apply as part of this checkpoint.

Before any live backup exists, restore the earlier repository revision and run `just ci` to roll back this code change. No HOME action is required.

After a future cutover changes HOME, run `just link-cutover-restore` before reverting repository code. Keep the backup until rcm ownership, dedicated private installers, shell startup, and the complete local gate pass.
