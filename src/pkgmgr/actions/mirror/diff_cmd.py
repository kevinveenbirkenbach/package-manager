from __future__ import annotations

from typing import List

from .context import build_context
from .printing import print_header
from .types import Repository


def diff_mirrors(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    all_repos: List[Repository],
) -> None:
    """
    Show differences between config mirrors and MIRRORS file.

    - Mirrors present only in config are reported as "ONLY IN CONFIG".
    - Mirrors present only in MIRRORS file are reported as "ONLY IN FILE".
    - Mirrors with same name but different URLs are reported as "URL MISMATCH".
    """
    for repo in selected_repos:
        ctx = build_context(repo, repositories_base_dir, all_repos)

        print_header("[MIRROR DIFF]", ctx)

        config_m = ctx.config_mirrors
        file_m = ctx.file_mirrors

        if not config_m and not file_m:
            print("  No mirrors configured in config or MIRRORS file.")
            print()
            continue

        # Mirrors only in config
        for name, url in sorted(config_m.items()):
            if name not in file_m:
                print(f"  [ONLY IN CONFIG] {name}: {url}")

        # Mirrors only in MIRRORS file
        for name, url in sorted(file_m.items()):
            if name not in config_m:
                print(f"  [ONLY IN FILE]   {name}: {url}")

        # Mirrors with same name but different URLs
        shared = set(config_m) & set(file_m)
        for name in sorted(shared):
            url_cfg = config_m.get(name)
            url_file = file_m.get(name)
            if url_cfg != url_file:
                print(
                    f"  [URL MISMATCH]  {name}:\n"
                    f"      config: {url_cfg}\n"
                    f"      file:   {url_file}"
                )

        if config_m and file_m and config_m == file_m:
            print("  [OK] Mirrors in config and MIRRORS file are in sync.")

        print()
