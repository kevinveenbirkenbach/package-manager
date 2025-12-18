#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Iterable, List, Tuple

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
        silent: bool = False,
        force_update: bool = True,
    ) -> None:
        from pkgmgr.actions.install import install_repos
        from pkgmgr.actions.repository.pull import pull_with_verification
        from pkgmgr.core.repository.identifier import get_repo_identifier

        failures: List[Tuple[str, str]] = []

        for repo in list(selected_repos):
            identifier = get_repo_identifier(repo, all_repos)

            try:
                pull_with_verification(
                    [repo],
                    repositories_base_dir,
                    all_repos,
                    [],
                    no_verification,
                    preview,
                )
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else str(exc.code)
                failures.append((identifier, f"pull failed (exit={code})"))
                if not quiet:
                    print(
                        f"[Warning] update: pull failed for {identifier} (exit={code}). Continuing..."
                    )
                continue
            except Exception as exc:
                failures.append((identifier, f"pull failed: {exc}"))
                if not quiet:
                    print(
                        f"[Warning] update: pull failed for {identifier}: {exc}. Continuing..."
                    )
                continue

            try:
                install_repos(
                    [repo],
                    repositories_base_dir,
                    bin_dir,
                    all_repos,
                    no_verification,
                    preview,
                    quiet,
                    clone_mode,
                    update_dependencies,
                    force_update=force_update,
                    silent=silent,
                    emit_summary=False,
                )
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else str(exc.code)
                failures.append((identifier, f"install failed (exit={code})"))
                if not quiet:
                    print(
                        f"[Warning] update: install failed for {identifier} (exit={code}). Continuing..."
                    )
                continue
            except Exception as exc:
                failures.append((identifier, f"install failed: {exc}"))
                if not quiet:
                    print(
                        f"[Warning] update: install failed for {identifier}: {exc}. Continuing..."
                    )
                continue

        if failures and not quiet:
            print("\n[pkgmgr] Update finished with warnings:")
            for ident, msg in failures:
                print(f"  - {ident}: {msg}")

        if failures and not silent:
            raise SystemExit(1)

        if system_update:
            self._system_updater.run(preview=preview)
