# src/pkgmgr/actions/install/pipeline.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installation pipeline orchestration for repositories.
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
    command: Optional[str]
    layer: Optional[CliLayer]


class CommandResolver:
    def __init__(self, ctx: RepoContext) -> None:
        self._ctx = ctx

    def resolve(self) -> CommandState:
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
    def __init__(self, installers: Sequence[BaseInstaller]) -> None:
        self._installers = list(installers)

    def run(self, ctx: RepoContext) -> None:
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

        for installer in self._installers:
            layer_name = getattr(installer, "layer", None)

            if layer_name is None:
                self._run_installer(installer, ctx, identifier, repo_dir, quiet)
                continue

            try:
                installer_layer = CliLayer(layer_name)
            except ValueError:
                installer_layer = None

            if state.layer is not None and installer_layer is not None:
                current_prio = layer_priority(state.layer)
                installer_prio = layer_priority(installer_layer)

                if current_prio < installer_prio:
                    if not quiet:
                        print(
                            "[pkgmgr] Skipping installer "
                            f"{installer.__class__.__name__} for {identifier} – "
                            f"CLI already provided by layer {state.layer.value!r}."
                        )
                    continue

                if current_prio == installer_prio and not ctx.force_update:
                    if not quiet:
                        print(
                            "[pkgmgr] Skipping installer "
                            f"{installer.__class__.__name__} for {identifier} – "
                            f"layer {installer_layer.value!r} is already loaded."
                        )
                    continue

            if not installer.supports(ctx):
                continue

            caps = installer.discover_capabilities(ctx)
            if caps and caps.issubset(provided_capabilities):
                if not quiet:
                    print(
                        f"Skipping installer {installer.__class__.__name__} "
                        f"for {identifier} – capabilities {caps} already provided."
                    )
                continue

            if not quiet:
                if (
                    ctx.force_update
                    and state.layer is not None
                    and installer_layer == state.layer
                ):
                    print(
                        f"[pkgmgr] Running installer {installer.__class__.__name__} "
                        f"for {identifier} in '{repo_dir}' (upgrade requested)..."
                    )
                else:
                    print(
                        f"[pkgmgr] Running installer {installer.__class__.__name__} "
                        f"for {identifier} in '{repo_dir}' "
                        f"(new capabilities: {caps or set()})..."
                    )

            self._run_installer(installer, ctx, identifier, repo_dir, quiet)

            provided_capabilities.update(caps)

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

    @staticmethod
    def _run_installer(
        installer: BaseInstaller,
        ctx: RepoContext,
        identifier: str,
        repo_dir: str,
        quiet: bool,
    ) -> None:
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
