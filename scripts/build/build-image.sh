#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/resolve-base-image.sh"

base_image="$(resolve_base_image "$distro")"

echo ">>> Building test image for distro '$distro' (BASE_IMAGE=$base_image)..."

docker build \
  --build-arg BASE_IMAGE="$base_image" \
  -t "package-manager-test-$distro" \
  .
