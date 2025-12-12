#!/usr/bin/env bash
set -euo pipefail

echo "[setup] Starting setup..."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${PROJECT_ROOT}"

VENV_DIR="${HOME}/.venvs/pkgmgr"
RC_LINE='if [ -d "${HOME}/.venvs/pkgmgr" ]; then . "${HOME}/.venvs/pkgmgr/bin/activate"; if [ -n "${PS1:-}" ]; then echo "Global Python virtual environment '\''~/.venvs/pkgmgr'\'' activated."; fi; fi'

# ------------------------------------------------------------
# Normal user mode: dev setup with venv
# ------------------------------------------------------------

echo "[setup] Running in normal user mode (developer setup)."

echo "[setup] Ensuring main.py is executable..."
chmod +x main.py || true

echo "[setup] Ensuring global virtualenv root: ${HOME}/.venvs"
mkdir -p "${HOME}/.venvs"

echo "[setup] Creating/updating virtualenv via helper..."
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${PROJECT_ROOT}"

PIP_EDITABLE="${PKGMGR_PIP_EDITABLE:-1}"
PIP_EXTRAS="${PKGMGR_PIP_EXTRAS:-}"
PREFER_NIX="${PKGMGR_PREFER_NIX:-0}"

echo "[venv] Using VENV_DIR=${VENV_DIR}"

if [[ "${PREFER_NIX}" == "1" ]]; then
  echo "[venv] PKGMGR_PREFER_NIX=1 set."
  echo "[venv] Hint: Use Nix instead of a venv for reproducible installs:"
  echo "[venv]   nix develop"
  echo "[venv]   nix run .#pkgmgr -- --help"
  exit 2
fi

echo "[venv] Ensuring virtualenv parent directory exists..."
mkdir -p "$(dirname "${VENV_DIR}")"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "[venv] Creating virtual environment at: ${VENV_DIR}"
  python3 -m venv "${VENV_DIR}"
else
  echo "[venv] Virtual environment already exists at: ${VENV_DIR}"
fi

echo "[venv] Installing Python tooling into venv..."
"${VENV_DIR}/bin/python" -m ensurepip --upgrade
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel

# ---------------------------------------------------------------------------
# Install dependencies
# ---------------------------------------------------------------------------
if [[ -f "pyproject.toml" ]]; then
  echo "[venv] Detected pyproject.toml. Installing project via pip..."

  target="."
  if [[ -n "${PIP_EXTRAS}" ]]; then
    target=".[${PIP_EXTRAS}]"
  fi

  if [[ "${PIP_EDITABLE}" == "1" ]]; then
    echo "[venv] pip install -e ${target}"
    "${VENV_DIR}/bin/pip" install -e "${target}"
  else
    echo "[venv] pip install ${target}"
    "${VENV_DIR}/bin/pip" install "${target}"
  fi
else
  echo "[venv] No pyproject.toml found. Skipping dependency installation."
fi

echo "[venv] Done."

echo "[setup] Ensuring ~/.bashrc and ~/.zshrc exist..."
touch "${HOME}/.bashrc" "${HOME}/.zshrc"

echo "[setup] Ensuring venv auto-activation is present in shell rc files..."
for rc in "${HOME}/.bashrc" "${HOME}/.zshrc"; do
    if ! grep -qxF "${RC_LINE}" "$rc"; then
        echo "${RC_LINE}" >> "$rc"
        echo "[setup] Appended auto-activation to $rc"
    else
        echo "[setup] Auto-activation already present in $rc"
    fi
done

echo "[setup] Running main.py install via venv Python..."
"${VENV_DIR}/bin/python" main.py install

echo
echo "[setup] Developer setup complete."
echo "Restart your shell (or run 'exec bash' or 'exec zsh') to activate the environment."