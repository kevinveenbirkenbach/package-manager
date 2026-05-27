"""Re-deploy an existing release without modifying files or creating a new tag.

The release workflow normally bumps versions, rewrites packaging
manifests, commits, tags, pushes, and uploads to PyPI in one shot.
When a post-tag step fails mid-flight (typical examples: `git push`
rejected, `twine upload` aborted by a broken venv, `update-latest`
rejected by branch protection) the local tag still exists on HEAD but
the side effects downstream are incomplete.

`retry_release` re-runs the idempotent tail of that flow so a botched
release can be re-pushed without touching code or recreating tags:

  * `git push origin <branch> <tag>` for the existing HEAD tag
  * re-align the floating `latest` tag if HEAD tag is the highest

Publishing (PyPI etc.) stays the caller's responsibility — the publish
workflow is already idempotent (twine rejects duplicates per spec) and
can be invoked independently via the `publish` subcommand.
"""

from __future__ import annotations

import os

from pkgmgr.actions.publish.git_tags import head_semver_tags
from pkgmgr.core.git import GitRunError, run
from pkgmgr.core.git.queries import get_current_branch
from pkgmgr.core.version.semver import SemVer

from .git_ops import is_highest_version_tag, update_latest_tag


def retry_release(
    pyproject_path: str = "pyproject.toml",
    preview: bool = False,
) -> None:
    """Re-push the HEAD release without re-tagging or modifying any files."""
    try:
        branch = get_current_branch() or "main"
    except GitRunError:
        branch = "main"
    print(f"Retrying release push on branch: {branch}")

    tags = head_semver_tags(cwd=os.path.dirname(os.path.abspath(pyproject_path)))
    if not tags:
        raise RuntimeError(
            "No version tag on HEAD. Nothing to retry — "
            "run `pkgmgr release <type>` first to create a release."
        )
    tag = max(tags, key=SemVer.parse)
    print(f"Re-pushing existing tag: {tag}")

    run(["push", "origin", branch, tag], preview=preview)

    try:
        if is_highest_version_tag(tag):
            update_latest_tag(tag, preview=preview)
        else:
            print(f"[INFO] Skipping 'latest' update (tag {tag} is not the highest).")
    except GitRunError as exc:
        print(f"[WARN] Failed to update floating 'latest' tag for {tag}: {exc}")

    if preview:
        print(f"[PREVIEW] Retry push for {tag} would now complete.")
        return

    print(f"Retry push completed for {tag}.")
