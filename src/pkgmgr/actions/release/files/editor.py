from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Optional


def _open_editor_for_changelog(initial_message: Optional[str] = None) -> str:
    editor = os.environ.get("EDITOR", "nano")

    with tempfile.NamedTemporaryFile(
        mode="w+",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp_path = tmp.name
        tmp.write(
            "# Write the changelog entry for this release.\n"
            "# Lines starting with '#' will be ignored.\n"
            "# Empty result will fall back to a generic message.\n\n"
        )
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
        with open(tmp_path, "r", encoding="utf-8") as f:
            content = f.read()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    lines = [line for line in content.splitlines() if not line.strip().startswith("#")]
    return "\n".join(lines).strip()
