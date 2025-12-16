from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.repository.create.templates import TemplateRenderer


class TestTemplateRendererPreview(unittest.TestCase):
    def test_render_preview_does_not_write(self) -> None:
        # Ensure TemplateRenderer does not try to resolve real repo root.
        with (
            patch(
                "pkgmgr.actions.repository.create.templates.TemplateRenderer._resolve_templates_dir",
                return_value="/tpl",
            ),
            patch(
                "pkgmgr.actions.repository.create.templates.os.walk",
                return_value=[("/tpl", [], ["README.md.j2"])],
            ),
            patch(
                "pkgmgr.actions.repository.create.templates.os.path.relpath",
                return_value="README.md.j2",
            ),
            patch("pkgmgr.actions.repository.create.templates.os.makedirs") as mk,
            patch("pkgmgr.actions.repository.create.templates.open", create=True) as op,
            patch("pkgmgr.actions.repository.create.templates.Environment") as env_cls,
        ):
            renderer = TemplateRenderer()

            renderer.render(
                repo_dir="/repo",
                context={"repository": "x"},
                preview=True,
            )

            mk.assert_not_called()
            op.assert_not_called()
            env_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()