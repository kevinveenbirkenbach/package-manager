#!/usr/bin/env bash
set -euo pipefail

echo "[init-nix] Starting Nix initialization..."

NIX_INSTALL_URL="${NIX_INSTALL_URL:-https://nixos.org/nix/install}"
NIX_DOWNLOAD_MAX_TIME="${NIX_DOWNLOAD_MAX_TIME:-300}"
NIX_DOWNLOAD_SLEEP_INTERVAL="${NIX_DOWNLOAD_SLEEP_INTERVAL:-20}"

# ---------------------------------------------------------------------------
# Detect whether we are inside a container (Docker/Podman/etc.)
# ---------------------------------------------------------------------------
is_container() {
  [[ -f /.dockerenv || -f /run/.containerenv ]] && return 0
  grep -qiE 'docker|container|podman|lxc' /proc/1/cgroup 2>/dev/null && return 0
  [[ -n "${container:-}" ]] && return 0
  return 1
}

# ---------------------------------------------------------------------------
# Ensure Nix binaries are on PATH (additive, never destructive)
# ---------------------------------------------------------------------------
ensure_nix_on_path() {
  if [[ -x /nix/var/nix/profiles/default/bin/nix ]]; then
    PATH="/nix/var/nix/profiles/default/bin:$PATH"
  fi
  if [[ -x "$HOME/.nix-profile/bin/nix" ]]; then
    PATH="$HOME/.nix-profile/bin:$PATH"
  fi
  if [[ -x /home/nix/.nix-profile/bin/nix ]]; then
    PATH="/home/nix/.nix-profile/bin:$PATH"
  fi
  if [[ -d "$HOME/.local/bin" ]]; then
    PATH="$HOME/.local/bin:$PATH"
  fi
  export PATH
}

# ---------------------------------------------------------------------------
# Resolve a path to a real executable (follows symlinks)
# ---------------------------------------------------------------------------
real_exe() {
  local p="${1:-}"
  [[ -z "$p" ]] && return 1

  local r
  r="$(readlink -f "$p" 2>/dev/null || echo "$p")"

  [[ -x "$r" ]] && { echo "$r"; return 0; }
  return 1
}

# ---------------------------------------------------------------------------
# Resolve nix binary path robustly (works across distros + Arch /usr/sbin)
# ---------------------------------------------------------------------------
resolve_nix_bin() {
  local nix_cmd=""
  nix_cmd="$(command -v nix 2>/dev/null || true)"
  [[ -n "$nix_cmd" ]] && real_exe "$nix_cmd" && return 0

  # IMPORTANT: prefer system locations before /usr/local to avoid self-symlink traps
  [[ -x /usr/sbin/nix ]]      && { echo "/usr/sbin/nix"; return 0; } # Arch package can land here
  [[ -x /usr/bin/nix ]]       && { echo "/usr/bin/nix"; return 0; }
  [[ -x /bin/nix ]]           && { echo "/bin/nix"; return 0; }

  # /usr/local last, and only if it resolves to a real executable
  [[ -e /usr/local/bin/nix ]] && real_exe "/usr/local/bin/nix" && return 0

  [[ -x /nix/var/nix/profiles/default/bin/nix ]] && {
    echo "/nix/var/nix/profiles/default/bin/nix"; return 0;
  }

  [[ -x "$HOME/.nix-profile/bin/nix" ]] && {
    echo "$HOME/.nix-profile/bin/nix"; return 0;
  }

  [[ -x "$HOME/.local/bin/nix" ]] && {
    echo "$HOME/.local/bin/nix"; return 0;
  }

  [[ -x /home/nix/.nix-profile/bin/nix ]] && {
    echo "/home/nix/.nix-profile/bin/nix"; return 0;
  }

  return 1
}

# ---------------------------------------------------------------------------
# Ensure globally reachable nix symlink(s) (CI / non-login shells) - root only
#
# Key rule:
# - Never overwrite distro-managed nix locations (Arch may ship nix in /usr/sbin).
# - But for sudo secure_path (CentOS), /usr/local/bin is often NOT included.
#   Therefore: also create /usr/bin/nix (and /usr/sbin/nix) ONLY if they do not exist.
# ---------------------------------------------------------------------------
ensure_global_nix_symlinks() {
  local nix_bin="${1:-}"

  [[ -z "$nix_bin" ]] && nix_bin="$(resolve_nix_bin 2>/dev/null || true)"

  if [[ -z "$nix_bin" || ! -x "$nix_bin" ]]; then
    echo "[init-nix] WARNING: nix binary not found, cannot create global symlink(s)."
    return 0
  fi

  # Always link to the real executable to avoid /usr/local/bin/nix -> /usr/local/bin/nix
  nix_bin="$(real_exe "$nix_bin" 2>/dev/null || echo "$nix_bin")"

  local targets=()

  # Always provide /usr/local/bin/nix for CI shells
  mkdir -p /usr/local/bin 2>/dev/null || true
  targets+=("/usr/local/bin/nix")

  # Provide sudo-friendly locations only if they are NOT present (do not override distro paths)
  if [[ ! -e /usr/bin/nix ]]; then
    targets+=("/usr/bin/nix")
  fi
  if [[ ! -e /usr/sbin/nix ]]; then
    targets+=("/usr/sbin/nix")
  fi

  local target current_real
  for target in "${targets[@]}"; do
    current_real=""
    if [[ -e "$target" ]]; then
      current_real="$(real_exe "$target" 2>/dev/null || true)"
    fi

    if [[ -n "$current_real" && "$current_real" == "$nix_bin" ]]; then
      echo "[init-nix] $target already points to: $nix_bin"
      continue
    fi

    # If something exists but is not the same (and we promised not to override), skip.
    if [[ -e "$target" && "$target" != "/usr/local/bin/nix" ]]; then
      echo "[init-nix] WARNING: $target exists; not overwriting."
      continue
    fi

    if ln -sf "$nix_bin" "$target" 2>/dev/null; then
      echo "[init-nix] Ensured $target -> $nix_bin"
    else
      echo "[init-nix] WARNING: Failed to ensure $target symlink."
    fi
  done
}

# ---------------------------------------------------------------------------
# Ensure user-level nix symlink (works without root; CI-safe)
# ---------------------------------------------------------------------------
ensure_user_nix_symlink() {
  local nix_bin="${1:-}"

  [[ -z "$nix_bin" ]] && nix_bin="$(resolve_nix_bin 2>/dev/null || true)"

  if [[ -z "$nix_bin" || ! -x "$nix_bin" ]]; then
    echo "[init-nix] WARNING: nix binary not found, cannot create user symlink."
    return 0
  fi

  nix_bin="$(real_exe "$nix_bin" 2>/dev/null || echo "$nix_bin")"

  mkdir -p "$HOME/.local/bin" 2>/dev/null || true
  ln -sf "$nix_bin" "$HOME/.local/bin/nix"

  echo "[init-nix] Ensured $HOME/.local/bin/nix -> $nix_bin"

  PATH="$HOME/.local/bin:$PATH"
  export PATH

  if [[ -w "$HOME/.profile" ]] && ! grep -q 'init-nix.sh' "$HOME/.profile" 2>/dev/null; then
    cat >>"$HOME/.profile" <<'EOF'

# PATH for nix (added by package-manager init-nix.sh)
if [ -d "$HOME/.local/bin" ]; then
  PATH="$HOME/.local/bin:$PATH"
fi
EOF
  fi
}

# ---------------------------------------------------------------------------
# Ensure Nix build group and users exist (build-users-group = nixbld) - root only
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

  case "$mode" in
    daemon)    mode_flag="--daemon" ;;
    no-daemon) mode_flag="--no-daemon" ;;
    *)
      echo "[init-nix] ERROR: Invalid mode '$mode' (expected 'daemon' or 'no-daemon')."
      exit 1
      ;;
  esac

  installer="$(mktemp -t nix-installer.XXXXXX)"
  chmod 0644 "$installer"

  echo "[init-nix] Downloading Nix installer from $NIX_INSTALL_URL (max ${NIX_DOWNLOAD_MAX_TIME}s)..."

  while true; do
    if curl -fL "$NIX_INSTALL_URL" -o "$installer"; then
      echo "[init-nix] Successfully downloaded installer to $installer"
      break
    fi

    elapsed=$((elapsed + NIX_DOWNLOAD_SLEEP_INTERVAL))
    echo "[init-nix] WARNING: Download failed. Retrying in ${NIX_DOWNLOAD_SLEEP_INTERVAL}s (elapsed ${elapsed}s)..."

    if (( elapsed >= NIX_DOWNLOAD_MAX_TIME )); then
      echo "[init-nix] ERROR: Giving up after ${elapsed}s trying to download Nix installer."
      rm -f "$installer"
      exit 1
    fi

    sleep "$NIX_DOWNLOAD_SLEEP_INTERVAL"
  done

  if [[ -n "$run_as" ]]; then
    chown "$run_as:$run_as" "$installer" 2>/dev/null || true
    echo "[init-nix] Running installer as user '$run_as' ($mode_flag)..."
    if command -v sudo >/dev/null 2>&1; then
      sudo -u "$run_as" bash -lc "sh '$installer' $mode_flag"
    else
      su - "$run_as" -c "sh '$installer' $mode_flag"
    fi
  else
    echo "[init-nix] Running installer as current user ($mode_flag)..."
    sh "$installer" "$mode_flag"
  fi

  rm -f "$installer"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  # Fast path: already available
  if command -v nix >/dev/null 2>&1; then
    echo "[init-nix] Nix already available on PATH: $(command -v nix)"
    ensure_nix_on_path

    if [[ "${EUID:-0}" -eq 0 ]]; then
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

    if [[ ! -d /nix ]]; then
      echo "[init-nix] Creating /nix with owner nix:nixbld..."
      mkdir -m 0755 /nix
      chown nix:nixbld /nix
    else
      local current_owner current_group
      current_owner="$(stat -c '%U' /nix 2>/dev/null || echo '?')"
      current_group="$(stat -c '%G' /nix 2>/dev/null || echo '?')"
      if [[ "$current_owner" != "nix" || "$current_group" != "nixbld" ]]; then
        echo "[init-nix] Fixing /nix ownership from $current_owner:$current_group to nix:nixbld..."
        chown -R nix:nixbld /nix
      fi
    fi

    install_nix_with_retry "no-daemon" "nix"

    ensure_nix_on_path

    # Ensure stable global symlink(s) (sudo secure_path friendly)
    ensure_global_nix_symlinks "/home/nix/.nix-profile/bin/nix"

    # Ensure non-root users can traverse and execute nix user profile
    if [[ -d /home/nix ]]; then
      chmod o+rx /home/nix 2>/dev/null || true
    fi
    if [[ -d /home/nix/.nix-profile ]]; then
      chmod -R o+rx /home/nix/.nix-profile 2>/dev/null || true
    fi

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
