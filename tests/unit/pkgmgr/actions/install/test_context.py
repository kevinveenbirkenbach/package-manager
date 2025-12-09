import unittest
from pkgmgr.actions.repository.install.context import RepoContext


class TestRepoContext(unittest.TestCase):
    def test_repo_context_fields_are_stored(self):
        repo = {"name": "test-repo"}
        ctx = RepoContext(
            repo=repo,
            identifier="test-id",
            repo_dir="/tmp/test",
            repositories_base_dir="/tmp",
            bin_dir="/usr/local/bin",
            all_repos=[repo],
            no_verification=True,
            preview=False,
            quiet=True,
            clone_mode="ssh",
            update_dependencies=True,
        )

        self.assertEqual(ctx.repo, repo)
        self.assertEqual(ctx.identifier, "test-id")
        self.assertEqual(ctx.repo_dir, "/tmp/test")
        self.assertEqual(ctx.repositories_base_dir, "/tmp")
        self.assertEqual(ctx.bin_dir, "/usr/local/bin")
        self.assertEqual(ctx.all_repos, [repo])
        self.assertTrue(ctx.no_verification)
        self.assertFalse(ctx.preview)
        self.assertTrue(ctx.quiet)
        self.assertEqual(ctx.clone_mode, "ssh")
        self.assertTrue(ctx.update_dependencies)


if __name__ == "__main__":
    unittest.main()