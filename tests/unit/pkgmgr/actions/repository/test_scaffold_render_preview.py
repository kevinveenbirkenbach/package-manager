from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.repository.scaffold import render_default_templates


class TestScaffoldRenderPreview(unittest.TestCase):
    def test_render_preview_does_not_write(self) -> None:
        with (
            patch("pkgmgr.actions.repository.scaffold._templates_dir", return_value="/tpl"),
            patch("pkgmgr.actions.repository.scaffold.os.path.isdir", return_value=True),
            patch("pkgmgr.actions.repository.scaffold.os.walk", return_value=[("/tpl", [], ["README.md.j2"])]),
            patch("pkgmgr.actions.repository.scaffold.os.path.relpath", return_value="README.md.j2"),
            patch("pkgmgr.actions.repository.scaffold.os.makedirs") as mk,
            patch("pkgmgr.actions.repository.scaffold.open", create=True) as op,
            patch("pkgmgr.actions.repository.scaffold.Environment") as env_cls,
        ):
            env = env_cls.return_value
            env.get_template.return_value.render.return_value = "X"

            render_default_templates(
                "/repo",
                context={"repository": "x"},
                preview=True,
            )

            mk.assert_not_called()
            op.assert_not_called()
            env.get_template.assert_not_called()


if __name__ == "__main__":
    unittest.main()
