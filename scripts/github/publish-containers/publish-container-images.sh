#!/usr/bin/env bash
set -euo pipefail

: "${OWNER:?OWNER must be set}"
: "${VERSION:?VERSION must be set}"
: "${PKGMGR_DISTRO:?PKGMGR_DISTRO must be set}"
: "${PLATFORM:?PLATFORM must be set}"

bash scripts/build/image.sh \
  --publish \
  --registry ghcr.io \
  --owner "${OWNER}" \
  --version "${VERSION}" \
  --platform "${PLATFORM}"
