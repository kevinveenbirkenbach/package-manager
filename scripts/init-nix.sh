#!/usr/bin/env bash
set -euo pipefail

echo ">>> Initializing Nix environment for package-manager..."

# 1. /nix store
if [ ! -d /nix ]; then
  echo ">>> Creating /nix store directory"
  mkdir -m 0755 /nix
  chown root:root /nix
fi

# 2. Enable nix-daemon if available
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q nix-daemon.service; then
  echo ">>> Enabling nix-daemon.service"
  systemctl enable --now nix-daemon.service 2>/dev/null || true
else
  echo ">>> Warning: nix-daemon.service not found or systemctl not available."
fi

# 3. Ensure nix-users group
if ! getent group nix-users >/dev/null 2>&1; then
  echo ">>> Creating nix-users group"
  groupadd -r nix-users 2>/dev/null || true
fi

# 4. Add users to nix-users (best-effort)
if command -v loginctl >/dev/null 2>&1; then
  for user in $(loginctl list-users | awk 'NR>1 {print $2}'); do
    if id "$user" >/dev/null 2>&1; then
      echo ">>> Adding user '$user' to nix-users"
      usermod -aG nix-users "$user" 2>/dev/null || true
    fi
  done
elif command -v logname >/dev/null 2>&1; then
  USERNAME="$(logname 2>/dev/null || true)"
  if [ -n "$USERNAME" ] && id "$USERNAME" >/dev/null 2>&1; then
    echo ">>> Adding user '$USERNAME' to nix-users"
    usermod -aG nix-users "$USERNAME" 2>/dev/null || true
  fi
fi

echo ">>> Nix initialization complete."
echo ">>> You may need to log out and log back in to activate group membership."
