#!/usr/bin/env bash
set -euo pipefail

IMAGE="pkgmgr-$distro"

echo
echo "------------------------------------------------------------"
echo ">>> Testing VENV: $IMAGE"
echo "------------------------------------------------------------"
echo "[test-env-virtual] Inspect image metadata:"
docker image inspect "$IMAGE" | sed -n '1,40p'

echo "[test-env-virtual] Running: docker run --rm --entrypoint pkgmgr $IMAGE --help"
echo

# Run the command and capture the output
if OUTPUT=$(docker run --rm \
        -e REINSTALL_PKGMGR=1 \
        -v pkgmgr_nix_store_${distro}:/nix \
        -v "$(pwd):/src" \
        -v "pkgmgr_nix_cache_${distro}:/root/.cache/nix" \
        "$IMAGE" 2>&1); then
    echo "$OUTPUT"
    echo
    echo "[test-env-virtual] SUCCESS: $IMAGE responded to 'pkgmgr --help'"

else
    echo "$OUTPUT"
    echo
    echo "[test-env-virtual] ERROR: $IMAGE failed to run 'pkgmgr --help'"
    exit 1
fi