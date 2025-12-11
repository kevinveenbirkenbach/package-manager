#!/usr/bin/env bash
set -euo pipefail

echo "[debian/package] Building Debian package..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

BUILD_ROOT="/tmp/package-manager-debian-build"
rm -rf "${BUILD_ROOT}"
mkdir -p "${BUILD_ROOT}"

echo "[debian/package] Syncing project sources to ${BUILD_ROOT}..."
rsync -a \
  --exclude 'packaging/debian' \
  "${PROJECT_ROOT}/" "${BUILD_ROOT}/"

echo "[debian/package] Overlaying debian/ metadata from packaging/debian..."
mkdir -p "${BUILD_ROOT}/debian"
cp -a "${PROJECT_ROOT}/packaging/debian/." "${BUILD_ROOT}/debian/"

cd "${BUILD_ROOT}"

echo "[debian/package] Running dpkg-buildpackage..."
dpkg-buildpackage -us -uc -b

echo "[debian/package] Installing generated DEB package..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ./../package-manager_*.deb
rm -rf /var/lib/apt/lists/*

echo "[debian/package] Done."
