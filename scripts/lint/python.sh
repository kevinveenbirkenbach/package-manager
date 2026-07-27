#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo ">>> Running RUFF lint on src and tests (local, no container)"
echo "============================================================"

if ! command -v ruff >/dev/null 2>&1; then
  echo "ruff is not installed or not on PATH." >&2
  echo "Install it with: pip install ruff" >&2
  exit 127
fi

ruff --version
ruff check src tests
