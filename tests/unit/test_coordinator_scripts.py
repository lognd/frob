"""Unit tests for the reusable coordinator scripts under `scripts/` (T-1863).

Every public function in `scripts/check_summary.py`, `scripts/fleet_status.py`,
and `scripts/verify_lands.py` is ordinary importable Python -- `git`/`frob`
subprocess calls are monkeypatched here, and the pure parsing/traversal
logic runs against small fixture data with no subprocess at all. This is
the real-tests half of T-1863's TEST001 obligation (the `.claude/hooks/`
path-class exemption's rationale -- harness-only invocation, no meaningful
way to unit test outside it -- does not transfer to this shape).
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.unit.conftest import _load_script as _load

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO_ROOT / "scripts"

check_summary = _load("check_summary")
fleet_status = _load("fleet_status")
verify_lands = _load("verify_lands")


def _report(*, results: list[dict[str, Any]]) -> dict[str, Any]:
    """A minimal `frob check --json`-shaped report for the given results."""
    return {"results": results}


def _diag(severity: str, code: str = "X001", file: str = "a.py", line: int = 1) -> dict:
    """A minimal diagnostic dict, severity nested exactly as frob emits it."""
    return {"severity": severity, "code": code, "file": file, "line": line, "message": "m"}


class TestLoadReport:
    """`check_summary.load_report`."""

    def test_reads_path(self, tmp_path: Path) -> None:
        """A path argument is read and parsed as JSON."""
        report = _report(results=[])
        path = tmp_path / "out.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        assert check_summary.load_report(str(path)) == report

    def test_reads_stdin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`None` (or '-') reads and parses JSON from stdin."""
        report = _report(results=[])
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(report)))
        assert check_summary.load_report(None) == report


class TestIterDiagnostics:
    """`check_summary.iter_diagnostics`."""

    def test_yields_tool_and_diagnostic(self) -> None:
        """Each diagnostic under a tool record's `diagnostics` list is yielded
        paired with that record's `tool` name."""
        report = _report(
            results=[
                {"tool": "ruff", "diagnostics": [_diag("warning"), _diag("error")]},
                {"tool": "ty", "diagnostics": [_diag("error")]},
            ]
        )
        pairs = list(check_summary.iter_diagnostics(report))
        assert [tool for tool, _ in pairs] == ["ruff", "ruff", "ty"]
        assert len(pairs) == 3

    def test_empty_results(self) -> None:
        """No `results` key yields nothing, rather than raising."""
        assert list(check_summary.iter_diagnostics({})) == []


class TestSummarise:
    """`check_summary.summarise`."""

    def test_counts_by_severity(self) -> None:
        """Severity counts tally every diagnostic across every tool record."""
        report = _report(
            results=[
                {"tool": "ruff", "diagnostics": [_diag("warning"), _diag("note")]},
                {"tool": "ty", "diagnostics": [_diag("error")]},
            ]
        )
        severities, _ = check_summary.summarise(report)
        assert severities == {"warning": 1, "note": 1, "error": 1}

    def test_collects_error_rows(self) -> None:
        """Only `severity == "error"` diagnostics become error rows, in order."""
        report = _report(
            results=[
                {
                    "tool": "ty",
                    "diagnostics": [
                        _diag("error", code="E1", file="a.py", line=3),
                        _diag("warning", code="W1"),
                        _diag("error", code="E2", file="b.py", line=9),
                    ],
                }
            ]
        )
        _, errors = check_summary.summarise(report)
        assert [row[1] for row in errors] == ["E1", "E2"]
        assert errors[0][2:4] == ("a.py", 3)


class TestCheckSummaryMain:
    """`check_summary.main`."""

    def test_exit_zero_when_clean(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """No error-severity diagnostics anywhere exits 0."""
        report = _report(results=[{"tool": "ruff", "diagnostics": [_diag("warning")]}])
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(report)))
        monkeypatch.setattr(sys, "argv", ["check_summary.py"])
        assert check_summary.main() == 0
        out = capsys.readouterr().out
        assert "ERRORS   0" in out

    def test_exit_one_when_errors(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """At least one error-severity diagnostic exits 1 and is printed."""
        report = _report(results=[{"tool": "ty", "diagnostics": [_diag("error", code="E1")]}])
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(report)))
        monkeypatch.setattr(sys, "argv", ["check_summary.py"])
        assert check_summary.main() == 1
        out = capsys.readouterr().out
        assert "ERRORS   1" in out
        assert "E1" in out


def _completed(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    """A `subprocess.CompletedProcess` stub for monkeypatching `subprocess.run`."""
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


class TestRootDirt:
    """`fleet_status.root_dirt`."""

    def test_clean_repo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty porcelain output means no dirt lines."""
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(""))
        assert fleet_status.root_dirt() == []

    def test_dirty_repo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-empty porcelain lines are returned verbatim, blank lines dropped."""
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **k: _completed(" M foo.py\n ?? bar.py\n")
        )
        assert fleet_status.root_dirt() == ["M foo.py", " ?? bar.py"]


class TestLeases:
    """`fleet_status.leases`."""

    def test_reads_lease_records(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Every `*.json` lease file under LEASES is parsed as a record."""
        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        (leases_dir / "T-0001.json").write_text(
            json.dumps({"ticket_id": "T-0001", "worktree": "/x"}), encoding="utf-8"
        )
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)
        assert fleet_status.leases() == [{"ticket_id": "T-0001", "worktree": "/x"}]

    def test_no_lease_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A missing leases directory returns an empty list, not an error."""
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "does-not-exist")
        assert fleet_status.leases() == []

    def test_unreadable_lease_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Malformed JSON is reported with an '<unreadable>' worktree, not raised."""
        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        (leases_dir / "T-0002.json").write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)
        records = fleet_status.leases()
        assert records == [{"ticket_id": "T-0002", "worktree": "<unreadable>"}]


class TestWorktrees:
    """`fleet_status.worktrees`."""

    def test_reports_idle_age(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A worktree whose last commit is older than idle_seconds is flagged idle."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)
        monkeypatch.setattr(fleet_status.time, "time", lambda: 1_000_000.0)
        monkeypatch.setattr(
            fleet_status, "_git", lambda args, cwd: str(int(1_000_000.0) - 9999)
        )
        rows = fleet_status.worktrees(idle_seconds=100)
        assert rows == [("one", 9999, True)]

    def test_no_worktree_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A missing worktrees directory returns an empty list, not an error."""
        monkeypatch.setattr(fleet_status, "WORKTREES", tmp_path / "does-not-exist")
        assert fleet_status.worktrees(idle_seconds=100) == []


class TestTicketLease:
    """`fleet_status.ticket_lease` (T-2133)."""

    def test_reads_a_live_lease(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The single `<id>.json` lease file is read and parsed directly."""
        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        record = {
            "ticket_id": "T-2114",
            "scope": ["src/x.py"],
            "worktree": "/w",
            "branch": "b",
            "recorded_at": "2026-08-01T00:00:00+00:00",
        }
        (leases_dir / "T-2114.json").write_text(json.dumps(record), encoding="utf-8")
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)
        assert fleet_status.ticket_lease("T-2114") == record

    def test_no_lease_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No lease file for this specific id returns None, not an error."""
        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)
        assert fleet_status.ticket_lease("T-9999") is None

    def test_unreadable_lease_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Malformed JSON reads as '<unreadable>', mirroring `leases()`."""
        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        (leases_dir / "T-2114.json").write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)
        assert fleet_status.ticket_lease("T-2114") == {
            "ticket_id": "T-2114",
            "worktree": "<unreadable>",
        }


class TestTicketFrontmatterOnMain:
    """`fleet_status.ticket_frontmatter_on_main` (T-2133)."""

    def test_reads_state_and_scope(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`state:` and the `scope:` list block are parsed from the
        committed ticket.md's YAML frontmatter."""
        text = (
            "---\n"
            "id: T-2114\n"
            "state: in-progress\n"
            "scope:\n"
            "- src/a.py\n"
            "- 'src/b.py'\n"
            "priority: high\n"
        )
        monkeypatch.setattr(fleet_status, "_git", lambda args, cwd: text)
        assert fleet_status.ticket_frontmatter_on_main("T-2114") == {
            "state": "in-progress",
            "scope": ["src/a.py", "src/b.py"],
            "blocked_by": [],
        }

    # frob:ticket T-2196
    # frob:tests \
    # tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain.test_reads_bl\
    # ocked_by
    def test_reads_blocked_by(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The `blocked_by:` list block parses the same way `scope:` does."""
        text = (
            "---\n"
            "id: T-2114\n"
            "state: queued\n"
            "blocked_by:\n"
            "- T-0001\n"
            "- 'T-0002'\n"
            "scope:\n"
            "- src/a.py\n"
            "priority: high\n"
        )
        monkeypatch.setattr(fleet_status, "_git", lambda args, cwd: text)
        assert fleet_status.ticket_frontmatter_on_main("T-2114") == {
            "state": "queued",
            "scope": ["src/a.py"],
            "blocked_by": ["T-0001", "T-0002"],
        }

    def test_missing_ticket_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`git show` returning nothing (ticket absent on main) is None."""
        monkeypatch.setattr(fleet_status, "_git", lambda args, cwd: "")
        assert fleet_status.ticket_frontmatter_on_main("T-9999") is None


# frob:ticket T-2179
class TestWorktreesTouchingTicket:
    """`fleet_status.worktrees_touching_ticket` (T-2133, scope-aware per
    T-draft-05563e8d)."""

    # frob:ticket T-2179
    def test_finds_a_branch_with_unlanded_commits(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A worktree whose branch has a `main..HEAD` commit that -- in
        that SAME commit's own diff -- touches BOTH `tickets/<id>/` and a
        declared-scope file is reported by name (T-2181: correlation is
        per commit, not per whole branch)."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        (worktrees_dir / "two").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        def fake_git(args: list[str], cwd: Path) -> str:
            if cwd.name != "one":
                return ""
            if args[0] == "log":
                return "abc123"
            return "src/a.py\ntickets/T-2114/ticket.md"

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status.worktrees_touching_ticket(
            "T-2114", ["src/a.py"]
        ) == ["one"]

    # frob:ticket T-2179
    def test_empty_when_nothing_touches_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No worktree with matching commits returns an empty list."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)
        monkeypatch.setattr(fleet_status, "_git", lambda args, cwd: "")
        assert fleet_status.worktrees_touching_ticket("T-2114", ["src/a.py"]) == []

    # frob:ticket T-2179
    def test_ledger_only_churn_is_not_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2172 follow-up (the coordinator's own T-2114 incident): a
        branch that touched `tickets/<id>/` (e.g. id-collision-recovery
        renumbering) but NEVER touched a file in the ticket's own declared
        scope must NOT be reported as 'already implemented' -- the exact
        false-positive shape that printed seven unrelated branches for a
        ticket nobody had actually worked."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        def fake_git(args: list[str], cwd: Path) -> str:
            if args[0] == "log":
                return "abc123"
            # that commit's own diff touches ONLY the ticket's own ledger
            # path, never the declared scope glob below
            return "tickets/T-2114/ticket.md"

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert (
            fleet_status.worktrees_touching_ticket(
                "T-2114", ["src/frob/app/ticket_runner/_land_cmd.py"]
            )
            == []
        )

    # frob:ticket T-2179
    def test_empty_scope_globs_never_reports(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No known scope to check against (empty `scope_globs`) must read
        as 'cannot confirm implementation', never fall back to the old
        looser any-ticket-dir-commit behavior."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)
        monkeypatch.setattr(fleet_status, "_git", lambda args, cwd: "abc123")
        assert fleet_status.worktrees_touching_ticket("T-2114", []) == []

    # frob:ticket T-2181
    def test_scope_touch_in_a_different_commit_is_not_correlated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2181 (T-2179 residue): a branch can have ONE commit that
        touches `tickets/<id>/` (pure ledger bookkeeping -- e.g. a
        `blocked_by` edit made while working a DIFFERENT ticket) and a
        SEPARATE, unrelated commit that touches a file matching this
        ticket's own scope globs (real work done for that OTHER ticket,
        which happens to share a scope-glob file). Measured for real:
        `--ticket T-2114` reported `t-2107` and `t2049-series`, neither of
        which had implemented T-2114 -- each had one commit touching
        `tickets/T-2114/` and a wholly separate commit touching
        `_land_cmd.py` for its own ticket (T-2108, T-2049). Correlating at
        the WHOLE-BRANCH level (the pre-fix behavior) reported the branch
        anyway, because it only asked "does any commit touch the ticket
        dir" and "does the whole diff touch scope" as two independent
        questions. Fixed behavior: correlation happens PER COMMIT (`git
        show --name-only` on each commit that itself touches
        `tickets/<id>/`), so the branch's OTHER commit -- which touches
        the scope file but never `tickets/T-2114/` -- is never seen by
        this function at all."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        def fake_git(args: list[str], cwd: Path) -> str:
            if args[0] == "log":
                # one commit touches only the ticket dir (bookkeeping)
                return "aaa111"
            if args[0] == "show":
                sha = args[-1]
                if sha == "aaa111":
                    return "tickets/T-2114/ticket.md"
                return ""
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert (
            fleet_status.worktrees_touching_ticket(
                "T-2114", ["src/frob/app/ticket_runner/_land_cmd.py"]
            )
            == []
        )


class TestScopeIntersections:
    """`fleet_status.scope_intersections` (T-2180)."""

    def test_reports_overlapping_pair(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Two tickets whose effective scope shares a glob are reported as
        a colliding pair, with the overlapping glob(s) named -- the
        T-1748/T-1780 shape (a five-ticket docs series all scoped to the
        same file, then a sixth ticket claiming it again with no
        override)."""
        monkeypatch.setattr(
            fleet_status,
            "ticket_readiness",
            lambda tid: {
                "ticket_id": tid,
                "lease": None,
                "main": {
                    "state": "queued",
                    "scope": ["docs/modules/tickets.md"],
                },
            },
        )
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        collisions = fleet_status.scope_intersections(["T-1748", "T-1780"])
        assert len(collisions) == 1
        assert collisions[0]["a"] == "T-1748"
        assert collisions[0]["b"] == "T-1780"
        assert ("docs/modules/tickets.md", "docs/modules/tickets.md") in collisions[
            0
        ]["overlapping_globs"]

    def test_no_overlap_reports_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Disjoint declared scopes report no collisions at all."""

        def fake_readiness(tid: str) -> dict:
            scope = ["src/a.py"] if tid == "T-1" else ["src/b.py"]
            return {
                "ticket_id": tid,
                "lease": None,
                "main": {"state": "queued", "scope": scope},
            }

        monkeypatch.setattr(fleet_status, "ticket_readiness", fake_readiness)
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        assert fleet_status.scope_intersections(["T-1", "T-2"]) == []

    def test_checks_against_a_held_lease_outside_the_requested_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A requested ticket's effective scope is ALSO checked against
        every held lease not already in the requested set, so a
        coordinator sees external contention against an already in-flight
        lease, not just contention within the wave being vetted."""
        monkeypatch.setattr(
            fleet_status,
            "ticket_readiness",
            lambda tid: {
                "ticket_id": tid,
                "lease": None,
                "main": {"state": "queued", "scope": ["src/shared.py"]},
            },
        )
        monkeypatch.setattr(
            fleet_status,
            "leases",
            lambda: [{"ticket_id": "T-9999", "scope": ["src/shared.py"]}],
        )
        collisions = fleet_status.scope_intersections(["T-1"])
        assert len(collisions) == 1
        assert collisions[0] == {
            "a": "T-1",
            "b": "T-9999",
            "overlapping_globs": [("src/shared.py", "src/shared.py")],
        }


class TestLandProcessRows:
    """`fleet_status.land_process_rows` (T-2180)."""

    def test_parses_matching_rows_and_skips_others(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rows whose argv contains `ticket land` are parsed into
        structured dicts (pid, etimes, cputime, argv); the header line
        and rows for unrelated commands are skipped."""
        stdout = (
            "    PID  ETIMES     TIME COMMAND\n"
            "    100     300    00:10 /venv/bin/python -m frob ticket land "
            "--ticket T-1234\n"
            "    200      50    00:00 vim some_file.py\n"
        )
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **k: _completed(stdout)
        )
        rows = fleet_status.land_process_rows()
        assert len(rows) == 1
        assert rows[0]["pid"] == 100
        assert rows[0]["etimes"] == 300
        assert rows[0]["cputime"] == "00:10"
        assert "ticket land" in rows[0]["argv"]

    def test_failed_ps_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A nonzero `ps` exit reads as no rows, never a raised error."""
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **k: _completed("", returncode=1)
        )
        assert fleet_status.land_process_rows() == []


class TestLandInvocations:
    """`fleet_status.land_invocations` (T-2180)."""

    def test_collapses_process_fan_out_by_ticket_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The ~4-row process fan-out for a single real land (bash
        wrapper, timeout, uv run, the python process -- T-1344's own
        measured shape) collapses to ONE invocation keyed on the ticket id
        parsed from argv, not a per-row count. `ps aux | grep -c "frob
        ticket land"` returns ~4 for this same input; this must return 1.
        T-2193: the ticket id is a POSITIONAL argument after `land`
        (`frob ticket land T-1234 --worktree ...`) -- there is no
        `--ticket` flag on this subcommand -- so this fixture uses the
        real argv shape, not a flag form that would never match a live
        land."""
        rows = [
            {
                "pid": 100,
                "etimes": 300,
                "cputime": "00:10",
                "argv": "bash -c timeout 540 uv run frob ticket land T-1234 --worktree /w",
            },
            {
                "pid": 101,
                "etimes": 298,
                "cputime": "00:05",
                "argv": "timeout 540 uv run frob ticket land T-1234 --worktree /w",
            },
            {
                "pid": 102,
                "etimes": 295,
                "cputime": "00:05",
                "argv": "uv run frob ticket land T-1234 --worktree /w",
            },
            {
                "pid": 103,
                "etimes": 290,
                "cputime": "04:30",
                "argv": "/venv/bin/python -m frob ticket land T-1234 --worktree /w",
            },
        ]
        monkeypatch.setattr(fleet_status, "land_process_rows", lambda: rows)
        invocations = fleet_status.land_invocations()
        assert len(invocations) == 1
        inv = invocations[0]
        assert inv["ticket_id"] == "T-1234"
        assert sorted(inv["pids"]) == [100, 101, 102, 103]
        # elapsed = MAX etimes across the group (the longest-lived row)
        assert inv["elapsed_s"] == 300
        # cpu = MAX parsed cpu time across the group (270s = 4:30)
        assert inv["cpu_s"] == 270

    # frob:ticket T-2193
    def test_must_pass_control_one_land_many_processes_reports_one(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2193's own must-pass control: a fixture representing exactly
        ONE real land as several processes (the measured live incident --
        13 rows for pid 2298926, its wrapper processes and sibling
        invocations, most at cpu=0s and one at cpu=67s) reports exactly
        ONE invocation. A test that only asserts 'some lands are
        reported' cannot distinguish working from inflated; this asserts
        the exact count."""
        rows = [
            {
                "pid": 2298899,
                "etimes": 90,
                "cputime": "00:00",
                "argv": "bash -c timeout 540 uv run frob ticket land T-9999 --worktree /w",
            },
            {
                "pid": 2298920,
                "etimes": 90,
                "cputime": "00:00",
                "argv": "timeout 540 uv run frob ticket land T-9999 --worktree /w",
            },
            {
                "pid": 2298926,
                "etimes": 90,
                "cputime": "01:07",
                "argv": "/venv/bin/python -m frob ticket land T-9999 --worktree /w",
            },
        ]
        monkeypatch.setattr(fleet_status, "land_process_rows", lambda: rows)
        invocations = fleet_status.land_invocations()
        assert len(invocations) == 1
        assert invocations[0]["ticket_id"] == "T-9999"
        assert invocations[0]["cpu_s"] == 67

    def test_rows_with_no_ticket_id_are_dropped_not_reported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2193: a row whose argv parses no ticket id at all (a
        coordinator's own long-lived wait-loop shell whose command line
        merely CONTAINS the substring 'frob ticket land', measured for
        real at elapsed=101983s -- ~28 hours, plainly not a land) is
        DROPPED from `land_invocations` entirely, not reported as its own
        `ticket_id=None` invocation -- the earlier behavior still
        inflated `LANDS IN FLIGHT` by one per such row."""
        rows = [
            {
                "pid": 428763,
                "etimes": 101983,
                "cputime": "00:07",
                "argv": (
                    "/bin/bash -c until [ \"$(pgrep -f 'frob ticket land T-' "
                    "| wc -l)\" -eq 0 ]; do sleep 15; done"
                ),
            },
        ]
        monkeypatch.setattr(fleet_status, "land_process_rows", lambda: rows)
        assert fleet_status.land_invocations() == []

    # frob:ticket T-2249
    def test_child_cpu_s_sums_live_descendants_not_tracked_rows(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fold-in fix (not separately ticketed): a healthy land's own 4
        tracked rows can each read ~0 CPU while the real work happens in
        a CHILD process (e.g. `frob check`) neither `land_process_rows`
        nor its `cpu_s` ever sees. `child_cpu_s` must total that child's
        own CPU time, found by walking `_all_process_ppid_cpu`'s ppid
        links from the tracked pids -- summing descendants only, never
        double-counting the tracked pids themselves."""
        rows = [
            {
                "pid": 200,
                "etimes": 60,
                "cputime": "00:01",
                "argv": "uv run frob ticket land T-5555 --worktree /w",
            },
        ]
        monkeypatch.setattr(fleet_status, "land_process_rows", lambda: rows)
        monkeypatch.setattr(
            fleet_status,
            "_all_process_ppid_cpu",
            lambda: {
                200: (1, 1),  # the tracked land pid itself: ppid=1, 1s cpu
                201: (200, 45),  # child: frob check, 45s cpu
                202: (201, 5),  # grandchild spawned by frob check
            },
        )
        invocations = fleet_status.land_invocations()
        assert len(invocations) == 1
        assert invocations[0]["cpu_s"] == 1
        assert invocations[0]["child_cpu_s"] == 50


class TestDescendantCpuSeconds:
    """`fleet_status._descendant_cpu_seconds` (T-2249)."""

    def test_sums_only_live_descendants_not_the_root(self) -> None:
        """The root pid's own cpu-seconds are never included -- only
        pids reachable by following ppid links FROM the root."""
        table = {1: (0, 999), 100: (1, 3), 101: (100, 7), 200: (1, 4)}
        assert fleet_status._descendant_cpu_seconds([100], table) == 7
        # 200 is a sibling of 100 under pid 1, not a descendant of 100
        assert fleet_status._descendant_cpu_seconds([1], table) == 3 + 7 + 4

    def test_no_children_returns_zero(self) -> None:
        table = {100: (1, 5)}
        assert fleet_status._descendant_cpu_seconds([100], table) == 0


class TestLandLockHolderPids:
    """`fleet_status.land_lock_holder_pids` (T-2180)."""

    def test_finds_a_pid_holding_the_lock_open(self, tmp_path: Path) -> None:
        """A pid whose `fd` table contains a symlink resolving to
        `.frob/land.lock` is reported as a live holder -- the /proc-fd
        liveness check, not the recorded pid or the lock's file age."""
        root = tmp_path / "repo"
        (root / ".frob").mkdir(parents=True)
        lock_path = root / ".frob" / "land.lock"
        lock_path.write_text("{}", encoding="utf-8")

        proc = tmp_path / "proc"
        # pid 555 holds the lock open via fd 7
        fd_dir = proc / "555" / "fd"
        fd_dir.mkdir(parents=True)
        (fd_dir / "7").symlink_to(lock_path)
        # pid 999 holds an unrelated file open
        other_fd_dir = proc / "999" / "fd"
        other_fd_dir.mkdir(parents=True)
        (other_fd_dir / "3").symlink_to(root / ".frob" / "quarantine.json")

        assert fleet_status.land_lock_holder_pids(root, proc=proc) == [555]

    def test_no_live_holder_returns_empty(self, tmp_path: Path) -> None:
        """No pid's fd table points at the lock file: reported as no live
        holder, distinct from the lock file's own existence."""
        root = tmp_path / "repo"
        (root / ".frob").mkdir(parents=True)
        (root / ".frob" / "land.lock").write_text("{}", encoding="utf-8")

        proc = tmp_path / "proc"
        fd_dir = proc / "111" / "fd"
        fd_dir.mkdir(parents=True)
        (fd_dir / "1").symlink_to(root / ".frob" / "quarantine.json")

        assert fleet_status.land_lock_holder_pids(root, proc=proc) == []


class TestPrintLandStatus:
    """`fleet_status._print_land_status` (T-2180)."""

    def test_prints_invocations_and_live_lock_holder(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Each invocation prints its ticket id, pids, elapsed, and cpu
        time; a live lock holder prints its pid(s), never the recorded-pid
        or lock-age language."""
        monkeypatch.setattr(
            fleet_status,
            "land_invocations",
            lambda: [
                {
                    "ticket_id": "T-1234",
                    "pids": [100, 101],
                    "elapsed_s": 300,
                    "cpu_s": 270,
                }
            ],
        )
        monkeypatch.setattr(
            fleet_status, "land_lock_holder_pids", lambda root: [100]
        )
        monkeypatch.setattr(fleet_status, "host_load", lambda: (19.5, 10 * 1024 * 1024))
        monkeypatch.setattr(fleet_status, "leases", lambda: [{"ticket_id": "T-1"}])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 1)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "LANDS IN FLIGHT: 1" in out
        assert "T-1234" in out and "elapsed=300s" in out and "cpu=270s" in out
        assert "LAND LOCK: held, live holder pid(s)=[100]" in out
        assert "LOAD 19.5" in out and "MEM 10.0GB avail" in out
        assert "1 live lease(s) (1 total)" in out

    # frob:ticket T-2249
    def test_prints_child_cpu_when_nonzero_omits_when_zero(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Fold-in fix: an invocation with `child_cpu_s` > 0 prints the
        `(+Ns in children)` suffix; one with `child_cpu_s` == 0 (or the
        key entirely absent, matching a caller on an older shape) prints
        exactly as before -- never a spurious `(+0s in children)`."""
        monkeypatch.setattr(
            fleet_status,
            "land_invocations",
            lambda: [
                {
                    "ticket_id": "T-1111",
                    "pids": [10],
                    "elapsed_s": 60,
                    "cpu_s": 1,
                    "child_cpu_s": 45,
                },
                {
                    "ticket_id": "T-2222",
                    "pids": [20],
                    "elapsed_s": 60,
                    "cpu_s": 30,
                    "child_cpu_s": 0,
                },
            ],
        )
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [])
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        monkeypatch.setattr(fleet_status, "swap_pressure", lambda: None)
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 0)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "T-1111" in out and "cpu=1s (+45s in children)" in out
        assert "T-2222" in out and "cpu=30s" in out
        assert "cpu=30s (+0s in children)" not in out

    def test_prints_no_live_holder_as_normal_resting_state_not_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A lock file that exists but has no live /proc-fd holder --
        the NORMAL resting state for an idle repo, since flock is
        kernel-released the instant its holder dies -- must never read
        as 'stale' (fold-in fix, not separately ticketed: this exact
        wording contributed to one retracted ticket claiming a stale
        lock deadlocked the fleet). Still names the real state (no live
        holder) and still warns against trusting the recorded pid or
        lock age -- it is a liveness fact, not silence. REPO is
        monkeypatched to a scratch directory so this test never touches
        the real repo's own `.frob/land.lock`."""
        fake_repo = tmp_path / "repo"
        (fake_repo / ".frob").mkdir(parents=True)
        (fake_repo / ".frob" / "land.lock").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "REPO", fake_repo)
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [])
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        monkeypatch.setattr(fleet_status, "swap_pressure", lambda: None)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "LANDS IN FLIGHT: 0" in out
        assert "stale" not in out.lower()
        assert "no live holder" in out.lower()
        assert "normal resting state" in out.lower()
        assert "LOAD: unknown" in out

    # frob:ticket T-2222
    def test_guidance_line_uses_live_count_not_raw_count(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2222 acceptance [2]: the concurrency guidance clause's own
        number is the LIVE count, never `len(leases())` -- 6 raw leases
        with only 4 live must print '4 live lease(s) (6 total)', not
        '6 lease(s)' (the measured incident: a coordinator held dispatch
        believing 6 leases meant 6 live agents)."""
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [])
        monkeypatch.setattr(fleet_status, "host_load", lambda: (1.0, 1024 * 1024))
        monkeypatch.setattr(
            fleet_status, "leases", lambda: [{"ticket_id": f"T-{i}"} for i in range(6)]
        )
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 4)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "4 live lease(s) (6 total)" in out
        assert "6 lease(s) --" not in out


class TestLeaseClassification:
    """`fleet_status.lease_classification` / `live_lease_count` (T-2222)."""

    def _record(self, tmp_path: Path, **overrides: object) -> dict:
        worktree = tmp_path / "wt"
        worktree.mkdir(exist_ok=True)
        record: dict = {
            "ticket_id": "T-9001",
            "worktree": str(worktree),
            "scope": ["src/frob/**"],
            "branch": "t-9001",
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        record.update(overrides)
        return record

    def test_live_lease_stays_live(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The must-still-pass control: a genuinely live lease (worktree
        exists, ticket in-progress on main, well within TTL) MUST STILL
        report 'live' -- a fix that marks everything reclaimable would
        satisfy every other test here and be catastrophic (T-2222
        acceptance [4])."""
        record = self._record(tmp_path)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "in-progress", "scope": [], "blocked_by": []},
        )
        assert fleet_status.lease_classification(record) == "live"
        assert fleet_status.live_lease_count([record]) == 1

    def test_holder_dead_is_reclaimable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Past TTL with no live process cwd'd into the worktree ->
        reclaimable (T-1382's own real shape: `holder-dead`)."""
        stale_recorded = (
            datetime.now(UTC).timestamp() - fleet_status._LEASE_TTL_SECONDS - 3600
        )
        record = self._record(
            tmp_path,
            recorded_at=datetime.fromtimestamp(stale_recorded, tz=UTC).isoformat(),
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "in-progress", "scope": [], "blocked_by": []},
        )
        monkeypatch.setattr(
            fleet_status, "_scan_for_live_worktree_process", lambda path: None
        )
        assert fleet_status.lease_classification(record) == "reclaimable"
        assert fleet_status.live_lease_count([record]) == 0

    def test_ticket_terminal_is_reclaimable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket whose `main` state is `done`/`dropped` can never
        legitimately still hold a lease -- reclaimable regardless of TTL
        or worktree liveness."""
        record = self._record(tmp_path)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "done", "scope": [], "blocked_by": []},
        )
        assert fleet_status.lease_classification(record) == "reclaimable"

    def test_path_gone_is_reclaimable(self, tmp_path: Path) -> None:
        """A recorded worktree path that no longer exists on disk at all
        is reclaimable -- the cheapest, most-common shape, checked first
        (no `ticket_frontmatter_on_main` call needed at all)."""
        record = {
            "ticket_id": "T-9002",
            "worktree": str(tmp_path / "gone"),
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        assert fleet_status.lease_classification(record) == "reclaimable"

    def test_root_worktree_is_structurally_unreclaimable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2222 acceptance [3]: a lease whose `worktree` resolves to
        THIS repo's own root reports `'root-resident'` -- derived from
        comparing the record's own `worktree` field against the resolved
        repo root (`REPO`), never a ticket-id allowlist (T-1686's real
        shape: 53 processes cwd'd into the shared root at once, which
        would otherwise read as 'live' forever). A root-resident lease
        does NOT count toward `live_lease_count` either -- it was never a
        real dispatched agent."""
        monkeypatch.setattr(fleet_status, "REPO", tmp_path)
        record = self._record(tmp_path, worktree=str(tmp_path))
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "in-progress", "scope": [], "blocked_by": []},
        )
        assert fleet_status.lease_classification(record) == "root-resident"
        assert fleet_status.live_lease_count([record]) == 0

    def test_classification_is_strictly_read_only(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2222 acceptance [5]: classifying a batch of leases (including
        reclaimable and root-resident ones) never releases, modifies, or
        deletes anything -- `Path.unlink` is monkeypatched to raise if
        called at all, and both classification calls must still complete
        without hitting it."""

        def _fail_if_called(self: Path) -> None:  # pragma: no cover - guard
            raise AssertionError(
                "lease_classification/live_lease_count must never delete "
                "or modify a lease file"
            )

        monkeypatch.setattr(Path, "unlink", _fail_if_called)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "in-progress", "scope": [], "blocked_by": []},
        )
        monkeypatch.setattr(fleet_status, "REPO", tmp_path / "not-the-repo-root")
        live_record = self._record(tmp_path)
        gone_record = {
            "ticket_id": "T-9003",
            "worktree": str(tmp_path / "does-not-exist"),
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        assert fleet_status.lease_classification(live_record) == "live"
        assert fleet_status.lease_classification(gone_record) == "reclaimable"
        assert fleet_status.live_lease_count([live_record, gone_record]) == 1


class TestHostLoad:
    """`fleet_status.host_load` (T-2180)."""

    def test_reads_loadavg_and_mem_available(self, tmp_path: Path) -> None:
        """Both values are read from their own structured /proc fields --
        `MemAvailable`, not `MemFree`, so a busy-but-healthy host with
        `MemFree` near 0 does not read as a false alarm."""
        proc = tmp_path / "proc"
        proc.mkdir()
        (proc / "loadavg").write_text("19.48 11.75 9.23 12/616 123\n", encoding="utf-8")
        (proc / "meminfo").write_text(
            "MemTotal:       24000000 kB\n"
            "MemFree:               0 kB\n"
            "MemAvailable:   10485760 kB\n",
            encoding="utf-8",
        )
        result = fleet_status.host_load(proc)
        assert result == (19.48, 10485760)

    def test_missing_proc_files_return_none(self, tmp_path: Path) -> None:
        """A `/proc` with neither file present (a sandboxed or non-Linux
        host) reads as unknown, never a fabricated zero load/plenty of
        memory."""
        proc = tmp_path / "proc"
        proc.mkdir()
        assert fleet_status.host_load(proc) is None


class TestSwapPressure:
    """`fleet_status.swap_pressure` (T-2249)."""

    def test_reads_swap_used_and_total(self, tmp_path: Path) -> None:
        """`swap_used_kb = SwapTotal - SwapFree`, matching `free`'s own
        arithmetic -- the measured incident's own numbers (24GB total,
        17GB free, so 6GB [6291456 kB rounded] used)."""
        proc = tmp_path / "proc"
        proc.mkdir()
        (proc / "meminfo").write_text(
            "MemTotal:       24000000 kB\n"
            "SwapTotal:      25165824 kB\n"
            "SwapFree:       17825792 kB\n",
            encoding="utf-8",
        )
        assert fleet_status.swap_pressure(proc) == (7340032, 25165824)

    def test_swap_total_zero_never_crashes_or_claims_pressure(
        self, tmp_path: Path
    ) -> None:
        """MUST-STILL-PASS: `SwapTotal: 0` (no swap configured, a real
        and common case) reads as `(0, 0)`, never a crash and never fed
        to `_swap_guidance` as pressure."""
        proc = tmp_path / "proc"
        proc.mkdir()
        (proc / "meminfo").write_text(
            "MemTotal:       24000000 kB\nSwapTotal:             0 kB\nSwapFree:              0 kB\n",
            encoding="utf-8",
        )
        assert fleet_status.swap_pressure(proc) == (0, 0)
        assert fleet_status._swap_guidance((0, 0)) == "3-4 agent concurrent"

    def test_missing_proc_file_returns_none(self, tmp_path: Path) -> None:
        """A `/proc` with no `meminfo` at all reads as unknown, never a
        fabricated zero (which `_swap_guidance` would otherwise be unable
        to distinguish from 'genuinely no swap in use')."""
        proc = tmp_path / "proc"
        proc.mkdir()
        assert fleet_status.swap_pressure(proc) is None


class TestSwapGuidance:
    """`fleet_status._swap_guidance` (T-2249)."""

    def test_swap_above_floor_overrides_the_static_guidance(self) -> None:
        """(MUST FAIL FIRST, pre-fix) Swap usage at/above
        `_SWAP_PRESSURE_FLOOR_KB` (1GB) replaces the static '3-4 agent'
        text with the real pressure, using the measured incident's own
        6GB figure."""
        guidance = fleet_status._swap_guidance((6 * 1024 * 1024, 24 * 1024 * 1024))
        assert "3-4 agent" not in guidance
        assert "SWAP" in guidance
        assert "6.0GB" in guidance

    def test_swap_below_floor_keeps_the_static_guidance(self) -> None:
        """A few MB of swap (well under the 1GB floor, the ticket's own
        'not any swap at all' caution) must NOT trip the pressure
        guidance -- a machine legitimately using a little swap is not
        automatically over-committed."""
        guidance = fleet_status._swap_guidance((10 * 1024, 24 * 1024 * 1024))
        assert guidance == "3-4 agent concurrent"

    def test_unknown_swap_keeps_the_static_guidance(self) -> None:
        """`swap is None` (unreadable /proc) must never be read as
        'pressure' -- pressure is only ever claimed from a real reading,
        same posture as `host_load` returning `None`."""
        assert fleet_status._swap_guidance(None) == "3-4 agent concurrent"


# frob:ticket T-2179
class TestTicketReadiness:
    """`fleet_status.ticket_readiness` (T-2133)."""

    # frob:ticket T-2179
    def test_dispatchable_when_no_lease_no_commits_no_divergence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A queued ticket, no live lease, no sibling-branch commits: ready."""
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "queued", "scope": ["src/a.py"]},
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["dispatchable"] is True
        assert readiness["scope_diverges"] is False
        assert readiness["worktrees_with_commits"] == []

    # frob:ticket T-2179
    def test_not_dispatchable_when_a_live_lease_exists(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A live lease (someone already working it) blocks dispatch --
        the exact T-2114 incident: dispatched believing the lease 'should
        be free now' when another worktree still held it."""
        monkeypatch.setattr(
            fleet_status,
            "ticket_lease",
            lambda tid: {
                "ticket_id": tid,
                "scope": ["src/a.py"],
                "worktree": "/w",
                "branch": "b",
                "recorded_at": "2026-08-01T00:00:00+00:00",
            },
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "queued", "scope": ["src/a.py"]},
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        assert fleet_status.ticket_readiness("T-2114")["dispatchable"] is False

    # frob:ticket T-2179
    def test_not_dispatchable_when_another_branch_already_has_commits(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Already-implemented-elsewhere (no lease left, but real commits
        on a sibling branch) also blocks dispatch."""
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "queued", "scope": ["src/a.py"]},
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: ["sibling"]
        )
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["dispatchable"] is False
        assert readiness["worktrees_with_commits"] == ["sibling"]

    # frob:ticket T-2179
    def test_flags_scope_divergence_between_the_live_lease_and_main(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The live lease's scope differing from main's committed scope is
        surfaced as `scope_diverges`, the 'single highest-value signal'
        this ticket exists to add."""
        monkeypatch.setattr(
            fleet_status,
            "ticket_lease",
            lambda tid: {
                "ticket_id": tid,
                "scope": ["src/a.py"],
                "worktree": "/w",
                "branch": "b",
                "recorded_at": "2026-08-01T00:00:00+00:00",
            },
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "queued", "scope": ["src/a.py", "src/b.py"]},
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["scope_diverges"] is True
        assert readiness["dispatchable"] is False

    # frob:ticket T-2196
    # frob:tests \
    # tests/unit/test_coordinator_scripts.py::TestTicketReadiness.test_not_dispatchable\
    # _when_ticket_does_not_exist_on_main
    def test_not_dispatchable_when_ticket_does_not_exist_on_main(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2196's own reproduction: a ticket absent from `main` must
        never read `dispatchable: True`, no matter how clean the lease/
        commit checks come back -- the fact `ticket_frontmatter_on_main`
        already measures (and `main: ticket does not exist on main`
        already PRINTS) must gate the verdict, not be computed and then
        discarded."""
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)
        monkeypatch.setattr(
            fleet_status, "ticket_frontmatter_on_main", lambda tid: None
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        readiness = fleet_status.ticket_readiness("T-9999")
        assert readiness["main"] is None
        assert readiness["dispatchable"] is False

    # frob:ticket T-2196
    # frob:tests \
    # tests/unit/test_coordinator_scripts.py::TestTicketReadiness.test_not_dispatchable\
    # _when_a_blocker_is_still_open
    def test_not_dispatchable_when_a_blocker_is_still_open(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`blocked_by` naming a still-open ticket must block dispatch --
        acceptance [2]'s named audit target: this edge was never checked
        at all before T-2196, so a ticket correctly blocked on an open
        dependency still read as `dispatchable: True`."""
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)

        def fake_main(tid: str) -> dict | None:
            if tid == "T-2114":
                return {
                    "state": "queued",
                    "scope": ["src/a.py"],
                    "blocked_by": ["T-0001"],
                }
            if tid == "T-0001":
                return {"state": "in-progress", "scope": [], "blocked_by": []}
            return None

        monkeypatch.setattr(fleet_status, "ticket_frontmatter_on_main", fake_main)
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["open_blockers"] == ["T-0001"]
        assert readiness["dispatchable"] is False

    # frob:ticket T-2196
    # frob:tests \
    # tests/unit/test_coordinator_scripts.py::TestTicketReadiness.test_dispatchable_whe\
    # n_every_blocker_is_done
    def test_dispatchable_when_every_blocker_is_done(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A `blocked_by` entry that is `done` on `main` does not block
        dispatch -- the positive control for the previous test, proving
        the new check discriminates rather than always refusing."""
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)

        def fake_main(tid: str) -> dict | None:
            if tid == "T-2114":
                return {
                    "state": "queued",
                    "scope": ["src/a.py"],
                    "blocked_by": ["T-0001"],
                }
            if tid == "T-0001":
                return {"state": "done", "scope": [], "blocked_by": []}
            return None

        monkeypatch.setattr(fleet_status, "ticket_frontmatter_on_main", fake_main)
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["open_blockers"] == []
        assert readiness["dispatchable"] is True


class TestScopeLeaseCollisions:
    """`fleet_status.scope_lease_collisions` / `_expand_scope_globs_to_paths`
    (T-2225)."""

    def _make_tree(self, tmp_path: Path) -> Path:
        (tmp_path / "src" / "frob" / "tickets").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "tickets" / "_land.py").write_text(
            "x = 1\n", encoding="utf-8"
        )
        (tmp_path / "src" / "frob" / "app").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "app" / "config.py").write_text(
            "y = 2\n", encoding="utf-8"
        )
        return tmp_path

    def test_glob_scope_collides_with_a_literal_lease_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2225 acceptance [1]/[2]: a glob scope entry (`src/frob/**`)
        colliding only after EXPANSION against the real filesystem with a
        live lease's literal scope file (`src/frob/tickets/_land.py`) is
        detected -- the measured incident this fixes: no lexical/string
        comparison of those two texts would ever match."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        monkeypatch.setattr(
            fleet_status,
            "lease_classification",
            lambda record: "live",
        )
        held = [
            {
                "ticket_id": "T-2215",
                "worktree": str(root),
                "scope": ["src/frob/tickets/_land.py"],
                "recorded_at": "2026-08-01T00:00:00+00:00",
            }
        ]
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/**"], held
        )
        assert len(collisions) == 1
        assert collisions[0]["ticket_id"] == "T-2215"
        assert any("_land.py" in p for p in collisions[0]["paths"])

    def test_no_collision_when_files_are_disjoint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2225 acceptance [3]: a ticket whose scope files do not overlap
        any live lease's own MUST STILL report no collision (must-still-
        pass control against a fix that flags everything)."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        monkeypatch.setattr(fleet_status, "lease_classification", lambda record: "live")
        held = [
            {
                "ticket_id": "T-2215",
                "worktree": str(root),
                "scope": ["src/frob/tickets/_land.py"],
                "recorded_at": "2026-08-01T00:00:00+00:00",
            }
        ]
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/app/config.py"], held
        )
        assert collisions == []

    def test_a_reclaimable_lease_is_never_a_collision(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2225 acceptance [4]: a lease `lease_classification` calls
        reclaimable (or root-resident) is not held by anyone and must
        never count as a collision, even though its scope files
        genuinely overlap on disk -- reuses T-2222's own classification,
        never re-implements staleness rules here."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        monkeypatch.setattr(
            fleet_status, "lease_classification", lambda record: "reclaimable"
        )
        held = [
            {
                "ticket_id": "T-2215",
                "worktree": str(root),
                "scope": ["src/frob/tickets/_land.py"],
                "recorded_at": "2026-08-01T00:00:00+00:00",
            }
        ]
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/**"], held
        )
        assert collisions == []


class TestTicketReadinessScopeCollision:
    """`fleet_status.ticket_readiness`'s scope-collision integration
    (T-2225)."""

    def test_not_dispatchable_when_scope_files_are_held_by_another_live_lease(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2225's own reproduction: `--ticket` on a ticket whose scope
        files are held by another ticket's live lease must report the
        collision and `dispatchable: False` -- fails today: prints
        `lease: none` / `dispatchable: True`."""
        (tmp_path / "src" / "frob" / "tickets").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "tickets" / "_land.py").write_text(
            "x = 1\n", encoding="utf-8"
        )
        monkeypatch.setattr(fleet_status, "REPO", tmp_path)
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "queued", "scope": ["src/frob/**"], "blocked_by": []},
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        monkeypatch.setattr(
            fleet_status,
            "leases",
            lambda: [
                {
                    "ticket_id": "T-2215",
                    "worktree": str(tmp_path),
                    "scope": ["src/frob/tickets/_land.py"],
                    "recorded_at": "2026-08-01T00:00:00+00:00",
                }
            ],
        )
        monkeypatch.setattr(fleet_status, "lease_classification", lambda record: "live")
        readiness = fleet_status.ticket_readiness("T-2220")
        assert readiness["scope_lease_collisions"] != []
        assert readiness["dispatchable"] is False

    def test_dispatchable_when_no_colliding_lease(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-still-pass control: a ticket whose scope files are held
        by no one still reports dispatchable."""
        (tmp_path / "src" / "frob" / "app").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "app" / "config.py").write_text(
            "y = 2\n", encoding="utf-8"
        )
        monkeypatch.setattr(fleet_status, "REPO", tmp_path)
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda tid: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {
                "state": "queued",
                "scope": ["src/frob/app/config.py"],
                "blocked_by": [],
            },
        )
        monkeypatch.setattr(
            fleet_status, "worktrees_touching_ticket", lambda tid, globs: []
        )
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["scope_lease_collisions"] == []
        assert readiness["dispatchable"] is True


# frob:ticket T-2172
class TestFleetStatusMain:
    """`fleet_status.main`."""

    def test_exit_zero_when_clean(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A clean root, with no leases/worktrees, exits 0."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        assert fleet_status.main() == 0
        assert "CLEAN" in capsys.readouterr().out

    def test_exit_one_when_dirty(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Any dirt line exits 1 and is echoed under a DIRTY banner."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [" M x.py"])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        assert fleet_status.main() == 1
        out = capsys.readouterr().out
        assert "DIRTY" in out
        assert " M x.py" in out

    # frob:ticket T-2133
    def test_ticket_flag_exits_one_when_not_dispatchable(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A clean root but a NOT-dispatchable `--ticket` still exits 1,
        with the reason (a live lease) printed -- T-2133's own exit-code
        gate, so this can drive a dispatch loop without prose parsing."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_readiness",
            lambda tid: {
                "ticket_id": tid,
                "lease": {
                    "recorded_at": "2026-08-01T00:00:00+00:00",
                    "worktree": "/w",
                    "scope": ["src/a.py"],
                },
                "main": {"state": "in-progress", "scope": ["src/a.py"]},
                "scope_diverges": False,
                "worktrees_with_commits": [],
                "dispatchable": False,
            },
        )
        monkeypatch.setattr(sys, "argv", ["fleet_status.py", "--ticket", "T-2114"])
        assert fleet_status.main() == 1
        out = capsys.readouterr().out
        assert "TICKET T-2114" in out
        assert "dispatchable: False" in out

    # frob:ticket T-2133
    def test_ticket_flag_exits_zero_when_dispatchable(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A clean root and a dispatchable `--ticket` exits 0."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_readiness",
            lambda tid: {
                "ticket_id": tid,
                "lease": None,
                "main": {"state": "queued", "scope": ["src/a.py"]},
                "scope_diverges": False,
                "worktrees_with_commits": [],
                "dispatchable": True,
            },
        )
        monkeypatch.setattr(sys, "argv", ["fleet_status.py", "--ticket", "T-2114"])
        assert fleet_status.main() == 0
        assert "dispatchable: True" in capsys.readouterr().out

    # frob:ticket T-2172
    def test_ticket_readiness_prints_before_the_general_report(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`TICKET <id>` prints FIRST, ahead of `ROOT` -- the coordinator's
        own report that a per-ticket answer was buried below the general
        fleet report; `--ticket` exists precisely to be the first thing
        read."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(
            fleet_status,
            "ticket_readiness",
            lambda tid: {
                "ticket_id": tid,
                "lease": None,
                "main": {"state": "queued", "scope": ["src/a.py"]},
                "scope_diverges": False,
                "worktrees_with_commits": [],
                "dispatchable": True,
            },
        )
        monkeypatch.setattr(sys, "argv", ["fleet_status.py", "--ticket", "T-2114"])
        fleet_status.main()
        out = capsys.readouterr().out
        assert out.index("TICKET T-2114") < out.index("ROOT")


# frob:ticket T-2172
class TestPrintTicketReadiness:
    """`fleet_status._print_ticket_readiness` (ARCH001/ARCH103 split,
    T-2172)."""

    # frob:ticket T-2172
    def test_prints_dispatchable_true(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A dispatchable, no-lease readiness dict prints the plain shape
        and returns True."""
        readiness = {
            "ticket_id": "T-2114",
            "lease": None,
            "main": {"state": "queued", "scope": ["src/a.py"]},
            "scope_diverges": False,
            "worktrees_with_commits": [],
            "dispatchable": True,
        }
        assert fleet_status._print_ticket_readiness(readiness) is True
        out = capsys.readouterr().out
        assert "TICKET T-2114" in out
        assert "lease: none" in out
        assert "dispatchable: True" in out

    # frob:ticket T-2172
    def test_prints_lease_scope_divergence_and_sibling_commits(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A held lease, a scope divergence, and sibling-branch commits
        each print their own dedicated line, and the function returns
        False (not dispatchable)."""
        readiness = {
            "ticket_id": "T-2114",
            "lease": {
                "recorded_at": "2026-08-01T00:00:00+00:00",
                "worktree": "/w",
                "scope": ["src/a.py"],
            },
            "main": {"state": "in-progress", "scope": ["src/a.py", "src/b.py"]},
            "scope_diverges": True,
            "worktrees_with_commits": ["sibling"],
            "dispatchable": False,
        }
        assert fleet_status._print_ticket_readiness(readiness) is False
        out = capsys.readouterr().out
        assert "lease: recorded_at=2026-08-01T00:00:00+00:00" in out
        assert "SCOPE DIVERGES" in out
        assert "ALREADY IMPLEMENTED on: sibling" in out
        assert "dispatchable: False" in out


# frob:ticket T-2172
class TestPrintFleetReport:
    """`fleet_status._print_fleet_report` (ARCH001/ARCH103 split,
    T-2172)."""

    # frob:ticket T-2172
    # frob:ticket T-2180
    def test_prints_all_four_sections(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """ROOT, LANDS, QUARANTINE, LEASES, and WORKTREES each print their
        own section, in that order (T-2180 added LANDS between ROOT and
        QUARANTINE)."""
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(
            fleet_status,
            "leases",
            lambda: [{"ticket_id": "T-2114", "worktree": "/w/t-2114"}],
        )
        monkeypatch.setattr(
            fleet_status, "worktrees", lambda idle_seconds: [("one", 10, False)]
        )
        fleet_status._print_fleet_report([" M x.py"], idle_seconds=1200)
        out = capsys.readouterr().out
        assert out.index("ROOT") < out.index("QUARANTINE") < out.index("LEASES")
        assert out.index("LEASES") < out.index("WORKTREES")
        assert "DIRTY" in out and " M x.py" in out

    # frob:ticket T-2222
    def test_leases_section_shows_classification_per_lease(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2222: each LEASES row prints its own `lease_classification`
        verdict, and the section header shows the LIVE count alongside
        the raw total -- a reclaimable lease (path-gone here) never reads
        indistinguishably from a live one."""
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(
            fleet_status,
            "leases",
            lambda: [{"ticket_id": "T-2114", "worktree": "/does/not/exist"}],
        )
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        fleet_status._print_fleet_report([], idle_seconds=1200)
        out = capsys.readouterr().out
        assert "LEASES 1 (0 live)" in out
        assert "T-2114 -> exist  [reclaimable]" in out


def _write_ticket(
    tickets_dir: Path,
    ticket_id: str,
    *,
    state: str = "queued",
    priority: str = "high",
    created: str = "2026-01-01",
    tier: str = "ticket",
    runs_last: bool = False,
    parent: str | None = None,
) -> None:
    """Write a minimal `tickets/<id>/ticket.md` fixture file with just the
    frontmatter fields `_parse_ticket_ledger_file` reads. `runs_last`
    (T-2200) is written as the same flat `key: value` line real
    `frob ticket` output uses (`runs_last: true`/`runs_last: false`), the
    STRUCTURED field the parser reads -- never inferred from `title`, so a
    fixture whose title happens to say 'RUNS LAST' (mirroring T-1614's
    real title) with `runs_last=False` must NOT be treated as deferred.
    `parent` (T-2229), when given, is written the same way real `frob
    ticket new --parent` output is; omitted entirely when `None` (mirrors
    a ledger row with no `parent:` line at all, not a literal 'null')."""
    ticket_dir = tickets_dir / ticket_id
    ticket_dir.mkdir(parents=True)
    parent_line = f"parent: {parent}\n" if parent is not None else ""
    (ticket_dir / "ticket.md").write_text(
        f"---\n"
        f"id: {ticket_id}\n"
        f"title: 'a title'\n"
        f"state: {state}\n"
        f"kind: feature\n"
        f"created: '{created}'\n"
        f"priority: {priority}\n"
        f"tier: {tier}\n"
        f"runs_last: {'true' if runs_last else 'false'}\n"
        f"{parent_line}"
        f"---\n",
        encoding="utf-8",
    )


class TestRottingTickets:
    """`fleet_status.rotting_tickets` (T-2182)."""

    def test_flags_a_ticket_past_its_priority_threshold(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A queued CRITICAL ticket older than its own 3-day threshold is
        reported, with age and threshold both present -- this MUST fail
        against current main (rotting_tickets does not exist there)."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir, "T-0001", state="queued", priority="critical",
            created="2020-01-01",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        monkeypatch.setattr(
            fleet_status, "_rot_day_thresholds",
            lambda: {"critical": 3, "high": 7, "medium": 30, "low": 90},
        )
        rotting = fleet_status.rotting_tickets()
        assert len(rotting) == 1
        assert rotting[0]["id"] == "T-0001"
        assert rotting[0]["priority"] == "critical"
        assert rotting[0]["threshold_days"] == 3
        assert rotting[0]["age_days"] > 3

    def test_ignores_tickets_still_under_threshold(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket created today never rots, regardless of priority."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir, "T-0002", state="queued", priority="critical",
            created=date.today().isoformat(),
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        assert fleet_status.rotting_tickets() == []

    def test_only_queued_and_planned_states_are_considered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An old ticket that is in-progress/done/dropped/blocked is NOT
        rotting -- TICK004's own selection (only queued/planned) is
        mirrored exactly, not a broader 'any old ticket' sweep."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir, "T-0003", state="in-progress", priority="critical",
            created="2020-01-01",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        assert fleet_status.rotting_tickets() == []

    def test_distinguishes_epic_and_story_tier_from_ticket_tier(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rotting tickets, stories, and epics are all reported (epics are
        NOT exempted) with their own `tier` field intact, so a caller can
        split them by required action."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir, "T-0004", state="queued", priority="critical",
            created="2020-01-01", tier="ticket",
        )
        _write_ticket(
            tickets_dir, "T-0005", state="queued", priority="critical",
            created="2020-01-01", tier="epic",
        )
        _write_ticket(
            tickets_dir, "T-0006", state="planned", priority="critical",
            created="2020-01-01", tier="story",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        tiers = {t["id"]: t["tier"] for t in rotting}
        assert tiers == {"T-0004": "ticket", "T-0005": "epic", "T-0006": "story"}

    def test_reads_runs_last_as_a_structured_field_not_from_title(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2200: `runs_last` comes from the ledger frontmatter's own
        `runs_last:` line, never inferred from `title` text -- a ticket
        whose title literally says 'RUNS LAST' (mirroring T-1614's real
        title) but whose `runs_last:` line is `false` must read as an
        ordinary (non-deferred) rotting ticket, and vice versa."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir, "T-0007", state="queued", priority="critical",
            created="2020-01-01", runs_last=True,
        )
        _write_ticket(
            tickets_dir, "T-0008", state="queued", priority="critical",
            created="2020-01-01", runs_last=False,
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        flags = {t["id"]: t["runs_last"] for t in rotting}
        assert flags == {"T-0007": True, "T-0008": False}

    # frob:ticket T-2229
    def test_epic_with_active_child_is_flagged_has_active_child(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2229's measured incident: T-1623 (epic, rotting) had children
        T-2223/T-2224 in-progress on main. `has_active_child` must read
        `True` for the epic -- the child need not itself be rotting."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir, "T-1623", state="queued", priority="critical",
            created="2020-01-01", tier="epic",
        )
        _write_ticket(
            tickets_dir, "T-2223", state="in-progress", priority="high",
            created=date.today().isoformat(), parent="T-1623",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        by_id = {t["id"]: t for t in rotting}
        assert by_id["T-1623"]["has_active_child"] is True

    # frob:ticket T-2229
    def test_epic_with_no_children_at_all_is_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-STILL-PASS: a genuinely undecomposed epic (no children at
        all) must still read `has_active_child=False` -- it keeps rotting
        under the ordinary message."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir, "T-0009", state="queued", priority="critical",
            created="2020-01-01", tier="epic",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        assert rotting[0]["has_active_child"] is False

    # frob:ticket T-2229
    def test_epic_whose_only_child_is_terminal_is_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A child that is `done`/`dropped` does NOT count as active --
        an epic whose decomposition is fully finished (or whose only
        child was dropped) is not 'being worked', it is either finished
        or genuinely stalled again."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir, "T-0010", state="queued", priority="critical",
            created="2020-01-01", tier="epic",
        )
        _write_ticket(
            tickets_dir, "T-0011", state="done", priority="high",
            created=date.today().isoformat(), parent="T-0010",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        assert rotting[0]["has_active_child"] is False


class TestPrintTicketRot:
    """`fleet_status._print_ticket_rot` (T-2182)."""

    def test_splits_by_tier_under_distinct_action_headings(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A leaf ticket prints under 'NEEDS DISPATCH'; an epic/story
        prints under 'NEEDS DECOMPOSITION' -- two distinct headings naming
        the required action, never one undifferentiated count (T-0411/
        T-2182's own incident: 10 of 15 rotting tickets were epics, only
        4 leaf tickets, and reporting them as one count read as noise for
        a whole session)."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-0004",
                    "priority": "critical",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                },
                {
                    "id": "T-0005",
                    "priority": "critical",
                    "tier": "epic",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 2" in out
        assert "NEEDS DISPATCH (1):" in out
        assert "NEEDS DECOMPOSITION (1):" in out
        assert "T-0004" in out.split("NEEDS DECOMPOSITION")[0]
        assert "T-0005" in out.split("NEEDS DECOMPOSITION")[1]

    # frob:ticket T-2229
    def test_decomposed_epic_prints_under_its_own_heading_not_needs_decomposition(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2229's measured incident: an epic already decomposed (a
        non-terminal child ticket exists) must print under 'DECOMPOSED,
        BEING WORKED', never under 'NEEDS DECOMPOSITION' -- and must
        still be reported (never dropped), same as the runs_last
        precedent."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-0005",
                    "priority": "critical",
                    "tier": "epic",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                    "has_active_child": False,
                },
                {
                    "id": "T-1623",
                    "priority": "critical",
                    "tier": "epic",
                    "state": "queued",
                    "age_days": 11,
                    "threshold_days": 3,
                    "has_active_child": True,
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 2" in out
        assert "NEEDS DECOMPOSITION (1):" in out
        assert "DECOMPOSED, BEING WORKED (1):" in out
        assert "T-0005" in out.split("DECOMPOSED, BEING WORKED")[0]
        assert "T-1623" in out.split("DECOMPOSED, BEING WORKED")[1]

    def test_runs_last_ticket_gets_its_own_deferred_bucket_not_needs_dispatch(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2200: a rotting leaf ticket with `runs_last=True` (T-1614's
        real shape) is reported under 'DEFERRED (RUNS LAST)', never under
        'NEEDS DISPATCH' -- `frob ticket start` structurally refuses a
        `runs_last` ticket with `RunsLastBlocked`, so listing it as
        dispatchable is advice the tool itself rejects. This MUST fail
        against the pre-fix report, which had no third bucket at all and
        put every leaf ticket -- runs_last or not -- under NEEDS DISPATCH.
        The must-still-pass control lives alongside it: an ordinary
        (non-runs_last) rotting leaf ticket still appears under NEEDS
        DISPATCH, unaffected."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-1614",
                    "priority": "high",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 11,
                    "threshold_days": 7,
                    "runs_last": True,
                },
                {
                    "id": "T-0004",
                    "priority": "critical",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                    "runs_last": False,
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 2" in out
        assert "NEEDS DISPATCH (1):" in out
        assert "DEFERRED (RUNS LAST) (1):" in out
        # T-1614 must NOT be listed under NEEDS DISPATCH.
        needs_dispatch_block = out.split("DEFERRED (RUNS LAST)")[0]
        assert "T-1614" not in needs_dispatch_block
        assert "T-0004" in needs_dispatch_block
        deferred_block = out.split("DEFERRED (RUNS LAST)")[1]
        assert "T-1614" in deferred_block
        assert "RunsLastBlocked" in deferred_block


class TestQuarantineState:
    """`fleet_status.quarantine_state` (T-2049)."""

    def test_reports_raised_with_undisposed_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An uncleared record reports 'raised' plus the count of findings
        with an empty (undisposed) `disposition`."""
        store = tmp_path / "quarantine.json"
        store.write_text(
            json.dumps(
                {
                    "cleared_at": None,
                    "findings": [
                        {"disposition": ""},
                        {"disposition": "filed"},
                        {"disposition": ""},
                    ],
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(fleet_status, "QUARANTINE", store)
        assert fleet_status.quarantine_state() == ("raised", 2)

    def test_reports_clear_when_store_says_cleared(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A record with `cleared_at` set is 'clear', regardless of its
        (now-historical) findings list."""
        store = tmp_path / "quarantine.json"
        store.write_text(
            json.dumps({"cleared_at": "2026-01-01T00:00:00+00:00", "findings": []}),
            encoding="utf-8",
        )
        monkeypatch.setattr(fleet_status, "QUARANTINE", store)
        assert fleet_status.quarantine_state() == ("clear", 0)

    def test_reports_clear_when_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No quarantine has ever been raised (missing store) is 'clear'."""
        monkeypatch.setattr(fleet_status, "QUARANTINE", tmp_path / "does-not-exist.json")
        assert fleet_status.quarantine_state() == ("clear", 0)

    def test_unreadable_store_is_unknown_never_clear(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Malformed JSON is 'unknown', never misread as 'clear' -- an
        unreadable store must never look like a green light to dispatch."""
        store = tmp_path / "quarantine.json"
        store.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "QUARANTINE", store)
        assert fleet_status.quarantine_state() == ("unknown", 0)

    def test_non_dict_record_is_unknown(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valid JSON that is not an object (e.g. a bare list) is 'unknown',
        not misparsed as a clear/empty record."""
        store = tmp_path / "quarantine.json"
        store.write_text("[]", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "QUARANTINE", store)
        assert fleet_status.quarantine_state() == ("unknown", 0)


class TestFleetStatusMainQuarantine:
    """`fleet_status.main`'s quarantine line (T-2049)."""

    def test_prints_raised_with_undisposed_count_and_consequence(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A raised quarantine is printed with its undisposed count and the
        deferred-landing consequence -- the whole point of T-2049 is that
        this line appears in the ONE place already read before dispatch."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("raised", 2))
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        fleet_status.main()
        out = capsys.readouterr().out
        assert "QUARANTINE RAISED" in out
        assert "2" in out
        assert "synchronous" in out

    def test_prints_clear(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A clear quarantine is reported plainly, not silently omitted."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        fleet_status.main()
        out = capsys.readouterr().out
        assert "QUARANTINE clear" in out

    def test_prints_unknown_as_unsafe(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """An unreadable store is reported as unknown/unsafe, never as
        clear."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("unknown", 0))
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        fleet_status.main()
        out = capsys.readouterr().out
        assert "QUARANTINE UNKNOWN" in out
        assert "clear" not in out.lower().split("quarantine unknown")[0]


class TestResolve:
    """`verify_lands.resolve`."""

    def test_resolves_full_sha(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A resolvable sha/ref returns git's full commit id, stripped."""
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed("abc123\n"))
        assert verify_lands.resolve("abc") == "abc123"

    def test_unknown_sha_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A sha `rev-parse` cannot verify returns None, never raises."""
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **k: _completed("", returncode=128)
        )
        assert verify_lands.resolve("not-a-sha") is None


class TestIsAncestor:
    """`verify_lands.is_ancestor`."""

    def test_true_when_ancestor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`merge-base --is-ancestor` exit 0 means the sha landed."""
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(returncode=0))
        assert verify_lands.is_ancestor("abc123", "main") is True

    def test_false_when_not_ancestor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A non-zero exit means the sha resolves but never landed on ref."""
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(returncode=1))
        assert verify_lands.is_ancestor("abc123", "main") is False


class TestSubject:
    """`verify_lands.subject`."""

    def test_returns_commit_subject(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The stripped stdout of `git log -1 --format=%s` is returned."""
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **k: _completed("fix: a thing\n")
        )
        assert verify_lands.subject("abc123") == "fix: a thing"


# frob:ticket T-2220
class TestLoadLandCommit:
    """`verify_lands.load_land_commit` -- T-2220's ticket-id resolution."""

    # frob:ticket T-2220
    def test_returns_land_commit_for_a_landed_ticket(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket whose `land_commit` field is set resolves to that sha."""
        from typani.result import Ok

        class _Fake:
            land_commit = "abc123full"

        # `load_land_commit` imports `frob.tickets._load_one` internally
        # (lazy import, at call time) -- patch the module attribute it
        # will fetch.
        import frob.tickets as tickets_mod

        monkeypatch.setattr(tickets_mod, "_load_one", lambda root, tid: Ok(_Fake()))
        assert verify_lands.load_land_commit("T-9999") == "abc123full"

    # frob:ticket T-2220
    def test_returns_none_for_an_unlanded_ticket(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket that exists but was never landed has `land_commit=None`."""
        from typani.result import Ok

        class _Fake:
            land_commit = None

        import frob.tickets as tickets_mod

        monkeypatch.setattr(tickets_mod, "_load_one", lambda root, tid: Ok(_Fake()))
        assert verify_lands.load_land_commit("T-9998") is None

    # frob:ticket T-2220
    def test_returns_missing_for_an_unknown_ticket_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket id that resolves to no ticket at all returns a `KeyError`
        instance (never raised), kept distinct from `None`/a real sha."""
        from typani.result import Err

        import frob.tickets as tickets_mod

        monkeypatch.setattr(
            tickets_mod, "_load_one", lambda root, tid: Err("not-found")
        )
        result = verify_lands.load_land_commit("T-0000")
        assert isinstance(result, KeyError)


# frob:ticket T-2220
class TestVerifyLandsMain:
    """`verify_lands.main`."""

    # frob:ticket T-2220
    # frob:tests tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain.test_ticket_id_argument_resolves_via_land_commit  # noqa: E501
    def test_ticket_id_argument_resolves_via_land_commit(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Acceptance criterion 3 (must-still-pass) + criterion 4: a SHA
        argument still works unchanged, AND a ticket id argument resolves
        through `load_land_commit` to a sha before the same ancestor check
        every plain sha gets -- this is what makes a `--plan` land
        (unreachable by any commit-subject grep) resolvable by id."""
        monkeypatch.setattr(
            verify_lands, "load_land_commit", lambda tid: "planlandedshafull"
        )
        monkeypatch.setattr(verify_lands, "resolve", lambda sha: f"{sha}-resolved")
        monkeypatch.setattr(verify_lands, "is_ancestor", lambda sha, ref: True)
        monkeypatch.setattr(verify_lands, "subject", lambda sha: "chore: land --plan")
        monkeypatch.setattr(
            sys, "argv", ["verify_lands.py", "T-2211", "realsha", "--ref", "main"]
        )
        assert verify_lands.main() == 0
        out = capsys.readouterr().out
        assert "ON main" in out
        assert "planlandedsh" in out  # sha truncated to 12 chars, same as ON's format

    # frob:ticket T-2220
    # frob:tests tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain.test_never_landed_ticket_id_refused_distinguishably_from_a_typo_sha  # noqa: E501
    def test_never_landed_ticket_id_refused_distinguishably_from_a_typo_sha(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Acceptance criterion 5: an unlanded ticket id (`land_commit`
        still `None`) is refused with a message DISTINCT from `UNKNOWN-SHA`
        (a plain typo) -- never conflated, exactly the discipline
        `resolve`/`is_ancestor` already apply to unknown-vs-missing shas."""
        monkeypatch.setattr(verify_lands, "load_land_commit", lambda tid: None)
        monkeypatch.setattr(verify_lands, "resolve", lambda sha: None)
        monkeypatch.setattr(
            sys, "argv", ["verify_lands.py", "T-2299", "typo123", "--ref", "main"]
        )
        assert verify_lands.main() == 1
        out = capsys.readouterr().out
        assert "NOT-LANDED" in out
        assert "T-2299" in out
        assert "UNKNOWN-SHA typo123" in out
        assert "NOT-LANDED" not in out.split("UNKNOWN-SHA")[1]

    def test_distinguishes_unknown_from_missing(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """An unresolvable sha prints UNKNOWN-SHA; a resolvable, non-landed sha
        prints MISSING -- the two must never be conflated (that conflation is
        the exact bug this script exists to prevent)."""

        def fake_resolve(sha: str) -> str | None:
            return None if sha == "typo123" else f"{sha}full"

        monkeypatch.setattr(verify_lands, "resolve", fake_resolve)
        monkeypatch.setattr(verify_lands, "is_ancestor", lambda sha, ref: False)
        monkeypatch.setattr(verify_lands, "subject", lambda sha: "irrelevant")
        monkeypatch.setattr(
            sys, "argv", ["verify_lands.py", "typo123", "realsha", "--ref", "main"]
        )
        assert verify_lands.main() == 1
        out = capsys.readouterr().out
        assert "UNKNOWN-SHA typo123" in out
        assert "MISSING" in out
        assert "realshafull" in out
