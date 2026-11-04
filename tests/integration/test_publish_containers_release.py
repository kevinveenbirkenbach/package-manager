from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RESOLVER = (
    REPO_ROOT
    / "scripts"
    / "github"
    / "publish-containers"
    / "compute-publish-container-info.sh"
)
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "publish-containers.yml"

GIT_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


class TestComputePublishContainerInfo(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.repo = tmp / "repo"
        self.repo.mkdir()
        self.output = tmp / "github_output"
        self.git("init", "-q", "-b", "main")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            env=GIT_ENV,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def commit(self, *tags: str) -> str:
        self.git("commit", "-q", "--allow-empty", "-m", " ".join(tags) or "untagged")
        for tag in tags:
            self.git("tag", tag)
        return self.git("rev-parse", "HEAD")

    def push_main(self) -> None:
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")

    def resolve(self, workflow_run_sha: str):
        self.output.write_text("")
        result = subprocess.run(
            ["bash", str(RESOLVER)],
            cwd=self.repo,
            env={
                **GIT_ENV,
                "GITHUB_OUTPUT": str(self.output),
                "WORKFLOW_RUN_SHA": workflow_run_sha,
            },
            capture_output=True,
            text=True,
            check=False,
        )
        outputs = dict(
            line.split("=", 1) for line in self.output.read_text().splitlines()
        )
        return result, outputs

    def releases(self, workflow_run_sha: str) -> list[dict[str, str]]:
        result, outputs = self.resolve(workflow_run_sha)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(outputs["releases"])

    def test_a_rebuild_with_stable_on_the_newest_release_publishes_it_once(
        self,
    ) -> None:
        self.commit("v2.3.0")
        newest = self.commit("v2.4.0", "stable")
        self.push_main()

        self.assertEqual(
            self.releases(""),
            [{"sha": newest, "version": "2.4.0", "aliases": "latest 2 2.4 stable"}],
        )

    def test_a_rebuild_with_stable_behind_publishes_the_newest_and_the_stable_release(
        self,
    ) -> None:
        self.commit("v2.2.0")
        stable = self.commit("v2.3.0", "stable")
        newest = self.commit("v2.4.0")
        self.commit("v2.5.0-rc1")
        self.push_main()

        self.assertEqual(
            self.releases(""),
            [
                {"sha": newest, "version": "2.4.0", "aliases": "latest 2 2.4"},
                {"sha": stable, "version": "2.3.0", "aliases": "2.3 stable"},
            ],
        )

    def test_the_stable_release_takes_no_prefix_a_newer_release_leads(self) -> None:
        stable = self.commit("v2.3.0", "stable")
        self.commit("v2.3.1")
        newest = self.commit("v2.4.0")
        self.push_main()

        self.assertEqual(
            self.releases(""),
            [
                {"sha": newest, "version": "2.4.0", "aliases": "latest 2 2.4"},
                {"sha": stable, "version": "2.3.0", "aliases": "stable"},
            ],
        )

    def test_a_rebuild_publishes_the_newest_release_on_main_not_its_tip(
        self,
    ) -> None:
        self.commit("v1.9.0")
        newest = self.commit("v1.10.0")
        self.commit()
        self.push_main()
        self.git("checkout", "-q", "-b", "side")
        self.commit("v3.0.0")

        result, outputs = self.resolve("")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(outputs["releases"]),
            [{"sha": newest, "version": "1.10.0", "aliases": "latest 1 1.10"}],
        )
        self.assertIn("the stable image stays where it is", result.stdout)

    def test_a_workflow_run_publishes_the_commit_it_tagged(self) -> None:
        self.commit("v2.3.0")
        tagged = self.commit("v2.4.0", "stable")
        self.push_main()

        self.assertEqual(
            self.releases(tagged),
            [{"sha": tagged, "version": "2.4.0", "aliases": "latest 2 2.4 stable"}],
        )

    def test_a_workflow_run_of_a_backport_moves_only_the_prefixes_it_leads(
        self,
    ) -> None:
        self.commit("v2.3.0")
        self.commit("v2.4.0", "stable")
        backport = self.commit("v2.3.1")
        self.push_main()

        self.assertEqual(
            self.releases(backport),
            [{"sha": backport, "version": "2.3.1", "aliases": "2.3"}],
        )

    def test_a_workflow_run_outside_main_publishes_nothing(self) -> None:
        self.commit("v2.3.0")
        self.push_main()
        self.git("checkout", "-q", "-b", "side")
        outside = self.commit("v9.0.0")

        self.assertEqual(self.releases(outside), [])

    def test_a_workflow_run_without_an_x_y_z_tag_publishes_nothing(self) -> None:
        self.commit("v2.3.0")
        candidate = self.commit("v2.4.0-rc1")
        self.push_main()

        self.assertEqual(self.releases(candidate), [])

    def test_a_rebuild_without_a_release_on_main_fails(self) -> None:
        self.commit("v1.0.0-rc1", "stable")
        self.push_main()

        result, outputs = self.resolve("")

        self.assertEqual(result.returncode, 1)
        self.assertEqual(outputs, {})
        self.assertIn("No vX.Y.Z tag is reachable from origin/main", result.stderr)


class TestPublishContainersWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = yaml.safe_load(WORKFLOW.read_text())

    def test_the_releases_are_rebuilt_daily_at_03_utc_and_on_demand(self) -> None:
        triggers = self.workflow[True]
        steps = {
            step.get("id"): step for step in self.workflow["jobs"]["prepare"]["steps"]
        }

        self.assertEqual(triggers["schedule"], [{"cron": "0 3 * * *"}])
        self.assertIn("workflow_dispatch", triggers)
        self.assertEqual(
            steps["info"]["run"],
            "bash scripts/github/publish-containers/compute-publish-container-info.sh",
        )
        self.assertEqual(
            steps["info"]["env"]["WORKFLOW_RUN_SHA"],
            "${{ github.event.workflow_run.head_sha }}",
        )

    def test_every_resolved_release_is_built_and_merged_with_its_own_tags(
        self,
    ) -> None:
        jobs = self.workflow["jobs"]
        merge_env = jobs["merge"]["steps"][-1]["env"]

        for job in ("build", "merge"):
            self.assertEqual(
                jobs[job]["strategy"]["matrix"]["release"],
                "${{ fromJSON(needs.prepare.outputs.releases) }}",
            )
            self.assertEqual(
                jobs[job]["steps"][0]["with"]["ref"], "${{ matrix.release.sha }}"
            )
        self.assertEqual(merge_env["VERSION"], "${{ matrix.release.version }}")
        self.assertEqual(merge_env["ALIASES"], "${{ matrix.release.aliases }}")


if __name__ == "__main__":
    unittest.main()
