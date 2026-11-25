import os
import shutil
import sys
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from pkgmgr.actions.publish.workflow import publish


class TestPublishWorkflowChildren(unittest.TestCase):
    def publish_with(self, mirror: str, environ: dict) -> tuple[list, str]:
        """
        Args:
            mirror: the PyPI project URL of the mirrors file.
            environ: extra environment variables of the pkgmgr process;
                "{repo}" in a value becomes the repository directory.

        Returns:
            The recorded subprocess.run calls and the repository directory,
            whose dist is a symlink to a foreign directory with an old
            artifact.
        """
        repo_dir = tempfile.mkdtemp()
        foreign = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, repo_dir)
        self.addCleanup(shutil.rmtree, foreign)
        with open(os.path.join(foreign, "example-0.9.0.tar.gz"), "w"):
            pass
        os.symlink(foreign, os.path.join(repo_dir, "dist"))

        def run(argv, *_args, **kwargs):
            if argv[2] == "build" and "--help" not in argv:
                if "--outdir" in argv:
                    out = argv[argv.index("--outdir") + 1]
                else:
                    out = os.path.join(kwargs["cwd"], "dist")
                with open(os.path.join(out, "example-1.0.0.tar.gz"), "w"):
                    pass
            return kwargs

        module = "pkgmgr.actions.publish.workflow"
        with ExitStack() as stack:
            stack.enter_context(
                patch(f"{module}.read_mirrors_file", return_value={"pypi": mirror})
            )
            stack.enter_context(
                patch(f"{module}.head_semver_tags", return_value=["v1.0.0"])
            )
            resolver = stack.enter_context(patch(f"{module}.TokenResolver"))
            mock_run = stack.enter_context(
                patch(f"{module}.subprocess.run", side_effect=run)
            )
            stack.enter_context(
                patch.dict(
                    os.environ,
                    {
                        name: value.format(repo=repo_dir)
                        for name, value in environ.items()
                    },
                )
            )
            resolver.return_value.get_token.return_value = MagicMock(token="t")
            publish(repo={}, repo_dir=repo_dir, interactive=False, allow_prompt=False)
        return mock_run.call_args_list, repo_dir

    def test_every_child_runs_under_the_current_interpreter(self):
        calls, _ = self.publish_with("https://pypi.org/project/example/", {})
        argvs = [call.args[0] for call in calls]
        self.assertEqual(
            [argv[2] for argv in argvs], ["build", "twine", "build", "twine"]
        )
        self.assertEqual({argv[0] for argv in argvs}, {sys.executable})

    def test_children_never_run_in_the_repository(self):
        calls, repo_dir = self.publish_with("https://pypi.org/project/example/", {})
        cwds = {call.kwargs["cwd"] for call in calls}
        self.assertEqual(len(cwds), 1)
        self.assertNotEqual(os.path.realpath(cwds.pop()), os.path.realpath(repo_dir))

    def test_only_the_fresh_build_is_uploaded(self):
        calls, repo_dir = self.publish_with("https://pypi.org/project/example/", {})
        upload = calls[-1].args[0]
        self.assertEqual(
            [os.path.basename(path) for path in upload if path.endswith(".tar.gz")],
            ["example-1.0.0.tar.gz"],
        )
        self.assertEqual(calls[2].args[0][-1], repo_dir)

    def test_no_pkgmgr_variable_reaches_a_child(self):
        calls, _ = self.publish_with(
            "https://pypi.org/project/example/",
            {"PKGMGR_PYPI_TOKEN": "secret", "PKGMGR_GITHUB_TOKEN": "secret"},
        )
        for call in calls:
            self.assertFalse(
                [name for name in call.kwargs["env"] if name.startswith("PKGMGR_")]
            )
        self.assertEqual(calls[-1].kwargs["env"]["TWINE_PASSWORD"], "t")

    def test_no_repository_path_stays_on_the_children_pythonpath(self):
        calls, _ = self.publish_with(
            "https://pypi.org/project/example/",
            {"PYTHONPATH": os.pathsep.join(["{repo}", "{repo}/src", "/opt/keep"])},
        )
        self.assertEqual(
            {call.kwargs["env"]["PYTHONPATH"] for call in calls}, {"/opt/keep"}
        )

    def test_the_upload_goes_to_the_host_of_the_mirror(self):
        for mirror, url in (
            ("https://pypi.org/project/example/", "https://upload.pypi.org/legacy/"),
            ("https://test.pypi.org/project/example/", "https://test.pypi.org/legacy/"),
        ):
            with self.subTest(mirror=mirror):
                calls, _ = self.publish_with(mirror, {})
                upload = calls[-1].args[0]
                self.assertIn("--non-interactive", upload)
                self.assertEqual(upload[upload.index("--repository-url") + 1], url)


if __name__ == "__main__":
    unittest.main()
