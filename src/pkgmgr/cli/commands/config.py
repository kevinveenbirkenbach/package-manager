#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from pkgmgr.cli.context import CLIContext
from pkgmgr.actions.config.init import config_init
from pkgmgr.actions.config.add import interactive_add
from pkgmgr.core.repository.resolve import resolve_repos
from pkgmgr.core.config.save import save_user_config
from pkgmgr.actions.config.show import show_config
from pkgmgr.core.command.run import run_command


def _load_user_config(user_config_path: str) -> Dict[str, Any]:
    """
    Load the user config from ~/.config/pkgmgr/config.yaml
    (or whatever ctx.user_config_path is), creating the directory if needed.
    """
    user_config_path_expanded = os.path.expanduser(user_config_path)
    cfg_dir = os.path.dirname(user_config_path_expanded)
    if cfg_dir and not os.path.isdir(cfg_dir):
        os.makedirs(cfg_dir, exist_ok=True)

    if os.path.exists(user_config_path_expanded):
        with open(user_config_path_expanded, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"repositories": []}
    return {"repositories": []}


def _find_defaults_source_dir() -> Optional[str]:
    """
    Find the directory inside the installed pkgmgr package OR the
    project root that contains default config files.

    Preferred locations (in dieser Reihenfolge):
      - <pkg_root>/config_defaults
      - <pkg_root>/config
      - <project_root>/config_defaults
      - <project_root>/config
    """
    import pkgmgr  # local import to avoid circular deps

    pkg_root = Path(pkgmgr.__file__).resolve().parent
    project_root = pkg_root.parent

    candidates = [
        pkg_root / "config_defaults",
        pkg_root / "config",
        project_root / "config_defaults",
        project_root / "config",
    ]
    for cand in candidates:
        if cand.is_dir():
            return str(cand)
    return None


def _update_default_configs(user_config_path: str) -> None:
    """
    Copy all default *.yml/*.yaml files from the installed pkgmgr package
    into ~/.config/pkgmgr/, overwriting existing ones – except the user
    config file itself (config.yaml), which is never touched.
    """
    source_dir = _find_defaults_source_dir()
    if not source_dir:
        print(
            "[WARN] No config_defaults or config directory found in "
            "pkgmgr installation. Nothing to update."
        )
        return

    dest_dir = os.path.dirname(os.path.expanduser(user_config_path))
    if not dest_dir:
        dest_dir = os.path.expanduser("~/.config/pkgmgr")
    os.makedirs(dest_dir, exist_ok=True)

    for name in os.listdir(source_dir):
        lower = name.lower()
        if not (lower.endswith(".yml") or lower.endswith(".yaml")):
            continue
        if name == "config.yaml":
            # Never overwrite the user config template / live config
            continue

        src = os.path.join(source_dir, name)
        dst = os.path.join(dest_dir, name)

        shutil.copy2(src, dst)
        print(f"[INFO] Updated default config file: {dst}")


def handle_config(args, ctx: CLIContext) -> None:
    """
    Handle 'pkgmgr config' subcommands.
    """

    user_config_path = ctx.user_config_path

    # ------------------------------------------------------------
    # config show
    # ------------------------------------------------------------
    if args.subcommand == "show":
        if args.all or (not args.identifiers):
            # Full merged config view
            show_config([], user_config_path, full_config=True)
        else:
            # Show only matching entries from user config
            user_config = _load_user_config(user_config_path)
            selected = resolve_repos(
                args.identifiers,
                user_config.get("repositories", []),
            )
            if selected:
                show_config(
                    selected,
                    user_config_path,
                    full_config=False,
                )
        return

    # ------------------------------------------------------------
    # config add
    # ------------------------------------------------------------
    if args.subcommand == "add":
        interactive_add(ctx.config_merged, user_config_path)
        return

    # ------------------------------------------------------------
    # config edit
    # ------------------------------------------------------------
    if args.subcommand == "edit":
        run_command(f"nano {user_config_path}")
        return

    # ------------------------------------------------------------
    # config init
    # ------------------------------------------------------------
    if args.subcommand == "init":
        user_config = _load_user_config(user_config_path)
        config_init(
            user_config,
            ctx.config_merged,
            ctx.binaries_dir,
            user_config_path,
        )
        return

    # ------------------------------------------------------------
    # config delete
    # ------------------------------------------------------------
    if args.subcommand == "delete":
        user_config = _load_user_config(user_config_path)

        if args.all or not args.identifiers:
            print(
                "[ERROR] 'config delete' requires explicit identifiers. "
                "Use 'config show' to inspect entries."
            )
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

    # ------------------------------------------------------------
    # config ignore
    # ------------------------------------------------------------
    if args.subcommand == "ignore":
        user_config = _load_user_config(user_config_path)

        if args.all or not args.identifiers:
            print(
                "[ERROR] 'config ignore' requires explicit identifiers. "
                "Use 'config show' to inspect entries."
            )
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
                    print(f"Set ignore for {key} to {entry['ignore']}")

        save_user_config(user_config, user_config_path)
        return

    # ------------------------------------------------------------
    # config update
    # ------------------------------------------------------------
    if args.subcommand == "update":
        """
        Copy default YAML configs from the installed package into the
        user's ~/.config/pkgmgr directory.

        This will overwrite files with the same name (except config.yaml).
        """
        _update_default_configs(user_config_path)
        return

    # ------------------------------------------------------------
    # Unknown subcommand
    # ------------------------------------------------------------
    print(f"Unknown config subcommand: {args.subcommand}")
    sys.exit(2)
