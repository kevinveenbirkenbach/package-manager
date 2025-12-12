#!/usr/bin/env bash
set -euo pipefail

# Unified docker image builder for all distros.
#
# Supports:
#   --missing     Build only if image does not exist
#   --no-cache    Disable docker layer cache
#   --target      Dockerfile target (e.g. virgin|full)
#   --tag         Override image tag (default: pkgmgr-$distro[-$target])
#
# Requires:
#   - env var: distro (arch|debian|ubuntu|fedora|centos)
#   - base.sh in same dir
#
# Examples:
#   distro=arch   bash scripts/build/image.sh
#   distro=arch   bash scripts/build/image.sh --no-cache
#   distro=arch   bash scripts/build/image.sh --missing
#   distro=arch   bash scripts/build/image.sh --target virgin
#   distro=arch   bash scripts/build/image.sh --target virgin --missing
#   distro=arch   bash scripts/build/image.sh --tag myimg:arch

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/base.sh"

: "${distro:?Environment variable 'distro' must be set (arch|debian|ubuntu|fedora|centos)}"

NO_CACHE=0
MISSING_ONLY=0
TARGET=""
IMAGE_TAG="" # derive later unless --tag is provided

usage() {
  local default_tag="pkgmgr-${distro}"
  if [[ -n "${TARGET:-}" ]]; then
    default_tag="${default_tag}-${TARGET}"
  fi

  cat <<EOF
Usage: distro=<distro> $0 [--missing] [--no-cache] [--target <name>] [--tag <image>]

Options:
  --missing         Build only if the image does not already exist
  --no-cache        Build with --no-cache
  --target <name>   Build a specific Dockerfile target (e.g. virgin|full)
  --tag <image>     Override the output image tag (default: ${default_tag})
  -h, --help        Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-cache) NO_CACHE=1; shift ;;
    --missing)  MISSING_ONLY=1; shift ;;
    --target)
      TARGET="${2:-}"
      if [[ -z "${TARGET}" ]]; then
        echo "ERROR: --target requires a value (e.g. virgin|full)" >&2
        exit 2
      fi
      shift 2
      ;;
    --tag)
      IMAGE_TAG="${2:-}"
      if [[ -z "${IMAGE_TAG}" ]]; then
        echo "ERROR: --tag requires a value" >&2
        exit 2
      fi
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

# Auto-tag: if --tag not provided, derive from distro (+ target suffix)
if [[ -z "${IMAGE_TAG}" ]]; then
  IMAGE_TAG="pkgmgr-${distro}"
  if [[ -n "${TARGET}" ]]; then
    IMAGE_TAG="${IMAGE_TAG}-${TARGET}"
  fi
fi

BASE_IMAGE="$(resolve_base_image "$distro")"

if [[ "${MISSING_ONLY}" == "1" ]]; then
  if docker image inspect "${IMAGE_TAG}" >/dev/null 2>&1; then
    echo "[build] Image already exists: ${IMAGE_TAG} (skipping due to --missing)"
    exit 0
  fi
fi

echo
echo "------------------------------------------------------------"
echo "[build] Building image: ${IMAGE_TAG}"
echo "distro     = ${distro}"
echo "BASE_IMAGE = ${BASE_IMAGE}"
if [[ -n "${TARGET}" ]]; then echo "target    = ${TARGET}"; fi
if [[ "${NO_CACHE}" == "1" ]]; then echo "cache     = disabled"; fi
echo "------------------------------------------------------------"

build_args=(--build-arg "BASE_IMAGE=${BASE_IMAGE}")

if [[ "${NO_CACHE}" == "1" ]]; then
  build_args+=(--no-cache)
fi

if [[ -n "${TARGET}" ]]; then
  build_args+=(--target "${TARGET}")
fi

build_args+=(-t "${IMAGE_TAG}" .)

docker build "${build_args[@]}"
