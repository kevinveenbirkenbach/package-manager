#!/usr/bin/env bash
set -euo pipefail

echo ">>> Running E2E tests in all distros: $DISTROS"

for distro in $DISTROS; do
  echo "============================================================"
  echo ">>> Running E2E tests: $distro"
  echo "============================================================"

  MOUNT_NIX=""
  if [[ "$distro" == "arch" ]]; then
    MOUNT_NIX="-v pkgmgr_nix_store:/nix"
  fi

  docker run --rm \
    -v "$(pwd):/src" \
    $MOUNT_NIX \
    -v "pkgmgr_nix_cache:/root/.cache/nix" \
    -e PKGMGR_DEV=1 \
    --workdir /src \
    --entrypoint bash \
    "package-manager-test-$distro" \
    -c '
      set -e;

      if [ -f /etc/os-release ]; then
        . /etc/os-release;
      fi;

      echo "Running tests inside distro: $ID";

      # Try to load nix environment
      if [ -f "/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh" ]; then
        . "/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh";
      fi

      if [ -f "$HOME/.nix-profile/etc/profile.d/nix.sh" ]; then
        . "$HOME/.nix-profile/etc/profile.d/nix.sh";
      fi

      PATH="/nix/var/nix/profiles/default/bin:$HOME/.nix-profile/bin:$PATH";

      command -v nix >/dev/null || {
        echo "ERROR: nix not found.";
        exit 1;
      }

      git config --global --add safe.directory /src || true;

      nix develop .#default --no-write-lock-file -c \
        python3 -m unittest discover \
          -s /src/tests/e2e \
          -p "test_*.py";
    '
done
