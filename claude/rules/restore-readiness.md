# Restore Readiness

Before any destructive operation on production state, confirm a recent **restorable** backup exists. Authorization to act is not the same thing as readiness to roll back.

## Rules

- Before proposing or executing a destructive action — reset, wipe, recreate, drop, mass-delete, force-overwrite, schema rewrite, container reset, factory-reset — first answer: **if this goes wrong in the next minute, what command brings it back?** If the answer isn't concrete, stop and create a backup first
- A backup is only "real" if it contains the data that would be lost. Routine/scheduled backups are not automatically sufficient — verify the relevant tables/files/keys are actually inside the most recent archive before treating it as a rollback path
- Never conflate "the user authorized X" with "X is safe to do." The user is authorizing the *intent*, not vouching for backup state — that's your job to verify
- When you ask the user to do destructive UI work themselves, surface the rollback path in the same message ("we have backup Y from $TIME; if anything goes wrong, restore via Z")
- After taking a manual quiesced/pre-destructive backup, **inspect its contents** before proceeding — `tar tzf <archive> | grep <expected-file>` for tarballs, `pg_restore --list` for postgres dumps, etc. The session that triggered this rule shipped backups for two days that "succeeded" but silently captured nothing because of a single-character filename mismatch

## When backup creation is the next action

- Take it before any other step in the destructive flow — even before stopping services or starting migrations
- If the existing scheduled backup retention pool would evict your pre-destructive snapshot before validation completes, write the snapshot to a separate path/prefix that the pruner doesn't touch
- Verify the backup includes both config and durable state (DBs, user-generated data) — config-only backups are not rollback-capable for stateful services

## When you can't verify rollback

If you can't produce a concrete restore command for the data at risk, the destructive action is not yet safe to propose. Stop and either:

1. Build the restore path first (write the command, verify it works on a non-production instance), or
2. Tell the user the rollback path is uncertain and let them decide whether to proceed without one

## Anti-patterns

- Asking the user to perform destructive UI work without first confirming a backup with the relevant data exists
- Proposing "let me reset X" without a sentence naming the rollback artifact and how to use it
- Trusting Watchtower / nightly cron / built-in retention as a sufficient backup without checking what's inside the most recent archive
- Treating a backup script's `exit 0` as proof of capture — the script may have silently skipped the file you actually needed (filename drift, permission errors, conditional guards)
- Reading the backup contents only after a failure — the time to verify is *before* the destructive action, when there's still something to lose
- Documenting the rollback path only in commit messages — operators in the middle of a recovery don't read git log
