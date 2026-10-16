"""Unit tests for cone-compare.py: which findings count as a cone disagreement."""
# frob:ticket 01M51CKH84ZBS7G3SP7XM0FM1F
import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location(
    "cone_compare", pathlib.Path(__file__).with_name("cone-compare.py")
)
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)


def f(fp, sev="error"):
    """A minimal finding."""
    return {"fingerprint": fp, "severity": sev, "rule": "R", "file": "a", "line": 1, "message": "m"}


class MissedTests(unittest.TestCase):
    """Disagreement is a new failing finding the scoped check lacks."""

    def test_agreement_when_cone_reports_the_new_finding(self):
        self.assertEqual(cc.missed([f("a")], [], [f("a")]), [])

    def test_disagreement_when_cone_misses_it(self):
        self.assertEqual([x["fingerprint"] for x in cc.missed([f("a")], [], [])], ["a"])

    def test_preexisting_findings_are_not_the_lands(self):
        self.assertEqual(cc.missed([f("a")], [f("a")], []), [])

    def test_below_fail_on_is_ignored(self):
        self.assertEqual(cc.missed([f("a", "advisory")], [], []), [])


if __name__ == "__main__":
    unittest.main()
