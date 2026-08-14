# Rcm link reconciliation

The chezmoi backup and rollback rehearsal needs a trustworthy view of the links that rcm owns today. A broken-link-only scan is insufficient: a source can still exist after rcm excludes it, and a removed top-level source directory can leave nested links behind after it disappears from current source discovery.

## Read-only inventory

Run the inventory from the public checkout:

```sh
just link-inventory
```

The command does not create, replace, or remove HOME entries. It compares exact `lsrc` target/source mappings from the configured canonical checkouts with live symlinks under every current or historical rcm top-level HOME root. The authoritative history is the complete ancestry of each canonical checkout's current `HEAD`; non-ancestor branches are outside inventory scope and must be reconciled separately if they were ever installed. As a conservative prerequisite, each repository as a whole must report that it is non-shallow, even when a shallow boundary belongs only to an unrelated ref; run `git fetch --unshallow` before inventory. This distinction keeps linked-worktree development from falsely reporting every installed public link as changed. `docs/rcm-link-owners.tsv` adds the dedicated installer contracts that intentionally sit outside ordinary rcm ownership. Exact contracts must name a source currently tracked by Git or inventory fails; wildcard contracts expand only from tracked children. A removed or misspelled installer source therefore cannot silently retain ownership. Nested targets behind a symlinked or non-directory HOME ancestor are collisions; the inventory never traverses that ancestor.

Each row has one disposition:

- `rcm`: the live link exactly matches the source reported by `lsrc`.
- `dedicated`: the live link exactly matches a declared dedicated installer mapping.
- `obsolete`: the link points into a configured dotfiles checkout but neither current owner declares it.
- `unclassified`: the path collides with a declared target, points somewhere unexpected, or belongs to no declared owner.

The separate status reports whether a link is `linked`, `broken`, `missing`, `changed`, or a non-symlink `collision`. Machine-readable consumers can run `rcm-links inventory --format json`; schema version 1 preserves the same records without relying on path delimiters. The output contains local absolute paths and is operational evidence, not content to commit or paste into a public issue.

## Approval-bound cleanup

Generate a cleanup plan in a private temporary directory. The plan contains only links currently classified as `obsolete`, plus their exact raw link targets and the configured HOME and repository roots:

```sh
set -eu
approval_dir=$(mktemp -d)
approval_file="$approval_dir/plan.json"
just link-cleanup-plan > "$approval_file"
chmod 600 "$approval_file"
jq '{approval_sha256, links}' "$approval_file"
```

Review every target and raw link target locally. Explicit approval means recording both the exact list and the displayed `approval_sha256`; the digest alone is not a substitute for reviewing the paths. Keep the plan private because it contains absolute local paths.

After that separate approval, set `APPROVED_DIGEST` to the approved value and apply the exact plan:

```sh
test -n "${approval_file:?keep approval_file from the reviewed plan step}"
test -n "${APPROVED_DIGEST:?set APPROVED_DIGEST to the separately approved digest}"
just link-cleanup "$approval_file" "$APPROVED_DIGEST"
just link-inventory
```

Cleanup rejects an unknown schema, duplicate or unsafe paths, a changed plan digest, different HOME or repository roots, a target that is no longer obsolete, a changed raw link target, a non-symlink target, and any symlinked or non-directory ancestor. It preflights the complete set and reloads the owner manifest, `lsrc`, tracked installer children, Git history, and live inventory immediately before each pending mutation. It then opens the parent chain with non-following directory descriptors and atomically moves the entry through the held descriptor into a fresh mode-700 quarantine directory. Only an entry whose inode metadata and raw target still match the approved symlink is deleted. A raced or unverifiable entry remains in the reported quarantine path. Cleanup does not prune HOME directories; its own empty quarantine directory is removed after a verified deletion. A concurrent failure after cleanup starts reports the completed count, and rerunning the same approved command treats verified absent targets as complete and resumes the remaining set.

Use the same reviewed plan and digest to restore every removed link while its parent directories remain unchanged:

```sh
test -n "${approval_file:?keep approval_file from the reviewed plan step}"
test -n "${APPROVED_DIGEST:?keep the separately approved digest}"
just link-restore "$approval_file" "$APPROVED_DIGEST"
just link-inventory
```

Restore refuses an absent path that acquired a current rcm or dedicated owner, any occupied or mismatched target, and any missing, symlinked, or non-directory ancestor. It reloads every ownership input immediately before each pending creation, then holds the same non-following parent descriptors while recreating the approved raw link target and verifies the resulting inventory. Rerunning the same approved command treats an existing link as complete only when the fresh inventory still classifies it as obsolete and its raw target exactly matches the plan. Remove the private temporary directory only after cleanup verification and the rollback window are complete.

## Working-state boundary

Pulling the change and running `just ci`, `just link-inventory`, or `just link-cleanup-plan` leaves installed dotfiles untouched. Only `just link-cleanup` and `just link-restore` mutate HOME, and both require the private plan plus its separately approved digest. Continue using `just link` for active deployment, and do not run chezmoi against the real HOME.

Before cleanup, rollback is a repository revert followed by `just ci`. After cleanup, use `just link-restore` with the retained approved plan before reverting repository code; a repository revert alone cannot recreate obsolete links that rcm no longer owns. Preserve the verified post-cleanup inventory as the target-set input for the chezmoi backup rehearsal.
