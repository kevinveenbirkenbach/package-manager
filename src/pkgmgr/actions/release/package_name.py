"""Resolve the distro-package name for a release.

The release flow writes the package identifier into `debian/changelog`,
the RPM `%changelog` stanza, etc. Historically pkgmgr derived this
identifier from the repository folder name (`os.path.basename(repo_root)`),
which silently breaks when the repo is renamed but the existing packaging
files still ship the legacy name. Renaming the folder must not change the
distro-package identity — `apt`, `pacman`, `dnf`, and every downstream
manifest pin the old name.

The resolver therefore walks the existing packaging files in priority
order and only falls back to the folder name when none of them ship an
explicit name.

Priority:
  1. `debian/control` `Package:` field (most authoritative — dpkg-source
     refuses to build if changelog and control disagree)
  2. `packaging/arch/PKGBUILD` `pkgname=` value
  3. RPM spec `Name:` field
  4. Repository folder basename (legacy fallback)
"""

from __future__ import annotations

import os
import re

from pkgmgr.core.repository.paths import RepoPaths

_DEBIAN_PACKAGE_RE = re.compile(r"^Package:\s*(\S+)\s*$", re.MULTILINE)
_PKGBUILD_NAME_RE = re.compile(r"^pkgname=([^\s#]+)\s*$", re.MULTILINE)
_RPM_NAME_RE = re.compile(r"^Name:\s*(\S+)\s*$", re.MULTILINE)


def _read(path: str | None) -> str:
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _extract(pattern: re.Pattern[str], text: str) -> str | None:
    if not text:
        return None
    match = pattern.search(text)
    if not match:
        return None
    value = match.group(1).strip().strip('"').strip("'")
    return value or None


def resolve_package_name(paths: RepoPaths) -> str:
    """Return the distro-package name for the repo, with a folder fallback.

    The fallback uses `os.path.basename(paths.repo_dir)` so behaviour is
    backwards-compatible for repos that ship no packaging metadata yet.
    """
    debian_name = _extract(_DEBIAN_PACKAGE_RE, _read(paths.debian_control))
    if debian_name:
        return debian_name

    pkgbuild_name = _extract(_PKGBUILD_NAME_RE, _read(paths.arch_pkgbuild))
    if pkgbuild_name:
        return pkgbuild_name

    rpm_name = _extract(_RPM_NAME_RE, _read(paths.rpm_spec))
    if rpm_name:
        return rpm_name

    return os.path.basename(paths.repo_dir) or "package"
