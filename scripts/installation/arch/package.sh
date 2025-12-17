#!/usr/bin/env bash
set -euo pipefail

echo "[arch/package] Building Arch package (makepkg --nodeps) in an isolated build dir..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# We must not build inside /opt/src/pkgmgr (mounted repo). Build in /tmp to avoid permission issues.
BUILD_ROOT="/tmp/package-manager-arch-build"
PKG_SRC_DIR="${PROJECT_ROOT}/packaging/arch"
PKG_BUILD_DIR="${BUILD_ROOT}/packaging/arch"

if [[ ! -f "${PKG_SRC_DIR}/PKGBUILD" ]]; then
  echo "[arch/package] ERROR: PKGBUILD not found in ${PKG_SRC_DIR}"
  exit 1
fi

echo "[arch/package] Preparing build directory: ${BUILD_ROOT}"
rm -rf "${BUILD_ROOT}"
mkdir -p "${BUILD_ROOT}"

echo "[arch/package] Syncing project sources to ${BUILD_ROOT}..."
# Keep it simple: copy everything; adjust excludes if needed later.
rsync -a --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '.venvs' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  "${PROJECT_ROOT}/" "${BUILD_ROOT}/"

if [[ ! -d "${PKG_BUILD_DIR}" ]]; then
  echo "[arch/package] ERROR: Build PKG dir missing: ${PKG_BUILD_DIR}"
  exit 1
fi

# ------------------------------------------------------------
# Unprivileged user for Arch package build (makepkg)
# ------------------------------------------------------------
if ! id aur_builder >/dev/null 2>&1; then
  echo "[arch/package] ERROR: user 'aur_builder' not found. Run scripts/installation/arch/aur-builder-setup.sh first."
  exit 1
fi

echo "[arch/package] Using 'aur_builder' user for makepkg..."
chown -R aur_builder:aur_builder "${BUILD_ROOT}"

echo "[arch/package] Running makepkg in: ${PKG_BUILD_DIR}"
su aur_builder -c "cd '${PKG_BUILD_DIR}' && rm -f package-manager-*.pkg.tar.* && makepkg --noconfirm --clean --nodeps"

echo "[arch/package] Installing generated Arch package..."
pkg_path="$(find "${PKG_BUILD_DIR}" -maxdepth 1 -type f -name 'package-manager-*.pkg.tar.*' | head -n1)"
if [[ -z "${pkg_path}" ]]; then
  echo "[arch/package] ERROR: Built package not found in ${PKG_BUILD_DIR}"
  exit 1
fi

pacman -U --noconfirm "${pkg_path}"

echo "[arch/package] Cleanup build directory..."
rm -rf "${BUILD_ROOT}"

echo "[arch/package] Done."
