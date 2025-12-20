# src/pkgmgr/cli/commands/mirror.py
from __future__ import annotations

import sys
from typing import Any, Dict, List

from pkgmgr.actions.mirror import (
    diff_mirrors,
    list_mirrors,
    merge_mirrors,
    set_mirror_visibility,
    setup_mirrors,
)
from pkgmgr.cli.context import CLIContext

Repository = Dict[str, Any]


def handle_mirror_command(
    ctx: CLIContext,
    args: Any,
    selected: List[Repository],
) -> None:
    """
    Entry point for 'pkgmgr mirror' subcommands.

    Subcommands:
      - mirror list
      - mirror diff
      - mirror merge
      - mirror setup
      - mirror check
      - mirror provision
      - mirror visibility
    """
    if not selected:
        print("[INFO] No repositories selected for 'mirror' command.")
        sys.exit(1)

    subcommand = getattr(args, "subcommand", None)

    if subcommand == "list":
        source = getattr(args, "source", "all")
        list_mirrors(
            selected_repos=selected,
            repositories_base_dir=ctx.repositories_base_dir,
            all_repos=ctx.all_repositories,
            source=source,
        )
        return

    if subcommand == "diff":
        diff_mirrors(
            selected_repos=selected,
            repositories_base_dir=ctx.repositories_base_dir,
            all_repos=ctx.all_repositories,
        )
        return

    if subcommand == "merge":
        source = getattr(args, "source", None)
        target = getattr(args, "target", None)
        preview = getattr(args, "preview", False)

        if source == target:
            print(
                "[ERROR] For 'mirror merge', source and target must differ (config vs file)."
            )
            sys.exit(2)

        explicit_config_path = getattr(args, "config_path", None)
        user_config_path = explicit_config_path or getattr(
            ctx, "user_config_path", None
        )

        merge_mirrors(
            selected_repos=selected,
            repositories_base_dir=ctx.repositories_base_dir,
            all_repos=ctx.all_repositories,
            source=source,
            target=target,
            preview=preview,
            user_config_path=user_config_path,
        )
        return

    if subcommand == "setup":
        preview = getattr(args, "preview", False)
        setup_mirrors(
            selected_repos=selected,
            repositories_base_dir=ctx.repositories_base_dir,
            all_repos=ctx.all_repositories,
            preview=preview,
            local=True,
            remote=False,
            ensure_remote=False,
            ensure_visibility=None,
        )
        return

    if subcommand == "check":
        preview = getattr(args, "preview", False)
        setup_mirrors(
            selected_repos=selected,
            repositories_base_dir=ctx.repositories_base_dir,
            all_repos=ctx.all_repositories,
            preview=preview,
            local=False,
            remote=True,
            ensure_remote=False,
            ensure_visibility=None,
        )
        return

    if subcommand == "provision":
        preview = getattr(args, "preview", False)
        public = bool(getattr(args, "public", False))

        setup_mirrors(
            selected_repos=selected,
            repositories_base_dir=ctx.repositories_base_dir,
            all_repos=ctx.all_repositories,
            preview=preview,
            local=False,
            remote=True,
            ensure_remote=True,
            ensure_visibility="public" if public else None,
        )
        return

    if subcommand == "visibility":
        preview = getattr(args, "preview", False)
        visibility = getattr(args, "visibility", None)
        if visibility not in ("private", "public"):
            print("[ERROR] mirror visibility expects 'private' or 'public'.")
            sys.exit(2)

        set_mirror_visibility(
            selected_repos=selected,
            repositories_base_dir=ctx.repositories_base_dir,
            all_repos=ctx.all_repositories,
            visibility=visibility,
            preview=preview,
        )
        return

    print(f"[ERROR] Unknown mirror subcommand: {subcommand}")
    sys.exit(2)
