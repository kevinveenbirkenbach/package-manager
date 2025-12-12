#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/os_resolver.sh"

OS_ID="$(osr_get_os_id)"

echo "[run-dependencies] Detected OS: ${OS_ID}"

if ! osr_is_supported "${OS_ID}"; then
  echo "[run-dependencies] Unsupported OS: ${OS_ID}"
  exit 1
fi

DEP_SCRIPT="$(osr_script_path_for "${SCRIPT_DIR}" "${OS_ID}" "dependencies")"

if [[ ! -f "${DEP_SCRIPT}" ]]; then
  echo "[run-dependencies] Dependency script not found: ${DEP_SCRIPT}"
  exit 1
fi

echo "[run-dependencies] Executing: ${DEP_SCRIPT}"
exec bash "${DEP_SCRIPT}"
