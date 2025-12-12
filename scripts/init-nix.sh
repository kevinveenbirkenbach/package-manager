#!/usr/bin/env bash
set -euo pipefail

echo "[init-nix] Starting Nix initialization..."

NIX_INSTALL_URL="${NIX_INSTALL_URL:-https://nixos.org/nix/install}"
NIX_DOWNLOAD_MAX_TIME=300      # 5 minutes
NIX_DOWNLOAD_SLEEP_INTERVAL=20 # 20 seconds

# ---------------------------------------------------------------------------
# Detect whether we are inside a container (Docker/Podman/etc.)
# ---------------------------------------------------------------------------
is_container() {
  if [[ -f /.dockerenv ]] || [[ -f /run/.containerenv ]]; then
    return 0
  fi

  if grep -qiE 'docker|container|podman|lxc' /proc/1/cgroup 2>/dev/null; then
    return 0
  fi

  if [[ -n "${container:-}" ]]; then
    return 0
  fi

  return 1
}

# ---------------------------------------------------------------------------
# Ensure Nix binaries are on PATH (multi-user or single-user)
# ---------------------------------------------------------------------------
ensure_nix_on_path() {
  if [[ -x /nix/var/nix/profiles/default/bin/nix ]]; then
    export PATH="/nix/var/nix/profiles/default/bin:${PATH}"
  fi

  if [[ -x "${HOME}/.nix-profile/bin/nix" ]]; then
    export PATH="${HOME}/.nix-profile/bin:${PATH}"
  fi

  if [[ -x /home/nix/.nix-profile/bin/nix ]]; then
    export PATH="/home/nix/.nix-profile/bin:${PATH}"
  fi
}

# ---------------------------------------------------------------------------
# Ensure Nix build group and users exist (build-users-group = nixbld)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Download and run Nix installer with retry
#   Usage: install_nix_with_retry daemon|no-daemon [run_as_user]
# ---------------------------------------------------------------------------
install_nix_with_retry() {
  local mode="$1"
  local run_as="${2:-}"
  local installer elapsed=0 mode_flag

  case "${mode}" in
    daemon)    mode_flag="--daemon" ;;
    no-daemon) mode_flag="--no-daemon" ;;
    *)
      echo "[init-nix] ERROR: Invalid mode '${mode}', expected 'daemon' or 'no-daemon'."
      exit 1
      ;;
  esac

  installer="$(mktemp -t nix-installer.XXXXXX)"

  # -------------------------------------------------------------------------
  # FIX: mktemp creates files with 0600 by default, which breaks when we later
  #      run the installer as a different user (e.g., 'nix' in container+root).
  #      Make it readable and (best-effort) owned by the target user.
  # -------------------------------------------------------------------------
  chmod 0644 "${installer}"

  echo "[init-nix] Downloading Nix installer from ${NIX_INSTALL_URL} with retry (max ${NIX_DOWNLOAD_MAX_TIME}s)..."

  while true; do
    if curl -fL "${NIX_INSTALL_URL}" -o "${installer}"; then
      echo "[init-nix] Successfully downloaded Nix installer to ${installer}"
      break
    fi

    local curl_exit=$?
    echo "[init-nix] WARNING: Failed to download Nix installer (curl exit code ${curl_exit})."

    elapsed=$((elapsed + NIX_DOWNLOAD_SLEEP_INTERVAL))
    if (( elapsed >= NIX_DOWNLOAD_MAX_TIME )); then
      echo "[init-nix] ERROR: Giving up after ${elapsed}s trying to download Nix installer."
      rm -f "${installer}"
      exit 1
    fi

    echo "[init-nix] Retrying in ${NIX_DOWNLOAD_SLEEP_INTERVAL}s (elapsed: ${elapsed}s/${NIX_DOWNLOAD_MAX_TIME}s)..."
    sleep "${NIX_DOWNLOAD_SLEEP_INTERVAL}"
  done

  if [[ -n "${run_as}" ]]; then
    # Best-effort: ensure the target user can read the downloaded installer
    chown "${run_as}:${run_as}" "${installer}" 2>/dev/null || true

    echo "[init-nix] Running installer as user '${run_as}' with mode '${mode}'..."
    if command -v sudo >/dev/null 2>&1; then
      sudo -u "${run_as}" bash -lc "sh '${installer}' ${mode_flag}"
    else
      su - "${run_as}" -c "sh '${installer}' ${mode_flag}"
    fi
  else
    echo "[init-nix] Running installer as current user with mode '${mode}'..."
    sh "${installer}" "${mode_flag}"
  fi

  rm -f "${installer}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  # Fast path: Nix already available
  if command -v nix >/dev/null 2>&1; then
    echo "[init-nix] Nix already available on PATH: $(command -v nix)"
    return 0
  fi

  ensure_nix_on_path

  if command -v nix >/dev/null 2>&1; then
    echo "[init-nix] Nix found after adjusting PATH: $(command -v nix)"
    return 0
  fi

  echo "[init-nix] Nix not found, starting installation logic..."

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
  if [[ "${IN_CONTAINER}" -eq 1 && "${EUID:-0}" -eq 0 ]]; then
    echo "[init-nix] Container + root – installing as 'nix' user (single-user)."

    ensure_nix_build_group

    if ! id nix >/dev/null 2>&1; then
      echo "[init-nix] Creating user 'nix'..."
      local BASH_SHELL
      BASH_SHELL="$(command -v bash || true)"
      [[ -z "${BASH_SHELL}" ]] && BASH_SHELL="/bin/sh"
      useradd -m -r -g nixbld -s "${BASH_SHELL}" nix
    fi

    if [[ ! -d /nix ]]; then
      echo "[init-nix] Creating /nix with owner nix:nixbld..."
      mkdir -m 0755 /nix
      chown nix:nixbld /nix
    else
      local current_owner current_group
      current_owner="$(stat -c '%U' /nix 2>/dev/null || echo '?')"
      current_group="$(stat -c '%G' /nix 2>/dev/null || echo '?')"
      if [[ "${current_owner}" != "nix" || "${current_group}" != "nixbld" ]]; then
        echo "[init-nix] Fixing /nix ownership from ${current_owner}:${current_group} to nix:nixbld..."
        chown -R nix:nixbld /nix
      fi
      if [[ ! -w /nix ]]; then
        echo "[init-nix] WARNING: /nix is not writable after chown; Nix installer may fail."
      fi
    fi

    install_nix_with_retry "no-daemon" "nix"

    ensure_nix_on_path

    if [[ -x /home/nix/.nix-profile/bin/nix && ! -e /usr/local/bin/nix ]]; then
      echo "[init-nix] Creating /usr/local/bin/nix symlink -> /home/nix/.nix-profile/bin/nix"
      ln -s /home/nix/.nix-profile/bin/nix /usr/local/bin/nix
    fi

  # -------------------------------------------------------------------------
  # Host (no container)
  # -------------------------------------------------------------------------
  elif [[ "${IN_CONTAINER}" -eq 0 ]]; then
    if command -v systemctl >/dev/null 2>&1; then
      echo "[init-nix] Host with systemd – using multi-user install (--daemon)."
      if [[ "${EUID:-0}" -eq 0 ]]; then
        ensure_nix_build_group
      fi
      install_nix_with_retry "daemon"
    else
      if [[ "${EUID:-0}" -eq 0 ]]; then
        echo "[init-nix] Host without systemd as root – using single-user install (--no-daemon)."
        ensure_nix_build_group
      else
        echo "[init-nix] Host without systemd as non-root – using single-user install (--no-daemon)."
      fi
      install_nix_with_retry "no-daemon"
    fi

  # -------------------------------------------------------------------------
  # Container, but not root (rare)
  # -------------------------------------------------------------------------
  else
    echo "[init-nix] Container as non-root – using single-user install (--no-daemon)."
    install_nix_with_retry "no-daemon"
  fi

  # -------------------------------------------------------------------------
  # After installation: PATH + /etc/profile
  # -------------------------------------------------------------------------
  ensure_nix_on_path

  if ! command -v nix >/dev/null 2>&1; then
    echo "[init-nix] WARNING: Nix installation finished, but 'nix' is still not on PATH."
    echo "[init-nix] You may need to source your shell profile manually."
  else
    echo "[init-nix] Nix successfully installed at: $(command -v nix)"
  fi

  if [[ -w /etc/profile ]] && ! grep -q 'Nix profiles' /etc/profile 2>/dev/null; then
    cat <<'EOF' >> /etc/profile

# Nix profiles (added by package-manager init-nix.sh)
if [ -d /nix/var/nix/profiles/default/bin ]; then
  PATH="/nix/var/nix/profiles/default/bin:$PATH"
fi
if [ -d "$HOME/.nix-profile/bin" ]; then
  PATH="$HOME/.nix-profile/bin:$PATH"
fi
EOF
    echo "[init-nix] Appended Nix PATH setup to /etc/profile"
  fi

  echo "[init-nix] Nix initialization complete."
}

main "$@"
