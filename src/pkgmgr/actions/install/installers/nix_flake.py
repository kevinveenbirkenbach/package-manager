#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for Nix flakes.

If a repository contains flake.nix and the 'nix' command is available, this
installer will try to install profile outputs from the flake.

Behavior:
  - If flake.nix is present and `nix` exists on PATH:
      * First remove any existing `package-manager` profile entry (best-effort).
      * Then install one or more flake outputs via `nix profile install`.
  - For the package-manager repo:
      * `pkgmgr` is mandatory (CLI), `default` is optional.
  - For all other repos:
      * `default` is mandatory.

Special handling:
  - If PKGMGR_DISABLE_NIX_FLAKE_INSTALLER=1 is set, the installer is
    globally disabled (useful for CI or debugging).

The higher-level InstallationPipeline and CLI-layer model decide when this
installer is allowed to run, based on where the current CLI comes from
(e.g. Nix, OS packages, Python, Makefile).
"""

import os
import shutil
from typing import TYPE_CHECKING, List, Tuple

from pkgmgr.actions.install.installers.base import BaseInstaller
from pkgmgr.core.command.run import run_command

if TYPE_CHECKING:
    from pkgmgr.actions.install.context import RepoContext
    from pkgmgr.actions.install import InstallContext


class NixFlakeInstaller(BaseInstaller):
    """Install Nix flake profiles for repositories that define flake.nix."""

    # Logical layer name, used by capability matchers.
    layer = "nix"

    FLAKE_FILE = "flake.nix"
    PROFILE_NAME = "package-manager"

    def supports(self, ctx: "RepoContext") -> bool:
        """
        Only support repositories that:
          - Are NOT explicitly disabled via PKGMGR_DISABLE_NIX_FLAKE_INSTALLER=1,
          - Have a flake.nix,
          - And have the `nix` command available.
        """
        # Optional global kill-switch for CI or debugging.
        if os.environ.get("PKGMGR_DISABLE_NIX_FLAKE_INSTALLER") == "1":
            print(
                "[INFO] PKGMGR_DISABLE_NIX_FLAKE_INSTALLER=1 – "
                "NixFlakeInstaller is disabled."
            )
            return False

        # Nix must be available.
        if shutil.which("nix") is None:
            return False

        # flake.nix must exist in the repository.
        flake_path = os.path.join(ctx.repo_dir, self.FLAKE_FILE)
        return os.path.exists(flake_path)

    def _ensure_old_profile_removed(self, ctx: "RepoContext") -> None:
        """
        Best-effort removal of an existing profile entry.

        This handles the "already provides the following file" conflict by
        removing previous `package-manager` installations before we install
        the new one.

        Any error in `nix profile remove` is intentionally ignored, because
        a missing profile entry is not a fatal condition.
        """
        if shutil.which("nix") is None:
            return

        cmd = f"nix profile remove {self.PROFILE_NAME} || true"
        try:
            # NOTE: no allow_failure here → matches the existing unit tests
            run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
        except SystemExit:
            # Unit tests explicitly assert this is swallowed
            pass

    def _profile_outputs(self, ctx: "RepoContext") -> List[Tuple[str, bool]]:
        """
        Decide which flake outputs to install and whether failures are fatal.

        Returns a list of (output_name, allow_failure) tuples.

        Rules:
          - For the package-manager repo (identifier 'pkgmgr' or 'package-manager'):
                [("pkgmgr", False), ("default", True)]
          - For all other repos:
                [("default", False)]
        """
        ident = ctx.identifier

        if ident in {"pkgmgr", "package-manager"}:
            # pkgmgr: main CLI output is "pkgmgr" (mandatory),
            # "default" is nice-to-have (non-fatal).
            return [("pkgmgr", False), ("default", True)]

        # Generic repos: we expect a sensible "default" package/app.
        # Failure to install it is considered fatal.
        return [("default", False)]

    def run(self, ctx: "InstallContext") -> None:
        """
        Install Nix flake profile outputs.

        For the package-manager repo, failure installing 'pkgmgr' is fatal,
        failure installing 'default' is non-fatal.
        For other repos, failure installing 'default' is fatal.
        """
        # Reuse supports() to keep logic in one place.
        if not self.supports(ctx):  # type: ignore[arg-type]
            return

        outputs = self._profile_outputs(ctx)  # list of (name, allow_failure)

        print(
            "Nix flake detected in "
            f"{ctx.identifier}, attempting to install profile outputs: "
            + ", ".join(name for name, _ in outputs)
        )

        # Handle the "already installed" case up-front for the shared profile.
        self._ensure_old_profile_removed(ctx)  # type: ignore[arg-type]

        for output, allow_failure in outputs:
            cmd = f"nix profile install {ctx.repo_dir}#{output}"
            print(f"[INFO] Running: {cmd}")
            ret = os.system(cmd)

            # Extract real exit code from os.system() result
            if os.WIFEXITED(ret):
                exit_code = os.WEXITSTATUS(ret)
            else:
                # abnormal termination (signal etc.) – keep raw value
                exit_code = ret

            if exit_code == 0:
                print(f"Nix flake output '{output}' successfully installed.")
                continue

            print(f"[Error] Failed to install Nix flake output '{output}'")
            print(f"[Error] Command exited with code {exit_code}")

            if not allow_failure:
                raise SystemExit(exit_code)

            print(
                "[Warning] Continuing despite failure to install "
                f"optional output '{output}'."
            )
