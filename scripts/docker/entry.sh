#!/usr/bin/env bash
set -euo pipefail

echo "[docker-pkgmgr] Starting package-manager container"

# ---------------------------------------------------------------------------
# Log distribution info
# ---------------------------------------------------------------------------
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  echo "[docker-pkgmgr] Detected distro: ${ID:-unknown} (like: ${ID_LIKE:-})"
fi

# Always use /opt/src/pkgmgr (mounted from host) as working directory
echo "[docker-pkgmgr] Using /opt/src/pkgmgr as working directory"
cd /opt/src/pkgmgr

# ---------------------------------------------------------------------------
# DEV mode: rebuild package-manager from the mounted /opt/src/pkgmgr tree
# ---------------------------------------------------------------------------
if [[ "${REINSTALL_PKGMGR:-0}" == "1" ]]; then
  echo "[docker-pkgmgr] DEV mode enabled (REINSTALL_PKGMGR=1)"
  echo "[docker-pkgmgr] Rebuilding package-manager from /opt/src/pkgmgr via scripts/installation/package.sh..."
  bash scripts/installation/package.sh || exit 1
fi

# ---------------------------------------------------------------------------
# Hand off to pkgmgr or arbitrary command
# ---------------------------------------------------------------------------
if [[ $# -eq 0 ]]; then
  echo "[docker-pkgmgr] No arguments provided. Showing pkgmgr help..."
  exec pkgmgr --help
else
  echo "[docker-pkgmgr] Executing command: $*"
  exec "$@"
fi
