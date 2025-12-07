#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${NIX_CONFIG:-}" ]]; then
  export NIX_CONFIG="experimental-features = nix-command flakes"
fi

FLAKE_DIR="/usr/lib/package-manager"

exec nix run "${FLAKE_DIR}#pkgmgr" -- "$@"
