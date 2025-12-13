#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil

from pkgmgr.actions.install import install_repos
from pkgmgr.actions.repository.pull import pull_with_verification


def update_repos(
    selected_repos,
    repositories_base_dir,
    bin_dir,
    all_repos,
    no_verification,
    system_update,
    preview: bool,
    quiet: bool,
    update_dependencies: bool,
    clone_mode: str,
    force_update: bool = True,
) -> None:
    """
    Update repositories by pulling latest changes and installing them.
    """
    pull_with_verification(
        selected_repos,
        repositories_base_dir,
        all_repos,
        [],
        no_verification,
        preview,
    )

    install_repos(
        selected_repos,
        repositories_base_dir,
        bin_dir,
        all_repos,
        no_verification,
        preview,
        quiet,
        clone_mode,
        update_dependencies,
        force_update=force_update,
    )

    if system_update:
        from pkgmgr.core.command.run import run_command

        if shutil.which("nix") is not None:
            try:
                run_command("nix profile upgrade '.*'", preview=preview)
            except SystemExit as e:
                print(f"[Warning] 'nix profile upgrade' failed: {e}")

        run_command("sudo -u aur_builder yay -Syu --noconfirm", preview=preview)
        run_command("sudo pacman -Syyu --noconfirm", preview=preview)
