"""
Integration test: update all configured repositories using
--clone-mode shallow and --no-verification, WITHOUT system updates.

This test is intended to be run inside the Docker container where:
  - network access is available,
  - the config/config.yaml is present,
  - and it is safe to perform real git operations.

It passes if BOTH commands complete successfully (in separate tests):
  1) pkgmgr update --all --clone-mode shallow --no-verification
  2) nix run .#pkgmgr -- update --all --clone-mode shallow --no-verification
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_install_pkgmgr_shallow import (
    nix_profile_list_debug,
    remove_pkgmgr_from_nix_profile,
    pkgmgr_help_debug,
)


def _make_temp_gitconfig_with_safe_dirs(home: Path) -> Path:
    gitconfig = home / ".gitconfig"
    gitconfig.write_text(
        "[safe]\n"
        "\tdirectory = /src\n"
        "\tdirectory = /src/.git\n"
        "\tdirectory = *\n"
    )
    return gitconfig


class TestIntegrationUpdateAllshallowNoSystem(unittest.TestCase):
    def _common_env(self, home_dir: str) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = home_dir

        home = Path(home_dir)
        home.mkdir(parents=True, exist_ok=True)

        env["GIT_CONFIG_GLOBAL"] = str(_make_temp_gitconfig_with_safe_dirs(home))

        # Ensure nix is discoverable if the container has it
        env["PATH"] = "/nix/var/nix/profiles/default/bin:" + env.get("PATH", "")

        return env

    def _run_cmd(self, cmd: list[str], label: str, env: dict[str, str]) -> None:
        cmd_repr = " ".join(cmd)
        print(f"\n[TEST] Running ({label}): {cmd_repr}")

        proc = subprocess.run(
            cmd,
            check=False,
            cwd=os.getcwd(),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        print(proc.stdout.rstrip())

        if proc.returncode != 0:
            print(f"\n[TEST] Command failed ({label})")
            print(f"[TEST] Command : {cmd_repr}")
            print(f"[TEST] Exit code: {proc.returncode}")

            nix_profile_list_debug(f"ON FAILURE ({label})")

            raise AssertionError(
                f"({label}) {cmd_repr!r} failed with exit code {proc.returncode}.\n\n"
                f"--- output ---\n{proc.stdout}\n"
            )

    def _common_setup(self) -> None:
        nix_profile_list_debug("BEFORE CLEANUP")
        remove_pkgmgr_from_nix_profile()
        nix_profile_list_debug("AFTER CLEANUP")

    def test_update_all_repositories_shallow_pkgmgr_no_system(self) -> None:
        self._common_setup()
        with tempfile.TemporaryDirectory(prefix="pkgmgr-updateall-nosys-") as tmp:
            env = self._common_env(tmp)
            args = [
                "update",
                "--all",
                "--clone-mode",
                "shallow",
                "--no-verification",
            ]
            self._run_cmd(["pkgmgr", *args], label="pkgmgr", env=env)
            pkgmgr_help_debug()

    def test_update_all_repositories_shallow_nix_pkgmgr_no_system(self) -> None:
        self._common_setup()
        with tempfile.TemporaryDirectory(prefix="pkgmgr-updateall-nosys-nix-") as tmp:
            env = self._common_env(tmp)
            args = [
                "update",
                "--all",
                "--clone-mode",
                "shallow",
                "--no-verification",
            ]
            self._run_cmd(
                ["nix", "run", ".#pkgmgr", "--", *args],
                label="nix run .#pkgmgr",
                env=env,
            )
            pkgmgr_help_debug()


if __name__ == "__main__":
    unittest.main()
