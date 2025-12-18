# src/pkgmgr/actions/install/__init__.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
High-level entry point for repository installation.

Responsibilities:

  - Ensure the repository directory exists (clone if necessary).
  - Verify the repository (GPG / commit checks).
  - Build a RepoContext object.
  - Delegate the actual installation decision logic to InstallationPipeline.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.verify import verify_repository
from pkgmgr.actions.repository.clone import clone_repos
from pkgmgr.actions.install.context import RepoContext
from pkgmgr.actions.install.installers.os_packages import (
    ArchPkgbuildInstaller,
    DebianControlInstaller,
    RpmSpecInstaller,
)
from pkgmgr.actions.install.installers.nix import (
    NixFlakeInstaller,
)
from pkgmgr.actions.install.installers.python import PythonInstaller
from pkgmgr.actions.install.installers.makefile import (
    MakefileInstaller,
)
from pkgmgr.actions.install.pipeline import InstallationPipeline

Repository = Dict[str, Any]

INSTALLERS = [
    ArchPkgbuildInstaller(),
    DebianControlInstaller(),
    RpmSpecInstaller(),
    NixFlakeInstaller(),
    PythonInstaller(),
    MakefileInstaller(),
]


def _ensure_repo_dir(
    repo: Repository,
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool,
    no_verification: bool,
    clone_mode: str,
    identifier: str,
) -> Optional[str]:
    """
    Compute and, if necessary, clone the repository directory.

    Returns the absolute repository path or None if cloning ultimately failed.
    """
    repo_dir = get_repo_dir(repositories_base_dir, repo)

    if not os.path.exists(repo_dir):
        print(f"Repository directory '{repo_dir}' does not exist. Cloning it now...")
        clone_repos(
            [repo],
            repositories_base_dir,
            all_repos,
            preview,
            no_verification,
            clone_mode,
        )
        if not os.path.exists(repo_dir):
            print(f"Cloning failed for repository {identifier}. Skipping installation.")
            return None

    return repo_dir


def _verify_repo(
    repo: Repository,
    repo_dir: str,
    no_verification: bool,
    identifier: str,
    silent: bool,
) -> bool:
    """
    Verify a repository using the configured verification data.

    Returns True if verification is considered okay and installation may continue.
    """
    verified_info = repo.get("verified")
    verified_ok, errors, _commit_hash, _signing_key = verify_repository(
        repo,
        repo_dir,
        mode="local",
        no_verification=no_verification,
    )

    if not no_verification and verified_info and not verified_ok:
        print(f"Warning: Verification failed for {identifier}:")
        for err in errors:
            print(f"  - {err}")

        if silent:
            # Non-interactive mode: continue with a warning.
            print(
                f"[Warning] Continuing despite verification failure for {identifier} (--silent)."
            )
        else:
            choice = input("Continue anyway? [y/N]: ").strip().lower()
            if choice != "y":
                print(f"Skipping installation for {identifier}.")
                return False

    return True


def _create_context(
    repo: Repository,
    identifier: str,
    repo_dir: str,
    repositories_base_dir: str,
    bin_dir: str,
    all_repos: List[Repository],
    no_verification: bool,
    preview: bool,
    quiet: bool,
    clone_mode: str,
    update_dependencies: bool,
    force_update: bool,
) -> RepoContext:
    """
    Build a RepoContext instance for the given repository.
    """
    return RepoContext(
        repo=repo,
        identifier=identifier,
        repo_dir=repo_dir,
        repositories_base_dir=repositories_base_dir,
        bin_dir=bin_dir,
        all_repos=all_repos,
        no_verification=no_verification,
        preview=preview,
        quiet=quiet,
        clone_mode=clone_mode,
        update_dependencies=update_dependencies,
        force_update=force_update,
    )


def install_repos(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    bin_dir: str,
    all_repos: List[Repository],
    no_verification: bool,
    preview: bool,
    quiet: bool,
    clone_mode: str,
    update_dependencies: bool,
    force_update: bool = False,
    silent: bool = False,
    emit_summary: bool = True,
) -> None:
    """
    Install one or more repositories according to the configured installers
    and the CLI layer precedence rules.

    If force_update=True, installers of the currently active layer are allowed
    to run again (upgrade/refresh), even if that layer is already loaded.

    If silent=True, repository failures are downgraded to warnings and the
    overall command never exits non-zero because of per-repository failures.
    """
    pipeline = InstallationPipeline(INSTALLERS)
    failures: List[Tuple[str, str]] = []

    for repo in selected_repos:
        identifier = get_repo_identifier(repo, all_repos)

        try:
            repo_dir = _ensure_repo_dir(
                repo=repo,
                repositories_base_dir=repositories_base_dir,
                all_repos=all_repos,
                preview=preview,
                no_verification=no_verification,
                clone_mode=clone_mode,
                identifier=identifier,
            )
            if not repo_dir:
                failures.append((identifier, "clone/ensure repo directory failed"))
                continue

            if not _verify_repo(
                repo=repo,
                repo_dir=repo_dir,
                no_verification=no_verification,
                identifier=identifier,
                silent=silent,
            ):
                continue

            ctx = _create_context(
                repo=repo,
                identifier=identifier,
                repo_dir=repo_dir,
                repositories_base_dir=repositories_base_dir,
                bin_dir=bin_dir,
                all_repos=all_repos,
                no_verification=no_verification,
                preview=preview,
                quiet=quiet,
                clone_mode=clone_mode,
                update_dependencies=update_dependencies,
                force_update=force_update,
            )

            pipeline.run(ctx)

        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else str(exc.code)
            failures.append((identifier, f"installer failed (exit={code})"))
            if not quiet:
                print(
                    f"[Warning] install: repository {identifier} failed (exit={code}). Continuing..."
                )
            continue
        except Exception as exc:
            failures.append((identifier, f"unexpected error: {exc}"))
            if not quiet:
                print(
                    f"[Warning] install: repository {identifier} hit an unexpected error: {exc}. Continuing..."
                )
            continue

    if failures and emit_summary and not quiet:
        print("\n[pkgmgr] Installation finished with warnings:")
        for ident, msg in failures:
            print(f"  - {ident}: {msg}")

    if failures and not silent:
        raise SystemExit(1)
