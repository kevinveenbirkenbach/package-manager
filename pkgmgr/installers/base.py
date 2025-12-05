#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base interface for all installer components in the pkgmgr installation pipeline.
"""

from abc import ABC, abstractmethod

from pkgmgr.context import RepoContext


class BaseInstaller(ABC):
    """
    A single step in the installation pipeline for a repository.

    Implementations should be small and focused on one technology or manifest
    type (e.g. PKGBUILD, Nix, Python, Ansible, pkgmgr.yml).
    """

    @abstractmethod
    def supports(self, ctx: RepoContext) -> bool:
        """
        Return True if this installer should run for the given repository
        context. This is typically based on file existence or platform checks.

        Implementations must never swallow critical errors silently; if a
        configuration is broken, they should raise SystemExit.
        """
        raise NotImplementedError

    @abstractmethod
    def run(self, ctx: RepoContext) -> None:
        """
        Execute the installer logic for the given repository context.

        Implementations are allowed to raise SystemExit (for example via
        run_command()) on errors. Such failures are considered fatal for
        the installation pipeline.
        """
        raise NotImplementedError
