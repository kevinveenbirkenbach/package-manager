#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=lib/bootstrap_config.sh
# shellcheck source=lib/detect.sh
# shellcheck source=lib/path.sh
# shellcheck source=lib/symlinks.sh
# shellcheck source=lib/users.sh
# shellcheck source=lib/install.sh
# shellcheck source=lib/nix_conf_file.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/lib/bootstrap_config.sh"
source "${SCRIPT_DIR}/lib/detect.sh"
source "${SCRIPT_DIR}/lib/path.sh"
source "${SCRIPT_DIR}/lib/symlinks.sh"
source "${SCRIPT_DIR}/lib/users.sh"
source "${SCRIPT_DIR}/lib/install.sh"
source "${SCRIPT_DIR}/lib/nix_conf_file.sh"

echo "[init-nix] Starting Nix initialization..."

main() {
  # Fast path: already available
  if command -v nix >/dev/null 2>&1; then
    echo "[init-nix] Nix already available on PATH: $(command -v nix)"
    ensure_nix_on_path

    if [[ "${EUID:-0}" -eq 0 ]]; then
      nixconf_ensure_experimental_features
      ensure_global_nix_symlinks "$(resolve_nix_bin 2>/dev/null || true)"
    else
      ensure_user_nix_symlink "$(resolve_nix_bin 2>/dev/null || true)"
    fi

    return 0
  fi

  ensure_nix_on_path

  if command -v nix >/dev/null 2>&1; then
    echo "[init-nix] Nix found after PATH adjustment: $(command -v nix)"
    if [[ "${EUID:-0}" -eq 0 ]]; then
      ensure_global_nix_symlinks "$(resolve_nix_bin 2>/dev/null || true)"
    else
      ensure_user_nix_symlink "$(resolve_nix_bin 2>/dev/null || true)"
    fi
    return 0
  fi

  local IN_CONTAINER=0
  if is_container; then
    IN_CONTAINER=1
    echo "[init-nix] Detected container environment."
  else
    echo "[init-nix] No container detected."
  fi

  # -------------------------------------------------------------------------
  # Container + root: dedicated "nix" user, single-user install
  # -------------------------------------------------------------------------
  if [[ "$IN_CONTAINER" -eq 1 && "${EUID:-0}" -eq 0 ]]; then
    echo "[init-nix] Container + root: installing as 'nix' user (single-user)."

    ensure_nix_build_group

    if ! id nix >/dev/null 2>&1; then
      echo "[init-nix] Creating user 'nix'..."
      local BASH_SHELL
      BASH_SHELL="$(command -v bash || true)"
      [[ -z "$BASH_SHELL" ]] && BASH_SHELL="/bin/sh"
      useradd -m -r -g nixbld -s "$BASH_SHELL" nix
    fi

    ensure_nix_store_dir_for_container_user

    install_nix_with_retry "no-daemon" "nix"

    ensure_nix_on_path

    # Ensure stable global symlink(s) (sudo secure_path friendly)
    ensure_global_nix_symlinks "/home/nix/.nix-profile/bin/nix"

    # Ensure non-root users can traverse and execute nix user profile
    ensure_container_profile_perms

  # -------------------------------------------------------------------------
  # Host (no container)
  # -------------------------------------------------------------------------
  else
    if command -v systemctl >/dev/null 2>&1; then
      echo "[init-nix] Host with systemd: using multi-user install (--daemon)."
      if [[ "${EUID:-0}" -eq 0 ]]; then
        ensure_nix_build_group
      fi
      install_nix_with_retry "daemon"
    else
      echo "[init-nix] No systemd detected: using single-user install (--no-daemon)."
      if [[ "${EUID:-0}" -eq 0 ]]; then
        ensure_nix_build_group
      fi
      install_nix_with_retry "no-daemon"
    fi
  fi

  # -------------------------------------------------------------------------
  # After install: PATH + symlink(s)
  # -------------------------------------------------------------------------
  ensure_nix_on_path

  if [[ "${EUID:-0}" -eq 0 ]]; then
    nixconf_ensure_experimental_features
  fi

  local nix_bin_post
  nix_bin_post="$(resolve_nix_bin 2>/dev/null || true)"

  if [[ "${EUID:-0}" -eq 0 ]]; then
    ensure_global_nix_symlinks "$nix_bin_post"
  else
    ensure_user_nix_symlink "$nix_bin_post"
  fi

  # Final verification (must succeed for CI)
  if ! command -v nix >/dev/null 2>&1; then
    echo "[init-nix] ERROR: nix not found after installation."
    echo "[init-nix] DEBUG: resolved nix path = ${nix_bin_post:-<empty>}"
    echo "[init-nix] DEBUG: PATH = $PATH"
    exit 1
  fi

  echo "[init-nix] Nix successfully available at: $(command -v nix)"
  echo "[init-nix] Nix initialization complete."
}

main "$@"
