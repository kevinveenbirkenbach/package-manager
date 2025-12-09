#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Detect and export a valid CA bundle so Nix, Git, curl and Python tooling
# can successfully perform HTTPS requests on all distros (Debian, Ubuntu,
# Fedora, RHEL, CentOS, etc.)
# ---------------------------------------------------------------------------
detect_ca_bundle() {
  # Common CA bundle locations across major Linux distributions
  local candidates=(
    /etc/ssl/certs/ca-certificates.crt                       # Debian/Ubuntu
    /etc/ssl/cert.pem                                       # Some distros
    /etc/pki/tls/certs/ca-bundle.crt                        # Fedora/RHEL/CentOS
    /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem       # CentOS/RHEL extracted bundle
    /etc/ssl/ca-bundle.pem                                  # Generic fallback
  )

  for path in "${candidates[@]}"; do
    if [[ -f "$path" ]]; then
      echo "$path"
      return 0
    fi
  done

  return 1
}

# Use existing NIX_SSL_CERT_FILE if provided, otherwise auto-detect
CA_BUNDLE="${NIX_SSL_CERT_FILE:-}"

if [[ -z "${CA_BUNDLE}" ]]; then
  CA_BUNDLE="$(detect_ca_bundle || true)"
fi

if [[ -n "${CA_BUNDLE}" ]]; then
  # Export for Nix (critical)
  export NIX_SSL_CERT_FILE="${CA_BUNDLE}"

  # Export for Git, Python requests, curl, etc.
  export SSL_CERT_FILE="${CA_BUNDLE}"
  export REQUESTS_CA_BUNDLE="${CA_BUNDLE}"
  export GIT_SSL_CAINFO="${CA_BUNDLE}"

  echo "[docker] Using CA bundle: ${CA_BUNDLE}"
else
  echo "[docker] WARNING: No CA certificate bundle found."
  echo "[docker] HTTPS access for Nix flakes and other tools may fail."
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[docker] Starting package-manager container"

# ---------------------------------------------------------------------------
# Log distribution info
# ---------------------------------------------------------------------------
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  echo "[docker] Detected distro: ${ID:-unknown} (like: ${ID_LIKE:-})"
fi

# Always use /src (mounted from host) as working directory
echo "[docker] Using /src as working directory"
cd /src

# ---------------------------------------------------------------------------
# DEV mode: rebuild package-manager from the mounted /src tree
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Hand off to pkgmgr or arbitrary command
# ---------------------------------------------------------------------------
if [[ $# -eq 0 ]]; then
  echo "[docker] No arguments provided. Showing pkgmgr help..."
  exec pkgmgr --help
else
  echo "[docker] Executing command: $*"
  exec "$@"
fi
