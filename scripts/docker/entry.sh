#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Ensure Nix has access to a valid CA bundle (TLS trust store)
# ---------------------------------------------------------------------------
if [[ -z "${NIX_SSL_CERT_FILE:-}" ]]; then
  if [[ -f /etc/ssl/certs/ca-certificates.crt ]]; then
    # Debian/Ubuntu-style path
    export NIX_SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
    echo "[docker] Using CA bundle: ${NIX_SSL_CERT_FILE}"
  elif [[ -f /etc/pki/tls/certs/ca-bundle.crt ]]; then
    # Fedora/RHEL/CentOS-style path
    export NIX_SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt
    echo "[docker] Using CA bundle: ${NIX_SSL_CERT_FILE}"
  else
    echo "[docker] WARNING: No CA bundle found for Nix (NIX_SSL_CERT_FILE not set)."
    echo "[docker] HTTPS access for Nix flakes may fail."
  fi
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[docker] Starting package-manager container"

# Distro info for logging
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  echo "[docker] Detected distro: ${ID:-unknown} (like: ${ID_LIKE:-})"
fi

# Always use /src (mounted from host) as working directory
echo "[docker] Using /src as working directory"
cd /src

# ------------------------------------------------------------
# DEV mode: build/install package-manager from current /src
# ------------------------------------------------------------
if [[ "${PKGMGR_DEV:-0}" == "1" ]]; then
  echo "[docker] DEV mode enabled (PKGMGR_DEV=1)"
  echo "[docker] Rebuilding package-manager from /src via scripts/installation/run-package.sh..."

  if [[ -x scripts/installation/run-package.sh ]]; then
    bash scripts/installation/run-package.sh
  else
    echo "[docker] ERROR: scripts/installation/run-package.sh not found or not executable"
    exit 1
  fi
fi

# ------------------------------------------------------------
# Hand-off to pkgmgr / arbitrary command
# ------------------------------------------------------------
if [[ $# -eq 0 ]]; then
  echo "[docker] No arguments provided. Showing pkgmgr help..."
  exec pkgmgr --help
else
  echo "[docker] Executing command: $*"
  exec "$@"
fi
