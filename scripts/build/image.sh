#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# shellcheck source=./scripts/build/base.sh
source "${SCRIPT_DIR}/base.sh"

: "${PKGMGR_DISTRO:?Environment variable 'PKGMGR_DISTRO' must be set (arch|debian|ubuntu|fedora|centos)}"

NO_CACHE=0
MISSING_ONLY=0
IMAGE_TAG=""         # local image name or base tag (without registry)
PUSH=0               # if 1 -> use buildx and push (requires docker buildx)
PUBLISH=0            # if 1 -> push with semantic tags (latest/version/stable + arch aliases)
REGISTRY=""          # e.g. ghcr.io
OWNER=""             # e.g. github org/user
REPO_PREFIX="pkgmgr" # image base name (pkgmgr)
VERSION=""           # X.Y.Z (required for --publish)
IS_STABLE="false"    # "true" -> publish stable tags
PLATFORM=""          # e.g. linux/arm64 -> build and push only this platform
MERGE=0              # if 1 -> join the per-platform tags of --version under the publish tags
DEFAULT_DISTRO="arch"

usage() {
  local default_tag="pkgmgr-${PKGMGR_DISTRO}"

  cat <<EOF
Usage: PKGMGR_DISTRO=<distro> $0 [options]

Build options:
  --missing             Build only if the image does not already exist (local build only)
  --no-cache            Build with --no-cache
  --tag <image>         Override the output image tag (default: ${default_tag})

Publish options:
  --push                Push the built image (uses docker buildx build --push)
  --publish             Publish semantic tags (latest, <version>, optional stable) + arch aliases
  --registry <reg>      Registry (e.g. ghcr.io)
  --owner <owner>       Registry namespace (e.g. \${GITHUB_REPOSITORY_OWNER})
  --repo-prefix <name>  Image base name (default: pkgmgr)
  --version <X.Y.Z>     Version for --publish
  --stable <true|false> Whether to publish :stable tags (default: false)
  --platform <os/arch>  Build and push only this platform; with --publish as <version>-<arch>
  --merge               Join the <version>-<arch> tags of all platforms under the publish tags

Notes:
- --publish implies --push and requires --registry, --owner, and --version.
- --platform requires --push; --merge requires --publish and builds nothing.
- Local build (no --push) uses "docker build" and creates a local image like "pkgmgr-arch".
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-cache) NO_CACHE=1; shift ;;
    --missing)  MISSING_ONLY=1; shift ;;
    --tag)
      IMAGE_TAG="${2:-}"
      [[ -n "${IMAGE_TAG}" ]] || { echo "ERROR: --tag requires a value"; exit 2; }
      shift 2
      ;;
    --push) PUSH=1; shift ;;
    --publish) PUBLISH=1; PUSH=1; shift ;;
    --registry)
      REGISTRY="${2:-}"
      [[ -n "${REGISTRY}" ]] || { echo "ERROR: --registry requires a value"; exit 2; }
      shift 2
      ;;
    --owner)
      OWNER="${2:-}"
      [[ -n "${OWNER}" ]] || { echo "ERROR: --owner requires a value"; exit 2; }
      shift 2
      ;;
    --repo-prefix)
      REPO_PREFIX="${2:-}"
      [[ -n "${REPO_PREFIX}" ]] || { echo "ERROR: --repo-prefix requires a value"; exit 2; }
      shift 2
      ;;
    --version)
      VERSION="${2:-}"
      [[ -n "${VERSION}" ]] || { echo "ERROR: --version requires a value"; exit 2; }
      shift 2
      ;;
    --stable)
      IS_STABLE="${2:-}"
      [[ -n "${IS_STABLE}" ]] || { echo "ERROR: --stable requires a value (true|false)"; exit 2; }
      shift 2
      ;;
    --platform)
      PLATFORM="${2:-}"
      [[ -n "${PLATFORM}" ]] || { echo "ERROR: --platform requires a value"; exit 2; }
      shift 2
      ;;
    --merge) MERGE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

# Derive default local tag if not provided
if [[ -z "${IMAGE_TAG}" ]]; then
  IMAGE_TAG="${REPO_PREFIX}-${PKGMGR_DISTRO}"
fi

BASE_IMAGE="$(resolve_base_image "$PKGMGR_DISTRO")"

# Local-only "missing" shortcut
if [[ "${MISSING_ONLY}" == "1" ]]; then
  if [[ "${PUSH}" == "1" ]]; then
    echo "ERROR: --missing is only supported for local builds (without --push/--publish)" >&2
    exit 2
  fi
  if docker image inspect "${IMAGE_TAG}" >/dev/null 2>&1; then
    echo "[build] Image already exists: ${IMAGE_TAG} (skipping due to --missing)"
    exit 0
  fi
fi

# Validate publish parameters
if [[ "${PUBLISH}" == "1" ]]; then
  [[ -n "${REGISTRY}" ]] || { echo "ERROR: --publish requires --registry"; exit 2; }
  [[ -n "${OWNER}" ]]    || { echo "ERROR: --publish requires --owner"; exit 2; }
  [[ -n "${VERSION}" ]]  || { echo "ERROR: --publish requires --version"; exit 2; }
fi

if [[ -n "${PLATFORM}" ]]; then
  [[ "${PUSH}" == "1" ]] || { echo "ERROR: --platform requires --push or --publish"; exit 2; }
  [[ ",$(resolve_platforms "$PKGMGR_DISTRO")," == *",${PLATFORM},"* ]] \
    || { echo "ERROR: ${PKGMGR_DISTRO} offers no platform ${PLATFORM}"; exit 2; }
fi

if [[ "${MERGE}" == "1" ]]; then
  [[ "${PUBLISH}" == "1" ]] || { echo "ERROR: --merge requires --publish"; exit 2; }
  [[ -z "${PLATFORM}" ]]    || { echo "ERROR: --merge and --platform exclude each other"; exit 2; }
fi

DISTRO_TAG_BASE="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${PKGMGR_DISTRO}"

# Guard: --push without --publish requires fully-qualified --tag
if [[ "${PUSH}" == "1" && "${PUBLISH}" != "1" ]]; then
  if [[ "${IMAGE_TAG}" != */* ]]; then
    echo "ERROR: --push requires --tag with a fully-qualified name (e.g. ghcr.io/<owner>/<image>:tag), or use --publish" >&2
    exit 2
  fi
fi

echo
echo "------------------------------------------------------------"
echo "[build] Building image"
echo "distro     = ${PKGMGR_DISTRO}"
echo "BASE_IMAGE = ${BASE_IMAGE}"
echo "platforms = ${PLATFORM:-$(resolve_platforms "$PKGMGR_DISTRO")}"
if [[ "${NO_CACHE}" == "1" ]]; then echo "cache     = disabled"; fi
if [[ "${PUSH}" == "1" ]]; then echo "push      = enabled"; fi
if [[ "${PUBLISH}" == "1" ]]; then
  echo "publish   = enabled"
  echo "registry  = ${REGISTRY}"
  echo "owner     = ${OWNER}"
  echo "version   = ${VERSION}"
  echo "stable    = ${IS_STABLE}"
fi
echo "------------------------------------------------------------"

# Common build args
build_args=(--build-arg "BASE_IMAGE=${BASE_IMAGE}")

if [[ "${NO_CACHE}" == "1" ]]; then
  build_args+=(--no-cache)
fi

compute_publish_tags() {
  local distro_tag_base="${DISTRO_TAG_BASE}"
  local alias_tag_base=""

  if [[ "${PKGMGR_DISTRO}" == "${DEFAULT_DISTRO}" ]]; then
    alias_tag_base="${REGISTRY}/${OWNER}/${REPO_PREFIX}"
  fi

  local tags=()
  tags+=("${distro_tag_base}:latest")
  tags+=("${distro_tag_base}:${VERSION}")

  if [[ "${IS_STABLE}" == "true" ]]; then
    tags+=("${distro_tag_base}:stable")
  fi

  if [[ -n "${alias_tag_base}" ]]; then
    tags+=("${alias_tag_base}:latest")
    tags+=("${alias_tag_base}:${VERSION}")
    if [[ "${IS_STABLE}" == "true" ]]; then
      tags+=("${alias_tag_base}:stable")
    fi
  fi

  printf '%s\n' "${tags[@]}"
}

if [[ "${MERGE}" == "1" ]]; then
  merge_args=(docker buildx imagetools create)
  while IFS= read -r t; do
    merge_args+=(-t "$t")
  done < <(compute_publish_tags)

  IFS=',' read -ra platforms <<< "$(resolve_platforms "$PKGMGR_DISTRO")"
  for p in "${platforms[@]}"; do
    merge_args+=("${DISTRO_TAG_BASE}:${VERSION}-${p#*/}")
  done

  echo "[build] Running: ${merge_args[*]}"
  "${merge_args[@]}"
  docker buildx imagetools inspect "${DISTRO_TAG_BASE}:${VERSION}"
elif [[ "${PUSH}" == "1" ]]; then
  bx_args=(docker buildx build --push)

  if [[ "${PUBLISH}" == "1" && -n "${PLATFORM}" ]]; then
    bx_args+=(-t "${DISTRO_TAG_BASE}:${VERSION}-${PLATFORM#*/}")
  elif [[ "${PUBLISH}" == "1" ]]; then
    while IFS= read -r t; do
      bx_args+=(-t "$t")
    done < <(compute_publish_tags)
  else
    bx_args+=(-t "${IMAGE_TAG}")
  fi

  bx_args+=(--platform "${PLATFORM:-$(resolve_platforms "$PKGMGR_DISTRO")}")
  bx_args+=("${build_args[@]}")
  bx_args+=(.)

  echo "[build] Running: ${bx_args[*]}"
  "${bx_args[@]}"
else
  local_args=(docker build)
  local_args+=("${build_args[@]}")
  local_args+=(-t "${IMAGE_TAG}")
  local_args+=(.)

  echo "[build] Running: ${local_args[*]}"
  "${local_args[@]}"
fi
