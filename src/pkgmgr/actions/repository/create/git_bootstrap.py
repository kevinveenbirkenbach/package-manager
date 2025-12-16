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


class GitBootstrapper:
    def init_repo(self, repo_dir: str, preview: bool) -> None:
        init(cwd=repo_dir, preview=preview)
        add_all(cwd=repo_dir, preview=preview)
        try:
            commit("Initial commit", cwd=repo_dir, preview=preview)
        except GitCommitError as exc:
            print(f"[WARN] Initial commit failed (continuing): {exc}")

    def push_default_branch(self, repo_dir: str, preview: bool) -> None:
        try:
            branch_move("main", cwd=repo_dir, preview=preview)
            push_upstream("origin", "main", cwd=repo_dir, preview=preview)
            return
        except GitPushUpstreamError:
            pass

        try:
            branch_move("master", cwd=repo_dir, preview=preview)
            push_upstream("origin", "master", cwd=repo_dir, preview=preview)
        except GitPushUpstreamError as exc:
            print(f"[WARN] Push failed: {exc}")
