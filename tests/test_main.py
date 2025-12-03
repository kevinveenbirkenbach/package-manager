# tests/test_main.py
import unittest
import main


class TestMainModule(unittest.TestCase):
    def test_proxy_commands_defined(self):
        """
        Basic sanity check: main.py should define PROXY_COMMANDS
        with git/docker/docker compose entries.
        """
        self.assertTrue(hasattr(main, "PROXY_COMMANDS"))
        self.assertIn("git", main.PROXY_COMMANDS)
        self.assertIn("docker", main.PROXY_COMMANDS)
        self.assertIn("docker compose", main.PROXY_COMMANDS)


if __name__ == "__main__":
    unittest.main()
