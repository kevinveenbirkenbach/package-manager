#!/usr/bin/env bash
set -euo pipefail

echo "[ubuntu/package] Building Ubuntu (Debian-style) package..."

dpkg-buildpackage -us -uc -b

echo "[ubuntu/package] Installing generated DEB package..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ./../package-manager_*.deb
rm -rf /var/lib/apt/lists/*

echo "[ubuntu/package] Done."
