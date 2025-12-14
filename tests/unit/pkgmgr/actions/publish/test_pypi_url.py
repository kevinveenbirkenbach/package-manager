
import unittest
from pkgmgr.actions.publish.pypi_url import parse_pypi_project_url


class TestParsePyPIUrl(unittest.TestCase):
    def test_valid_pypi_url(self):
        t = parse_pypi_project_url("https://pypi.org/project/example/")
        self.assertIsNotNone(t)
        self.assertEqual(t.project, "example")

    def test_invalid_url(self):
        self.assertIsNone(parse_pypi_project_url("https://example.com/foo"))
