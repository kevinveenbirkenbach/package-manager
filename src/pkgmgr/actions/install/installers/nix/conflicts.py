from __future__ import annotations

from typing import TYPE_CHECKING, List

from .profile import NixProfileInspector
from .retry import GitHubRateLimitRetry
from .runner import CommandRunner
from .textparse import NixConflictTextParser

if TYPE_CHECKING:
    from pkgmgr.actions.install.context import RepoContext


class NixConflictResolver:
    """
    Resolves nix profile file conflicts by:
      1. Parsing conflicting store paths from stderr
      2. Mapping them to profile remove tokens via `nix profile list --json`
      3. Removing those tokens deterministically
      4. Retrying install
    """

    def __init__(
        self,
        runner: CommandRunner,
        retry: GitHubRateLimitRetry,
        profile: NixProfileInspector,
    ) -> None:
        self._runner = runner
        self._retry = retry
        self._profile = profile
        self._parser = NixConflictTextParser()

    def resolve(
        self,
        ctx: "RepoContext",
        install_cmd: str,
        stdout: str,
        stderr: str,
        *,
        output: str,
        max_rounds: int = 10,
    ) -> bool:
        quiet = bool(getattr(ctx, "quiet", False))
        combined = f"{stdout}\n{stderr}"

        for _ in range(max_rounds):
            # 1) Extract conflicting store prefixes from nix error output
            store_prefixes = self._parser.existing_store_prefixes(combined)

            # 2) Resolve them to concrete remove tokens
            tokens: List[str] = self._profile.find_remove_tokens_for_store_prefixes(
                ctx,
                self._runner,
                store_prefixes,
            )

            # 3) Fallback: output-name based lookup (also covers nix suggesting: `nix profile remove pkgmgr`)
            if not tokens:
                tokens = self._profile.find_remove_tokens_for_output(
                    ctx, self._runner, output
                )

            if tokens:
                if not quiet:
                    print(
                        "[nix] conflict detected; removing existing profile entries: "
                        + ", ".join(tokens)
                    )

                for t in tokens:
                    # tokens may contain things like "pkgmgr" or "pkgmgr-1" or quoted tokens (we keep raw)
                    self._runner.run(ctx, f"nix profile remove {t}", allow_failure=True)

                res = self._retry.run_with_retry(ctx, self._runner, install_cmd)
                if res.returncode == 0:
                    return True

                combined = f"{res.stdout}\n{res.stderr}"
                continue

            # 4) Last-resort fallback: use textual remove tokens from stderr (“nix profile remove X”)
            tokens = self._parser.remove_tokens(combined)
            if tokens:
                if not quiet:
                    print("[nix] fallback remove tokens: " + ", ".join(tokens))

                for t in tokens:
                    self._runner.run(ctx, f"nix profile remove {t}", allow_failure=True)

                res = self._retry.run_with_retry(ctx, self._runner, install_cmd)
                if res.returncode == 0:
                    return True

                combined = f"{res.stdout}\n{res.stderr}"
                continue

            if not quiet:
                print(
                    "[nix] conflict detected but could not resolve profile entries to remove."
                )
            return False

        return False
