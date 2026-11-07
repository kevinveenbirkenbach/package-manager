from __future__ import annotations

import os

from pkgmgr.core.git.run import END_OF_OPTIONS

from .checks import attribute_binary, hidden_entries, unsafe_configs
from .diff import parse_patch
from .files import read_note, untracked_views
from .model import Commit, Review, Section
from .repo import base_ref, git_optional, git_text, top_level
from .views import file_views

DIFF_FLAGS = [
    "--no-color",
    "--no-ext-diff",
    "--no-textconv",
    "-M",
    "--submodule=short",
    "--ignore-submodules=none",
    "--src-prefix=a/",
    "--dst-prefix=b/",
]


def _commit(sha: str, anchor: str, top: str, limit: int) -> Commit:
    meta = git_text(
        [
            "show",
            "-s",
            "--no-color",
            "--no-show-signature",
            "--format=%h%x00%an <%ae>%x00%s%x00%b",
            END_OF_OPTIONS,
            sha,
        ],
        top,
    )
    short, author, subject, body = meta.split("\0", 3)
    patch = git_text(
        [
            "show",
            "--format=",
            "--no-show-signature",
            "--diff-merges=first-parent",
            *DIFF_FLAGS,
            END_OF_OPTIONS,
            sha,
        ],
        top,
    )
    return Commit(
        anchor=anchor,
        short=short,
        author=author,
        subject=subject,
        body=body.rstrip("\n"),
        files=file_views(parse_patch(patch), anchor, top, limit),
    )


def collect_review(
    cwd: str, max_file_lines: int, base: str | None, notes: list[str]
) -> Review:
    """
    Args:
        cwd: Directory inside the git working copy to review.
        max_file_lines: Diff lines shown per file before the rest is summarised.
        base: Branch, under refs/heads/ or refs/remotes/, whose ``REF..HEAD``
            commits are listed, or None for no Commits section.
        notes: Regular text files shown verbatim at the top, relative to
            ``cwd``; a symbolic link anywhere in the path is refused.

    Returns:
        The collected Review model.
    """
    top = top_level(cwd)
    base_name, base_sha = (None, None) if base is None else base_ref(base, top)
    note_items = tuple(read_note(path, cwd) for path in notes)
    unsafe = unsafe_configs(top)
    skipped = (
        f"Unstaged changes and index tree not computed: {'; '.join(unsafe)}."
        if unsafe
        else None
    )
    staged = Section(
        key="staged",
        title="Staged",
        files=file_views(
            parse_patch(git_text(["diff", "--cached", *DIFF_FLAGS], top)),
            "staged",
            top,
            max_file_lines,
        ),
        skipped=None,
    )
    unstaged = Section(
        key="unstaged",
        title="Unstaged",
        files=()
        if skipped
        else file_views(
            parse_patch(git_text(["diff", *DIFF_FLAGS], top)),
            "unstaged",
            top,
            max_file_lines,
        ),
        skipped=skipped,
    )
    untracked = Section(
        key="untracked",
        title="Untracked",
        files=untracked_views(top, max_file_lines),
        skipped=None,
    )
    commits: tuple[Commit, ...] = ()
    if base_sha is not None:
        shas = git_text(["rev-list", END_OF_OPTIONS, f"{base_sha}..HEAD"], top)
        commits = tuple(
            _commit(sha, f"commit-{index}", top, max_file_lines)
            for index, sha in enumerate(shas.split(), 1)
        )
    tracked = [
        *staged.files,
        *unstaged.files,
        *(view for commit in commits for view in commit.files),
    ]
    return Review(
        top_level=top,
        name=os.path.basename(top),
        branch=git_optional(
            ["symbolic-ref", "--short", "-q", END_OF_OPTIONS, "HEAD"], top
        ),
        head=git_optional(
            ["rev-parse", "--verify", "--quiet", "--short", END_OF_OPTIONS, "HEAD"],
            top,
        ),
        index_tree="(not computed, see the warnings)"
        if skipped
        else git_optional(["write-tree"], top) or "(index has unmerged entries)",
        base=base_name,
        base_short=None
        if base_sha is None
        else git_text(["rev-parse", "--short", END_OF_OPTIONS, base_sha], top).strip(),
        warnings=tuple(
            ([skipped] if skipped else [])
            + hidden_entries(top)
            + attribute_binary(tracked, top)
        ),
        notes=note_items,
        sections=(staged, unstaged, untracked),
        commits=commits,
    )
