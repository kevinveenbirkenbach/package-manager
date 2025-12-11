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
\033[3mKevin's Package Manager is a multi-repository, multi-package, and multi-format 
development tool crafted by and designed for:\033[0m
  \033[1;34mKevin Veen-Birkenbach\033[0m
  \033[4mhttps://www.veen.world/\033[0m

\033[1mOverview:\033[0m
A powerful toolchain that unifies and automates workflows across heterogeneous
project ecosystems. pkgmgr is not only a package manager — it is a full 
developer-oriented orchestration tool.

It automatically detects, merges, and processes metadata from multiple 
dependency formats, including:
  • \033[1;33mPython:\033[0m pyproject.toml, requirements.txt  
  • \033[1;33mNix:\033[0m flake.nix  
  • \033[1;33mArch Linux:\033[0m PKGBUILD  
  • \033[1;33mAnsible:\033[0m requirements.yml  

This allows pkgmgr to perform installation, updates, verification, dependency
resolution, and synchronization across complex multi-repo environments — with a
single unified command-line interface.

\033[1mDeveloper Tools:\033[0m
pkgmgr includes an integrated toolbox to enhance daily development workflows:

  • \033[1;33mVS Code integration:\033[0m Auto-generate and open multi-repo workspaces  
  • \033[1;33mTerminal integration:\033[0m Open repositories in new GNOME Terminal tabs  
  • \033[1;33mExplorer integration:\033[0m Open repositories in your file manager  
  • \033[1;33mRelease automation:\033[0m Version bumping, changelog updates, and tagging  
  • \033[1;33mBatch operations:\033[0m Execute shell commands across multiple repositories  
  • \033[1;33mGit/Docker/Make wrappers:\033[0m Unified command proxying for many tools 

\033[1mCapabilities:\033[0m
  • Clone, pull, verify, update, and manage many repositories at once  
  • Resolve dependencies across languages and ecosystems  
  • Standardize install/update workflows  
  • Create symbolic executable wrappers for any project  
  • Merge configuration from default + user config layers  

Use pkgmgr as both a robust package management framework and a versatile 
development orchestration tool.

For detailed help on each command, use:
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
    binaries_dir = os.path.expanduser(
        directories.get("binaries", "~/.local/bin")
    )

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
