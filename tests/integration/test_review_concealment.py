from __future__ import annotations

import os
import unittest

from pkgmgr.actions.review import ReviewError
from tests.integration.test_review import git, write
from tests.integration.test_review_hardening import MODULE, ReviewRepoCase

INVISIBLE = "".join(
    map(
        chr,
        (
            *range(0x202A, 0x202F),
            *range(0x2066, 0x206A),
            *range(0x200B, 0x2010),
            0x061C,
            0xFEFF,
        ),
    )
)
RLO, LRI, ZWSP, BOM = map(chr, (0x202E, 0x2066, 0x200B, 0xFEFF))
HIDDEN = "<li>Index entry {} is marked {}: its worktree changes are not shown.</li>"
ATTRIBUTE_BINARY = (
    "{} is shown as binary because {}, not because of its content: "
    "run git diff --text to see it."
)
UNSET = "a gitattributes entry unsets its diff attribute"
DRIVER = "its gitattributes diff driver {0} sets diff.{0}.binary"


def marks(text: str) -> str:
    return "".join(f"&lt;U+{ord(char):04X}&gt;" for char in text)


class TestReviewConcealment(ReviewRepoCase):
    def test_replace_objects_cannot_mask_the_index(self) -> None:
        evil = self._object("blob", "print('evil')\n")
        benign = self._object("blob", "print('staged')\n")
        git(self.repo, "update-index", "--cacheinfo", f"100644,{evil},app.py")
        git(self.repo, "replace", evil, benign)
        git(self.repo, "update-index", "--skip-worktree", "app.py")
        git(self.repo, "update-index", "--assume-unchanged", "lib.py")
        write(self._path("lib.py"), b"print('hidden')\n")

        html = self._render(None, [])

        self.assertIn("print(&#39;evil&#39;)", html)
        self.assertNotIn("print(&#39;staged&#39;)", html)
        self.assertIn(HIDDEN.format("app.py", "skip-worktree"), html)
        self.assertIn(HIDDEN.format("lib.py", "assume-unchanged"), html)

    def test_ignored_submodule_change_is_shown(self) -> None:
        sub = self._submodule(self.repo, "sub", "\tignore = all\n")
        git(sub, "commit", "--allow-empty", "-m", "two")
        new = git(sub, "rev-parse", "HEAD")
        git(self.repo, "update-index", "--cacheinfo", f"160000,{new},sub")

        gitmodules = self._render(None, [])
        write(self._path(".gitmodules"), MODULE.format("sub", "").encode())
        git(self.repo, "config", "diff.ignoreSubmodules", "all")
        config = self._render(None, [])

        for source, html in (("gitmodules", gitmodules), ("config", config)):
            with self.subTest(source=source):
                self.assertIn(f"Subproject commit {new}", html)

    def test_attribute_binary_is_warned(self) -> None:
        write(self._path(".gitattributes"), b"*.txt -diff\n")
        write(self._path(".git", "info", "attributes"), b"*.md binary\n")
        write(self._path("plain.txt"), b"plain text\n")
        write(self._path("readme.md"), b"# readme\n")
        write(self._path("image.bin"), b"\x00\x01binary\n")
        git(self.repo, "add", ".gitattributes", "plain.txt", "readme.md", "image.bin")

        html = self._render(None, [])

        self.assertIn('data-path="image.bin"', html)
        for path in ("plain.txt", "readme.md"):
            self.assertIn(f"<li>{ATTRIBUTE_BINARY.format(path, UNSET)}</li>", html)
        for path in ("image.bin", "new.txt"):
            self.assertNotIn(f"{path} is shown as binary", html)

    def test_binary_diff_driver_is_warned(self) -> None:
        write(self._path(".gitattributes"), b"*.dat diff=opaque\n*.bin diff=plain\n")
        git(self.repo, "config", "diff.opaque.binary", "yes")
        write(self._path("data.dat"), b"text data\n")
        write(self._path("image.bin"), b"\x00\x01binary\n")
        git(self.repo, "add", ".gitattributes", "data.dat", "image.bin")

        html = self._render(None, [])

        self.assertIn('data-path="image.bin"', html)
        warning = ATTRIBUTE_BINARY.format("data.dat", DRIVER.format("opaque"))
        self.assertIn(f"<li>{warning}</li>", html)
        self.assertNotIn("image.bin is shown as binary", html)

    def test_base_resolves_the_branch_not_a_shadow(self) -> None:
        head = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", "refs/tags/main", head)
        tag_shadow = self._render("main", [])
        write(self._path(".git", "main"), f"{head}\n".encode())
        dir_shadow = self._render("main", [])

        for html in (tag_shadow, dir_shadow):
            self.assertIn('id="commits" data-commits="1"', html)
            self.assertIn("<dt>Base</dt><dd>refs/heads/main @ ", html)

    def test_base_refuses_ambiguous_and_other_refs(self) -> None:
        head = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", "refs/remotes/main", head)
        git(self.repo, "update-ref", "refs/tags/v1", head)
        cases = {
            "main": "ambiguous base ref",
            "refs/tags/v1": "unknown base ref",
            "HEAD~1": "unknown base ref",
            head: "unknown base ref",
        }

        for base, message in cases.items():
            with (
                self.subTest(base=base),
                self.assertRaisesRegex(ReviewError, message),
            ):
                self._render(base, [])

    def test_invisible_characters_are_marked(self) -> None:
        tree = git(self.repo, "rev-parse", "HEAD^{tree}")
        message = f"fix{RLO}: subject\n\nbody{LRI}text"
        commit = git(self.repo, "commit-tree", tree, "-p", "HEAD", "-m", message)
        git(self.repo, "update-ref", "HEAD", commit)
        write(self._path(f"evil{RLO}txt.py"), f"code{ZWSP}line{BOM}\n".encode())
        note = os.path.join(self.root, "note.txt")
        write(note, f"note{INVISIBLE}\n".encode())

        html = self._render("main", [note])

        for char in INVISIBLE:
            self.assertNotIn(char, html, f"U+{ord(char):04X}")
        self.assertIn(f"fix{marks(RLO)}: subject", html)
        self.assertIn(f"body{marks(LRI)}text", html)
        self.assertIn(f"evil{marks(RLO)}txt.py", html)
        self.assertIn(f"code{marks(ZWSP)}line{marks(BOM)}", html)
        self.assertIn(f"note{marks(INVISIBLE)}", html)


if __name__ == "__main__":
    unittest.main()
