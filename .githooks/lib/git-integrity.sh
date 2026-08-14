#!/usr/bin/env bash
# Shared identity, signature, and exact-tip attestation checks for Git hooks.

readonly GIT_INTEGRITY_ALLOWED_IDENTITIES=(
  "Thomas Gautier <thomas@gautier.gg>"
)

# Commits at and before this migration boundary predate local signature
# enforcement. A new remote branch audits every descendant after this exact
# public main tip instead of pretending the legacy history was signed.
readonly GIT_INTEGRITY_SIGNATURE_BASELINE="cdb18f25d965c6baf43e587f9cdc38a49c83fa33"

git_integrity_resolve_mise() {
  local candidate found
  found=$(command -v mise 2>/dev/null || true)
  if [[ -n "$found" ]]; then
    printf '%s\n' "$found"
    return 0
  fi
  if [[ -n "${HOME:-}" ]]; then
    for candidate in "$HOME/.local/bin/mise" "$HOME/.local/share/mise/bin/mise"; do
      if [[ -x "$candidate" ]]; then
        printf '%s\n' "$candidate"
        return 0
      fi
    done
  fi
  printf '%s\n' "git-integrity: mise not found; add it to PATH or install it under ~/.local/bin" >&2
  return 1
}

git_integrity_normalize_identity() {
  local variable=$1 identity
  if ! identity=$(git var "$variable" 2>&1); then
    printf 'git-integrity: Git could not resolve %s: %s\n' "$variable" "$identity" >&2
    return 1
  fi
  printf '%s\n' "$identity" | sed -E 's/[[:space:]][0-9]+[[:space:]][+-][0-9]{4}$//'
}

git_integrity_check_identity() {
  local variable identity expected accepted
  for variable in GIT_AUTHOR_IDENT GIT_COMMITTER_IDENT; do
    identity=$(git_integrity_normalize_identity "$variable") || return 1
    accepted=0
    for expected in "${GIT_INTEGRITY_ALLOWED_IDENTITIES[@]}"; do
      if [[ "$identity" == "$expected" ]]; then
        accepted=1
        break
      fi
    done
    if [[ "$accepted" -ne 1 ]]; then
      printf "pre-commit: %s is '%s'; allowed identities are:\n" "$variable" "$identity" >&2
      printf '  %s\n' "${GIT_INTEGRITY_ALLOWED_IDENTITIES[@]}" >&2
      printf '%s\n' "pre-commit: set the intended Git identity before retrying" >&2
      return 1
    fi
  done
}

git_integrity_is_zero_sha() {
  [[ "$1" =~ ^0+$ ]]
}

git_integrity_has_signature_header() {
  local sha=$1 headers
  if ! headers=$(git cat-file -p "$sha" 2>&1); then
    printf 'pre-push: could not read commit %s: %s\n' "$sha" "$headers" >&2
    return 1
  fi
  printf '%s\n' "$headers" | awk '
    BEGIN { found = 0 }
    /^gpgsig(-sha256)? / { found = 1 }
    /^$/ { exit }
    END { exit(found ? 0 : 1) }
  '
}

git_integrity_check_push_signatures() {
  local local_sha=$1 remote_sha=$2 range commits sha shallow

  git_integrity_is_zero_sha "$local_sha" && return 0
  if ! git cat-file -e "$local_sha^{commit}" 2>/dev/null; then
    printf 'pre-push: local ref %s is not a readable commit\n' "$local_sha" >&2
    return 1
  fi
  if ! shallow=$(git rev-parse --is-shallow-repository 2>&1); then
    printf 'pre-push: could not inspect repository history: %s\n' "$shallow" >&2
    return 1
  fi
  if [[ "$shallow" == true ]]; then
    printf '%s\n' "pre-push: repository history is shallow; fetch complete history before pushing" >&2
    return 1
  fi
  if [[ "$shallow" != false ]]; then
    printf 'pre-push: unexpected shallow-repository result: %s\n' "$shallow" >&2
    return 1
  fi

  if git_integrity_is_zero_sha "$remote_sha"; then
    if ! git cat-file -e "$GIT_INTEGRITY_SIGNATURE_BASELINE^{commit}" 2>/dev/null; then
      printf 'pre-push: signature baseline %s is unavailable; fetch complete main history\n' "$GIT_INTEGRITY_SIGNATURE_BASELINE" >&2
      return 1
    fi
    if ! git merge-base --is-ancestor "$GIT_INTEGRITY_SIGNATURE_BASELINE" "$local_sha"; then
      printf 'pre-push: branch does not descend from signature baseline %s\n' "$GIT_INTEGRITY_SIGNATURE_BASELINE" >&2
      return 1
    fi
    range="$GIT_INTEGRITY_SIGNATURE_BASELINE..$local_sha"
  else
    if ! git cat-file -e "$remote_sha^{commit}" 2>/dev/null; then
      printf 'pre-push: remote tip %s is unavailable locally; fetch before pushing\n' "$remote_sha" >&2
      return 1
    fi
    range="$remote_sha..$local_sha"
  fi

  if ! commits=$(git rev-list "$range" 2>&1); then
    printf 'pre-push: could not enumerate pushed ancestry %s: %s\n' "$range" "$commits" >&2
    return 1
  fi
  while IFS= read -r sha; do
    [[ -n "$sha" ]] || continue
    if ! git_integrity_has_signature_header "$sha"; then
      printf 'pre-push: commit %s has no Git signature header; repair signing and recreate the commit before pushing\n' "$sha" >&2
      return 1
    fi
  done <<<"$commits"
}

git_integrity_check_local_ci_attestation() {
  local expected_sha=$1 git_dir marker attested line_count
  if ! git_dir=$(git rev-parse --absolute-git-dir 2>/dev/null); then
    printf '%s\n' "local-ci: could not resolve the attestation path" >&2
    return 1
  fi
  marker="$git_dir/local-ci-attestation"
  if [[ ! -f "$marker" || -L "$marker" ]]; then
    printf "local-ci: no trusted attestation for %s; run 'just ci-attest'\n" "$expected_sha" >&2
    return 1
  fi
  if ! line_count=$(wc -l <"$marker" 2>/dev/null) || ! attested=$(sed -n '1p' "$marker" 2>/dev/null); then
    printf 'local-ci: could not read attestation at %s\n' "$marker" >&2
    return 1
  fi
  if [[ "$line_count" -ne 1 ]] || ! [[ "$attested" =~ ^[0-9a-f]{40}$|^[0-9a-f]{64}$ ]]; then
    printf "local-ci: malformed attestation at %s; remove it and run 'just ci-attest'\n" "$marker" >&2
    return 1
  fi
  if [[ "$attested" != "$expected_sha" ]]; then
    printf "local-ci: attestation covers %s, not %s; run 'just ci-attest'\n" "${attested:0:12}" "${expected_sha:0:12}" >&2
    return 1
  fi
}
