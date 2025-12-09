from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from pkgmgr.cli.context import CLIContext
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.core.git import get_tags
from pkgmgr.core.version.semver import SemVer, find_latest_version
from pkgmgr.core.version.source import (
    read_pyproject_version,
    read_flake_version,
    read_pkgbuild_version,
    read_debian_changelog_version,
    read_spec_version,
    read_ansible_galaxy_version,
)


Repository = Dict[str, Any]


def handle_version(
    args,
    ctx: CLIContext,
    selected: List[Repository],
) -> None:
    """
    Handle the 'version' command.

    Shows version information from various sources (git tags, pyproject,
    flake.nix, PKGBUILD, debian, spec, Ansible Galaxy).
    """

    repo_list = selected
    if not repo_list:
        print("No repositories selected for version.")
        sys.exit(1)

    print("pkgmgr version info")
    print("====================")

    for repo in repo_list:
        # Resolve repository directory
        repo_dir = repo.get("directory")
        if not repo_dir:
            try:
                repo_dir = get_repo_dir(ctx.repositories_base_dir, repo)
            except Exception:
                repo_dir = None

        # If no local clone exists, skip gracefully with info message
        if not repo_dir or not os.path.isdir(repo_dir):
            identifier = get_repo_identifier(repo, ctx.all_repositories)
            print(f"\nRepository: {identifier}")
            print("----------------------------------------")
            print(
                "[INFO] Skipped: repository directory does not exist "
                "locally, version detection is not possible."
            )
            continue

        print(f"\nRepository: {repo_dir}")
        print("----------------------------------------")

        # 1) Git tags (SemVer)
        try:
            tags = get_tags(cwd=repo_dir)
        except Exception as exc:
            print(f"[ERROR] Could not read git tags: {exc}")
            tags = []

        latest_tag_info: Optional[Tuple[str, SemVer]]
        latest_tag_info = find_latest_version(tags) if tags else None

        if latest_tag_info is None:
            latest_tag_str = None
            latest_ver = None
        else:
            latest_tag_str, latest_ver = latest_tag_info

        # 2) Packaging / metadata sources
        pyproject_version = read_pyproject_version(repo_dir)
        flake_version = read_flake_version(repo_dir)
        pkgbuild_version = read_pkgbuild_version(repo_dir)
        debian_version = read_debian_changelog_version(repo_dir)
        spec_version = read_spec_version(repo_dir)
        ansible_version = read_ansible_galaxy_version(repo_dir)

        # 3) Print version summary
        if latest_ver is not None:
            print(
                f"Git (latest SemVer tag): {latest_tag_str} (parsed: {latest_ver})"
            )
        else:
            print("Git (latest SemVer tag): <none found>")

        print(f"pyproject.toml:         {pyproject_version or '<not found>'}")
        print(f"flake.nix:              {flake_version or '<not found>'}")
        print(f"PKGBUILD:               {pkgbuild_version or '<not found>'}")
        print(f"debian/changelog:       {debian_version or '<not found>'}")
        print(f"package-manager.spec:   {spec_version or '<not found>'}")
        print(f"Ansible Galaxy meta:    {ansible_version or '<not found>'}")

        # 4) Consistency hint (Git tag vs. pyproject)
        if latest_ver is not None and pyproject_version is not None:
            try:
                file_ver = SemVer.parse(pyproject_version)
                if file_ver != latest_ver:
                    print(
                        f"[WARN] Version mismatch: Git={latest_ver}, pyproject={file_ver}"
                    )
            except ValueError:
                print(
                    f"[WARN] pyproject version {pyproject_version!r} is not valid SemVer."
                )
