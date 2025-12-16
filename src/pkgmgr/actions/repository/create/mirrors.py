from __future__ import annotations

from typing import Any, Dict

from pkgmgr.actions.mirror.io import write_mirrors_file
from pkgmgr.actions.mirror.setup_cmd import setup_mirrors

Repository = Dict[str, Any]


class MirrorBootstrapper:
    """
    MIRRORS is the single source of truth.

    Defaults are written to MIRRORS and mirror setup derives
    git remotes exclusively from that file (git URLs only).
    """

    def write_defaults(
        self,
        *,
        repo_dir: str,
        primary: str,
        name: str,
        preview: bool,
    ) -> None:
        mirrors = {
            primary,
            f"https://pypi.org/project/{name}/",
        }
        write_mirrors_file(repo_dir, mirrors, preview=preview)

    def setup(
        self,
        *,
        repo: Repository,
        repositories_base_dir: str,
        all_repos: list[Repository],
        preview: bool,
        remote: bool,
    ) -> None:
        # IMPORTANT:
        # Do NOT set repo["mirrors"] here.
        # MIRRORS file is the single source of truth.
        setup_mirrors(
            selected_repos=[repo],
            repositories_base_dir=repositories_base_dir,
            all_repos=all_repos,
            preview=preview,
            local=True,
            remote=True,
            ensure_remote=remote,
        )
