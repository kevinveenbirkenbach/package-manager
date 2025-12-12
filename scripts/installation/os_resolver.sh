#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# OsResolver (bash "class-style" module)
# Centralizes OS detection + normalization + supported checks + script paths.
# -----------------------------------------------------------------------------

osr_detect_raw_id() {
  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    echo "${ID:-unknown}"
  else
    echo "unknown"
  fi
}

osr_detect_id_like() {
  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    echo "${ID_LIKE:-}"
  else
    echo ""
  fi
}

osr_normalize_id() {
  local raw="${1:-unknown}"
  local like="${2:-}"

  # Explicit mapping first (your bugfix: manjaro -> arch everywhere)
  case "${raw}" in
    manjaro) echo "arch"; return 0 ;;
  esac

  # Keep direct IDs when they are already supported
  case "${raw}" in
    arch|debian|ubuntu|fedora|centos) echo "${raw}"; return 0 ;;
  esac

  # Fallback mapping via ID_LIKE for better portability
  # Example: many Arch derivatives expose ID_LIKE="arch"
  if [[ " ${like} " == *" arch "* ]]; then
    echo "arch"; return 0
  fi
  if [[ " ${like} " == *" debian "* ]]; then
    echo "debian"; return 0
  fi
  if [[ " ${like} " == *" fedora "* ]]; then
    echo "fedora"; return 0
  fi
  if [[ " ${like} " == *" rhel "* || " ${like} " == *" centos "* ]]; then
    echo "centos"; return 0
  fi

  echo "${raw}"
}

osr_get_os_id() {
  local raw like
  raw="$(osr_detect_raw_id)"
  like="$(osr_detect_id_like)"
  osr_normalize_id "${raw}" "${like}"
}

osr_is_supported() {
  local id="${1:-unknown}"
  case "${id}" in
    arch|debian|ubuntu|fedora|centos) return 0 ;;
    *) return 1 ;;
  esac
}

osr_script_path_for() {
  local script_dir="${1:?script_dir required}"
  local os_id="${2:?os_id required}"
  local kind="${3:?kind required}" # "dependencies" or "package"

  echo "${script_dir}/${os_id}/${kind}.sh"
}
