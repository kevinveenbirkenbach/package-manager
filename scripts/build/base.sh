#!/usr/bin/env bash
set -euo pipefail

# The distribution bases this repository builds on. They are published by
# https://github.com/kevinveenbirkenbach/base-images, one multi-platform image
# per distribution, and carry the build dependencies the package build needs.
#
# Env overrides exist for testing an unpublished base; the registry namespace
# follows the images repository, not this one.

: "${BASE_IMAGES_REGISTRY:=ghcr.io}"
: "${BASE_IMAGES_OWNER:=kevinveenbirkenbach}"
: "${BASE_IMAGES_TAG:=latest}"

resolve_base_image() {
  local PKGMGR_DISTRO="$1"
  case "$PKGMGR_DISTRO" in
    arch|manjaro|debian|ubuntu|fedora|centos)
      echo "${BASE_IMAGES_REGISTRY}/${BASE_IMAGES_OWNER}/base-${PKGMGR_DISTRO}:${BASE_IMAGES_TAG}"
      ;;
    *) echo "ERROR: Unknown distro '$PKGMGR_DISTRO'" >&2; exit 1 ;;
  esac
}

# Platforms each distribution's base offers; see base-images/scripts/build/distros.sh.
resolve_platforms() {
  local PKGMGR_DISTRO="$1"
  case "$PKGMGR_DISTRO" in
    arch|manjaro|debian|ubuntu|fedora|centos) echo "linux/amd64,linux/arm64" ;;
    *) echo "ERROR: Unknown distro '$PKGMGR_DISTRO'" >&2; exit 1 ;;
  esac
}
