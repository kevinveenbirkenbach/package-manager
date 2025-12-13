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

nixconf_ensure_experimental_features() {
  local nix_conf want
  nix_conf="$(nixconf_file_path)"
  want="experimental-features = nix-command flakes"

  mkdir -p /etc/nix

  if [[ ! -f "${nix_conf}" ]]; then
    echo "[nix-conf] Creating ${nix_conf} with: ${want}"
    printf "%s\n" "${want}" >"${nix_conf}"
    return 0
  fi

  if grep -qE '^\s*experimental-features\s*=' "${nix_conf}"; then
    if grep -qE '^\s*experimental-features\s*=.*\bnix-command\b' "${nix_conf}" \
      && grep -qE '^\s*experimental-features\s*=.*\bflakes\b' "${nix_conf}"; then
      echo "[nix-conf] experimental-features already correct"
      return 0
    fi

    echo "[nix-conf] Extending experimental-features in ${nix_conf}"

    local current
    current="$(grep -E '^\s*experimental-features\s*=' "${nix_conf}" | head -n1 | cut -d= -f2-)"
    current="$(echo "${current}" | xargs)" # trim

    # Build a merged feature string without duplicates (simple token set)
    local merged="nix-command flakes"
    local token
    for token in ${current}; do
      if [[ " ${merged} " != *" ${token} "* ]]; then
        merged="${merged} ${token}"
      fi
    done

    sed -i "s|^\s*experimental-features\s*=.*|experimental-features = ${merged}|" "${nix_conf}"
    return 0
  fi

  echo "[nix-conf] Appending to ${nix_conf}: ${want}"
  printf "\n%s\n" "${want}" >>"${nix_conf}"
}
