#!/usr/bin/env bash

# Prevent double-sourcing
if [[ -n "${PKGMGR_NIX_CONFIG_SH:-}" ]]; then
  return 0
fi
PKGMGR_NIX_CONFIG_SH=1

NIX_INSTALL_URL="${NIX_INSTALL_URL:-https://nixos.org/nix/install}"
NIX_DOWNLOAD_MAX_TIME="${NIX_DOWNLOAD_MAX_TIME:-300}"
NIX_DOWNLOAD_SLEEP_INTERVAL="${NIX_DOWNLOAD_SLEEP_INTERVAL:-20}"
