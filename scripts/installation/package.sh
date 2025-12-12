#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/os_resolver.sh"

OS_ID="$(osr_get_os_id)"

echo "[package] Detected OS: ${OS_ID}"

if ! osr_is_supported "${OS_ID}"; then
  echo "[package] Unsupported OS: ${OS_ID}"
  exit 1
fi

PKG_SCRIPT="$(osr_script_path_for "${SCRIPT_DIR}" "${OS_ID}" "package")"

if [[ ! -f "${PKG_SCRIPT}" ]]; then
  echo "[package] Package script not found: ${PKG_SCRIPT}"
  exit 1
fi

echo "[package] Executing: ${PKG_SCRIPT}"
exec bash "${PKG_SCRIPT}"
