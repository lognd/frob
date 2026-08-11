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


class TestWorktreesTouchingTicket:
    """`fleet_status.worktrees_touching_ticket` (T-2133)."""

    def test_finds_a_branch_with_unlanded_commits(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A worktree whose branch has `main..HEAD` commits touching
        `tickets/<id>/` is reported by name."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        (worktrees_dir / "two").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        def fake_git(args: list[str], cwd: Path) -> str:
            return "abc123 done report" if cwd.name == "one" else ""

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status.worktrees_touching_ticket("T-2114") == ["one"]

    def test_empty_when_nothing_touches_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No worktree with matching commits returns an empty list."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)
        monkeypatch.setattr(fleet_status, "_git", lambda args, cwd: "")
        assert fleet_status.worktrees_touching_ticket("T-2114") == []


class TestTicketReadiness:
    """`fleet_status.ticket_readiness` (T-2133)."""

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
        monkeypatch.setattr(fleet_status, "worktrees_touching_ticket", lambda tid: [])
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["dispatchable"] is True
        assert readiness["scope_diverges"] is False
        assert readiness["worktrees_with_commits"] == []

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
        monkeypatch.setattr(fleet_status, "worktrees_touching_ticket", lambda tid: [])
        assert fleet_status.ticket_readiness("T-2114")["dispatchable"] is False

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
            fleet_status, "worktrees_touching_ticket", lambda tid: ["sibling"]
        )
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["dispatchable"] is False
        assert readiness["worktrees_with_commits"] == ["sibling"]

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
        monkeypatch.setattr(fleet_status, "worktrees_touching_ticket", lambda tid: [])
        readiness = fleet_status.ticket_readiness("T-2114")
        assert readiness["scope_diverges"] is True
        assert readiness["dispatchable"] is False


class TestFleetStatusMain:
    """`fleet_status.main`."""

    def test_exit_zero_when_clean(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A clean root, with no leases/worktrees, exits 0."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
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
