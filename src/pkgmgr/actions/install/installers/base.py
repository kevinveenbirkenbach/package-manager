#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base interface for all installer components in the pkgmgr installation pipeline.
"""

from abc import ABC, abstractmethod
from typing import Set, Optional

from pkgmgr.actions.install.context import RepoContext
from pkgmgr.actions.install.capabilities import CAPABILITY_MATCHERS


class BaseInstaller(ABC):
    """
    A single step in the installation pipeline for a repository.

    Implementations should be small and focused on one technology or manifest
    type (e.g. PKGBUILD, Nix, Python, Makefile, etc.).
    """

    #: Logical layer name for this installer.
    #   Examples: "nix", "python", "makefile".
    #   This is used by capability matchers to decide which patterns to
    #   search for in the repository.
    layer: Optional[str] = None

    def discover_capabilities(self, ctx: RepoContext) -> Set[str]:
        """
        Determine which logical capabilities this installer will provide
        for this specific repository instance.

        This method delegates to the global capability matchers, which
        inspect build/configuration files (flake.nix, pyproject.toml,
        Makefile, etc.) and decide, via string matching, whether a given
        capability is actually provided by this layer.
        """
        caps: Set[str] = set()
        if not self.layer:
            return caps

        for matcher in CAPABILITY_MATCHERS:
            if matcher.applies_to_layer(self.layer) and matcher.is_provided(
                ctx, self.layer
            ):
                caps.add(matcher.name)

        return caps

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
