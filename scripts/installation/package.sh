#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

OS_ID="$(detect_os_id)"

# Map Manjaro to Arch
if [[ "${OS_ID}" == "manjaro" ]]; then
  echo "[package] Mapping OS 'manjaro' → 'arch'"
  OS_ID="arch"
fi

echo "[package] Detected OS: ${OS_ID}"

case "${OS_ID}" in
  arch|debian|ubuntu|fedora|centos)
    PKG_SCRIPT="${SCRIPT_DIR}/${OS_ID}/package.sh"
    ;;
  *)
    echo "[package] Unsupported OS: ${OS_ID}"
    exit 1
    ;;
esac

if [[ ! -f "${PKG_SCRIPT}" ]]; then
  echo "[package] Package script not found: ${PKG_SCRIPT}"
  exit 1
fi

echo "[package] Executing: ${PKG_SCRIPT}"
exec bash "${PKG_SCRIPT}"
