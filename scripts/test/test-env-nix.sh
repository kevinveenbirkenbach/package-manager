#!/usr/bin/env bash
set -euo pipefail

IMAGE="pkgmgr-${PKGMGR_DISTRO}"

echo "============================================================"
echo ">>> Running Nix flake-only test in ${PKGMGR_DISTRO} container"
echo ">>> Image: ${IMAGE}"
echo "============================================================"

docker run --rm \
  -v "$(pwd):/opt/src/pkgmgr" \
  -v "pkgmgr_nix_store_${PKGMGR_DISTRO}:/nix" \
  -v "pkgmgr_nix_cache_${PKGMGR_DISTRO}:/root/.cache/nix" \
  --workdir /opt/src/pkgmgr \
  -e REINSTALL_PKGMGR=1 \
  "${IMAGE}" \
  bash -lc '
    set -euo pipefail

    if command -v git >/dev/null 2>&1; then
      git config --global --add safe.directory /opt/src/pkgmgr || true
      git config --global --add safe.directory /opt/src/pkgmgr/.git || true
      git config --global --add safe.directory "*" || true
    fi

    echo ">>> preflight: nix must exist in image"
    if ! command -v nix >/dev/null 2>&1; then
      echo "NO_NIX"
      echo "ERROR: nix not found in image '"${IMAGE}"' (PKGMGR_DISTRO='"${PKGMGR_DISTRO}"')"
      echo "HINT: Ensure Nix is installed during image build for this distro."
      exit 1
    fi

    echo ">>> nix version"
    nix --version

    # ------------------------------------------------------------
    # Retry helper for GitHub API rate-limit (HTTP 403)
    # ------------------------------------------------------------
    if [[ -f /opt/src/pkgmgr/scripts/nix/lib/retry_403.sh ]]; then
      # shellcheck source=./scripts/nix/lib/retry_403.sh
      source /opt/src/pkgmgr/scripts/nix/lib/retry_403.sh
    elif [[ -f ./scripts/nix/lib/retry_403.sh ]]; then
      # shellcheck source=./scripts/nix/lib/retry_403.sh
      source ./scripts/nix/lib/retry_403.sh
    else
      echo "ERROR: retry helper not found: scripts/nix/lib/retry_403.sh"
      exit 1
    fi

    echo ">>> nix flake show"
    run_with_github_403_retry nix flake show . --no-write-lock-file >/dev/null

    echo ">>> nix build .#default"
    run_with_github_403_retry nix build .#default --no-link --no-write-lock-file

    echo ">>> nix run .#pkgmgr -- --help"
    run_with_github_403_retry nix run .#pkgmgr -- --help --no-write-lock-file

    echo ">>> OK: Nix flake-only test succeeded."
  '
