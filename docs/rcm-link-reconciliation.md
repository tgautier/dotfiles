# Rcm link reconciliation

The chezmoi backup and rollback rehearsal needs a trustworthy view of the links that rcm owns today. A broken-link-only scan is insufficient: a source can still exist after rcm excludes it, and a removed top-level source directory can leave nested links behind after it disappears from current source discovery.

## Read-only inventory

Run the inventory from the public checkout:

```sh
just link-inventory
```

The command does not create, replace, or remove HOME entries. It compares exact `lsrc` target/source mappings from the configured canonical checkouts with live symlinks under every current or historical rcm top-level HOME root. This distinction keeps linked-worktree development from falsely reporting every installed public link as changed. `docs/rcm-link-owners.tsv` adds the dedicated installer contracts that intentionally sit outside ordinary rcm ownership. Wildcard contracts expand only from children currently tracked by Git, so a removed installer source cannot silently retain ownership.

Each row has one disposition:

- `rcm`: the live link exactly matches the source reported by `lsrc`.
- `dedicated`: the live link exactly matches a declared dedicated installer mapping.
- `obsolete`: the link points into a configured dotfiles checkout but neither current owner declares it.
- `unclassified`: the path collides with a declared target, points somewhere unexpected, or belongs to no declared owner.

The separate status reports whether a link is `linked`, `broken`, `missing`, `changed`, or a non-symlink `collision`. Machine-readable consumers can run `rcm-links inventory --format json`; schema version 1 preserves the same records without relying on path delimiters. The output contains local absolute paths and is operational evidence, not content to commit or paste into a public issue.

## Working-state boundary

This phase is inventory-only. Pulling the change and running `just ci` or `just link-inventory` leaves installed dotfiles untouched. Continue using `just link` for active deployment, and do not run chezmoi against the real HOME.

Rollback is a repository revert: restore the previous revision and rerun `just ci`. No HOME rollback is required because this checkpoint has no mutating command. The later cleanup checkpoint must re-read every symlink immediately before unlinking it, preserve dedicated and unclassified entries, and verify the resulting inventory before the target set becomes backup input for the chezmoi cutover.
