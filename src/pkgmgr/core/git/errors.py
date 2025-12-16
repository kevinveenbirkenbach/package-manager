from __future__ import annotations


class GitError(RuntimeError):
    """Base error raised for Git related failures."""


class GitCommandError(GitError):
    """
    Base class for state-changing git command failures.

    Use subclasses to provide stable error types for callers.
    """
    def __init__(self, message: str, *, cwd: str = ".") -> None:
        super().__init__(message)
        self.cwd = cwd