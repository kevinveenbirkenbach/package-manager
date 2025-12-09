#!/usr/bin/env bash
set -euo pipefail

echo "[arch/package] Building Arch package (makepkg --nodeps)..."

if id aur_builder >/dev/null 2>&1; then
  echo "[arch/package] Using 'aur_builder' user for makepkg..."
  chown -R aur_builder:aur_builder "$(pwd)"
  su aur_builder -c "cd '$(pwd)' && rm -f package-manager-*.pkg.tar.* && makepkg --noconfirm --clean --nodeps"
else
  echo "[arch/package] WARNING: user 'aur_builder' not found, running makepkg as current user..."
  rm -f package-manager-*.pkg.tar.*
  makepkg --noconfirm --clean --nodeps
fi

echo "[arch/package] Installing generated Arch package..."
pacman -U --noconfirm package-manager-*.pkg.tar.*

echo "[arch/package] Done."
