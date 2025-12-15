#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[arch/dependencies] Installing Arch build dependencies..."

pacman -Syu --noconfirm

if ! pacman-key --list-sigs &>/dev/null; then
    echo "[arch/dependencies] Initializing pacman keyring..."
    pacman-key --init
    pacman-key --populate archlinux
fi

pacman -S --noconfirm --needed \
  base-devel \
  git \
  rsync \
  curl \
  ca-certificates \
  python \
  python-pip \
  xz

pacman -Scc --noconfirm

# Always run AUR builder setup for Arch
AUR_SETUP="${SCRIPT_DIR}/aur-builder-setup.sh"

if [[ ! -x "${AUR_SETUP}" ]]; then
  echo "[arch/dependencies] ERROR: AUR builder setup script not found or not executable: ${AUR_SETUP}"
  exit 1
fi

echo "[arch/dependencies] Running AUR builder setup..."
bash "${AUR_SETUP}"

echo "[arch/dependencies] Done."
