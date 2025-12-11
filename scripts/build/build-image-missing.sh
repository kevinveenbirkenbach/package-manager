#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/resolve-base-image.sh"

IMAGE="package-manager-test-$distro"
BASE_IMAGE="$(resolve_base_image "$distro")"

if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "[build-missing] Image already exists: $IMAGE (skipping)"
    exit 0
fi

echo
echo "------------------------------------------------------------"
echo "[build-missing] Building missing image: $IMAGE"
echo "BASE_IMAGE = $BASE_IMAGE"
echo "------------------------------------------------------------"

docker build \
    --build-arg BASE_IMAGE="$BASE_IMAGE" \
    -t "$IMAGE" \
    .
