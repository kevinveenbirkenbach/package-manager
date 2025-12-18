from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from pkgmgr.cli.context import CLIContext
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.core.git.queries import get_tags
from pkgmgr.core.version.semver import SemVer, find_latest_version
from pkgmgr.core.version.installed import (
    get_installed_python_version,
    get_installed_nix_profile_version,
)
from pkgmgr.core.version.source import (
    read_pyproject_version,
    read_pyproject_project_name,
    read_flake_version,
    read_pkgbuild_version,
    read_debian_changelog_version,
    read_spec_version,
    read_ansible_galaxy_version,
)

Repository = Dict[str, Any]


def _print_pkgmgr_self_version() -> None:
    """
    Print version information for pkgmgr itself (installed env + nix profile),
    used when no repository is selected (e.g. user is not inside a repo).
    """
    print("pkgmgr version info")
    print("====================")
    print("\nRepository: <pkgmgr self>")
    print("----------------------------------------")

    # Common distribution/module naming variants.
    python_candidates = [
        "package-manager",  # PyPI dist name in your project
        "package_manager",  # module-ish variant
        "pkgmgr",  # console/alias-ish
    ]
    nix_candidates = [
        "pkgmgr",
        "package-manager",
    ]

    installed_python = get_installed_python_version(*python_candidates)
    installed_nix = get_installed_nix_profile_version(*nix_candidates)

    if installed_python:
        print(
            f"Installed (Python env):  {installed_python.version} "
            f"(dist: {installed_python.name})"
        )
    else:
        print("Installed (Python env):  <not installed>")

    if installed_nix:
        print(
            f"Installed (Nix profile): {installed_nix.version} "
            f"(match: {installed_nix.name})"
        )
    else:
        print("Installed (Nix profile): <not installed>")

    # Helpful context for debugging "why do versions differ?"
    print(f"Python executable:       {sys.executable}")
    print(f"Python prefix:           {sys.prefix}")


def handle_version(
    args,
    ctx: CLIContext,
    selected: List[Repository],
) -> None:
    """
    Handle the 'version' command.

    Shows version information from:
      - Git tags
      - packaging metadata
      - installed Python environment
      - installed Nix profile

    Special case:
      - If no repositories are selected (e.g. not in a repo and no identifiers),
        print pkgmgr's own installed versions instead of exiting with an error.
    """
    if not selected:
        _print_pkgmgr_self_version()
        return

    print("pkgmgr version info")
    print("====================")

    for repo in selected:
        identifier = get_repo_identifier(repo, ctx.all_repositories)

        python_candidates: list[str] = []
        nix_candidates: list[str] = [identifier]

        for key in ("pypi", "pip", "python_package", "distribution", "package"):
            val = repo.get(key)
            if isinstance(val, str) and val.strip():
                python_candidates.append(val.strip())

        python_candidates.append(identifier)

        installed_python = get_installed_python_version(*python_candidates)
        installed_nix = get_installed_nix_profile_version(*nix_candidates)

        repo_dir = repo.get("directory")
        if not repo_dir:
            try:
                repo_dir = get_repo_dir(ctx.repositories_base_dir, repo)
            except Exception:
                repo_dir = None

        if not repo_dir or not os.path.isdir(repo_dir):
            print(f"\nRepository: {identifier}")
            print("----------------------------------------")
            print(
                "[INFO] Skipped: repository directory does not exist locally, "
                "version detection is not possible."
            )

            if installed_python:
                print(
                    f"Installed (Python env):  {installed_python.version} "
                    f"(dist: {installed_python.name})"
                )
            else:
                print("Installed (Python env):  <not installed>")

            if installed_nix:
                print(
                    f"Installed (Nix profile): {installed_nix.version} "
                    f"(match: {installed_nix.name})"
                )
            else:
                print("Installed (Nix profile): <not installed>")

            continue

        print(f"\nRepository: {repo_dir}")
        print("----------------------------------------")

        try:
            tags = get_tags(cwd=repo_dir)
        except Exception as exc:
            print(f"[ERROR] Could not read git tags: {exc}")
            tags = []

        latest_tag_info: Optional[Tuple[str, SemVer]] = (
            find_latest_version(tags) if tags else None
        )

        if latest_tag_info:
            tag, ver = latest_tag_info
            print(f"Git (latest SemVer tag): {tag} (parsed: {ver})")
        else:
            print("Git (latest SemVer tag): <none found>")

        pyproject_version = read_pyproject_version(repo_dir)
        pyproject_name = read_pyproject_project_name(repo_dir)
        flake_version = read_flake_version(repo_dir)
        pkgbuild_version = read_pkgbuild_version(repo_dir)
        debian_version = read_debian_changelog_version(repo_dir)
        spec_version = read_spec_version(repo_dir)
        ansible_version = read_ansible_galaxy_version(repo_dir)

        if pyproject_name:
            installed_python = get_installed_python_version(
                pyproject_name, *python_candidates
            )

        if installed_python:
            print(
                f"Installed (Python env):  {installed_python.version} "
                f"(dist: {installed_python.name})"
            )
        else:
            print("Installed (Python env):  <not installed>")

        if installed_nix:
            print(
                f"Installed (Nix profile): {installed_nix.version} "
                f"(match: {installed_nix.name})"
            )
        else:
            print("Installed (Nix profile): <not installed>")

        print(f"pyproject.toml:         {pyproject_version or '<not found>'}")
        print(f"flake.nix:              {flake_version or '<not found>'}")
        print(f"PKGBUILD:               {pkgbuild_version or '<not found>'}")
        print(f"debian/changelog:       {debian_version or '<not found>'}")
        print(f"package-manager.spec:   {spec_version or '<not found>'}")
        print(f"Ansible Galaxy meta:    {ansible_version or '<not found>'}")

        if latest_tag_info and pyproject_version:
            try:
                file_ver = SemVer.parse(pyproject_version)
                if file_ver != latest_tag_info[1]:
                    print(
                        f"[WARN] Version mismatch: "
                        f"Git={latest_tag_info[1]}, pyproject={file_ver}"
                    )
            except ValueError:
                print(
                    f"[WARN] pyproject version {pyproject_version!r} "
                    f"is not valid SemVer."
                )
