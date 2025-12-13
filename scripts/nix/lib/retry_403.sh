#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${PKGMGR_NIX_RETRY_403_SH:-}" ]]; then
  return 0
fi
PKGMGR_NIX_RETRY_403_SH=1

# Retry only when we see the GitHub API rate limit 403 error during nix flake evaluation.
# Retries 7 times with delays: 10, 30, 50, 80, 130, 210, 420 seconds.
run_with_github_403_retry() {
  local -a delays=(10 30 50 80 130 210 420)
  local attempt=0
  local max_retries="${#delays[@]}"

  while true; do
    local err tmp
    tmp="$(mktemp -t nix-err.XXXXXX)"
    err=0

    # Run the command; capture stderr for inspection while preserving stdout.
    if "$@" 2>"$tmp"; then
      rm -f "$tmp"
      return 0
    else
      err=$?
    fi

    # Only retry on the specific GitHub API rate limit 403 case.
    if grep -qE 'HTTP error 403' "$tmp" && grep -qiE 'API rate limit exceeded|api\.github\.com' "$tmp"; then
      if (( attempt >= max_retries )); then
        cat "$tmp" >&2
        rm -f "$tmp"
        return "$err"
      fi

      local sleep_s="${delays[$attempt]}"
      attempt=$((attempt + 1))

      echo "[nix-retry] GitHub API rate-limit (403). Retry ${attempt}/${max_retries} in ${sleep_s}s: $*" >&2
      cat "$tmp" >&2
      rm -f "$tmp"
      sleep "$sleep_s"
      continue
    fi

    # Not our retry case -> fail fast with original stderr.
    cat "$tmp" >&2
    rm -f "$tmp"
    return "$err"
  done
}
