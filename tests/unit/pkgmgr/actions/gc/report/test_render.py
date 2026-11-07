from __future__ import annotations

import unittest

from pkgmgr.actions.gc.report.render import render_text

NOW = 1_000_000.0


def report(**overrides: object) -> dict:
    base = {
        "generated_at": NOW,
        "threshold_bytes": 1 << 20,
        "worktrees": [
            {
                "path": "/r/.worktrees/x",
                "branch": None,
                "orphaned": False,
                "missing": False,
                "size_bytes": 3 << 30,
                "last_activity": NOW - 2 * 86400,
                "foreign_entries": 4,
            },
            {
                "path": "/r/.claude/worktrees/agent-1",
                "branch": None,
                "orphaned": True,
                "missing": False,
                "size_bytes": 5 << 20,
                "last_activity": NOW - 90,
                "foreign_entries": 0,
            },
        ],
        "preserved": [
            {
                "path": "/r/.worktrees/x",
                "branch": None,
                "paths": 2,
                "preserved": False,
                "reasons": [
                    "detached HEAD reachable from no ref",
                    "a: content in no ref",
                ],
            }
        ],
        "roots": [
            {
                "root": "/tmp",
                "children": [
                    {
                        "path": "/tmp/core",
                        "kind": "core-dump",
                        "size_bytes": 2 << 20,
                        "newest_mtime": NOW - 3 * 3600,
                    }
                ],
            }
        ],
        "core_dumps": [
            {
                "path": "/tmp/core",
                "size_bytes": 2 << 20,
                "apparent_bytes": 1 << 30,
                "mtime": NOW - 3 * 3600,
            }
        ],
        "docker": None,
        "balance": [
            {
                "filesystem": "/",
                "total_bytes": 100 << 30,
                "free_bytes": 10 << 30,
                "attributed_bytes": 3 << 30,
            }
        ],
        "warnings": ["docker unavailable: not installed"],
    }
    return {**base, **overrides}


class TestRenderText(unittest.TestCase):
    def test_sections_and_rows(self) -> None:
        lines = render_text(report()).splitlines()

        self.assertIn("== worktrees", lines)
        worktree = next(line for line in lines if line.endswith("/r/.worktrees/x"))
        self.assertEqual(
            worktree.split(),
            ["3.0G", "2.0d", "4", "linked", "(detached)", "/r/.worktrees/x"],
        )
        orphan = next(line for line in lines if "agent-1" in line)
        self.assertEqual(orphan.split()[1:5], ["1.5m", "0", "orphaned", "-"])
        verdict = next(line for line in lines if line.startswith("no "))
        self.assertIn(
            "detached HEAD reachable from no ref; a: content in no ref", verdict
        )
        self.assertIn("== root /tmp (over 1.0M)", lines)
        rows = [line.split() for line in lines]
        self.assertIn(["2.0M", "1.0G", "3.0h", "/tmp/core"], rows)
        self.assertIn(["/", "100.0G", "10.0G", "3.0G"], rows)
        self.assertEqual(lines[-1], "WARN  docker unavailable: not installed")
        self.assertNotIn("== docker", lines)

    def test_docker_rows_and_empty_sections(self) -> None:
        docker = [
            {
                "type": "Images",
                "total": 3,
                "active": 1,
                "size": "1GB",
                "reclaimable": "0B",
            }
        ]

        text = render_text(report(docker=docker, core_dumps=[], warnings=[]))

        self.assertIn("== core dumps\n(none)", text)
        self.assertIn("== docker", text)
        self.assertIn("Images  3      1       1GB   0B", text)


if __name__ == "__main__":
    unittest.main()
