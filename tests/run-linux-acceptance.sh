#!/usr/bin/env bash
set -euo pipefail

# Run the fresh-machine acceptance harness inside a Linux container.
# The container image provides just, chezmoi, rcm, python3, and zsh.
# Source trees are injected at runtime via git archive, never baked
# into the image layer cache.

script_dir="$(cd "$(dirname "$0")" && pwd)"
public_dir="$(cd "$script_dir/.." && pwd)"
image_name="dotfiles-setup-acceptance"
private_dir="${1:-}"

if ! command -v docker >/dev/null 2>&1; then
    echo "docker is not available" >&2
    exit 1
fi

staging="$(mktemp -d)"
cleanup() {
    rm -rf "$staging"
}
trap cleanup EXIT

docker build \
    --file "$script_dir/setup-acceptance.Dockerfile" \
    --tag "$image_name" \
    --quiet \
    "$script_dir" >/dev/null

git -C "$public_dir" archive --format=tar --output="$staging/public.tar" HEAD

run_container() {
    local label="$1"
    shift

    docker run --rm \
        --mount "type=tmpfs,destination=/home/acceptance" \
        --volume "$staging/public.tar:/tmp/public.tar:ro" \
        "$@" \
        --env "GIT_CONFIG_GLOBAL=/dev/null" \
        --env "GIT_CONFIG_NOSYSTEM=1" \
        --env "HOME=/home/acceptance" \
        --env "LC_ALL=C.UTF-8" \
        "$image_name" \
        bash -euo pipefail -c '
            mkdir -p /srv/public
            tar -xf /tmp/public.tar -C /srv/public
            cd /srv/public
            git init --quiet
            git config user.name "Linux Acceptance"
            git config user.email "acceptance@example.invalid"
            git add --all
            git -c commit.gpgsign=false commit --quiet -m fixture

            acceptance_args=("--public-source" "/srv/public")

            if [ -f /tmp/private.tar ]; then
                mkdir -p /srv/private
                tar -xf /tmp/private.tar -C /srv/private
                cd /srv/private
                git init --quiet
                git config user.name "Linux Acceptance"
                git config user.email "acceptance@example.invalid"
                git add --all
                git -c commit.gpgsign=false commit --quiet -m fixture
                acceptance_args+=("--private-source" "/srv/private")
            fi

            cd /srv/public
            PYTHONDONTWRITEBYTECODE=1 python3 tests/setup_acceptance.py "${acceptance_args[@]}"
        '
    echo "==> $label complete"
}

echo "--- Linux acceptance: public-only ---"
run_container "linux/public-only"

if [ -n "$private_dir" ]; then
    if [ ! -d "$private_dir/.git" ]; then
        echo "private source is not a Git repository: $private_dir" >&2
        exit 1
    fi
    git -C "$private_dir" archive --format=tar --output="$staging/private.tar" HEAD
    echo "--- Linux acceptance: with-companion ---"
    run_container "linux/with-companion" \
        --volume "$staging/private.tar:/tmp/private.tar:ro"
fi

echo "Linux acceptance passed"
