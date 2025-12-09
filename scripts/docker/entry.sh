#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[docker] Starting package-manager container"

# Distro-Info nur für Logging
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  echo "[docker] Detected distro: ${ID:-unknown} (like: ${ID_LIKE:-})"
fi

# Wir arbeiten immer aus /src (vom Host gemountet)
echo "[docker] Using /src as working directory"
cd /src

# ------------------------------------------------------------
# DEV-Mode: aus dem aktuellen /src heraus Paket bauen/installieren
# ------------------------------------------------------------
if [[ "${PKGMGR_DEV:-0}" == "1" ]]; then
  echo "[docker] DEV mode enabled (PKGMGR_DEV=1)"
  echo "[docker] Rebuilding package-manager from /src via scripts/installation/run-package.sh..."

  if [[ -x scripts/installation/run-package.sh ]]; then
    bash scripts/installation/run-package.sh
  else
    echo "[docker] ERROR: scripts/installation/run-package.sh not found or not executable"
    exit 1
  fi
fi

# ------------------------------------------------------------
# Hand-off zu pkgmgr / beliebigem Kommando
# ------------------------------------------------------------
if [[ $# -eq 0 ]]; then
  echo "[docker] No arguments provided. Showing pkgmgr help..."
  exec pkgmgr --help
else
  echo "[docker] Executing command: $*"
  exec "$@"
fi
