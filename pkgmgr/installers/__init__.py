#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer package for pkgmgr.

Each installer implements a small, focused step in the repository
installation pipeline (e.g. PKGBUILD dependencies, Nix flakes, Python,
Ansible requirements, pkgmgr.yml, Makefile, AUR).
"""

from pkgmgr.installers.base import BaseInstaller  # noqa: F401
from pkgmgr.installers.pkgmgr_manifest import PkgmgrManifestInstaller  # noqa: F401
from pkgmgr.installers.pkgbuild import PkgbuildInstaller  # noqa: F401
from pkgmgr.installers.nix_flake import NixFlakeInstaller  # noqa: F401
from pkgmgr.installers.ansible_requirements import AnsibleRequirementsInstaller  # noqa: F401
from pkgmgr.installers.python import PythonInstaller  # noqa: F401
from pkgmgr.installers.makefile import MakefileInstaller  # noqa: F401
from pkgmgr.installers.aur import AurInstaller  # noqa: F401
