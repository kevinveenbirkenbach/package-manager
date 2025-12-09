#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Helpers to extract version information from various packaging files.

All functions take a repository directory and return either a version
string or None if the corresponding file or version field is missing.

Supported sources:
- pyproject.toml   (PEP 621, [project].version)
- flake.nix        (version = "X.Y.Z";)
- PKGBUILD         (pkgver / pkgrel)
- debian/changelog (first entry line: package (version) ...)
- RPM spec file    (package-manager.spec: Version / Release)
- Ansible Galaxy   (galaxy.yml or meta/main.yml)
"""

from __future__ import annotations

import os
import re
from typing import Optional

import yaml


def read_pyproject_version(repo_dir: str) -> Optional[str]:
    """
    Read the version from pyproject.toml in repo_dir, if present.

    Expects a PEP 621-style [project] table with a 'version' field.
    Returns the version string or None.
    """
    path = os.path.join(repo_dir, "pyproject.toml")
    if not os.path.exists(path):
        return None

    try:
        try:
            import tomllib  # Python 3.11+
        except ModuleNotFoundError:  # pragma: no cover
            tomllib = None

        if tomllib is None:
            return None

        with open(path, "rb") as f:
            data = tomllib.load(f)

        project = data.get("project", {})
        if isinstance(project, dict):
            version = project.get("version")
            if isinstance(version, str):
                return version.strip() or None
    except Exception:
        # Intentionally swallow errors and fall back to None.
        return None

    return None


def read_flake_version(repo_dir: str) -> Optional[str]:
    """
    Read the version from flake.nix in repo_dir, if present.

    Looks for a line like:
        version = "1.2.3";
    and returns the string inside the quotes.
    """
    path = os.path.join(repo_dir, "flake.nix")
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return None

    match = re.search(r'version\s*=\s*"([^"]+)"', text)
    if not match:
        return None
    version = match.group(1).strip()
    return version or None


def read_pkgbuild_version(repo_dir: str) -> Optional[str]:
    """
    Read the version from PKGBUILD in repo_dir, if present.

    Expects:
        pkgver=1.2.3
        pkgrel=1

    Returns either "1.2.3-1" (if both are present) or just "1.2.3".
    """
    path = os.path.join(repo_dir, "PKGBUILD")
    if not os.path.exists(path):
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
    Read the latest Debian version from debian/changelog in repo_dir, if present.

    The first non-empty line typically looks like:
        package-name (1.2.3-1) unstable; urgency=medium

    We extract the text inside the first parentheses.
    """
    path = os.path.join(repo_dir, "debian", "changelog")
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                match = re.search(r"\(([^)]+)\)", line)
                if match:
                    version = match.group(1).strip()
                    return version or None
                break
    except Exception:
        return None

    return None


def read_spec_version(repo_dir: str) -> Optional[str]:
    """
    Read the version from a RPM spec file.

    For now, we assume a fixed file name 'package-manager.spec'
    in repo_dir with lines like:

        Version: 1.2.3
        Release: 1%{?dist}

    Returns either "1.2.3-1" (if Release is present) or "1.2.3".
    Any RPM macro suffix like '%{?dist}' is stripped from the release.
    """
    path = os.path.join(repo_dir, "package-manager.spec")
    if not os.path.exists(path):
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
        # Strip common RPM macro suffix like %... (e.g. 1%{?dist})
        release = release_raw.split("%", 1)[0].strip()
        # Also strip anything after first whitespace, just in case
        release = release.split(" ", 1)[0].strip()
        if release:
            return f"{version}-{release}"

    return version or None


def read_ansible_galaxy_version(repo_dir: str) -> Optional[str]:
    """
    Read the version from Ansible Galaxy metadata, if present.

    Supported locations:
    - galaxy.yml  (preferred for modern roles/collections)
    - meta/main.yml (legacy style roles; uses galaxy_info.version or version)
    """
    # 1) galaxy.yml in repo root
    galaxy_path = os.path.join(repo_dir, "galaxy.yml")
    if os.path.exists(galaxy_path):
        try:
            with open(galaxy_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            version = data.get("version")
            if isinstance(version, str) and version.strip():
                return version.strip()
        except Exception:
            # Ignore parse errors and fall through to meta/main.yml
            pass

    # 2) meta/main.yml (classic Ansible role)
    meta_path = os.path.join(repo_dir, "meta", "main.yml")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # Preferred: galaxy_info.version
            galaxy_info = data.get("galaxy_info") or {}
            if isinstance(galaxy_info, dict):
                version = galaxy_info.get("version")
                if isinstance(version, str) and version.strip():
                    return version.strip()

            # Fallback: top-level 'version'
            version = data.get("version")
            if isinstance(version, str) and version.strip():
                return version.strip()
        except Exception:
            return None

    return None
