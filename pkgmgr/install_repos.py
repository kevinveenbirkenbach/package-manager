#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Repository installation pipeline for pkgmgr.

This module orchestrates the installation of repositories by:

  1. Ensuring the repository directory exists (cloning if necessary).
  2. Verifying the repository according to the configured policies.
  3. Creating executable links using create_ink(), after resolving the
     appropriate command via resolve_command_for_repo().
  4. Running a sequence of modular installer components that handle
     specific technologies or manifests (PKGBUILD, Nix flakes, Python
     via pyproject.toml, Makefile, OS-specific package metadata).

The goal is to keep this file thin and delegate most logic to small,
focused installer classes.
"""

import os
from typing import List, Dict, Any

from pkgmgr.get_repo_identifier import get_repo_identifier
from pkgmgr.get_repo_dir import get_repo_dir
from pkgmgr.create_ink import create_ink
from pkgmgr.verify import verify_repository
from pkgmgr.clone_repos import clone_repos
from pkgmgr.context import RepoContext
from pkgmgr.resolve_command import resolve_command_for_repo

# Installer implementations
from pkgmgr.installers.os_packages import (
    ArchPkgbuildInstaller,
    DebianControlInstaller,
    RpmSpecInstaller,
)
from pkgmgr.installers.nix_flake import NixFlakeInstaller
from pkgmgr.installers.python import PythonInstaller
from pkgmgr.installers.makefile import MakefileInstaller


# Layering:
#   1) OS packages: PKGBUILD / debian/control / RPM spec  → os-deps.*
#   2) Nix flakes (flake.nix)                            → e.g. python-runtime, make-install
#   3) Python (pyproject.toml)                           → e.g. python-runtime, make-install
#   4) Makefile fallback                                 → e.g. make-install
INSTALLERS = [
    ArchPkgbuildInstaller(),        # Arch
    DebianControlInstaller(),       # Debian/Ubuntu
    RpmSpecInstaller(),             # Fedora/RHEL/CentOS
    NixFlakeInstaller(),            # flake.nix (Nix layer)
    PythonInstaller(),              # pyproject.toml
    MakefileInstaller(),            # generic 'make install'
]


def _ensure_repo_dir(
    repo: Dict[str, Any],
    repositories_base_dir: str,
    all_repos: List[Dict[str, Any]],
    preview: bool,
    no_verification: bool,
    clone_mode: str,
    identifier: str,
) -> str:
    """
    Ensure the repository directory exists. If not, attempt to clone it.

    Returns the repository directory path or an empty string if cloning failed.
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
            return ""

    return repo_dir


def _verify_repo(
    repo: Dict[str, Any],
    repo_dir: str,
    no_verification: bool,
    identifier: str,
) -> bool:
    """
    Verify the repository using verify_repository().

    Returns True if installation should proceed, False if it should be skipped.
    """
    verified_info = repo.get("verified")
    verified_ok, errors, commit_hash, signing_key = verify_repository(
        repo,
        repo_dir,
        mode="local",
        no_verification=no_verification,
    )

    if not no_verification and verified_info and not verified_ok:
        print(f"Warning: Verification failed for {identifier}:")
        for err in errors:
            print(f"  - {err}")
        choice = input("Proceed with installation? (y/N): ").strip().lower()
        if choice != "y":
            print(f"Skipping installation for {identifier}.")
            return False

    return True


def _create_context(
    repo: Dict[str, Any],
    identifier: str,
    repo_dir: str,
    repositories_base_dir: str,
    bin_dir: str,
    all_repos: List[Dict[str, Any]],
    no_verification: bool,
    preview: bool,
    quiet: bool,
    clone_mode: str,
    update_dependencies: bool,
) -> RepoContext:
    """
    Build a RepoContext for the given repository and parameters.
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
    )


def install_repos(
    selected_repos: List[Dict[str, Any]],
    repositories_base_dir: str,
    bin_dir: str,
    all_repos: List[Dict[str, Any]],
    no_verification: bool,
    preview: bool,
    quiet: bool,
    clone_mode: str,
    update_dependencies: bool,
) -> None:
    """
    Install repositories by creating symbolic links and processing standard
    manifest files (PKGBUILD, flake.nix, Python manifests, Makefile, etc.)
    via dedicated installer components.

    Any installer failure (SystemExit) is treated as fatal and will abort
    the current installation.
    """
    for repo in selected_repos:
        identifier = get_repo_identifier(repo, all_repos)
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
            continue

        if not _verify_repo(
            repo=repo,
            repo_dir=repo_dir,
            no_verification=no_verification,
            identifier=identifier,
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
        )

        # ------------------------------------------------------------
        # Resolve the command for this repository before creating the link.
        # If no command is resolved, no link will be created.
        # ------------------------------------------------------------
        resolved_command = resolve_command_for_repo(
            repo=repo,
            repo_identifier=identifier,
            repo_dir=repo_dir,
        )

        if resolved_command:
            repo["command"] = resolved_command
        else:
            repo.pop("command", None)

        # ------------------------------------------------------------
        # Create the symlink using create_ink (if a command is set).
        # ------------------------------------------------------------
        create_ink(
            repo,
            repositories_base_dir,
            bin_dir,
            all_repos,
            quiet=quiet,
            preview=preview,
        )

        # Track which logical capabilities have already been provided by
        # earlier installers for this repository. This allows us to skip
        # installers that would only duplicate work (e.g. Python runtime
        # already provided by Nix flake → skip pyproject/Makefile).
        provided_capabilities: set[str] = set()

        # Run all installers that support this repository, but only if they
        # provide at least one capability that is not yet satisfied.
        for installer in INSTALLERS:
            if not installer.supports(ctx):
                continue

            caps = installer.discover_capabilities(ctx)

            # If the installer declares capabilities and *all* of them are
            # already provided, we can safely skip it.
            if caps and caps.issubset(provided_capabilities):
                if not quiet:
                    print(
                        f"Skipping installer {installer.__class__.__name__} "
                        f"for {identifier} – capabilities {caps} already provided."
                    )
                continue

            # ------------------------------------------------------------
            # Debug output + clear error if an installer fails
            # ------------------------------------------------------------
            if not quiet:
                print(
                    f"[pkgmgr] Running installer {installer.__class__.__name__} "
                    f"for {identifier} in '{repo_dir}' "
                    f"(new capabilities: {caps or '∅'})..."
                )

            try:
                installer.run(ctx)
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else str(exc.code)

                print(
                    f"[ERROR] Installer {installer.__class__.__name__} failed "
                    f"for repository {identifier} (dir: {repo_dir}) "
                    f"with exit code {exit_code}."
                )
                print(
                    "[ERROR] This usually means an underlying command failed "
                    "(e.g. 'make install', 'nix build', 'pip install', ...)."
                )
                print(
                    "[ERROR] Check the log above for the exact command output. "
                    "You can also run this repository in isolation via:\n"
                    f"        pkgmgr install {identifier} --clone-mode shallow --no-verification"
                )

                # Re-raise so that CLI/tests fail clearly,
                # but now with much more context.
                raise

            # Only merge capabilities if the installer succeeded
            provided_capabilities.update(caps)
