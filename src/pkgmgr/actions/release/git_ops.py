#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Git-related helpers for the release workflow.

Responsibilities:
  - Run Git (or shell) commands with basic error reporting.
  - Ensure main/master are synchronized with origin before tagging.
  - Maintain the floating 'latest' tag that always points to the newest
    release tag.
"""

from __future__ import annotations

import subprocess

from pkgmgr.core.git import GitError


def run_git_command(cmd: str) -> None:
    """
    Run a Git (or shell) command with basic error reporting.

    The command is executed via the shell, primarily for readability
    when printed (as in 'git commit -am "msg"').
    """
    print(f"[GIT] {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] Git command failed: {cmd}")
        print(f"        Exit code: {exc.returncode}")
        if exc.stdout:
            print("--- stdout ---")
            print(exc.stdout)
        if exc.stderr:
            print("--- stderr ---")
            print(exc.stderr)
        raise GitError(f"Git command failed: {cmd}") from exc


def sync_branch_with_remote(branch: str, preview: bool = False) -> None:
    """
    Ensure the local main/master branch is up-to-date before tagging.

    Behaviour:
      - For main/master: run 'git fetch origin' and 'git pull origin <branch>'.
      - For all other branches: only log that no automatic sync is performed.
    """
    if branch not in ("main", "master"):
        print(
            f"[INFO] Skipping automatic git pull for non-main/master branch "
            f"{branch}."
        )
        return

    print(
        f"[INFO] Updating branch {branch} from origin before creating tags..."
    )

    if preview:
        print("[PREVIEW] Would run: git fetch origin")
        print(f"[PREVIEW] Would run: git pull origin {branch}")
        return

    run_git_command("git fetch origin")
    run_git_command(f"git pull origin {branch}")


def update_latest_tag(new_tag: str, preview: bool = False) -> None:
    """
    Move the floating 'latest' tag to the newly created release tag.

    Implementation details:
      - We explicitly dereference the tag object via `<tag>^{}` so that
        'latest' always points at the underlying commit, not at another tag.
      - We create/update 'latest' as an annotated tag with a short message so
        Git configurations that enforce annotated/signed tags do not fail
        with "no tag message".
    """
    target_ref = f"{new_tag}^{{}}"
    print(f"[INFO] Updating 'latest' tag to point at {new_tag} (commit {target_ref})...")

    if preview:
        print(f"[PREVIEW] Would run: git tag -f -a latest {target_ref} "
              f'-m "Floating latest tag for {new_tag}"')
        print("[PREVIEW] Would run: git push origin latest --force")
        return

    run_git_command(
        f'git tag -f -a latest {target_ref} '
        f'-m "Floating latest tag for {new_tag}"'
    )
    run_git_command("git push origin latest --force")
