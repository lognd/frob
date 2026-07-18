"""Tests for frob.gates: drift, coverage, scope, pre-work, invariant, test gates."""

from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

from frob.gates import (
    GateConfig,
    PreworkSweep,
    Severity,
    SystemSpec,
    TestPolicy,
    active_ticket,
    coverage_gate,
    delta_violations,
    drift_gate,
    invariant_gate,
    is_baseline_stale,
    load_baseline,
    load_coverage,
    prework_gate,
    record_prework,
    run_gates,
    scope_gate,
    stamp_baseline,
    stamp_coverage,
    violation_fingerprint,
)
from frob.gates import (
    test_gate as run_test_gate,
)
from frob.gates.invariants import Criticality, InvariantError, load_invariants
from frob.gitio import Diff, Hunk
from frob.graph import build_graph
from frob.graph._models import LockEntry, LockFile
from frob.testing import CollectedTests
from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState
from frob.tickets._store import write_ticket


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _snapshot(root: Path):
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


def _rules(violations) -> list[str]:
    """The rule id of every violation, in order."""
    return [v.rule for v in violations]


def _files(violations) -> set[str]:
    """The set of files named by the violations."""
    return {v.file for v in violations}


def _first_rule(violations, rule):
    """The first violation with `rule`, or None -- assertion convenience."""
    for v in violations:
        if v.rule == rule:
            return v
    return None


def _by_rule(violations, rule) -> list:
    """Every violation carrying `rule` -- assertion convenience."""
    return [v for v in violations if v.rule == rule]


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    if not any(root.iterdir()):
        (root / ".gitkeep").write_text("")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "base", "--allow-empty"], cwd=root, check=True
    )


def _ticket(
    *,
    ticket_id: str = "T-0001",
    state: TicketState = TicketState.QUEUED,
    scope: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
    attachments: tuple = (),
    body: str = "## Description\nx\n\n## Done report\ndone\n",
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title="Sample",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        scope=scope,
        evidence=evidence,
        attachments=attachments,
        body=body,
    )


def _write_ticket(root: Path, ticket: Ticket) -> None:
    write_ticket(root, ticket).danger_ok


_WIDGET_PY = '''class Widget:
    """A widget."""

    def render(self, value: int) -> str:
        """Render the widget."""
        # frob:doc docs/x.md#widget
        return str(value)
'''


class TestDriftGate:
    def test_drift001_stale_ack_has_remedy(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        ref = "src/a.py::Widget.render"
        record = snap.symbols[ref]
        lock = LockFile(entries=(LockEntry(ref=ref, facet="sig", digest="deadbeef"),))
        assert record.digests.sig != "deadbeef"

        violations = drift_gate(snap, lock)
        v = _first_rule(violations, "DRIFT001")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "frob ack" in v.message
        assert v.file == "src/a.py"

    def test_drift002_dangling_has_candidates(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        _write(
            tmp_path,
            "docs/x.md",
            "# Widget\n\n<!-- frob:describes src/a.py::Widget.gone -->\n",
        )
        snap = _snapshot(tmp_path)
        lock = LockFile()
        violations = drift_gate(snap, lock)
        v = _first_rule(violations, "DRIFT002")
        assert v is not None
        assert "run: frob ack" in v.message or "candidates" in v.message

    def test_no_drift_when_clean(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::drift_gate
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        violations = drift_gate(snap, LockFile())
        assert violations == ()


def _violation(rule="R1", file="a.py", message="m", severity=Severity.WARN, line=1):
    from frob.gates import Violation

    return Violation(
        rule=rule, severity=severity, file=file, line=line, message=message
    )


class TestBaselineDelta:
    """T-0095: baseline stamp + --delta filtering."""

    def test_fingerprint_ignores_line_number(self) -> None:
        # frob:tests src/frob/gates/_baseline.py::violation_fingerprint kind="unit"
        a = _violation(line=1)
        b = _violation(line=99)
        assert violation_fingerprint(a) == violation_fingerprint(b)

    def test_fingerprint_differs_on_rule_file_or_message(self) -> None:
        base = _violation()
        assert violation_fingerprint(base) != violation_fingerprint(
            _violation(rule="R2")
        )
        assert violation_fingerprint(base) != violation_fingerprint(
            _violation(file="b.py")
        )
        assert violation_fingerprint(base) != violation_fingerprint(
            _violation(message="other")
        )

    def test_stamp_and_load_round_trip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_baseline.py::stamp_baseline kind="unit"
        _write(tmp_path, "src/a.py", "def f():\n    pass\n")
        violations = (_violation(file="src/a.py"),)
        result = stamp_baseline(tmp_path, violations)
        assert result.is_ok
        baseline = load_baseline(tmp_path)
        assert baseline is not None
        assert violation_fingerprint(violations[0]) in baseline["fingerprints"]

    def test_load_baseline_missing_is_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_baseline.py::load_baseline kind="unit"
        assert load_baseline(tmp_path) is None

    def test_delta_filters_known_violations(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_baseline.py::delta_violations kind="unit"
        _write(tmp_path, "src/a.py", "def f():\n    pass\n")
        old = _violation(file="src/a.py", message="old")
        stamp_baseline(tmp_path, (old,))
        baseline = load_baseline(tmp_path)
        assert baseline is not None
        new = _violation(file="src/a.py", message="new")
        kept = delta_violations((old, new), baseline)
        assert kept == (new,)

    def test_baseline_not_stale_when_files_unchanged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_baseline.py::is_baseline_stale kind="unit"
        _write(tmp_path, "src/a.py", "def f():\n    pass\n")
        stamp_baseline(tmp_path, (_violation(file="src/a.py"),))
        baseline = load_baseline(tmp_path)
        assert baseline is not None
        assert is_baseline_stale(tmp_path, baseline) is False

    def test_baseline_stale_when_file_changes(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def f():\n    pass\n")
        stamp_baseline(tmp_path, (_violation(file="src/a.py"),))
        baseline = load_baseline(tmp_path)
        assert baseline is not None
        _write(tmp_path, "src/a.py", "def f():\n    return 1\n")
        assert is_baseline_stale(tmp_path, baseline) is True


class TestCoverageGate:
    def test_cov001_undocumented_public_symbol(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        assert any(v.rule == "COV001" for v in violations)

    def test_cov001_passes_when_documented(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::coverage_gate
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        # only the method carries a frob:doc edge; the enclosing class is
        # still undocumented, so only assert on the documented symbol
        render_cov001 = [
            v for v in violations if v.rule == "COV001" and "Widget.render" in v.message
        ]
        assert render_cov001 == []

    def test_cov002_unticketed_diff_hunk(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        v = _first_rule(violations, "COV002")
        assert v is not None
        assert "frob ticket new" in v.message

    def test_cov002_passes_with_open_ticket_edge(self, tmp_path: Path) -> None:
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.IN_PROGRESS)})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        assert not any(v.rule == "COV002" for v in violations)

    def test_cov003_done_ticket_missing_evidence(self, tmp_path: Path) -> None:
        snap = _snapshot(tmp_path)
        queue = TicketQueue(
            tickets={
                "T-0002": _ticket(
                    ticket_id="T-0002",
                    state=TicketState.DONE,
                    evidence=("tests/test_x.py::test_missing",),
                )
            }
        )
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        assert any(v.rule == "COV003" for v in violations)

    def test_cov003_passes_when_evidence_collected(self, tmp_path: Path) -> None:
        snap = _snapshot(tmp_path)
        node = "tests/test_x.py::test_present"
        queue = TicketQueue(
            tickets={
                "T-0002": _ticket(
                    ticket_id="T-0002", state=TicketState.DONE, evidence=(node,)
                )
            }
        )
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = coverage_gate(snap, queue, diff, tests)
        assert not any(v.rule == "COV003" for v in violations)

    def test_cov004_missing_attachment(self, tmp_path: Path) -> None:
        from frob.tickets import Attachment

        snap = _snapshot(tmp_path)
        att = Attachment(
            path="attachments/T-0003/01-x.png", caption="x", sha256="ab" * 32
        )
        queue = TicketQueue(
            tickets={"T-0003": _ticket(ticket_id="T-0003", attachments=(att,))}
        )
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        assert any(v.rule == "COV004" for v in violations)

    def test_todo001_unbound_directive(self, tmp_path: Path) -> None:
        source = "def helper(x):\n    # frob:todo T-9999\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        assert any(v.rule == "TODO001" for v in violations)

    def test_todo001_bare_comment_in_touched_file(self, tmp_path: Path) -> None:
        source = "def helper(x):\n    # TODO: fix this later\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(1, 3)),))
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        assert any(v.rule == "TODO001" and "bare TODO" in v.message for v in violations)

    def test_waiver_suppresses_and_reports(self, tmp_path: Path) -> None:
        source = (
            "def helper(x):\n"
            '    """A public helper waived from doc obligations."""\n'
            '    # frob:waive COV001 reason="legacy code, ticket filed"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        assert _first_rule(violations, "COV001") is not None

        from frob.gates import _apply_waivers  # noqa: PLC0415 - internal, test-only

        kept, waived = _apply_waivers(violations, snap)
        assert _first_rule(kept, "COV001") is None
        waived_cov001 = _first_rule(waived, "COV001")
        assert waived_cov001 is not None
        assert waived_cov001.waived is not None

    def test_waive001_missing_reason(self, tmp_path: Path) -> None:
        source = "def helper(x):\n    # frob:waive COV001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates import _waive001_violations  # noqa: PLC0415

        violations = _waive001_violations(snap)
        assert any(v.rule == "WAIVE001" for v in violations)
        assert violations[0].severity == Severity.ERROR

    def test_waive002_known_gate_rule_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_waive002_violations kind="unit"
        source = 'def helper(x):\n    # frob:waive COV001 reason="ok"\n    return x\n'
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates import _waive002_violations  # noqa: PLC0415

        violations = _waive002_violations(snap, frozenset())
        assert violations == ()

    def test_waive002_flags_arch_category_as_ineffective(self, tmp_path: Path) -> None:
        # T-0101: a waiver on an arch category (e.g. long-function) can
        # never be matched by _apply_waivers -- WAIVE002 must say so loudly
        # rather than silently doing nothing.
        source = (
            'def helper(x):\n    # frob:waive long-function reason="huge but ok"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates import _waive002_violations  # noqa: PLC0415

        violations = _waive002_violations(snap, frozenset())
        v = _first_rule(violations, "WAIVE002")
        assert v is not None
        assert v.severity == Severity.WARN
        assert "frob-arch" in v.message

    def test_waive002_flags_unknown_rule_id_as_ineffective(
        self, tmp_path: Path
    ) -> None:
        source = (
            'def helper(x):\n    # frob:waive NOTAREALRULE reason="typo"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates import _waive002_violations  # noqa: PLC0415

        violations = _waive002_violations(snap, frozenset())
        v = _first_rule(violations, "WAIVE002")
        assert v is not None
        assert "not a recognized gate or policy rule id" in v.message

    def test_waive002_honors_loaded_policy_rule_ids(self, tmp_path: Path) -> None:
        source = (
            'def helper(x):\n    # frob:waive POL-custom reason="known false positive"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates import _waive002_violations  # noqa: PLC0415

        violations = _waive002_violations(snap, frozenset({"POL-custom"}))
        assert violations == ()

    def test_waive002_end_to_end_via_run_gates(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::run_gates kind="integration"
        _git_init(tmp_path)
        source = (
            'def helper(x):\n    # frob:waive god-class reason="legacy, tracked"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add file"], cwd=tmp_path, check=True
        )
        cfg = GateConfig(root=str(tmp_path), base="main")
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert _first_rule(report.violations, "WAIVE002") is not None


class TestScopePrework:
    def test_scope001_out_of_scope_file(self, tmp_path: Path) -> None:
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/allowed/**",))
        diff = Diff(base="x", hunks=(Hunk(file="src/other/f.py", span=(1, 1)),))
        violations = scope_gate(diff, ticket, snap)
        assert any(v.rule == "SCOPE001" for v in violations)

    def test_scope001_passes_in_scope(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/allowed/**",))
        diff = Diff(base="x", hunks=(Hunk(file="src/allowed/f.py", span=(1, 1)),))
        violations = scope_gate(diff, ticket, snap)
        assert violations == ()

    def test_scope_unrestricted_when_no_scope_declared(self, tmp_path: Path) -> None:
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=())
        diff = Diff(base="x", hunks=(Hunk(file="src/anything.py", span=(1, 1)),))
        assert scope_gate(diff, ticket, snap) == ()

    def test_pre001_missing_sweep(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        snap = _snapshot(tmp_path)
        ticket = _ticket(state=TicketState.IN_PROGRESS)
        violations = prework_gate(ticket, snap, Nothing())
        assert any(v.rule == "PRE001" for v in violations)
        assert "frob ticket start" in violations[0].message

    def test_pre001_passes_with_current_sweep(self, tmp_path: Path) -> None:
        from typani.option import Some

        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/**",))

        from frob.gates import _scope_digest  # noqa: PLC0415

        digest = _scope_digest(ticket, snap)
        sweep = PreworkSweep(
            date=date(2026, 1, 1), dup_findings=0, xref_hits=(), digest=digest
        )
        violations = prework_gate(ticket, snap, Some(sweep))
        assert violations == ()

    def test_pre001_stale_sweep(self, tmp_path: Path) -> None:
        from typani.option import Some

        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/**",))
        sweep = PreworkSweep(
            date=date(2026, 1, 1), dup_findings=0, xref_hits=(), digest="stale"
        )
        violations = prework_gate(ticket, snap, Some(sweep))
        assert any(v.rule == "PRE001" for v in violations)

    def test_prework_skips_when_not_in_progress(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::prework_gate
        from typani.option import Nothing

        snap = _snapshot(tmp_path)
        ticket = _ticket(state=TicketState.QUEUED)
        assert prework_gate(ticket, snap, Nothing()) == ()

    def test_record_and_load_prework_roundtrip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_prework.py::record_prework
        from frob.gates._prework import load_prework

        sweep = PreworkSweep(
            date=date(2026, 1, 1), dup_findings=2, xref_hits=("a", "b"), digest="abc"
        )
        result = record_prework(tmp_path, "T-0001", sweep)
        assert result.is_ok
        loaded = load_prework(tmp_path, "T-0001")
        assert loaded == sweep


class TestActiveTicket:
    def test_explicit_flag_wins(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::active_ticket
        _git_init(tmp_path)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "T-0002-other"], cwd=tmp_path, check=True
        )
        result = active_ticket(tmp_path, "T-0001")
        assert result.is_some
        assert result.danger_some == "T-0001"

    def test_branch_regex_match(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "T-0042-do-a-thing"],
            cwd=tmp_path,
            check=True,
        )
        result = active_ticket(tmp_path, None)
        assert result.is_some
        assert result.danger_some == "T-0042"

    def test_nothing_fallback(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        result = active_ticket(tmp_path, None)
        assert result.is_nothing


class TestInvariantGate:
    def test_inv001_no_evidence(self, tmp_path: Path) -> None:
        from frob.gates.invariants import Invariant

        snap = _snapshot(tmp_path)
        inv = Invariant(
            id="INV-001", statement="x", criticality=Criticality.HIGH, evidence=()
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = invariant_gate((inv,), snap, tests)
        assert any(v.rule == "INV001" for v in violations)

    def test_inv001_uncollected_node_id(self, tmp_path: Path) -> None:
        from frob.gates.invariants import Invariant

        snap = _snapshot(tmp_path)
        inv = Invariant(
            id="INV-001",
            statement="x",
            criticality=Criticality.HIGH,
            evidence=("tests/test_x.py::test_y",),
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = invariant_gate((inv,), snap, tests)
        assert any(v.rule == "INV001" for v in violations)

    def test_inv001_passes_with_collected_evidence(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::invariant_gate
        source = "def f(x):\n    # frob:invariant INV-001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates.invariants import Invariant

        node = "tests/test_x.py::test_y"
        inv = Invariant(
            id="INV-001", statement="x", criticality=Criticality.HIGH, evidence=(node,)
        )
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = invariant_gate((inv,), snap, tests)
        assert violations == ()

    def test_inv002_no_anchor(self, tmp_path: Path) -> None:
        from frob.gates.invariants import Invariant

        snap = _snapshot(tmp_path)
        node = "tests/test_x.py::test_y"
        inv = Invariant(
            id="INV-001", statement="x", criticality=Criticality.HIGH, evidence=(node,)
        )
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = invariant_gate((inv,), snap, tests)
        assert any(v.rule == "INV002" for v in violations)

    def test_inv001_evidence_via_policy_rule_id(self, tmp_path: Path) -> None:
        from frob.gates.invariants import Invariant

        snap = _snapshot(tmp_path)
        inv = Invariant(
            id="INV-001",
            statement="x",
            criticality=Criticality.HIGH,
            evidence=("POL-thing",),
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = invariant_gate((inv,), snap, tests, frozenset({"POL-thing"}))
        assert not any(v.rule == "INV001" for v in violations)


class TestInvariantLoad:
    def test_malformed_bad_id(self, tmp_path: Path) -> None:
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-abc.md").write_text(
            "---\nid: INV-abc\nstatement: x\ncriticality: high\nevidence: []\n---\nprose\n"
        )
        result = load_invariants(tmp_path)
        assert result.is_err
        assert result.danger_err == InvariantError.Malformed

    def test_duplicate_id(self, tmp_path: Path) -> None:
        (tmp_path / "invariants").mkdir()
        text = "---\nid: INV-001\nstatement: x\ncriticality: high\nevidence: []\n---\nprose\n"
        (tmp_path / "invariants" / "INV-001.md").write_text(text)
        (tmp_path / "invariants" / "INV-001-dup.md").write_text(text)
        result = load_invariants(tmp_path)
        assert result.is_err
        assert result.danger_err == InvariantError.DuplicateId

    def test_missing_directory_ok(self, tmp_path: Path) -> None:
        result = load_invariants(tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()

    def test_loads_valid(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/invariants.py::load_invariants
        (tmp_path / "invariants").mkdir()
        text = (
            "---\nid: INV-007\nstatement: locks are atomic\ncriticality: high\n"
            "evidence:\n  - tests/test_lock.py::test_atomic\n---\nRationale.\n"
        )
        (tmp_path / "invariants" / "INV-007.md").write_text(text)
        result = load_invariants(tmp_path)
        assert result.is_ok
        assert result.danger_ok[0].id == "INV-007"
        assert result.danger_ok[0].evidence == ("tests/test_lock.py::test_atomic",)


class TestTestGate:
    def test_test001_public_symbol_no_unit_edge(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::test_gate
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert any(v.rule == "TEST001" for v in violations)

    def test_test002_below_min_unit_cases(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        source = "def helper(x):\n    return x\n"
        _write(tmp_path, "src/frob/pkg/a.py", source)
        test_source = (
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n"
        )
        _write(tmp_path, "tests/test_a.py", test_source)
        snap = _snapshot(tmp_path)
        node = "tests/test_a.py::test_helper"
        tests = CollectedTests(node_ids=frozenset({node}))
        cfg = TestPolicy(min_unit_cases=3)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST002" in rule_ids
        assert "TEST001" not in rule_ids

    def test_test002_satisfied_by_rust_directive_bound_cross_file(
        self, tmp_path: Path
    ) -> None:
        """Regression for T-0090: a `frob:tests` directive living in a
        different rust file than its target symbol must still count as unit
        evidence, even though `CollectedTests` (pytest-only) never sees the
        rust test's node id."""
        from typani.option import Nothing

        _write(
            tmp_path,
            "strata-core/src/lib.rs",
            "pub fn parse_source(x: &str) -> i32 {\n    0\n}\n",
        )
        _write(
            tmp_path,
            "strata-core/src/parse.rs",
            '// frob:tests strata-core/src/lib.rs::parse_source kind="unit"\n'
            "#[test]\n"
            "fn test_parse_basic() {\n"
            "    assert_eq!(1, 1);\n"
            "}\n",
        )
        snap = _snapshot(tmp_path)
        # No rust test collector exists yet -- CollectedTests is pytest-only,
        # so this deliberately stays empty to prove the fix does not depend
        # on the src ever landing in tests.node_ids.
        tests = CollectedTests(node_ids=frozenset())
        cfg = TestPolicy(min_unit_cases=1)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST002" not in rule_ids
        assert "TEST001" not in rule_ids

    def test_test002_rust_directive_from_non_test_symbol_does_not_satisfy(
        self, tmp_path: Path
    ) -> None:
        """Regression for the T-0090 review finding: a `frob:tests` directive
        whose `src` is a real symbol but NOT test code (no `tests` module
        segment, no `test_`/`_test` leaf name) must not count as evidence --
        extension alone (`.rs`) is not enough, or any non-test rust/ts/c/cpp
        symbol could rubber-stamp coverage for anything it names."""
        from typani.option import Nothing

        _write(
            tmp_path,
            "strata-core/src/lib.rs",
            "pub fn parse_source(x: &str) -> i32 {\n    0\n}\n\n"
            '// frob:tests strata-core/src/lib.rs::parse_source kind="unit"\n'
            "pub fn unrelated_helper(x: &str) -> i32 {\n    0\n}\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        cfg = TestPolicy(min_unit_cases=1)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST002" in rule_ids

    def test_test003_interface_without_integration(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert any(v.rule == "TEST003" for v in violations)

    def test_test004_system_below_min_e2e(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        snap = _snapshot(tmp_path)
        system = SystemSpec(
            id="cli-check", entrypoint="frob check", min_e2e=2, paths=()
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (system,), Nothing(), tests, TestPolicy())
        assert any(v.rule == "TEST004" for v in violations)

    def test_test004_passes_with_enough_e2e(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        test_source = (
            'def test_a():\n    # frob:tests cli-check kind="e2e"\n    assert True\n'
        )
        _write(tmp_path, "tests/test_a.py", test_source)
        snap = _snapshot(tmp_path)
        node = "tests/test_a.py::test_a"
        system = SystemSpec(
            id="cli-check", entrypoint="frob check", min_e2e=1, paths=()
        )
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = run_test_gate(snap, (system,), Nothing(), tests, TestPolicy())
        assert not any(v.rule == "TEST004" for v in violations)

    def test_test005_unit_branch_floor(self, tmp_path: Path) -> None:
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::helper"]
        coverage = CoverageData(
            source_sha="x", symbol_branch={record.symref: 40.0}, module_line={}
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(unit_branch_cov=90)
        )
        assert any(v.rule == "TEST005" and v.file == record.id.path for v in violations)

    def test_test005_module_line_floor(self, tmp_path: Path) -> None:
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x", symbol_branch={}, module_line={"src/frob/pkg/a.py": 10.0}
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(module_line_cov=85)
        )
        assert any(
            v.rule == "TEST005" and v.file == "src/frob/pkg/a.py" for v in violations
        )

    def test_test005_system_line_floor(self, tmp_path: Path) -> None:
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x", symbol_branch={}, module_line={"src/frob/pkg/a.py": 10.0}
        )
        system = SystemSpec(
            id="sys", entrypoint="x", min_e2e=0, paths=("src/frob/pkg/*",)
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (system,), Some(coverage), tests, TestPolicy(system_line_cov=80)
        )
        assert any(v.rule == "TEST005" and "sys" in v.file for v in violations)

    def test_test006_missing_stamp(self, tmp_path: Path) -> None:
        snap = _snapshot(tmp_path)
        from frob.gates import _test006  # noqa: PLC0415

        violations = _test006(snap)
        assert any(v.rule == "TEST006" for v in violations)

    def test_test006_stale_stamp(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        stamp = {
            "source_sha": "x",
            "file_hashes": {"src/frob/pkg/a.py": "not-the-real-hash"},
        }
        (tmp_path / ".frob").mkdir(exist_ok=True)
        (tmp_path / ".frob" / "coverage-stamp").write_text(json.dumps(stamp))
        from frob.gates import _test006  # noqa: PLC0415

        violations = _test006(snap)
        assert any(v.rule == "TEST006" for v in violations)

    def test_edge_with_uncollected_node_id_does_not_satisfy(
        self, tmp_path: Path
    ) -> None:
        from typani.option import Nothing

        source = "def helper(x):\n    return x\n"
        _write(tmp_path, "src/frob/pkg/a.py", source)
        test_source = (
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n"
        )
        _write(tmp_path, "tests/test_a.py", test_source)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset()
        )  # the test was deleted/not collected
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert any(v.rule == "TEST002" for v in violations)


class TestCoverageLoad:
    def test_missing_coverage_xml(self, tmp_path: Path) -> None:
        result = load_coverage(tmp_path)
        assert result.is_err

    def test_malformed_coverage_xml(self, tmp_path: Path) -> None:
        (tmp_path / "coverage.xml").write_text("not xml <<<")
        result = load_coverage(tmp_path)
        assert result.is_err

    def test_parses_line_to_symbol_span(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::helper"]
        start = record.span[0]
        xml = f"""<?xml version="1.0"?>
<coverage>
  <packages>
    <package>
      <classes>
        <class filename="src/frob/pkg/a.py" line-rate="0.5">
          <lines>
            <line number="{start}" hits="1" branch="false"/>
            <line number="{start + 1}" hits="0" branch="false"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""
        (tmp_path / "coverage.xml").write_text(xml)
        result = load_coverage(tmp_path, snap)
        assert result.is_ok
        data = result.danger_ok
        assert data.module_line["src/frob/pkg/a.py"] == 50.0
        assert record.symref in data.symbol_branch

    def test_stamp_coverage_roundtrip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::stamp_coverage
        # frob:tests src/frob/gates/_coverage.py::load_stamp
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        (tmp_path / "coverage.xml").write_text("<coverage></coverage>")
        result = stamp_coverage(tmp_path)
        assert result.is_ok
        from frob.gates._coverage import load_stamp

        stamp = load_stamp(tmp_path)
        assert stamp is not None
        assert "src/frob/pkg/a.py" in stamp["file_hashes"]


class TestRunGates:
    def test_run_gates_end_to_end(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::run_gates
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _git_init(tmp_path)
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"drift", "coverage"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert "drift" in report.stats.counts
        assert "coverage" in report.stats.counts
        assert isinstance(report.violations, tuple)
        assert isinstance(report.waived, tuple)

    def test_run_gates_skips_scope_without_ticket(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "prework"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert "scope" in report.stats.skipped
        assert "prework" in report.stats.skipped


class TestSeverityOverrides:
    def test_override_downgrades_and_ignores_garbage(self, tmp_path, monkeypatch):
        from frob.gates import Severity, Violation, _apply_severity_overrides

        (tmp_path / "frob.toml").write_text(
            '[gates.severity]\nCOV001 = "warn"\nDRIFT001 = "error"\nBAD = "loud"\n',
            encoding="utf-8",
        )
        violations = (
            Violation(
                rule="COV001",
                severity=Severity.ERROR,
                file="a.py",
                line=1,
                message="m",
            ),
            Violation(
                rule="SCOPE001",
                severity=Severity.ERROR,
                file="b.py",
                line=2,
                message="m",
            ),
        )
        out = _apply_severity_overrides(violations, tmp_path)
        assert out[0].severity == Severity.WARN
        assert out[1].severity == Severity.ERROR

    def test_no_frob_toml_is_identity(self, tmp_path):
        from frob.gates import Severity, Violation, _apply_severity_overrides

        violations = (
            Violation(
                rule="COV001",
                severity=Severity.ERROR,
                file="a.py",
                line=1,
                message="m",
            ),
        )
        assert _apply_severity_overrides(violations, tmp_path) == violations


class TestDoclinkGate:
    def test_orphan_doc_is_error_and_linked_docs_pass(self, tmp_path):
        # frob:tests src/frob/gates/__init__.py::doclink_gate kind="unit"
        from frob.gates import doclink_gate
        from frob.graph import build_graph

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "docs" / "index.md").write_text(
            "# Docs\n\n[linked](linked.md)\n", encoding="utf-8"
        )
        (root / "docs" / "linked.md").write_text("# Linked\n", encoding="utf-8")
        (root / "docs" / "orphan.md").write_text("# Orphan\n", encoding="utf-8")
        (root / "docs" / "described.md").write_text(
            "<!-- frob:describes src/m.py::f -->\n# Described\n", encoding="utf-8"
        )
        (root / "src" / "m.py").write_text("def f():\n    return 1\n")

        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = doclink_gate(root, snap)
        assert _files(violations) == {"docs/orphan.md"}
        assert set(_rules(violations)) <= {"DOC001"}

    def test_new_file_is_auto_obligated_by_glob(self, tmp_path):
        from frob.gates import doclink_gate
        from frob.graph import build_graph

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "index.md").write_text("# Docs\n", encoding="utf-8")
        cache = root / ".frob" / "cache.db"
        snap = build_graph(root, cache).danger_ok
        assert doclink_gate(root, snap) == ()

        (root / "docs" / "brand_new.md").write_text("# New\n", encoding="utf-8")
        violations = doclink_gate(root, build_graph(root, cache).danger_ok)
        assert {v.file for v in violations} == {"docs/brand_new.md"}


class TestCov002ScopeCoverage:
    def test_open_ticket_scope_covers_changed_symbol(self, tmp_path):
        """COV002 passes when a changed symbol's file is within an open
        ticket's declared scope -- one ticket covers a whole refactor."""
        import subprocess

        from frob.gates import GateConfig, run_gates
        from frob.tickets import (
            Origin,
            TicketKind,
            TicketSpec,
            TicketState,
            new_ticket,
            transition,
        )

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text("def f():\n    return 1\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=tmp_path, check=True)

        t = new_ticket(
            tmp_path,
            TicketSpec(
                title="refactor",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                scope=("src/**",),
            ),
        ).danger_ok
        transition(tmp_path, t.id, TicketState.PLANNED)
        transition(tmp_path, t.id, TicketState.IN_PROGRESS)
        (tmp_path / "src" / "m.py").write_text("def f():\n    return 2\n")

        report = run_gates(
            GateConfig(root=str(tmp_path), base="main", gates=frozenset({"coverage"}))
        ).danger_ok
        assert not [v for v in report.violations if v.rule == "COV002"]


class TestGatesDegradeWithoutDiff:
    def test_diff_independent_gates_run_without_git(self, tmp_path):
        """A repo with no valid base (fresh, no commits) must still run the
        diff-independent gates instead of skipping the whole stage."""
        from frob.gates import GateConfig, run_gates

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text(
            "# frob:invariant INV-001\ndef f(x):\n    return x\n"
        )
        (tmp_path / "frob.toml").write_text(
            '[fuzz]\nenforce = "invariant-anchored"\n', encoding="utf-8"
        )
        # no git repo at all -> working_diff fails -> must not error the stage
        report = run_gates(
            GateConfig(root=str(tmp_path), base="main", gates=frozenset({"fuzz"}))
        )
        assert report.is_ok, report.err
        assert any(v.rule == "FUZZ001" for v in report.danger_ok.violations)


class TestConventionUnitBinding:
    def test_test001_satisfied_by_convention_name(self, tmp_path):
        """T-0018: a public function is unit-covered by a conventionally
        named test (test_<name>) even without an explicit frob:tests edge."""
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "src/m.py", "def normalize(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_m.py::test_normalize_handles_empty"})
        )
        violations = run_test_gate(
            snap, (), Nothing(), tests, TestPolicy(min_unit_cases=1)
        )
        assert not any(v.rule == "TEST001" for v in violations)

    def test_test001_still_fires_without_matching_test(self, tmp_path):
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "src/m.py", "def normalize(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_m.py::test_other_thing"})
        )
        violations = run_test_gate(
            snap, (), Nothing(), tests, TestPolicy(min_unit_cases=1)
        )
        assert any(v.rule == "TEST001" for v in violations)

    def test_short_symbol_names_do_not_match_everything(self, tmp_path):
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "src/m.py", "def of(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset({"tests/test_m.py::test_unrelated"}))
        violations = run_test_gate(
            snap, (), Nothing(), tests, TestPolicy(min_unit_cases=1)
        )
        assert any(v.rule == "TEST001" and "::of" in v.message for v in violations)


class TestPairLevelIntegration:
    def _snap_with_dep(self, tmp_path):
        # consumer pkg src/app uses-contract on provider pkg src/core
        _write(tmp_path, "src/core/__init__.py", "def engine():\n    return 1\n")
        _write(
            tmp_path,
            "src/app/__init__.py",
            "# frob:uses-contract src/core/__init__.py::engine\n"
            "def handler():\n    return 2\n",
        )
        return _snapshot(tmp_path)

    def test_test007_fires_on_uncovered_boundary(self, tmp_path):
        # frob:tests src/frob/gates/__init__.py::test_gate
        from typani.option import Nothing

        from frob.gates import test_gate as run_tg
        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        snap = self._snap_with_dep(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        pol = TestPolicy(min_unit_cases=1, pair_integration=True)
        violations = run_tg(snap, (), Nothing(), tests, pol)
        assert any(
            v.rule == "TEST007" and "src/app" in v.message and "src/core" in v.message
            for v in violations
        )

    def test_test007_off_by_default(self, tmp_path):
        from typani.option import Nothing

        from frob.gates import test_gate as run_tg
        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        snap = self._snap_with_dep(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_tg(snap, (), Nothing(), tests, TestPolicy(min_unit_cases=1))
        assert not any(v.rule == "TEST007" for v in violations)

    def test_test007_passes_when_boundary_tested(self, tmp_path):
        from typani.option import Nothing

        from frob.gates import test_gate as run_tg
        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "src/core/__init__.py", "def engine():\n    return 1\n")
        _write(
            tmp_path,
            "src/app/__init__.py",
            "# frob:uses-contract src/core/__init__.py::engine\n"
            "def handler():\n    return 2\n",
        )
        _write(
            tmp_path,
            "tests/app/test_boundary.py",
            "def test_app_core():\n"
            '    # frob:tests src/core/__init__.py kind="integration"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"tests/app/test_boundary.py::test_app_core"})
        )
        pol = TestPolicy(min_unit_cases=1, pair_integration=True)
        violations = run_tg(snap, (), Nothing(), tests, pol)
        assert not any(v.rule == "TEST007" for v in violations)


class TestOptInGates:
    """dup_gate/fuzz_gate/perf_gate are opt-in (default off in frob.toml);
    each gate must genuinely no-op when its config key is absent, and this
    is verified against a real GraphSnapshot/Diff rather than mocked."""

    def test_dup_gate_off_by_default(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::dup_gate
        from frob.gates import dup_gate

        _write(tmp_path, "src/a.py", "def foo():\n    return 1\n")
        snap = _snapshot(tmp_path)
        diff = Diff(base="main", hunks=())
        violations = dup_gate(tmp_path, snap, diff)
        assert violations == ()

    def test_fuzz_gate_off_by_default(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::fuzz_gate
        from frob.gates import fuzz_gate

        _write(tmp_path, "src/a.py", "def foo(x: int) -> int:\n    return x\n")
        snap = _snapshot(tmp_path)
        violations = fuzz_gate(tmp_path, snap)
        assert violations == ()

    def test_perf_gate_flags_list_membership_in_loop(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::perf_gate
        from frob.gates import perf_gate

        _write(
            tmp_path,
            "src/a.py",
            "def scan(items):\n"
            "    data = [1, 2, 3]\n"
            "    hits = 0\n"
            "    for x in items:\n"
            "        if x in data:\n"
            "            hits += 1\n"
            "    return hits\n",
        )
        snap = _snapshot(tmp_path)
        violations = perf_gate(tmp_path, snap)
        assert any(v.rule == "PERF001" for v in violations)


class TestScopeDigest:
    def test_digest_is_stable_and_scope_sensitive(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_digest kind="unit"
        from frob.gates import scope_digest

        _write(tmp_path, "src/a.py", "def a():\n    return 1\n")
        _write(tmp_path, "src/b.py", "def b():\n    return 2\n")
        snap = _snapshot(tmp_path)

        digest = scope_digest(("src/a.py",), snap)
        # Deterministic: the same scope over the same snapshot hashes identically.
        assert digest == scope_digest(("src/a.py",), snap)
        assert len(digest) == 64  # sha256 hexdigest
        # A wider scope that pulls in another matching file must change the hash.
        assert scope_digest(("src/*.py",), snap) != digest

    def test_non_matching_scope_is_empty_hash(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_digest kind="unit"
        from frob.gates import scope_digest

        _write(tmp_path, "src/a.py", "def a():\n    return 1\n")
        snap = _snapshot(tmp_path)

        # A scope matching nothing hashes the empty set -- distinct from any
        # scope that matches at least one file, and identical across snapshots.
        empty = scope_digest(("does/not/exist/*.py",), snap)
        assert empty == scope_digest(("nothing_here/*",), snap)
        assert empty != scope_digest(("src/a.py",), snap)


def test_gates_run_gates_integration(tmp_path: Path) -> None:
    # frob:tests src/frob/gates kind="integration"
    # Exercises frob.gates across its real dependency boundary: build_graph
    # (a real snapshot with a doc edge), load_queue, load_lock, and
    # collect_python_tests all feed run_gates, which merges the drift and
    # coverage gate results. A documented public symbol must NOT raise COV001,
    # while an undocumented sibling must -- proving the graph edges reach the
    # coverage gate through the real loader stack, not a stub.
    _write(
        tmp_path,
        "src/frob/pkg/a.py",
        "# frob:doc docs/pkg.md#api\n"
        "def documented(x):\n"
        "    return x\n\n"
        "def undocumented(x):\n"
        "    return x\n",
    )
    _git_init(tmp_path)
    cfg = GateConfig(
        root=str(tmp_path), base="main", gates=frozenset({"drift", "coverage"})
    )
    result = run_gates(cfg)
    assert result.is_ok
    report = result.danger_ok
    cov001 = _by_rule(report.violations, "COV001")
    assert "src/frob/pkg/a.py" in _files(cov001)  # undocumented symbol flagged
    cov001_symbols = {v.message.split()[1] for v in cov001}
    assert any("undocumented" in s for s in cov001_symbols)
    assert not any("::documented" in s for s in cov001_symbols)
