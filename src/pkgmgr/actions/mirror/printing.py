from __future__ import annotations

from .types import MirrorMap, RepoMirrorContext


def print_header(
    title_prefix: str,
    ctx: RepoMirrorContext,
) -> None:
    """
    Print a standard header for mirror-related output.

    title_prefix examples:
      - "[MIRROR]"
      - "[MIRROR DIFF]"
      - "[MIRROR MERGE]"
      - "[MIRROR SETUP:LOCAL]"
      - "[MIRROR SETUP:REMOTE]"
    """
    print("============================================================")
    print(f"{title_prefix} Repository: {ctx.identifier}")
    print(f"{title_prefix} Directory:  {ctx.repo_dir}")
    print("============================================================")


def print_named_mirrors(label: str, mirrors: MirrorMap) -> None:
    """
    Print a labeled mirror block (e.g. '[config mirrors]').
    """
    print(f"  [{label}]")
    if mirrors:
        for name, url in sorted(mirrors.items()):
            print(f"    - {name}: {url}")
    else:
        print("    (none)")
