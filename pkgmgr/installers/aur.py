#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for Arch AUR dependencies declared in an `aur.yml` file.

This installer is:
  - Arch-only (requires `pacman`)
  - helper-driven (yay/paru/..)
  - safe to ignore on non-Arch systems

Config parsing errors are treated as fatal to avoid silently ignoring
broken configuration.
"""

import os
import shutil
from typing import List

import yaml

from pkgmgr.installers.base import BaseInstaller
from pkgmgr.context import RepoContext
from pkgmgr.run_command import run_command


AUR_CONFIG_FILENAME = "aur.yml"


class AurInstaller(BaseInstaller):
    """
    Installer for Arch AUR dependencies declared in an `aur.yml` file.
    """

    def _is_arch_like(self) -> bool:
        return shutil.which("pacman") is not None

    def _config_path(self, ctx: RepoContext) -> str:
        return os.path.join(ctx.repo_dir, AUR_CONFIG_FILENAME)

    def _load_config(self, ctx: RepoContext) -> dict:
        """
        Load and validate aur.yml.

        Any parsing error or invalid top-level structure is treated as fatal
        (SystemExit).
        """
        path = self._config_path(ctx)
        if not os.path.exists(path):
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as exc:
            print(f"[Error] Failed to load AUR config from '{path}': {exc}")
            raise SystemExit(f"AUR config '{path}' could not be parsed: {exc}")

        if not isinstance(data, dict):
            print(f"[Error] AUR config '{path}' is not a mapping.")
            raise SystemExit(f"AUR config '{path}' must be a mapping at top level.")

        return data

    def _get_helper(self, cfg: dict) -> str:
        # Priority: config.helper > $AUR_HELPER > "yay"
        helper = cfg.get("helper")
        if isinstance(helper, str) and helper.strip():
            return helper.strip()

        env_helper = os.environ.get("AUR_HELPER")
        if env_helper:
            return env_helper.strip()

        return "yay"

    def _get_packages(self, cfg: dict) -> List[str]:
        raw = cfg.get("packages", [])
        if not isinstance(raw, list):
            return []

        names: List[str] = []
        for entry in raw:
            if isinstance(entry, str):
                name = entry.strip()
                if name:
                    names.append(name)
            elif isinstance(entry, dict):
                name = str(entry.get("name", "")).strip()
                if name:
                    names.append(name)

        return names

    # --- BaseInstaller API -------------------------------------------------

    def supports(self, ctx: RepoContext) -> bool:
        """
        This installer is supported if:
          - We are on an Arch-like system (pacman available),
          - An aur.yml exists,
          - That aur.yml declares at least one package.

        An invalid aur.yml will raise SystemExit during config loading.
        """
        if not self._is_arch_like():
            return False

        cfg = self._load_config(ctx)
        if not cfg:
            return False

        packages = self._get_packages(cfg)
        return len(packages) > 0

    def run(self, ctx: RepoContext) -> None:
        """
        Install AUR packages using the configured helper (default: yay).

        Missing helper is treated as non-fatal (warning), everything else
        that fails in run_command() is fatal.
        """
        if not self._is_arch_like():
            print("AUR installer skipped: not an Arch-like system.")
            return

        cfg = self._load_config(ctx)
        if not cfg:
            print("AUR installer: no valid aur.yml found; skipping.")
            return

        packages = self._get_packages(cfg)
        if not packages:
            print("AUR installer: no AUR packages defined; skipping.")
            return

        helper = self._get_helper(cfg)
        if shutil.which(helper) is None:
            print(
                f"[Warning] AUR helper '{helper}' is not available on PATH. "
                f"Please install it (e.g. via your aur_builder setup). "
                f"Skipping AUR installation."
            )
            return

        pkg_list_str = " ".join(packages)
        print(f"Installing AUR packages via '{helper}': {pkg_list_str}")

        cmd = f"{helper} -S --noconfirm {pkg_list_str}"
        run_command(cmd, preview=ctx.preview)
