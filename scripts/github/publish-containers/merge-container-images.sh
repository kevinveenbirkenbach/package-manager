#!/usr/bin/env bash
set -euo pipefail

: "${OWNER:?OWNER must be set}"
: "${VERSION:?VERSION must be set}"
: "${IS_STABLE:?IS_STABLE must be set}"
: "${PKGMGR_DISTRO:?PKGMGR_DISTRO must be set}"

bash scripts/build/image.sh \
  --publish \
  --registry ghcr.io \
  --owner "${OWNER}" \
  --version "${VERSION}" \
  --stable "${IS_STABLE}" \
  --merge
