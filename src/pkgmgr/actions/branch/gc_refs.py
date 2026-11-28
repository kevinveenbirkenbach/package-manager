from __future__ import annotations

import os

from pkgmgr.core.git import GitRunError, run

HELD_FILES = (
    ("rebase-merge/head-name", "rebase in progress"),
    ("rebase-merge/update-refs", "rebase in progress"),
    ("rebase-apply/head-name", "rebase in progress"),
    ("BISECT_START", "bisect in progress"),
)


def _git(args: list[str], cwd: str) -> str:
    return run(args, cwd=cwd, scan=True)


def _common_dir(cwd: str) -> str:
    return _git(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd)


def _symbolic(repo_root: str, prefix: str, git_dir: str = "") -> dict[str, str]:
    """
    List the resolvable refs under a prefix with their symref targets.

    Args:
        repo_root: main worktree root of the repository.
        prefix: a ref prefix such as `refs/heads` or `refs/remotes/origin`.
        git_dir: the git common dir (shared refs plus the main worktree's own)
            or a `worktrees/<id>` dir whose refs to list, or "" for the refs
            as repo_root's worktree sees them.

    Returns:
        Full ref name -> the ref it points to, or "" for a plain ref.
    """
    args = ["for-each-ref", "--format=%(refname)%00%(symref)", prefix]
    out = _git([f"--git-dir={git_dir}", *args] if git_dir else args, repo_root)
    return dict(line.split("\x00", 1) for line in out.splitlines())


def _worktree_heads(repo_root: str, git_dirs: list[str]) -> dict[str, str]:
    """
    Read the branch every worktree's HEAD names, on any ref backend.

    Args:
        repo_root: main worktree root of the repository.
        git_dirs: the git common dir first, then each `worktrees/<id>`.

    Returns:
        Branch name -> skip reason, from `git --git-dir=<dir> symbolic-ref
        HEAD` for each of them, whatever its id.

    Raises:
        GitBaseError: when a HEAD is neither readable nor detached.
    """
    heads: dict[str, str] = {}
    for git_dir in git_dirs:
        try:
            target = _git(
                [f"--git-dir={git_dir}", "symbolic-ref", "--quiet", "HEAD"], repo_root
            )
        except GitRunError as exc:
            if exc.returncode == 1:
                continue
            raise
        if target.startswith("refs/heads/"):
            heads.setdefault(
                target.removeprefix("refs/heads/"), f"checked out in {git_dir}"
            )
    return heads


def _git_dirs(repo_root: str) -> list[str]:
    """
    List the git dirs of every worktree of the repository.

    Args:
        repo_root: main worktree root of the repository.

    Returns:
        The git common dir, then each entry of `<common>/worktrees/`, whatever
        its id and whether `git worktree list` shows it.
    """
    common = _common_dir(repo_root)
    base = os.path.join(common, "worktrees")
    entries = sorted(os.listdir(base)) if os.path.isdir(base) else []
    return [common, *(os.path.join(base, entry) for entry in entries)]


def _held_branches(repo_root: str) -> dict[str, str]:
    """
    Find the local branches that something besides a listed worktree holds.

    Args:
        repo_root: main worktree root of the repository.

    Returns:
        Branch name -> skip reason: a symbolic branch, the branch any symbolic
        ref under `refs/` (also a tag or remote-tracking one) or under the
        main worktree's or any registration's `refs/worktree/` names, the HEAD
        of the main repository and of every `worktrees/<id>` registration,
        also one `git worktree list` omits, each rebase-merge and rebase-apply
        head-name, an interactive rebase's update-refs and BISECT_START; all
        read through the git common dir, whichever worktree repo_root is.

    Raises:
        GitBaseError: when git cannot read a registration, symref or HEAD.
        OSError: when a state file exists but cannot be read.
        ValueError: when a state file is not UTF-8.
    """
    git_dirs = _git_dirs(repo_root)
    held: dict[str, str] = {}
    symrefs = _symbolic(repo_root, "refs", git_dirs[0])
    for git_dir in git_dirs[1:]:
        for ref, target in _symbolic(repo_root, "refs/worktree", git_dir).items():
            symrefs[f"worktrees/{os.path.basename(git_dir)}/{ref}"] = target
    for ref, target in symrefs.items():
        if target and ref.startswith("refs/heads/"):
            held.setdefault(
                ref.removeprefix("refs/heads/"), f"symbolic ref to {target}"
            )
        if target.startswith("refs/heads/"):
            held.setdefault(
                target.removeprefix("refs/heads/"), f"target of symbolic ref {ref}"
            )
    for branch, reason in _worktree_heads(repo_root, git_dirs).items():
        held.setdefault(branch, reason)
    for git_dir in git_dirs:
        for name, operation in HELD_FILES:
            try:
                with open(os.path.join(git_dir, name), encoding="utf-8") as fh:
                    lines = fh.read().splitlines()
            except FileNotFoundError:
                continue
            for line in lines:
                ref = line.strip().removeprefix("ref: ")
                if ref.startswith("refs/heads/") or name == "BISECT_START":
                    held.setdefault(
                        ref.removeprefix("refs/heads/"), f"{operation} in {git_dir}"
                    )
    return held
