#!/usr/bin/env bash
set -euo pipefail

IMAGE="package-manager-test-$distro"

echo
echo "------------------------------------------------------------"
echo ">>> Testing container: $IMAGE"
echo "------------------------------------------------------------"

echo "[test-container] Running: docker run --rm --entrypoint pkgmgr $IMAGE --help"
echo

# Run the command and capture the output
if OUTPUT=$(docker run --rm \
        -e PKGMGR_DEV=1 \
        -v pkgmgr_nix_store_${distro}:/nix \
        -v "$(pwd):/src" \
        -v "pkgmgr_nix_cache_${distro}:/root/.cache/nix" \
        "$IMAGE" 2>&1); then
    echo "$OUTPUT"
    echo
    echo "[test-container] SUCCESS: $IMAGE responded to 'pkgmgr --help'"

else
    echo "$OUTPUT"
    echo
    echo "[test-container] ERROR: $IMAGE failed to run 'pkgmgr --help'"
    exit 1
fi