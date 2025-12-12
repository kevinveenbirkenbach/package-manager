#!/usr/bin/env bash
set -euo pipefail

echo "[centos/dependencies] Installing CentOS build dependencies..."

dnf -y update
dnf -y install \
  git \
  rsync \
  rpm-build \
  make \
  gcc \
  bash \
  curl-minimal \
  ca-certificates \
  python3 \
  sudo \
  xz

dnf clean all

echo "[centos/dependencies] Done."
