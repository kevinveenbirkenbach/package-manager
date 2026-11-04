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
PUBLISH=0            # if 1 -> push <version>, <version>.<unix-ts> and the --aliases, plus arch aliases
REGISTRY=""          # e.g. ghcr.io
OWNER=""             # e.g. github org/user
REPO_PREFIX="pkgmgr" # image base name (pkgmgr)
VERSION=""           # X.Y.Z (required for --publish)
ALIASES=""           # moving tags besides <version>, e.g. "latest 2 2.4 stable"
ALIASES_SET=0        # 1 once --aliases was given, also when empty
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
  --publish             Publish <version>, <version>.<unix-ts> and every --aliases tag, plus arch
                        aliases
  --registry <reg>      Registry (e.g. ghcr.io)
  --owner <owner>       Registry namespace (e.g. \${GITHUB_REPOSITORY_OWNER})
  --repo-prefix <name>  Image base name (default: pkgmgr)
  --version <X.Y.Z>     Version for --publish
  --aliases "<tags>"    Moving tags besides <version>, space separated, may be empty
                        (e.g. "latest 2 2.4 stable")
  --platform <os/arch>  Build and push only this platform; with --publish as <version>-<arch>,
                        skipped when its package set equals the published <version>
  --merge               Join the <version>-<arch> tags of all platforms under the publish tags;
                        when <version> already joins exactly these images, only the aliases
                        that do not are moved and no <version>.<unix-ts> is added

Notes:
- --publish implies --push and requires --registry, --owner, and --version.
- --publish without --platform requires --aliases.
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
    --aliases)
      [[ $# -ge 2 ]] || { echo "ERROR: --aliases requires a value, empty for none"; exit 2; }
      ALIASES="$2"
      ALIASES_SET=1
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
  [[ -n "${PLATFORM}" || "${ALIASES_SET}" == "1" ]] \
    || { echo "ERROR: --publish without --platform requires --aliases"; exit 2; }
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
STAMP="$(date -u +%s)"

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
  echo "stamp     = ${STAMP}"
  echo "aliases   = ${ALIASES}"
fi
echo "------------------------------------------------------------"

# Common build args
build_args=(--build-arg "BASE_IMAGE=${BASE_IMAGE}")

if [[ "${NO_CACHE}" == "1" ]]; then
  build_args+=(--no-cache)
fi

publish_bases() {
  echo "${DISTRO_TAG_BASE}"
  if [[ "${PKGMGR_DISTRO}" == "${DEFAULT_DISTRO}" ]]; then
    echo "${REGISTRY}/${OWNER}/${REPO_PREFIX}"
  fi
}

moving_tags() {
  local base alias
  local -a aliases
  read -ra aliases <<< "${ALIASES}"
  while read -r base; do
    echo "${base}:${VERSION}"
    for alias in "${aliases[@]}"; do
      echo "${base}:${alias}"
    done
  done < <(publish_bases)
}

stamp_tags() {
  local base
  while read -r base; do
    echo "${base}:${VERSION}.${STAMP}"
  done < <(publish_bases)
}

raw_index() {
  docker buildx imagetools inspect --raw "$1" 2>/dev/null || true
}

digest_of() {
  docker buildx imagetools inspect --format '{{json .Manifest.Digest}}' "$1"
}

if [[ "${MERGE}" == "1" ]]; then
  sources=()
  IFS=',' read -ra platforms <<< "$(resolve_platforms "$PKGMGR_DISTRO")"
  for p in "${platforms[@]}"; do
    sources+=("${DISTRO_TAG_BASE}:${VERSION}-${p#*/}")
  done

  mapfile -t moving < <(moving_tags)
  planned="$(docker buildx imagetools create --dry-run -t "${DISTRO_TAG_BASE}:${VERSION}" "${sources[@]}")"
  tags=()
  if [[ "$(raw_index "${DISTRO_TAG_BASE}:${VERSION}")" == "${planned}" ]]; then
    for t in "${moving[@]}"; do
      if [[ "$(raw_index "${t}")" != "${planned}" ]]; then
        tags+=("${t}")
      fi
    done
  else
    mapfile -t stamps < <(stamp_tags)
    tags=("${moving[@]}" "${stamps[@]}")
  fi

  if ((${#tags[@]} == 0)); then
    echo "[build] ${PKGMGR_DISTRO} ${VERSION}: every tag already joins these platform images, nothing to push."
    exit 0
  fi

  create_args=()
  for t in "${tags[@]}"; do
    create_args+=(-t "$t")
  done

  echo "[build] Running: docker buildx imagetools create ${create_args[*]} ${sources[*]}"
  docker buildx imagetools create "${create_args[@]}" "${sources[@]}"

  version_digest="$(digest_of "${DISTRO_TAG_BASE}:${VERSION}")"
  for t in "${moving[@]}"; do
    if [[ "$(digest_of "${t}")" != "${version_digest}" ]]; then
      echo "[build] ❌ ${PKGMGR_DISTRO}: :${VERSION} and ${t} point at different images." >&2
      echo "[build]    Whoever pinned ${t##*:} stopped receiving what ${VERSION} gets." >&2
      exit 1
    fi
  done
  echo "[build] ✅ ${PKGMGR_DISTRO}: every tag of ${VERSION} == ${version_digest}"
elif [[ "${PUSH}" == "1" ]]; then
  if [[ "${PUBLISH}" == "1" && -n "${PLATFORM}" ]]; then
    probe="${REPO_PREFIX}-${PKGMGR_DISTRO}:probe"
    docker buildx build --load --platform "${PLATFORM}" -t "${probe}" "${build_args[@]}" .

    package_set="$(package_set_cmd "${PKGMGR_DISTRO}")"
    built_set="$(docker run --rm --platform "${PLATFORM}" --entrypoint bash "${probe}" -lc "${package_set}" | sha256sum)"
    published_set="$(docker run --rm --pull always --platform "${PLATFORM}" --entrypoint bash "${DISTRO_TAG_BASE}:${VERSION}" -lc "${package_set}" 2>/dev/null | sha256sum || true)"
    if [[ "${built_set}" == "${published_set}" ]]; then
      echo "[build] ${PKGMGR_DISTRO} ${PLATFORM} unchanged since the published ${VERSION}, nothing to push."
      exit 0
    fi
  fi

  bx_args=(docker buildx build --push)

  if [[ "${PUBLISH}" == "1" && -n "${PLATFORM}" ]]; then
    bx_args+=(-t "${DISTRO_TAG_BASE}:${VERSION}-${PLATFORM#*/}")
  elif [[ "${PUBLISH}" == "1" ]]; then
    while IFS= read -r t; do
      bx_args+=(-t "$t")
    done < <(moving_tags)
    while IFS= read -r t; do
      bx_args+=(-t "$t")
    done < <(stamp_tags)
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
