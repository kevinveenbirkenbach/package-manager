#!/usr/bin/env python3

"""
Backwards-compatible facade for the release file update helpers.

Implementations live in this package:
  pkgmgr.actions.release.files.*

Keep this package stable so existing imports continue to work, e.g.:
  from pkgmgr.actions.release.files import update_pyproject_version
"""

from __future__ import annotations

from .changelog_md import update_changelog
from .debian import _get_debian_author, update_debian_changelog
from .editor import _open_editor_for_changelog
from .flake import update_flake_version
from .pkgbuild import update_pkgbuild_version
from .pyproject import update_pyproject_version
from .rpm_changelog import update_spec_changelog
from .rpm_spec import update_spec_version

__all__ = [
    "_get_debian_author",
    "_open_editor_for_changelog",
    "update_changelog",
    "update_debian_changelog",
    "update_flake_version",
    "update_pkgbuild_version",
    "update_pyproject_version",
    "update_spec_changelog",
    "update_spec_version",
]
