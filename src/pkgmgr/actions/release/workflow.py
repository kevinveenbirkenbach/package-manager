from __future__ import annotations
from typing import Optional

import os
import sys
from typing import Optional

from pkgmgr.actions.branch import close_branch
from pkgmgr.core.git import get_current_branch, GitError

from .files import (
    update_changelog,
    update_debian_changelog,
    update_flake_version,
    update_pkgbuild_version,
    update_pyproject_version,
    update_spec_changelog,
    update_spec_version,
)
from .git_ops import (
    ensure_clean_and_synced,
    is_highest_version_tag,
    run_git_command,
    update_latest_tag,
)
from .prompts import confirm_proceed_release, should_delete_branch
from .versioning import bump_semver, determine_current_version


def _release_impl(
    pyproject_path: str = "pyproject.toml",
    changelog_path: str = "CHANGELOG.md",
    release_type: str = "patch",
    message: Optional[str] = None,
    preview: bool = False,
    close: bool = False,
    force: bool = False,
) -> None:
    # Determine current branch early
    try:
        branch = get_current_branch() or "main"
    except GitError:
        branch = "main"
    print(f"Releasing on branch: {branch}")

    # Pull BEFORE making any modifications
    ensure_clean_and_synced(preview=preview)

    current_ver = determine_current_version()
    new_ver = bump_semver(current_ver, release_type)
    new_ver_str = str(new_ver)
    new_tag = new_ver.to_tag(with_prefix=True)

    mode = "PREVIEW" if preview else "REAL"
    print(f"Release mode: {mode}")
    print(f"Current version: {current_ver}")
    print(f"New version:     {new_ver_str} ({release_type})")

    repo_root = os.path.dirname(os.path.abspath(pyproject_path))

    update_pyproject_version(pyproject_path, new_ver_str, preview=preview)
    changelog_message = update_changelog(
        changelog_path,
        new_ver_str,
        message=message,
        preview=preview,
    )

    flake_path = os.path.join(repo_root, "flake.nix")
    update_flake_version(flake_path, new_ver_str, preview=preview)

    pkgbuild_path = os.path.join(repo_root, "PKGBUILD")
    update_pkgbuild_version(pkgbuild_path, new_ver_str, preview=preview)

    spec_path = os.path.join(repo_root, "package-manager.spec")
    update_spec_version(spec_path, new_ver_str, preview=preview)

    effective_message: Optional[str] = message
    if effective_message is None and isinstance(changelog_message, str):
        if changelog_message.strip():
            effective_message = changelog_message.strip()

    debian_changelog_path = os.path.join(repo_root, "debian", "changelog")
    package_name = os.path.basename(repo_root) or "package-manager"

    update_debian_changelog(
        debian_changelog_path,
        package_name=package_name,
        new_version=new_ver_str,
        message=effective_message,
        preview=preview,
    )

    update_spec_changelog(
        spec_path=spec_path,
        package_name=package_name,
        new_version=new_ver_str,
        message=effective_message,
        preview=preview,
    )

    commit_msg = f"Release version {new_ver_str}"
    tag_msg = effective_message or commit_msg

    files_to_add = [
        pyproject_path,
        changelog_path,
        flake_path,
        pkgbuild_path,
        spec_path,
        debian_changelog_path,
    ]
    existing_files = [p for p in files_to_add if p and os.path.exists(p)]

    if preview:
        for path in existing_files:
            print(f"[PREVIEW] Would run: git add {path}")
        print(f'[PREVIEW] Would run: git commit -am "{commit_msg}"')
        print(f'[PREVIEW] Would run: git tag -a {new_tag} -m "{tag_msg}"')
        print(f"[PREVIEW] Would run: git push origin {branch}")
        print(f"[PREVIEW] Would run: git push origin {new_tag}")

        if is_highest_version_tag(new_tag):
            update_latest_tag(new_tag, preview=True)
        else:
            print(f"[PREVIEW] Skipping 'latest' update (tag {new_tag} is not the highest).")

        if close and branch not in ("main", "master"):
            if force:
                print(f"[PREVIEW] Would delete branch {branch} (forced).")
            else:
                print(f"[PREVIEW] Would ask whether to delete branch {branch} after release.")
        return

    for path in existing_files:
        run_git_command(f"git add {path}")

    run_git_command(f'git commit -am "{commit_msg}"')
    run_git_command(f'git tag -a {new_tag} -m "{tag_msg}"')

    # Push branch and ONLY the newly created version tag (no --tags)
    run_git_command(f"git push origin {branch}")
    run_git_command(f"git push origin {new_tag}")

    # Update 'latest' only if this is the highest version tag
    try:
        if is_highest_version_tag(new_tag):
            update_latest_tag(new_tag, preview=False)
        else:
            print(f"[INFO] Skipping 'latest' update (tag {new_tag} is not the highest).")
    except GitError as exc:
        print(f"[WARN] Failed to update floating 'latest' tag for {new_tag}: {exc}")
        print("'latest' tag was not updated.")

    print(f"Release {new_ver_str} completed.")

    if close:
        if branch in ("main", "master"):
            print(f"[INFO] close=True but current branch is {branch}; skipping branch deletion.")
            return

        if not should_delete_branch(force=force):
            print(f"[INFO] Branch deletion declined. Keeping branch {branch}.")
            return

        print(f"[INFO] Deleting branch {branch} after successful release...")
        try:
            close_branch(name=branch, base_branch="main", cwd=".")
        except Exception as exc:
            print(f"[WARN] Failed to close branch {branch} automatically: {exc}")


def release(
    pyproject_path: str = "pyproject.toml",
    changelog_path: str = "CHANGELOG.md",
    release_type: str = "patch",
    message: Optional[str] = None,
    preview: bool = False,
    force: bool = False,
    close: bool = False,
) -> None:
    if preview:
        _release_impl(
            pyproject_path=pyproject_path,
            changelog_path=changelog_path,
            release_type=release_type,
            message=message,
            preview=True,
            close=close,
            force=force,
        )
        return

    # If force or non-interactive: no preview+confirmation step
    if force or (not sys.stdin.isatty()):
        _release_impl(
            pyproject_path=pyproject_path,
            changelog_path=changelog_path,
            release_type=release_type,
            message=message,
            preview=False,
            close=close,
            force=force,
        )
        return

    print("[INFO] Running preview before actual release...\n")
    _release_impl(
        pyproject_path=pyproject_path,
        changelog_path=changelog_path,
        release_type=release_type,
        message=message,
        preview=True,
        close=close,
        force=force,
    )

    if not confirm_proceed_release():
        print()
        return

    print("\n[INFO] Running REAL release...\n")
    _release_impl(
        pyproject_path=pyproject_path,
        changelog_path=changelog_path,
        release_type=release_type,
        message=message,
        preview=False,
        close=close,
        force=force,
    )
