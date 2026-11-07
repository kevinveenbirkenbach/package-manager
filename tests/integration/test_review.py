from __future__ import annotations

import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

from pkgmgr.actions.review import ReviewError, write_review
from pkgmgr.cli.commands.review import handle_review
from pkgmgr.cli.parser import create_parser

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.org",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.org",
}
COMMIT_MESSAGE = (
    'feat: <script>alert("subject")</script>\n\nBody <script>alert("body")</script>'
)


def git(cwd: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        env=GIT_ENV,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write(path: str, content: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(content)


class TestReview(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        self.repo = os.path.join(self.root, "my repo")
        git(self.root, "init", "-b", "main", self.repo)
        app = "".join(f"line {n}\n" for n in range(1, 21))
        write(self._path("app.py"), app.encode())
        write(self._path("notes.md"), b"# Notes\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "init")

        git(self.repo, "checkout", "-b", "feature")
        write(self._path("notes.md"), b"# Notes\nfeature\n")
        git(self.repo, "commit", "-am", COMMIT_MESSAGE)

        write(self._path("app.py"), app.replace("line 5\n", "line five\n").encode())
        big = "".join(f"big {n}\n" for n in range(1, 31))
        write(self._path("dir with space", "big.txt"), big.encode())
        write(self._path("image.png"), b"\x89PNG\x00\x01\x02")
        git(self.repo, "mv", "notes.md", "renamed.md")
        git(self.repo, "add", "-A")

        unstaged = app.replace("line 5\n", "line five\n")
        write(
            self._path("app.py"), unstaged.replace("line 15\n", "line 15!\n").encode()
        )

        write(
            self._path("todo.txt"),
            b"first\n<script>alert('file')</script>\nlast\n",
        )
        write(self._path("blob.bin"), b"\x00\xffdata")

        self.note = os.path.join(self.root, "score.txt")
        write(self.note, b"<b>score</b> 90/5\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _path(self, *parts: str) -> str:
        return os.path.join(self.repo, *parts)

    def _render(self, out: str, base: str | None, notes: list[str]) -> str:
        path = write_review(
            cwd=self.repo,
            out=os.path.join(self.root, "out", out),
            max_file_lines=10,
            base=base,
            notes=notes,
        )
        return Path(path).read_text(encoding="utf-8")

    def _link(self, rel: str, line: int) -> str:
        return f"vscode://file{quote(os.path.join(self.repo, rel))}:{line}"

    def test_sections_and_counts(self) -> None:
        html = self._render("page.html", None, [])

        self.assertIn(
            'id="staged" data-files="4" data-added="31" data-removed="1"', html
        )
        self.assertIn(
            'id="unstaged" data-files="1" data-added="1" data-removed="1"', html
        )
        self.assertIn(
            'id="untracked" data-files="2" data-added="3" data-removed="0"', html
        )
        self.assertNotIn('id="commits"', html)
        self.assertIn(
            'notes.md</span><span class="arrow"> &rarr; </span>renamed.md', html
        )
        self.assertIn('<span class="tag">binary</span>', html)
        self.assertIn('data-path="blob.bin"', html)
        self.assertIn("Binary file, contents not shown.", html)
        self.assertIn(git(self.repo, "write-tree"), html)
        self.assertIn(git(self.repo, "rev-parse", "--short", "HEAD"), html)

    def test_base_adds_commits_section(self) -> None:
        html = self._render("page.html", "main", [])

        self.assertIn(
            'id="commits" data-commits="1" data-files="1" data-added="1" '
            'data-removed="0"',
            html,
        )
        self.assertIn("t &lt;t@example.org&gt;", html)
        self.assertIn(git(self.repo, "rev-parse", "--short", "feature"), html)

    def test_untrusted_text_is_escaped(self) -> None:
        html = self._render("page.html", "main", [self.note])

        self.assertEqual(html.count("<script"), 1)
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;alert(&#39;file&#39;)&lt;/script&gt;", html)
        self.assertIn("feat: &lt;script&gt;alert(&#34;subject&#34;)", html)
        self.assertIn("Body &lt;script&gt;alert(&#34;body&#34;)", html)
        self.assertIn("<figcaption>score.txt</figcaption>", html)
        self.assertIn("&lt;b&gt;score&lt;/b&gt; 90/5", html)

    def test_rendering_is_deterministic(self) -> None:
        first = self._render("one.html", "main", [self.note])
        second = self._render("two.html", "main", [self.note])

        self.assertEqual(first.encode("utf-8"), second.encode("utf-8"))

    def test_vscode_links_and_truncation(self) -> None:
        html = self._render("page.html", None, [])

        self.assertIn(f'class="open" href="{self._link("app.py", 5)}"', html)
        self.assertIn(f'class="open" href="{self._link("app.py", 15)}"', html)
        self.assertIn(f'<a href="{self._link("app.py", 5)}">5</a>', html)
        self.assertIn("my%20repo/dir%20with%20space/big.txt:1", html)
        self.assertIn("big 10</td>", html)
        self.assertNotIn("big 11</td>", html)
        self.assertIn("20 more lines not shown", html)

    def test_errors_exit_two(self) -> None:
        plain = os.path.join(self.root, "plain")
        os.makedirs(plain)
        with (
            patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": self.root}),
            self.assertRaisesRegex(ReviewError, "not inside a git working copy"),
        ):
            write_review(cwd=plain, out="x.html", max_file_lines=5, base=None, notes=[])
        with self.assertRaisesRegex(ReviewError, "unknown base ref"):
            write_review(
                cwd=self.repo,
                out="x.html",
                max_file_lines=5,
                base="no-such-ref",
                notes=[],
            )
        args = create_parser("test").parse_args(
            ["review", "--out", "x.html", "--max-file-lines", "5", "--base", "nope"]
        )
        stderr = io.StringIO()
        with (
            patch("pkgmgr.cli.commands.review.os.getcwd", return_value=self.repo),
            redirect_stderr(stderr),
            self.assertRaises(SystemExit) as exit_ctx,
        ):
            handle_review(args, ctx=None)
        self.assertEqual(exit_ctx.exception.code, 2)
        self.assertEqual(len(stderr.getvalue().splitlines()), 1)
        self.assertFalse(os.path.exists(self._path("x.html")))

    def test_cli_forwards_every_option(self) -> None:
        args = create_parser("test").parse_args(
            [
                "review",
                "--out",
                "page.html",
                "--max-file-lines",
                "50",
                "--base",
                "origin/main",
                "--note",
                "score.txt",
                "--note",
                "message.txt",
            ]
        )
        target = os.path.join(self.root, "page.html")
        stdout = io.StringIO()
        with (
            patch("pkgmgr.cli.commands.review.os.getcwd", return_value=self.repo),
            patch(
                "pkgmgr.cli.commands.review.write_review", return_value=target
            ) as run_review,
            redirect_stdout(stdout),
        ):
            handle_review(args, ctx=None)

        run_review.assert_called_once_with(
            cwd=self.repo,
            out="page.html",
            max_file_lines=50,
            base="origin/main",
            notes=["score.txt", "message.txt"],
        )
        self.assertEqual(stdout.getvalue(), f"file://{target}\n")

        bare = create_parser("test").parse_args(
            ["review", "--out", "p.html", "--max-file-lines", "3"]
        )
        self.assertIsNone(bare.base)
        self.assertEqual(bare.note, [])


if __name__ == "__main__":
    unittest.main()
