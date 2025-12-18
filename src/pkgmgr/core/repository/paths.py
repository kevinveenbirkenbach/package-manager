#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Central repository path resolver.

Goal:
- Provide ONE place to define where packaging / changelog / metadata files live.
- Prefer modern layout (packaging/*) but stay backwards-compatible with legacy
  root-level paths.

Both:
- readers (pkgmgr.core.version.source)
- writers (pkgmgr.actions.release.workflow)

should use this module instead of hardcoding paths.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class RepoPaths:
    repo_dir: str

    pyproject_toml: str
    flake_nix: str

    # Human changelog (typically Markdown)
    changelog_md: Optional[str]

    # Packaging-related files
    arch_pkgbuild: Optional[str]
    debian_changelog: Optional[str]
    rpm_spec: Optional[str]


def _first_existing(candidates: Iterable[str]) -> Optional[str]:
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


def _find_first_spec_in_dir(dir_path: str) -> Optional[str]:
    if not os.path.isdir(dir_path):
        return None
    try:
        for fn in sorted(os.listdir(dir_path)):
            if fn.endswith(".spec"):
                p = os.path.join(dir_path, fn)
                if os.path.isfile(p):
                    return p
    except OSError:
        return None
    return None


def resolve_repo_paths(repo_dir: str) -> RepoPaths:
    """
    Resolve canonical file locations for a repository.

    Preferences (new layout first, legacy fallback second):
      - PKGBUILD:            packaging/arch/PKGBUILD  -> PKGBUILD
      - Debian changelog:    packaging/debian/changelog -> debian/changelog
      - RPM spec:            packaging/fedora/package-manager.spec
                             -> first *.spec in packaging/fedora
                             -> first *.spec in repo root
      - CHANGELOG.md:        CHANGELOG.md -> packaging/CHANGELOG.md (optional fallback)

    Notes:
      - This resolver only returns paths; it does not read/parse files.
      - Callers should treat Optional paths as "may not exist".
    """
    repo_dir = os.path.abspath(repo_dir)

    pyproject_toml = os.path.join(repo_dir, "pyproject.toml")
    flake_nix = os.path.join(repo_dir, "flake.nix")

    changelog_md = _first_existing(
        [
            os.path.join(repo_dir, "CHANGELOG.md"),
            os.path.join(repo_dir, "packaging", "CHANGELOG.md"),
        ]
    )

    arch_pkgbuild = _first_existing(
        [
            os.path.join(repo_dir, "packaging", "arch", "PKGBUILD"),
            os.path.join(repo_dir, "PKGBUILD"),
        ]
    )

    debian_changelog = _first_existing(
        [
            os.path.join(repo_dir, "packaging", "debian", "changelog"),
            os.path.join(repo_dir, "debian", "changelog"),
        ]
    )

    # RPM spec: prefer the canonical file, else first spec in packaging/fedora, else first spec in repo root.
    rpm_spec = _first_existing(
        [
            os.path.join(repo_dir, "packaging", "fedora", "package-manager.spec"),
        ]
    )
    if rpm_spec is None:
        rpm_spec = _find_first_spec_in_dir(
            os.path.join(repo_dir, "packaging", "fedora")
        )
    if rpm_spec is None:
        rpm_spec = _find_first_spec_in_dir(repo_dir)

    return RepoPaths(
        repo_dir=repo_dir,
        pyproject_toml=pyproject_toml,
        flake_nix=flake_nix,
        changelog_md=changelog_md,
        arch_pkgbuild=arch_pkgbuild,
        debian_changelog=debian_changelog,
        rpm_spec=rpm_spec,
    )
