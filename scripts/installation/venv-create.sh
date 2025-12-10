#!/usr/bin/env bash
set -euo pipefail

# venv-create.sh
#
# Small helper to create/update a Python virtual environment for pkgmgr.
#
# Usage:
#   PKGMGR_VENV_DIR=/home/dev/.venvs/pkgmgr bash scripts/installation/venv-create.sh
# or
#   bash scripts/installation/venv-create.sh /home/dev/.venvs/pkgmgr

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${PROJECT_ROOT}"

VENV_DIR="${PKGMGR_VENV_DIR:-${1:-${HOME}/.venvs/pkgmgr}}"

echo "[venv-create] Using VENV_DIR=${VENV_DIR}"

echo "[venv-create] Ensuring virtualenv parent directory exists..."
mkdir -p "$(dirname "${VENV_DIR}")"

if [[ ! -d "${VENV_DIR}" ]]; then
    echo "[venv-create] Creating virtual environment at: ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
else
    echo "[venv-create] Virtual environment already exists at: ${VENV_DIR}"
fi

echo "[venv-create] Installing Python tooling into venv..."
"${VENV_DIR}/bin/python" -m ensurepip --upgrade
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel

if [[ -f "requirements.txt" ]]; then
    echo "[venv-create] Installing dependencies from requirements.txt..."
    "${VENV_DIR}/bin/pip" install -r requirements.txt
elif [[ -f "_requirements.txt" ]]; then
    echo "[venv-create] Installing dependencies from _requirements.txt..."
    "${VENV_DIR}/bin/pip" install -r _requirements.txt
else
    echo "[venv-create] No requirements.txt or _requirements.txt found. Skipping dependency installation."
fi

echo "[venv-create] Done."
