from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any

from pkgmgr.core.git.queries import get_repo_root

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
except Exception as exc:  # pragma: no cover
    Environment = None  # type: ignore
    FileSystemLoader = None  # type: ignore
    StrictUndefined = None  # type: ignore
    _JINJA_IMPORT_ERROR = exc
else:
    _JINJA_IMPORT_ERROR = None


class TemplateRenderer:
    def __init__(self) -> None:
        self.templates_dir = self._resolve_templates_dir()

    def render(
        self,
        *,
        repo_dir: str,
        context: Dict[str, Any],
        preview: bool,
    ) -> None:
        if preview:
            self._preview()
            return

        if Environment is None:
            raise RuntimeError(
                "Jinja2 is required but not available. "
                f"Import error: {_JINJA_IMPORT_ERROR}"
            )

        env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )

        for root, _, files in os.walk(self.templates_dir):
            for fn in files:
                if not fn.endswith(".j2"):
                    continue

                abs_src = os.path.join(root, fn)
                rel_src = os.path.relpath(abs_src, self.templates_dir)
                rel_out = rel_src[:-3]
                abs_out = os.path.join(repo_dir, rel_out)

                os.makedirs(os.path.dirname(abs_out), exist_ok=True)
                template = env.get_template(rel_src)
                rendered = template.render(**context)

                with open(abs_out, "w", encoding="utf-8") as f:
                    f.write(rendered)

    def _preview(self) -> None:
        for root, _, files in os.walk(self.templates_dir):
            for fn in files:
                if fn.endswith(".j2"):
                    rel = os.path.relpath(os.path.join(root, fn), self.templates_dir)
                    print(f"[Preview] Would render template: {rel} -> {rel[:-3]}")

    @staticmethod
    def _resolve_templates_dir() -> str:
        here = Path(__file__).resolve().parent
        root = get_repo_root(cwd=str(here))
        if not root:
            raise RuntimeError("Could not determine repository root for templates.")
        return os.path.join(root, "templates", "default")
