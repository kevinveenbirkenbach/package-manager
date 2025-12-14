#!/usr/bin/env bash
set -euo pipefail

FLAKE_DIR="/usr/lib/package-manager"
NIX_LIB_DIR="${FLAKE_DIR}/nix/lib"
RETRY_LIB="${NIX_LIB_DIR}/retry_403.sh"

# ---------------------------------------------------------------------------
# Hard requirement: retry helper must exist (fail if missing)
# ---------------------------------------------------------------------------
if [[ ! -f "${RETRY_LIB}" ]]; then
  echo "[launcher] ERROR: Required retry helper not found: ${RETRY_LIB}" >&2
  exit 1
fi

# shellcheck source=/usr/lib/package-manager/nix/lib/retry_403.sh
source "${RETRY_LIB}"

# ---------------------------------------------------------------------------
# Try to ensure that "nix" is on PATH (common locations + container user)
# ---------------------------------------------------------------------------
if ! command -v nix >/dev/null 2>&1; then
  CANDIDATES=(
    "/nix/var/nix/profiles/default/bin/nix"
    "${HOME:-/root}/.nix-profile/bin/nix"
    "/home/nix/.nix-profile/bin/nix"
  )

  for candidate in "${CANDIDATES[@]}"; do
    if [[ -x "$candidate" ]]; then
      PATH="$(dirname "$candidate"):${PATH}"
      export PATH
      break
    fi
  done
fi

# ---------------------------------------------------------------------------
# If nix is still missing, try to run nix/init.sh once
# ---------------------------------------------------------------------------
if ! command -v nix >/dev/null 2>&1; then
  if [[ -x "${FLAKE_DIR}/nix/init.sh" ]]; then
    "${FLAKE_DIR}/nix/init.sh" || true
  fi
fi

# ---------------------------------------------------------------------------
# Primary path: use Nix flake if available (with GitHub 403 retry)
# ---------------------------------------------------------------------------
if command -v nix >/dev/null 2>&1; then
  exec run_with_github_403_retry nix run "${FLAKE_DIR}#pkgmgr" -- "$@"
fi

echo "[launcher] ERROR: 'nix' binary not found on PATH after init."
echo "[launcher] Nix is required to run pkgmgr (no Python fallback)."
exit 1
