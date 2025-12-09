#!/usr/bin/env bash
set -euo pipefail

echo "[debian/package] Building Debian package..."

dpkg-buildpackage -us -uc -b

echo "[debian/package] Installing generated DEB package..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ./../package-manager_*.deb
rm -rf /var/lib/apt/lists/*

echo "[debian/package] Done."
