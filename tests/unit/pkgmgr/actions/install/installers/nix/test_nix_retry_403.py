from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.install.installers.nix.retry import (
    GitHubRateLimitRetry,
    RetryPolicy,
)
from pkgmgr.actions.install.installers.nix.types import RunResult


class DummyCtx:
    def __init__(self, quiet: bool = True) -> None:
        self.quiet = quiet


class FakeRunner:
    """
    Simulates a runner that returns:
      - HTTP 403 for the first N calls
      - success afterwards
    """

    def __init__(self, fail_count: int) -> None:
        self.fail_count = fail_count
        self.calls = 0

    def run(self, ctx: DummyCtx, cmd: str, allow_failure: bool) -> RunResult:
        self.calls += 1

        if self.calls <= self.fail_count:
            return RunResult(
                returncode=1,
                stdout="",
                stderr="error: HTTP error 403: rate limit exceeded (simulated)",
            )

        return RunResult(returncode=0, stdout="ok", stderr="")


class TestGitHub403Retry(unittest.TestCase):
    def test_retries_on_403_without_realtime_waiting(self) -> None:
        """
        Ensure:
          - It retries only on GitHub 403-like errors
          - It does not actually sleep in realtime (time.sleep patched)
          - It stops once a success occurs
          - Wait times follow Fibonacci(base=30) + jitter
        """
        policy = RetryPolicy(
            max_attempts=3,  # attempts: 1,2,3
            base_delay_seconds=30,  # fibonacci delays: 30, 30, 60
            jitter_seconds_min=0,
            jitter_seconds_max=60,
        )

        retry = GitHubRateLimitRetry(policy=policy)
        ctx = DummyCtx(quiet=True)
        runner = FakeRunner(fail_count=2)  # fail twice (403), then succeed

        # Make jitter deterministic and prevent real sleeping.
        with (
            patch(
                "pkgmgr.actions.install.installers.nix.retry.random.randint",
                return_value=5,
            ) as jitter_mock,
            patch(
                "pkgmgr.actions.install.installers.nix.retry.time.sleep"
            ) as sleep_mock,
        ):
            res = retry.run_with_retry(ctx, runner, "nix profile install /tmp#default")

        # Result should be success on 3rd attempt.
        self.assertEqual(res.returncode, 0)
        self.assertEqual(runner.calls, 3)

        # jitter should be used for each retry sleep (attempt 1->2, attempt 2->3) => 2 sleeps
        self.assertEqual(jitter_mock.call_count, 2)
        self.assertEqual(sleep_mock.call_count, 2)

        # Fibonacci delays for attempts=3: [30, 30, 60]
        # sleep occurs after failed attempt 1 and 2, so base delays are 30 and 30
        # wait_time = base_delay + jitter(5) => 35, 35
        sleep_args = [c.args[0] for c in sleep_mock.call_args_list]
        self.assertEqual(sleep_args, [35, 35])

    def test_does_not_retry_on_non_403_errors(self) -> None:
        """
        Ensure it does not retry when the error is not recognized as GitHub 403/rate limit.
        """
        policy = RetryPolicy(max_attempts=7, base_delay_seconds=30)
        retry = GitHubRateLimitRetry(policy=policy)
        ctx = DummyCtx(quiet=True)

        class Non403Runner:
            def __init__(self) -> None:
                self.calls = 0

            def run(self, ctx: DummyCtx, cmd: str, allow_failure: bool) -> RunResult:
                self.calls += 1
                return RunResult(
                    returncode=1, stdout="", stderr="some other error (simulated)"
                )

        runner = Non403Runner()

        with patch(
            "pkgmgr.actions.install.installers.nix.retry.time.sleep"
        ) as sleep_mock:
            res = retry.run_with_retry(ctx, runner, "nix profile install /tmp#default")

        self.assertEqual(res.returncode, 1)
        self.assertEqual(runner.calls, 1)  # no retries
        self.assertEqual(sleep_mock.call_count, 0)


if __name__ == "__main__":
    unittest.main()
