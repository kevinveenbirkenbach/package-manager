# -*- coding: utf-8 -*-
from __future__ import annotations

import os

from pkgmgr.core.config.load import load_config

from .context import CLIContext
from .parser import create_parser
from .dispatch import dispatch_command

__all__ = ["CLIContext", "create_parser", "dispatch_command", "main"]


# User config lives in the home directory:
#   ~/.config/pkgmgr/config.yaml
USER_CONFIG_PATH = os.path.expanduser("~/.config/pkgmgr/config.yaml")

DESCRIPTION_TEXT = """\
\033[1;32mPackage Manager 🤖📦\033[0m
\033[3mKevin's multi-distro package and workflow manager.\033[0m
\033[1;34mKevin Veen-Birkenbach\033[0m – \033[4mhttps://s.veen.world/pkgmgr\033[0m

Built in \033[1;33mPython\033[0m on top of \033[1;33mNix flakes\033[0m to manage many
repositories and packaging formats (pyproject.toml, flake.nix,
PKGBUILD, debian, Ansible, …) with one CLI.

For details on any command, run:
  \033[1mpkgmgr <command> --help\033[0m
"""


def main() -> None:
    """
    Entry point for the pkgmgr CLI.
    """

    config_merged = load_config(USER_CONFIG_PATH)

    # Directories: be robust and provide sane defaults if missing
    directories = config_merged.get("directories") or {}
    repositories_dir = os.path.expanduser(
        directories.get("repositories", "~/Repositories")
    )
    binaries_dir = os.path.expanduser(directories.get("binaries", "~/.local/bin"))

    # Ensure the merged config actually contains the resolved directories
    config_merged.setdefault("directories", {})
    config_merged["directories"]["repositories"] = repositories_dir
    config_merged["directories"]["binaries"] = binaries_dir

    all_repositories = config_merged.get("repositories", [])

    ctx = CLIContext(
        config_merged=config_merged,
        repositories_base_dir=repositories_dir,
        all_repositories=all_repositories,
        binaries_dir=binaries_dir,
        user_config_path=USER_CONFIG_PATH,
    )

    parser = create_parser(DESCRIPTION_TEXT)
    args = parser.parse_args()

    if not getattr(args, "command", None):
        parser.print_help()
        return

    dispatch_command(args, ctx)


if __name__ == "__main__":
    main()
