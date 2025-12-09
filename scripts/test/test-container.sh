#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo ">>> Running sanity test: verifying test containers start"
echo "============================================================"

for distro in $DISTROS; do
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
            -v "$(pwd):/src" \
            -v "pkgmgr_nix_cache:/root/.cache/nix" \
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
done

echo
echo "============================================================"
echo ">>> All containers passed the sanity check"
echo "============================================================"
