#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Iterable

from pkgmgr.actions.update.system_updater import SystemUpdater


class UpdateManager:
    """
    Orchestrates:
      - repository pull + installation
      - optional system update
    """

    def __init__(self) -> None:
        self._system_updater = SystemUpdater()

    def run(
        self,
        selected_repos: Iterable[Any],
        repositories_base_dir: str,
        bin_dir: str,
        all_repos: Any,
        no_verification: bool,
        system_update: bool,
        preview: bool,
        quiet: bool,
        update_dependencies: bool,
        clone_mode: str,
        force_update: bool = True,
    ) -> None:
        from pkgmgr.actions.install import install_repos
        from pkgmgr.actions.repository.pull import pull_with_verification

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
            self._system_updater.run(preview=preview)
