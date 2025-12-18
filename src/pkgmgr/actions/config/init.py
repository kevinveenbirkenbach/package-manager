#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Initialize user configuration by scanning the repositories base directory.

This module scans the path:

    defaults_config["directories"]["repositories"]

with the expected structure:

    {base}/{provider}/{account}/{repository}

For each discovered repository, the function:
  • derives provider, account, repository from the folder structure
  • (optionally) determines the latest commit hash via git
  • generates a unique CLI alias
  • marks ignore=True for newly discovered repos
  • skips repos already known in defaults or user config
"""

from __future__ import annotations

import os
from typing import Any, Dict

from pkgmgr.core.command.alias import generate_alias
from pkgmgr.core.config.save import save_user_config
from pkgmgr.core.git.queries import get_latest_commit


def config_init(
    user_config: Dict[str, Any],
    defaults_config: Dict[str, Any],
    bin_dir: str,
    user_config_path: str,
) -> None:
    """
    Scan the repositories base directory and add missing entries
    to the user configuration.
    """

    # ------------------------------------------------------------
    # Announce where we will write the result
    # ------------------------------------------------------------
    print("============================================================")
    print("[INIT] Writing user configuration to:")
    print(f"       {user_config_path}")
    print("============================================================")

    repositories_base_dir = os.path.expanduser(
        defaults_config["directories"]["repositories"]
    )

    print("[INIT] Scanning repository base directory:")
    print(f"       {repositories_base_dir}")
    print("")

    if not os.path.isdir(repositories_base_dir):
        print(f"[ERROR] Base directory does not exist: {repositories_base_dir}")
        return

    default_keys = {
        (entry.get("provider"), entry.get("account"), entry.get("repository"))
        for entry in defaults_config.get("repositories", [])
    }
    existing_keys = {
        (entry.get("provider"), entry.get("account"), entry.get("repository"))
        for entry in user_config.get("repositories", [])
    }
    existing_aliases = {
        entry.get("alias")
        for entry in user_config.get("repositories", [])
        if entry.get("alias")
    }

    new_entries = []
    scanned = 0
    skipped = 0

    # ------------------------------------------------------------
    # Actual scanning
    # ------------------------------------------------------------
    for provider in os.listdir(repositories_base_dir):
        provider_path = os.path.join(repositories_base_dir, provider)
        if not os.path.isdir(provider_path):
            continue

        print(f"[SCAN] Provider: {provider}")

        for account in os.listdir(provider_path):
            account_path = os.path.join(provider_path, account)
            if not os.path.isdir(account_path):
                continue

            print(f"[SCAN]   Account: {account}")

            for repo_name in os.listdir(account_path):
                repo_path = os.path.join(account_path, repo_name)
                if not os.path.isdir(repo_path):
                    continue

                scanned += 1
                key = (provider, account, repo_name)

                # Already known?
                if key in default_keys:
                    skipped += 1
                    print(
                        f"[SKIP]     (defaults)       {provider}/{account}/{repo_name}"
                    )
                    continue
                if key in existing_keys:
                    skipped += 1
                    print(
                        f"[SKIP]     (user-config)    {provider}/{account}/{repo_name}"
                    )
                    continue

                print(f"[ADD]      {provider}/{account}/{repo_name}")

                # Determine commit hash via git query
                verified_commit = get_latest_commit(repo_path) or ""
                if verified_commit:
                    print(f"[INFO]       Latest commit: {verified_commit}")
                else:
                    print(
                        "[WARN]       Could not read commit (not a git repo or no commits)."
                    )

                entry: Dict[str, Any] = {
                    "provider": provider,
                    "account": account,
                    "repository": repo_name,
                    "verified": {"commit": verified_commit},
                    "ignore": True,
                }

                # Alias generation
                alias = generate_alias(
                    {
                        "repository": repo_name,
                        "provider": provider,
                        "account": account,
                    },
                    bin_dir,
                    existing_aliases,
                )
                entry["alias"] = alias
                existing_aliases.add(alias)
                print(f"[INFO]       Alias generated: {alias}")

                new_entries.append(entry)

            print("")  # blank line between accounts

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------
    print("============================================================")
    print(f"[DONE] Scanned repositories:  {scanned}")
    print(f"[DONE] Skipped (known):       {skipped}")
    print(f"[DONE] New entries discovered: {len(new_entries)}")
    print("============================================================")

    # ------------------------------------------------------------
    # Save if needed
    # ------------------------------------------------------------
    if new_entries:
        user_config.setdefault("repositories", []).extend(new_entries)
        save_user_config(user_config, user_config_path)
        print("[SAVE] Wrote user configuration to:")
        print(f"       {user_config_path}")
    else:
        print("[INFO] No new repositories were added.")

    print("============================================================")
