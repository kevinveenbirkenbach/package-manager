from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Iterable, TYPE_CHECKING

from .types import RunResult

if TYPE_CHECKING:
    from pkgmgr.actions.install.context import RepoContext
    from .runner import CommandRunner


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 7
    base_delay_seconds: int = 30
    jitter_seconds_min: int = 0
    jitter_seconds_max: int = 60


class GitHubRateLimitRetry:
    """
    Retries nix install commands only when the error looks like a GitHub API rate limit (HTTP 403).
    Backoff: Fibonacci(base, base, ...) + random jitter.
    """

    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self._policy = policy or RetryPolicy()

    def run_with_retry(
        self,
        ctx: "RepoContext",
        runner: "CommandRunner",
        install_cmd: str,
    ) -> RunResult:
        quiet = bool(getattr(ctx, "quiet", False))
        delays = list(
            self._fibonacci_backoff(
                self._policy.base_delay_seconds, self._policy.max_attempts
            )
        )

        last: RunResult | None = None

        for attempt, base_delay in enumerate(delays, start=1):
            if not quiet:
                print(
                    f"[nix] attempt {attempt}/{self._policy.max_attempts}: {install_cmd}"
                )

            res = runner.run(ctx, install_cmd, allow_failure=True)
            last = res

            if res.returncode == 0:
                return res

            combined = f"{res.stdout}\n{res.stderr}"
            if not self._is_github_rate_limit_error(combined):
                return res

            if attempt >= self._policy.max_attempts:
                break

            jitter = random.randint(
                self._policy.jitter_seconds_min, self._policy.jitter_seconds_max
            )
            wait_time = base_delay + jitter

            if not quiet:
                print(
                    "[nix] GitHub rate limit detected (403). "
                    f"Retrying in {wait_time}s (base={base_delay}s, jitter={jitter}s)..."
                )

            time.sleep(wait_time)

        return (
            last
            if last is not None
            else RunResult(returncode=1, stdout="", stderr="nix install retry failed")
        )

    @staticmethod
    def _is_github_rate_limit_error(text: str) -> bool:
        t = (text or "").lower()
        return (
            "http error 403" in t
            or "rate limit exceeded" in t
            or "github api rate limit" in t
            or "api rate limit exceeded" in t
        )

    @staticmethod
    def _fibonacci_backoff(base: int, attempts: int) -> Iterable[int]:
        a, b = base, base
        for _ in range(max(1, attempts)):
            yield a
            a, b = b, a + b
