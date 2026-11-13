from __future__ import annotations

import argparse


def add_branch_subparsers(
    subparsers: argparse._SubParsersAction,
) -> None:
    """
    Register branch command and its subcommands.
    """
    branch_parser = subparsers.add_parser(
        "branch",
        help="Branch-related utilities (e.g. open/close/drop feature branches)",
    )
    branch_subparsers = branch_parser.add_subparsers(
        dest="subcommand",
        help="Branch subcommands",
        required=True,
    )

    # -----------------------------------------------------------------------
    # branch open
    # -----------------------------------------------------------------------
    branch_open = branch_subparsers.add_parser(
        "open",
        help="Create and push a new branch on top of a base branch",
    )
    branch_open.add_argument(
        "name",
        nargs="?",
        help=(
            "Name of the new branch (optional; will be asked interactively if omitted)"
        ),
    )
    branch_open.add_argument(
        "--base",
        default="main",
        help="Base branch to create the new branch from (default: main)",
    )

    # -----------------------------------------------------------------------
    # branch close
    # -----------------------------------------------------------------------
    branch_close = branch_subparsers.add_parser(
        "close",
        help="Merge a feature branch into base and delete it",
    )
    branch_close.add_argument(
        "name",
        nargs="?",
        help=(
            "Name of the branch to close (optional; current branch is used if omitted)"
        ),
    )
    branch_close.add_argument(
        "--base",
        default="main",
        help=(
            "Base branch to merge into (default: main; falls back to master "
            "internally if main does not exist)"
        ),
    )
    branch_close.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Skip confirmation prompt and close the branch directly",
    )

    # -----------------------------------------------------------------------
    # branch drop
    # -----------------------------------------------------------------------
    branch_drop = branch_subparsers.add_parser(
        "drop",
        help="Delete a branch locally and on origin (without merging)",
    )
    branch_drop.add_argument(
        "name",
        nargs="?",
        help=(
            "Name of the branch to drop (optional; current branch is used if omitted)"
        ),
    )
    branch_drop.add_argument(
        "--base",
        default="main",
        help=(
            "Base branch used to protect main/master from deletion "
            "(default: main; falls back to master internally)"
        ),
    )
    branch_drop.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Skip confirmation prompt and drop the branch directly",
    )

    branch_cleanup = branch_subparsers.add_parser(
        "cleanup",
        help=(
            "Remove merged branches that no worktree holds, locally and on the "
            "remotes (dry-run unless --apply)"
        ),
    )
    add_apply_options(branch_cleanup)
    branch_cleanup.add_argument(
        "--local",
        action="store_true",
        help=(
            "Delete only local branches whose tip is an ancestor of origin's "
            "remote-tracking default (else the only remote's) or a --merged-into "
            "REF, against the planned sha; refuse a repository without such a "
            "default, one git fails on, one whose holds cannot be read, one "
            "whose git dir is neither its common dir nor directly under "
            "<common>/worktrees/ and one with a symlink in or below refs, "
            "packed-refs, reftable or logs/refs, and still print the plan; skip "
            "a symbolic branch, a branch any symbolic ref of any worktree names, "
            "a branch a worktree, worktree registration, rebase or bisect holds, "
            "a --merged-into target, a branch with branch.<name>.deleteMerged "
            "false in any worktree's or the system config and the local "
            "upstream of a branch that stays, also of one --branch or --exclude "
            "leaves out; "
            "run git without inherited GIT_* variables but "
            "GIT_CEILING_DIRECTORIES; the keep config reads run once with the "
            "caller's GIT_CONFIG_* variables and once with the default system "
            "and passwd-home config, and either read's keep counts; read no "
            "forge token; "
            "never fetch, push, delete a remote branch, run docker or hooks, or "
            "refresh the branch tree file; exit 1 when an item failed, else 2 "
            "when a repository was refused, else 0; exit 2 without a plan when, "
            "without --all, the current directory is in no git repository, its "
            "git dir is neither its common dir nor directly under "
            "<common>/worktrees/, its main worktree belongs to another "
            "repository or its path or git output is not UTF-8, on --apply "
            "outside the host PID namespace, on a --merged-into REF that is not "
            "exactly one branch or remote-tracking ref (X~0, X^0, X@{0}, a sha), "
            "and on a --branch "
            "that matches nothing; meant for working clones"
        ),
    )

    branch_purge = branch_subparsers.add_parser(
        "purge",
        help="Delete unmerged or dirty branches after a confirmation per item",
    )

    for sub in (branch_cleanup, branch_purge):
        add_scan_options(sub)
        add_min_age_option(sub)

    branch_tree = branch_subparsers.add_parser(
        "tree",
        help=(
            "Print the branches and worktrees of every pkgmgr-managed repository "
            "with their cleanup state, without fetching"
        ),
    )
    branch_tree.add_argument(
        "--format",
        choices=("json", "yaml"),
        default="json",
        help="Output format (default: json)",
    )
    branch_tree.add_argument(
        "--output",
        metavar="FILE",
        help="Write atomically to FILE instead of stdout",
    )


def add_apply_options(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "--apply",
        action="store_true",
        help="Execute the plan instead of only printing it",
    )
    sub.add_argument(
        "--json",
        action="store_true",
        help="Print the plan as JSON",
    )


def add_scan_options(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "--all",
        action="store_true",
        help="Scan every pkgmgr-managed repository instead of the current one",
    )
    sub.add_argument(
        "--branch",
        action="append",
        default=[],
        metavar="NAME",
        help="Only this branch (or worktree path); repeatable",
    )
    sub.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="NAME",
        help="Skip this branch (or worktree path); repeatable",
    )
    sub.add_argument(
        "--merged-into",
        action="append",
        default=[],
        metavar="REF",
        help=(
            "Also count an item as merged when its commits are in REF (an "
            "integration line); REF is protected and a checkout at its tip "
            "counts as fresh; repeatable"
        ),
    )
    sub.add_argument(
        "--sizes",
        action="store_true",
        help="Measure each worktree's disk usage (du) into the plan",
    )


def add_min_age_option(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "--min-age",
        type=float,
        metavar="HOURS",
        help="Skip items whose newest commit, worktree index or changed file is younger",
    )
