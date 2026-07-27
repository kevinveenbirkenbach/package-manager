from __future__ import annotations

from pkgmgr.core.git.commands import (
    GitCommitError,
    GitPushUpstreamError,
    add_all,
    branch_move,
    commit,
    init,
    push_upstream,
)

DEFAULT_BRANCH = "main"


class GitBootstrapper:
    def init_repo(self, repo_dir: str, preview: bool) -> None:
        init(initial_branch=DEFAULT_BRANCH, cwd=repo_dir, preview=preview)
        add_all(cwd=repo_dir, preview=preview)
        try:
            commit("Initial commit", cwd=repo_dir, preview=preview)
        except GitCommitError as exc:
            print(f"[WARN] Initial commit failed (continuing): {exc}")

    def push_default_branch(self, repo_dir: str, preview: bool) -> None:
        branch_move(DEFAULT_BRANCH, cwd=repo_dir, preview=preview)
        try:
            push_upstream("origin", DEFAULT_BRANCH, cwd=repo_dir, preview=preview)
        except GitPushUpstreamError as exc:
            print(f"[WARN] Push failed: {exc}")
