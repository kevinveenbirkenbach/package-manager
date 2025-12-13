#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installation pipeline orchestration for repositories.

This module implements the "Setup Controller" logic:

  1. Detect current CLI command for the repo (if any).
  2. Classify it into a layer (os-packages, nix, python, makefile).
  3. Iterate over installers in layer order:
       - Skip installers whose layer is weaker than an already-loaded one.
       - Run only installers that support() the repo and add new capabilities.
       - After each installer, re-resolve the command and update the layer.
  4. Maintain the repo["command"] field and create/update symlinks via create_ink().

The goal is to prevent conflicting installations and make the layering
behaviour explicit and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Set

from pkgmgr.actions.install.context import RepoContext
from pkgmgr.actions.install.installers.base import BaseInstaller
from pkgmgr.actions.install.layers import (
    CliLayer,
    classify_command_layer,
    layer_priority,
)
from pkgmgr.core.command.ink import create_ink
from pkgmgr.core.command.resolve import resolve_command_for_repo


@dataclass
class CommandState:
    """
    Represents the current CLI state for a repository:

      - command: absolute or relative path to the CLI entry point
      - layer:   which conceptual layer this command belongs to
    """

    command: Optional[str]
    layer: Optional[CliLayer]


class CommandResolver:
    """
    Small helper responsible for resolving the current command for a repo
    and mapping it into a CommandState.
    """

    def __init__(self, ctx: RepoContext) -> None:
        self._ctx = ctx

    def resolve(self) -> CommandState:
        """
        Resolve the current command for this repository.

        If resolve_command_for_repo raises SystemExit (e.g. Python package
        without installed entry point), we treat this as "no command yet"
        from the point of view of the installers.
        """
        repo = self._ctx.repo
        identifier = self._ctx.identifier
        repo_dir = self._ctx.repo_dir

        try:
            cmd = resolve_command_for_repo(
                repo=repo,
                repo_identifier=identifier,
                repo_dir=repo_dir,
            )
        except SystemExit:
            cmd = None

        if not cmd:
            return CommandState(command=None, layer=None)

        layer = classify_command_layer(cmd, repo_dir)
        return CommandState(command=cmd, layer=layer)


class InstallationPipeline:
    """
    High-level orchestrator that applies a sequence of installers
    to a repository based on CLI layer precedence.
    """

    def __init__(self, installers: Sequence[BaseInstaller]) -> None:
        self._installers = list(installers)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, ctx: RepoContext) -> None:
        """
        Execute the installation pipeline for a single repository.

        - Detect initial command & layer.
        - Optionally create a symlink.
        - Run installers in order, skipping those whose layer is weaker
          than an already-loaded CLI.
        - After each installer, re-resolve the command and refresh the
          symlink if needed.
        """
        repo = ctx.repo
        repo_dir = ctx.repo_dir
        identifier = ctx.identifier
        repositories_base_dir = ctx.repositories_base_dir
        bin_dir = ctx.bin_dir
        all_repos = ctx.all_repos
        quiet = ctx.quiet
        preview = ctx.preview

        resolver = CommandResolver(ctx)
        state = resolver.resolve()

        # Persist initial command (if any) and create a symlink.
        if state.command:
            repo["command"] = state.command
            create_ink(
                repo,
                repositories_base_dir,
                bin_dir,
                all_repos,
                quiet=quiet,
                preview=preview,
            )
        else:
            repo.pop("command", None)

        provided_capabilities: Set[str] = set()

        # Main installer loop
        for installer in self._installers:
            layer_name = getattr(installer, "layer", None)

            # Installers without a layer participate without precedence logic.
            if layer_name is None:
                self._run_installer(installer, ctx, identifier, repo_dir, quiet)
                continue

            try:
                installer_layer = CliLayer(layer_name)
            except ValueError:
                # Unknown layer string → treat as lowest priority.
                installer_layer = None

            # "Previous/Current layer already loaded?"
            if state.layer is not None and installer_layer is not None:
                current_prio = layer_priority(state.layer)
                installer_prio = layer_priority(installer_layer)

                if current_prio < installer_prio:
                    # Current CLI comes from a higher-priority layer,
                    # so we skip this installer entirely.
                    if not quiet:
                        print(
                            "[pkgmgr] Skipping installer "
                            f"{installer.__class__.__name__} for {identifier} – "
                            f"CLI already provided by layer {state.layer.value!r}."
                        )
                    continue

                if current_prio == installer_prio:
                    # Same layer already provides a CLI; usually there is no
                    # need to run another installer on top of it.
                    if not quiet:
                        print(
                            "[pkgmgr] Skipping installer "
                            f"{installer.__class__.__name__} for {identifier} – "
                            f"layer {installer_layer.value!r} is already loaded."
                        )
                    continue

            # Check if this installer is applicable at all.
            if not installer.supports(ctx):
                continue

            # Capabilities: if everything this installer would provide is already
            # covered, we can safely skip it.
            caps = installer.discover_capabilities(ctx)
            if caps and caps.issubset(provided_capabilities):
                if not quiet:
                    print(
                        f"Skipping installer {installer.__class__.__name__} "
                        f"for {identifier} – capabilities {caps} already provided."
                    )
                continue

            if not quiet:
                print(
                    f"[pkgmgr] Running installer {installer.__class__.__name__} "
                    f"for {identifier} in '{repo_dir}' "
                    f"(new capabilities: {caps or set()})..."
                )

            # Run the installer with error reporting.
            self._run_installer(installer, ctx, identifier, repo_dir, quiet)

            provided_capabilities.update(caps)

            # After running an installer, re-resolve the command and layer.
            new_state = resolver.resolve()
            if new_state.command:
                repo["command"] = new_state.command
                create_ink(
                    repo,
                    repositories_base_dir,
                    bin_dir,
                    all_repos,
                    quiet=quiet,
                    preview=preview,
                )
            else:
                repo.pop("command", None)

            state = new_state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _run_installer(
        installer: BaseInstaller,
        ctx: RepoContext,
        identifier: str,
        repo_dir: str,
        quiet: bool,
    ) -> None:
        """
        Execute a single installer with unified error handling.
        """
        try:
            installer.run(ctx)
        except SystemExit as exc:
            exit_code = exc.code if isinstance(exc.code, int) else str(exc.code)
            print(
                f"[ERROR] Installer {installer.__class__.__name__} failed "
                f"for repository {identifier} (dir: {repo_dir}) "
                f"with exit code {exit_code}."
            )
            print(
                "[ERROR] This usually means an underlying command failed "
                "(e.g. 'make install', 'nix build', 'pip install', ...)."
            )
            print(
                "[ERROR] Check the log above for the exact command output. "
                "You can also run this repository in isolation via:\n"
                f"        pkgmgr install {identifier} "
                "--clone-mode shallow --no-verification"
            )
            raise
