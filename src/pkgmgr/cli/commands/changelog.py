from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from pkgmgr.cli.context import CLIContext
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.core.git.queries import get_tags
from pkgmgr.core.version.semver import extract_semver_from_tags
from pkgmgr.actions.changelog import generate_changelog


Repository = Dict[str, Any]


def _find_previous_and_current_tag(
    tags: List[str],
    target_tag: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Given a list of tags and an optional target tag, determine
    (previous_tag, current_tag) on the SemVer axis.

    If target_tag is None:
        - If there are at least two SemVer tags, return (prev, latest).
        - If there is only one SemVer tag, return (None, latest).
        - If there are no SemVer tags, return (None, None).

    If target_tag is given:
        - If target_tag is not a SemVer tag or is unknown, return (None, None).
        - Otherwise, return (previous_semver_tag, target_tag).
          If there is no previous SemVer tag, previous_semver_tag is None.
    """
    semver_pairs = extract_semver_from_tags(tags)
    if not semver_pairs:
        return None, None

    # Sort ascending by SemVer
    semver_pairs.sort(key=lambda item: item[1])

    tag_to_index = {tag: idx for idx, (tag, _ver) in enumerate(semver_pairs)}

    if target_tag is None:
        if len(semver_pairs) == 1:
            return None, semver_pairs[0][0]
        prev_tag = semver_pairs[-2][0]
        latest_tag = semver_pairs[-1][0]
        return prev_tag, latest_tag

    # target_tag is specified
    if target_tag not in tag_to_index:
        return None, None

    idx = tag_to_index[target_tag]
    current_tag = semver_pairs[idx][0]
    if idx == 0:
        return None, current_tag

    previous_tag = semver_pairs[idx - 1][0]
    return previous_tag, current_tag


def handle_changelog(
    args,
    ctx: CLIContext,
    selected: List[Repository],
) -> None:
    """
    Handle the 'changelog' command.

    Behaviour:
    - Without range: show changelog between the last two SemVer tags,
      or from the single SemVer tag to HEAD, or from the beginning if
      no tags exist.
    - With RANGE of the form 'A..B': show changelog between A and B.
    - With RANGE of the form 'vX.Y.Z': show changelog between the
      previous SemVer tag and vX.Y.Z (or from start if there is none).
    """

    if not selected:
        print("No repositories selected for changelog.")
        sys.exit(1)

    range_arg: str = getattr(args, "range", "") or ""

    print("pkgmgr changelog")
    print("=================")

    for repo in selected:
        # Resolve repository directory
        repo_dir = repo.get("directory")
        if not repo_dir:
            try:
                repo_dir = get_repo_dir(ctx.repositories_base_dir, repo)
            except Exception:
                repo_dir = None

        identifier = get_repo_identifier(repo, ctx.all_repositories)

        if not repo_dir or not os.path.isdir(repo_dir):
            print(f"\nRepository: {identifier}")
            print("----------------------------------------")
            print(
                "[INFO] Skipped: repository directory does not exist "
                "locally, changelog generation is not possible."
            )
            continue

        print(f"\nRepository: {identifier}")
        print(f"Path:       {repo_dir}")
        print("----------------------------------------")

        try:
            tags = get_tags(cwd=repo_dir)
        except Exception as exc:
            print(f"[ERROR] Could not read git tags: {exc}")
            tags = []

        from_ref: Optional[str] = None
        to_ref: Optional[str] = None

        if range_arg:
            # Explicit range provided
            if ".." in range_arg:
                # Format: A..B
                parts = range_arg.split("..", 1)
                from_ref = parts[0] or None
                to_ref = parts[1] or None
            else:
                # Single tag, compute previous + current
                prev_tag, cur_tag = _find_previous_and_current_tag(
                    tags,
                    target_tag=range_arg,
                )
                if cur_tag is None:
                    print(f"[WARN] Tag {range_arg!r} not found or not a SemVer tag.")
                    print("[INFO] Falling back to full history.")
                    from_ref = None
                    to_ref = None
                else:
                    from_ref = prev_tag
                    to_ref = cur_tag
        else:
            # No explicit range: last two SemVer tags (or fallback)
            prev_tag, cur_tag = _find_previous_and_current_tag(tags)
            from_ref = prev_tag
            to_ref = cur_tag  # may be None if no tags

        changelog_text = generate_changelog(
            cwd=repo_dir,
            from_ref=from_ref,
            to_ref=to_ref,
            include_merges=False,
        )

        if from_ref or to_ref:
            ref_desc = f"{from_ref or '<root>'}..{to_ref or 'HEAD'}"
        else:
            ref_desc = "<full history>"

        print(f"Range: {ref_desc}")
        print()
        print(changelog_text)
        print()
