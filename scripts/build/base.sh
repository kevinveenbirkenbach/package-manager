#!/usr/bin/env bash
set -euo pipefail

: "${BASE_IMAGE_ARCH:=archlinux:latest}"
: "${BASE_IMAGE_DEBIAN:=debian:stable-slim}"
: "${BASE_IMAGE_UBUNTU:=ubuntu:latest}"
: "${BASE_IMAGE_FEDORA:=fedora:latest}"
: "${BASE_IMAGE_CENTOS:=quay.io/centos/centos:stream9}"

resolve_base_image() {
  local distro="$1"
  case "$distro" in
    arch)   echo "$BASE_IMAGE_ARCH" ;;
    debian) echo "$BASE_IMAGE_DEBIAN" ;;
    ubuntu) echo "$BASE_IMAGE_UBUNTU" ;;
    fedora) echo "$BASE_IMAGE_FEDORA" ;;
    centos) echo "$BASE_IMAGE_CENTOS" ;;
    *) echo "ERROR: Unknown distro '$distro'" >&2; exit 1 ;;
  esac
}
