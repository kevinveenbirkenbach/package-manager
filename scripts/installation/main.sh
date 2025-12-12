#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "[installation/install] Warning: Installation is just possible via root."
  exit 0
fi

echo "[installation] Running as root (EUID=0)."
echo "[installation] Install Package Dependencies..."
bash  scripts/installation/dependencies.sh
echo "[installation] Install Distribution Package..."
bash scripts/installation/package.sh
echo "[installation] Root/system setup complete."
exit 0
