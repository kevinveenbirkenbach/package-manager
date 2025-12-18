from __future__ import annotations

from pkgmgr.core.git.commands import (
    fetch,
    pull_ff_only,
    push,
    tag_force_annotated,
)
from pkgmgr.core.git.queries import get_upstream_ref, list_tags


def ensure_clean_and_synced(*, preview: bool = False) -> None:
    """
    Always run a pull BEFORE modifying anything.
    Uses --ff-only to avoid creating merge commits automatically.
    If no upstream is configured, we skip.
    """
    upstream = get_upstream_ref()
    if not upstream:
        print("[INFO] No upstream configured for current branch. Skipping pull.")
        return

    print("[INFO] Syncing with remote before making any changes...")

    # Mirrors old behavior:
    #   git fetch origin --prune --tags --force
    #   git pull --ff-only
    fetch(remote="origin", prune=True, tags=True, force=True, preview=preview)
    pull_ff_only(preview=preview)


def _parse_v_tag(tag: str) -> tuple[int, ...] | None:
    """
    Parse tags like 'v1.2.3' into (1, 2, 3).
    Returns None if parsing is not possible.
    """
    if not tag.startswith("v"):
        return None

    raw = tag[1:]
    if not raw:
        return None

    parts = raw.split(".")
    out: list[int] = []
    for p in parts:
        if not p.isdigit():
            return None
        out.append(int(p))
    return tuple(out) if out else None


def is_highest_version_tag(tag: str) -> bool:
    """
    Return True if `tag` is the highest version among all tags matching v*.

    We avoid shelling out to `sort -V` and implement a small vX.Y.Z parser.
    Non-parseable v* tags are ignored for version comparison.
    """
    all_v = list_tags("v*")
    if not all_v:
        return True  # No tags yet -> current is highest by definition

    parsed_current = _parse_v_tag(tag)
    if parsed_current is None:
        # If the "current" tag isn't parseable, fall back to conservative behavior:
        # treat it as highest only if it matches the max lexicographically.
        latest_lex = max(all_v)
        print(f"[INFO] Latest tag (lex): {latest_lex}, Current tag: {tag}")
        return tag >= latest_lex

    parsed_all: list[tuple[int, ...]] = []
    for t in all_v:
        parsed = _parse_v_tag(t)
        if parsed is not None:
            parsed_all.append(parsed)

    if not parsed_all:
        # No parseable tags -> nothing to compare against
        return True

    latest = max(parsed_all)
    print(
        f"[INFO] Latest tag (parsed): v{'.'.join(map(str, latest))}, Current tag: {tag}"
    )
    return parsed_current >= latest


def update_latest_tag(new_tag: str, *, preview: bool = False) -> None:
    """
    Move the floating 'latest' tag to the newly created release tag.

    Notes:
    - We dereference the tag object via `<tag>^{}` so that 'latest' points to the commit.
    - 'latest' is forced (floating tag), therefore the push uses --force.
    """
    target_ref = f"{new_tag}^{{}}"
    print(
        f"[INFO] Updating 'latest' tag to point at {new_tag} (commit {target_ref})..."
    )

    tag_force_annotated(
        name="latest",
        target=target_ref,
        message=f"Floating latest tag for {new_tag}",
        preview=preview,
    )
    push("origin", "latest", force=True, preview=preview)
