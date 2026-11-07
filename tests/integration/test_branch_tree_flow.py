from __future__ import annotations

import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from pkgmgr.actions.branch import gc, tree
from pkgmgr.actions.worktree import flow
from tests.integration.test_branch_gc import GcFixture


class TestBranchTreeFlow(GcFixture, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.shared = os.path.join(self.root, "shared-worktrees")
        os.makedirs(self.shared)
        self.metas = os.path.join(self.repo, ".git", "worktrees")
        for patcher in (
            patch.object(gc, "host_pid_namespace", return_value=True),
            patch.object(gc, "list_compose_containers", return_value=[]),
            patch.object(gc, "_process_cwds", return_value={}),
            patch.object(tree, "secret_service_token", return_value=(None, "locked")),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _entry(self) -> dict:
        out = io.StringIO()
        with redirect_stdout(out):
            code = tree.branch_tree(
                [self.repo], fmt="json", output=None, worktrees_root=self.shared
            )
        self.assertEqual(code, 0)
        return json.loads(out.getvalue())["repos"][0]

    def _flows(self, entry: dict) -> dict[str, dict | None]:
        return {
            item["branch"]: item["flow"] for item in entry["items"] if item["branch"]
        }

    def _flow_warnings(self, entry: dict) -> list[str]:
        return [w for w in entry["warnings"] if w.startswith("flow of ")]

    def test_items_carry_their_flow_or_null(self) -> None:
        flow.write_flow(
            os.path.join(self.metas, "wt-merged"), "merged", ["origin/main"], ["prod"]
        )
        flow.write_flow(os.path.join(self.repo, ".git"), "main", [], ["origin/main"])

        entry = self._entry()
        flows = self._flows(entry)
        self.assertEqual(
            flows["merged"],
            {"pull": ["origin/main"], "push": ["prod"], "source": "file"},
        )
        self.assertEqual(
            flows["main"], {"pull": [], "push": ["origin/main"], "source": "file"}
        )
        self.assertIsNone(flows["dirty"])
        self.assertIsNone(flows["wip"])
        self.assertTrue(all("flow" in item for item in entry["items"]))
        self.assertEqual(self._flow_warnings(entry), [])

    def test_invalid_and_mismatched_flows_warn_without_failing(self) -> None:
        folder = os.path.join(self.metas, "wt-dirty", flow.FLOW_DIR)
        os.makedirs(folder)
        with open(os.path.join(folder, flow.FLOW_FILE), "w", encoding="utf-8") as fh:
            fh.write("version: 1\npull: [a..b]\npush: []\n")
        flow.write_flow(os.path.join(self.metas, "wt-merged"), "gone", ["main"], [])

        entry = self._entry()
        flows = self._flows(entry)
        self.assertEqual(flows["dirty"], {"pull": [], "push": [], "source": "invalid"})
        self.assertEqual(flows["merged"]["source"], "file")
        warnings = self._flow_warnings(entry)
        self.assertEqual(len(warnings), 2)
        self.assertTrue(
            any(
                w.startswith(f"flow of {self.dirty_wt}: pkgmgr/flow.yml")
                for w in warnings
            )
        )
        self.assertIn(
            f"flow of {self.merged_wt}: flow was set on gone, the worktree is on merged",
            warnings,
        )

    def test_a_forged_registration_reads_no_flow(self) -> None:
        flow.write_flow(os.path.join(self.metas, "wt-merged"), "merged", ["main"], [])
        with open(os.path.join(self.metas, "wt-locked", "gitdir"), "w") as fh:
            fh.write(os.path.join(self.merged_wt, ".git") + "\n")

        items = {item["branch"]: item for item in self._entry()["items"]}

        for branch in ("merged", "locked"):
            with self.subTest(branch=branch):
                self.assertEqual(items[branch]["worktree"], self.merged_wt)
                self.assertIsNone(items[branch]["flow"])


if __name__ == "__main__":
    unittest.main()
