"""Unit tests for cone-compare.py: which findings count as a cone disagreement."""
# frob:ticket 01M51CKH84ZBS7G3SP7XM0FM1F
import importlib.util
import pathlib
import tempfile
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


class ShellHelperTests(unittest.TestCase):
    """The subprocess helpers: sh, findings and lands."""

    def test_sh_returns_stdout_and_ignores_status(self):
        # frob:tests .github/scripts/cone-compare.py::sh
        self.assertEqual(cc.sh("sh", "-c", "echo hi; exit 3"), "hi\n")

    def test_findings_reads_the_envelope_line(self):
        # frob:tests .github/scripts/cone-compare.py::findings
        env = '{"verb":"check","data":{"findings":[{"fingerprint":"z"}]}}'
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp, "frob")
            fake.write_text("#!/bin/sh\necho noise\necho '" + env + "'\n")
            fake.chmod(0o755)
            got = cc.findings(str(fake), tmp)
        self.assertEqual(got, [{"fingerprint": "z"}])

    def test_findings_none_without_envelope(self):
        # frob:tests .github/scripts/cone-compare.py::findings
        self.assertIsNone(cc.findings("true", "."))

    def test_lands_keeps_newest_first_parent_lands_oldest_first(self):
        # frob:tests .github/scripts/cone-compare.py::lands
        log = "c3 tickets(land): ~AAA\nc2 chore: x\nc1 tickets(land): ~BBB\n"
        original = cc.sh
        cc.sh = lambda *a, **k: log
        try:
            got = cc.lands(5)
        finally:
            cc.sh = original
        self.assertEqual(got, [("c1", "~BBB"), ("c3", "~AAA")])

    def test_main_reports_zero_for_an_empty_window(self):
        # frob:tests .github/scripts/cone-compare.py::main
        original = cc.lands
        cc.lands = lambda count: []
        try:
            self.assertEqual(cc.main(["x", "frob", "1"]), 0)
        finally:
            cc.lands = original

    def test_main_fails_when_the_cone_missed_a_finding(self):
        # frob:tests .github/scripts/cone-compare.py::main
        saved = (cc.lands, cc.sh, cc.findings)
        cc.lands = lambda count: [("p", "~A"), ("s", "~B")]
        cc.sh = lambda *a, **k: ""
        calls = {"n": 0}

        def fake(frob, cwd, *extra):
            calls["n"] += 1
            if extra:
                return []
            return [f("new")] if calls["n"] == 2 else []

        cc.findings = fake
        try:
            self.assertEqual(cc.main(["x", "frob", "1"]), 1)
        finally:
            cc.lands, cc.sh, cc.findings = saved


if __name__ == "__main__":
    unittest.main()
