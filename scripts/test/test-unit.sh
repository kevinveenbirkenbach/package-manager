#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo ">>> Running UNIT tests in Arch container"
echo "============================================================"

docker run --rm \
  -v "$(pwd):/src" \
  -v "pkgmgr_nix_cache_${distro}:/root/.cache/nix" \
  -v pkgmgr_nix_store_${distro}:/nix \
  --workdir /src \
  -e PKGMGR_DEV=1 \
  -e TEST_PATTERN="${TEST_PATTERN}" \
  --entrypoint bash \
  "package-manager-test-arch" \
  -c '
    set -e;
    git config --global --add safe.directory /src || true;
    nix develop .#default --no-write-lock-file -c \
      python -m unittest discover \
        -s tests/unit \
        -t /src \
        -p "$TEST_PATTERN";
  '
