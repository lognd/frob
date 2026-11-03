"""Tests for render.py: the PyPI product list, version conversion and template fill."""
# frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5
import io
import contextlib
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render  # noqa: E402


class RenderTests(unittest.TestCase):
    """Pure helpers of render.py."""

    def test_products_lists_frob_first(self):
        # frob:tests packaging/pypi/render.py::products
        names = [p["name"] for p in render.products()]
        self.assertEqual(names[0], "frob")
        self.assertIn("grimble", names)

    def test_pep440_maps_prerelease_tags(self):
        # frob:tests packaging/pypi/render.py::pep440
        self.assertEqual(render.pep440("1.2.3"), "1.2.3")
        self.assertEqual(render.pep440("1.2.3-alpha.4"), "1.2.3a4")
        self.assertEqual(render.pep440("1.2.3-rc1"), "1.2.3rc1")
        with self.assertRaises(SystemExit):
            render.pep440("not-a-version")

    def test_fill_replaces_and_rejects_leftovers(self):
        # frob:tests packaging/pypi/render.py::fill
        self.assertEqual(render.fill("a @X@ b", {"X": "1"}), "a 1 b")
        with self.assertRaises(SystemExit):
            render.fill("@X@ @Y@", {"X": "1"})

    def test_lockstep_version_is_pep440_of_the_frob_cli_package(self):
        # frob:tests packaging/pypi/render.py::lockstep_version
        original = render.subprocess.run

        class Done:
            stdout = '{"packages":[{"name":"x","version":"9.9.9"},{"name":"frob-cli","version":"0.5.0-beta.2"}]}'

        render.subprocess.run = lambda *a, **k: Done()
        try:
            self.assertEqual(render.lockstep_version(), "0.5.0b2")
        finally:
            render.subprocess.run = original

    def test_main_lists_products_and_rejects_bad_usage(self):
        # frob:tests packaging/pypi/render.py::main
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(render.main(["list"]), 0)
        self.assertIn("frob", out.getvalue().split())
        self.assertEqual(render.main(["bogus"]), 2)


if __name__ == "__main__":
    unittest.main()
