# ------------------------------------------------------------
# Nix shell mode: do not touch venv, only run main.py install
# ------------------------------------------------------------

echo "[setup] Nix mode enabled (NIX_ENABLED=1)."
echo "[setup] Skipping virtualenv creation and dependency installation."
echo "[setup] Running main.py install via system python3..."
python3 main.py install
echo "[setup] Setup finished (Nix mode)."
