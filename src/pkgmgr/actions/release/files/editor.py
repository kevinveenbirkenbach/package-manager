from __future__ import annotations

import contextlib
import os
import subprocess
import tempfile


def _open_editor_for_changelog(
    initial_message: str | None = None,
    findings: list[str] | None = None,
) -> str:
    """Args:
    initial_message: the previous attempt, pre-loaded for editing.
    findings: why that attempt was rejected, shown above it.
    """
    editor = os.environ.get("EDITOR", "nano")

    with tempfile.NamedTemporaryFile(
        mode="w+",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp_path = tmp.name
        tmp.write(
            "; Write the changelog entry for this release.\n"
            "; Lines starting with ';' are ignored.\n"
            "; A leading '#' becomes a sub-heading; `code` becomes italic.\n"
            "; Empty result will fall back to a generic message.\n"
        )
        if findings:
            tmp.write(";\n; markdown-lint rejected the previous entry:\n")
            for finding in findings:
                for line in str(finding).splitlines() or [""]:
                    tmp.write(f";   {line}\n")
        tmp.write("\n")
        if initial_message:
            tmp.write(initial_message.strip() + "\n")
        tmp.flush()

    try:
        subprocess.call([editor, tmp_path])
    except FileNotFoundError:
        print(
            f"[WARN] Editor {editor!r} not found; proceeding without "
            "interactive changelog message."
        )

    try:
        with open(tmp_path, encoding="utf-8") as f:
            content = f.read()
    finally:
        with contextlib.suppress(OSError):
            os.remove(tmp_path)

    lines = [line for line in content.splitlines() if not line.strip().startswith(";")]
    return "\n".join(lines).strip()
