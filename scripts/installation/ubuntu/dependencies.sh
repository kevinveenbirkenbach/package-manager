#!/usr/bin/env bash
set -euo pipefail

echo "[ubuntu/dependencies] Installing Ubuntu build dependencies..."

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  build-essential \
  debhelper \
  dpkg-dev \
  git \
  tzdata \
  lsb-release \
  rsync \
  bash \
  curl \
  make \
  python3 \
  ca-certificates \
  xz-utils

rm -rf /var/lib/apt/lists/*

echo "[ubuntu/dependencies] Done."
