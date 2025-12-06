#!/usr/bin/env bash
set -euo pipefail

# Enable flakes if not already configured.
if [[ -z "${NIX_CONFIG:-}" ]]; then
  export NIX_CONFIG="experimental-features = nix-command flakes"
fi

# Run Kevin’s package manager via Nix flake
exec nix run "github:kevinveenbirkenbach/package-manager#pkgmgr" -- "$@"
