from __future__ import annotations

import json
import sys

from pkgmgr.core.git.errors import GitBaseError
from pkgmgr.core.git.run import run

from .flow import (
    NONE_LISTED,
    Flow,
    FlowError,
    check_names,
    clear_flow,
    describe,
    mismatch,
    read_flow,
    write_flow,
)

Located = tuple[str, str, str | None]


def locate(path: str) -> Located:
    """
    Args:
        path: any directory inside the worktree.

    Returns:
        The worktree root, its own git directory (`.git` of the main
        worktree, `<common>/worktrees/<id>` of a linked one) and its branch,
        None when detached.

    Raises:
        GitBaseError: path is not inside a worktree, e.g. a bare repository.
        OSError: path is no directory.
        ValueError: a path git printed spans lines.
    """
    out = run(
        ["rev-parse", "--absolute-git-dir", "--show-toplevel"], cwd=path, scan=True
    )
    git_dir, top = out.split("\n")
    try:
        ref = run(["symbolic-ref", "--quiet", "HEAD"], cwd=top, scan=True)
    except GitBaseError:
        ref = ""
    branch = ref.removeprefix("refs/heads/") if ref.startswith("refs/heads/") else None
    return top, git_dir, branch


def _located(path: str) -> Located | None:
    try:
        return locate(path)
    except (GitBaseError, OSError, ValueError) as exc:
        print(
            f"Refusing: {path} is not a git worktree: {describe(exc)}",
            file=sys.stderr,
        )
        return None


def _report(located: Located, flow: Flow, as_json: bool) -> None:
    top, git_dir, branch = located
    result = {
        "worktree": top,
        "git_dir": git_dir,
        "branch": branch,
        "flow_branch": flow.branch,
        "pull": flow.pull,
        "push": flow.push,
        "source": flow.source,
        "warnings": flow.warnings + mismatch(flow, branch),
    }
    if as_json:
        print(json.dumps(result, indent=2))
        return
    for warning in result["warnings"]:
        print(f"WARN     {warning}")
    for key in ("pull", "push"):
        print(f"{key}: {', '.join(result[key]) or NONE_LISTED}")


def worktree_flow_show(path: str, *, as_json: bool) -> int:
    """
    Print the flow of the worktree at path.

    Args:
        path: any directory inside the worktree.
        as_json: print the result as JSON instead of text.

    Returns:
        0, also without a flow or with an invalid file; 2 when path is not a
        git worktree.
    """
    located = _located(path)
    if located is None:
        return 2
    _report(located, read_flow(located[1]), as_json)
    return 0


def worktree_flow_set(
    path: str, *, pull: list[str], push: list[str], as_json: bool
) -> int:
    """
    Replace both lists of the worktree's flow and print the result.

    Args:
        path: any directory inside the worktree.
        pull: refs merged into the branch before a gate, deploy or merge, in
            order; may be empty.
        push: branches the branch is merged into when finished, in order;
            may be empty.
        as_json: print the result as JSON instead of text.

    Returns:
        0 when written, 1 when the write failed, 2 on an invalid name or when
        path is not a git worktree; nothing is written unless 0.
    """
    try:
        pull, push = check_names("pull", pull), check_names("push", push)
    except FlowError as exc:
        print(f"Refusing: {exc}", file=sys.stderr)
        return 2
    located = _located(path)
    if located is None:
        return 2
    try:
        write_flow(located[1], located[2], pull, push)
    except OSError as exc:
        print(f"Cannot write the flow of {located[0]}: {exc}", file=sys.stderr)
        return 1
    _report(located, read_flow(located[1]), as_json)
    return 0


def worktree_flow_clear(path: str, *, as_json: bool) -> int:
    """
    Remove the worktree's flow and print the empty result.

    Args:
        path: any directory inside the worktree.
        as_json: print the result as JSON instead of text.

    Returns:
        0 when no flow is left, 1 when the removal failed, 2 when path is not
        a git worktree.
    """
    located = _located(path)
    if located is None:
        return 2
    try:
        clear_flow(located[1])
    except OSError as exc:
        print(f"Cannot clear the flow of {located[0]}: {exc}", file=sys.stderr)
        return 1
    _report(located, read_flow(located[1]), as_json)
    return 0
