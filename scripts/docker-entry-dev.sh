#!/usr/bin/env bash
set -euo pipefail

echo "[entry] Using /src as working tree for package-manager..."
cd /src

# Optional: altes Paket entfernen
echo "[entry] Removing existing 'package-manager' Arch package (if installed)..."
pacman -Rns --noconfirm package-manager || true

# Build-Owner richtig setzen (falls /src vom Host kommt)
echo "[entry] Fixing ownership of /src for user 'builder'..."
chown -R builder:builder /src

echo "[entry] Rebuilding Arch package from /src as user 'builder'..."
su builder -c "cd /src && makepkg -s --noconfirm --clean"

echo "[entry] Installing freshly built package-manager-*.pkg.tar.*..."
pacman -U --noconfirm /src/package-manager-*.pkg.tar.*

echo "[entry] Handing off to pkgmgr with args: $*"
exec pkgmgr "$@"
