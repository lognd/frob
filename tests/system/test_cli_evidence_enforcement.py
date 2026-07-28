"""End-to-end dogfood test for T-0398's evidence-integrity enforcement --
drives the REAL `frob ticket close` CLI subprocess (not the library
function directly), proving the fix is actually wired into the command an
operator/agent runs, not just a capable-but-unreached library.

Each FAIL case here is a literal reproduction of one of docs/audits/
tickets-testing.md's D-01/D-02/D-03 repros, run through the real CLI:
- D-01: "record evidence on a RED test ... frob ticket close -> DONE" must
  now be Err, not DONE.
- D-02: "frob ticket evidence T-feature-x tests/test_logging.py::test_x
  (unrelated test) -> closes" must now be Err, not DONE.
- D-03: "append a bare '## Done report' line -> close precondition met"
  must now be Err, not DONE.
And the discharging PASS case: a genuinely covering, passing test with a
substantive Done report must still close cleanly (the false-positive
guard this whole dispatch round exists to prove is not broken).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.system.conftest import run


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "tickets.md").write_text("# Tickets\n\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "init", cwd=root)


def _new_in_progress_ticket(
    root: Path, *, scope: str, body: str = "## Description\nx\n"
) -> str:
    """Create + plan + start a ticket, returning its id (always T-0001,
    the first allocated in a fresh repo)."""
    created = run(
        "ticket",
        "new",
        "--title",
        "dogfood",
        "--kind",
        "feature",
        "--scope",
        scope,
        "--body",
        body,
        "--path",
        str(root),
    )
    assert created.returncode == 0, created.stdout + created.stderr
    run("ticket", "plan", "T-0001", "--path", str(root))
    started = run("ticket", "start", "T-0001", "--path", str(root))
    assert started.returncode == 0, started.stdout + started.stderr
    return "T-0001"


class TestCliEvidenceEnforcementEndToEnd:
    """T-0398: `frob ticket close`, the real CLI subprocess, must enforce
    D-01 (pass), D-02 (scope-binding), D-03 (substantive Done report)."""

    # frob:tests \
    # tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd\
    # .test_close_fails_on_red_evidence
    def test_close_fails_on_red_evidence(self, tmp_path: Path) -> None:
        """D-01: a RED (failing) evidence test must FAIL `frob ticket
        close`, not silently satisfy it."""
        root = tmp_path
        _init_repo(root)
        (root / "tests").mkdir()
        (root / "tests" / "test_red.py").write_text(
            "def test_it():\n    assert False, 'deliberately red'\n"
        )
        _git("add", "-A", cwd=root)
        _git("commit", "-q", "-m", "add red test", cwd=root)

        _new_in_progress_ticket(
            root,
            scope="tests/test_red.py",
            body="## Description\nx\n\n## Done report\nAll good.\n",
        )

        result = run(
            "ticket",
            "close",
            "T-0001",
            "--evidence",
            "tests/test_red.py::test_it",
            "--path",
            str(root),
        )
        out = result.stdout + result.stderr
        assert result.returncode != 0, out
        assert "EvidenceNotPassing" in out, out

        show = run("ticket", "show", "T-0001", "--path", str(root))
        assert "[in-progress]" in (show.stdout + show.stderr)

    # frob:tests \
    # tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd\
    # .test_close_fails_on_unrelated_evidence
    def test_close_fails_on_unrelated_evidence(self, tmp_path: Path) -> None:
        """D-02: a PASSING but UNRELATED (non-scope-covering) evidence
        test must FAIL `frob ticket close`, not silently satisfy it."""
        root = tmp_path
        _init_repo(root)
        (root / "tests").mkdir()
        (root / "src_a").mkdir()
        (root / "src_b").mkdir()
        (root / "tests" / "test_unrelated.py").write_text(
            "def test_it():\n    assert True\n"
        )
        (root / "src_a" / "feature.py").write_text(
            "def feature() -> int:\n    return 1\n"
        )
        _git("add", "-A", cwd=root)
        _git("commit", "-q", "-m", "add unrelated test + scoped source", cwd=root)

        _new_in_progress_ticket(
            root,
            # Ticket is scoped to src_a/, NOT tests/test_unrelated.py --
            # the evidence below covers neither by graph edge nor by
            # direct scope membership.
            scope="src_a/",
            body="## Description\nx\n\n## Done report\nAll good.\n",
        )

        result = run(
            "ticket",
            "close",
            "T-0001",
            "--evidence",
            "tests/test_unrelated.py::test_it",
            "--path",
            str(root),
        )
        out = result.stdout + result.stderr
        assert result.returncode != 0, out
        assert "EvidenceScopeUnbound" in out, out

        show = run("ticket", "show", "T-0001", "--path", str(root))
        assert "[in-progress]" in (show.stdout + show.stderr)

    # frob:tests \
    # tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd\
    # .test_close_fails_on_empty_done_report
    def test_close_fails_on_empty_done_report(self, tmp_path: Path) -> None:
        """D-03: a bare '## Done report' heading with nothing under it
        must FAIL `frob ticket close`, not silently satisfy it."""
        root = tmp_path
        _init_repo(root)
        (root / "tests").mkdir()
        (root / "tests" / "test_green.py").write_text(
            "def test_it():\n    assert True\n"
        )
        _git("add", "-A", cwd=root)
        _git("commit", "-q", "-m", "add green test", cwd=root)

        _new_in_progress_ticket(
            root,
            scope="tests/test_green.py",
            # Bare heading, no content under it -- D-03's exact repro.
            body="## Description\nx\n\n## Done report\n",
        )

        result = run(
            "ticket",
            "close",
            "T-0001",
            "--evidence",
            "tests/test_green.py::test_it",
            "--path",
            str(root),
        )
        out = result.stdout + result.stderr
        assert result.returncode != 0, out
        assert "MissingEvidence" in out, out

        show = run("ticket", "show", "T-0001", "--path", str(root))
        assert "[in-progress]" in (show.stdout + show.stderr)

    # frob:tests \
    # tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd\
    # .test_close_succeeds_with_covering_passing_evidence_and_substantive_report
    def test_close_succeeds_with_covering_passing_evidence_and_substantive_report(
        self, tmp_path: Path
    ) -> None:
        """The discharging PASS case: a genuinely covering (in-scope),
        actually-passing test plus a substantive Done report must still
        close CLEANLY through the real, now-strict CLI -- proving the
        enforcement does not false-positive on honest, well-reported
        work."""
        root = tmp_path
        _init_repo(root)
        (root / "tests").mkdir()
        (root / "src_c").mkdir()
        (root / "tests" / "test_covering.py").write_text(
            "def test_it():\n    assert True\n"
        )
        (root / "src_c" / "thing.py").write_text("def thing() -> int:\n    return 1\n")
        _git("add", "-A", cwd=root)
        _git("commit", "-q", "-m", "add covering test + source", cwd=root)

        _new_in_progress_ticket(
            root,
            # Both the source AND its own covering test are in scope --
            # evidence_covers_scope's direct-file-in-scope route (T-0398).
            scope="src_c/,tests/test_covering.py",
            body="## Description\nx\n\n## Done report\nImplemented thing(); "
            "verified via test_covering.\n",
        )

        result = run(
            "ticket",
            "close",
            "T-0001",
            "--evidence",
            "tests/test_covering.py::test_it",
            "--path",
            str(root),
        )
        out = result.stdout + result.stderr
        assert result.returncode == 0, out

        show = run("ticket", "show", "T-0001", "--path", str(root))
        assert "[done]" in (show.stdout + show.stderr)

    # frob:tests \
    # tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd\
    # .test_docs_kind_cmd_evidence_path_still_works
    def test_docs_kind_cmd_evidence_path_still_works(self, tmp_path: Path) -> None:
        """False-positive guard: a docs-kind ticket closed purely via
        `--evidence-cmd` (no pytest node ids at all) must still close --
        D-02's scope-binding check must not misfire on the cmd-evidence
        channel, which the dispatch explicitly warned not to break."""
        root = tmp_path
        _init_repo(root)

        created = run(
            "ticket",
            "new",
            "--title",
            "docs dogfood",
            "--kind",
            "docs",
            "--body",
            "## Description\nx\n\n## Done report\nDocs updated.\n",
            "--path",
            str(root),
        )
        assert created.returncode == 0, created.stdout + created.stderr
        run("ticket", "plan", "T-0001", "--path", str(root))
        started = run("ticket", "start", "T-0001", "--path", str(root))
        assert started.returncode == 0, started.stdout + started.stderr

        result = run(
            "ticket",
            "close",
            "T-0001",
            "--evidence-cmd",
            "true",
            "--path",
            str(root),
        )
        out = result.stdout + result.stderr
        assert result.returncode == 0, out

        show = run("ticket", "show", "T-0001", "--path", str(root))
        assert "[done]" in (show.stdout + show.stderr)
