#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/resolve-base-image.sh"

base_image="$(resolve_base_image "$distro")"

echo ">>> Building test image for distro '$distro' with NO CACHE (BASE_IMAGE=$base_image)..."

docker build \
  --no-cache \
  --build-arg BASE_IMAGE="$base_image" \
  -t "package-manager-test-$distro" \
  .
