from __future__ import annotations

import os

from pkgmgr.actions.branch.gc import GITLINK
from pkgmgr.core.git.errors import GitBaseError, GitRunError
from pkgmgr.core.git.queries import FILTER_CONFIG, local_config
from pkgmgr.core.git.run import run

from .model import FileView, ReviewError
from .repo import git_text

ATTRIBUTE_BINARY = (
    "{} is shown as binary because {}, not because of its content: "
    "run git diff --text to see it."
)
UNSET = "a gitattributes entry unsets its diff attribute"
DRIVER = "its gitattributes diff driver {0} sets diff.{0}.binary"
RUNS = "a command git would run on this host"


def hidden_entries(top: str) -> list[str]:
    listing = git_text(["ls-files", "-v", "-z"], top)
    return [
        f"Index entry {entry[2:]} is marked "
        f"{'skip-worktree' if entry[0] == 'S' else 'assume-unchanged'}: "
        "its worktree changes are not shown."
        for entry in listing.split("\0")
        if entry[:1] == "S" or entry[:1].islower()
    ]


def _binary_drivers(top: str) -> set[str]:
    try:
        out = run(
            ["config", "-z", "--type=bool", "--get-regexp", r"^diff\..*\.binary$"],
            cwd=top,
            scan=True,
        )
    except GitRunError as exc:
        if exc.returncode == 1:
            return set()
        raise ReviewError("git config failed reading diff.<driver>.binary") from None
    last: dict[str, str] = {}
    for record in filter(None, out.split("\0")):
        key, _, value = record.partition("\n")
        last[key.removeprefix("diff.").removesuffix(".binary")] = value
    return {driver for driver, value in last.items() if value == "true"}


def attribute_binary(files: list[FileView], top: str) -> list[str]:
    paths = list(dict.fromkeys(view.diff.path for view in files if view.diff.binary))
    if not paths:
        return []
    fields = git_text(["check-attr", "-z", "diff", "--", *paths], top).split("\0")
    reasons = {
        **{driver: DRIVER.format(driver) for driver in _binary_drivers(top)},
        "unset": UNSET,
    }
    return [
        ATTRIBUTE_BINARY.format(path, reasons[value])
        for path, value in zip(fields[0::3], fields[2::3])
        if value in reasons
    ]


def _submodule_configs(top: str, prefix: str) -> list[str]:
    """
    Args:
        top: Real path of the top-level working tree.
        prefix: Submodule path below ``top`` whose gitlinks are walked, or ""
            for the top level itself.

    Returns:
        One reason per populated submodule, nested ones included, whose
        config defines a filter or cannot be read. A gitlink behind a symbolic
        link or without a ``.git`` is skipped: git runs nothing there either.
    """
    listing = git_text(["ls-files", "--stage", "-z"], os.path.join(top, prefix))
    gitlinks = dict.fromkeys(
        path
        for meta, _, path in (entry.partition("\t") for entry in listing.split("\0"))
        if meta.startswith(f"{GITLINK} ")
    )
    reasons: list[str] = []
    for path in gitlinks:
        relative = os.path.join(prefix, path)
        full = os.path.join(top, relative)
        if os.path.realpath(full) != full or not os.path.lexists(
            os.path.join(full, ".git")
        ):
            continue
        try:
            keys = local_config(full, FILTER_CONFIG)
            nested = _submodule_configs(top, relative)
        except (GitBaseError, ReviewError):
            reasons.append(
                f"the config of submodule {relative} cannot be read, so its "
                "filters cannot be ruled out"
            )
            continue
        if keys:
            reasons.append(
                f"the config of submodule {relative} defines {', '.join(keys)}, {RUNS}"
            )
        reasons.extend(nested)
    return reasons


def unsafe_configs(top: str) -> list[str]:
    keys = local_config(top, FILTER_CONFIG)
    own = [f"the repository config defines {', '.join(keys)}, {RUNS}"] if keys else []
    return own + _submodule_configs(os.path.realpath(top), "")
