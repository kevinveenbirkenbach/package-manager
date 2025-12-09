#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# aur-builder-setup.sh
#
# Setup helper for an 'aur_builder' user and yay on Arch-based
# systems. Intended for host usage and can also be used in
# containers if desired.
# ------------------------------------------------------------

echo "[aur-builder-setup] Checking for pacman..."
if ! command -v pacman >/dev/null 2>&1; then
  echo "[aur-builder-setup] pacman not found – this is not an Arch-based system. Skipping."
  exit 0
fi

if [[ "${EUID:-0}" -ne 0 ]]; then
  ROOT_CMD="sudo"
else
  ROOT_CMD=""
fi

echo "[aur-builder-setup] Installing base-devel, git, sudo..."
${ROOT_CMD} pacman -Syu --noconfirm
${ROOT_CMD} pacman -S --needed --noconfirm base-devel git sudo

echo "[aur-builder-setup] Ensuring aur_builder group/user..."
if ! getent group aur_builder >/dev/null 2>&1; then
  ${ROOT_CMD} groupadd -r aur_builder
fi

if ! id -u aur_builder >/dev/null 2>&1; then
  ${ROOT_CMD} useradd -m -r -g aur_builder -s /bin/bash aur_builder
fi

echo "[aur-builder-setup] Configuring sudoers for aur_builder..."
${ROOT_CMD} bash -c "echo '%aur_builder ALL=(ALL) NOPASSWD: /usr/bin/pacman' > /etc/sudoers.d/aur_builder"
${ROOT_CMD} chmod 0440 /etc/sudoers.d/aur_builder

if command -v sudo >/dev/null 2>&1; then
  RUN_AS_AUR=(sudo -u aur_builder bash -lc)
else
  RUN_AS_AUR=(su - aur_builder -c)
fi

echo "[aur-builder-setup] Ensuring yay is installed for aur_builder..."
if ! "${RUN_AS_AUR[@]}" 'command -v yay >/dev/null 2>&1'; then
  "${RUN_AS_AUR[@]}" 'cd ~ && rm -rf yay && git clone https://aur.archlinux.org/yay.git && cd yay && makepkg -si --noconfirm'
else
  echo "[aur-builder-setup] yay already installed."
fi

echo "[aur-builder-setup] Done."
