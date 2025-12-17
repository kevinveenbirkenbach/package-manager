#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo ">>> Running UNIT tests in ${PKGMGR_DISTRO} container"
echo "============================================================"

docker run --rm \
  -v "$(pwd):/opt/src/pkgmgr" \
  -v "pkgmgr_nix_cache_${PKGMGR_DISTRO}:/root/.cache/nix" \
  -v "pkgmgr_nix_store_${PKGMGR_DISTRO}:/nix" \
  --workdir /opt/src/pkgmgr \
  -e REINSTALL_PKGMGR=1 \
  -e TEST_PATTERN="${TEST_PATTERN}" \
  -e NIX_CONFIG="${NIX_CONFIG}" \
  "pkgmgr-${PKGMGR_DISTRO}" \
  bash -lc '
    set -e;
    git config --global --add safe.directory /opt/src/pkgmgr || true;
    nix develop .#default --no-write-lock-file -c \
      python3 -m unittest discover \
        -s tests/unit \
        -t /opt/src/pkgmgr \
        -p "$TEST_PATTERN";
  '
