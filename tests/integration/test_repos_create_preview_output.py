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
            patch(
                "pkgmgr.actions.repository.create.config_writer.generate_alias",
                return_value="repo",
            ),
            patch(
                "pkgmgr.actions.repository.create.config_writer.save_user_config",
            ),
            patch(
                "pkgmgr.actions.repository.create.config_writer.os.path.exists",
                return_value=False,
            ),
            patch(
                "pkgmgr.actions.repository.create.service.os.makedirs",
            ),
            patch(
                "pkgmgr.actions.repository.create.templates.TemplateRenderer._resolve_templates_dir",
                return_value="/tpl",
            ),
            patch(
                "pkgmgr.actions.repository.create.templates.os.walk",
                return_value=[("/tpl", [], ["README.md.j2"])],
            ),
            patch(
                "pkgmgr.actions.repository.create.git_bootstrap.init",
            ),
            patch(
                "pkgmgr.actions.repository.create.git_bootstrap.add_all",
            ),
            patch(
                "pkgmgr.actions.repository.create.git_bootstrap.commit",
            ),
            patch(
                "pkgmgr.actions.repository.create.mirrors.write_mirrors_file",
            ),
            patch(
                "pkgmgr.actions.repository.create.mirrors.setup_mirrors",
            ),
            patch(
                "pkgmgr.actions.repository.create.service.get_config_value",
                return_value=None,
            ),
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
        self.assertIn("[Preview] Would add repository to config:", s)
        self.assertIn("[Preview] Would ensure directory exists:", s)


if __name__ == "__main__":
    unittest.main()
