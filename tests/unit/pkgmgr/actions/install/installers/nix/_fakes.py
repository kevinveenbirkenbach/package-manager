from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class FakeRunResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class FakeRunner:
    """
    Minimal runner stub compatible with:
      - CommandRunner.run(ctx, cmd, allow_failure=...)
      - Generic runner.run(ctx, cmd, allow_failure=...)
    """

    def __init__(self, mapping: Optional[dict[str, Any]] = None, default: Any = None):
        self.mapping = mapping or {}
        self.default = default if default is not None else FakeRunResult(0, "", "")
        self.calls: list[tuple[Any, str, bool]] = []

    def run(self, ctx, cmd: str, allow_failure: bool = False):
        self.calls.append((ctx, cmd, allow_failure))
        return self.mapping.get(cmd, self.default)


class FakeRetry:
    """
    Mimics GitHubRateLimitRetry.run_with_retry(ctx, runner, cmd)
    """

    def __init__(self, results: list[FakeRunResult]):
        self._results = list(results)
        self.calls: list[str] = []

    def run_with_retry(self, ctx, runner, cmd: str):
        self.calls.append(cmd)
        if self._results:
            return self._results.pop(0)
        return FakeRunResult(0, "", "")
