#!/usr/bin/env bash
set -euo pipefail

echo "[uninstall] Starting pkgmgr uninstall..."

VENV_DIR="${HOME}/.venvs/pkgmgr"

# ------------------------------------------------------------
# Remove virtual environment
# ------------------------------------------------------------
echo "[uninstall] Removing global user virtual environment if it exists..."
if [[ -d "$VENV_DIR" ]]; then
    rm -rf "$VENV_DIR"
    echo "[uninstall] Removed: $VENV_DIR"
else
    echo "[uninstall] No venv found at: $VENV_DIR"
fi

# ------------------------------------------------------------
# Remove auto-activation lines from shell RC files
# ------------------------------------------------------------
# Matches:
#   ~/.venvs/pkgmgr/bin/activate
#   ./.venvs/pkgmgr/bin/activate
RC_PATTERN='(\./)?\.venvs/pkgmgr/bin/activate'

echo "[uninstall] Cleaning up ~/.bashrc and ~/.zshrc entries..."
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [[ -f "$rc" ]]; then
        # Remove activation lines (functional)
        sed -E -i "/$RC_PATTERN/d" "$rc"

        # Remove leftover echo / cosmetic lines referencing pkgmgr venv
        sed -i '/\.venvs\/pkgmgr/d' "$rc"

        echo "[uninstall] Cleaned $rc"
    else
        echo "[uninstall] File not found: $rc (skipped)"
    fi
done

echo "[uninstall] Done. Restart your shell (or run 'exec bash' or 'exec zsh') to apply changes."
