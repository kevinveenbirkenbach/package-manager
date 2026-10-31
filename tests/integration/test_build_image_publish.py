from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = "--build-arg BASE_IMAGE=ghcr.io/kevinveenbirkenbach/base-{distro}:latest ."


class TestBuildImagePublish(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.log = tmp / "docker.log"
        fake = tmp / "docker"
        fake.write_text('#!/usr/bin/env bash\necho "$*" >> "$FAKE_DOCKER_LOG"\n')
        fake.chmod(0o755)
        self.env = {
            k: v for k, v in os.environ.items() if not k.startswith("BASE_IMAGES_")
        }
        self.env["PATH"] = f"{tmp}{os.pathsep}{os.environ['PATH']}"
        self.env["FAKE_DOCKER_LOG"] = str(self.log)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, script: str, distro: str, *args: str, **env: str):
        result = subprocess.run(
            ["bash", f"scripts/build/{script}", *args],
            check=False,
            cwd=REPO_ROOT,
            env={**self.env, "PKGMGR_DISTRO": distro, **env},
            capture_output=True,
            text=True,
        )
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result, calls

    def _publish(self, distro: str, *args: str):
        return self._run(
            "image.sh",
            distro,
            "--publish",
            "--registry",
            "ghcr.io",
            "--owner",
            "o",
            "--version",
            "2.1.2",
            *args,
        )

    def test_platform_pushes_only_the_arch_tag(self) -> None:
        result, calls = self._publish("debian", "--platform", "linux/arm64")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            calls,
            [
                (
                    "buildx build --push -t ghcr.io/o/pkgmgr-debian:2.1.2-arm64 "
                    "--platform linux/arm64 "
                )
                + BASE.format(distro="debian")
            ],
        )

    def test_merge_joins_arch_tags_under_release_and_alias_tags(self) -> None:
        result, calls = self._publish("arch", "--stable", "true", "--merge")

        self.assertEqual(result.returncode, 0, result.stderr)
        tags = " ".join(
            f"-t ghcr.io/o/{image}:{tag}"
            for image in ("pkgmgr-arch", "pkgmgr")
            for tag in ("latest", "2.1.2", "stable")
        )
        self.assertEqual(
            calls,
            [
                (
                    f"buildx imagetools create {tags} "
                    "ghcr.io/o/pkgmgr-arch:2.1.2-amd64 ghcr.io/o/pkgmgr-arch:2.1.2-arm64"
                ),
                "buildx imagetools inspect ghcr.io/o/pkgmgr-arch:2.1.2",
            ],
        )

    def test_unknown_platform_and_merge_without_publish_are_refused(self) -> None:
        unknown, _ = self._publish("debian", "--platform", "linux/s390x")
        no_publish, calls = self._run("image.sh", "debian", "--merge")

        self.assertEqual(unknown.returncode, 2)
        self.assertEqual(no_publish.returncode, 2)
        self.assertEqual(calls, [])

    def test_publish_builds_each_platform_then_merges(self) -> None:
        result, calls = self._run(
            "publish.sh", "fedora", OWNER="o", VERSION="2.1.2", DISTROS="fedora"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [c.split(" -t ")[0] for c in calls],
            ["buildx build --push", "buildx build --push", "buildx imagetools create"]
            + ["buildx imagetools inspect ghcr.io/o/pkgmgr-fedora:2.1.2"],
        )
        self.assertIn("--platform linux/amd64", calls[0])
        self.assertIn("--platform linux/arm64", calls[1])
        self.assertNotIn(":stable", calls[2])


if __name__ == "__main__":
    unittest.main()
