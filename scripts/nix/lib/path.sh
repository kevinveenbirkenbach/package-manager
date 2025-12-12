#!/usr/bin/env bash

if [[ -n "${PKGMGR_NIX_PATH_SH:-}" ]]; then
  return 0
fi
PKGMGR_NIX_PATH_SH=1

# Ensure Nix binaries are on PATH (additive, never destructive)
ensure_nix_on_path() {
  if [[ -x /nix/var/nix/profiles/default/bin/nix ]]; then
    PATH="/nix/var/nix/profiles/default/bin:$PATH"
  fi
  if [[ -x "$HOME/.nix-profile/bin/nix" ]]; then
    PATH="$HOME/.nix-profile/bin:$PATH"
  fi
  if [[ -x /home/nix/.nix-profile/bin/nix ]]; then
    PATH="/home/nix/.nix-profile/bin:$PATH"
  fi
  if [[ -d "$HOME/.local/bin" ]]; then
    PATH="$HOME/.local/bin:$PATH"
  fi
  export PATH
}

# Resolve a path to a real executable (follows symlinks)
real_exe() {
  local p="${1:-}"
  [[ -z "$p" ]] && return 1

  local r
  r="$(readlink -f "$p" 2>/dev/null || echo "$p")"

  [[ -x "$r" ]] && { echo "$r"; return 0; }
  return 1
}

# Resolve nix binary path robustly (works across distros + Arch /usr/sbin)
resolve_nix_bin() {
  local nix_cmd=""
  nix_cmd="$(command -v nix 2>/dev/null || true)"
  [[ -n "$nix_cmd" ]] && real_exe "$nix_cmd" && return 0

  # IMPORTANT: prefer system locations before /usr/local to avoid self-symlink traps
  [[ -x /usr/sbin/nix ]]      && { echo "/usr/sbin/nix"; return 0; } # Arch package can land here
  [[ -x /usr/bin/nix ]]       && { echo "/usr/bin/nix"; return 0; }
  [[ -x /bin/nix ]]           && { echo "/bin/nix"; return 0; }

  # /usr/local last, and only if it resolves to a real executable
  [[ -e /usr/local/bin/nix ]] && real_exe "/usr/local/bin/nix" && return 0

  [[ -x /nix/var/nix/profiles/default/bin/nix ]] && {
    echo "/nix/var/nix/profiles/default/bin/nix"; return 0;
  }

  [[ -x "$HOME/.nix-profile/bin/nix" ]] && {
    echo "$HOME/.nix-profile/bin/nix"; return 0;
  }

  [[ -x "$HOME/.local/bin/nix" ]] && {
    echo "$HOME/.local/bin/nix"; return 0;
  }

  [[ -x /home/nix/.nix-profile/bin/nix ]] && {
    echo "/home/nix/.nix-profile/bin/nix"; return 0;
  }

  return 1
}
