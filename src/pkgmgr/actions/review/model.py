from __future__ import annotations

from dataclasses import dataclass


class ReviewError(RuntimeError):
    pass


@dataclass(frozen=True)
class Line:
    kind: str
    old: int | None
    new: int | None
    text: str


@dataclass(frozen=True)
class Hunk:
    header: str
    new_start: int
    lines: tuple[Line, ...]


@dataclass(frozen=True)
class FileDiff:
    old_path: str | None
    new_path: str | None
    status: str
    binary: bool
    mode_change: str | None
    hunks: tuple[Hunk, ...]

    @property
    def path(self) -> str:
        return self.new_path if self.new_path is not None else str(self.old_path)

    @property
    def moved(self) -> bool:
        return self.status in ("renamed", "copied")

    @property
    def added(self) -> int:
        return sum(
            1 for hunk in self.hunks for line in hunk.lines if line.kind == "add"
        )

    @property
    def removed(self) -> int:
        return sum(
            1 for hunk in self.hunks for line in hunk.lines if line.kind == "del"
        )


@dataclass(frozen=True)
class FileView:
    anchor: str
    diff: FileDiff
    detail: str | None
    link_base: str | None
    link: str | None
    hunks: tuple[Hunk, ...]
    hidden: int

    @property
    def search(self) -> str:
        if self.diff.moved:
            return f"{self.diff.old_path} {self.diff.new_path}"
        return self.diff.path


@dataclass(frozen=True)
class Section:
    key: str
    title: str
    files: tuple[FileView, ...]
    skipped: str | None

    @property
    def added(self) -> int:
        return sum(view.diff.added for view in self.files)

    @property
    def removed(self) -> int:
        return sum(view.diff.removed for view in self.files)


@dataclass(frozen=True)
class Commit:
    anchor: str
    short: str
    author: str
    subject: str
    body: str
    files: tuple[FileView, ...]

    @property
    def added(self) -> int:
        return sum(view.diff.added for view in self.files)

    @property
    def removed(self) -> int:
        return sum(view.diff.removed for view in self.files)


@dataclass(frozen=True)
class Note:
    title: str
    text: str


@dataclass(frozen=True)
class Review:
    top_level: str
    name: str
    branch: str | None
    head: str | None
    index_tree: str
    base: str | None
    base_short: str | None
    warnings: tuple[str, ...]
    notes: tuple[Note, ...]
    sections: tuple[Section, ...]
    commits: tuple[Commit, ...]

    @property
    def commit_files(self) -> int:
        return sum(len(commit.files) for commit in self.commits)

    @property
    def commit_added(self) -> int:
        return sum(commit.added for commit in self.commits)

    @property
    def commit_removed(self) -> int:
        return sum(commit.removed for commit in self.commits)
