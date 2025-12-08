from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

import yaml

from pkgmgr.cli_core.context import CLIContext
from pkgmgr.config_init import config_init
from pkgmgr.interactive_add import interactive_add
from pkgmgr.resolve_repos import resolve_repos
from pkgmgr.save_user_config import save_user_config
from pkgmgr.show_config import show_config
from pkgmgr.run_command import run_command


def _load_user_config(user_config_path: str) -> Dict[str, Any]:
    """
    Load the user config file, returning a default structure if it does not exist.
    """
    if os.path.exists(user_config_path):
        with open(user_config_path, "r") as f:
            return yaml.safe_load(f) or {"repositories": []}
    return {"repositories": []}


def handle_config(args, ctx: CLIContext) -> None:
    """
    Handle the 'config' command and its subcommands.
    """

    user_config_path = ctx.user_config_path

    # --------------------------------------------------------
    # config show
    # --------------------------------------------------------
    if args.subcommand == "show":
        if args.all or (not args.identifiers):
            show_config([], user_config_path, full_config=True)
        else:
            selected = resolve_repos(args.identifiers, ctx.all_repositories)
            if selected:
                show_config(
                    selected,
                    user_config_path,
                    full_config=False,
                )
        return

    # --------------------------------------------------------
    # config add
    # --------------------------------------------------------
    if args.subcommand == "add":
        interactive_add(ctx.config_merged, user_config_path)
        return

    # --------------------------------------------------------
    # config edit
    # --------------------------------------------------------
    if args.subcommand == "edit":
        run_command(f"nano {user_config_path}")
        return

    # --------------------------------------------------------
    # config init
    # --------------------------------------------------------
    if args.subcommand == "init":
        user_config = _load_user_config(user_config_path)
        config_init(
            user_config,
            ctx.config_merged,
            ctx.binaries_dir,
            user_config_path,
        )
        return

    # --------------------------------------------------------
    # config delete
    # --------------------------------------------------------
    if args.subcommand == "delete":
        user_config = _load_user_config(user_config_path)

        if args.all or not args.identifiers:
            print("You must specify identifiers to delete.")
            return

        to_delete = resolve_repos(
            args.identifiers,
            user_config.get("repositories", []),
        )
        new_repos = [
            entry
            for entry in user_config.get("repositories", [])
            if entry not in to_delete
        ]
        user_config["repositories"] = new_repos
        save_user_config(user_config, user_config_path)
        print(f"Deleted {len(to_delete)} entries from user config.")
        return

    # --------------------------------------------------------
    # config ignore
    # --------------------------------------------------------
    if args.subcommand == "ignore":
        user_config = _load_user_config(user_config_path)

        if args.all or not args.identifiers:
            print("You must specify identifiers to modify ignore flag.")
            return

        to_modify = resolve_repos(
            args.identifiers,
            user_config.get("repositories", []),
        )

        for entry in user_config["repositories"]:
            key = (
                entry.get("provider"),
                entry.get("account"),
                entry.get("repository"),
            )
            for mod in to_modify:
                mod_key = (
                    mod.get("provider"),
                    mod.get("account"),
                    mod.get("repository"),
                )
                if key == mod_key:
                    entry["ignore"] = args.set == "true"
                    print(
                        f"Set ignore for {key} to {entry['ignore']}"
                    )

        save_user_config(user_config, user_config_path)
        return

    # If we end up here, something is wrong with subcommand routing
    print(f"Unknown config subcommand: {args.subcommand}")
    sys.exit(2)
