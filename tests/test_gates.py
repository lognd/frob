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
    drift_gate,
    invariant_gate,
    load_coverage,
    prework_gate,
    record_prework,
    run_gates,
    scope_gate,
    stamp_coverage,
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
        assert any(v.rule == "DRIFT001" for v in violations)
        v = next(v for v in violations if v.rule == "DRIFT001")
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
        assert any(v.rule == "DRIFT002" for v in violations)
        v = next(v for v in violations if v.rule == "DRIFT002")
        assert "run: frob ack" in v.message or "candidates" in v.message

    def test_no_drift_when_clean(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::drift_gate
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        violations = drift_gate(snap, LockFile())
        assert violations == ()


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
        assert any(v.rule == "COV002" for v in violations)
        v = next(v for v in violations if v.rule == "COV002")
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
        assert any(v.rule == "COV001" for v in violations)

        from frob.gates import _apply_waivers  # noqa: PLC0415 - internal, test-only

        kept, waived = _apply_waivers(violations, snap)
        assert not any(v.rule == "COV001" for v in kept)
        assert any(v.rule == "COV001" for v in waived)
        assert waived[[v.rule for v in waived].index("COV001")].waived is not None

    def test_waive001_missing_reason(self, tmp_path: Path) -> None:
        source = "def helper(x):\n    # frob:waive COV001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates import _waive001_violations  # noqa: PLC0415

        violations = _waive001_violations(snap)
        assert any(v.rule == "WAIVE001" for v in violations)
        assert violations[0].severity == Severity.ERROR


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
        inv = Invariant(id="INV-001", statement="x", criticality=Criticality.HIGH, evidence=())
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
            id="INV-001", statement="x", criticality=Criticality.HIGH, evidence=("POL-thing",)
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
        assert any(v.rule == "TEST002" for v in violations)
        assert not any(v.rule == "TEST001" for v in violations)

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
    # frob:tests src/frob/gates/__init__.py::scope_digest
    def test_override_downgrades_and_ignores_garbage(self, tmp_path, monkeypatch):
        from frob.gates import Severity, Violation, _apply_severity_overrides

        (tmp_path / "frob.toml").write_text(
            '[gates.severity]\nCOV001 = "warn"\nDRIFT001 = "error"\nBAD = "loud"\n',
            encoding="utf-8",
        )
        violations = (
            Violation(
                rule="COV001", severity=Severity.ERROR, file="a.py", line=1,
                message="m",
            ),
            Violation(
                rule="SCOPE001", severity=Severity.ERROR, file="b.py", line=2,
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
                rule="COV001", severity=Severity.ERROR, file="a.py", line=1,
                message="m",
            ),
        )
        assert _apply_severity_overrides(violations, tmp_path) == violations


class TestDoclinkGate:
    # frob:tests src/frob/gates/__init__.py::doclink_gate
    def test_orphan_doc_is_error_and_linked_docs_pass(self, tmp_path):
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
        orphans = {v.file for v in violations}
        assert orphans == {"docs/orphan.md"}
        assert all(v.rule == "DOC001" for v in violations)

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
            TicketSpec(title="refactor", kind=TicketKind.FEATURE,
                       origin=Origin.AGENT, scope=("src/**",)),
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
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_m.py::test_unrelated"})
        )
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
