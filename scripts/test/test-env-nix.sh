#!/usr/bin/env bash
set -euo pipefail

IMAGE="pkgmgr-${distro}"

echo "============================================================"
echo ">>> Running Nix flake-only test in ${distro} container"
echo ">>> Image: ${IMAGE}"
echo "============================================================"

docker run --rm \
  -v "$(pwd):/src" \
  -v "pkgmgr_nix_store_${distro}:/nix" \
  -v "pkgmgr_nix_cache_${distro}:/root/.cache/nix" \
  --workdir /src \
  -e REINSTALL_PKGMGR=1 \
  "${IMAGE}" \
  bash -lc '
    set -euo pipefail

    if command -v git >/dev/null 2>&1; then
      git config --global --add safe.directory /src || true
      git config --global --add safe.directory /src/.git || true
      git config --global --add safe.directory "*" || true
    fi

    echo ">>> preflight: nix must exist in image"
    if ! command -v nix >/dev/null 2>&1; then
      echo "NO_NIX"
      echo "ERROR: nix not found in image '\'''"${IMAGE}"''\'' (distro='"${distro}"')"
      echo "HINT: Ensure Nix is installed during image build for this distro."
      exit 1
    fi

    echo ">>> nix version"
    nix --version

    echo ">>> nix flake show"
    nix flake show . --no-write-lock-file >/dev/null

    echo ">>> nix build .#default"
    nix build .#default --no-link --no-write-lock-file

    echo ">>> nix run .#pkgmgr -- --help"
    nix run .#pkgmgr -- --help --no-write-lock-file

    echo ">>> OK: Nix flake-only test succeeded."
  '
