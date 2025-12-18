import os
from tests.e2e._util import run
import tempfile
import unittest
from pathlib import Path


class TestPkgmgrInstallThreeTimesNix(unittest.TestCase):
    def test_three_times_install_nix(self):
        with tempfile.TemporaryDirectory(prefix="pkgmgr-nix-") as tmp:
            tmp_path = Path(tmp)

            env = os.environ.copy()
            env["HOME"] = tmp

            # Ensure nix is found
            env["PATH"] = "/nix/var/nix/profiles/default/bin:" + os.environ.get(
                "PATH", ""
            )

            # IMPORTANT:
            # nix run uses git+file:///src internally -> Git will reject /src if it's not a safe.directory.
            # Our test sets HOME to a temp dir, so we must provide a temp global gitconfig.
            gitconfig = tmp_path / ".gitconfig"
            gitconfig.write_text(
                "[safe]\n\tdirectory = /src\n\tdirectory = /src/.git\n\tdirectory = *\n"
            )
            env["GIT_CONFIG_GLOBAL"] = str(gitconfig)

            for i in range(1, 4):
                print(f"\n=== RUN {i}/3 ===")
                run(
                    "nix run .#pkgmgr -- install pkgmgr --update --clone-mode shallow --no-verification",
                    env=env,
                    shell=True,
                )
