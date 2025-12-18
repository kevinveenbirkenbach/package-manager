#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer package for pkgmgr.

This exposes all installer classes so users can import them directly from
pkgmgr.actions.install.installers.
"""

from pkgmgr.actions.install.installers.base import BaseInstaller  # noqa: F401
from pkgmgr.actions.install.installers.nix import NixFlakeInstaller  # noqa: F401
from pkgmgr.actions.install.installers.python import PythonInstaller  # noqa: F401
from pkgmgr.actions.install.installers.makefile import MakefileInstaller  # noqa: F401

# OS-specific installers
from pkgmgr.actions.install.installers.os_packages.arch_pkgbuild import (
    ArchPkgbuildInstaller as ArchPkgbuildInstaller,
)  # noqa: F401
from pkgmgr.actions.install.installers.os_packages.debian_control import (
    DebianControlInstaller as DebianControlInstaller,
)  # noqa: F401
from pkgmgr.actions.install.installers.os_packages.rpm_spec import RpmSpecInstaller  # noqa: F401
