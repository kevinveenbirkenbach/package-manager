from tests.e2e._util import run
import tempfile
import unittest
from pathlib import Path
import os


class TestPkgmgrInstallThreeTimesVenv(unittest.TestCase):
    def test_three_times_install_venv(self):
        with tempfile.TemporaryDirectory(prefix="pkgmgr-venv-") as tmp:
            home = Path(tmp)
            bin_dir = home / ".local" / "bin"
            bin_dir.mkdir(parents=True)

            env = os.environ.copy()
            env["HOME"] = tmp

            # pkgmgr kommt aus dem Projekt-venv
            env["PATH"] = f"{Path.cwd() / '.venv' / 'bin'}:{bin_dir}:" + os.environ.get(
                "PATH", ""
            )

            # nix explizit deaktivieren → Python/Venv-Pfad
            env["PKGMGR_DISABLE_NIX_FLAKE_INSTALLER"] = "1"

            for i in range(1, 4):
                print(f"\n=== RUN {i}/3 ===")
                run(
                    "pkgmgr install pkgmgr --update --clone-mode shallow --no-verification",
                    env=env,
                    shell=True,
                )
