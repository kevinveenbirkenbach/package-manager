#!/usr/bin/env bash
set -euo pipefail

echo "[docker] Starting package-manager container"

# ---------------------------------------------------------------------------
# Log distribution info
# ---------------------------------------------------------------------------
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  echo "[docker] Detected distro: ${ID:-unknown} (like: ${ID_LIKE:-})"
fi

# Always use /src (mounted from host) as working directory
echo "[docker] Using /src as working directory"
cd /src

# ---------------------------------------------------------------------------
# DEV mode: rebuild package-manager from the mounted /src tree
# ---------------------------------------------------------------------------
if [[ "${REINSTALL_PKGMGR:-0}" == "1" ]]; then
  echo "[docker] DEV mode enabled (REINSTALL_PKGMGR=1)"
  echo "[docker] Rebuilding package-manager from /src via scripts/installation/package.sh..."
  bash scripts/installation/package.sh || exit 1
fi

# ---------------------------------------------------------------------------
# Hand off to pkgmgr or arbitrary command
# ---------------------------------------------------------------------------
if [[ $# -eq 0 ]]; then
  echo "[docker] No arguments provided. Showing pkgmgr help..."
  exec pkgmgr --help
else
  echo "[docker] Executing command: $*"
  exec "$@"
fi
