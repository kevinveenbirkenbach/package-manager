from __future__ import annotations

import subprocess

from pkgmgr.actions.branch.gc import END_OF_OPTIONS
from pkgmgr.core.git.errors import GitBaseError
from pkgmgr.core.git.run import SCAN_FLAGS, SCAN_TIMEOUT, _scan_env, run

from .model import ReviewError

BRANCH_NAMESPACES = ("refs/heads/", "refs/remotes/")


def git_text(args: list[str], cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", *SCAN_FLAGS, "-c", "core.quotepath=false", *args],
            cwd=cwd,
            env=_scan_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=SCAN_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise ReviewError(f"git {args[0]} timed out") from None
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", "replace").strip().splitlines()
        reason = stderr[0] if stderr else f"exit code {result.returncode}"
        raise ReviewError(f"git {args[0]} failed: {reason}")
    return result.stdout.decode("utf-8", "replace")


def git_optional(args: list[str], cwd: str) -> str | None:
    try:
        return run(args, cwd=cwd, scan=True) or None
    except GitBaseError:
        return None


def top_level(cwd: str) -> str:
    top = git_optional(["rev-parse", "--show-toplevel"], cwd)
    if top is None:
        raise ReviewError(f"not inside a git working copy: {cwd!r}")
    return top


def base_ref(base: str, top: str) -> tuple[str, str]:
    names = (
        [base]
        if base.startswith(BRANCH_NAMESPACES)
        else [namespace + base for namespace in BRANCH_NAMESPACES]
    )
    refs: dict[str, str] = {}
    for name in names:
        sha = git_optional(
            ["show-ref", "--verify", "--hash", END_OF_OPTIONS, name], top
        )
        if sha is not None:
            refs[name] = sha
    if len(refs) > 1:
        raise ReviewError(f"ambiguous base ref: {base!r} names {' and '.join(refs)}")
    if not refs:
        raise ReviewError(
            f"unknown base ref: {base!r}, expected a branch under "
            f"{' or '.join(BRANCH_NAMESPACES)}"
        )
    [(name, sha)] = refs.items()
    commit = git_optional(
        ["rev-parse", "--verify", "--quiet", END_OF_OPTIONS, f"{sha}^{{commit}}"], top
    )
    if commit is None:
        raise ReviewError(f"base ref {name!r} does not point to a commit")
    return name, commit
