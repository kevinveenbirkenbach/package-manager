from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pkgmgr.actions.release.retry import retry_release
from pkgmgr.actions.repository.push import (
    PushRefusedError,
    push_branch,
    sign_unpushed,
)
from pkgmgr.cli.context import CLIContext
from pkgmgr.cli.parser import create_parser
from pkgmgr.cli.proxy import maybe_handle_proxy


def git(cwd: str, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen signs the commits")
class TestPushMirrorLeases(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(os.path.realpath(self._tmp.name))
        self.root = str(root)
        key = root / "key"
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
            check=True,
        )
        (root / "allowed").write_text(f"t@example.org {(root / 'key.pub').read_text()}")
        (root / "gitconfig").write_text(
            "[user]\n\tname = t\n\temail = t@example.org\n"
            f"\tsigningkey = {key}\n"
            "[gpg]\n\tformat = ssh\n"
            f'[gpg "ssh"]\n\tallowedSignersFile = {root / "allowed"}\n'
            "[commit]\n\tgpgsign = false\n"
            "[init]\n\tdefaultBranch = main\n"
        )
        env = patch.dict(
            os.environ,
            {"GIT_CONFIG_GLOBAL": str(root / "gitconfig"), "GIT_CONFIG_NOSYSTEM": "1"},
        )
        env.start()
        self.addCleanup(env.stop)

        self.canonical = str(root / "canonical.git")
        self.mirror = str(root / "mirror.git")
        self.repo = str(root / "repo")
        git(self.root, "init", "-q", "--bare", self.canonical)
        git(self.root, "init", "-q", "--bare", self.mirror)
        git(self.root, "init", "-q", self.repo)
        git(self.repo, "remote", "add", "origin", self.canonical)
        git(self.repo, "remote", "set-url", "--add", "--push", "origin", self.canonical)
        git(self.repo, "remote", "set-url", "--add", "--push", "origin", self.mirror)
        self.init = self._commit("init")
        git(self.repo, "push", "-q", self.canonical, "main")
        git(self.repo, "push", "-q", self.mirror, "main")
        git(self.repo, "fetch", "-q", "origin")
        git(self.repo, "branch", "-q", "--set-upstream-to=origin/main")

    def _commit(self, name: str, cwd: str | None = None, *flags: str) -> str:
        cwd = cwd or self.repo
        Path(cwd, f"{name}.txt").write_text(name)
        git(cwd, "add", f"{name}.txt")
        git(cwd, "commit", "-q", *flags, "-m", name)
        return git(cwd, "rev-parse", "HEAD")

    def _push(self, rewrite: bool = False) -> str:
        with redirect_stdout(io.StringIO()) as out:
            sign_unpushed(self.repo)
            push_branch(self.repo, [], sign=True, rewrite=rewrite)
        return out.getvalue()

    def _cli_push(self, cwd: str, *argv: str) -> None:
        ctx = CLIContext(
            config_merged={},
            repositories_base_dir=os.path.join(self.root, "base"),
            all_repositories=[],
            binaries_dir=os.path.join(self.root, "bin"),
            user_config_path=os.path.join(self.root, "config.yaml"),
        )
        args = create_parser("pkgmgr").parse_args(["push", "-j", "1", *argv])
        prev = os.getcwd()
        os.chdir(cwd)
        self.addCleanup(os.chdir, prev)

        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as cm:
            maybe_handle_proxy(args, ctx)

        self.assertEqual(cm.exception.code, 0)

    def _tip(self, bare: str, ref: str = "refs/heads/main") -> str:
        return subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref],
            cwd=bare,
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _assert_shipped_signed(self) -> None:
        head = git(self.repo, "rev-parse", "HEAD")
        self.assertEqual(self._tip(self.canonical), head)
        self.assertEqual(self._tip(self.mirror), head)
        signatures = git(self.repo, "log", "--format=%G?", f"{self.init}..HEAD")
        self.assertEqual(set(signatures.split()), {"G"})

    def test_mirror_equal_gets_the_signed_commit(self) -> None:
        self._commit("feature")

        self._push()

        self._assert_shipped_signed()

    def test_mirror_behind_is_fast_forwarded(self) -> None:
        self._commit("first", None, "-S")
        git(self.repo, "push", "-q", self.canonical, "main")
        git(self.repo, "fetch", "-q", "origin")
        self._commit("second")

        self._push()

        self._assert_shipped_signed()

    def test_mirror_on_older_rewrite_is_replaced_after_resign(self) -> None:
        unsigned = self._commit("feature")
        git(self.repo, "push", "-q", self.mirror, "main")

        self._push()

        self._assert_shipped_signed()
        self.assertNotEqual(self._tip(self.mirror), unsigned)

    def test_mirror_only_commit_is_refused_and_kept(self) -> None:
        other = os.path.join(self.root, "other")
        git(self.root, "clone", "-q", self.mirror, other)
        foreign = self._commit("foreign", other)
        git(other, "push", "-q", "origin", "main")
        self._commit("feature")

        with self.assertRaises(PushRefusedError) as cm:
            self._push()
        with self.assertRaises(PushRefusedError):
            self._push(rewrite=True)

        self.assertIn(self.mirror, str(cm.exception))
        self.assertEqual(self._tip(self.mirror), foreign)
        self.assertEqual(self._tip(self.canonical), git(self.repo, "rev-parse", "HEAD"))

    def test_content_rewrite_needs_the_rewrite_flag(self) -> None:
        self._commit("feature")
        self._push()
        shipped = git(self.repo, "rev-parse", "HEAD")
        Path(self.repo, "feature.txt").write_text("changed")
        git(self.repo, "commit", "-q", "-a", "--amend", "--no-edit")

        with self.assertRaises(PushRefusedError) as cm:
            self._push()

        self.assertIn(self.canonical, str(cm.exception))
        self.assertEqual(self._tip(self.canonical), shipped)
        self.assertEqual(self._tip(self.mirror), shipped)

        self._push(rewrite=True)

        self._assert_shipped_signed()
        self.assertNotEqual(self._tip(self.mirror), shipped)

    def test_worktree_outside_base_dir_is_pushed(self) -> None:
        worktree = os.path.join(self.root, "wt")
        git(self.repo, "worktree", "add", "-q", "-b", "feature", worktree)
        head_before = self._commit("feature", worktree)

        self._cli_push(worktree)

        head = git(worktree, "rev-parse", "HEAD")
        self.assertNotEqual(head, head_before)
        self.assertEqual(self._tip(self.canonical, "refs/heads/feature"), head)
        self.assertEqual(self._tip(self.mirror, "refs/heads/feature"), head)
        self.assertEqual(
            git(worktree, "rev-parse", "--abbrev-ref", "@{u}"), "origin/feature"
        )

    def test_no_sign_pushes_unsigned_commits_to_every_url(self) -> None:
        unsigned = self._commit("feature")

        self._cli_push(self.repo, "--no-sign")

        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), unsigned)
        self.assertEqual(self._tip(self.canonical), unsigned)
        self.assertEqual(self._tip(self.mirror), unsigned)
        self.assertEqual(git(self.repo, "log", "-1", "--format=%G?"), "N")

    def test_release_retry_refuses_unsigned_range(self) -> None:
        self._commit("release")
        git(self.repo, "tag", "-a", "v1.0.0", "-m", "v1.0.0")
        cwd = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, cwd)

        with redirect_stdout(io.StringIO()), self.assertRaises(PushRefusedError):
            retry_release(pyproject_path=os.path.join(self.repo, "pyproject.toml"))

        self.assertEqual(self._tip(self.canonical), git(self.repo, "rev-parse", "@{u}"))
        self.assertEqual(self._tip(self.canonical, "refs/tags/v1.0.0"), "")


if __name__ == "__main__":
    unittest.main()
