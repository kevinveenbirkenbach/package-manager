#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# main.sh
#
# Developer / system setup entrypoint.
#
# Responsibilities:
#   - If inside a Nix shell (IN_NIX_SHELL=1):
#       * Skip venv creation and dependency installation
#       * Run `python3 main.py install`
#   - If running as root (EUID=0):
#       * Run system-level installer (run-package.sh)
#   - Otherwise (normal user):
#       * Create ~/.venvs/pkgmgr virtual environment if missing
#       * Install Python dependencies into that venv
#       * Append auto-activation to ~/.bashrc and ~/.zshrc
#       * Run `main.py install` using the venv Python
# ------------------------------------------------------------

echo "[installation/main] Starting setup..."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${PROJECT_ROOT}"

VENV_DIR="${HOME}/.venvs/pkgmgr"
RC_LINE='if [ -d "${HOME}/.venvs/pkgmgr" ]; then . "${HOME}/.venvs/pkgmgr/bin/activate"; if [ -n "${PS1:-}" ]; then echo "Global Python virtual environment '\''~/.venvs/pkgmgr'\'' activated."; fi; fi'

# ------------------------------------------------------------
# 1) Nix shell mode: do not touch venv, only run main.py install
# ------------------------------------------------------------
if [[ -n "${IN_NIX_SHELL:-}" ]]; then
    echo "[installation/main] Nix shell detected (IN_NIX_SHELL=1)."
    echo "[installation/main] Skipping virtualenv creation and dependency installation."
    echo "[installation/main] Running main.py install via system python3..."
    python3 main.py install
    echo "[installation/main] Setup finished (Nix mode)."
    exit 0
fi

# ------------------------------------------------------------
# 2) Root mode: system / distro-level installation
# ------------------------------------------------------------
if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    echo "[installation/main] Running as root (EUID=0)."
    echo "[installation/main] Skipping user virtualenv and shell RC modifications."
    echo "[installation/main] Delegating to scripts/installation/run-package.sh..."
    bash scripts/installation/run-package.sh
    echo "[installation/main] Root/system setup complete."
    exit 0
fi

# ------------------------------------------------------------
# 3) Normal user mode: dev setup with venv
# ------------------------------------------------------------

echo "[installation/main] Running in normal user mode (developer setup)."

echo "[installation/main] Ensuring main.py is executable..."
chmod +x main.py || true

echo "[installation/main] Ensuring global virtualenv root: ${HOME}/.venvs"
mkdir -p "${HOME}/.venvs"

echo "[installation/main] Creating/updating virtualenv via helper..."
PKGMGR_VENV_DIR="${VENV_DIR}" bash scripts/installation/venv-create.sh

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
