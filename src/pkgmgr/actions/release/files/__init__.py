#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Backwards-compatible facade for the release file update helpers.

Implementations live in this package:
  pkgmgr.actions.release.files.*

Keep this package stable so existing imports continue to work, e.g.:
  from pkgmgr.actions.release.files import update_pyproject_version
"""

from __future__ import annotations

from .editor import _open_editor_for_changelog
from .pyproject import update_pyproject_version
from .flake import update_flake_version
from .pkgbuild import update_pkgbuild_version
from .rpm_spec import update_spec_version
from .changelog_md import update_changelog
from .debian import _get_debian_author, update_debian_changelog
from .rpm_changelog import update_spec_changelog

__all__ = [
    "_open_editor_for_changelog",
    "update_pyproject_version",
    "update_flake_version",
    "update_pkgbuild_version",
    "update_spec_version",
    "update_changelog",
    "_get_debian_author",
    "update_debian_changelog",
    "update_spec_changelog",
]
