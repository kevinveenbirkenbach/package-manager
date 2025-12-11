from __future__ import annotations

from typing import List

from .context import build_context
from .printing import print_header, print_named_mirrors
from .types import Repository


def list_mirrors(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    all_repos: List[Repository],
    source: str = "all",
) -> None:
    """
    List mirrors for the selected repositories.

    source:
      - "config"   → only mirrors from configuration
      - "file"     → only mirrors from MIRRORS file
      - "resolved" → merged view (config + file, file wins)
      - "all"      → show config + file + resolved
    """
    for repo in selected_repos:
        ctx = build_context(repo, repositories_base_dir, all_repos)
        resolved_m = ctx.resolved_mirrors

        print_header("[MIRROR]", ctx)

        if source in ("config", "all"):
            print_named_mirrors("config mirrors", ctx.config_mirrors)
            if source == "config":
                print()
                continue  # next repo

        if source in ("file", "all"):
            print_named_mirrors("MIRRORS file", ctx.file_mirrors)
            if source == "file":
                print()
                continue  # next repo

        if source in ("resolved", "all"):
            print_named_mirrors("resolved mirrors", resolved_m)

        print()
