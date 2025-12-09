#!/usr/bin/env bash
set -euo pipefail

resolve_base_image() {
  local distro="$1"

  case "$distro" in
    arch)   echo "$BASE_IMAGE_ARCH" ;;
    debian) echo "$BASE_IMAGE_DEBIAN" ;;
    ubuntu) echo "$BASE_IMAGE_UBUNTU" ;;
    fedora) echo "$BASE_IMAGE_FEDORA" ;;
    centos) echo "$BASE_IMAGE_CENTOS" ;;
    *)
      echo "ERROR: Unknown distro '$distro'" >&2
      exit 1
      ;;
  esac
}
