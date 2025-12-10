#!/usr/bin/env bash
set -euo pipefail

echo "[init-nix] Starting Nix initialization..."

# ---------------------------------------------------------------------------
# Helper: detect whether we are inside a container (Docker/Podman/etc.)
# ---------------------------------------------------------------------------
is_container() {
  # Docker / Podman markers
  if [[ -f /.dockerenv ]] || [[ -f /run/.containerenv ]]; then
    return 0
  fi

  # cgroup hints
  if grep -qiE 'docker|container|podman|lxc' /proc/1/cgroup 2>/dev/null; then
    return 0
  fi

  # Environment variable used by some runtimes
  if [[ -n "${container:-}" ]]; then
    return 0
  fi

  return 1
}

# ---------------------------------------------------------------------------
# Helper: ensure Nix binaries are on PATH (multi-user or single-user)
# ---------------------------------------------------------------------------
ensure_nix_on_path() {
  # Multi-user profile (daemon install)
  if [[ -x /nix/var/nix/profiles/default/bin/nix ]]; then
    export PATH="/nix/var/nix/profiles/default/bin:${PATH}"
  fi

  # Single-user profile (current user)
  if [[ -x "${HOME}/.nix-profile/bin/nix" ]]; then
    export PATH="${HOME}/.nix-profile/bin:${PATH}"
  fi

  # Single-user profile for dedicated "nix" user (container case)
  if [[ -x /home/nix/.nix-profile/bin/nix ]]; then
    export PATH="/home/nix/.nix-profile/bin:${PATH}"
  fi
}

# ---------------------------------------------------------------------------
# Fast path: Nix already available
# ---------------------------------------------------------------------------
if command -v nix >/dev/null 2>&1; then
  echo "[init-nix] Nix already available on PATH: $(command -v nix)"
  exit 0
fi

ensure_nix_on_path

if command -v nix >/dev/null 2>&1; then
  echo "[init-nix] Nix found after adjusting PATH: $(command -v nix)"
  exit 0
fi

echo "[init-nix] Nix not found, starting installation logic..."

IN_CONTAINER=0
if is_container; then
  IN_CONTAINER=1
  echo "[init-nix] Detected container environment."
else
  echo "[init-nix] No container detected."
fi

# ---------------------------------------------------------------------------
# Container + root: install Nix as dedicated "nix" user (single-user)
# ---------------------------------------------------------------------------
if [[ "${IN_CONTAINER}" -eq 1 && "${EUID:-0}" -eq 0 ]]; then
  echo "[init-nix] Running as root inside a container – using dedicated 'nix' user."

  # Ensure nixbld group (required by Nix)
  if ! getent group nixbld >/dev/null 2>&1; then
    echo "[init-nix] Creating group 'nixbld'..."
    groupadd -r nixbld
  fi

  # Ensure Nix build users (nixbld1..nixbld10) as members of nixbld
  for i in $(seq 1 10); do
    if ! id "nixbld$i" >/dev/null 2>&1; then
      echo "[init-nix] Creating build user nixbld$i..."
      # -r: system account, -g: primary group, -G: supplementary (ensures membership is listed)
      useradd -r -g nixbld -G nixbld -s /usr/sbin/nologin "nixbld$i"
    fi
  done

  # Ensure "nix" user (home at /home/nix)
  if ! id nix >/dev/null 2>&1; then
    echo "[init-nix] Creating user 'nix'..."
    # Resolve a valid shell path across distros:
    # - Debian/Ubuntu: /bin/bash
    # - Arch:          /usr/bin/bash (often symlinked)
    # Fall back to /bin/sh on ultra-minimal systems.
    BASH_SHELL="$(command -v bash || true)"
    if [[ -z "${BASH_SHELL}" ]]; then
      BASH_SHELL="/bin/sh"
    fi
    useradd -m -r -g nixbld -s "${BASH_SHELL}" nix
  fi

  # Ensure /nix exists and is writable by the "nix" user.
  #
  # In some base images (or previous runs), /nix may already exist and be
  # owned by root. In that case the Nix single-user installer will abort with:
  #
  #   "directory /nix exists, but is not writable by you"
  #
  # To keep container runs idempotent and robust, we always enforce
  # ownership nix:nixbld here.
  if [[ ! -d /nix ]]; then
    echo "[init-nix] Creating /nix with owner nix:nixbld..."
    mkdir -m 0755 /nix
    chown nix:nixbld /nix
  else
    current_owner="$(stat -c '%U' /nix 2>/dev/null || echo '?')"
    current_group="$(stat -c '%G' /nix 2>/dev/null || echo '?')"
    if [[ "${current_owner}" != "nix" || "${current_group}" != "nixbld" ]]; then
      echo "[init-nix] /nix already exists with owner ${current_owner}:${current_group} – fixing to nix:nixbld..."
      chown -R nix:nixbld /nix
    else
      echo "[init-nix] /nix already exists with correct owner nix:nixbld."
    fi

    if [[ ! -w /nix ]]; then
      echo "[init-nix] WARNING: /nix is still not writable after chown; Nix installer may fail."
    fi
  fi

  # Run Nix single-user installer as "nix"
  echo "[init-nix] Installing Nix as user 'nix' (single-user, --no-daemon)..."
  if command -v sudo >/dev/null 2>&1; then
    sudo -u nix bash -lc 'sh <(curl -L https://nixos.org/nix/install) --no-daemon'
  else
    su - nix -c 'sh <(curl -L https://nixos.org/nix/install) --no-daemon'
  fi

  # After installation, expose nix to root via PATH and symlink
  ensure_nix_on_path

  if [[ -x /home/nix/.nix-profile/bin/nix ]]; then
    if [[ ! -e /usr/local/bin/nix ]]; then
      echo "[init-nix] Creating /usr/local/bin/nix symlink -> /home/nix/.nix-profile/bin/nix"
      ln -s /home/nix/.nix-profile/bin/nix /usr/local/bin/nix
    fi
  fi

  ensure_nix_on_path

  if command -v nix >/dev/null 2>&1; then
    echo "[init-nix] Nix successfully installed (container mode) at: $(command -v nix)"
  else
    echo "[init-nix] WARNING: Nix installation finished in container, but 'nix' is still not on PATH."
  fi

  # Optionally add PATH hints to /etc/profile (best effort)
  if [[ -w /etc/profile ]]; then
    if ! grep -q 'Nix profiles' /etc/profile 2>/dev/null; then
      cat <<'EOF' >> /etc/profile

# Nix profiles (added by package-manager init-nix.sh)
if [ -d /nix/var/nix/profiles/default/bin ]; then
  PATH="/nix/var/nix/profiles/default/bin:$PATH"
fi
if [ -d "$HOME/.nix-profile/bin" ]; then
  PATH="$HOME/.nix-profile/bin:$PATH"
fi
EOF
      echo "[init-nix] Appended Nix PATH setup to /etc/profile (container mode)."
    fi
  fi

  echo "[init-nix] Nix initialization complete (container root mode)."
  exit 0
fi

# ---------------------------------------------------------------------------
# Non-container or non-root container: normal installer paths
# ---------------------------------------------------------------------------
if [[ "${IN_CONTAINER}" -eq 0 ]]; then
  # Real host
  if command -v systemctl >/dev/null 2>&1; then
    echo "[init-nix] Host with systemd – using multi-user install (--daemon)."
    sh <(curl -L https://nixos.org/nix/install) --daemon
  else
    if [[ "${EUID:-0}" -eq 0 ]]; then
      echo "[init-nix] WARNING: Running as root without systemd on host."
      echo "[init-nix] Falling back to single-user install (--no-daemon), but this is not recommended."
      sh <(curl -L https://nixos.org/nix/install) --no-daemon
    else
      echo "[init-nix] Non-root host without systemd – using single-user install (--no-daemon)."
      sh <(curl -L https://nixos.org/nix/install) --no-daemon
    fi
  fi
else
  # Container, but not root (rare)
  echo "[init-nix] Container as non-root user – using single-user install (--no-daemon)."
  sh <(curl -L https://nixos.org/nix/install) --no-daemon
fi

# ---------------------------------------------------------------------------
# After installation: fix PATH (runtime + shell profiles)
# ---------------------------------------------------------------------------
ensure_nix_on_path

if ! command -v nix >/dev/null 2>&1; then
  echo "[init-nix] WARNING: Nix installation finished, but 'nix' is still not on PATH."
  echo "[init-nix] You may need to source your shell profile manually."
  exit 0
fi

echo "[init-nix] Nix successfully installed at: $(command -v nix)"

# Update global /etc/profile if writable (helps especially on minimal systems)
if [[ -w /etc/profile ]]; then
  if ! grep -q 'Nix profiles' /etc/profile 2>/dev/null; then
    cat <<'EOF' >> /etc/profile

# Nix profiles (added by package-manager init-nix.sh)
if [ -d /nix/var/nix/profiles/default/bin ]; then
  PATH="/nix/var/nix/profiles/default/bin:$PATH"
fi
if [ -d "$HOME/.nix-profile/bin" ]; then
  PATH="$HOME/.nix-profile/bin:$PATH"
fi
EOF
    echo "[init-nix] Appended Nix PATH setup to /etc/profile"
  fi
fi

echo "[init-nix] Nix initialization complete."
