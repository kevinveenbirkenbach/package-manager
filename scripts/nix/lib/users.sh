#!/usr/bin/env bash

if [[ -n "${PKGMGR_NIX_USERS_SH:-}" ]]; then
  return 0
fi
PKGMGR_NIX_USERS_SH=1

# Ensure Nix build group and users exist (build-users-group = nixbld) - root only
ensure_nix_build_group() {
  if ! getent group nixbld >/dev/null 2>&1; then
    echo "[init-nix] Creating group 'nixbld'..."
    groupadd -r nixbld
  fi

  for i in $(seq 1 10); do
    if ! id "nixbld$i" >/dev/null 2>&1; then
      echo "[init-nix] Creating build user nixbld$i..."
      useradd -r -g nixbld -G nixbld -s /usr/sbin/nologin "nixbld$i"
    fi
  done
}

# Container-only helper: /nix ownership + perms for single-user install as 'nix'
ensure_nix_store_dir_for_container_user() {
  if [[ ! -d /nix ]]; then
    echo "[init-nix] Creating /nix with owner nix:nixbld..."
    mkdir -m 0755 /nix
    chown nix:nixbld /nix
    return 0
  fi

  local current_owner current_group
  current_owner="$(stat -c '%U' /nix 2>/dev/null || echo '?')"
  current_group="$(stat -c '%G' /nix 2>/dev/null || echo '?')"
  if [[ "$current_owner" != "nix" || "$current_group" != "nixbld" ]]; then
    echo "[init-nix] Fixing /nix ownership from $current_owner:$current_group to nix:nixbld..."
    chown -R nix:nixbld /nix
  fi
}

# Container-only helper: make nix profile executable/traversable for non-root
ensure_container_profile_perms() {
  if [[ -d /home/nix ]]; then
    chmod o+rx /home/nix 2>/dev/null || true
  fi
  if [[ -d /home/nix/.nix-profile ]]; then
    chmod -R o+rx /home/nix/.nix-profile 2>/dev/null || true
  fi
}
