from __future__ import annotations

import subprocess

from typing import TYPE_CHECKING

from .types import RunResult

if TYPE_CHECKING:
    from pkgmgr.actions.install.context import RepoContext


class CommandRunner:
    """
    Executes commands (shell=True) inside a repository directory (if provided).
    Supports preview mode and compact failure output logging.
    """

    def run(self, ctx: "RepoContext", cmd: str, allow_failure: bool) -> RunResult:
        repo_dir = getattr(ctx, "repo_dir", None) or getattr(ctx, "repo_path", None)
        preview = bool(getattr(ctx, "preview", False))
        quiet = bool(getattr(ctx, "quiet", False))

        if preview:
            if not quiet:
                print(f"[preview] {cmd}")
            return RunResult(returncode=0, stdout="", stderr="")

        try:
            p = subprocess.run(
                cmd,
                shell=True,
                cwd=repo_dir,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as e:
            if not allow_failure:
                raise
            return RunResult(returncode=1, stdout="", stderr=str(e))

        res = RunResult(
            returncode=p.returncode, stdout=p.stdout or "", stderr=p.stderr or ""
        )

        if res.returncode != 0 and not quiet:
            self._print_compact_failure(res)

        if res.returncode != 0 and not allow_failure:
            raise SystemExit(res.returncode)

        return res

    @staticmethod
    def _print_compact_failure(res: RunResult) -> None:
        out = (res.stdout or "").strip()
        err = (res.stderr or "").strip()

        if out:
            print("[nix] stdout (last lines):")
            print("\n".join(out.splitlines()[-20:]))

        if err:
            print("[nix] stderr (last lines):")
            print("\n".join(err.splitlines()[-40:]))
