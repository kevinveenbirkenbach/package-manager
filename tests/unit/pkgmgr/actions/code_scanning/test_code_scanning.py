from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from pkgmgr.actions.code_scanning import (
    CodeScanningError,
    download_code_scanning,
)

_ALERTS = [
    {
        "number": 1,
        "state": "open",
        "html_url": "https://example/1",
        "rule": {
            "id": "py/sql-injection",
            "security_severity_level": "high",
            "severity": "error",
            "description": "SQL injection",
        },
        "most_recent_instance": {
            "location": {"path": "app.py", "start_line": 10},
            "message": {"text": "Possible SQL injection"},
        },
        "tool": {"name": "CodeQL"},
    }
]


def _cp(stdout: str = "", returncode: int = 0, stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)


def _fake_gh(args):
    if args[:2] == ["repo", "view"]:
        return _cp(stdout="owner/pkgmgr-cs-test\n")
    endpoint = args[1] if len(args) > 1 else ""
    if endpoint.endswith("code-scanning/alerts"):
        return _cp(stdout=json.dumps(_ALERTS))
    if endpoint.endswith("code-scanning/analyses"):
        return _cp(stdout=json.dumps([{"id": 42, "created_at": "2026-01-01"}]))
    return _cp(returncode=1, stderr=f"unexpected: {args}")


class TestDownloadCodeScanning(unittest.TestCase):
    def test_writes_alerts_summary_and_analyses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch(
                    "pkgmgr.actions.code_scanning.shutil.which",
                    return_value="/usr/bin/gh",
                ),
                mock.patch("pkgmgr.actions.code_scanning._gh", side_effect=_fake_gh),
            ):
                result = download_code_scanning(output_dir=tmp)

            self.assertEqual(result.repo, "owner/pkgmgr-cs-test")
            self.assertEqual(result.alert_count, 1)

            with open(os.path.join(tmp, "alerts.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f), _ALERTS)
            with open(os.path.join(tmp, "summary.md"), encoding="utf-8") as f:
                summary = f.read()
            self.assertIn("py/sql-injection", summary)
            self.assertIn("app.py:10", summary)
            self.assertIn("high", summary)
            self.assertTrue(os.path.exists(os.path.join(tmp, "analyses.json")))

    def test_default_output_dir_uses_repo_name(self) -> None:
        with (
            mock.patch(
                "pkgmgr.actions.code_scanning.shutil.which", return_value="/usr/bin/gh"
            ),
            mock.patch("pkgmgr.actions.code_scanning._gh", side_effect=_fake_gh),
        ):
            result = download_code_scanning()
        self.addCleanup(shutil.rmtree, "/tmp/pkgmgr-cs-test", ignore_errors=True)
        self.assertTrue(
            result.output_dir.startswith("/tmp/pkgmgr-cs-test/code-scanner/"),
            msg=result.output_dir,
        )

    def test_errors_when_gh_missing(self) -> None:
        with mock.patch("pkgmgr.actions.code_scanning.shutil.which", return_value=None):
            with self.assertRaises(CodeScanningError):
                download_code_scanning(output_dir="/tmp/should-not-be-created")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
