#!/usr/bin/env bash

if [[ -n "${PKGMGR_NIX_INSTALL_SH:-}" ]]; then
  return 0
fi
PKGMGR_NIX_INSTALL_SH=1

# Requires: NIX_INSTALL_URL, NIX_DOWNLOAD_MAX_TIME, NIX_DOWNLOAD_SLEEP_INTERVAL

# Download and run Nix installer with retry
#   Usage: install_nix_with_retry daemon|no-daemon [run_as_user]
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
    su - "$run_as" -s /bin/bash -c "bash -lc \"sh '$installer' $mode_flag\""
  else
    echo "[init-nix] Running installer as current user ($mode_flag)..."
    sh "$installer" "$mode_flag"
  fi

  rm -f "$installer"
}
