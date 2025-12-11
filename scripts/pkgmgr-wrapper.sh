#!/usr/bin/env bash
set -euo pipefail

# Ensure NIX_CONFIG has our defaults if not already set
if [[ -z "${NIX_CONFIG:-}" ]]; then
  export NIX_CONFIG="experimental-features = nix-command flakes"
fi

FLAKE_DIR="/usr/lib/package-manager"

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
# If nix is still missing, try to run init-nix.sh once
# ---------------------------------------------------------------------------
if ! command -v nix >/dev/null 2>&1; then
  if [[ -x "${FLAKE_DIR}/init-nix.sh" ]]; then
    "${FLAKE_DIR}/init-nix.sh" || true
  fi
fi

# ---------------------------------------------------------------------------
# Primary path: use Nix flake if available
# ---------------------------------------------------------------------------
if command -v nix >/dev/null 2>&1; then
  exec nix run "${FLAKE_DIR}#pkgmgr" -- "$@"
fi

echo "[pkgmgr-wrapper] ERROR: 'nix' binary not found on PATH after init."
echo "[pkgmgr-wrapper] Nix is required to run pkgmgr (no Python fallback)."
exit 1
