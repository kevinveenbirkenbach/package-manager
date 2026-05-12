#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "[installation/install] ERROR: Installation requires root. Re-run with sudo." >&2
  exit 1
fi

echo "[installation] Running as root (EUID=0)."
echo "[installation] Install Package Dependencies..."
bash  scripts/installation/dependencies.sh
echo "[installation] Install Distribution Package..."
bash scripts/installation/package.sh
echo "[installation] Root/system setup complete."
exit 0
