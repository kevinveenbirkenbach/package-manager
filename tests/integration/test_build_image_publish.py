from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = "--build-arg BASE_IMAGE=ghcr.io/kevinveenbirkenbach/base-{distro}:latest ."
STAMP = "1767225600"
DIGEST = "{{json .Manifest.Digest}}"

FAKE_DOCKER = """#!/usr/bin/env bash
echo "$*" >> "$FAKE_DOCKER_LOG"
case "$*" in
  "run "*" ghcr.io/"*)
    for tag in ${FAKE_PUBLISHED_TAGS}; do
      if [[ "$*" == *" ${tag} -lc "* ]]; then echo "${FAKE_PUBLISHED_SET}"; exit 0; fi
    done
    exit 1 ;;
  "run "*) echo "${FAKE_BUILT_SET}" ;;
  "buildx imagetools create --dry-run "*) echo "${FAKE_PLANNED_INDEX}" ;;
  "buildx imagetools inspect --raw "*)
    if [[ " ${FAKE_CURRENT_TAGS} " == *" ${!#} "* ]]; then
      echo "${FAKE_PLANNED_INDEX}"
    else
      echo stale
    fi ;;
  "buildx imagetools inspect --format "*)
    if [[ "${!#}" == "${FAKE_DRIFTED_TAG}" ]]; then echo old; else echo new; fi ;;
esac
"""


def refs(image: str, *tags: str) -> list[str]:
    return [f"ghcr.io/o/{image}:{tag}" for tag in tags]


def sources(distro: str, version: str) -> str:
    return " ".join(refs(f"pkgmgr-{distro}", f"{version}-amd64", f"{version}-arm64"))


def tag_args(tags: list[str]) -> str:
    return " ".join(f"-t {tag}" for tag in tags)


class TestBuildImagePublish(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.log = tmp / "docker.log"
        fake = tmp / "docker"
        fake.write_text(FAKE_DOCKER)
        fake.chmod(0o755)
        date = tmp / "date"
        date.write_text(f"#!/usr/bin/env bash\necho {STAMP}\n")
        date.chmod(0o755)
        self.env = {
            k: v for k, v in os.environ.items() if not k.startswith("BASE_IMAGES_")
        }
        self.env["PATH"] = f"{tmp}{os.pathsep}{os.environ['PATH']}"
        self.env["FAKE_DOCKER_LOG"] = str(self.log)
        self.env["FAKE_BUILT_SET"] = "built"
        self.env["FAKE_PUBLISHED_SET"] = "published"
        self.env["FAKE_PUBLISHED_TAGS"] = ""
        self.env["FAKE_PLANNED_INDEX"] = "planned"
        self.env["FAKE_CURRENT_TAGS"] = ""
        self.env["FAKE_DRIFTED_TAG"] = ""

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

    def _publish(self, distro: str, version: str, *args: str, **env: str):
        return self._run(
            "image.sh",
            distro,
            "--publish",
            "--registry",
            "ghcr.io",
            "--owner",
            "o",
            "--version",
            version,
            *args,
            **env,
        )

    def test_platform_pushes_only_the_arch_tag(self) -> None:
        result, calls = self._publish("debian", "2.1.2", "--platform", "linux/arm64")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            calls,
            [
                ("buildx build --load --platform linux/arm64 -t pkgmgr-debian:probe ")
                + BASE.format(distro="debian"),
                (
                    "run --rm --platform linux/arm64 --entrypoint bash "
                    "pkgmgr-debian:probe -lc dpkg-query -W"
                ),
                (
                    "run --rm --pull always --platform linux/arm64 --entrypoint bash "
                    "ghcr.io/o/pkgmgr-debian:2.1.2 -lc dpkg-query -W"
                ),
                (
                    "buildx build --push -t ghcr.io/o/pkgmgr-debian:2.1.2-arm64 "
                    "--platform linux/arm64 "
                )
                + BASE.format(distro="debian"),
            ],
        )

    def test_platform_unchanged_since_its_own_published_version_pushes_nothing(
        self,
    ) -> None:
        result, calls = self._publish(
            "debian",
            "2.3.0",
            "--platform",
            "linux/arm64",
            FAKE_BUILT_SET="same",
            FAKE_PUBLISHED_SET="same",
            FAKE_PUBLISHED_TAGS="ghcr.io/o/pkgmgr-debian:2.3.0",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nothing to push", result.stdout)
        self.assertFalse([c for c in calls if c.startswith("buildx build --push")])

    def test_platform_pushes_when_its_packages_changed(self) -> None:
        result, calls = self._publish(
            "debian",
            "2.3.0",
            "--platform",
            "linux/arm64",
            FAKE_PUBLISHED_TAGS="ghcr.io/o/pkgmgr-debian:2.3.0",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(calls[-1].startswith("buildx build --push"), calls)

    def test_platform_pushes_while_its_version_is_not_out(self) -> None:
        result, calls = self._publish(
            "debian",
            "2.4.0",
            "--platform",
            "linux/arm64",
            FAKE_BUILT_SET="same",
            FAKE_PUBLISHED_SET="same",
            FAKE_PUBLISHED_TAGS="ghcr.io/o/pkgmgr-debian:latest",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            (
                "run --rm --pull always --platform linux/arm64 --entrypoint bash "
                "ghcr.io/o/pkgmgr-debian:2.4.0 -lc dpkg-query -W"
            ),
            calls,
        )
        self.assertTrue(calls[-1].startswith("buildx build --push"), calls)

    def test_merge_of_the_newest_release_tags_latest_and_its_prefixes(self) -> None:
        result, calls = self._publish(
            "arch", "2.4.0", "--aliases", "latest 2 2.4", "--merge"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        moving = refs("pkgmgr-arch", "2.4.0", "latest", "2", "2.4") + refs(
            "pkgmgr", "2.4.0", "latest", "2", "2.4"
        )
        stamps = refs("pkgmgr-arch", f"2.4.0.{STAMP}") + refs(
            "pkgmgr", f"2.4.0.{STAMP}"
        )
        self.assertEqual(
            calls,
            [
                (
                    "buildx imagetools create --dry-run "
                    f"-t ghcr.io/o/pkgmgr-arch:2.4.0 {sources('arch', '2.4.0')}"
                ),
                "buildx imagetools inspect --raw ghcr.io/o/pkgmgr-arch:2.4.0",
                (
                    f"buildx imagetools create {tag_args(moving + stamps)} "
                    f"{sources('arch', '2.4.0')}"
                ),
                f"buildx imagetools inspect --format {DIGEST} ghcr.io/o/pkgmgr-arch:2.4.0",
            ]
            + [f"buildx imagetools inspect --format {DIGEST} {t}" for t in moving],
        )

    def test_merge_of_an_older_stable_release_tags_stable_and_only_its_own_prefixes(
        self,
    ) -> None:
        result, calls = self._publish(
            "debian", "2.3.0", "--aliases", "2.3 stable", "--merge"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        tags = refs("pkgmgr-debian", "2.3.0", "2.3", "stable", f"2.3.0.{STAMP}")
        self.assertIn(
            f"buildx imagetools create {tag_args(tags)} {sources('debian', '2.3.0')}",
            calls,
        )

    def test_merge_moves_stable_to_an_unchanged_build_without_a_new_stamp(
        self,
    ) -> None:
        result, calls = self._publish(
            "debian",
            "2.4.0",
            "--aliases",
            "latest 2 2.4 stable",
            "--merge",
            FAKE_CURRENT_TAGS=" ".join(
                refs("pkgmgr-debian", "2.4.0", "latest", "2", "2.4")
            ),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [c for c in calls if c.startswith("buildx imagetools create -t")],
            [
                "buildx imagetools create -t ghcr.io/o/pkgmgr-debian:stable "
                + sources("debian", "2.4.0")
            ],
        )

    def test_merge_pushes_nothing_when_every_tag_shows_the_build(self) -> None:
        result, calls = self._publish(
            "arch",
            "2.4.0",
            "--aliases",
            "latest 2 2.4 stable",
            "--merge",
            FAKE_CURRENT_TAGS=" ".join(
                refs("pkgmgr-arch", "2.4.0", "latest", "2", "2.4", "stable")
                + refs("pkgmgr", "2.4.0", "latest", "2", "2.4", "stable")
            ),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nothing to push", result.stdout)
        self.assertEqual(
            [c for c in calls if c.startswith("buildx imagetools create -t")], []
        )

    def test_merge_fails_when_a_tag_drifts_from_its_version(self) -> None:
        result, _ = self._publish(
            "debian",
            "2.1.2",
            "--aliases",
            "2.1",
            "--merge",
            FAKE_DRIFTED_TAG="ghcr.io/o/pkgmgr-debian:2.1",
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            ":2.1.2 and ghcr.io/o/pkgmgr-debian:2.1 point at different images",
            result.stderr,
        )

    def test_unknown_platform_merge_without_publish_or_aliases_are_refused(
        self,
    ) -> None:
        unknown, _ = self._publish("debian", "2.1.2", "--platform", "linux/s390x")
        no_publish, _ = self._run("image.sh", "debian", "--merge")
        no_aliases, calls = self._publish("debian", "2.1.2", "--merge")

        self.assertEqual(unknown.returncode, 2)
        self.assertEqual(no_publish.returncode, 2)
        self.assertEqual(no_aliases.returncode, 2)
        self.assertEqual(calls, [])

    def test_publish_builds_each_platform_then_merges(self) -> None:
        result, calls = self._run(
            "publish.sh",
            "fedora",
            OWNER="o",
            VERSION="2.1.2",
            ALIASES="2.1 stable",
            DISTROS="fedora",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        pushes = [
            c
            for c in calls
            if c.startswith(("buildx build --push", "buildx imagetools create"))
        ]
        self.assertEqual(
            [c.split(" -t ")[0] for c in pushes],
            [
                "buildx build --push",
                "buildx build --push",
                "buildx imagetools create --dry-run",
                "buildx imagetools create",
            ],
        )
        self.assertIn("--platform linux/amd64", pushes[0])
        self.assertIn("--platform linux/arm64", pushes[1])
        self.assertIn("-t ghcr.io/o/pkgmgr-fedora:stable ", pushes[3])
        self.assertNotIn(":latest", pushes[3])


if __name__ == "__main__":
    unittest.main()
