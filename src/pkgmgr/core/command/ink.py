#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.core.repository.dir import get_repo_dir


def create_ink(
    repo,
    repositories_base_dir,
    bin_dir,
    all_repos,
    quiet: bool = False,
    preview: bool = False,
) -> None:
    """
    Create a symlink for the repository's command.

    IMPORTANT:
    This function is intentionally kept *simple*. All decision logic for
    choosing the command lives inside resolve_command_for_repo().

    Behavior:
      - If repo["command"] is defined → create a symlink to it.
      - If repo["command"] is missing or None → do NOT create a link.

    Safety:
      - If the resolved command path is identical to the final link target,
        we skip symlink creation to avoid self-referential symlinks that
        would break shell resolution ("too many levels of symbolic links").
    """

    repo_identifier = get_repo_identifier(repo, all_repos)
    repo_dir = get_repo_dir(repositories_base_dir, repo)

    command = repo.get("command")
    if not command:
        if not quiet:
            print(f"No command resolved for '{repo_identifier}'. Skipping link.")
        return

    link_path = os.path.join(bin_dir, repo_identifier)

    # ------------------------------------------------------------------
    # Safety guard: avoid self-referential symlinks
    #
    # Example of a broken situation we must avoid:
    #   - command        = ~/.local/bin/package-manager
    #   - link_path      = ~/.local/bin/package-manager
    #   - create_ink() removes the real binary and creates a symlink
    #     pointing to itself → zsh: too many levels of symbolic links
    #
    # If the resolved command already lives exactly at the target path,
    # we treat it as "already installed" and skip any modification.
    # ------------------------------------------------------------------
    if os.path.abspath(command) == os.path.abspath(link_path):
        if not quiet:
            print(
                f"[pkgmgr] Command for '{repo_identifier}' already lives at "
                f"'{link_path}'. Skipping symlink creation to avoid a "
                "self-referential link."
            )
        return

    if preview:
        print(f"[Preview] Would link {link_path} → {command}")
        return

    # Mark local repo scripts as executable if needed
    try:
        if os.path.realpath(command).startswith(os.path.realpath(repo_dir)):
            os.chmod(command, 0o755)
    except Exception as e:
        if not quiet:
            print(f"Failed to set permissions on '{command}': {e}")

    # Create bin directory
    os.makedirs(bin_dir, exist_ok=True)

    # Remove existing
    if os.path.exists(link_path) or os.path.islink(link_path):
        os.remove(link_path)

    # Create the link
    os.symlink(command, link_path)

    if not quiet:
        print(f"Symlink created: {link_path} → {command}")

    # ------------------------------------------------------------
    # Optional alias support (same as before)
    # ------------------------------------------------------------
    alias_name = repo.get("alias")
    if alias_name:
        alias_link_path = os.path.join(bin_dir, alias_name)

        if alias_name == repo_identifier:
            if not quiet:
                print(
                    f"Alias '{alias_name}' equals identifier. Skipping alias creation."
                )
            return

        try:
            if os.path.exists(alias_link_path) or os.path.islink(alias_link_path):
                os.remove(alias_link_path)
            os.symlink(link_path, alias_link_path)
            if not quiet:
                print(f"Alias '{alias_name}' created → {repo_identifier}")
        except Exception as e:
            if not quiet:
                print(f"Error creating alias '{alias_name}': {e}")
