#!/usr/bin/env bash
set -euo pipefail

echo "[fedora/dependencies] Installing Fedora build dependencies..."

dnf -y update
dnf -y install \
  git \
  rsync \
  rpm-build \
  make \
  gcc \
  bash \
  curl \
  ca-certificates \
  python3 \
  xz

dnf clean all

echo "[fedora/dependencies] Done."
