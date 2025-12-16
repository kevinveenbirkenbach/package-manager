from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from pkgmgr.actions.repository.create import create_repo


class TestCreateRepoPreviewOutput(unittest.TestCase):
    def test_create_repo_preview_prints_expected_steps(self) -> None:
        cfg = {"directories": {"repositories": "/tmp/Repositories"}, "repositories": []}

        out = io.StringIO()
        with (
            redirect_stdout(out),
            patch("pkgmgr.actions.repository.create.os.path.exists", return_value=False),
            patch("pkgmgr.actions.repository.create.generate_alias", return_value="repo"),
            patch("pkgmgr.actions.repository.create.save_user_config"),
            patch("pkgmgr.actions.repository.create.os.makedirs"),
            patch("pkgmgr.actions.repository.create.render_default_templates"),
            patch("pkgmgr.actions.repository.create.write_mirrors_file"),
            patch("pkgmgr.actions.repository.create.setup_mirrors"),
            patch("pkgmgr.actions.repository.create.get_config_value", return_value=None),
            patch("pkgmgr.actions.repository.create.init"),
            patch("pkgmgr.actions.repository.create.add_all"),
            patch("pkgmgr.actions.repository.create.commit"),
        ):
            create_repo(
                "github.com/acme/repo",
                cfg,
                "/tmp/user.yml",
                "/tmp/bin",
                remote=False,
                preview=True,
            )

        s = out.getvalue()
        self.assertIn("[Preview] Would save user config:", s)
        self.assertIn("[Preview] Would ensure directory exists:", s)


if __name__ == "__main__":
    unittest.main()
