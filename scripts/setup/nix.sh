#!/usr/bin/env bash

# ------------------------------------------------------------
# Nix shell mode: do not touch venv, only run install
# ------------------------------------------------------------

echo "[setup] Nix mode enabled (NIX_ENABLED=1)."
echo "[setup] Skipping virtualenv creation and dependency installation."
echo "[setup] Running install via system python3..."
python3 -m pkgmgr install
echo "[setup] Setup finished (Nix mode)."
