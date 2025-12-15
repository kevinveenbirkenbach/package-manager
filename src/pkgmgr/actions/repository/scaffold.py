from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
except Exception as exc:  # pragma: no cover
    Environment = None  # type: ignore[assignment]
    FileSystemLoader = None  # type: ignore[assignment]
    StrictUndefined = None  # type: ignore[assignment]
    _JINJA_IMPORT_ERROR = exc
else:
    _JINJA_IMPORT_ERROR = None


def _repo_root_from_here(anchor: Optional[Path] = None) -> str:
    """
    Prefer git root (robust in editable installs / different layouts).
    Fallback to a conservative relative parent lookup.
    """
    here = (anchor or Path(__file__)).resolve().parent
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(here),
            check=False,
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            top = (r.stdout or "").strip()
            if top:
                return top
    except Exception:
        pass

    # Fallback: src/pkgmgr/actions/repository/scaffold.py -> <repo root> = parents[5]
    p = (anchor or Path(__file__)).resolve()
    if len(p.parents) < 6:
        raise RuntimeError(f"Unexpected path depth for: {p}")
    return str(p.parents[5])


def _templates_dir() -> str:
    return os.path.join(_repo_root_from_here(), "templates", "default")


def render_default_templates(
    repo_dir: str,
    *,
    context: Dict[str, Any],
    preview: bool,
) -> None:
    """
    Render templates/default/*.j2 into repo_dir.
    Keeps create.py clean: create.py calls this function only.
    """
    tpl_dir = _templates_dir()
    if not os.path.isdir(tpl_dir):
        raise RuntimeError(f"Templates directory not found: {tpl_dir}")

    # Preview mode: do not require Jinja2 at all. We only print planned outputs.
    if preview:
        for root, _, files in os.walk(tpl_dir):
            for fn in files:
                if not fn.endswith(".j2"):
                    continue
                abs_src = os.path.join(root, fn)
                rel_src = os.path.relpath(abs_src, tpl_dir)
                rel_out = rel_src[:-3]
                print(f"[Preview] Would render template: {rel_src} -> {rel_out}")
        return

    if Environment is None or FileSystemLoader is None or StrictUndefined is None:
        raise RuntimeError(
            "Jinja2 is required for repo templates but is not available. "
            f"Import error: {_JINJA_IMPORT_ERROR}"
        )

    env = Environment(
        loader=FileSystemLoader(tpl_dir),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )

    for root, _, files in os.walk(tpl_dir):
        for fn in files:
            if not fn.endswith(".j2"):
                continue

            abs_src = os.path.join(root, fn)
            rel_src = os.path.relpath(abs_src, tpl_dir)
            rel_out = rel_src[:-3]
            abs_out = os.path.join(repo_dir, rel_out)

            os.makedirs(os.path.dirname(abs_out), exist_ok=True)
            template = env.get_template(rel_src)
            rendered = template.render(**context)

            with open(abs_out, "w", encoding="utf-8") as f:
                f.write(rendered)
