---
name: just
description: |
  Justfile authoring skill for the just command runner.
  Covers: recipe design, dependency management, variables, shebang recipes, error handling,
  output control, modules, built-in functions, settings, and common patterns.
  Use when: writing or reviewing Justfiles, adding project commands, or structuring
  multi-step workflows.
version: 1.0.0
date: 2026-02-22
user-invocable: true
---

# Justfile Authoring

Guidance for writing maintainable, correct Justfiles. `just` is a command runner — not a build system. It saves and runs project-specific commands without Make's complexity.

Based on the [Just Programmer's Manual](https://just.systems/man/en/) and patterns from production codebases.

---

## 1. Design Philosophy

A Justfile is the project's command palette. Every developer interaction with the project should go through `just`.

- **One canonical way** — for any operation (build, test, lint, deploy), there should be exactly one recipe. Never leave developers guessing which command to run
- **Composites at the top** — high-level recipes (`dev`, `build`, `test`, `check`) sit at the top of the file, composed from lower-level recipes
- **Self-documenting** — `just` (no arguments) shows all recipes with descriptions. Every recipe should have a comment explaining what it does
- **Idempotent where possible** — running a recipe twice should produce the same result. Guard against re-running setup steps unnecessarily
- **Fail fast** — recipes should fail on the first error, not silently continue

---

## 2. File Structure

Organize the Justfile into sections with comment headers:

```just
# Default: show help
default:
    @just --list

# ─────────────────────────────────────────────
# Top-Level Composites
# ─────────────────────────────────────────────

# Run all code quality checks
check: lint typecheck test

# ─────────────────────────────────────────────
# Frontend (app-*)
# ─────────────────────────────────────────────

# Build frontend for production
app-build:
    yarn build

# ─────────────────────────────────────────────
# Backend (api-*)
# ─────────────────────────────────────────────

# Build the API
api-build:
    cd api && cargo build
```

**Ordering:**
1. `default` recipe (always first)
2. Top-level composites (`dev`, `build`, `test`, `check`, `lint`)
3. Domain-grouped recipes (frontend, backend, database, docker, CI)
4. Setup and cleanup recipes (last)

---

## 3. Recipe Naming

Use `{domain}-{action}` with hyphens, all lowercase:

| Pattern | Examples |
|---------|----------|
| `{domain}-{verb}` | `app-build`, `api-test`, `db-migrate` |
| `{domain}-{verb}-{modifier}` | `app-test-force`, `api-build-release` |
| `{noun}` (composites) | `build`, `test`, `lint`, `check`, `dev` |

**Conventions:**
- Group related recipes by prefix: `app-*`, `api-*`, `db-*`, `docker-*`, `e2e-*`
- Private recipes start with `_`: `_helper` (hidden from `--list`)
- Force/reset variants append `-force` or `-reset`
- Composites use bare nouns (no prefix)

---

## 4. Comments and Documentation

```just
# This comment appears in `just --list` output
recipe-name:
    command

// This doc-comment also appears in `just --list` (just 1.14.0+)
// and supports multi-line descriptions
recipe-name:
    command

# This is an implementation note (won't appear if a doc-comment exists)
// User-facing description
recipe-name:
    command
```

- Every recipe should have a `#` or `//` comment describing what it does
- Use `#` comments between recipe groups as section headers
- Use inline `# NOTE:` comments to document non-obvious dependency ordering or sequencing constraints

---

## 5. Dependencies

Dependencies run before the recipe body:

```just
# Dependencies run left-to-right, then the body executes
build: lint typecheck
    yarn build

# Chain recipes without a body (pure composite)
check: lint typecheck test
```

### Dependency ordering

Dependencies execute **sequentially, left-to-right** in the dependency list. This is guaranteed by `just` — use this for ordering constraints:

```just
# gen-client depends on openapi.json from gen-openapi
# NOTE: gen-client depends on openapi.json from gen-openapi — must run sequentially
gen: gen-openapi gen-client gen-config-schema
```

### Calling recipes from the body

Use `just {recipe}` inside a recipe body when you need conditional or mid-body invocation:

```just
reset: kill
    just docker-reset
    yarn install
    just docker-up
    just db-migrate
```

**When to use dependencies vs body calls:**
- **Dependencies** — unconditional prerequisites that must run first
- **Body calls** — when ordering interleaves with other commands, or when the call is conditional

### Parameterized dependencies

Pass arguments to dependencies:

```just
build profile="dev": (cargo-build profile)

cargo-build profile:
    cd api && cargo build --profile {{profile}}
```

---

## 6. Variables

### Simple assignment

```just
project := "my-app"
port := "3001"
```

### Computed variables (backtick capture)

```just
# Captures stdout of the command at evaluation time
git_sha := `git rev-parse --short HEAD`

# With fallback for when the command might fail
db_url := `cargo run -q --bin config -- database.url 2>/dev/null || echo "postgresql://localhost/mydb"`
```

**Gotcha:** Backtick variables are evaluated when the Justfile loads, not when a recipe runs. If the command is slow (e.g., `cargo run`), it adds startup latency to every `just` invocation — even `just --list`. Guard expensive commands with a fallback (`|| echo "default"`) and keep them fast.

### Environment variables

```just
# Export all variables to recipes as env vars
set export

# Or export individual variables
export DATABASE_URL := "postgresql://localhost/mydb"

# Read from environment with fallback
port := env("PORT", "3001")
```

### Variable interpolation

Always use `{{variable}}` in recipe bodies:

```just
greet name="world":
    echo "Hello, {{name}}!"
```

To produce a literal `{{`, escape with `{{ "{{" }}`.

---

## 7. Recipe Parameters

```just
# Required parameter
deploy target:
    ./deploy.sh {{target}}

# Optional with default
serve port="3000":
    node server.js --port {{port}}

# Variadic (collects remaining args)
test *args:
    cargo test {{args}}

# Variadic with a separator
docker-run +args:
    docker run {{args}}
```

- `*args` — zero or more arguments (optional)
- `+args` — one or more arguments (required)
- Parameters with defaults are optional; without defaults are required

---

## 8. Shebang Recipes

For multi-line logic, use shebang recipes:

```just
db-install:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ "$(uname)" == "Darwin" ]]; then
        if ! brew --prefix libpq &>/dev/null; then
            echo "Error: libpq not found. Run: brew install libpq"
            exit 1
        fi
        export PKG_CONFIG_PATH="$(brew --prefix libpq)/lib/pkgconfig"
    fi
    cargo install diesel_cli --no-default-features --features postgres
```

**Rules:**
- Always start with `#!/usr/bin/env bash` (or another interpreter)
- Always `set -euo pipefail` for bash — fail on errors, undefined vars, and pipe failures
- The entire script runs as one temp file, so variables persist across lines
- Use shebang recipes when logic requires conditionals, loops, or error handling beyond what single commands provide

### Other interpreters

```just
# Python
analyze:
    #!/usr/bin/env python3
    import json
    data = json.load(open("config.json"))
    print(f"Found {len(data)} entries")

# Node.js
validate:
    #!/usr/bin/env node
    const fs = require('fs');
    console.log(JSON.parse(fs.readFileSync('package.json')).name);
```

---

## 9. Output Control

### Suppress recipe echo

By default, `just` prints each line before executing it. Suppress with `@`:

```just
# @ on the recipe — suppresses all line echoes
@default:
    just --list

# @ on individual lines
status:
    @echo "Checking status..."
    git status
    @echo "Done."
```

### Quiet mode

```just
set quiet  # Suppress all recipe line echoes globally
```

Or per-recipe:

```just
[quiet]
helper:
    echo "This line echo is suppressed, but the echo output still shows"
```

### Suppress errors

Prefix a line with `-` to continue on failure:

```just
kill:
    -pkill -f "my-app"
    -docker compose down
    @echo "Cleanup complete."
```

This is useful for cleanup recipes where some processes may not be running.

---

## 10. Conditional Expressions

```just
# if/else expression
greeting := if env("CI", "") == "true" { "CI build" } else { "Local build" }

# In recipe bodies
test:
    {{ if os() == "macos" { "echo macOS" } else { "echo Linux" } }}
```

### Conditional recipe execution

```just
# Run recipe only on macOS
[macos]
setup-mac:
    brew install libpq

# Run recipe only on Linux
[linux]
setup-linux:
    apt-get install -y libpq-dev
```

---

## 11. Settings

Configure Justfile behavior at the top of the file:

```just
# Use bash for all recipes (default is sh)
set shell := ["bash", "-euo", "pipefail", "-c"]

# Load .env file
set dotenv-load

# Export all variables as environment variables
set export

# Change working directory to the Justfile's location
set working-directory := justfile_directory()

# Allow duplicate recipe names (last one wins)
set allow-duplicate-recipes

# Windows: use PowerShell instead of cmd.exe
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]
```

**Recommended defaults for new projects:**

```just
set shell := ["bash", "-euo", "pipefail", "-c"]
```

This gives consistent bash behavior with strict error handling across all recipes (not just shebang recipes).

---

## 12. Built-in Functions

### Commonly used

| Function | Purpose | Example |
|----------|---------|---------|
| `os()` | Operating system | `if os() == "macos" { ... }` |
| `arch()` | CPU architecture | `arch()` → `"aarch64"` |
| `env(name, default)` | Environment variable | `env("CI", "false")` |
| `justfile_directory()` | Justfile's parent dir | Useful for `set working-directory` |
| `invocation_directory()` | Where `just` was called from | Path resolution |
| `uuid()` | Random UUID | Temp file naming |
| `sha256(str)` | SHA-256 hash | Cache keys |
| `datetime(fmt)` | Current date/time | Timestamps |
| `quote(str)` | Shell-safe quoting | Safe argument passing |

### Path functions

| Function | Purpose |
|----------|---------|
| `absolute_path(p)` | Resolve to absolute path |
| `join(a, b)` | Join path components |
| `parent_directory(p)` | Parent of path |
| `file_name(p)` | Last component |
| `file_stem(p)` | Name without extension |
| `file_extension(p)` | Extension only |
| `clean(p)` | Normalize path separators |

### String functions

| Function | Purpose |
|----------|---------|
| `uppercase(s)` | Convert to uppercase |
| `lowercase(s)` | Convert to lowercase |
| `replace(s, from, to)` | String replacement |
| `trim(s)` | Remove surrounding whitespace |
| `contains(s, pattern)` | Check if string contains substring |

---

## 13. Modules and Imports

Split large Justfiles into modules (just 1.19.0+):

```just
# Import recipes from another file
import "ci.just"

# Module with namespace
mod docker "docker.just"
# Access as: just docker::up
```

**When to modularize:**
- Justfile exceeds ~300 lines
- Distinct teams own different recipe groups
- CI recipes differ significantly from dev recipes

**When to keep a single file:**
- Most projects — a single well-organized Justfile is simpler to navigate and maintain
- Under ~300 lines — the overhead of multiple files isn't worth it

---

## 14. Common Patterns

### Default help

```just
default:
    @just --list
```

Every Justfile should have this. Running `just` with no arguments shows available recipes.

### Composite recipes

```just
# Top-level composites delegate to domain recipes
build: app-build api-build
lint: app-lint api-lint
test: app-test api-test e2e-test
check: app-lint app-typecheck api-check
```

**Avoid redundant composition** — if `api-check` already runs `api-lint`, don't also include `api-lint` in `check`:

```just
# WRONG — api-lint runs twice (once directly, once inside api-check)
check: lint api-check

# CORRECT — call app-lint directly, api-check handles its own linting
check: app-lint app-typecheck api-check
```

### Prerequisite guards

```just
# Check that a tool is installed before using it
db-check-diesel:
    @which diesel > /dev/null 2>&1 || (echo "Error: diesel_cli not found. Run: just db-install-diesel" && exit 1)

db-migrate: db-check-diesel
    diesel migration run
```

### Docker integration

```just
# Use --wait to block until healthchecks pass
docker-up:
    docker compose up -d --wait

# Profile-based separation (dev tools vs core services)
docker-up-dev:
    docker compose --profile dev up -d --wait

docker-up-db:
    docker compose up -d --wait

docker-down:
    docker compose --profile dev down

docker-reset:
    docker compose --profile dev down -v
```

Use `--wait` instead of manual polling loops when containers have healthchecks defined. Keep a manual wait recipe as a fallback for mid-recipe restarts.

### Setup recipes

```just
setup: install-tools
    yarn install
    just docker-up
    just db-migrate
    just gen
    @echo "Setup complete! Run 'just dev' to start."
```

- Install prerequisites first (tools, dependencies)
- Start infrastructure (Docker, databases)
- Run migrations and code generation
- Print next steps

### Force/reset variants

```just
# Normal: assumes DB is clean
app-test:
    R8N_ENV=test yarn test

# Force: resets DB first, then runs the normal recipe
app-test-force target="test": (db-reset target)
    just app-test
```

Name the force variant `{recipe}-force`. Use dependencies to compose: reset, then run.

### Environment-parameterized recipes

```just
# Single env variable — reads from shell, defaults to "dev"
default-env := env("R8N_ENV", "dev")

# Recipes accept positional env parameter, resolve URLs through config
# NOTE: `env` is reserved in just — use a different parameter name (e.g. `target`)
db-migrate target=default-env:
    cd api && R8N_ENV={{target}} diesel migration run --database-url "$(R8N_ENV={{target}} cargo run -q --bin config -- database.url)"

# Multi-env composites call sub-recipes with explicit positional args
db-sync-all: (db-migrate) (db-migrate "test")
```

Calling convention: `just db-migrate test` (positional), not `just db-migrate target=test` (`key=value` on the CLI sets variables, not parameters).

### CI simulation

```just
ci-local: lint typecheck test build
    @echo "Local CI passed!"

ci-full: ci-local e2e-test
    @echo "Full CI passed!"
```

Mirror your CI pipeline locally so developers catch failures before pushing.

---

## 15. Error Handling

### Strict mode via settings

```just
set shell := ["bash", "-euo", "pipefail", "-c"]
```

This ensures every non-shebang recipe fails on:
- Any command returning non-zero (`-e`)
- Undefined variables (`-u`)
- Pipe failures (`-o pipefail`)

### Ignoring expected failures

```just
kill:
    -pkill -f "my-app"       # May not be running
    -docker compose down      # May not be up
```

Use `-` only for cleanup/teardown where failure is expected and harmless.

### Error messages

```just
db-check:
    @which diesel > /dev/null 2>&1 || (echo "Error: diesel_cli not found. Run: just db-install-diesel" && exit 1)
```

When a guard fails, tell the user **what failed** and **how to fix it**.

---

## 16. Debugging

```just
# Parse the Justfile without running anything
just --list

# Show what would run without executing
just --dry-run recipe-name

# Evaluate a variable
just --evaluate variable-name

# Show all variables
just --evaluate

# Verbose execution (shows each command before running)
just --verbose recipe-name
```

---

## 17. Anti-patterns

### Raw commands when a recipe exists

```just
# WRONG — bypasses the recipe's profile flag and --wait
reset:
    docker compose down -v
    docker compose up -d

# CORRECT — reuse existing recipes
reset:
    just docker-reset
    just docker-up
```

Always call `just {recipe}` instead of duplicating the command. This ensures flags, profiles, and healthcheck waits stay consistent.

### Redundant dependencies

```just
# WRONG — dev depends on docker-up, so fresh runs it twice
fresh: docker-reset docker-up db-sync dev

# CORRECT — don't include docker-up if dev already depends on it,
# or remove dev if it just prints instructions
fresh: docker-reset docker-up db-sync
    @echo "Ready! Run 'just dev' to start."
```

Trace the dependency graph before adding recipes to a dependency list.

### Slow backtick variables

```just
# WRONG — runs cargo on every just invocation, even `just --list`
db-url := `cargo run --bin config -- database.url`

# BETTER — fast fallback prevents blocking when cargo isn't built
db-url := `cargo run -q --bin config -- database.url 2>/dev/null || echo "postgresql://localhost/mydb"`
```

### Missing error handling in shebang recipes

```just
# WRONG — no strict mode, failures silently continue
setup:
    #!/usr/bin/env bash
    rm -rf build
    mkdir build
    cd build && cmake ..

# CORRECT — fail fast
setup:
    #!/usr/bin/env bash
    set -euo pipefail
    rm -rf build
    mkdir build
    cd build && cmake ..
```

### Hardcoded paths and credentials

```just
# WRONG — hardcoded absolute path and credentials
deploy:
    scp -i /home/me/.ssh/key build/* user:pass@server:/app

# CORRECT — use variables and environment
deploy user host:
    scp build/* {{user}}@{{host}}:/app
```

Never put secrets, passwords, or API keys in the Justfile. Use environment variables or config files.

### Over-modularizing

Don't split into modules until the Justfile is genuinely hard to navigate (~300+ lines, distinct ownership boundaries). A single well-organized file with section headers is easier to search and understand.

---

## 18. Shell Compatibility

**zsh `!` corruption**: see global *shell* rule for full details. In jq filters, use `== ... | not` instead of `!=`.

### Cross-platform recipes

Use `os()` and platform attributes for platform-specific logic:

```just
[macos]
install-deps:
    brew install libpq

[linux]
install-deps:
    sudo apt-get install -y libpq-dev
```

---

## 19. Quick Reference

### Command line

| Command | Purpose |
|---------|---------|
| `just` | Show available recipes |
| `just recipe` | Run a recipe |
| `just recipe arg1 arg2` | Run with arguments |
| `just --list` | List recipes with descriptions |
| `just --dry-run recipe` | Show what would run |
| `just --evaluate` | Show all variables |
| `just --evaluate var` | Show one variable |
| `just --verbose recipe` | Run with command echo |
| `just --choose` | Interactive recipe picker |
| `just --fmt` | Format the Justfile |
| `just --check --fmt` | Check formatting without changing |

### Syntax cheat sheet

```just
# Variable assignment
name := "value"
computed := `shell command`
from_env := env("VAR", "default")

# Recipe with dependency
recipe: dep1 dep2
    command

# Recipe with parameters
recipe param1 param2="default":
    echo {{param1}} {{param2}}

# Shebang recipe
recipe:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "multi-line logic"

# Suppress echo
@recipe:
    echo "only output shows, not the command"

# Ignore errors
recipe:
    -command-that-may-fail

# Conditional
value := if condition { "yes" } else { "no" }

# Platform-specific
[macos]
recipe:
    mac-command

[linux]
recipe:
    linux-command
```
