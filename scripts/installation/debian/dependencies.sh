#!/usr/bin/env bash
set -euo pipefail

echo "[debian/dependencies] Installing Debian build dependencies..."

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  build-essential \
  debhelper \
  dpkg-dev \
  git \
  rsync \
  bash \
  curl \
  ca-certificates \
  python3 \
  xz-utils

rm -rf /var/lib/apt/lists/*

echo "[debian/dependencies] Done."
