from __future__ import annotations

import subprocess

from pkgmgr.core.git import GitError


def run_git_command(cmd: str) -> None:
    print(f"[GIT] {cmd}")
    try:
        subprocess.run(
            cmd,
            shell=True,
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] Git command failed: {cmd}")
        print(f"        Exit code: {exc.returncode}")
        if exc.stdout:
            print("\n" + exc.stdout)
        if exc.stderr:
            print("\n" + exc.stderr)
        raise GitError(f"Git command failed: {cmd}") from exc


def _capture(cmd: str) -> str:
    res = subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True)
    return (res.stdout or "").strip()


def ensure_clean_and_synced(preview: bool = False) -> None:
    """
    Always run a pull BEFORE modifying anything.
    Uses --ff-only to avoid creating merge commits automatically.
    If no upstream is configured, we skip.
    """
    upstream = _capture("git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null")
    if not upstream:
        print("[INFO] No upstream configured for current branch. Skipping pull.")
        return

    if preview:
        print("[PREVIEW] Would run: git fetch origin --prune --tags --force")
        print("[PREVIEW] Would run: git pull --ff-only")
        return

    print("[INFO] Syncing with remote before making any changes...")
    run_git_command("git fetch origin --prune --tags --force")
    run_git_command("git pull --ff-only")

def is_highest_version_tag(tag: str) -> bool:
    """
    Return True if `tag` is the highest version among all tags matching v*.
    Comparison uses `sort -V` for natural version ordering.
    """
    all_v = _capture("git tag --list 'v*'")
    if not all_v:
        return True  # No tags yet, so the current tag is the highest

    # Get the latest tag in natural version order
    latest = _capture("git tag --list 'v*' | sort -V | tail -n1")
    print(f"[INFO] Latest tag: {latest}, Current tag: {tag}")
    
    # Ensure that the current tag is always considered the highest if it's the latest one
    return tag >= latest  # Use comparison operator to consider all future tags


def update_latest_tag(new_tag: str, preview: bool = False) -> None:
    """
    Move the floating 'latest' tag to the newly created release tag.

    Notes:
    - We dereference the tag object via `<tag>^{}` so that 'latest' points to the commit.
    - 'latest' is forced (floating tag), therefore the push uses --force.
    """
    target_ref = f"{new_tag}^{{}}"
    print(f"[INFO] Updating 'latest' tag to point at {new_tag} (commit {target_ref})...")

    if preview:
        print(
            f'[PREVIEW] Would run: git tag -f -a latest {target_ref} '
            f'-m "Floating latest tag for {new_tag}"'
        )
        print("[PREVIEW] Would run: git push origin latest --force")
        return

    run_git_command(
        f'git tag -f -a latest {target_ref} -m "Floating latest tag for {new_tag}"'
    )
    run_git_command("git push origin latest --force")
