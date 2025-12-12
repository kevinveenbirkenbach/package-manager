#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib.sh"

OS_ID="$(detect_os_id)"

echo "[run-dependencies] Detected OS: ${OS_ID}"

case "${OS_ID}" in
  arch|debian|ubuntu|fedora|centos)
    DEP_SCRIPT="${SCRIPT_DIR}/${OS_ID}/dependencies.sh"
    ;;
  *)
    echo "[run-dependencies] Unsupported OS: ${OS_ID}"
    exit 1
    ;;
esac

if [[ ! -f "${DEP_SCRIPT}" ]]; then
  echo "[run-dependencies] Dependency script not found: ${DEP_SCRIPT}"
  exit 1
fi

echo "[run-dependencies] Executing: ${DEP_SCRIPT}"
exec bash "${DEP_SCRIPT}"
