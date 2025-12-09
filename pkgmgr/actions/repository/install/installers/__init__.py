#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer package for pkgmgr.

This exposes all installer classes so users can import them directly from
pkgmgr.actions.repository.install.installers.
"""

from pkgmgr.actions.repository.install.installers.base import BaseInstaller  # noqa: F401
from pkgmgr.actions.repository.install.installers.nix_flake import NixFlakeInstaller  # noqa: F401
from pkgmgr.actions.repository.install.installers.python import PythonInstaller  # noqa: F401
from pkgmgr.actions.repository.install.installers.makefile import MakefileInstaller  # noqa: F401

# OS-specific installers
from pkgmgr.actions.repository.install.installers.os_packages.arch_pkgbuild import ArchPkgbuildInstaller  # noqa: F401
from pkgmgr.actions.repository.install.installers.os_packages.debian_control import DebianControlInstaller  # noqa: F401
from pkgmgr.actions.repository.install.installers.os_packages.rpm_spec import RpmSpecInstaller  # noqa: F401
