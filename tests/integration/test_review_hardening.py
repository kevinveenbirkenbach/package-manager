from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pkgmgr.actions.review import ReviewError, write_review
from tests.integration.test_review import GIT_ENV, git, write

SECRET = b"SECRET-KEY-MATERIAL\n"
SIGNATURE = (
    "gpgsig -----BEGIN PGP SIGNATURE-----\n \n iQEzBAABCAAdFiEE\n"
    " -----END PGP SIGNATURE-----"
)
MODULE = '[submodule "{0}"]\n\tpath = {0}\n\turl = ./{0}\n{1}'


class ReviewRepoCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        self.repo = os.path.join(self.root, "repo")
        self.marker = os.path.join(self.root, "marker")
        self.secret = os.path.join(self.root, "secret", "id_ed25519")
        write(self.secret, SECRET)
        git(self.root, "init", "-b", "main", self.repo)
        write(self._path("app.py"), b"print('base')\n")
        write(self._path("lib.py"), b"print('lib')\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "init")
        git(self.repo, "checkout", "-b", "feature")
        write(self._path("app.py"), b"print('feature')\n")
        git(self.repo, "commit", "-am", "feature")
        write(self._path("app.py"), b"print('staged')\n")
        git(self.repo, "add", "app.py")
        write(self._path("app.py"), b"print('unstaged')\n")
        write(self._path("new.txt"), b"untracked\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _path(self, *parts: str) -> str:
        return os.path.join(self.repo, *parts)

    def _render(self, base: str | None, notes: list[str]) -> str:
        path = write_review(
            cwd=self.repo,
            out=os.path.join(self.root, "out", "page.html"),
            max_file_lines=50,
            base=base,
            notes=notes,
        )
        return Path(path).read_text(encoding="utf-8")

    def _trap(self, path: str, tail: str) -> str:
        write(path, f"#!/bin/sh\ntouch '{self.marker}'\n{tail}\n".encode())
        os.chmod(path, 0o755)
        return path

    def _assert_fires(self, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=self.repo,
            env=GIT_ENV,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )
        self.assertTrue(os.path.exists(self.marker), f"plain git {args[0]} fires")
        os.remove(self.marker)

    def _submodule(self, parent: str, name: str, extra: str = "") -> str:
        path = os.path.join(parent, name)
        git(parent, "init", "-b", "main", path)
        write(os.path.join(path, "f.txt"), b"one\n")
        git(path, "add", "-A")
        git(path, "commit", "-m", "one")
        head = git(path, "rev-parse", "HEAD")
        write(os.path.join(parent, ".gitmodules"), MODULE.format(name, extra).encode())
        git(parent, "update-index", "--add", "--cacheinfo", f"160000,{head},{name}")
        git(parent, "add", ".gitmodules")
        git(parent, "commit", "-m", name)
        return path

    def _object(self, kind: str, content: str) -> str:
        return subprocess.run(
            ["git", "hash-object", "-t", kind, "-w", "--stdin"],
            cwd=self.repo,
            env=GIT_ENV,
            input=content,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()


class TestReviewHardening(ReviewRepoCase):
    def test_fsmonitor_never_runs(self) -> None:
        monitor = self._trap(os.path.join(self.root, "fsmonitor"), "exit 1")
        git(self.repo, "config", "core.fsmonitor", monitor)
        self._assert_fires("diff")

        self._render("main", [])

        self.assertFalse(os.path.exists(self.marker))

    def test_repository_filter_never_runs(self) -> None:
        write(self._path(".git", "info", "attributes"), b"* filter=trap\n")
        clean = self._trap(os.path.join(self.root, "clean"), "exec cat")
        git(self.repo, "config", "filter.trap.clean", clean)
        self._assert_fires("diff")

        html = self._render("main", [])

        self.assertFalse(os.path.exists(self.marker))
        self.assertIn('id="unstaged" data-files="0"', html)
        self.assertIn("filter.trap.clean", html)
        self.assertNotIn("print(&#39;unstaged&#39;)", html)
        self.assertIn("<dd>(not computed, see the warnings)</dd>", html)

    def test_submodule_filter_never_runs(self) -> None:
        sub = self._submodule(self.repo, "sub")
        inner = self._submodule(sub, "inner")
        clean = self._trap(os.path.join(self.root, "clean"), "exec cat")
        for path in (sub, inner):
            write(os.path.join(path, ".git", "info", "attributes"), b"* filter=x\n")
            write(os.path.join(path, "f.txt"), b"two\n")
            git(path, "config", "filter.x.clean", clean)
        self._assert_fires("diff")

        html = self._render(None, [])

        self.assertFalse(os.path.exists(self.marker))
        self.assertIn('id="unstaged" data-files="0"', html)
        self.assertIn("the config of submodule sub defines filter.x.clean", html)
        self.assertIn("the config of submodule sub/inner defines filter.x.clean", html)
        self.assertIn("<dd>(not computed, see the warnings)</dd>", html)

    def test_signature_program_never_runs(self) -> None:
        header, message = git(self.repo, "cat-file", "commit", "HEAD").split("\n\n", 1)
        signed = self._object("commit", f"{header}\n{SIGNATURE}\n\n{message}\n")
        git(self.repo, "update-ref", "HEAD", signed)
        program = self._trap(os.path.join(self.root, "gpg"), "exit 1")
        git(self.repo, "config", "gpg.program", program)
        self._assert_fires("log", "-1", "--format=%G?")

        html = self._render("main", [])

        self.assertFalse(os.path.exists(self.marker))
        self.assertIn('id="commits" data-commits="1"', html)
        self.assertNotIn('<span class="sig', html)

    def test_hooks_never_run(self) -> None:
        hooks = os.path.join(self.root, "hooks")
        self._trap(os.path.join(hooks, "post-index-change"), "exit 0")
        git(self.repo, "config", "core.hooksPath", hooks)
        self._assert_fires("update-index", "--force-write-index")

        self._render("main", [])

        self.assertFalse(os.path.exists(self.marker))

    def test_note_symlinks_are_refused(self) -> None:
        link = os.path.join(self.root, "score.txt")
        os.symlink(self.secret, link)
        parent = os.path.join(self.root, "notes")
        os.symlink(os.path.dirname(self.secret), parent)

        for note in (link, os.path.join(parent, "id_ed25519")):
            with (
                self.subTest(note=note),
                self.assertRaisesRegex(ReviewError, "cannot read note"),
            ):
                self._render(None, [note])

    def test_untracked_parent_swap_is_not_followed(self) -> None:
        write(self._path("sub", "id_ed25519"), b"harmless\n")
        real_run = subprocess.run
        swapped: list[list[str]] = []

        def swap(cmd, *args, **kwargs):
            result = real_run(cmd, *args, **kwargs)
            if "--others" in cmd and not swapped:
                os.rename(self._path("sub"), os.path.join(self.root, "sub-real"))
                os.symlink(os.path.dirname(self.secret), self._path("sub"))
                swapped.append(cmd)
            return result

        with patch("subprocess.run", swap):
            html = self._render(None, [])

        self.assertTrue(swapped)
        self.assertNotIn(SECRET.decode().strip(), html)
        self.assertIn("Not a regular file, contents not shown.", html)

    def test_out_symlink_is_replaced_not_followed(self) -> None:
        keys = b"ssh-ed25519 AAAA operator\n"
        victim = os.path.join(self.root, "authorized_keys")
        write(victim, keys)
        missing = os.path.join(self.root, "missing_keys")
        out = os.path.join(self.root, "out")
        os.makedirs(out)
        os.symlink(victim, os.path.join(out, "page.html"))
        os.symlink(missing, os.path.join(out, "dangling.html"))

        for name in ("page.html", "dangling.html"):
            with self.subTest(out=name):
                path = write_review(
                    cwd=self.repo,
                    out=os.path.join(out, name),
                    max_file_lines=50,
                    base=None,
                    notes=[],
                )
                info = os.lstat(path)
                self.assertTrue(stat.S_ISREG(info.st_mode))
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o600)

        self.assertEqual(Path(victim).read_bytes(), keys)
        self.assertFalse(os.path.lexists(missing))
        self.assertEqual(sorted(os.listdir(out)), ["dangling.html", "page.html"])


if __name__ == "__main__":
    unittest.main()
