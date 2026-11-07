"""Tests for the shell helpers in CI and smoke scripts, run through a real shell."""
# frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / ".github" / "scripts" / "ensure-ledger-refs.sh"
LOOP = ROOT / "packaging" / "smoke" / "fixture-loop.sh"


def run(args, cwd=None, env=None):
    """Run a command, returning the completed process."""
    # frob:accept LOG001 because="false positive: output is captured for assertions, never inherited by the std streams"
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False, env=env)


def git(cwd, *args):
    """Run git in cwd, failing the test when it fails."""
    out = run(["git", *args], cwd=cwd)
    assert out.returncode == 0, out.stderr
    return out.stdout


def function(script, name):
    """The source of shell function `name` (one-line or multi-line definition) from script."""
    text = script.read_text()
    m = re.search(rf"^{name}\(\) \{{[^\n]*\}}$", text, re.M) or re.search(rf"^{name}\(\) \{{\n.*?^\}}", text, re.S | re.M)
    assert m, name
    return m.group(0)


class LedgerRefsTests(unittest.TestCase):
    """ensure-ledger-refs.sh against a real origin and a detached checkout."""

    def test_tickets_value_reads_the_tickets_table_or_the_default(self):
        # frob:tests .github/scripts/ensure-ledger-refs.sh::tickets_value
        with tempfile.TemporaryDirectory() as tmp:
            toml = pathlib.Path(tmp, "frob.toml")
            toml.write_text('[other]\nref = "no"\n[tickets]\nref = "refs/heads/dev"\n')
            body = function(LEDGER, "tickets_value")
            script = f'toml="{toml}"\n{body}\ntickets_value ref X\ntickets_value branch fallback\n'
            out = run(["bash", "-c", script]).stdout.split()
            self.assertEqual(out, ["refs/heads/dev", "fallback"])

    def test_ensure_local_creates_the_branch_from_origin(self):
        # frob:tests .github/scripts/ensure-ledger-refs.sh::ensure_local
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            origin, work = tmp / "origin", tmp / "work"
            git(tmp, "init", "-q", "-b", "dev", str(origin))
            git(origin, "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-q", "--allow-empty", "-m", "x")
            git(tmp, "clone", "-q", str(origin), str(work))
            git(work, "checkout", "-q", "--detach")
            git(work, "branch", "-D", "dev")
            (work / "frob.toml").write_text('[tickets]\nref = "refs/heads/dev"\n')
            out = run(["bash", str(LEDGER)], cwd=work)
            self.assertEqual(out.returncode, 0, out.stderr)
            git(work, "rev-parse", "--verify", "refs/heads/dev")
            self.assertIn("created local dev", out.stderr)


class FixtureLoopTests(unittest.TestCase):
    """fixture-loop.sh helper functions."""

    def sh(self, body, stdin=""):
        """Run the named helper definitions plus `body` under sh."""
        defs = "\n".join(function(LOOP, n) for n in ("log", "die", "fj", "pick", "has"))
        return subprocess.run(["sh", "-c", defs + "\n" + body], input=stdin, capture_output=True, text=True, check=False)

    def test_die_prints_and_exits_nonzero(self):
        # frob:tests packaging/smoke/fixture-loop.sh::die
        out = self.sh("die boom")
        self.assertEqual(out.returncode, 1)
        self.assertIn("FAIL: boom", out.stderr)

    def test_pick_extracts_a_string_value(self):
        # frob:tests packaging/smoke/fixture-loop.sh::pick
        out = self.sh("pick id", stdin='{"ok":true,"id":"T1"}\n')
        self.assertEqual(out.stdout.strip(), "T1")

    def test_has_passes_on_a_substring_and_dies_otherwise(self):
        # frob:tests packaging/smoke/fixture-loop.sh::has
        self.assertEqual(self.sh('has "abc" b why').returncode, 0)
        out = self.sh('has "abc" z why')
        self.assertEqual(out.returncode, 1)
        self.assertIn("why: missing z", out.stderr)

    def test_fj_requires_an_ok_envelope(self):
        # frob:tests packaging/smoke/fixture-loop.sh::fj
        good = self.sh('frob() { echo \'{"ok":true}\'; }\nfj check')
        self.assertEqual(good.returncode, 0, good.stderr)
        envelope = self.sh('frob() { echo \'{"ok":true}\'; }\nfj check\ncase "$out" in *\'"ok":true\'*) exit 7 ;; esac')
        self.assertEqual(envelope.returncode, 7)
        bad = self.sh('frob() { echo \'{"ok":false}\'; }\nfj check')
        self.assertEqual(bad.returncode, 1)


if __name__ == "__main__":
    unittest.main()
