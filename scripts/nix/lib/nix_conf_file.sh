#!/usr/bin/env bash
set -euo pipefail

# Prevent double-sourcing
if [[ -n "${PKGMGR_NIX_CONF_FILE_SH:-}" ]]; then
  return 0
fi
PKGMGR_NIX_CONF_FILE_SH=1

nixconf_file_path() {
  echo "/etc/nix/nix.conf"
}

# Ensure a given nix.conf key contains required tokens (merged, no duplicates)
nixconf_ensure_features_key() {
  local nix_conf="$1"
  local key="$2"
  shift 2
  local required=("$@")

  mkdir -p /etc/nix

  # Create file if missing (with just the required tokens)
  if [[ ! -f "${nix_conf}" ]]; then
    local want="${key} = ${required[*]}"
    echo "[nix-conf] Creating ${nix_conf} with: ${want}"
    printf "%s\n" "${want}" >"${nix_conf}"
    return 0
  fi

  # Key exists -> merge tokens
  if grep -qE "^\s*${key}\s*=" "${nix_conf}"; then
    local ok=1
    local t
    for t in "${required[@]}"; do
      if ! grep -qE "^\s*${key}\s*=.*\b${t}\b" "${nix_conf}"; then
        ok=0
        break
      fi
    done

    if [[ "$ok" -eq 1 ]]; then
      echo "[nix-conf] ${key} already correct"
      return 0
    fi

    echo "[nix-conf] Extending ${key} in ${nix_conf}"

    local current
    current="$(grep -E "^\s*${key}\s*=" "${nix_conf}" | head -n1 | cut -d= -f2-)"
    current="$(echo "${current}" | xargs)" # trim

    local merged=""
    local token

    # Start with existing tokens
    for token in ${current}; do
      if [[ " ${merged} " != *" ${token} "* ]]; then
        merged="${merged} ${token}"
      fi
    done

    # Add required tokens
    for token in "${required[@]}"; do
      if [[ " ${merged} " != *" ${token} "* ]]; then
        merged="${merged} ${token}"
      fi
    done

    merged="$(echo "${merged}" | xargs)" # trim

    sed -i "s|^\s*${key}\s*=.*|${key} = ${merged}|" "${nix_conf}"
    return 0
  fi

  # Key missing -> append
  local want="${key} = ${required[*]}"
  echo "[nix-conf] Appending to ${nix_conf}: ${want}"
  printf "\n%s\n" "${want}" >>"${nix_conf}"
}

nixconf_ensure_experimental_features() {
  local nix_conf
  nix_conf="$(nixconf_file_path)"

  # Ensure both keys to avoid prompts and cover older/alternate expectations
  nixconf_ensure_features_key "${nix_conf}" "experimental-features" "nix-command" "flakes"
  nixconf_ensure_features_key "${nix_conf}" "extra-experimental-features" "nix-command" "flakes"
}
