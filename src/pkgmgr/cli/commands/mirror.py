from __future__ import annotations

import sys
from typing import Any, Dict, List

from pkgmgr.actions.mirror import (
    diff_mirrors,
    list_mirrors,
    merge_mirrors,
    setup_mirrors,
)
from pkgmgr.cli.context import CLIContext

Repository = Dict[str, Any]


def handle_mirror_command(
    args,
    ctx: CLIContext,
    selected: List[Repository],
) -> None:
    """
    Entry point for 'pkgmgr mirror' subcommands.

    Subcommands:
      - mirror list   → list configured mirrors
      - mirror diff   → compare config vs MIRRORS file
      - mirror merge  → merge mirrors between config and MIRRORS file
      - mirror setup  → configure local Git + remote placeholders
    """
    if not selected:
        print("[INFO] No repositories selected for 'mirror' command.")
        sys.exit(1)

    subcommand = getattr(args, "subcommand", None)

    # ------------------------------------------------------------
    # mirror list
    # ------------------------------------------------------------
    if subcommand == "list":
        source = getattr(args, "source", "all")
        list_mirrors(
            selected_repos=selected,
            repositories_base_dir=ctx.repositories_base_dir,
            all_repos=ctx.all_repositories,
            source=source,
        )
        return

    # ------------------------------------------------------------
    # mirror diff
    # ------------------------------------------------------------
    if subcommand == "diff":
        diff_mirrors(
            selected_repos=selected,
            repositories_base_dir=ctx.repositories_base_dir,
            all_repos=ctx.all_repositories,
        )
        return

    # ------------------------------------------------------------
    # mirror merge
    # ------------------------------------------------------------
    if subcommand == "merge":
        source = getattr(args, "source", None)
        target = getattr(args, "target", None)
        preview = getattr(args, "preview", False)

        if source == target:
            print(
                "[ERROR] For 'mirror merge', source and target "
                "must differ (one of: config, file)."
            )
            sys.exit(2)

        # Config file path can be passed explicitly via --config-path.
        # If not given, fall back to the global context (if available).
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

    # ------------------------------------------------------------
    # mirror setup
    # ------------------------------------------------------------
    if subcommand == "setup":
        local = getattr(args, "local", False)
        remote = getattr(args, "remote", False)
        preview = getattr(args, "preview", False)

        # If neither flag is set → default to both.
        if not local and not remote:
            local = True
            remote = True

        setup_mirrors(
            selected_repos=selected,
            repositories_base_dir=ctx.repositories_base_dir,
            all_repos=ctx.all_repositories,
            preview=preview,
            local=local,
            remote=remote,
        )
        return

    print(f"[ERROR] Unknown mirror subcommand: {subcommand}")
    sys.exit(2)
