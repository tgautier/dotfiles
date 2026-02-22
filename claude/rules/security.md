# Security

## Secrets in code

- Never commit credentials, tokens, API keys, or secrets to any repository
- The **only** exception is `dotfiles-private` — that repo exists specifically for plaintext secrets and is private
- Before staging files, scan for patterns that look like secrets: `export.*TOKEN=`, `export.*KEY=`, `export.*SECRET=`, `password`, `ghp_`, `sk-`, `AKIA`
- If a secret is found outside `dotfiles-private`, stop and warn the user — do not commit

## Environment variables

- Never echo, log, or print environment variables that may contain secrets
- Never pass secrets as command-line arguments (visible in `ps` output) — use environment variables or stdin
- Never include secrets in URLs, query strings, or commit messages

## Sensitive files

- Never commit `.env`, `.env.*`, `credentials.json`, `*.pem`, `*.key`, or similar files
- If a `.gitignore` is missing entries for sensitive files, suggest adding them before committing
- Never remove secret-related entries from `.gitignore`

## Repo visibility

- Before creating a GitHub repository, confirm visibility (public/private) with the user
- Never change a private repo to public without explicit user confirmation
