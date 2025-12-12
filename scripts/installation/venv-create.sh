#!/usr/bin/env bash
set -euo pipefail

# venv-create.sh
#
# Create/update a Python virtual environment for pkgmgr and install dependencies.
#
# Priority order:
#  1) pyproject.toml  -> pip install (editable by default)
#  2) requirements.txt
#  3) _requirements.txt (legacy)
#
# Usage:
#   PKGMGR_VENV_DIR=/home/dev/.venvs/pkgmgr bash scripts/installation/venv-create.sh
# or
#   bash scripts/installation/venv-create.sh /home/dev/.venvs/pkgmgr
#
# Optional:
#   PKGMGR_PIP_EDITABLE=0           # install non-editable (default: 1)
#   PKGMGR_PIP_EXTRAS="dev,test"    # install extras: .[dev,test]
#   PKGMGR_PREFER_NIX=1             # print Nix hint and exit non-zero

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${PROJECT_ROOT}"

VENV_DIR="${PKGMGR_VENV_DIR:-${1:-${HOME}/.venvs/pkgmgr}}"
PIP_EDITABLE="${PKGMGR_PIP_EDITABLE:-1}"
PIP_EXTRAS="${PKGMGR_PIP_EXTRAS:-}"
PREFER_NIX="${PKGMGR_PREFER_NIX:-0}"

echo "[venv-create] Using VENV_DIR=${VENV_DIR}"

if [[ "${PREFER_NIX}" == "1" ]]; then
  echo "[venv-create] PKGMGR_PREFER_NIX=1 set."
  echo "[venv-create] Hint: Use Nix instead of a venv for reproducible installs:"
  echo "[venv-create]   nix develop"
  echo "[venv-create]   nix run .#pkgmgr -- --help"
  exit 2
fi

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

# ---------------------------------------------------------------------------
# Install dependencies
# ---------------------------------------------------------------------------
if [[ -f "pyproject.toml" ]]; then
  echo "[venv-create] Detected pyproject.toml. Installing project via pip..."

  target="."
  if [[ -n "${PIP_EXTRAS}" ]]; then
    target=".[${PIP_EXTRAS}]"
  fi

  if [[ "${PIP_EDITABLE}" == "1" ]]; then
    echo "[venv-create] pip install -e ${target}"
    "${VENV_DIR}/bin/pip" install -e "${target}"
  else
    echo "[venv-create] pip install ${target}"
    "${VENV_DIR}/bin/pip" install "${target}"
  fi

elif [[ -f "requirements.txt" ]]; then
  echo "[venv-create] Installing dependencies from requirements.txt..."
  "${VENV_DIR}/bin/pip" install -r requirements.txt

elif [[ -f "_requirements.txt" ]]; then
  echo "[venv-create] Installing dependencies from _requirements.txt (legacy)..."
  "${VENV_DIR}/bin/pip" install -r _requirements.txt

else
  echo "[venv-create] No pyproject.toml, requirements.txt, or _requirements.txt found. Skipping dependency installation."
fi

echo "[venv-create] Done."
