#!/usr/bin/env bash

if [[ -n "${PKGMGR_NIX_SYMLINKS_SH:-}" ]]; then
  return 0
fi
PKGMGR_NIX_SYMLINKS_SH=1

# Requires: real_exe, resolve_nix_bin
# shellcheck disable=SC2034

# Ensure globally reachable nix symlink(s) (CI / non-login shells) - root only
ensure_global_nix_symlinks() {
  local nix_bin="${1:-}"

  [[ -z "$nix_bin" ]] && nix_bin="$(resolve_nix_bin 2>/dev/null || true)"

  if [[ -z "$nix_bin" || ! -x "$nix_bin" ]]; then
    echo "[init-nix] WARNING: nix binary not found, cannot create global symlink(s)."
    return 0
  fi

  # Always link to the real executable to avoid /usr/local/bin/nix -> /usr/local/bin/nix
  nix_bin="$(real_exe "$nix_bin" 2>/dev/null || echo "$nix_bin")"

  local targets=()

  # Always provide /usr/local/bin/nix for CI shells
  mkdir -p /usr/local/bin 2>/dev/null || true
  targets+=("/usr/local/bin/nix")

  # Provide sudo-friendly locations only if they are NOT present (do not override distro paths)
  if [[ ! -e /usr/bin/nix ]]; then
    targets+=("/usr/bin/nix")
  fi
  if [[ ! -e /usr/sbin/nix ]]; then
    targets+=("/usr/sbin/nix")
  fi

  local target current_real
  for target in "${targets[@]}"; do
    current_real=""
    if [[ -e "$target" ]]; then
      current_real="$(real_exe "$target" 2>/dev/null || true)"
    fi

    if [[ -n "$current_real" && "$current_real" == "$nix_bin" ]]; then
      echo "[init-nix] $target already points to: $nix_bin"
      continue
    fi

    # If something exists but is not the same (and we promised not to override), skip.
    if [[ -e "$target" && "$target" != "/usr/local/bin/nix" ]]; then
      echo "[init-nix] WARNING: $target exists; not overwriting."
      continue
    fi

    if ln -sf "$nix_bin" "$target" 2>/dev/null; then
      echo "[init-nix] Ensured $target -> $nix_bin"
    else
      echo "[init-nix] WARNING: Failed to ensure $target symlink."
    fi
  done
}

# Ensure user-level nix symlink (works without root; CI-safe)
ensure_user_nix_symlink() {
  local nix_bin="${1:-}"

  [[ -z "$nix_bin" ]] && nix_bin="$(resolve_nix_bin 2>/dev/null || true)"

  if [[ -z "$nix_bin" || ! -x "$nix_bin" ]]; then
    echo "[init-nix] WARNING: nix binary not found, cannot create user symlink."
    return 0
  fi

  nix_bin="$(real_exe "$nix_bin" 2>/dev/null || echo "$nix_bin")"

  mkdir -p "$HOME/.local/bin" 2>/dev/null || true
  ln -sf "$nix_bin" "$HOME/.local/bin/nix"

  echo "[init-nix] Ensured $HOME/.local/bin/nix -> $nix_bin"

  PATH="$HOME/.local/bin:$PATH"
  export PATH

  if [[ -w "$HOME/.profile" ]] && ! grep -q 'nix/init.sh' "$HOME/.profile" 2>/dev/null; then
    cat >>"$HOME/.profile" <<'EOF'

# PATH for nix (added by package-manager nix/init.sh)
if [ -d "$HOME/.local/bin" ]; then
  PATH="$HOME/.local/bin:$PATH"
fi
EOF
  fi
}
