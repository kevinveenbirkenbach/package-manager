from tests.e2e._util import run
import tempfile
import unittest
from pathlib import Path

class TestMakefileThreeTimes(unittest.TestCase):
    def test_make_install_three_times(self):
        with tempfile.TemporaryDirectory(prefix="makefile-3x-") as tmp:
            repo = Path(tmp)

            # Minimal Makefile with install target
            (repo / "Makefile").write_text(
                "install:\n\t@echo install >> install.log\n"
            )

            for i in range(1, 4):
                print(f"\n=== RUN {i}/3 ===")
                run(["make", "install"], cwd=repo)

            log = (repo / "install.log").read_text().splitlines()
            self.assertEqual(
                len(log),
                3,
                "make install should have been executed exactly three times",
            )
