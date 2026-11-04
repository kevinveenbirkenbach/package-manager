#!/usr/bin/env bash
set -euo pipefail

# Publish one image per distro, each covering every platform its base offers.
#
# Required env:
#   OWNER      (e.g. GITHUB_REPOSITORY_OWNER)
#   VERSION    (e.g. 1.2.3)
#   ALIASES    moving tags besides VERSION, space separated, may be empty (e.g. "latest 1 1.2 stable")
#
# Optional env:
#   REGISTRY   (default: ghcr.io)
#   DISTROS    (default: "arch debian ubuntu fedora centos")

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# shellcheck source=./scripts/build/base.sh
source "${SCRIPT_DIR}/base.sh"

REGISTRY="${REGISTRY:-ghcr.io}"
DISTROS="${DISTROS:-arch debian ubuntu fedora centos}"

: "${OWNER:?Environment variable OWNER must be set (e.g. github.repository_owner)}"
: "${VERSION:?Environment variable VERSION must be set (e.g. 1.2.3)}"
: "${ALIASES?Environment variable ALIASES must be set, empty for none (e.g. \"latest 1 1.2 stable\")}"

echo "[publish] REGISTRY=${REGISTRY}"
echo "[publish] OWNER=${OWNER}"
echo "[publish] VERSION=${VERSION}"
echo "[publish] ALIASES=${ALIASES}"
echo "[publish] DISTROS=${DISTROS}"

for d in ${DISTROS}; do
  echo
  echo "============================================================"
  echo "[publish] PKGMGR_DISTRO=${d}"
  echo "============================================================"

  IFS=',' read -ra platforms <<< "$(resolve_platforms "${d}")"
  for p in "${platforms[@]}"; do
    PKGMGR_DISTRO="${d}" bash "${SCRIPT_DIR}/image.sh" \
      --publish \
      --registry "${REGISTRY}" \
      --owner "${OWNER}" \
      --version "${VERSION}" \
      --platform "${p}"
  done

  PKGMGR_DISTRO="${d}" bash "${SCRIPT_DIR}/image.sh" \
    --publish \
    --registry "${REGISTRY}" \
    --owner "${OWNER}" \
    --version "${VERSION}" \
    --aliases "${ALIASES}" \
    --merge
done

echo
echo "[publish] Done."
