from __future__ import annotations

import base64
import hashlib
import os
import tempfile

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .collect import collect_review
from .model import Review, ReviewError

TEMPLATE = "review.html.j2"
INVISIBLE = {
    code: f"<U+{code:04X}>"
    for code in (
        *range(0x200B, 0x2010),
        *range(0x202A, 0x202F),
        *range(0x2066, 0x206A),
        0x061C,
        0xFEFF,
    )
}


def _csp_hash(text: str) -> str:
    digest = hashlib.sha256(str(text).encode("utf-8")).digest()
    return "sha256-" + base64.b64encode(digest).decode("ascii")


def _visible(value: object) -> object:
    # not isinstance: Markup.translate() would splice the marks in unescaped,
    # and macro output is Markup whose text was already marked when built
    return value.translate(INVISIBLE) if type(value) is str else value


def render_review(review: Review) -> str:
    environment = Environment(
        loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__))),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        finalize=_visible,
    )
    environment.filters["csp_hash"] = _csp_hash
    return environment.get_template(TEMPLATE).render(review=review)


def write_review(
    cwd: str, out: str, max_file_lines: int, base: str | None, notes: list[str]
) -> str:
    """
    Args:
        cwd: Directory inside the git working copy to review.
        out: Output HTML path, relative to ``cwd`` unless absolute; written as
            a new mode 0600 file renamed onto it, so a symbolic link there is
            replaced, never followed.
        max_file_lines: Diff lines shown per file before the rest is summarised.
        base: Branch whose ``REF..HEAD`` commits are listed, or None.
        notes: Text files shown verbatim at the top of the page.

    Returns:
        The absolute path of the written page.
    """
    html = render_review(
        collect_review(cwd=cwd, max_file_lines=max_file_lines, base=base, notes=notes)
    )
    path = os.path.abspath(os.path.join(cwd, out))
    directory = os.path.dirname(path)
    try:
        os.makedirs(directory, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix=".review-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(html)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        except OSError:
            os.unlink(temp)
            raise
    except OSError as exc:
        raise ReviewError(f"cannot write {path!r}: {exc.strerror}") from None
    return path
