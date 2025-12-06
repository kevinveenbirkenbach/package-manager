import runpy
import sys
import unittest
import subprocess


def nix_profile_list_debug(label: str) -> None:
    """
    Print `nix profile list` for debugging inside the test container.
    Never fails the test.
    """
    print(f"\n--- NIX PROFILE LIST ({label}) ---")
    proc = subprocess.run(
        ["nix", "profile", "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()

    if stdout:
        print(stdout)
    if stderr:
        print("stderr:", stderr)
    print("--- END ---\n")


def remove_pkgmgr_from_nix_profile() -> None:
    """
    Best-effort cleanup before running the integration test.

    We *do not* try to parse profile indices here, because modern `nix profile list`
    prints a descriptive format without an index column inside the container.

    Instead, we directly try to remove possible names:
      - 'pkgmgr'      (the actual name shown in `nix profile list`)
      - 'package-manager' (the name mentioned in Nix's own error hints)
    """
    for spec in ("pkgmgr", "package-manager"):
        subprocess.run(
            ["nix", "profile", "remove", spec],
            check=False,  # never fail on cleanup
        )


class TestIntegrationInstalPKGMGRShallow(unittest.TestCase):
    def test_install_pkgmgr_self_install(self) -> None:
        # Debug before cleanup
        nix_profile_list_debug("BEFORE CLEANUP")

        # Cleanup: aggressively try to drop any pkgmgr/profile entries
        remove_pkgmgr_from_nix_profile()

        # Debug after cleanup
        nix_profile_list_debug("AFTER CLEANUP")

        original_argv = sys.argv
        try:
            sys.argv = [
                "python",
                "install",
                "pkgmgr",
                "--clone-mode",
                "shallow",
                "--no-verification",
            ]
            runpy.run_module("main", run_name="__main__")
        finally:
            sys.argv = original_argv


if __name__ == "__main__":
    unittest.main()
