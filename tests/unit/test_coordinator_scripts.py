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

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO_ROOT / "scripts"


def _load(name: str) -> ModuleType:
    """Import a `scripts/<name>.py` module by path (scripts/ has no __init__)."""
    path = _SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_scripts_under_test.{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        ticket land"` returns ~4 for this same input; this must return 1."""
        rows = [
            {
                "pid": 100,
                "etimes": 300,
                "cputime": "00:10",
                "argv": "bash -c timeout 540 uv run frob ticket land --ticket T-1234",
            },
            {
                "pid": 101,
                "etimes": 298,
                "cputime": "00:05",
                "argv": "timeout 540 uv run frob ticket land --ticket T-1234",
            },
            {
                "pid": 102,
                "etimes": 295,
                "cputime": "00:05",
                "argv": "uv run frob ticket land --ticket T-1234",
            },
            {
                "pid": 103,
                "etimes": 290,
                "cputime": "04:30",
                "argv": "/venv/bin/python -m frob ticket land --ticket T-1234",
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

    def test_rows_with_no_ticket_id_are_never_merged_together(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Two rows that each lack a `--ticket` fragment cannot be
        correlated to each other -- each is reported as its own,
        `ticket_id=None` invocation rather than silently merged into one
        (which would misreport their combined elapsed/cpu as a single
        land)."""
        rows = [
            {"pid": 200, "etimes": 50, "cputime": "00:01", "argv": "frob ticket land"},
            {"pid": 201, "etimes": 20, "cputime": "00:02", "argv": "frob ticket land"},
        ]
        monkeypatch.setattr(fleet_status, "land_process_rows", lambda: rows)
        invocations = fleet_status.land_invocations()
        assert len(invocations) == 2
        assert all(inv["ticket_id"] is None for inv in invocations)
        assert {inv["pids"][0] for inv in invocations} == {200, 201}


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
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "LANDS IN FLIGHT: 1" in out
        assert "T-1234" in out and "elapsed=300s" in out and "cpu=270s" in out
        assert "LAND LOCK: held, live holder pid(s)=[100]" in out
        assert "LOAD 19.5" in out and "MEM 10.0GB avail" in out and "1 lease(s)" in out

    def test_prints_stale_lock_when_no_live_holder(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A lock file that exists but has no live /proc-fd holder prints
        STALE, never silently reads as free -- the exact "stale-lock
        theory survived long enough to be filed critical" incident this
        function exists to prevent, and never "trusts" the recorded pid
        or the lock's file-modification age. REPO is monkeypatched to a
        scratch directory so this test never touches the real repo's own
        `.frob/land.lock`."""
        fake_repo = tmp_path / "repo"
        (fake_repo / ".frob").mkdir(parents=True)
        (fake_repo / ".frob" / "land.lock").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "REPO", fake_repo)
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [])
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "LANDS IN FLIGHT: 0" in out
        assert "stale" in out.lower()
        assert "LOAD: unknown" in out


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
        assert "T-2114 -> t-2114" in out
        assert "one" in out


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


class TestVerifyLandsMain:
    """`verify_lands.main`."""

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
