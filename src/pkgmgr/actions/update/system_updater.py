#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import platform
import shutil

from pkgmgr.actions.update.os_release import OSReleaseInfo


class SystemUpdater:
    """
    Executes distro-specific system update commands, plus Nix profile upgrades if available.
    """

    def run(self, *, preview: bool) -> None:
        from pkgmgr.core.command.run import run_command

        # Distro-agnostic: Nix profile upgrades (if Nix is present).
        if shutil.which("nix") is not None:
            try:
                run_command("nix profile upgrade '.*'", preview=preview)
            except SystemExit as e:
                print(f"[Warning] 'nix profile upgrade' failed: {e}")

        osr = OSReleaseInfo.load()

        if osr.is_arch_family():
            self._update_arch(preview=preview)
            return

        if osr.is_debian_family():
            self._update_debian(preview=preview)
            return

        if osr.is_fedora_family():
            self._update_fedora(preview=preview)
            return

        distro = osr.pretty_name or platform.platform()
        print(f"[Warning] Unsupported distribution for system update: {distro}")

    def _update_arch(self, *, preview: bool) -> None:
        from pkgmgr.core.command.run import run_command

        yay = shutil.which("yay")
        pacman = shutil.which("pacman")
        sudo = shutil.which("sudo")

        # Prefer yay if available (repo + AUR in one pass).
        # Avoid running yay and pacman afterwards to prevent double update passes.
        if yay and sudo:
            run_command("sudo -u aur_builder yay -Syu --noconfirm", preview=preview)
            return

        if pacman and sudo:
            run_command("sudo pacman -Syu --noconfirm", preview=preview)
            return

        print(
            "[Warning] Cannot update Arch system: missing required tools (sudo/yay/pacman)."
        )

    def _update_debian(self, *, preview: bool) -> None:
        from pkgmgr.core.command.run import run_command

        sudo = shutil.which("sudo")
        apt_get = shutil.which("apt-get")

        if not (sudo and apt_get):
            print(
                "[Warning] Cannot update Debian/Ubuntu system: missing required tools (sudo/apt-get)."
            )
            return

        env = "DEBIAN_FRONTEND=noninteractive"
        run_command(f"sudo {env} apt-get update -y", preview=preview)
        run_command(f"sudo {env} apt-get -y dist-upgrade", preview=preview)

    def _update_fedora(self, *, preview: bool) -> None:
        from pkgmgr.core.command.run import run_command

        sudo = shutil.which("sudo")
        dnf = shutil.which("dnf")
        microdnf = shutil.which("microdnf")

        if not sudo:
            print("[Warning] Cannot update Fedora/RHEL-like system: missing sudo.")
            return

        if dnf:
            run_command("sudo dnf -y upgrade", preview=preview)
            return

        if microdnf:
            run_command("sudo microdnf -y upgrade", preview=preview)
            return

        print("[Warning] Cannot update Fedora/RHEL-like system: missing dnf/microdnf.")
