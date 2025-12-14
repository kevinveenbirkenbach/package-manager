# src/pkgmgr/core/version/source.py
from __future__ import annotations

import os
import re
from typing import Optional

import yaml

from pkgmgr.core.repository.paths import resolve_repo_paths


def read_pyproject_version(repo_dir: str) -> Optional[str]:
    """
    Read the version from pyproject.toml in repo_dir, if present.

    Expects a PEP 621-style [project] table with a 'version' field.
    """
    paths = resolve_repo_paths(repo_dir)
    path = paths.pyproject_toml
    if not os.path.isfile(path):
        return None

    try:
        import tomllib  # Python 3.11+
    except Exception:
        import tomli as tomllib  # type: ignore

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        project = data.get("project") or {}
        version = project.get("version")
        return str(version).strip() if version else None
    except Exception:
        return None


def read_pyproject_project_name(repo_dir: str) -> Optional[str]:
    """
    Read distribution name from pyproject.toml ([project].name).

    This is required to correctly resolve installed Python package
    versions via importlib.metadata.
    """
    paths = resolve_repo_paths(repo_dir)
    path = paths.pyproject_toml
    if not os.path.isfile(path):
        return None

    try:
        import tomllib  # Python 3.11+
    except Exception:
        import tomli as tomllib  # type: ignore

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        project = data.get("project") or {}
        name = project.get("name")
        return str(name).strip() if name else None
    except Exception:
        return None


def read_flake_version(repo_dir: str) -> Optional[str]:
    """
    Read the version from flake.nix in repo_dir, if present.

    Looks for:
        version = "X.Y.Z";
    """
    paths = resolve_repo_paths(repo_dir)
    path = paths.flake_nix
    if not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return None

    match = re.search(r'version\s*=\s*"([^"]+)"', text)
    if not match:
        return None

    return match.group(1).strip() or None


def read_pkgbuild_version(repo_dir: str) -> Optional[str]:
    """
    Read the version from PKGBUILD (preferring packaging/arch/PKGBUILD).

    Combines pkgver and pkgrel if both exist:
      pkgver=1.2.3
      pkgrel=1
    -> 1.2.3-1
    """
    paths = resolve_repo_paths(repo_dir)
    path = paths.arch_pkgbuild
    if not path or not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return None

    ver_match = re.search(r"^pkgver\s*=\s*(.+)$", text, re.MULTILINE)
    if not ver_match:
        return None
    pkgver = ver_match.group(1).strip()

    rel_match = re.search(r"^pkgrel\s*=\s*(.+)$", text, re.MULTILINE)
    if rel_match:
        pkgrel = rel_match.group(1).strip()
        if pkgrel:
            return f"{pkgver}-{pkgrel}"

    return pkgver or None


def read_debian_changelog_version(repo_dir: str) -> Optional[str]:
    """
    Read the latest version from debian changelog.

    Preferred path:
      packaging/debian/changelog
    Fallback:
      debian/changelog

    Expected format:
      package (1.2.3-1) unstable; urgency=medium
    """
    paths = resolve_repo_paths(repo_dir)
    path = paths.debian_changelog
    if not path or not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                match = re.search(r"\(([^)]+)\)", line)
                if match:
                    return match.group(1).strip() or None
                break
    except Exception:
        return None

    return None


def read_spec_version(repo_dir: str) -> Optional[str]:
    """
    Read the version from an RPM spec file.

    Preferred paths:
      packaging/fedora/package-manager.spec
      packaging/fedora/*.spec
      repo_root/*.spec

    Combines:
      Version: 1.2.3
      Release: 1%{?dist}
    -> 1.2.3-1
    """
    paths = resolve_repo_paths(repo_dir)
    path = paths.rpm_spec
    if not path or not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return None

    ver_match = re.search(r"^Version:\s*(.+)$", text, re.MULTILINE)
    if not ver_match:
        return None
    version = ver_match.group(1).strip()

    rel_match = re.search(r"^Release:\s*(.+)$", text, re.MULTILINE)
    if rel_match:
        release_raw = rel_match.group(1).strip()
        release = release_raw.split("%", 1)[0].split(" ", 1)[0].strip()
        if release:
            return f"{version}-{release}"

    return version or None


def read_ansible_galaxy_version(repo_dir: str) -> Optional[str]:
    """
    Read the version from Ansible Galaxy metadata.

    Supported:
      - galaxy.yml
      - meta/main.yml (galaxy_info.version or version)
    """
    galaxy_yml = os.path.join(repo_dir, "galaxy.yml")
    if os.path.isfile(galaxy_yml):
        try:
            with open(galaxy_yml, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            version = data.get("version")
            if isinstance(version, str) and version.strip():
                return version.strip()
        except Exception:
            pass

    meta_yml = os.path.join(repo_dir, "meta", "main.yml")
    if os.path.isfile(meta_yml):
        try:
            with open(meta_yml, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            galaxy_info = data.get("galaxy_info") or {}
            if isinstance(galaxy_info, dict):
                version = galaxy_info.get("version")
                if isinstance(version, str) and version.strip():
                    return version.strip()

            version = data.get("version")
            if isinstance(version, str) and version.strip():
                return version.strip()
        except Exception:
            return None

    return None
