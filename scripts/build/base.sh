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

package_set_cmd() {
  local PKGMGR_DISTRO="$1"
  case "$PKGMGR_DISTRO" in
    arch|manjaro) echo 'pacman -Q' ;;
    debian|ubuntu) echo 'dpkg-query -W' ;;
    fedora|centos) echo 'rpm -qa | sort' ;;
    *) echo "ERROR: Unknown distro '$PKGMGR_DISTRO'" >&2; exit 1 ;;
  esac
}

version_prefixes() {
  local -a parts
  IFS=. read -ra parts <<< "$1"
  local acc="${parts[0]}" i
  echo "${acc}"
  for ((i = 1; i < ${#parts[@]}; i++)); do
    acc+=".${parts[i]}"
    echo "${acc}"
  done
}
