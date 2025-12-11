#!/usr/bin/env bash
set -euo pipefail

echo "[arch/package] Building Arch package (makepkg --nodeps)..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PKG_DIR="${PROJECT_ROOT}/packaging/arch"

if [[ ! -f "${PKG_DIR}/PKGBUILD" ]]; then
  echo "[arch/package] ERROR: PKGBUILD not found in ${PKG_DIR}"
  exit 1
fi

cd "${PKG_DIR}"

if id aur_builder >/dev/null 2>&1; then
  echo "[arch/package] Using 'aur_builder' user for makepkg..."
  chown -R aur_builder:aur_builder "${PKG_DIR}"
  su aur_builder -c "cd '${PKG_DIR}' && rm -f package-manager-*.pkg.tar.* && makepkg --noconfirm --clean --nodeps"
else
  echo "[arch/package] WARNING: user 'aur_builder' not found, running makepkg as current user..."
  rm -f package-manager-*.pkg.tar.*
  makepkg --noconfirm --clean --nodeps
fi

echo "[arch/package] Installing generated Arch package..."
pacman -U --noconfirm package-manager-*.pkg.tar.*

echo "[arch/package] Done."
