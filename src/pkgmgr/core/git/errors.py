from __future__ import annotations


class GitBaseError(RuntimeError):
    """Base error raised for Git related failures."""


class GitRunError(GitBaseError):
    """Base error raised for Git related failures."""


class GitNotRepositoryError(GitBaseError):
    """Raised when the current working directory is not a git repository."""


class GitQueryError(GitRunError):
    """Base class for read-only git query failures."""


class GitCommandError(GitRunError):
    """
    Base class for state-changing git command failures.

    Use subclasses to provide stable error types for callers.
    """

    def __init__(self, message: str, *, cwd: str = ".") -> None:
        super().__init__(message)
        if cwd in locals():
            self.cwd = cwd
