#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Repository installation pipeline for pkgmgr.

This module orchestrates the installation of repositories by:

  1. Ensuring the repository directory exists (cloning if necessary).
  2. Verifying the repository according to the configured policies.
  3. Creating executable links using create_ink().
  4. Running a sequence of modular installer components that handle
     specific technologies or manifests (pkgmgr.yml, PKGBUILD, Nix,
     Ansible requirements, Python, Makefile, AUR).

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

# Installer implementations
from pkgmgr.installers.pkgmgr_manifest import PkgmgrManifestInstaller
from pkgmgr.installers.pkgbuild import PkgbuildInstaller
from pkgmgr.installers.nix_flake import NixFlakeInstaller
from pkgmgr.installers.ansible_requirements import AnsibleRequirementsInstaller
from pkgmgr.installers.python import PythonInstaller
from pkgmgr.installers.makefile import MakefileInstaller
from pkgmgr.installers.aur import AurInstaller


# Ordered list of installers to apply to each repository.
INSTALLERS = [
    PkgmgrManifestInstaller(),
    PkgbuildInstaller(),
    NixFlakeInstaller(),
    AnsibleRequirementsInstaller(),
    PythonInstaller(),
    MakefileInstaller(),
    AurInstaller(),
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
    manifest files (pkgmgr.yml, PKGBUILD, flake.nix, Ansible requirements,
    Python manifests, Makefile, AUR) via dedicated installer components.

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

        # Create the symlink using create_ink before running installers.
        create_ink(
            repo,
            repositories_base_dir,
            bin_dir,
            all_repos,
            quiet=quiet,
            preview=preview,
        )

        # Run all installers that support this repository.
        for installer in INSTALLERS:
            if installer.supports(ctx):
                installer.run(ctx)
