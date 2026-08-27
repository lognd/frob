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
import os
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
wait_for_land_slot = _load("wait_for_land_slot")


def _report(*, results: list[dict[str, Any]]) -> dict[str, Any]:
    """A minimal `frob check --json`-shaped report for the given results."""
    return {"results": results}


def _diag(severity: str, code: str = "X001", file: str = "a.py", line: int = 1) -> dict:
    """A minimal diagnostic dict, severity nested exactly as frob emits it."""
    return {
        "severity": severity,
        "code": code,
        "file": file,
        "line": line,
        "message": "m",
    }


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


class TestFindTest006:
    """`check_summary.find_test006` (T-2763)."""

    def test_finds_test006_diagnostics(self) -> None:
        """A TEST006 diagnostic is returned with its tool and message."""
        report = _report(
            results=[
                {
                    "tool": "gate:TEST",
                    "diagnostics": [
                        _diag("error", code="TEST006"),
                        _diag("warning", code="TEST014"),
                    ],
                }
            ]
        )
        found = check_summary.find_test006(report)
        assert len(found) == 1
        assert found[0][0] == "gate:TEST"

    def test_empty_when_no_test006(self) -> None:
        """No TEST006 diagnostics anywhere returns an empty list."""
        report = _report(
            results=[{"tool": "ruff", "diagnostics": [_diag("error", code="E1")]}]
        )
        assert check_summary.find_test006(report) == []


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
        report = _report(
            results=[{"tool": "ty", "diagnostics": [_diag("error", code="E1")]}]
        )
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(report)))
        monkeypatch.setattr(sys, "argv", ["check_summary.py"])
        assert check_summary.main() == 1
        out = capsys.readouterr().out
        assert "ERRORS   1" in out
        assert "E1" in out

    def test_test006_banner_leads_output_when_present(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A TEST006 finding prints a leading stale-coverage banner (T-2763)."""
        report = _report(
            results=[
                {"tool": "gate:TEST", "diagnostics": [_diag("error", code="TEST006")]}
            ]
        )
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(report)))
        monkeypatch.setattr(sys, "argv", ["check_summary.py"])
        check_summary.main()
        out = capsys.readouterr().out
        assert "COVERAGE STALE/MISSING (TEST006)" in out
        assert out.index("COVERAGE STALE/MISSING") < out.index("SEVERITY")

    def test_no_banner_when_test006_absent(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """No TEST006 finding means no banner at all."""
        report = _report(results=[{"tool": "ruff", "diagnostics": [_diag("warning")]}])
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(report)))
        monkeypatch.setattr(sys, "argv", ["check_summary.py"])
        check_summary.main()
        out = capsys.readouterr().out
        assert "COVERAGE STALE/MISSING" not in out


def _completed(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    """A `subprocess.CompletedProcess` stub for monkeypatching `subprocess.run`."""
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


# frob:ticket T-2677
class TestResolveRepoRoot:
    """`fleet_status._resolve_repo_root` -- REPO must resolve to the SHARED
    primary checkout regardless of which linked worktree the script runs
    from (T-2677: `__file__`-derived resolution silently reported 0 live
    leases fleet-wide when run from inside a worktree, because a
    worktree's own `.git` is a FILE, not a directory)."""

    def _init_repo(self, root: Path) -> None:
        _run_git(["init", "-q", "-b", "main"], root)
        _run_git(["config", "user.email", "test@example.com"], root)
        _run_git(["config", "user.name", "Test"], root)
        (root / "README.md").write_text("x\n")
        _run_git(["add", "-A"], root)
        _run_git(["commit", "-q", "-m", "c1"], root)

    def test_positive_control_matches_primary_checkout(self, tmp_path: Path) -> None:
        """The exact real-world shape T-2677 measured: resolving from
        inside a linked worktree must return the SAME root as resolving
        from the primary checkout itself, for the same real repo.
        frob:tests scripts/fleet_status.py::_resolve_repo_root"""
        repo = tmp_path / "repo"
        repo.mkdir()
        self._init_repo(repo)
        worktree = tmp_path / "wt"
        _run_git(["worktree", "add", "-q", "-b", "wt-branch", str(worktree)], repo)

        from_primary = fleet_status._resolve_repo_root(repo)
        from_worktree = fleet_status._resolve_repo_root(worktree)

        assert from_primary.resolve() == repo.resolve()
        assert from_worktree.resolve() == repo.resolve()
        assert from_worktree.resolve() == from_primary.resolve()

    def test_falls_back_when_not_a_git_checkout(self, tmp_path: Path) -> None:
        """Outside any git checkout (git itself unavailable/refuses),
        the `__file__`-derived fallback is returned rather than raising.
        frob:tests scripts/fleet_status.py::_resolve_repo_root"""
        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        result = fleet_status._resolve_repo_root(not_a_repo)
        assert result == not_a_repo


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

    def test_phantom_modified_entry_dropped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2586: a bare 'M' status whose content-comparing `git diff --stat
        HEAD` comes back empty is a stat-shortcut phantom (CRLF/mtime
        churn with no logical change) and must NOT be reported dirty."""

        def _fake_run(args, **_k):  # noqa: ANN001
            if "status" in args:
                return _completed("M rapid-debt.jsonl\n")
            if "diff" in args:
                return _completed("")  # no real content difference
            return _completed("")

        monkeypatch.setattr(subprocess, "run", _fake_run)
        assert fleet_status.root_dirt() == []

    def test_genuine_modified_entry_kept(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """T-2586: a bare 'M' status whose `git diff --stat HEAD` DOES show
        a real difference must still be reported dirty -- the positive
        control that proves this is content confirmation, not a blanket
        suppression of the 'M' status class."""

        def _fake_run(args, **_k):  # noqa: ANN001
            if "status" in args:
                return _completed("M rapid-debt.jsonl\n")
            if "diff" in args:
                return _completed(" rapid-debt.jsonl | 1 +\n 1 file changed\n")
            return _completed("")

        monkeypatch.setattr(subprocess, "run", _fake_run)
        assert fleet_status.root_dirt() == ["M rapid-debt.jsonl"]

    def test_untracked_entry_never_reverified(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2586: an untracked ('??') path is never a stat-shortcut
        candidate -- it must be reported dirty without ever calling
        `git diff` to confirm it (untracked residue, e.g. from a killed
        retry loop, has no HEAD blob to diff against in the first
        place)."""
        calls: list[list[str]] = []

        def _fake_run(args, **_k):  # noqa: ANN001
            calls.append(args)
            if "status" in args:
                return _completed("?? stray-file.txt\n")
            return _completed("")

        monkeypatch.setattr(subprocess, "run", _fake_run)
        assert fleet_status.root_dirt() == ["?? stray-file.txt"]
        assert not any("diff" in c for c in calls), (
            "an untracked entry must never trigger a content re-verification call"
        )


class TestLeases:
    """`fleet_status.leases`."""

    def test_reads_lease_records(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every `*.json` lease file under LEASES is parsed as a record."""
        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        (leases_dir / "T-0001.json").write_text(
            json.dumps({"ticket_id": "T-0001", "worktree": "/x"}), encoding="utf-8"
        )
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)
        assert fleet_status.leases() == [{"ticket_id": "T-0001", "worktree": "/x"}]

    def test_no_lease_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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


class TestInProgressTicketScopeLeases:
    """`fleet_status.in_progress_ticket_scope_leases` (T-2651)."""

    @staticmethod
    def _write_ticket(
        tickets_dir: Path, ticket_id: str, state: str, scope: list[str]
    ) -> None:
        scope_block = "\n".join(f"- {item}" for item in scope)
        text = (
            "---\n"
            f"id: {ticket_id}\n"
            "title: fixture\n"
            f"state: {state}\n"
            "kind: bug\n"
            "scope:\n"
            f"{scope_block}\n"
            "---\n"
        )
        ticket_dir = tickets_dir / ticket_id
        ticket_dir.mkdir(parents=True)
        (ticket_dir / "ticket.md").write_text(text, encoding="utf-8")

    def test_no_worktree_flagged_as_leak(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An in-progress ticket with declared scope and NO resolvable
        worktree (no lease file, no scope-correlated worktree) appears,
        flagged `leaked=True` -- the missing case T-2651 exists to catch:
        T-2377 sat in-progress for nine hours after its worktree was
        removed and was invisible to the old, file-based reporter."""
        tickets_dir = tmp_path / "tickets"
        self._write_ticket(tickets_dir, "T-0001", "in-progress", ["src/a.py"])
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "no-leases")
        monkeypatch.setattr(fleet_status, "WORKTREES", tmp_path / "no-worktrees")
        entries = fleet_status.in_progress_ticket_scope_leases()
        assert entries == [
            {
                "ticket_id": "T-0001",
                "scope": ["src/a.py"],
                "worktree": None,
                "leaked": True,
            }
        ]

    def test_live_worktree_named_not_leaked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An in-progress ticket whose lease file still resolves to a
        live worktree directory is named, not leaked -- the unchanged
        case: today's behavior for a healthy lease stays exactly as it
        was."""
        tickets_dir = tmp_path / "tickets"
        self._write_ticket(tickets_dir, "T-0002", "in-progress", ["src/b.py"])
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)

        worktrees_dir = tmp_path / "worktrees"
        live_wt = worktrees_dir / "t-0002"
        live_wt.mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        (leases_dir / "T-0002.json").write_text(
            json.dumps({"ticket_id": "T-0002", "worktree": str(live_wt)}),
            encoding="utf-8",
        )
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)

        entries = fleet_status.in_progress_ticket_scope_leases()
        assert entries == [
            {
                "ticket_id": "T-0002",
                "scope": ["src/b.py"],
                "worktree": "t-0002",
                "leaked": False,
            }
        ]

    def test_queued_ticket_excluded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A QUEUED ticket's declared scope never appears -- a lease binds
        only at in-progress (T-0453); reporting queued scopes as leases
        would make the list useless in the opposite direction."""
        tickets_dir = tmp_path / "tickets"
        self._write_ticket(tickets_dir, "T-0003", "queued", ["src/c.py"])
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "no-leases")
        monkeypatch.setattr(fleet_status, "WORKTREES", tmp_path / "no-worktrees")
        assert fleet_status.in_progress_ticket_scope_leases() == []


# frob:ticket T-2654
class TestBlockedInProgressLeases:
    """`fleet_status.blocked_in_progress_leases` (T-2654): an in-progress
    ticket that is also `blocked_by` an open blocker cannot proceed, so
    any lease it holds is pure waste -- the T-2377 shape, detectable
    without waiting for its worktree to vanish."""

    # frob:ticket T-2654
    def test_in_progress_with_open_blocker_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The positive control: in-progress + blocked_by a still-open
        (queued) blocker is flagged, naming the open blocker id."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(tickets_dir, "T-2568", state="queued")
        _write_ticket(
            tickets_dir, "T-2377", state="in-progress", blocked_by=("T-2568",)
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        entries = fleet_status.blocked_in_progress_leases()
        assert entries == [{"ticket_id": "T-2377", "open_blockers": ["T-2568"]}]

    # frob:ticket T-2654
    def test_in_progress_with_no_blockers_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Negative control: an in-progress ticket with NO `blocked_by`
        at all is not flagged -- without this, every in-progress ticket
        would read as flagged."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(tickets_dir, "T-0010", state="in-progress")
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        assert fleet_status.blocked_in_progress_leases() == []

    # frob:ticket T-2654
    def test_in_progress_with_only_terminal_blockers_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Negative control: an in-progress ticket whose only blocker is
        `done` is not flagged -- a resolved blocker must not read as
        still holding the lease hostage."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(tickets_dir, "T-0011", state="done")
        _write_ticket(
            tickets_dir, "T-0012", state="in-progress", blocked_by=("T-0011",)
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        assert fleet_status.blocked_in_progress_leases() == []

    # frob:ticket T-2654
    def test_queued_ticket_with_open_blocker_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Negative control: a QUEUED ticket blocked by an open blocker
        is never flagged -- a lease binds only at in-progress (T-0453),
        so a queued-and-blocked ticket holds no lease to waste."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(tickets_dir, "T-0013", state="queued")
        _write_ticket(tickets_dir, "T-0014", state="queued", blocked_by=("T-0013",))
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        assert fleet_status.blocked_in_progress_leases() == []


class TestWorktrees:
    """`fleet_status.worktrees`."""

    def test_reports_idle_age(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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

    def test_no_worktree_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing worktrees directory returns an empty list, not an error."""
        monkeypatch.setattr(fleet_status, "WORKTREES", tmp_path / "does-not-exist")
        assert fleet_status.worktrees(idle_seconds=100) == []


# frob:ticket T-2599
# frob:ticket T-2755
class TestWorktreeContentClassification:
    """`fleet_status.worktree_content_classification` (T-2599): the
    content-presence test that replaces the three measured-wrong tests
    (`git log main..HEAD` commit count, `git diff --stat` size, and a
    raw insertion count with no direction check)."""

    def _fake_git(self, diff_by_args: dict, show_by_path: dict):  # noqa: ANN001, ANN201
        """A `_git` stand-in keyed on the exact argv this module calls
        with -- `("diff", "main", "HEAD", "--", ...)` and
        `("show", "main:<path>")` are the only two shapes
        `worktree_content_classification` issues."""

        def fake(args: list[str], cwd: Path) -> str:  # noqa: ARG001
            if args[0] == "diff":
                return diff_by_args.get(tuple(args), "")
            if args[0] == "show":
                return show_by_path.get(args[1], "")
            return ""

        return fake

    def test_stranded_new_content_not_on_main(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def brand_new():\n"
        )
        monkeypatch.setattr(
            fleet_status,
            "_git",
            self._fake_git(
                {diff_args: diff_text}, {"main:src/x.py": "def old():\n    pass\n"}
            ),
        )
        verdict, samples = fleet_status.worktree_content_classification(tmp_path)
        assert verdict == "STRANDED"
        assert any("brand_new" in s for s in samples)

    def test_stale_when_content_fully_landed_despite_many_commits(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The failure mode `git log main..HEAD` fell into: land SQUASHES,
        so a worktree whose content fully landed can still show a big
        `main..HEAD` diff in raw form, but every `+` line's text is
        already present on main -- not stranded.
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def landed():\n"
        monkeypatch.setattr(
            fleet_status,
            "_git",
            self._fake_git(
                {diff_args: diff_text}, {"main:src/x.py": "def landed():\n    pass\n"}
            ),
        )
        verdict, samples = fleet_status.worktree_content_classification(tmp_path)
        assert verdict == "STALE"
        assert samples == []

    def test_stale_when_only_behind_main(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty restricted diff (the worktree is purely behind, or the
        diff is entirely outside src/tests/docs/scripts) is STALE, never
        STRANDED. frob:tests scripts/fleet_status.py::worktree_content_classification"""
        monkeypatch.setattr(fleet_status, "_git", self._fake_git({}, {}))
        verdict, samples = fleet_status.worktree_content_classification(tmp_path)
        assert verdict == "STALE"
        assert samples == []

    # frob:ticket T-2755
    def test_active_ticket_never_stranded_or_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A worktree whose branch resolves to a NON-terminal ticket is
        ACTIVE regardless of its diff -- the content test is never even
        run (a stranded-content-shaped diff here would otherwise read
        STRANDED). frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def brand_new():\n"
        )
        monkeypatch.setattr(
            fleet_status, "_git", self._fake_git({diff_args: diff_text}, {})
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda ticket_id: {"state": "in-progress"},
        )
        verdict, samples = fleet_status.worktree_content_classification(
            tmp_path, ticket_ids=["T-2599"]
        )
        assert verdict == "ACTIVE"
        assert samples == []

    # frob:ticket T-2625
    # frob:ticket T-2755
    def test_queued_ticket_with_live_lease_still_active(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2625 positive control: a `queued` ticket that DOES hold a
        live lease record still reads ACTIVE unconditionally -- ACTIVE
        stays the safe direction for anything actually claimed, even in
        the unusual state where a lease outlives a state write."""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def brand_new():\n"
        )
        monkeypatch.setattr(
            fleet_status, "_git", self._fake_git({diff_args: diff_text}, {})
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda ticket_id: {"state": "queued"},
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_lease",
            lambda ticket_id: {"ticket_id": ticket_id, "worktree": "/w/t-2625"},
        )
        verdict, samples = fleet_status.worktree_content_classification(
            tmp_path, ticket_ids=["T-2625"]
        )
        assert verdict == "ACTIVE"
        assert samples == []

    # frob:ticket T-2625
    # frob:ticket T-2755
    def test_queued_ticket_with_no_lease_falls_through_to_content_test(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2625 negative control (the ticket's own measured instance):
        a `queued` ticket with NO lease record anywhere is NOT
        automatically ACTIVE -- it falls through to the ordinary content
        test, which here reports STALE for an empty diff. Without this
        fix, `t-1599`'s queued-with-no-lease shape would read identically
        to a genuinely in-progress worktree."""
        monkeypatch.setattr(fleet_status, "_git", self._fake_git({}, {}))
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda ticket_id: {"state": "queued"},
        )
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda ticket_id: None)
        verdict, samples = fleet_status.worktree_content_classification(
            tmp_path, ticket_ids=["T-1599"]
        )
        assert verdict == "STALE"
        assert samples == []

    # frob:ticket T-2755
    def test_stale_when_terminal_ticket_land_commit_is_ancestor_of_main(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2617: a terminal ticket whose recorded `land_commit` IS an
        ancestor of main is STALE even though its diff LOOKS
        stranded-shaped (new content with no counterpart line on main by
        exact text) -- the real failure mode T-2617 measured: `t-2576`/
        `t-2593` both landed, but the superseding code renamed the
        symbols their own diffs added, so exact-line-text matching alone
        misreads them as STRANDED. `land_commit`-ancestry is the precise
        signal that overrides the diff-shape guess entirely.
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n"
            "+_write_baseline(root, fresh, actual_head)\n"
        )
        monkeypatch.setattr(
            fleet_status, "_git", self._fake_git({diff_args: diff_text}, {})
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda ticket_id: {"state": "done", "land_commit": "deadbeef"},
        )
        monkeypatch.setattr(
            fleet_status, "_is_ancestor_of_main", lambda commit, path: True
        )
        verdict, samples = fleet_status.worktree_content_classification(
            tmp_path, ticket_ids=["T-2576"]
        )
        assert verdict == "STALE"
        assert samples == []

    # frob:ticket T-2755
    def test_stranded_survives_terminal_ticket_with_unlanded_land_commit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A terminal ticket whose `land_commit` is NOT an ancestor of main
        (dangling/garbage-collected sha, or a ledger edited by hand) falls
        through to the ordinary content test instead of being trusted
        blindly. frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def brand_new():\n"
        )
        monkeypatch.setattr(
            fleet_status,
            "_git",
            self._fake_git(
                {diff_args: diff_text}, {"main:src/x.py": "def old():\n    pass\n"}
            ),
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda ticket_id: {"state": "done", "land_commit": "deadbeef"},
        )
        monkeypatch.setattr(
            fleet_status, "_is_ancestor_of_main", lambda commit, path: False
        )
        verdict, samples = fleet_status.worktree_content_classification(
            tmp_path, ticket_ids=["T-2576"]
        )
        assert verdict == "STRANDED"
        assert any("brand_new" in s for s in samples)

    def test_stale_when_deletion_dominant(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2617: an ad-hoc-named worktree (no resolvable ticket, so no
        `land_commit` to consult) whose diff is overwhelmingly deletion-
        side is STALE -- the `gate-internals` shape T-2617 measured
        (110259 deletions against 12618 insertions, ratio ~8.7), detected
        by magnitude since there is no ticket to check ancestry against.
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        numstat_args = (
            "diff",
            "--numstat",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def renamed_form():\n"
        )
        numstat_text = "10\t100\tsrc/x.py\n"

        def fake(args: list[str], cwd: Path) -> str:  # noqa: ARG001, ANN001
            if tuple(args) == numstat_args:
                return numstat_text
            if tuple(args) == diff_args:
                return diff_text
            if args and args[0] == "show":
                return ""
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake)
        verdict, samples = fleet_status.worktree_content_classification(tmp_path)
        assert verdict == "STALE"
        assert samples == []

    def test_stranded_survives_a_small_mostly_additive_diff(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The deliberately-constructed T-2617 positive control: an
        ad-hoc-named worktree whose diff is almost entirely additions
        (no deletion-dominant shape to short-circuit on) with a symbol
        genuinely absent from main is still STRANDED -- proves the
        deletion-ratio fallback does not degrade into "everything STALE".
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        numstat_args = (
            "diff",
            "--numstat",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def never_landed():\n"
        )
        numstat_text = "1\t0\tsrc/x.py\n"

        def fake(args: list[str], cwd: Path) -> str:  # noqa: ARG001, ANN001
            if tuple(args) == numstat_args:
                return numstat_text
            if tuple(args) == diff_args:
                return diff_text
            if args and args[0] == "show" and args[1] == "main:src/x.py":
                return "def old():\n    pass\n"
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake)
        verdict, samples = fleet_status.worktree_content_classification(tmp_path)
        assert verdict == "STRANDED"
        assert any("never_landed" in s for s in samples)


def _run_git(args: list[str], cwd: Path) -> str:
    """Run real `git` (no mock) for `TestWorktreeContentClassificationLiveGit`'s
    fixture setup, raising on any non-zero exit -- fixture-building code
    should fail loudly, unlike `fleet_status._git`'s own defensive `""`
    return."""
    done = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


# frob:ticket T-2755
# frob:waive WIRE001 reason="private test-fixture helper used only by this file's own \
# tests -- no production caller to wire it to by design" permanent="true"
def _init_bare_repo(root: Path) -> None:
    """A bare `git init -b main` plus committer identity for `_run_git`-
    based live-git fixtures -- module-level, replacing THREE identical
    private per-class `_init_repo(self, root)` methods
    (`TestWorktreeContentClassificationLiveGit`, `TestInProgressTicket
    ScopeLeasesLiveGit`, and this ticket's own new `TestWorktreeStarted
    TicketIds`) that all carried the exact same 3-line body -- T-2755
    consolidates them into the one home NO DUPLICATION calls for, rather
    than adding a fourth copy alongside the other two. `TestResolveRepo
    Root._init_repo` is NOT one of the three: it also commits a README,
    a genuinely different fixture shape, so it stays its own method."""
    _run_git(["init", "-q", "-b", "main"], root)
    _run_git(["config", "user.email", "test@example.com"], root)
    _run_git(["config", "user.name", "Test"], root)


# frob:ticket T-2755
class TestWorktreeStartedTicketIds:
    """T-2755: `_worktree_started_ticket_ids` reads back EVERY ticket id
    a worktree's own unlanded history (`main..HEAD`) structurally
    started, with no assumption about the worktree's directory NAME --
    the reverse direction of T-2747's `_worktree_started_ticket` (which
    checks one candidate id) and the fix for `worktree_content_
    classification`'s own naming-convention short-circuit (T-2599's
    `_worktree_ticket_id`, a `t-<id>`-only match), which silently
    resolved to `None` for most of this fleet's real worktree names."""

    # frob:ticket T-2755
    def test_non_conventionally_named_worktree_resolves(self, tmp_path: Path) -> None:
        """T-2755 must-now-fire: a worktree named after its SUBJECT
        (`waive-liveness`, T-2740's own real name per T-2747's docstring)
        -- `_worktree_ticket_id("waive-liveness")` returns `None` (no
        `t-<id>` match), but the structural resolver still finds the
        started id from the worktree's own history.
        frob:tests scripts/fleet_status.py::_worktree_started_ticket_ids"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        (repo / "x.txt").write_text("x\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1"], repo)

        worktree = tmp_path / "waive-liveness"
        _run_git(["worktree", "add", "-q", "-b", "waive-liveness", str(worktree)], repo)
        (worktree / "x.txt").write_text("x\nchanged\n")
        _run_git(["add", "-A"], worktree)
        _run_git(
            ["commit", "-q", "-m", "chore(tickets): record T-2740 start transition"],
            worktree,
        )

        assert fleet_status._worktree_started_ticket_ids(worktree) == ["T-2740"]
        assert fleet_status._worktree_ticket_id("waive-liveness") is None

    # frob:ticket T-2755
    def test_no_start_transition_commits_resolves_empty(self, tmp_path: Path) -> None:
        """Negative control: a worktree with unlanded commits but NONE
        of them the canonical start-transition subject resolves to `[]`,
        never force-matched to a ticket id it never structurally started.
        frob:tests scripts/fleet_status.py::_worktree_started_ticket_ids"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        (repo / "x.txt").write_text("x\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1"], repo)

        worktree = tmp_path / "scratch-experiment"
        _run_git(
            ["worktree", "add", "-q", "-b", "scratch-experiment", str(worktree)], repo
        )
        (worktree / "x.txt").write_text("x\nchanged\n")
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: unrelated change"], worktree)

        assert fleet_status._worktree_started_ticket_ids(worktree) == []

    # frob:ticket T-2755
    def test_series_worktree_resolves_every_started_id(self, tmp_path: Path) -> None:
        """T-2755 must-now-fire: a grouped-dispatch series worktree
        (`t2763-t2359`-shaped: named for one ticket, holding several)
        structurally started TWO ids -- both resolve, not just the one
        embedded in the directory name.
        frob:tests scripts/fleet_status.py::_worktree_started_ticket_ids"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        (repo / "x.txt").write_text("x\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1"], repo)

        worktree = tmp_path / "t2763-t2359"
        _run_git(["worktree", "add", "-q", "-b", "t2763-t2359", str(worktree)], repo)
        (worktree / "x.txt").write_text("x\nchanged once\n")
        _run_git(["add", "-A"], worktree)
        _run_git(
            ["commit", "-q", "-m", "chore(tickets): record T-2763 start transition"],
            worktree,
        )
        (worktree / "x.txt").write_text("x\nchanged once\nchanged twice\n")
        _run_git(["add", "-A"], worktree)
        _run_git(
            ["commit", "-q", "-m", "chore(tickets): record T-2359 start transition"],
            worktree,
        )

        assert fleet_status._worktree_started_ticket_ids(worktree) == [
            "T-2359",
            "T-2763",
        ]


# frob:ticket T-2755
class TestWorktreeContentClassificationLiveGit:
    """T-2617: `worktree_content_classification` run UNMOCKED against a
    real git repository built from real commits -- `_git` itself is not
    monkeypatched here, only `fleet_status.REPO` (so `ticket_frontmatter_
    on_main`'s ticket-ledger lookups resolve against the fixture repo
    instead of this actual project). T-2617's own root cause was that
    `TestWorktreeContentClassification`'s string-fixture mocks never
    constructed the SUPERSEDED-symbol case (a function renamed by the
    code that replaced it has no byte-identical counterpart line, so the
    old exact-line-text check misread real landed work as stranded) --
    these tests reproduce that shape with genuine `git diff`/`git show`/
    `git merge-base` output, not hand-written diff text, closing exactly
    the gap T-2617 found."""

    # frob:ticket T-2755
    def test_superseded_symbol_with_landed_terminal_ticket_is_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The exact real-data shape T-2617 measured: `t-2576`'s worktree
        carries `_write_baseline(...)`, main's current file carries
        `_write_baseline_cas(...)` instead -- no byte-identical line in
        common, but the ticket is `done` and its `land_commit` IS an
        ancestor of main, so the correct verdict is STALE.
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "x.py").write_text(
            "def _write_baseline(root, fresh, actual_head):\n    pass\n"
        )
        tdir = repo / "tickets" / "T-9001"
        tdir.mkdir(parents=True)
        (tdir / "ticket.md").write_text("---\nid: T-9001\nstate: queued\n---\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: original _write_baseline"], repo)

        worktree = tmp_path / "t-9001"
        _run_git(["worktree", "add", "-q", "-b", "t-9001", str(worktree)], repo)

        (src / "x.py").write_text(
            "def _write_baseline_cas(root, fresh, actual_head):\n    pass\n"
        )
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c2: supersede with _write_baseline_cas"], repo)
        land_sha = _run_git(["rev-parse", "HEAD"], repo)

        (tdir / "ticket.md").write_text(
            f"---\nid: T-9001\nstate: done\nland_commit: {land_sha}\n---\n"
        )
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c3: mark T-9001 done"], repo)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        verdict, samples = fleet_status.worktree_content_classification(
            worktree, ticket_ids=["T-9001"]
        )
        assert verdict == "STALE"
        assert samples == []

    def test_genuinely_new_symbol_absent_from_main_is_stranded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2617's mandatory deliberately-constructed positive control:
        an ad-hoc-named worktree (no resolvable ticket) holding a symbol
        that never existed on main at all, with a mostly-additive diff
        (no deletion-dominant shape to short-circuit on), is STRANDED --
        proves the T-2617 fix does not degrade into labelling everything
        STALE. frob:tests scripts/fleet_status.py::worktree_content_classification"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "x.py").write_text("def existing():\n    pass\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() only"], repo)

        worktree = tmp_path / "adhoc-experiment"
        _run_git(
            ["worktree", "add", "-q", "-b", "adhoc-experiment", str(worktree)], repo
        )
        (worktree / "src" / "x.py").write_text(
            "def existing():\n    pass\n\n\ndef never_landed_anywhere():\n    return 1\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: add never_landed_anywhere"], worktree)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        verdict, samples = fleet_status.worktree_content_classification(worktree)
        assert verdict == "STRANDED"
        assert any("never_landed_anywhere" in s for s in samples)

    def test_far_behind_main_with_no_ticket_is_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2617's other real-data shape: `gate-internals` -- an ad-hoc
        long-idle worktree with no resolvable ticket, whose diff is
        overwhelmingly deletion-dominated because main simply moved on.
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        original = "\n".join(f"def fn_{i}():\n    pass\n" for i in range(40))
        (src / "x.py").write_text(original)
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: 40 functions"], repo)

        worktree = tmp_path / "gate-internals"
        _run_git(["worktree", "add", "-q", "-b", "gate-internals", str(worktree)], repo)
        # worktree adds one small tweak of its own and never syncs again
        (worktree / "src" / "x.py").write_text(
            original + "\ndef fn_extra_local():\n    pass\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: small local addition"], worktree)

        # main meanwhile grows a lot (the original 40 functions are left
        # untouched -- deletions here come from NEW main-side content the
        # worktree never picked up, the real "far behind" shape, not a
        # rename/rewrite of shared content)
        grown = (
            original
            + "\n"
            + "\n".join(
                f"def fn_new_{i}():\n    pass\n    pass\n    pass\n" for i in range(60)
            )
        )
        (src / "x.py").write_text(grown)
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c2: main grows a lot"], repo)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        verdict, samples = fleet_status.worktree_content_classification(worktree)
        assert verdict == "STALE"
        assert samples == []

    # frob:ticket T-2625
    # frob:ticket T-2755
    def test_queued_ticket_no_lease_falls_through_to_real_content_test(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2625's own measured shape, reproduced with real git state
        (not a string-fixture mock, per the T-2617 precedent this test
        class exists to hold to): a `queued` ticket with genuinely
        stranded content and NO lease file anywhere falls through the
        (now-conditional) ACTIVE short-circuit into the real, unmocked
        `git diff`/`git show` content test below it, which correctly
        reports STRANDED for content absent from main -- proving the fix
        does not just change a state-comparison in isolation, it changes
        what the REAL classifier does end to end for T-1599's exact
        shape (queued, no lease, some local diff)."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "x.py").write_text("def existing():\n    pass\n")
        tdir = repo / "tickets" / "T-1599"
        tdir.mkdir(parents=True)
        (tdir / "ticket.md").write_text("---\nid: T-1599\nstate: queued\n---\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() plus queued ticket"], repo)

        worktree = tmp_path / "t-1599"
        _run_git(["worktree", "add", "-q", "-b", "t-1599", str(worktree)], repo)
        (worktree / "src" / "x.py").write_text(
            "def existing():\n    pass\n\n\ndef never_landed_anywhere():\n    return 1\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: add never_landed_anywhere"], worktree)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        # No lease file anywhere for T-1599 -- point LEASES at an empty
        # directory so this does not accidentally read this actual
        # project's own real .git/frob-leases/ (LEASES is a module-level
        # constant fixed at import time from the REAL REPO, not
        # re-derived from the patched REPO above).
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "no-leases")
        verdict, samples = fleet_status.worktree_content_classification(
            worktree, ticket_ids=["T-1599"]
        )
        assert verdict == "STRANDED"
        assert any("never_landed_anywhere" in s for s in samples)

    # frob:ticket T-2755
    def test_non_conventionally_named_worktree_classifies_active_via_structural_ids(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2755 must-now-fire, end to end: a subject-named worktree
        (`waive-liveness`-shaped) holding an in-progress ticket must
        classify ACTIVE when its ids are resolved structurally
        (`_worktree_started_ticket_ids`) instead of via the old `t-<id>`
        naming convention (`_worktree_ticket_id("waive-liveness")` is
        `None`, which is exactly why this used to fall through to the
        raw content diff and could misreport STRANDED/STALE for
        genuinely active work).
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "x.py").write_text("def existing():\n    pass\n")
        tdir = repo / "tickets" / "T-2740"
        tdir.mkdir(parents=True)
        (tdir / "ticket.md").write_text("---\nid: T-2740\nstate: in-progress\n---\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() plus in-progress ticket"], repo)

        worktree = tmp_path / "waive-liveness"
        _run_git(["worktree", "add", "-q", "-b", "waive-liveness", str(worktree)], repo)
        _run_git(
            [
                "commit",
                "-q",
                "--allow-empty",
                "-m",
                "chore(tickets): record T-2740 start transition",
            ],
            worktree,
        )
        (worktree / "src" / "x.py").write_text(
            "def existing():\n    pass\n\n\ndef in_progress_work():\n    return 1\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: work in progress on T-2740"], worktree)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        verdict, samples = fleet_status.worktree_content_classification(
            worktree,
            ticket_ids=fleet_status._worktree_started_ticket_ids(worktree),
        )
        assert verdict == "ACTIVE"
        assert samples == []

    # frob:ticket T-2755
    def test_worktree_with_genuinely_no_ticket_is_not_force_matched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2755 negative control: a worktree that never ran `frob
        ticket start`/`work` at all (no start-transition commit anywhere
        in its history) must resolve `ticket_ids=[]` from the structural
        scan and fall through to the ordinary content test -- never
        force-matched to a ticket it never started, and never crashes on
        an empty id list.
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "x.py").write_text("def existing():\n    pass\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() only"], repo)

        worktree = tmp_path / "no-ticket-scratch"
        _run_git(
            ["worktree", "add", "-q", "-b", "no-ticket-scratch", str(worktree)], repo
        )
        (worktree / "src" / "x.py").write_text(
            "def existing():\n    pass\n\n\ndef scratch_only():\n    return 1\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: scratch change, no ticket"], worktree)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        started = fleet_status._worktree_started_ticket_ids(worktree)
        assert started == []
        verdict, samples = fleet_status.worktree_content_classification(
            worktree, ticket_ids=started
        )
        assert verdict == "STRANDED"
        assert any("scratch_only" in s for s in samples)


# frob:ticket T-2665
class TestInProgressTicketScopeLeasesLiveGit:
    """T-2665: `in_progress_ticket_scope_leases`'s fallback (`_resolve_
    worktree_for_in_progress_ticket`'s `worktrees_touching_ticket` scan)
    run against a REAL `git worktree add`, not a string/JSON fixture --
    the T-2617 precedent this class follows: the measured incident was a
    ticket whose LEASE FILE had been removed (`.git/frob-leases/*.json`
    is unlinked opportunistically, per T-2651's own docstring) while a
    real `git worktree` for it still existed on disk with an unlanded
    commit. `TestInProgressTicketScopeLeases`'s own mocked tests cover
    the lease-file-present path faithfully, but never construct a real
    worktree at all, so they cannot tell a genuine fallback-scan success
    apart from a fixture that merely looks right."""

    def test_live_worktree_with_lease_file_removed_is_not_leaked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2665's own measured shape: T-2583 was `in-progress` with a
        real `git worktree` on branch `t-2583` and an unlanded commit
        touching its declared scope, but NO `.git/frob-leases/T-2583.json`
        (removed, whether by the T-2651-documented opportunistic unlink
        or by hand) -- the detector reported `[LEAK]` anyway. This
        reproduces that exact combination with real git state: a real
        worktree, a real commit inside it that touches the ticket's own
        scope file, and an EMPTY leases directory (no lease file for this
        ticket at all, not even a stale one)."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "a.py").write_text("def existing():\n    pass\n")
        tdir = repo / "tickets" / "T-2583"
        tdir.mkdir(parents=True)
        (tdir / "ticket.md").write_text(
            "---\nid: T-2583\nstate: in-progress\nscope:\n- src/a.py\n---\n"
        )
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() plus in-progress ticket"], repo)

        worktree = tmp_path / "t-2583"
        _run_git(["worktree", "add", "-q", "-b", "t-2583", str(worktree)], repo)
        (worktree / "src" / "a.py").write_text(
            "def existing():\n    pass\n\n\ndef fix_applied():\n    return 1\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: work in progress on T-2583"], worktree)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", repo / "tickets")
        monkeypatch.setattr(fleet_status, "WORKTREES", tmp_path)
        # No lease file anywhere for T-2583 -- the exact measured shape.
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "no-leases")

        entries = fleet_status.in_progress_ticket_scope_leases()
        assert entries == [
            {
                "ticket_id": "T-2583",
                "scope": ["src/a.py"],
                "worktree": "t-2583",
                "leaked": False,
            }
        ], (
            "a live worktree with an unlanded commit touching the "
            "ticket's own scope must resolve via the fallback scan and "
            "must NOT report leaked=True, even with no lease file at all"
        )

    def test_no_worktree_and_no_lease_is_still_leaked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Positive control (must-still-pass direction), same real-git
        harness: an in-progress ticket with NEITHER a lease file NOR any
        worktree at all is still reported `leaked=True` -- T-2377's own
        original shape, the reason this detector exists. Without this, a
        fix for the false-LEAK direction could silently regress into
        never reporting a real leak again."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "a.py").write_text("def existing():\n    pass\n")
        tdir = repo / "tickets" / "T-2377"
        tdir.mkdir(parents=True)
        (tdir / "ticket.md").write_text(
            "---\nid: T-2377\nstate: in-progress\nscope:\n- src/a.py\n---\n"
        )
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() plus in-progress ticket"], repo)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", repo / "tickets")
        monkeypatch.setattr(fleet_status, "WORKTREES", tmp_path / "no-worktrees")
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "no-leases")

        entries = fleet_status.in_progress_ticket_scope_leases()
        assert entries == [
            {
                "ticket_id": "T-2377",
                "scope": ["src/a.py"],
                "worktree": None,
                "leaked": True,
            }
        ]


class TestWorktreeTicketId:
    """`fleet_status._worktree_ticket_id` (T-2599)."""

    def test_ticket_named_worktree_resolves(self) -> None:
        """frob:tests scripts/fleet_status.py::_worktree_ticket_id"""
        assert fleet_status._worktree_ticket_id("t-2599") == "T-2599"

    def test_ad_hoc_named_worktree_resolves_to_none(self) -> None:
        """frob:tests scripts/fleet_status.py::_worktree_ticket_id"""
        assert fleet_status._worktree_ticket_id("dev-friction") is None


class TestTicketLease:
    """`fleet_status.ticket_lease` (T-2133)."""

    def test_reads_a_live_lease(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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

    def test_no_lease_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
            "land_commit": None,
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
            "land_commit": None,
        }

    def test_missing_ticket_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`git show` returning nothing (ticket absent on main) is None."""
        monkeypatch.setattr(fleet_status, "_git", lambda args, cwd: "")
        assert fleet_status.ticket_frontmatter_on_main("T-9999") is None

    # frob:ticket T-2449
    def test_falls_back_to_archive_when_active_ledger_has_no_such_ticket(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2449's own fix: the ACTIVE `tickets/<id>/ticket.md` path
        resolves to nothing (empty git show), so this must fall back to
        `tickets/archive/<id>/ticket.md` before giving up -- the exact
        shape a completed-and-archived blocker has. Confirms the SECOND
        `_git` call (not the first) is what supplies the archived text."""
        archived_text = "---\nid: T-1692\nstate: done\nland_commit: abc123\nscope:\n- src/a.py\n---\n"
        calls: list[list[str]] = []

        def fake_git(args: list[str], cwd) -> str:  # noqa: ANN001
            calls.append(args)
            if "tickets/archive/" in args[-1]:
                return archived_text
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        result = fleet_status.ticket_frontmatter_on_main("T-1692")
        assert result == {
            "state": "done",
            "scope": ["src/a.py"],
            "blocked_by": [],
            "land_commit": "abc123",
        }
        assert any("tickets/T-1692/ticket.md" in c[-1] for c in calls)
        assert any("tickets/archive/T-1692/ticket.md" in c[-1] for c in calls)


# frob:ticket T-2449
class TestClassifyBlockers:
    """`fleet_status._classify_blockers` (T-2449): the `main:`-committed
    resolver, archive-aware via `ticket_frontmatter_on_main`."""

    def test_done_blocker_is_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "done", "scope": [], "blocked_by": []},
        )
        open_ids, unresolved_ids = fleet_status._classify_blockers(["T-0001"])
        assert open_ids == []
        assert unresolved_ids == []

    def test_archived_done_blocker_is_closed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2449's own measured incident: a blocker that only resolves
        via the archive fallback (`ticket_frontmatter_on_main` handles
        that internally) must still classify as closed, not unresolved
        and not open."""
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "done", "scope": [], "blocked_by": []},
        )
        open_ids, unresolved_ids = fleet_status._classify_blockers(["T-1692", "T-1693"])
        assert open_ids == []
        assert unresolved_ids == []

    def test_in_progress_blocker_is_open(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """MUST-STILL-BLOCK control: a genuinely open blocker still reports
        open -- this fix must never simply stop checking blocked_by."""
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "in-progress", "scope": [], "blocked_by": []},
        )
        open_ids, unresolved_ids = fleet_status._classify_blockers(["T-0002"])
        assert open_ids == ["T-0002"]
        assert unresolved_ids == []

    def test_missing_blocker_is_unresolved_not_open(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Acceptance [2]: a blocker id that resolves nowhere is reported
        in its OWN list, distinct from a genuinely open one."""
        monkeypatch.setattr(
            fleet_status, "ticket_frontmatter_on_main", lambda tid: None
        )
        open_ids, unresolved_ids = fleet_status._classify_blockers(["T-9999"])
        assert open_ids == []
        assert unresolved_ids == ["T-9999"]


# frob:ticket T-2449
class TestClassifyBlockersLocal:
    """`fleet_status._classify_blockers_local` (T-2449): the local-disk
    twin used by `_rotting_entry` so NEEDS DISPATCH agrees with
    `ticket_readiness`."""

    def test_done_archived_blocker_is_closed(self, tmp_path: Path) -> None:
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir / "archive",
            "T-1692",
            state="done",
            priority="critical",
        )
        open_ids, unresolved_ids = fleet_status._classify_blockers_local(
            ["T-1692"], tickets_dir
        )
        assert open_ids == []
        assert unresolved_ids == []

    def test_queued_blocker_is_open(self, tmp_path: Path) -> None:
        tickets_dir = tmp_path / "tickets"
        _write_ticket(tickets_dir, "T-0002", state="queued", priority="high")
        open_ids, unresolved_ids = fleet_status._classify_blockers_local(
            ["T-0002"], tickets_dir
        )
        assert open_ids == ["T-0002"]
        assert unresolved_ids == []

    def test_missing_blocker_is_unresolved(self, tmp_path: Path) -> None:
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir(parents=True)
        open_ids, unresolved_ids = fleet_status._classify_blockers_local(
            ["T-9999"], tickets_dir
        )
        assert open_ids == []
        assert unresolved_ids == ["T-9999"]


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
        assert fleet_status.worktrees_touching_ticket("T-2114", ["src/a.py"]) == ["one"]

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

    # frob:ticket T-2747
    def test_non_conventionally_named_worktree_matches_via_start_transition(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2747 positive control 1: a worktree named after its SUBJECT
        (`waive-liveness`, the real T-2740 shape) rather than `t-<id>`
        still matches -- because its own `main..HEAD` history carries the
        start-transition commit `commit_start_transition` writes, the
        dispatch condition no longer depends on the directory name at
        all."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "waive-liveness").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        # Realistic per-commit shape (matches the real T-2740 measurement):
        # the start-transition commit and the real scope-touching commit
        # are TWO SEPARATE commits -- no single commit touches both
        # `tickets/T-2740/` and scope, so the OLD dual-correlation check
        # genuinely returns False here (proving this is a real repro, not
        # a mock coincidence): only the NEW started-ticket fast path can
        # see the scope-touching commit at all.
        def fake_git(args: list[str], cwd: Path) -> str:
            if args[0] == "log" and args[-1] == "--format=%s":
                return "chore(tickets): record T-2740 start transition"
            if args[0] == "log" and args[-1] == "tickets/T-2740/":
                return "aaa111"  # ledger-only bookkeeping commit
            if args[0] == "log":
                return "bbb222"  # the real, separate scope-touching commit
            if args[0] == "show":
                sha = args[-1]
                if sha == "aaa111":
                    return "tickets/T-2740/ticket.md"
                if sha == "bbb222":
                    return "src/a.py"
                return ""
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status.worktrees_touching_ticket("T-2740", ["src/a.py"]) == [
            "waive-liveness"
        ]

    # frob:ticket T-2747
    def test_series_worktree_matches_sibling_ticket_via_start_transition(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2747 positive control 2: a worktree named for ticket A
        (`t2738-t2737`, named after T-2738) that ALSO started sibling
        ticket B (T-2737, the standard series-dispatch pattern) resolves
        B too -- the real shape the old `t-<id>`-regex fast path could
        never see, since the name only ever resolves to one id."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "t2738-t2737").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        # Same realistic per-commit split as the sibling test above: the
        # T-2737 start-transition commit and its own real scope-touching
        # commit are separate commits, so the OLD dual-correlation check
        # (which the worktree's NAME resolves to T-2738, never T-2737)
        # genuinely cannot see T-2737 as reached here either way -- this
        # proves the NEW started-ticket path is what recovers it.
        def fake_git(args: list[str], cwd: Path) -> str:
            if args[0] == "log" and args[-1] == "--format=%s":
                return (
                    "chore(tickets): record T-2738 start transition\n"
                    "chore(tickets): record T-2737 start transition"
                )
            if args[0] == "log" and args[-1] == "tickets/T-2737/":
                return "ccc333"  # ledger-only bookkeeping commit
            if args[0] == "log":
                return "ddd444"  # the real, separate scope-touching commit
            if args[0] == "show":
                sha = args[-1]
                if sha == "ccc333":
                    return "tickets/T-2737/ticket.md"
                if sha == "ddd444":
                    return "src/b.py"
                return ""
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status.worktrees_touching_ticket("T-2737", ["src/b.py"]) == [
            "t2738-t2737"
        ]

    # frob:ticket T-2747
    def test_a_leaked_ticket_with_no_worktree_anywhere_still_reports_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2747 positive control 3 (the detector's purpose must
        survive): a ticket genuinely abandoned -- no worktree started it,
        no worktree touches its scope -- must still resolve to no hits at
        all, i.e. still read as a leak. Without this, the fix would have
        traded a false LEAK for a false LIVE, which is the more dangerous
        direction (a stranded lease would never get reclaimed)."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "unrelated").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        def fake_git(args: list[str], cwd: Path) -> str:
            if args[0] == "log" and args[-1] == "--format=%s":
                return "chore(tickets): record T-9999 start transition"
            if args[0] == "log":
                return ""
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status.worktrees_touching_ticket("T-2114", ["src/a.py"]) == []


class TestWorktreeStartedTicket:
    """`fleet_status._worktree_started_ticket` (T-2747)."""

    def test_true_when_start_transition_commit_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """frob:tests scripts/fleet_status.py::_worktree_started_ticket"""

        def fake_git(args: list[str], cwd: Path) -> str:
            return "chore(tickets): record T-2740 start transition"

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status._worktree_started_ticket(tmp_path, "T-2740") is True

    def test_false_when_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """frob:tests scripts/fleet_status.py::_worktree_started_ticket"""

        def fake_git(args: list[str], cwd: Path) -> str:
            return "some other commit subject"

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status._worktree_started_ticket(tmp_path, "T-2740") is False


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
        assert ("docs/modules/tickets.md", "docs/modules/tickets.md") in collisions[0][
            "overlapping_globs"
        ]

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
    """`fleet_status.land_process_rows` (T-2180, T-2475)."""

    def test_parses_matching_rows_and_skips_others(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Rows whose argv contains `ticket land` are parsed into
        structured dicts (pid, etimes, cputime, argv); the header line
        and rows for unrelated commands are skipped. `proc` is an
        isolated empty tmp dir (T-2475: `_pid_has_land_argv_tokens`
        cannot re-confirm a pid it has no `/proc/<pid>/cmdline` for, so
        it returns `None` and the row is kept on the text pre-filter
        alone) -- never the real host `/proc`, which would make this
        test's verdict depend on whatever pid 100 happens to be on
        whatever machine runs it."""
        proc = tmp_path / "proc"
        proc.mkdir()
        stdout = (
            "    PID  ETIMES     TIME COMMAND\n"
            "    100     300    00:10 /venv/bin/python -m frob ticket land "
            "--ticket T-1234\n"
            "    200      50    00:00 vim some_file.py\n"
        )
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(stdout))
        rows = fleet_status.land_process_rows(proc)
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

    # frob:ticket T-2475
    def test_watcher_pgrep_pattern_is_not_counted_as_a_land(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """T-2475's measured incident: a coordinator's own wait-loop
        shell running `pgrep -f "frob ticket land T-2408"` reads
        identically to a real land in `ps -eo args` TEXT (both contain
        the substring 'ticket land T-2408'), and was misreported as a
        live land (elapsed=306s, cpu=0s) after the real land had
        already finished. The watcher's `/proc/<pid>/cmdline` has
        `ticket`/`land` GLUED inside one single argv element (the
        quoted `-f` pattern), never as two separate elements -- this
        must be dropped, while a genuine land row (pid 101, `ticket`/
        `land` as separate argv elements) must survive alongside it."""
        proc = tmp_path / "proc"
        proc.mkdir()
        watcher = proc / "100"
        watcher.mkdir()
        (watcher / "cmdline").write_bytes(b"pgrep\x00-f\x00frob ticket land T-2408\x00")
        real_land = proc / "101"
        real_land.mkdir()
        (real_land / "cmdline").write_bytes(
            b"timeout\x00540\x00uv\x00run\x00frob\x00ticket\x00land\x00T-2408\x00"
            b"--worktree\x00/w\x00"
        )
        stdout = (
            "    PID  ETIMES     TIME COMMAND\n"
            "    100     306    00:00 bash -c pgrep -f frob ticket land T-2408\n"
            "    101     300    00:10 timeout 540 uv run frob ticket land "
            "T-2408 --worktree /w\n"
        )
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(stdout))
        rows = fleet_status.land_process_rows(proc)
        assert [r["pid"] for r in rows] == [101]


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
                    '| wc -l)" -eq 0 ]; do sleep 15; done'
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


def _write_proc_locks(proc: Path, lines: list[str]) -> None:
    """Fake `<proc>/locks` (T-3093) -- `_true_flock_holder_pid` reads
    this exact path."""
    proc.mkdir(parents=True, exist_ok=True)
    (proc / "locks").write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestTrueFlockHolderPid:
    """`fleet_status._true_flock_holder_pid` (T-3093): the true-holder-vs-
    waiter distinction, read from `/proc/locks` rather than fd-open
    membership."""

    def test_finds_the_true_holder(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid.test_finds_the_true_holder  # noqa: E501
        lock_path = tmp_path / "land.lock"
        lock_path.write_text("{}", encoding="utf-8")
        st = lock_path.stat()
        maj, minor = os.major(st.st_dev), os.minor(st.st_dev)
        proc = tmp_path / "proc"
        _write_proc_locks(
            proc,
            [f"1: FLOCK  ADVISORY  WRITE 555 {maj:02x}:{minor:02x}:{st.st_ino} 0 EOF"],
        )
        assert fleet_status._true_flock_holder_pid(lock_path, proc=proc) == (
            True,
            555,
        )

    def test_ignores_a_lock_on_a_different_inode(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid.test_ignores_a_lock_on_a_different_inode  # noqa: E501
        """A waiter that later acquires an UNRELATED file's lock must
        never be misread as this lock's holder."""
        lock_path = tmp_path / "land.lock"
        lock_path.write_text("{}", encoding="utf-8")
        st = lock_path.stat()
        maj, minor = os.major(st.st_dev), os.minor(st.st_dev)
        proc = tmp_path / "proc"
        _write_proc_locks(
            proc,
            [f"1: FLOCK  ADVISORY  WRITE 999 {maj:02x}:{minor:02x}:{st.st_ino + 1} 0 EOF"],
        )
        assert fleet_status._true_flock_holder_pid(lock_path, proc=proc) == (
            True,
            None,
        )

    def test_unreadable_proc_locks_is_indeterminate(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid.test_unreadable_proc_locks_is_indeterminate  # noqa: E501
        """T-3093's own explicit requirement: when `/proc/locks` cannot
        be read at all, this MUST say "not determinable", never guess a
        pid or silently claim "no holder"."""
        lock_path = tmp_path / "land.lock"
        lock_path.write_text("{}", encoding="utf-8")
        proc = tmp_path / "proc-does-not-exist"
        assert fleet_status._true_flock_holder_pid(lock_path, proc=proc) == (
            False,
            None,
        )

    def test_missing_lock_file_is_true_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestTrueFlockHolderPid.test_missing_lock_file_is_true_none  # noqa: E501
        proc = tmp_path / "proc"
        _write_proc_locks(proc, [])
        assert fleet_status._true_flock_holder_pid(
            tmp_path / "does-not-exist.lock", proc=proc
        ) == (True, None)


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
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [100])
        monkeypatch.setattr(
            fleet_status, "_true_flock_holder_pid", lambda lock_path: (True, 100)
        )
        monkeypatch.setattr(fleet_status, "host_load", lambda: (19.5, 10 * 1024 * 1024))
        monkeypatch.setattr(fleet_status, "leases", lambda: [{"ticket_id": "T-1"}])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 1)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "LANDS IN FLIGHT: 1" in out
        assert "T-1234" in out and "elapsed=300s" in out and "cpu=270s" in out
        assert "LAND LOCK: held by pid=100" in out
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
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
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
        monkeypatch.setattr(fleet_status, "orphaned_forkserver_count", lambda: None)
        monkeypatch.setattr(fleet_status, "concurrent_check_count", lambda: None)
        monkeypatch.setattr(
            fleet_status, "stale_forkserver_count", lambda **kwargs: None
        )
        monkeypatch.setattr(fleet_status, "forkserver_swap_held_kb", lambda: None)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "LANDS IN FLIGHT: 0" in out
        # T-2517: "stale" is now a legitimate word in the (separate,
        # forkserver-specific) STALE FORKSERVERS line -- this test only
        # cares that the LAND LOCK line itself never uses it.
        land_lock_line = next(
            line for line in out.splitlines() if line.startswith("LAND LOCK")
        )
        assert "stale" not in land_lock_line.lower()
        assert "no live holder" in out.lower()
        assert "normal resting state" in out.lower()
        assert "LOAD: unknown" in out

    def test_distinguishes_true_holder_from_waiters(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestPrintLandStatus.test_distinguishes_true_holder_from_waiters  # noqa: E501
        """T-3093 must-fire: one land running, two waiting -- the output
        must name the single true holder and count the waiters
        separately, never label all three "holder"."""
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(
            fleet_status, "land_lock_holder_pids", lambda root: [100, 200, 300]
        )
        monkeypatch.setattr(
            fleet_status, "_true_flock_holder_pid", lambda lock_path: (True, 100)
        )
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        monkeypatch.setattr(fleet_status, "swap_pressure", lambda: None)
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 0)
        monkeypatch.setattr(fleet_status, "orphaned_forkserver_count", lambda: None)
        monkeypatch.setattr(fleet_status, "concurrent_check_count", lambda: None)
        monkeypatch.setattr(
            fleet_status, "stale_forkserver_count", lambda **kwargs: None
        )
        monkeypatch.setattr(fleet_status, "forkserver_swap_held_kb", lambda: None)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        land_lock_line = next(
            line for line in out.splitlines() if line.startswith("LAND LOCK")
        )
        assert "held by pid=100" in land_lock_line
        assert "2 waiter(s)" in land_lock_line
        assert "200" in land_lock_line and "300" in land_lock_line

    def test_must_stay_quiet_single_holder_no_waiters_unchanged_meaning(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestPrintLandStatus.test_must_stay_quiet_single_holder_no_waiters_unchanged_meaning  # noqa: E501
        """T-3093 must-stay-quiet: a single land, no waiters -- the
        output's MEANING is unchanged (still names pid=100 as the
        holder, no waiter count printed)."""
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [100])
        monkeypatch.setattr(
            fleet_status, "_true_flock_holder_pid", lambda lock_path: (True, 100)
        )
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        monkeypatch.setattr(fleet_status, "swap_pressure", lambda: None)
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 0)
        monkeypatch.setattr(fleet_status, "orphaned_forkserver_count", lambda: None)
        monkeypatch.setattr(fleet_status, "concurrent_check_count", lambda: None)
        monkeypatch.setattr(
            fleet_status, "stale_forkserver_count", lambda **kwargs: None
        )
        monkeypatch.setattr(fleet_status, "forkserver_swap_held_kb", lambda: None)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        land_lock_line = next(
            line for line in out.splitlines() if line.startswith("LAND LOCK")
        )
        assert "held by pid=100" in land_lock_line
        assert "waiter" not in land_lock_line.lower()

    def test_indeterminate_true_holder_says_so_not_a_confident_number(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestPrintLandStatus.test_indeterminate_true_holder_says_so_not_a_confident_number  # noqa: E501
        """T-3093's own explicit requirement: when the true holder cannot
        be determined from /proc, say so -- never print the fd-open set
        under a "holder" label."""
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(
            fleet_status, "land_lock_holder_pids", lambda root: [100, 200]
        )
        monkeypatch.setattr(
            fleet_status, "_true_flock_holder_pid", lambda lock_path: (False, None)
        )
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        monkeypatch.setattr(fleet_status, "swap_pressure", lambda: None)
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 0)
        monkeypatch.setattr(fleet_status, "orphaned_forkserver_count", lambda: None)
        monkeypatch.setattr(fleet_status, "concurrent_check_count", lambda: None)
        monkeypatch.setattr(
            fleet_status, "stale_forkserver_count", lambda **kwargs: None
        )
        monkeypatch.setattr(fleet_status, "forkserver_swap_held_kb", lambda: None)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        land_lock_line = next(
            line for line in out.splitlines() if line.startswith("LAND LOCK")
        )
        assert "not determinable" in land_lock_line.lower()
        assert "held by pid=" not in land_lock_line

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

    # frob:ticket T-2443
    def test_orphaned_forkserver_count_printed_alongside_swap_guidance(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Acceptance [2]: orphaned forkservers present must show up in
        the same report as the swap-pressure guidance -- turning an
        unexplained '1 agent (SWAP ...)' clause into an actionable
        number."""
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [])
        monkeypatch.setattr(fleet_status, "host_load", lambda: (1.0, 1024 * 1024))
        monkeypatch.setattr(
            fleet_status, "swap_pressure", lambda: (2 * 1024 * 1024, 24 * 1024 * 1024)
        )
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "live_lease_count", lambda held: 0)
        monkeypatch.setattr(fleet_status, "orphaned_forkserver_count", lambda: 94)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "ORPHANED FORKSERVERS: 94 do not have a live" in out

    # frob:ticket T-2443
    def test_zero_orphaned_forkservers_prints_zero_not_omitted(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """MUST-STILL-PASS: a clean host (0 orphans) prints the line as
        '0', never omits it -- the same 'absence of data vs. a real zero'
        distinction `swap_pressure`/`host_load` already enforce."""
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
        monkeypatch.setattr(fleet_status, "land_lock_holder_pids", lambda root: [])
        monkeypatch.setattr(fleet_status, "host_load", lambda: None)
        monkeypatch.setattr(fleet_status, "swap_pressure", lambda: None)
        monkeypatch.setattr(fleet_status, "orphaned_forkserver_count", lambda: 0)
        fleet_status._print_land_status()
        out = capsys.readouterr().out
        assert "ORPHANED FORKSERVERS: 0" in out


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


# frob:ticket T-2443
class TestOrphanedForkserverCount:
    """`fleet_status.orphaned_forkserver_count` (T-2443, ancestry-walk fix
    T-2818)."""

    @staticmethod
    def _write_entry(proc: Path, pid: int, *, cmdline: bytes, ppid: int) -> None:
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(cmdline)
        (entry / "stat").write_text(f"{pid} (python3) S {ppid} {pid} 0 0 -1 0\n")

    @staticmethod
    def _write_live_check(proc: Path, pid: int, *, ppid: int = 1) -> None:
        """A live `frob check` process at `pid` -- no forkserver cmdline,
        so it never enters `_forkserver_snapshot`, but it DOES enter
        `_live_check_pids` and `_all_process_ppids` (T-2818), which is all
        an ancestry test needs of it."""
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(b"/x/.venv/bin/frob\x00check\x00")
        (entry / "stat").write_text(f"{pid} (frob) S {ppid} {pid} 0 0 -1 0\n")

    _FORKSERVER_CMDLINE = (
        b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
    )

    def test_counts_forkserver_reparented_to_init(self, tmp_path: Path) -> None:
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(proc, 4242, cmdline=self._FORKSERVER_CMDLINE, ppid=1)
        assert fleet_status.orphaned_forkserver_count(proc) == 1

    def test_ignores_forkserver_with_live_parent(self, tmp_path: Path) -> None:
        """A forkserver whose immediate parent is a genuinely LIVE `frob
        check` process (T-2818: ancestry, not one-level ppid==1, is the
        fix's own required semantics) must not be counted orphaned."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_live_check(proc, 999)
        self._write_entry(proc, 4242, cmdline=self._FORKSERVER_CMDLINE, ppid=999)
        assert fleet_status.orphaned_forkserver_count(proc) == 0

    def test_ignores_non_forkserver_processes(self, tmp_path: Path) -> None:
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(proc, 4242, cmdline=b"sleep\x00600\x00", ppid=1)
        assert fleet_status.orphaned_forkserver_count(proc) == 0

    def test_missing_proc_returns_none(self, tmp_path: Path) -> None:
        assert fleet_status.orphaned_forkserver_count(tmp_path / "no-proc") is None

    def test_two_level_chain_with_dead_root_is_orphaned(self, tmp_path: Path) -> None:
        """T-2818's own positive control, the case that failed before this
        fix: a forkserver (4242) whose parent is ANOTHER forkserver (5000)
        whose own originating check already died (reparented to init, no
        live check pid anywhere in the tree). The old one-level test read
        4242 as 'live-parented' because 5000 is alive; the ancestry walk
        must classify BOTH as orphaned."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(proc, 5000, cmdline=self._FORKSERVER_CMDLINE, ppid=1)
        self._write_entry(proc, 4242, cmdline=self._FORKSERVER_CMDLINE, ppid=5000)
        assert fleet_status.orphaned_forkserver_count(proc) == 2

    def test_deep_chain_under_a_live_check_is_not_orphaned(
        self, tmp_path: Path
    ) -> None:
        """T-2818's other positive control, the one that matters most: a
        forkserver several hops below a genuinely RUNNING check must never
        read as orphaned, at any depth -- getting this wrong reaps live
        workers mid-check."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_live_check(proc, 6000)
        self._write_entry(proc, 5000, cmdline=self._FORKSERVER_CMDLINE, ppid=6000)
        self._write_entry(proc, 4242, cmdline=self._FORKSERVER_CMDLINE, ppid=5000)
        assert fleet_status.orphaned_forkserver_count(proc) == 0

    def test_zero_forkservers_reports_zero(self, tmp_path: Path) -> None:
        """MUST-STILL-PASS: no forkservers at all (even with other, live,
        non-forkserver processes present) reports a clean `0`, never an
        error or `None`."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_live_check(proc, 100)
        assert fleet_status.orphaned_forkserver_count(proc) == 0


# frob:ticket T-2517
class TestStaleForkserverCount:
    """`fleet_status.stale_forkserver_count` (T-2517): idle+aged, not
    ancestry-based -- the signal `orphaned_forkserver_count` cannot see
    for a forkserver whose creating agent shell is still alive."""

    @staticmethod
    def _write_proc(proc: Path, *, uptime_s: float) -> None:
        proc.mkdir()
        proc.joinpath("uptime").write_text(f"{uptime_s} 0.0\n", encoding="utf-8")

    @staticmethod
    def _write_forkserver(
        proc: Path, pid: int, *, age_s: float, ppid: int = 999
    ) -> None:
        clk_tck = os.sysconf("SC_CLK_TCK")
        uptime_s = float(proc.joinpath("uptime").read_text(encoding="utf-8").split()[0])
        starttime_ticks = int((uptime_s - age_s) * clk_tck)
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(
            b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
        )
        stat_fields = ["S", str(ppid), str(pid), "0", "0", "-1", "0"]
        stat_fields += ["0"] * 12  # pad up through nice/num_threads/itrealvalue
        stat_fields.append(str(starttime_ticks))  # fields[19] == starttime
        (entry / "stat").write_text(f"{pid} (python3) " + " ".join(stat_fields) + "\n")

    def test_counts_old_forkserver_when_no_checks_running(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount.test_counts_old_forkserver_when_no_checks_running  # noqa: E501
        proc = tmp_path / "proc"
        self._write_proc(proc, uptime_s=1_000_000.0)
        self._write_forkserver(proc, 4242, age_s=7200.0)  # 2h old
        assert fleet_status.stale_forkserver_count(proc, concurrent_checks=0) == 1

    def test_ignores_young_forkserver(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount.test_ignores_young_forkserver  # noqa: E501
        proc = tmp_path / "proc"
        self._write_proc(proc, uptime_s=1_000_000.0)
        self._write_forkserver(proc, 4242, age_s=30.0)  # 30s old, still working
        assert fleet_status.stale_forkserver_count(proc, concurrent_checks=0) == 0

    def test_never_counts_anything_while_a_check_is_running(
        self, tmp_path: Path
    ) -> None:
        """T-2517's own explicit caution: a live-parented forkserver MAY
        belong to a check about to start. `concurrent_checks > 0` must
        zero the count even for a forkserver that is genuinely 2h old --
        this function never claims 'stale' while a check might be using
        the pool."""
        # frob:tests tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount.test_never_counts_anything_while_a_check_is_running  # noqa: E501
        proc = tmp_path / "proc"
        self._write_proc(proc, uptime_s=1_000_000.0)
        self._write_forkserver(proc, 4242, age_s=7200.0)
        assert fleet_status.stale_forkserver_count(proc, concurrent_checks=1) == 0

    def test_unknown_concurrent_checks_never_counts_anything(
        self, tmp_path: Path
    ) -> None:
        """`concurrent_checks is None` (unknown) must degrade to 0, the
        same conservative posture as a positive count -- never treated as
        'assume zero checks running'."""
        # frob:tests tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount.test_unknown_concurrent_checks_never_counts_anything  # noqa: E501
        proc = tmp_path / "proc"
        self._write_proc(proc, uptime_s=1_000_000.0)
        self._write_forkserver(proc, 4242, age_s=7200.0)
        assert fleet_status.stale_forkserver_count(proc, concurrent_checks=None) == 0

    def test_missing_proc_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestStaleForkserverCount.test_missing_proc_returns_none  # noqa: E501
        assert (
            fleet_status.stale_forkserver_count(
                tmp_path / "no-proc", concurrent_checks=0
            )
            is None
        )


# frob:ticket T-2818
class TestDeriveForkserverStaleAfterS:
    """`fleet_status._derive_forkserver_stale_after_s` (T-2818): the age
    backstop threshold DERIVED from this repo's own recorded `frob check`
    timings, replacing a hardcoded constant -- the ticket's own explicit
    requirement, citing T-2715/`_TRUE_COUNT_BUDGET_S` as the precedent for
    why a frozen number silently stops tracking repo growth."""

    def test_derives_from_recorded_samples_with_headroom(self, tmp_path: Path) -> None:
        """Sums each group's own MAX sample (worst-case per stage) then
        applies the headroom multiplier -- two groups whose maxima are
        100s and 50s derive to (100 + 50) * headroom, floored only if that
        product is below the floor."""
        # frob:tests tests/unit/test_coordinator_scripts.py::TestDeriveForkserverStaleAfterS.test_derives_from_recorded_samples_with_headroom  # noqa: E501
        (tmp_path / ".frob").mkdir()
        (tmp_path / ".frob" / "check-budget-timing-samples.json").write_text(
            json.dumps({"gates-fast": [10.0, 100.0, 40.0], "static": [50.0, 20.0]}),
            encoding="utf-8",
        )
        expected = (100.0 + 50.0) * fleet_status._FORKSERVER_STALE_AFTER_HEADROOM
        assert fleet_status._derive_forkserver_stale_after_s(tmp_path) == max(
            expected, fleet_status._FORKSERVER_STALE_AFTER_FLOOR_S
        )

    def test_missing_samples_file_falls_back(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestDeriveForkserverStaleAfterS.test_missing_samples_file_falls_back  # noqa: E501
        assert (
            fleet_status._derive_forkserver_stale_after_s(tmp_path)
            == fleet_status._FORKSERVER_STALE_AFTER_S_FALLBACK
        )

    def test_malformed_samples_file_falls_back(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestDeriveForkserverStaleAfterS.test_malformed_samples_file_falls_back  # noqa: E501
        (tmp_path / ".frob").mkdir()
        (tmp_path / ".frob" / "check-budget-timing-samples.json").write_text(
            "not json{{", encoding="utf-8"
        )
        assert (
            fleet_status._derive_forkserver_stale_after_s(tmp_path)
            == fleet_status._FORKSERVER_STALE_AFTER_S_FALLBACK
        )

    def test_thin_samples_never_derive_below_the_floor(self, tmp_path: Path) -> None:
        """A tiny recorded sample (a fresh repo with only a couple of
        quick runs logged) must never derive a threshold below
        `_FORKSERVER_STALE_AFTER_FLOOR_S`, which would risk flagging an
        in-progress check's own forkservers as stale."""
        # frob:tests tests/unit/test_coordinator_scripts.py::TestDeriveForkserverStaleAfterS.test_thin_samples_never_derive_below_the_floor  # noqa: E501
        (tmp_path / ".frob").mkdir()
        (tmp_path / ".frob" / "check-budget-timing-samples.json").write_text(
            json.dumps({"lint": [0.5]}), encoding="utf-8"
        )
        assert (
            fleet_status._derive_forkserver_stale_after_s(tmp_path)
            == fleet_status._FORKSERVER_STALE_AFTER_FLOOR_S
        )


# frob:ticket T-2517
class TestForkserverSwapHeldKb:
    """`fleet_status.forkserver_swap_held_kb` (T-2517): summed VmSwap,
    never RSS -- a swapped-out process reports near-zero RSS while still
    holding real memory, the exact reading that hid the ticket's own
    12GB incident behind a clean-looking orphan count."""

    @staticmethod
    def _write_entry(
        proc: Path, pid: int, *, cmdline: bytes, vmswap_kb: int | None
    ) -> None:
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(cmdline)
        (entry / "stat").write_text(f"{pid} (python3) S 999 {pid} 0 0 -1 0\n")
        if vmswap_kb is not None:
            (entry / "status").write_text(
                f"Name:\tpython3\nVmRSS:\t     100 kB\nVmSwap:\t{vmswap_kb} kB\n",
                encoding="utf-8",
            )

    def test_sums_vmswap_across_every_forkserver(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestForkserverSwapHeldKb.test_sums_vmswap_across_every_forkserver  # noqa: E501
        proc = tmp_path / "proc"
        proc.mkdir()
        fs_cmdline = b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
        self._write_entry(proc, 100, cmdline=fs_cmdline, vmswap_kb=5000)
        self._write_entry(proc, 101, cmdline=fs_cmdline, vmswap_kb=7000)
        self._write_entry(proc, 102, cmdline=b"sleep\x00600\x00", vmswap_kb=9000)
        assert fleet_status.forkserver_swap_held_kb(proc) == 12000

    def test_missing_status_file_degrades_that_entry_to_zero_not_a_crash(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestForkserverSwapHeldKb.test_missing_status_file_degrades_that_entry_to_zero_not_a_crash  # noqa: E501
        proc = tmp_path / "proc"
        proc.mkdir()
        fs_cmdline = b"python3\x00-c\x00from multiprocessing.forkserver import main; main(...)\x00"
        self._write_entry(proc, 100, cmdline=fs_cmdline, vmswap_kb=None)
        self._write_entry(proc, 101, cmdline=fs_cmdline, vmswap_kb=3000)
        assert fleet_status.forkserver_swap_held_kb(proc) == 3000

    def test_missing_proc_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestForkserverSwapHeldKb.test_missing_proc_returns_none  # noqa: E501
        assert fleet_status.forkserver_swap_held_kb(tmp_path / "no-proc") is None


# frob:ticket T-2818
class TestForkserverContradictionLine:
    """`fleet_status._forkserver_contradiction_line` (T-2818): the loud
    refusal to let '0 orphaned + 0 stale' sit next to multi-gigabyte
    forkserver swap without comment -- the exact combination that hid a
    92-forkserver leak for 45 minutes."""

    def test_fires_on_zero_zero_high_swap(self) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestForkserverContradictionLine.test_fires_on_zero_zero_high_swap  # noqa: E501
        line = fleet_status._forkserver_contradiction_line(0, 0, 14 * 1024 * 1024)
        assert line is not None
        assert "CONTRADICTION" in line

    def test_silent_when_swap_below_pressure_floor(self) -> None:
        """MUST-STILL-PASS: 0/0 next to a few MB of ordinary idle swap
        (not the multi-gigabyte incident shape) must never fire -- this is
        not "any swap at all", matching `_SWAP_PRESSURE_FLOOR_KB`'s own
        contract."""
        # frob:tests tests/unit/test_coordinator_scripts.py::TestForkserverContradictionLine.test_silent_when_swap_below_pressure_floor  # noqa: E501
        assert fleet_status._forkserver_contradiction_line(0, 0, 1024) is None

    def test_silent_when_orphaned_or_stale_nonzero(self) -> None:
        """A nonzero orphaned/stale reading already explains the swap --
        no contradiction to surface."""
        # frob:tests tests/unit/test_coordinator_scripts.py::TestForkserverContradictionLine.test_silent_when_orphaned_or_stale_nonzero  # noqa: E501
        assert (
            fleet_status._forkserver_contradiction_line(3, 0, 14 * 1024 * 1024) is None
        )
        assert (
            fleet_status._forkserver_contradiction_line(0, 3, 14 * 1024 * 1024) is None
        )

    def test_silent_on_any_unknown_input(self) -> None:
        """MUST-STILL-PASS: a contradiction claim needs all three readings
        to be real -- any `None` (unknown) input suppresses it rather than
        guessing."""
        # frob:tests tests/unit/test_coordinator_scripts.py::TestForkserverContradictionLine.test_silent_on_any_unknown_input  # noqa: E501
        assert (
            fleet_status._forkserver_contradiction_line(None, 0, 14 * 1024 * 1024)
            is None
        )
        assert (
            fleet_status._forkserver_contradiction_line(0, None, 14 * 1024 * 1024)
            is None
        )
        assert fleet_status._forkserver_contradiction_line(0, 0, None) is None


# frob:ticket T-2473
class TestConcurrentCheckCount:
    """`fleet_status.concurrent_check_count` (T-2473)."""

    @staticmethod
    def _write_entry(proc: Path, pid: int, *, cmdline: bytes) -> None:
        entry = proc / str(pid)
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes(cmdline)

    def test_counts_check_processes(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount.test_counts_check_processes  # noqa: E501
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(proc, 100, cmdline=b"frob\x00check\x00")
        self._write_entry(
            proc, 101, cmdline=b"/x/.venv/bin/frob\x00check\x00--json\x00"
        )
        assert fleet_status.concurrent_check_count(proc) == 2

    def test_ignores_non_check_processes(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount.test_ignores_non_check_processes  # noqa: E501
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(proc, 200, cmdline=b"frob\x00ticket\x00land\x00")
        self._write_entry(proc, 201, cmdline=b"frob\x00checkpointer\x00")
        assert fleet_status.concurrent_check_count(proc) == 0

    def test_missing_proc_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount.test_missing_proc_returns_none  # noqa: E501
        assert fleet_status.concurrent_check_count(tmp_path / "no-proc") is None

    def test_counts_module_invoked_check(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestConcurrentCheckCount.test_counts_module_invoked_check  # noqa: E501
        """T-3093 regression: `python -m frob check ...` -- the fleet's
        own dominant invocation shape under `uv run` -- must count, not
        silently vanish. The anchor-bugged regex this replaced
        (`re.compile(rb"(?:^|/)frob\\x00")`) never matched a bare `frob`
        token that is neither the first token nor preceded by `/`."""
        proc = tmp_path / "proc"
        proc.mkdir()
        self._write_entry(
            proc,
            100,
            cmdline=(
                b"/x/.venv/bin/python\x00-m\x00frob\x00check\x00--json\x00"
                b"--budget\x00300\x00"
            ),
        )
        assert fleet_status.concurrent_check_count(proc) == 1


class TestIsLiveCheckCmdline:
    """`fleet_status._is_live_check_cmdline` (T-3093)."""

    def test_does_not_match_check_repro_subcommand(self) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestIsLiveCheckCmdline.test_does_not_match_check_repro_subcommand  # noqa: E501
        """Must not fire on a DIFFERENT ticket subcommand that merely
        contains the substring 'check' -- token equality, never a
        substring match."""
        assert (
            fleet_status._is_live_check_cmdline(
                b"frob\x00ticket\x00check-repro\x00T-1\x00"
            )
            is False
        )


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

    # frob:ticket T-2281
    def test_land_in_progress_ticket_with_no_lease_still_collides(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """(MUST FAIL FIRST) T-2281's measured incident: a ticket whose
        land is actively running holds NO lease (released locally before
        the squash reaches main) but its scope files are genuinely still
        contended. `land_ticket_ids` (from `land_invocations()`) is a
        SECOND occupancy source, independent of `held`; its scope is read
        from `main` since no lease exists to read it from."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: (
                {"state": "in-progress", "scope": ["src/frob/tickets/_land.py"]}
                if tid == "T-2254"
                else None
            ),
        )
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/**"], [], land_ticket_ids=["T-2254"]
        )
        assert len(collisions) == 1
        assert collisions[0]["ticket_id"] == "T-2254"
        assert any("_land.py" in p for p in collisions[0]["paths"])

    # frob:ticket T-2281
    def test_land_ticket_disjoint_scope_is_not_a_collision(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-STILL-PASS: a ticket with a land in flight whose scope
        does NOT overlap must still report no collision -- a fix that
        treats every in-flight land as blocking every dispatch would
        recreate an unreclaimable-lease-class defect from the opposite
        side."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: (
                {"state": "in-progress", "scope": ["src/frob/tickets/_land.py"]}
                if tid == "T-2254"
                else None
            ),
        )
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/app/config.py"], [], land_ticket_ids=["T-2254"]
        )
        assert collisions == []

    # frob:ticket T-2281
    def test_land_ticket_id_matching_a_live_lease_is_not_double_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket present in BOTH a live lease AND `land_ticket_ids`
        (a lease that has not yet been released, mid-land) is reported
        ONCE, from the lease path -- never twice."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        monkeypatch.setattr(fleet_status, "lease_classification", lambda record: "live")
        held = [
            {
                "ticket_id": "T-2254",
                "worktree": str(root),
                "scope": ["src/frob/tickets/_land.py"],
                "recorded_at": "2026-08-01T00:00:00+00:00",
            }
        ]
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/**"], held, land_ticket_ids=["T-2254"]
        )
        assert len(collisions) == 1

    # frob:ticket T-2281
    def test_the_ticket_s_own_id_in_land_ticket_ids_is_never_self_collision(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ticket's own id appearing in `land_ticket_ids` (it is itself
        actively landing right now) must never be reported as colliding
        with itself."""
        root = self._make_tree(tmp_path)
        monkeypatch.setattr(fleet_status, "REPO", root)
        collisions = fleet_status.scope_lease_collisions(
            "T-2220", ["src/frob/**"], [], land_ticket_ids=["T-2220"]
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
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
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
        monkeypatch.setattr(fleet_status, "land_invocations", lambda: [])
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
    def test_prints_dispatchable_true(self, capsys: pytest.CaptureFixture[str]) -> None:
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
# frob:ticket T-2654
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
    # frob:ticket T-2654
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
        monkeypatch.setattr(fleet_status, "in_progress_ticket_scope_leases", lambda: [])
        monkeypatch.setattr(fleet_status, "blocked_in_progress_leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        fleet_status._print_fleet_report([], idle_seconds=1200)
        out = capsys.readouterr().out
        assert "LEASES 1 (0 live, 0 leaked, 0 blocked-open)" in out
        assert "T-2114 -> exist  [reclaimable]" in out

    # frob:ticket T-2654
    def test_leases_section_reports_ledger_leak_missing_from_held(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2651: an in-progress ticket `in_progress_ticket_scope_leases`
        finds with no resolvable worktree, and that `leases()` (file-
        based) never held at all, still prints in the LEASES section,
        flagged LEAK -- the missing case this ticket fixes."""
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(
            fleet_status,
            "in_progress_ticket_scope_leases",
            lambda: [
                {
                    "ticket_id": "T-2377",
                    "scope": ["docs/modules/gates.md"],
                    "worktree": None,
                    "leaked": True,
                }
            ],
        )
        monkeypatch.setattr(fleet_status, "blocked_in_progress_leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        fleet_status._print_fleet_report([], idle_seconds=1200)
        out = capsys.readouterr().out
        assert "LEASES 1 (0 live, 1 leaked, 0 blocked-open)" in out
        assert "T-2377 -> <no worktree>  [LEAK]" in out

    # frob:ticket T-2654
    def test_leases_section_flags_blocked_open_lease(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2654: a held lease for an in-progress ticket whose
        `blocked_by` still names an open blocker gets a distinct
        `[BLOCKED-OPEN: ...]` suffix, and the header's `blocked-open`
        count reflects it -- the T-2377 shape, this time WITH a live
        lease held so it is not also a LEAK."""
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(
            fleet_status,
            "leases",
            lambda: [{"ticket_id": "T-2377", "worktree": "/w/t-2377"}],
        )
        monkeypatch.setattr(fleet_status, "in_progress_ticket_scope_leases", lambda: [])
        monkeypatch.setattr(
            fleet_status,
            "blocked_in_progress_leases",
            lambda: [{"ticket_id": "T-2377", "open_blockers": ["T-2568"]}],
        )
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        fleet_status._print_fleet_report([], idle_seconds=1200)
        out = capsys.readouterr().out
        assert "LEASES 1 (0 live, 0 leaked, 1 blocked-open)" in out
        assert "T-2377 -> t-2377" in out
        assert "[BLOCKED-OPEN: T-2568]" in out


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
    blocked_by: tuple[str, ...] = (),
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
    a ledger row with no `parent:` line at all, not a literal 'null').
    `blocked_by` (T-2449), when non-empty, is written as the same `- item`
    list-block shape real `frob ticket new --blocked-by` output uses;
    omitted entirely when empty (mirrors a ledger row with no
    `blocked_by:` key at all)."""
    ticket_dir = tickets_dir / ticket_id
    ticket_dir.mkdir(parents=True)
    parent_line = f"parent: {parent}\n" if parent is not None else ""
    blocked_by_block = (
        "blocked_by:\n" + "".join(f"- {b}\n" for b in blocked_by) if blocked_by else ""
    )
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
        f"{blocked_by_block}"
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
            tickets_dir,
            "T-0001",
            state="queued",
            priority="critical",
            created="2020-01-01",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        monkeypatch.setattr(
            fleet_status,
            "_rot_day_thresholds",
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
            tickets_dir,
            "T-0002",
            state="queued",
            priority="critical",
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
            tickets_dir,
            "T-0003",
            state="in-progress",
            priority="critical",
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
            tickets_dir,
            "T-0004",
            state="queued",
            priority="critical",
            created="2020-01-01",
            tier="ticket",
        )
        _write_ticket(
            tickets_dir,
            "T-0005",
            state="queued",
            priority="critical",
            created="2020-01-01",
            tier="epic",
        )
        _write_ticket(
            tickets_dir,
            "T-0006",
            state="planned",
            priority="critical",
            created="2020-01-01",
            tier="story",
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
            tickets_dir,
            "T-0007",
            state="queued",
            priority="critical",
            created="2020-01-01",
            runs_last=True,
        )
        _write_ticket(
            tickets_dir,
            "T-0008",
            state="queued",
            priority="critical",
            created="2020-01-01",
            runs_last=False,
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
            tickets_dir,
            "T-1623",
            state="queued",
            priority="critical",
            created="2020-01-01",
            tier="epic",
        )
        _write_ticket(
            tickets_dir,
            "T-2223",
            state="in-progress",
            priority="high",
            created=date.today().isoformat(),
            parent="T-1623",
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
            tickets_dir,
            "T-0009",
            state="queued",
            priority="critical",
            created="2020-01-01",
            tier="epic",
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
            tickets_dir,
            "T-0010",
            state="queued",
            priority="critical",
            created="2020-01-01",
            tier="epic",
        )
        _write_ticket(
            tickets_dir,
            "T-0011",
            state="done",
            priority="high",
            created=date.today().isoformat(),
            parent="T-0010",
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        assert rotting[0]["has_active_child"] is False

    # frob:ticket T-2449
    def test_archived_done_blockers_do_not_keep_a_ticket_permanently_blocked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2449's own reproduction of the T-1696 incident: a rotting
        leaf ticket names two blockers that are both DONE and ARCHIVED.
        MUST-NOW-DISPATCH: `open_blockers`/`unresolved_blockers` must
        both read empty, exactly reversing the pre-fix 'BLOCKED BY (still
        open): T-1692, T-1693' misdiagnosis."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir / "archive",
            "T-1692",
            state="done",
            priority="critical",
        )
        _write_ticket(
            tickets_dir / "archive",
            "T-1693",
            state="done",
            priority="critical",
        )
        _write_ticket(
            tickets_dir,
            "T-1696",
            state="queued",
            priority="high",
            created="2020-01-01",
            blocked_by=("T-1692", "T-1693"),
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        assert len(rotting) == 1
        assert rotting[0]["id"] == "T-1696"
        assert rotting[0]["open_blockers"] == []
        assert rotting[0]["unresolved_blockers"] == []

    # frob:ticket T-2449
    def test_a_genuinely_open_blocker_still_blocks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-STILL-BLOCK control: a blocker that is neither done nor
        dropped still reports as open -- this fix must never simply stop
        checking blocked_by."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(tickets_dir, "T-5000", state="in-progress", priority="critical")
        _write_ticket(
            tickets_dir,
            "T-5001",
            state="queued",
            priority="high",
            created="2020-01-01",
            blocked_by=("T-5000",),
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        rotting = fleet_status.rotting_tickets()
        assert rotting[0]["open_blockers"] == ["T-5000"]
        assert rotting[0]["unresolved_blockers"] == []


class TestPrintTicketRot:
    """`fleet_status._print_ticket_rot` (T-2182)."""

    # frob:ticket T-2449
    def test_blocked_leaf_never_appears_under_needs_dispatch(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2449 acceptance [3]: a leaf ticket with a still-open (or
        unresolved) blocker must print under 'BLOCKED (dependency not
        yet resolved)', never under 'NEEDS DISPATCH' -- this is the exact
        structural shape T-1696 had (rot alarm demanding dispatch while
        `ticket_readiness` refused it three ticks running)."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-1696",
                    "priority": "high",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 12,
                    "threshold_days": 7,
                    "open_blockers": ["T-1692"],
                    "unresolved_blockers": [],
                },
                {
                    "id": "T-2000",
                    "priority": "high",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 12,
                    "threshold_days": 7,
                    "open_blockers": [],
                    "unresolved_blockers": [],
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 2" in out
        assert "NEEDS DISPATCH (1):" in out
        assert "BLOCKED (dependency not yet resolved) (1):" in out
        assert "T-1696" not in out.split("BLOCKED (dependency")[0]
        assert "T-1696" in out.split("BLOCKED (dependency")[1]
        assert "T-2000" in out.split("BLOCKED (dependency")[0]

    # frob:ticket T-2449
    def test_unresolved_blocker_also_keeps_leaf_out_of_needs_dispatch(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """An UNRESOLVED (not just open) blocker also excludes a leaf from
        NEEDS DISPATCH -- fail-loudly, T-2391: 'cannot confirm' is never
        treated as 'safe to dispatch'."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-3000",
                    "priority": "high",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 12,
                    "threshold_days": 7,
                    "open_blockers": [],
                    "unresolved_blockers": ["T-9999"],
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "NEEDS DISPATCH" not in out
        assert "BLOCKED (dependency not yet resolved) (1):" in out
        assert "T-3000" in out

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

    # frob:ticket T-2468
    def test_epic_all_terminal_children_prints_under_needs_close(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2468 acceptance [0]: an epic whose children are all terminal
        (T-1135's exact shape -- one child, T-1197, done and archived)
        must print under 'NEEDS CLOSE', never under 'NEEDS
        DECOMPOSITION' -- the epic's own work is finished, it needs a
        rollup Done report and a close, not more decomposition."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-1135",
                    "priority": "high",
                    "tier": "epic",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                    "has_active_child": False,
                    "has_any_child": True,
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 1" in out
        assert "NEEDS CLOSE (1):" in out
        assert "T-1135" in out
        assert "NEEDS DECOMPOSITION" not in out

    # frob:ticket T-2475
    def test_blocked_story_with_terminal_child_prints_under_blocked_not_needs_close(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2475 positive control: T-1599's live shape -- tier=story,
        one archived-done child (so `has_active_child=False`,
        `has_any_child=True`, the exact NEEDS CLOSE trigger from T-2468's
        own test above) but an open `blocked_by` edge naming a still-open
        id. This must NOT print under NEEDS CLOSE -- there is no rollup
        to write, the other deliverables are still blocked -- it must
        print under BLOCKED (dependency not yet resolved) instead, with
        its tier disclosed even though a blocked LEAF ticket in the same
        bucket has no tier of its own (T-2475's per-ticket tier-display
        fix)."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-1599",
                    "priority": "high",
                    "tier": "story",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                    "has_active_child": False,
                    "has_any_child": True,
                    "open_blockers": ["T-2411"],
                    "unresolved_blockers": [],
                },
                {
                    "id": "T-2000",
                    "priority": "high",
                    "tier": "ticket",
                    "state": "queued",
                    "age_days": 12,
                    "threshold_days": 7,
                    "open_blockers": ["T-2001"],
                    "unresolved_blockers": [],
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 2" in out
        assert "NEEDS CLOSE" not in out
        assert "BLOCKED (dependency not yet resolved) (2):" in out
        blocked_section = out.split("BLOCKED (dependency")[1]
        assert "T-1599 tier=story" in blocked_section
        assert "T-2000 priority=" in blocked_section

    # frob:ticket T-2468
    def test_epic_with_no_children_at_all_still_prints_under_needs_decomposition(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-2468 acceptance [1]: an epic with NO children at all (never
        decomposed) still reports under 'NEEDS DECOMPOSITION' -- the
        NEEDS CLOSE split must not empty this bucket by
        reclassification, only siphon off the genuinely-finished case."""
        monkeypatch.setattr(
            fleet_status,
            "rotting_tickets",
            lambda: [
                {
                    "id": "T-9000",
                    "priority": "high",
                    "tier": "epic",
                    "state": "queued",
                    "age_days": 20,
                    "threshold_days": 3,
                    "has_active_child": False,
                    "has_any_child": False,
                },
            ],
        )
        fleet_status._print_ticket_rot()
        out = capsys.readouterr().out
        assert "TICKET ROT: 1" in out
        assert "NEEDS DECOMPOSITION (1):" in out
        assert "T-9000" in out
        assert "NEEDS CLOSE" not in out

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
        monkeypatch.setattr(
            fleet_status, "QUARANTINE", tmp_path / "does-not-exist.json"
        )
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


# frob:ticket T-2126
class TestVerifyQueueState:
    """`fleet_status.verify_queue_state` (T-2126, symmetric to
    `quarantine_state`/T-2049)."""

    # frob:ticket T-2126
    def test_reports_depth_and_oldest_age(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_coordinator_scripts.py::TestVerifyQueueState.test_reports_dep\
        # th_and_oldest_age
        """(MUST FAIL FIRST on main -- `verify_queue_state` does not exist
        yet): depth is the entry count, oldest_age_s is the OLDEST
        `enqueued_at` entry's age (the entry a coordinator most needs to
        know about, not the newest)."""
        store = tmp_path / "verify-queue.json"
        now = datetime(2026, 1, 1, tzinfo=UTC)
        store.write_text(
            json.dumps(
                [
                    {"enqueued_at": "2026-01-01T00:00:00+00:00"},  # 0s old
                    {"enqueued_at": "2025-12-31T23:00:00+00:00"},  # 3600s old
                ]
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(fleet_status, "VERIFY_QUEUE", store)
        depth, oldest_age_s = fleet_status.verify_queue_state(now=now)
        assert depth == 2
        assert oldest_age_s == pytest.approx(3600.0)

    # frob:ticket T-2126
    def test_zero_depth_when_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_coordinator_scripts.py::TestVerifyQueueState.test_zero_depth_\
        # when_no_file
        """MUST-STILL-PASS control: no queue file at all means nothing is
        queued -- `(0, None)`, not `(-1, None)` (the unreadable case)."""
        monkeypatch.setattr(
            fleet_status, "VERIFY_QUEUE", tmp_path / "does-not-exist.json"
        )
        assert fleet_status.verify_queue_state() == (0, None)

    # frob:ticket T-2126
    def test_unreadable_queue_is_unknown_never_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_coordinator_scripts.py::TestVerifyQueueState.test_unreadable_\
        # queue_is_unknown_never_zero
        """Malformed JSON is `(-1, None)`, never misread as `(0, None)` --
        mirrors `quarantine_state`'s own "cannot verify is never
        verified" posture: an unreadable store must never look like an
        empty, safe-to-dispatch queue."""
        store = tmp_path / "verify-queue.json"
        store.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "VERIFY_QUEUE", store)
        assert fleet_status.verify_queue_state() == (-1, None)


# frob:ticket T-2126
class TestFleetStatusMainVerifyQueue:
    """`fleet_status.main`'s VERIFY QUEUE line (T-2126)."""

    # frob:ticket T-2126
    def test_prints_depth_and_age_when_nonempty(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests \
        # tests/unit/test_coordinator_scripts.py::TestFleetStatusMainVerifyQueue.test_p\
        # rints_depth_and_age_when_nonempty
        """A nonzero queue depth is printed with its age, next to
        QUARANTINE -- symmetric to T-2049's own quarantine-line placement
        test above."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(fleet_status, "verify_queue_state", lambda: (3, 1234.0))
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        fleet_status.main()
        out = capsys.readouterr().out
        assert "VERIFY QUEUE depth=3" in out
        assert "1234s old" in out

    # frob:ticket T-2126
    def test_prints_empty_when_zero_depth(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests \
        # tests/unit/test_coordinator_scripts.py::TestFleetStatusMainVerifyQueue.test_p\
        # rints_empty_when_zero_depth
        """MUST-STILL-PASS control: a zero-depth queue is reported as
        empty, not silently omitted."""
        monkeypatch.setattr(fleet_status, "root_dirt", lambda: [])
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        monkeypatch.setattr(fleet_status, "worktrees", lambda idle_seconds: [])
        monkeypatch.setattr(fleet_status, "_print_land_status", lambda: None)
        monkeypatch.setattr(fleet_status, "_print_ticket_rot", lambda: None)
        monkeypatch.setattr(fleet_status, "quarantine_state", lambda: ("clear", 0))
        monkeypatch.setattr(fleet_status, "verify_queue_state", lambda: (0, None))
        monkeypatch.setattr(sys, "argv", ["fleet_status.py"])
        fleet_status.main()
        out = capsys.readouterr().out
        assert "VERIFY QUEUE empty" in out


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


# frob:ticket T-2775
class TestProbeLandsInFlight:
    """`wait_for_land_slot.probe_lands_in_flight` -- the ONLY place that
    parses the status probe's output; `None` (unmeasured) must never be
    confused with a genuine `0` reading."""

    def test_reads_a_genuine_count(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            wait_for_land_slot.subprocess,
            "run",
            lambda *a, **k: _completed("LANDS IN FLIGHT: 3\n  T-1 pids=1 ...\n"),
        )
        assert wait_for_land_slot.probe_lands_in_flight(["irrelevant"]) == 3

    def test_zero_is_a_real_reading_not_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            wait_for_land_slot.subprocess,
            "run",
            lambda *a, **k: _completed("LANDS IN FLIGHT: 0\n"),
        )
        assert wait_for_land_slot.probe_lands_in_flight(["irrelevant"]) == 0

    def test_nonzero_exit_is_unmeasured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """POSITIVE CONTROL (T-2775): force the status probe to fail --
        the exact case the whole ticket exists to guard. A nonzero exit
        must read as `None`, never as `0`."""
        monkeypatch.setattr(
            wait_for_land_slot.subprocess,
            "run",
            lambda *a, **k: _completed("LANDS IN FLIGHT: 0\n", returncode=1),
        )
        assert wait_for_land_slot.probe_lands_in_flight(["irrelevant"]) is None

    def test_unparseable_output_is_unmeasured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            wait_for_land_slot.subprocess,
            "run",
            lambda *a, **k: _completed("garbage, no such line here\n"),
        )
        assert wait_for_land_slot.probe_lands_in_flight(["irrelevant"]) is None

    def test_probe_timeout_is_unmeasured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*a, **k):
            raise subprocess.TimeoutExpired(cmd="fleet_status", timeout=30)

        monkeypatch.setattr(wait_for_land_slot.subprocess, "run", _raise)
        assert wait_for_land_slot.probe_lands_in_flight(["irrelevant"]) is None

    def test_probe_oserror_is_unmeasured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*a, **k):
            raise OSError("no such file")

        monkeypatch.setattr(wait_for_land_slot.subprocess, "run", _raise)
        assert wait_for_land_slot.probe_lands_in_flight(["irrelevant"]) is None


# frob:ticket T-2775
class TestWaitForSlot:
    """`wait_for_land_slot.wait_for_slot` -- the polling state machine.
    `probe_lands_in_flight` itself is monkeypatched here (not
    `subprocess.run`) so each case can script an exact sequence of
    readings over successive ticks without real subprocess semantics."""

    def _fake_clock(self):
        """A fake `now`/`sleep` pair advancing in lockstep so the state
        machine's own elapsed-time math runs deterministically with zero
        real wall-clock waiting."""
        state = {"t": 0.0}

        def now() -> float:
            return state["t"]

        def sleep(seconds: float) -> None:
            state["t"] += seconds

        return now, sleep

    def test_slot_already_free_returns_immediately(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(wait_for_land_slot, "probe_lands_in_flight", lambda cmd: 0)
        now, sleep = self._fake_clock()
        code, summary = wait_for_land_slot.wait_for_slot(
            command=["irrelevant"],
            max_in_flight=0,
            timeout_s=100,
            poll_interval_s=10,
            sleep=sleep,
            now=now,
        )
        assert code == wait_for_land_slot.EXIT_SLOT_FREE
        assert "slot free" in summary
        # POSITIVE CONTROL: the common uncontended case must not impose a
        # fixed sleep -- zero time should have elapsed.
        assert now() == 0.0

    def test_land_in_flight_then_free_blocks_then_returns(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POSITIVE CONTROL (T-2775): with a land genuinely in flight the
        script BLOCKS (does not return 0 early) until it later clears."""
        readings = iter([2, 2, 1, 0])
        monkeypatch.setattr(
            wait_for_land_slot, "probe_lands_in_flight", lambda cmd: next(readings)
        )
        now, sleep = self._fake_clock()
        code, summary = wait_for_land_slot.wait_for_slot(
            command=["irrelevant"],
            max_in_flight=0,
            timeout_s=100,
            poll_interval_s=10,
            sleep=sleep,
            now=now,
        )
        assert code == wait_for_land_slot.EXIT_SLOT_FREE
        assert now() == 30.0  # blocked through 3 non-qualifying polls

    def test_always_in_flight_times_out(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(wait_for_land_slot, "probe_lands_in_flight", lambda cmd: 5)
        now, sleep = self._fake_clock()
        code, summary = wait_for_land_slot.wait_for_slot(
            command=["irrelevant"],
            max_in_flight=0,
            timeout_s=40,
            poll_interval_s=10,
            sleep=sleep,
            now=now,
        )
        assert code == wait_for_land_slot.EXIT_TIMEOUT
        assert "timeout" in summary
        assert "last measured LANDS IN FLIGHT=5" in summary

    def test_always_unmeasurable_never_returns_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POSITIVE CONTROL (T-2775), the one the ticket names as the
        proof that matters: the status probe is forced to fail on EVERY
        poll. The script must exit with the measurement-failure code and
        NOT 0 -- an unmeasurable fleet must never be mistaken for a free
        slot."""
        monkeypatch.setattr(
            wait_for_land_slot, "probe_lands_in_flight", lambda cmd: None
        )
        now, sleep = self._fake_clock()
        code, summary = wait_for_land_slot.wait_for_slot(
            command=["irrelevant"],
            max_in_flight=0,
            timeout_s=40,
            poll_interval_s=10,
            sleep=sleep,
            now=now,
        )
        assert code == wait_for_land_slot.EXIT_MEASUREMENT_FAILED
        assert code != wait_for_land_slot.EXIT_SLOT_FREE
        assert "measurement failed" in summary

    def test_measured_then_unmeasurable_is_timeout_not_measurement_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Once ANY real reading was obtained, later probe failures must
        not retroactively turn a genuine (if incomplete) measurement into
        MEASUREMENT_FAILED -- that would hide the fact that a land really
        was observed in flight."""
        readings = iter([3, None, None, None, None])

        def fake_probe(cmd):
            try:
                return next(readings)
            except StopIteration:
                return None

        monkeypatch.setattr(wait_for_land_slot, "probe_lands_in_flight", fake_probe)
        now, sleep = self._fake_clock()
        code, summary = wait_for_land_slot.wait_for_slot(
            command=["irrelevant"],
            max_in_flight=0,
            timeout_s=40,
            poll_interval_s=10,
            sleep=sleep,
            now=now,
        )
        assert code == wait_for_land_slot.EXIT_TIMEOUT
        assert "last measured LANDS IN FLIGHT=3" in summary

    def test_verbose_tick_hook_receives_every_reading(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        readings = iter([2, 0])
        monkeypatch.setattr(
            wait_for_land_slot, "probe_lands_in_flight", lambda cmd: next(readings)
        )
        now, sleep = self._fake_clock()
        seen: list[int | None] = []
        code, _ = wait_for_land_slot.wait_for_slot(
            command=["irrelevant"],
            max_in_flight=0,
            timeout_s=100,
            poll_interval_s=10,
            on_tick=lambda reading, elapsed: seen.append(reading),
            sleep=sleep,
            now=now,
        )
        assert code == wait_for_land_slot.EXIT_SLOT_FREE
        assert seen == [2, 0]


# frob:ticket T-2775
class TestWaitForLandSlotMain:
    """`wait_for_land_slot.main` -- the CLI wrapper: exactly one summary
    line to stdout, `--verbose` adds per-tick lines to stderr, and
    `--fleet-status-cmd` is the fault-injection seam a caller (or this
    ticket's own required positive control) uses to force a real,
    end-to-end measurement failure without touching the live fleet."""

    def test_quiet_by_default_prints_one_summary_line(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(wait_for_land_slot, "probe_lands_in_flight", lambda cmd: 0)
        code = wait_for_land_slot.main(["--timeout", "5"])
        assert code == wait_for_land_slot.EXIT_SLOT_FREE
        out = capsys.readouterr()
        assert out.out.strip().count("\n") == 0
        assert "slot free" in out.out
        assert out.err == ""

    def test_verbose_adds_per_tick_lines_to_stderr(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        readings = iter([1, 0])
        monkeypatch.setattr(
            wait_for_land_slot, "probe_lands_in_flight", lambda cmd: next(readings)
        )
        code = wait_for_land_slot.main(
            ["--timeout", "5", "--poll-interval", "1", "--verbose"]
        )
        assert code == wait_for_land_slot.EXIT_SLOT_FREE
        out = capsys.readouterr()
        assert out.out.strip().count("\n") == 0
        assert "LANDS IN FLIGHT=1" in out.err
        assert "LANDS IN FLIGHT=0" in out.err

    def test_end_to_end_forced_probe_failure_via_fleet_status_cmd(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """POSITIVE CONTROL (T-2775), end-to-end through the real CLI and
        real `subprocess.run` (no monkeypatching of `probe_lands_in_flight`
        itself): `--fleet-status-cmd` points at a command that always
        fails, proving the wiring from CLI flag through to the
        measurement-failure exit code with nothing stubbed out."""
        code = wait_for_land_slot.main(
            [
                "--timeout",
                "2",
                "--poll-interval",
                "1",
                "--fleet-status-cmd",
                "false",
            ]
        )
        assert code == wait_for_land_slot.EXIT_MEASUREMENT_FAILED
        assert code != wait_for_land_slot.EXIT_SLOT_FREE
        out = capsys.readouterr()
        assert "measurement failed" in out.out


class TestFleetStatusLarge001WaiverParses:
    """T-2845: scripts/fleet_status.py's frob:waive LARGE001 directive was
    corrected to record real cross-calls found between its four concerns
    (readiness->rot, readiness->procscan) and a monkeypatch-coupling risk
    that made an actual file split unsafe. This is a regression test for
    the directive-DSL parser hazard flagged this session (an embedded
    escaped quote in a frob:waive reason broke the comment DSL repo-wide):
    the multi-line corrected reason must still parse cleanly and still
    suppress LARGE001 for this file via the real arch gate + waiver
    machinery `frob check` itself uses.

    frob:tests tests/unit/test_coordinator_scripts.py::TestFleetStatusLarge001WaiverParses.test_waiver_still_suppresses_large001
    """

    def test_waiver_still_suppresses_large001(self, tmp_path: Path) -> None:
        """arch_gate() + _apply_waivers() against a live build_graph()
        snapshot of this repo report zero KEPT LARGE001 findings for
        scripts/fleet_status.py -- proving the corrected, multi-line
        frob:quote(frob:waive reason) still parses as one directive and still
        binds, rather than silently regressing to a bare unwaived LARGE001
        error the way a malformed directive would."""
        from frob.gates._arch import arch_gate  # noqa: PLC0415
        from frob.gates._waive import _apply_waivers  # noqa: PLC0415
        from frob.graph import build_graph  # noqa: PLC0415

        repo_root = Path(__file__).resolve().parents[2]
        snapshot = build_graph(repo_root, tmp_path / "cache.db").danger_ok
        raw = arch_gate(repo_root)
        kept, waived = _apply_waivers(raw, snapshot)
        kept_offenders = [
            v for v in kept if v.rule == "LARGE001" and "fleet_status.py" in v.file
        ]
        waived_offenders = [
            v for v in waived if v.rule == "LARGE001" and "fleet_status.py" in v.file
        ]
        assert kept_offenders == [], f"unwaived LARGE001 on fleet_status.py: {kept_offenders}"
        assert waived_offenders != [], "expected fleet_status.py's LARGE001 to be waived"


# frob:ticket T-2854
class TestOwnDocstringHasNoMalformedDirective:
    """T-2854: this file's own TestFleetStatusLarge001WaiverParses docstring
    used to contain an unescaped line ('frob:waive reason still parses as
    one directive and still binds,') that the directive DSL parses per-line
    -- a docstring is directive-scannable too (T-0342), and that line's
    SHAPE (starts with 'frob:<verb>') is indistinguishable from a genuine
    one-line directive, so it was reported as a MalformedDirective ('bad
    attribute syntax'). Fixed by wrapping the mention in the DSL's own
    `frob:quote(...)` escape (T-1970) rather than weakening the scanner --
    see tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMention
    Escape for the escape mechanism's own isolated coverage. This test
    binds directly to THIS file's real content so a future edit re-
    introducing an unescaped directive-shaped docstring line here is
    caught immediately, not just in the synthetic fixture."""

    def test_no_malformed_directives_in_this_file(self) -> None:
        # frob:tests tests/unit/test_coordinator_scripts.py::TestOwnDocstringHasNoMalformedDirective.test_no_malformed_directives_in_this_file  # noqa: E501
        from frob.graph.dsl import parse_directives  # noqa: PLC0415
        from frob.lang import parse_file  # noqa: PLC0415

        this_file = Path(__file__)
        parsed = parse_file(this_file).danger_ok
        _edges, malformed = parse_directives(parsed)
        assert malformed == (), (
            f"unescaped directive-shaped prose in {this_file.name}: {malformed}"
        )
