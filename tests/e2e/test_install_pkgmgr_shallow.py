import runpy
import sys
import os
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
      - 'pkgmgr'          (the actual name shown in `nix profile list`)
      - 'package-manager' (the name mentioned in Nix's own error hints)
    """
    for spec in ("pkgmgr", "package-manager"):
        subprocess.run(
            ["nix", "profile", "remove", spec],
            check=False,  # never fail on cleanup
        )


def pkgmgr_help_debug() -> None:
    """
    Run `pkgmgr --help` after installation *inside an interactive bash shell*,
    print its output and return code, but never fail the test.

    Reason:
      - The installer adds venv/alias setup into shell rc files (~/.bashrc, ~/.zshrc)
      - Those changes are only applied in a new interactive shell session.
    """
    print("\n--- PKGMGR HELP (after installation, via bash -i) ---")

    # Simulate a fresh interactive bash, so ~/.bashrc gets sourced
    proc = subprocess.run(
        ["bash", "-i", "-c", "pkgmgr --help"],
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()

    if stdout:
        print(stdout)
    if stderr:
        print("stderr:", stderr)

    print(f"returncode: {proc.returncode}")
    print("--- END ---\n")

    # Important: this is **debug-only**. Do NOT fail the test here.
    # If you ever want to hard-assert on this, you can add an explicit
    # assertion in the test method instead of here.


class TestIntegrationInstalPKGMGRShallow(unittest.TestCase):
    def test_install_pkgmgr_self_install(self) -> None:
        """
        End-to-end test that runs "python main.py install pkgmgr ..." inside
        the test container.

        We isolate HOME into /tmp/pkgmgr-self-install so that:
          - ~/.config/pkgmgr points to an isolated test config area
          - ~/Repositories is owned by the current user inside the container
            (avoiding Nix's 'repository path is not owned by current user' error)
        """
        # Use a dedicated HOME for this test to avoid permission/ownership issues
        temp_home = "/tmp/pkgmgr-self-install"
        os.makedirs(temp_home, exist_ok=True)

        original_argv = sys.argv
        original_environ = os.environ.copy()

        try:
            # Isolate HOME so that ~ expands to /tmp/pkgmgr-self-install
            os.environ["HOME"] = temp_home

            # Optional: ensure XDG_* also use the temp HOME for extra isolation
            os.environ.setdefault("XDG_CONFIG_HOME", os.path.join(temp_home, ".config"))
            os.environ.setdefault("XDG_CACHE_HOME", os.path.join(temp_home, ".cache"))
            os.environ.setdefault("XDG_DATA_HOME", os.path.join(temp_home, ".local", "share"))

            # Debug before cleanup
            nix_profile_list_debug("BEFORE CLEANUP")

            # Cleanup: aggressively try to drop any pkgmgr/profile entries
            remove_pkgmgr_from_nix_profile()

            # Debug after cleanup
            nix_profile_list_debug("AFTER CLEANUP")

            sys.argv = [
                "python",
                "install",
                "pkgmgr",
                "--clone-mode",
                "shallow",
                "--no-verification",
            ]

            # Run installation via main.py
            runpy.run_module("main", run_name="__main__")

            # After successful installation: run `pkgmgr --help` for debug
            pkgmgr_help_debug()

        finally:
            sys.argv = original_argv
            # Restore full environment
            os.environ.clear()
            os.environ.update(original_environ)


if __name__ == "__main__":
    unittest.main()
