#!/usr/bin/env bash
set -euo pipefail

echo ">>> Running E2E tests in all distros: $DISTROS"

for distro in $DISTROS; do
  echo "============================================================"
  echo ">>> Running E2E tests: $distro"
  echo "============================================================"

  docker run --rm \
    -v "$(pwd):/src" \
    -v "pkgmgr_nix_store_${distro}:/nix" \
    -v "pkgmgr_nix_cache_${distro}:/root/.cache/nix" \
    -e PKGMGR_DEV=1 \
    -e TEST_PATTERN="${TEST_PATTERN}" \
    --workdir /src \
    --entrypoint bash \
    "package-manager-test-${distro}" \
    -c '
      set -euo pipefail

      # Load distro info
      if [ -f /etc/os-release ]; then
        . /etc/os-release
      fi

      echo "Running tests inside distro: ${ID:-unknown}"

      # Load Nix environment if available
      if [ -f "/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh" ]; then
        . "/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh"
      fi

      if [ -f "$HOME/.nix-profile/etc/profile.d/nix.sh" ]; then
        . "$HOME/.nix-profile/etc/profile.d/nix.sh"
      fi

      PATH="/nix/var/nix/profiles/default/bin:$HOME/.nix-profile/bin:$PATH"

      command -v nix >/dev/null || {
        echo "ERROR: nix not found."
        exit 1
      }

      # Mark the mounted repository as safe to avoid Git ownership errors
      if command -v git >/dev/null 2>&1; then
        git config --global --add safe.directory /src || true
      fi

      # Run the E2E tests inside the Nix development shell
      nix develop .#default --no-write-lock-file -c \
        python3 -m unittest discover \
          -s /src/tests/e2e \
          -p "$TEST_PATTERN"
    '
done
