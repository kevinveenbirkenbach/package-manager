from __future__ import annotations

import re

from .model import FileDiff, Hunk, Line

HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
GIT_HEADER = "diff --git "
ESCAPES = {
    "a": 7,
    "b": 8,
    "t": 9,
    "n": 10,
    "v": 11,
    "f": 12,
    "r": 13,
    '"': 34,
    "\\": 92,
}
HEADER_FIELDS = (
    "rename from ",
    "rename to ",
    "copy from ",
    "copy to ",
    "new file mode ",
    "deleted file mode ",
    "old mode ",
    "new mode ",
    "--- ",
    "+++ ",
)


def unquote(text: str) -> str:
    if len(text) < 2 or not (text.startswith('"') and text.endswith('"')):
        return text
    body = text[1:-1]
    raw = bytearray()
    index = 0
    while index < len(body):
        char = body[index]
        escaped = body[index + 1 : index + 2]
        octal = body[index + 1 : index + 4]
        if char == "\\" and escaped in ESCAPES:
            raw.append(ESCAPES[escaped])
            index += 2
        elif char == "\\" and len(octal) == 3 and set(octal) <= set("01234567"):
            raw.append(int(octal, 8) & 0xFF)
            index += 4
        else:
            raw.extend(char.encode("utf-8"))
            index += 1
    return raw.decode("utf-8", "replace")


def _side(value: str, prefix: str) -> str | None:
    value = value.removesuffix("\t")
    if value == "/dev/null":
        return None
    return unquote(value).removeprefix(prefix)


def _file(
    git_line: str, headers: list[str], pending: list[tuple[str, int, list[Line]]]
) -> FileDiff:
    fields: dict[str, str] = {}
    for header in headers:
        for key in HEADER_FIELDS:
            if header.startswith(key):
                fields[key.strip()] = header[len(key) :]
                break
    half = (len(git_line) - 1) // 2
    old_path = _side(git_line[:half], "a/")
    new_path = _side(git_line[half + 1 :], "b/")
    if "---" in fields:
        old_path = _side(fields["---"], "a/")
    if "+++" in fields:
        new_path = _side(fields["+++"], "b/")
    status = "modified"
    for kind, moved in (("rename", "renamed"), ("copy", "copied")):
        if f"{kind} from" in fields and f"{kind} to" in fields:
            old_path = unquote(fields[f"{kind} from"])
            new_path = unquote(fields[f"{kind} to"])
            status = moved
    if "new file mode" in fields:
        old_path, status = None, "added"
    if "deleted file mode" in fields:
        new_path, status = None, "deleted"
    mode_change = None
    if "old mode" in fields and "new mode" in fields:
        mode_change = f"{fields['old mode']} → {fields['new mode']}"
    return FileDiff(
        old_path=old_path,
        new_path=new_path,
        status=status,
        binary=any(header.startswith("Binary files ") for header in headers),
        mode_change=mode_change,
        hunks=tuple(
            Hunk(header, start, tuple(lines)) for header, start, lines in pending
        ),
    )


def parse_patch(text: str) -> list[FileDiff]:
    """
    Args:
        text: Output of ``git diff`` or ``git show`` produced with ``a/`` and
            ``b/`` prefixes and decoded without newline translation.

    Returns:
        One FileDiff per ``diff --git`` block, in git's order.
    """
    files: list[FileDiff] = []
    git_line: str | None = None
    headers: list[str] = []
    pending: list[tuple[str, int, list[Line]]] = []
    old_no = new_no = old_left = new_left = 0
    for raw in text.split("\n"):
        if pending and (old_left > 0 or new_left > 0):
            lines = pending[-1][2]
            sign, body = raw[:1], raw[1:]
            if sign == "+":
                lines.append(Line("add", None, new_no, body))
                new_no, new_left = new_no + 1, new_left - 1
            elif sign == "-":
                lines.append(Line("del", old_no, None, body))
                old_no, old_left = old_no + 1, old_left - 1
            elif sign == "\\":
                lines.append(Line("meta", None, None, raw))
            else:
                lines.append(Line("ctx", old_no, new_no, body))
                old_no, new_no = old_no + 1, new_no + 1
                old_left, new_left = old_left - 1, new_left - 1
            continue
        if raw.startswith(GIT_HEADER):
            if git_line is not None:
                files.append(_file(git_line, headers, pending))
            git_line, headers, pending = raw[len(GIT_HEADER) :], [], []
            continue
        if git_line is None:
            continue
        match = HUNK_HEADER.match(raw)
        if match:
            old_no, new_no = int(match[1]), int(match[3])
            old_left = 1 if match[2] is None else int(match[2])
            new_left = 1 if match[4] is None else int(match[4])
            pending.append((raw, new_no, []))
        elif pending and raw.startswith("\\"):
            pending[-1][2].append(Line("meta", None, None, raw))
        elif not pending:
            headers.append(raw)
    if git_line is not None:
        files.append(_file(git_line, headers, pending))
    return files
