#!/usr/bin/env bash
set -euo pipefail

IMAGE="pkgmgr-${PKGMGR_DISTRO}"

echo
echo "------------------------------------------------------------"
echo ">>> Testing VENV: ${IMAGE}"
echo "------------------------------------------------------------"

echo "[test-env-virtual] Inspect image metadata:"
docker image inspect "${IMAGE}" | sed -n '1,40p'
echo

# ------------------------------------------------------------
# Run VENV-based pkgmgr test inside container
# ------------------------------------------------------------
if OUTPUT=$(docker run --rm \
    -e REINSTALL_PKGMGR=1 \
    -v "$(pwd):/opt/src/pkgmgr" \
    -w /opt/src/pkgmgr \
    -e NIX_CONFIG="${NIX_CONFIG}" \
    "${IMAGE}" \
    bash -lc '
        set -euo pipefail

        echo "[test-env-virtual] Installing pkgmgr (distro package)..."
        make install

        echo "[test-env-virtual] Setting up Python venv..."
        make setup-venv

        echo "[test-env-virtual] Activating venv..."
        . "$HOME/.venvs/pkgmgr/bin/activate"

        echo "[test-env-virtual] Using pkgmgr from:"
        command -v pkgmgr
        pkgmgr --help
    ' 2>&1); then

    echo "$OUTPUT"
    echo
    echo "[test-env-virtual] SUCCESS: venv-based pkgmgr works in ${IMAGE}"

else
    echo "$OUTPUT"
    echo
    echo "[test-env-virtual] ERROR: venv-based pkgmgr failed in ${IMAGE}"
    exit 1
fi
