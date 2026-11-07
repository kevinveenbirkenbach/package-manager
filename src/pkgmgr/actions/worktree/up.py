from __future__ import annotations

import json
import os
import re
import sys

from pkgmgr.core.git.errors import GitRunError
from pkgmgr.core.git.queries import FILTER_CONFIG, local_config
from pkgmgr.core.git.run import END_OF_OPTIONS, run

from .hooks import INIT_HOOK, defined_in, hook_command, run_hook
from .slots import next_slot, used_slots, write_slot

PORT_PREFIX = re.compile(r"^\d+/")
HOST_AND_PATH = re.compile(r"([^:/]+)[:/](.*)")
NETWORK_CONFIG = (
    r"^(core\.(sshcommand|gitproxy)|remote\..*\.(uploadpack|receivepack)"
    r"|credential\..*helper|url\..*\.insteadof|protocol\..*allow)$"
)


def worktree_location(url: str) -> str:
    """
    Map a remote URL to `<host>/<owner>/<repo>`.

    Args:
        url: remote URL in https, ssh or scp form.

    Returns:
        The host followed by the repository path, without `.git` or a port;
        a local path loses its leading slash, so it always stays relative.
    """
    rest = url.removesuffix(".git").split("://", 1)[-1].split("@", 1)[-1]
    match = HOST_AND_PATH.match(rest)
    if not match:
        return rest.strip("/")
    host, path = match.groups()
    return f"{host}/{PORT_PREFIX.sub('', path).strip('/')}"


def _common_dir(cwd: str) -> str:
    return run(
        ["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=cwd, scan=True
    )


def _inside(path: str, root: str) -> bool:
    real, base = os.path.realpath(path), os.path.realpath(root)
    return os.path.commonpath([real, base]) == base


def _ref_exists(repo: str, ref: str) -> bool:
    try:
        run(
            ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
            cwd=repo,
            scan=True,
        )
    except GitRunError:
        return False
    return True


def _commit_of(repo: str, ref: str) -> str:
    # worktree add reads a start point that begins with "-" as HEAD even after
    # "--" or --end-of-options, so it only ever gets the resolved commit id
    return run(
        ["rev-parse", "--verify", "--quiet", END_OF_OPTIONS, f"{ref}^{{commit}}"],
        cwd=repo,
        scan=True,
    )


def _default_base(repo: str) -> str:
    try:
        return run(
            ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=repo, scan=True
        )
    except GitRunError:
        return "origin/main" if _ref_exists(repo, "origin/main") else "origin/master"


def worktree_up(
    repo_dir: str,
    branch: str,
    *,
    base: str | None,
    worktrees_dir: str,
    path: str | None,
    hooks: dict[str, dict[str, list[str]]],
    as_json: bool,
) -> int:
    """
    Check a branch out into its own worktree under the standard path.

    Args:
        repo_dir: any directory inside the repository.
        branch: branch to check out; created from base when it exists nowhere.
        base: start point of a new branch; None takes origin's default branch.
        worktrees_dir: root of the standard path
            `<worktrees_dir>/<host>/<owner>/<repo>/<branch>`.
        path: exact checkout path instead of the standard one, e.g. a
            directory an agent sandbox releases; None keeps the standard path.
        hooks: pinned hooks by managed repository root realpath, from the
            CLI; the worktree-init hook runs only when the repository root is
            pinned there, never from the Makefile or by origin's URL.
        as_json: print the result as JSON instead of text.

    Returns:
        0 when the worktree is ready, 1 when the worktree-init hook failed
        (the worktree stays), 2 when refused.
    """
    try:
        common = _common_dir(repo_dir)
        root = os.path.dirname(common)
        url = run(["remote", "get-url", "--", "origin"], cwd=root, scan=True)
        run(["check-ref-format", "--branch", branch], cwd=root, scan=True)
        filters = local_config(root, FILTER_CONFIG)
    except GitRunError as exc:
        print(f"Refusing: {str(exc).splitlines()[0]}", file=sys.stderr)
        return 2
    if filters:
        print(
            f"Refusing: {', '.join(filters)} in the repository config would run "
            "on the checkout",
            file=sys.stderr,
        )
        return 2

    location = worktree_location(url)
    if path:
        path = os.path.abspath(os.path.expanduser(path))
    else:
        standard = os.path.expanduser(worktrees_dir)
        path = os.path.join(standard, location, branch)
        if not _inside(path, standard):
            print(f"Refusing: {path} lies outside {standard}", file=sys.stderr)
            return 2
    if os.path.lexists(path):
        print(f"Refusing: {path} already exists", file=sys.stderr)
        return 2

    slot = next_slot(used_slots(common))
    pinned = hooks.get(os.path.realpath(root), {}).get(INIT_HOOK)
    try:
        command = hook_command(INIT_HOOK, pinned, path, slot) if pinned else None
    except RuntimeError as exc:
        print(f"Refusing: {exc}", file=sys.stderr)
        return 2

    warnings: list[str] = []
    network = local_config(root, NETWORK_CONFIG)
    if network:
        warnings.append(f"fetch skipped: {', '.join(network)} in the repository config")
    else:
        try:
            run(
                ["fetch", "--quiet", "--no-auto-maintenance", "origin"],
                cwd=root,
                scan=True,
            )
        except GitRunError as exc:
            warnings.append(f"fetch failed: {str(exc).splitlines()[0]}")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    start: str | None = None
    if _ref_exists(root, f"refs/heads/{branch}"):
        origin, add = "existing", ["worktree", "add", "--", path, branch]
    elif _ref_exists(root, f"refs/remotes/origin/{branch}"):
        origin = f"tracking origin/{branch}"
        add = [
            "worktree",
            "add",
            "--track",
            "-b",
            branch,
            "--",
            path,
            f"origin/{branch}",
        ]
    else:
        start = base or _default_base(root)
        origin = f"new from {start}"
        add = ["worktree", "add", "--no-track", "-b", branch, "--", path]
    try:
        if start is not None:
            add.append(_commit_of(root, start))
        run(add, cwd=root, scan=True)
    except GitRunError as exc:
        print(f"Refusing: {str(exc).splitlines()[0]}", file=sys.stderr)
        return 2

    write_slot(path, slot)

    hook = "none"
    code = 0
    if command:
        try:
            ran = run_hook(INIT_HOOK, command, path, check=False, stdout=sys.stderr)
            failure = None if ran.returncode == 0 else str(ran.returncode)
        except (RuntimeError, OSError) as exc:
            failure = str(exc)
        hook = INIT_HOOK if failure is None else f"{INIT_HOOK} failed ({failure})"
        code = 0 if failure is None else 1
    else:
        makefile = defined_in(path, INIT_HOOK)
        if makefile:
            hook = f"not pinned: {INIT_HOOK} in {makefile}"

    result = {
        "path": path,
        "branch": branch,
        "origin": origin,
        "slot": slot,
        "hook": hook,
        "warnings": warnings,
    }
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        for warning in warnings:
            print(f"WARN     {warning}")
        for key in ("path", "branch", "origin", "slot", "hook"):
            print(f"{key:<8} {result[key]}")
    return code
