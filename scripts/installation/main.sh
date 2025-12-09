#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# main.sh
#
# Developer setup entrypoint.
#
# Responsibilities:
#   - If inside a Nix shell (IN_NIX_SHELL=1):
#       * Skip venv creation and dependency installation
#       * Run `python3 main.py install`
#   - Otherwise:
#       * Create ~/.venvs/pkgmgr virtual environment if missing
#       * Install Python dependencies into that venv
#       * Append auto-activation to ~/.bashrc and ~/.zshrc
#       * Run `main.py install` using the venv Python
# ------------------------------------------------------------

echo "[installation/main] Starting developer setup..."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${PROJECT_ROOT}"

VENV_DIR="${HOME}/.venvs/pkgmgr"
RC_LINE='if [ -d "${HOME}/.venvs/pkgmgr" ]; then . "${HOME}/.venvs/pkgmgr/bin/activate"; if [ -n "${PS1:-}" ]; then echo "Global Python virtual environment '\''~/.venvs/pkgmgr'\'' activated."; fi; fi'

# ------------------------------------------------------------
# Nix shell mode: do not touch venv, only run main.py install
# ------------------------------------------------------------
if [[ -n "${IN_NIX_SHELL:-}" ]]; then
    echo "[installation/main] Nix shell detected (IN_NIX_SHELL=1)."
    echo "[installation/main] Skipping virtualenv creation and dependency installation."
    echo "[installation/main] Running main.py install via system python3..."
    python3 main.py install
    echo "[installation/main] Developer setup finished (Nix mode)."
    exit 0
fi

# ------------------------------------------------------------
# Normal host mode: create/update venv and run main.py install
# ------------------------------------------------------------

echo "[installation/main] Ensuring main.py is executable..."
chmod +x main.py || true

echo "[installation/main] Ensuring global virtualenv root: ${HOME}/.venvs"
mkdir -p "${HOME}/.venvs"

if [[ ! -d "${VENV_DIR}" ]]; then
    echo "[installation/main] Creating virtual environment at: ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
else
    echo "[installation/main] Virtual environment already exists at: ${VENV_DIR}"
fi

echo "[installation/main] Installing Python tooling into venv..."
"${VENV_DIR}/bin/python" -m ensurepip --upgrade
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel

if [[ -f "requirements.txt" ]]; then
    echo "[installation/main] Installing dependencies from requirements.txt..."
    "${VENV_DIR}/bin/pip" install -r requirements.txt
elif [[ -f "_requirements.txt" ]]; then
    echo "[installation/main] Installing dependencies from _requirements.txt..."
    "${VENV_DIR}/bin/pip" install -r _requirements.txt
else
    echo "[installation/main] No requirements.txt or _requirements.txt found. Skipping dependency installation."
fi

echo "[installation/main] Ensuring ~/.bashrc and ~/.zshrc exist..."
touch "${HOME}/.bashrc" "${HOME}/.zshrc"

echo "[installation/main] Ensuring venv auto-activation is present in shell rc files..."
for rc in "${HOME}/.bashrc" "${HOME}/.zshrc"; do
    if ! grep -qxF "${RC_LINE}" "$rc"; then
        echo "${RC_LINE}" >> "$rc"
        echo "[installation/main] Appended auto-activation to $rc"
    else
        echo "[installation/main] Auto-activation already present in $rc"
    fi
done

echo "[installation/main] Running main.py install via venv Python..."
"${VENV_DIR}/bin/python" main.py install

echo
echo "[installation/main] Developer setup complete."
echo "Restart your shell (or run 'exec bash' or 'exec zsh') to activate the environment."
