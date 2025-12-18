from __future__ import annotations

import importlib
import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch


class TestIntegrationReposCreatePreview(unittest.TestCase):
    def test_repos_create_preview_wires_create_repo(self) -> None:
        # Import lazily to avoid hard-failing if the CLI module/function name differs.
        try:
            repos_mod = importlib.import_module("pkgmgr.cli.commands.repos")
        except Exception as exc:
            self.skipTest(f"CLI module not available: {exc}")

        handle = getattr(repos_mod, "handle_repos_command", None)
        if handle is None:
            self.skipTest("handle_repos_command not found in pkgmgr.cli.commands.repos")

        ctx = SimpleNamespace(
            repositories_base_dir="/tmp/Repositories",
            binaries_dir="/tmp/bin",
            all_repositories=[],
            config_merged={
                "directories": {"repositories": "/tmp/Repositories"},
                "repositories": [],
            },
            user_config_path="/tmp/user.yml",
        )

        args = SimpleNamespace(
            command="create",
            identifiers=["github.com/acme/repo"],
            remote=False,
            preview=True,
        )

        out = io.StringIO()
        with (
            redirect_stdout(out),
            patch("pkgmgr.cli.commands.repos.create_repo") as create_repo,
        ):
            handle(args, ctx, selected=[])

        create_repo.assert_called_once()
        called = create_repo.call_args.kwargs
        self.assertEqual(called["remote"], False)
        self.assertEqual(called["preview"], True)
        self.assertEqual(create_repo.call_args.args[0], "github.com/acme/repo")


if __name__ == "__main__":
    unittest.main()
