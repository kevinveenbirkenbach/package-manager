#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer package for pkgmgr.

This exposes all installer classes so users can import them directly from
pkgmgr.installers.
"""

from pkgmgr.installers.base import BaseInstaller  # noqa: F401
from pkgmgr.installers.pkgmgr_manifest import PkgmgrManifestInstaller  # noqa: F401
from pkgmgr.installers.nix_flake import NixFlakeInstaller  # noqa: F401
from pkgmgr.installers.python import PythonInstaller  # noqa: F401
from pkgmgr.installers.makefile import MakefileInstaller  # noqa: F401

# OS-specific installers
from pkgmgr.installers.os_packages.arch_pkgbuild import ArchPkgbuildInstaller  # noqa: F401
from pkgmgr.installers.os_packages.debian_control import DebianControlInstaller  # noqa: F401
from pkgmgr.installers.os_packages.rpm_spec import RpmSpecInstaller  # noqa: F401
