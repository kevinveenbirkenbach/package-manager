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
      - 'pkgmgr'
      - 'package-manager'
    """
    for spec in ("pkgmgr", "package-manager"):
        subprocess.run(
            ["nix", "profile", "remove", spec],
            check=False,  # never fail on cleanup
        )


def configure_git_safe_directory() -> None:
    """
    Configure Git to treat /src as a safe directory.

    Needed because /src is a bind-mounted repository in CI, often owned by a
    different UID. Modern Git aborts with:
      'fatal: detected dubious ownership in repository at /src/.git'

    This fix applies ONLY inside this test container.
    """
    try:
        subprocess.run(
            ["git", "config", "--global", "--add", "safe.directory", "/src"],
            check=False,
        )
    except FileNotFoundError:
        print("[WARN] git not found – skipping safe.directory configuration")


def pkgmgr_help_debug() -> None:
    """
    Run `pkgmgr --help` after installation *inside an interactive bash shell*,
    print its output and return code, but never fail the test.

    This ensures the installer’s shell RC changes are actually loaded.
    """
    print("\n--- PKGMGR HELP (after installation, via bash -i) ---")

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


class TestIntegrationInstalPKGMGRShallow(unittest.TestCase):
    def test_install_pkgmgr_self_install(self) -> None:
        """
        End-to-end test that runs "python main.py install pkgmgr ..." inside
        the test container.

        HOME is isolated to avoid permission problems with Nix & repositories.
        """
        temp_home = "/tmp/pkgmgr-self-install"
        os.makedirs(temp_home, exist_ok=True)

        original_argv = sys.argv
        original_environ = os.environ.copy()

        try:
            # Isolate HOME so that ~ expands to /tmp/pkgmgr-self-install
            os.environ["HOME"] = temp_home

            # Optional XDG override for a fully isolated environment
            os.environ.setdefault("XDG_CONFIG_HOME", os.path.join(temp_home, ".config"))
            os.environ.setdefault("XDG_CACHE_HOME", os.path.join(temp_home, ".cache"))
            os.environ.setdefault("XDG_DATA_HOME", os.path.join(temp_home, ".local", "share"))

            # 🔧 IMPORTANT FIX: allow Git to access /src safely
            configure_git_safe_directory()

            # Debug before cleanup
            nix_profile_list_debug("BEFORE CLEANUP")

            # Cleanup: drop any pkgmgr entries from nix profile
            remove_pkgmgr_from_nix_profile()

            # Debug after cleanup
            nix_profile_list_debug("AFTER CLEANUP")

            # Prepare argv for module execution
            sys.argv = [
                "python",
                "install",
                "pkgmgr",
                "--clone-mode",
                "shallow",
                "--no-verification",
            ]

            # Execute installation via main.py
            runpy.run_module("main", run_name="__main__")

            # Debug: interactive shell test
            pkgmgr_help_debug()

        finally:
            # Restore system state
            sys.argv = original_argv
            os.environ.clear()
            os.environ.update(original_environ)


if __name__ == "__main__":
    unittest.main()
