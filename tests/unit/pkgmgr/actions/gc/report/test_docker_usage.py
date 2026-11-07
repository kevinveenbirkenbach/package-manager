from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from pkgmgr.actions.gc.report import docker_usage as module

DF_OUTPUT = (
    '{"Active":"2","Reclaimable":"1.2GB (50%)","Size":"2.4GB",'
    '"TotalCount":"10","Type":"Images"}\n'
    '{"Active":"0","Reclaimable":"0B","Size":"0B","TotalCount":"0",'
    '"Type":"Build Cache"}\n'
)


class TestDockerUsage(unittest.TestCase):
    def test_rows_are_parsed_from_json_lines(self) -> None:
        with patch.object(module, "_docker", return_value=DF_OUTPUT) as docker:
            rows, warning = module.docker_usage()

        docker.assert_called_once_with(["system", "df", "--format", "{{json .}}"])
        self.assertIsNone(warning)
        self.assertEqual(
            rows[0],
            {
                "type": "Images",
                "total": 10,
                "active": 2,
                "size": "2.4GB",
                "reclaimable": "1.2GB (50%)",
            },
        )
        self.assertEqual(rows[1]["type"], "Build Cache")

    def test_missing_docker_is_a_warning(self) -> None:
        with patch.object(module, "_docker", side_effect=FileNotFoundError):
            rows, warning = module.docker_usage()

        self.assertIsNone(rows)
        self.assertIn("not installed", warning)

    def test_failing_docker_is_a_warning(self) -> None:
        error = subprocess.CalledProcessError(
            1, ["docker", "system", "df"], stderr="daemon down"
        )
        with patch.object(module, "_docker", side_effect=error):
            rows, warning = module.docker_usage()

        self.assertIsNone(rows)
        self.assertIn("daemon down", warning)

    def test_unparsable_output_is_a_warning(self) -> None:
        with patch.object(module, "_docker", return_value="TYPE TOTAL\n[1]\n"):
            rows, warning = module.docker_usage()

        self.assertIsNone(rows)
        self.assertIn("not JSON lines", warning)


if __name__ == "__main__":
    unittest.main()
