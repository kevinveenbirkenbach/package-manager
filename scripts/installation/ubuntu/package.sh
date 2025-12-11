#!/usr/bin/env bash
set -euo pipefail

echo "[ubuntu/package] Building Ubuntu (Debian-style) package..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

BUILD_ROOT="/tmp/package-manager-ubuntu-build"
rm -rf "${BUILD_ROOT}"
mkdir -p "${BUILD_ROOT}"

echo "[ubuntu/package] Syncing project sources to ${BUILD_ROOT}..."
rsync -a \
  --exclude 'packaging/debian' \
  "${PROJECT_ROOT}/" "${BUILD_ROOT}/"

echo "[ubuntu/package] Overlaying debian/ metadata from packaging/debian..."
mkdir -p "${BUILD_ROOT}/debian"
cp -a "${PROJECT_ROOT}/packaging/debian/." "${BUILD_ROOT}/debian/"

cd "${BUILD_ROOT}"

echo "[ubuntu/package] Running dpkg-buildpackage..."
dpkg-buildpackage -us -uc -b

echo "[ubuntu/package] Installing generated DEB package..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ./../package-manager_*.deb
rm -rf /var/lib/apt/lists/*

echo "[ubuntu/package] Done."
