#!/usr/bin/env bash
set -euo pipefail

echo "[init-nix] Starting Nix initialization..."

NIX_INSTALL_URL="${NIX_INSTALL_URL:-https://nixos.org/nix/install}"
NIX_DOWNLOAD_MAX_TIME=300
NIX_DOWNLOAD_SLEEP_INTERVAL=20

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
  [[ -x /nix/var/nix/profiles/default/bin/nix ]] && \
    PATH="/nix/var/nix/profiles/default/bin:$PATH"

  [[ -x "$HOME/.nix-profile/bin/nix" ]] && \
    PATH="$HOME/.nix-profile/bin:$PATH"

  [[ -x /home/nix/.nix-profile/bin/nix ]] && \
    PATH="/home/nix/.nix-profile/bin:$PATH"

  export PATH
}

# ---------------------------------------------------------------------------
# Resolve nix binary path robustly (Arch-safe)
# ---------------------------------------------------------------------------
resolve_nix_bin() {
  local nix_cmd

  nix_cmd="$(command -v nix 2>/dev/null || true)"
  [[ -n "$nix_cmd" ]] && { echo "$nix_cmd"; return 0; }

  # Prefer canonical locations
  [[ -x /usr/local/bin/nix ]] && { echo "/usr/local/bin/nix"; return 0; }
  [[ -x /usr/bin/nix ]]       && { echo "/usr/bin/nix"; return 0; }
  [[ -x /usr/sbin/nix ]]      && { echo "/usr/sbin/nix"; return 0; }
  [[ -x /bin/nix ]]           && { echo "/bin/nix"; return 0; }

  [[ -x /nix/var/nix/profiles/default/bin/nix ]] && {
    echo "/nix/var/nix/profiles/default/bin/nix"; return 0;
  }

  [[ -x "$HOME/.nix-profile/bin/nix" ]] && {
    echo "$HOME/.nix-profile/bin/nix"; return 0;
  }

  [[ -x /home/nix/.nix-profile/bin/nix ]] && {
    echo "/home/nix/.nix-profile/bin/nix"; return 0;
  }

  return 1
}

# ---------------------------------------------------------------------------
# Ensure globally reachable nix symlinks (CI / non-login shells)
# ---------------------------------------------------------------------------
ensure_global_nix_symlinks() {
  local nix_bin="${1:-}"

  [[ -z "$nix_bin" ]] && nix_bin="$(resolve_nix_bin 2>/dev/null || true)"

  if [[ -z "$nix_bin" || ! -x "$nix_bin" ]]; then
    echo "[init-nix] WARNING: nix binary not found, cannot create symlinks."
    return 0
  fi

  mkdir -p /usr/local/bin || true

  ln -sf "$nix_bin" /usr/local/bin/nix && \
    echo "[init-nix] Ensured /usr/local/bin/nix -> $nix_bin"

  ln -sf "$nix_bin" /usr/bin/nix 2>/dev/null || true
  ln -sf "$nix_bin" /bin/nix      2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Ensure Nix build group and users exist
# ---------------------------------------------------------------------------
ensure_nix_build_group() {
  getent group nixbld >/dev/null 2>&1 || groupadd -r nixbld

  for i in $(seq 1 10); do
    id "nixbld$i" >/dev/null 2>&1 || \
      useradd -r -g nixbld -G nixbld -s /usr/sbin/nologin "nixbld$i"
  done
}

# ---------------------------------------------------------------------------
# Download and run Nix installer with retry
# ---------------------------------------------------------------------------
install_nix_with_retry() {
  local mode="$1"
  local run_as="${2:-}"
  local installer elapsed=0 mode_flag

  case "$mode" in
    daemon)    mode_flag="--daemon" ;;
    no-daemon) mode_flag="--no-daemon" ;;
    *) echo "[init-nix] ERROR: invalid mode $mode"; exit 1 ;;
  esac

  installer="$(mktemp -t nix-installer.XXXXXX)"
  chmod 0644 "$installer"

  while true; do
    if curl -fL "$NIX_INSTALL_URL" -o "$installer"; then
      break
    fi
    elapsed=$((elapsed + NIX_DOWNLOAD_SLEEP_INTERVAL))
    (( elapsed >= NIX_DOWNLOAD_MAX_TIME )) && {
      echo "[init-nix] ERROR: failed to download installer"
      exit 1
    }
    sleep "$NIX_DOWNLOAD_SLEEP_INTERVAL"
  done

  if [[ -n "$run_as" ]]; then
    chown "$run_as:$run_as" "$installer" 2>/dev/null || true
    if command -v sudo >/dev/null; then
      sudo -u "$run_as" bash -lc "sh '$installer' $mode_flag"
    else
      su - "$run_as" -c "sh '$installer' $mode_flag"
    fi
  else
    sh "$installer" "$mode_flag"
  fi

  rm -f "$installer"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  if command -v nix >/dev/null 2>&1; then
    echo "[init-nix] Nix already available on PATH: $(command -v nix)"
    [[ "${EUID:-0}" -eq 0 ]] && ensure_global_nix_symlinks "$(resolve_nix_bin)"
    return 0
  fi

  ensure_nix_on_path

  if command -v nix >/dev/null 2>&1; then
    echo "[init-nix] Nix found after PATH adjustment: $(command -v nix)"
    [[ "${EUID:-0}" -eq 0 ]] && ensure_global_nix_symlinks "$(resolve_nix_bin)"
    return 0
  fi

  local IN_CONTAINER=0
  is_container && IN_CONTAINER=1

  if [[ "$IN_CONTAINER" -eq 1 && "${EUID:-0}" -eq 0 ]]; then
    ensure_nix_build_group
    id nix >/dev/null 2>&1 || useradd -m -r -g nixbld -s /bin/bash nix
    mkdir -p /nix && chown nix:nixbld /nix
    install_nix_with_retry no-daemon nix
  else
    if command -v systemctl >/dev/null 2>&1; then
      [[ "${EUID:-0}" -eq 0 ]] && ensure_nix_build_group
      install_nix_with_retry daemon
    else
      install_nix_with_retry no-daemon
    fi
  fi

  ensure_nix_on_path

  if [[ "${EUID:-0}" -eq 0 ]]; then
    ensure_global_nix_symlinks "$(resolve_nix_bin)"
  fi

  command -v nix >/dev/null 2>&1 || {
    echo "[init-nix] ERROR: nix not found after installation"
    exit 1
  }

  echo "[init-nix] Nix successfully installed at: $(command -v nix)"
}

main "$@"
