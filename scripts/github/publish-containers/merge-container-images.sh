#!/usr/bin/env bash
set -euo pipefail

: "${OWNER:?OWNER must be set}"
: "${VERSION:?VERSION must be set}"
: "${ALIASES?ALIASES must be set, empty for none}"
: "${PKGMGR_DISTRO:?PKGMGR_DISTRO must be set}"

bash scripts/build/image.sh \
  --publish \
  --registry ghcr.io \
  --owner "${OWNER}" \
  --version "${VERSION}" \
  --aliases "${ALIASES}" \
  --merge
