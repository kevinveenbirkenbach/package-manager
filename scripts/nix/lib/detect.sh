#!/usr/bin/env bash

if [[ -n "${PKGMGR_NIX_DETECT_SH:-}" ]]; then
  return 0
fi
PKGMGR_NIX_DETECT_SH=1

# Detect whether we are inside a container (Docker/Podman/etc.)
is_container() {
  [[ -f /.dockerenv || -f /run/.containerenv ]] && return 0
  grep -qiE 'docker|container|podman|lxc' /proc/1/cgroup 2>/dev/null && return 0
  [[ -n "${container:-}" ]] && return 0
  return 1
}
