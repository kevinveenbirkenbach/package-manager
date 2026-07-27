from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
import tempfile

_HEADING = re.compile(r"^\s*#{1,6}\s+(.*?)\s*#*\s*$")
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_FINDING = re.compile(r"\bMD\d{3}\b")
_MULTI_BLANK = re.compile(r"\n{3,}")


class ChangelogLintError(RuntimeError):
    """Raised when a changelog entry cannot be made markdown-lint clean."""


def transform_changelog_message(text: str) -> str:
    """Normalise a free-form release message into the changelog house style.

    A leading ``#`` heading becomes a bold line of its own (markdown
    headings inside an entry body would collide with the ``## [version]``
    structure), and inline ``code`` spans become ``*italic*`` so the entry
    stays free of backticks.
    """
    text = _INLINE_CODE.sub(r"*\1*", text)

    out: list[str] = []
    for line in text.split("\n"):
        heading = _HEADING.match(line)
        if heading:
            if out and out[-1].strip():
                out.append("")
            out.append(f"**{heading.group(1).strip()}**")
            out.append("")
        else:
            out.append(line)

    joined = _MULTI_BLANK.sub("\n\n", "\n".join(out))
    return joined.strip()


def lint_changelog_entry(reference_path: str, entry: str) -> list[str]:
    """Return markdown-lint findings for *entry* (empty list when clean).

    The entry is checked inside a minimal ``# Changelog`` document so the
    result reflects only the entry, not pre-existing issues in the target
    file. ``markdownlint-cli2`` is used when available (picking up the
    target repository's own config, i.e. the same rules the repo enforces);
    otherwise a small built-in check runs.
    """
    document = f"# Changelog\n\n{entry.strip()}\n"
    if shutil.which("markdownlint-cli2"):
        return _markdownlint(reference_path, document)
    return _builtin_lint(document)


def _markdownlint(reference_path: str, document: str) -> list[str]:
    directory = os.path.dirname(os.path.abspath(reference_path)) or "."
    fd, tmp_path = tempfile.mkstemp(
        suffix=".md", prefix=".pkgmgr-changelog-", dir=directory
    )
    name = os.path.basename(tmp_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(document)
        proc = subprocess.run(
            ["markdownlint-cli2", name],
            cwd=directory,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return []
        output = f"{proc.stdout or ''}{proc.stderr or ''}"
        findings = [
            line.strip().replace(name, "changelog entry")
            for line in output.splitlines()
            if _FINDING.search(line)
        ]
        return findings or [output.strip() or "markdown-lint reported an error"]
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _builtin_lint(document: str) -> list[str]:
    errors: list[str] = []
    for number, line in enumerate(document.split("\n"), start=1):
        if line != line.rstrip():
            errors.append(f"line {number}: trailing whitespace (MD009)")
        if "`" in line:
            errors.append(f"line {number}: backtick is not allowed (use *italic*)")
    if "\n\n\n" in document:
        errors.append("multiple consecutive blank lines (MD012)")
    return errors
