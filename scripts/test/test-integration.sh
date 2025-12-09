#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo ">>> Running INTEGRATION tests in Arch container"
echo "============================================================"

docker run --rm \
  -v "$(pwd):/src" \
  -v "pkgmgr_nix_cache:/root/.cache/nix" \
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
        -s tests/integration \
        -t /src \
        -p "$TEST_PATTERN";
  '
