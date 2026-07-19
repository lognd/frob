"""Tests for frob.gates: drift, coverage, scope, pre-work, invariant, test gates."""

from __future__ import annotations

import builtins
import json
import subprocess
from datetime import date
from pathlib import Path

import pytest

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
    sys_gate,
    violation_fingerprint,
)
from frob.gates import (
    test_gate as run_test_gate,
)
from frob.gates.invariants import Criticality, InvariantError, load_invariants
from frob.gitio import Diff, Hunk, working_diff
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


def _marker_line(root: Path, ticket_id: str) -> int:
    """The 1-indexed line number of `ticket_id`'s `<!-- ticket:... -->`
    marker in `root/tickets.md`, for building a `Hunk` span that targets
    exactly that ticket's ledger entry."""
    marker = f"<!-- ticket:{ticket_id} -->"
    lines = (root / "tickets.md").read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, start=1):
        if marker in line:
            return i
    raise AssertionError(f"marker for {ticket_id} not found in tickets.md")


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

    def test_cov001_message_wording_for_docstring_without_doc_edge(
        self, tmp_path: Path
    ) -> None:
        # T-0213: a symbol with a docstring but no `frob:doc` edge must still
        # be flagged (a docstring alone does not satisfy COV001), and the
        # violation message must say so accurately -- not "undocumented",
        # which misleads adopters into thinking the docstring should have
        # been enough.
        _write(
            tmp_path,
            "src/a.py",
            'def helper(x):\n    """Docstring present, but no frob:doc edge."""\n    return x\n',
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        cov001 = [v for v in violations if v.rule == "COV001" and "helper" in v.message]
        assert len(cov001) == 1
        assert "no frob:doc edge" in cov001[0].message
        assert "undocumented" not in cov001[0].message

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

    def test_cov002_done_ticket_covers_own_closing_diff(self, tmp_path: Path) -> None:
        """T-0214: closing the covering ticket in the same uncommitted diff
        that edits the symbol it covers must not turn into a COV002 hard
        error -- the catch-22 this ticket fixes. THIS ticket's own
        `<!-- ticket:T-0001 -->` marker falling inside the touched
        `tickets.md` hunk span is the grace-window signal (not merely
        `tickets.md` being touched anywhere)."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        ticket = _ticket(state=TicketState.DONE)
        _write_ticket(tmp_path, ticket)
        marker_line = _marker_line(tmp_path, "T-0001")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        diff = Diff(
            base="x",
            hunks=(
                Hunk(file="src/a.py", span=record.span),
                Hunk(file="tickets.md", span=(marker_line, marker_line)),
            ),
        )
        queue = TicketQueue(tickets={"T-0001": ticket})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        assert not any(v.rule == "COV002" for v in violations)

    def test_cov002_done_ticket_without_grace_still_fires(self, tmp_path: Path) -> None:
        """A `DONE` ticket whose close already landed as a separate commit
        (so `tickets.md` is no longer part of this diff) must NOT cover a
        later, genuinely unrelated touch to the same symbol -- the grace
        window in test_cov002_done_ticket_covers_own_closing_diff
        must not weaken COV002 for a real coverage gap."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.DONE)})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        v = _first_rule(violations, "COV002")
        assert v is not None
        assert "frob ticket new" in v.message

    def test_cov002_stale_done_ticket_unrelated_tickets_md_touch_still_fires(
        self, tmp_path: Path
    ) -> None:
        """T-0214 bypass regression (reviewer-reproduced): a symbol bound via
        `frob:ticket` to an OLD, already-`DONE` ticket (T-0001, closed long
        ago, not part of this diff) must still fire COV002 even when the
        diff's `tickets.md` hunk touches a *different*, unrelated ticket
        (T-0002). Grace must be scoped to the specific ticket whose own
        marker is in the touched hunk -- "tickets.md was touched somewhere"
        is not sufficient, or every stale DONE ticket edge would silently
        pass coverage forever."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        stale_ticket = _ticket(ticket_id="T-0001", state=TicketState.DONE)
        _write_ticket(tmp_path, stale_ticket)
        unrelated_ticket = _ticket(ticket_id="T-0002", state=TicketState.DONE)
        _write_ticket(tmp_path, unrelated_ticket)
        marker_line = _marker_line(tmp_path, "T-0002")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        diff = Diff(
            base="x",
            hunks=(
                Hunk(file="src/a.py", span=record.span),
                # tickets.md is touched, but only T-0002's hunk -- T-0001's
                # own marker is nowhere in this diff.
                Hunk(file="tickets.md", span=(marker_line, marker_line)),
            ),
        )
        queue = TicketQueue(
            tickets={"T-0001": stale_ticket, "T-0002": unrelated_ticket}
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(snap, queue, diff, tests)
        v = _first_rule(violations, "COV002")
        assert v is not None
        assert "frob ticket new" in v.message

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

    def test_cov003_passes_for_rust_evidence_id(self, tmp_path: Path) -> None:
        """T-0092: a done ticket citing a cargo test id resolves against
        `collect_rust_tests`' node ids the same way a pytest id resolves
        against `collect_python_tests`' -- COV003 is language-agnostic once
        the id lands in `CollectedTests.node_ids` (merged by
        `frob.gates._load_tests`)."""
        snap = _snapshot(tmp_path)
        node = "strata-core/src/lib.rs::tests::reachable_returns_witness_paths"
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

    def test_load_tests_merges_python_and_rust_node_ids(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-0092: `_load_tests` merges `collect_python_tests` and
        `collect_rust_tests` into one `CollectedTests`, each collector
        degrading independently (a broken cargo toolchain must not blank
        out python evidence, and vice versa)."""
        from typani import Err, Ok

        import frob.gates as gates_mod
        from frob.testing import TestingError

        monkeypatch.setattr(
            gates_mod,
            "collect_python_tests",
            lambda root: Ok(
                CollectedTests(node_ids=frozenset({"tests/test_x.py::test_a"}))
            ),
        )
        monkeypatch.setattr(
            gates_mod,
            "collect_rust_tests",
            lambda root: Ok(
                CollectedTests(node_ids=frozenset({"crate/src/lib.rs::tests::foo"}))
            ),
        )
        merged = gates_mod._load_tests(tmp_path)
        assert merged.node_ids == frozenset(
            {"tests/test_x.py::test_a", "crate/src/lib.rs::tests::foo"}
        )

        # A broken rust collector degrades to "no rust ids", not a crash and
        # not a wipe of the python ids already collected.
        monkeypatch.setattr(
            gates_mod,
            "collect_rust_tests",
            lambda root: Err(TestingError.CollectFailed),
        )
        merged2 = gates_mod._load_tests(tmp_path)
        assert merged2.node_ids == frozenset({"tests/test_x.py::test_a"})

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

    def test_scope001_exempts_file_committed_by_earlier_ticket(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # Reproduces T-0108: ticket A commits within its own scope, then ticket
        # B's scope check must not flag A's already-committed file.
        _git_init(tmp_path)
        _write_ticket(
            tmp_path,
            _ticket(ticket_id="T-0001", scope=("src/a/**",)),
        )
        _write_ticket(
            tmp_path,
            _ticket(ticket_id="T-0002", scope=("src/b/**",)),
        )
        subprocess.run(
            ["git", "checkout", "-q", "-b", "work"], cwd=tmp_path, check=True
        )
        _write(tmp_path, "src/a/mod.py", "def f():\n    return 1\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat(a): add mod (T-0001)"],
            cwd=tmp_path,
            check=True,
        )
        queue = TicketQueue(
            tickets={
                "T-0001": _ticket(ticket_id="T-0001", scope=("src/a/**",)),
                "T-0002": _ticket(ticket_id="T-0002", scope=("src/b/**",)),
            }
        )
        diff = working_diff(tmp_path, "main").danger_ok
        snap = _snapshot(tmp_path)
        ticket_b = _ticket(ticket_id="T-0002", scope=("src/b/**",))

        # Without root/queue (old behavior): false positive SCOPE001 on A's file.
        violations_no_context = scope_gate(diff, ticket_b, snap)
        assert any(v.file == "src/a/mod.py" for v in violations_no_context)

        # With root/queue: T-0001's committed file is exempt from T-0002's check.
        violations = scope_gate(diff, ticket_b, snap, root=tmp_path, queue=queue)
        assert not any(v.file == "src/a/mod.py" for v in violations)

    def test_scope001_still_flags_uncommitted_out_of_scope_edit(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # The exemption must not swallow a ticket's own dirty, out-of-scope edit.
        _git_init(tmp_path)
        _write_ticket(tmp_path, _ticket(ticket_id="T-0002", scope=("src/b/**",)))
        _write(tmp_path, "src/a/mod.py", "def f():\n    return 1\n")
        queue = TicketQueue(
            tickets={"T-0002": _ticket(ticket_id="T-0002", scope=("src/b/**",))}
        )
        diff = working_diff(tmp_path, "main").danger_ok
        snap = _snapshot(tmp_path)
        ticket_b = _ticket(ticket_id="T-0002", scope=("src/b/**",))

        violations = scope_gate(diff, ticket_b, snap, root=tmp_path, queue=queue)
        assert any(v.file == "src/a/mod.py" for v in violations)

    def test_scope001_does_not_exempt_when_referenced_ticket_lacks_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # A commit referencing a ticket that doesn't declare the file in its own
        # scope must not grant an exemption.
        _git_init(tmp_path)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "work"], cwd=tmp_path, check=True
        )
        _write(tmp_path, "src/a/mod.py", "def f():\n    return 1\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat(a): add mod (T-0001)"],
            cwd=tmp_path,
            check=True,
        )
        queue = TicketQueue(
            tickets={
                "T-0001": _ticket(ticket_id="T-0001", scope=("src/other/**",)),
                "T-0002": _ticket(ticket_id="T-0002", scope=("src/b/**",)),
            }
        )
        diff = working_diff(tmp_path, "main").danger_ok
        snap = _snapshot(tmp_path)
        ticket_b = _ticket(ticket_id="T-0002", scope=("src/b/**",))

        violations = scope_gate(diff, ticket_b, snap, root=tmp_path, queue=queue)
        assert any(v.file == "src/a/mod.py" for v in violations)

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
        evidence. T-0092 gave rust a real execution-based collector
        (`collect_rust_tests`), so this now asserts through the FIRST branch
        of `_valid_edges` (real collected node id), not the structural
        fallback the T-0090 comment used to describe -- `.rs` was removed
        from `_NATIVE_TEST_EXTENSIONS` accordingly."""
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
        tests = CollectedTests(
            node_ids=frozenset({"strata-core/src/parse.rs::test_parse_basic"})
        )
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

    def test_test003_satisfied_by_parametrized_test_node_id(
        self, tmp_path: Path
    ) -> None:
        """Root-cause regression (feldspar FROBLEMS.md 2026-07-18,
        `test_library_thermo.py`): a `frob:tests` directive bound to a
        `@pytest.mark.parametrize`-decorated test looked like a broken
        comment-to-decorator attachment, but `frob.lang._extract` already
        resolves that binding correctly -- the real mismatch is that
        `pytest --collect-only` never emits the bare `path::func` node id
        for a parametrized test, only per-case `path::func[case-id]`
        ids, so an exact `in tests.node_ids` membership check could never
        validate a directive whose src is the bare (unparametrized)
        symref. `_node_id_collected` must accept any collected id that is
        the base id itself OR a `[...]`-suffixed parametrized expansion
        of it."""
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/thermo.py", "def helper(x):\n    return x\n")
        test_source = (
            '# frob:tests src/frob/pkg/thermo.py kind="integration"\n'
            "@pytest.mark.parametrize('x', [1, 2])\n"
            "def test_density(x):\n"
            "    assert True\n"
        )
        _write(tmp_path, "tests/test_thermo.py", test_source)
        snap = _snapshot(tmp_path)
        # Exactly what pytest --collect-only emits for a parametrized test:
        # bracketed per-case ids, never the bare function name.
        tests = CollectedTests(
            node_ids=frozenset(
                {
                    "tests/test_thermo.py::test_density[1]",
                    "tests/test_thermo.py::test_density[2]",
                }
            )
        )
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST003" not in _rules(violations)

    def test_test003_satisfied_by_proptest_macro_block(self, tmp_path: Path) -> None:
        """T-0318 litmus (feldspar): a `frob:tests` comment sitting directly
        above a `proptest! { ... }` block must satisfy TEST003. proptest's
        expansion synthesizes real `#[test]` fns at compile time (one per
        `fn` inside the macro's braces), which `cargo test --list` collects
        under THEIR OWN names -- never under a `proptest`-named node id --
        and tree-sitter parses the macro's braces as one opaque `token_tree`
        with no `function_item` descendants at all, so the directive has no
        literal AST node to bind to without `_walk_rust.py` emitting a
        stand-in symbol for the macro block itself (`_macro_symbol`).
        `_macro_symbol_file`/`_macro_file_collected` then resolve that
        stand-in's TESTS edge at file granularity: satisfied because the
        file has >=1 real collected case, not because any node id matches
        the stand-in's own synthesized qualname (which never collects)."""
        from typani.option import Nothing

        _write(
            tmp_path,
            "strata-core/src/lib.rs",
            "pub fn parse_source(x: &str) -> i32 {\n    0\n}\n",
        )
        _write(
            tmp_path,
            "strata-core/tests/prop_parse.rs",
            '// frob:tests strata-core/src/lib.rs kind="integration"\n'
            "proptest! {\n"
            "    #[test]\n"
            "    fn prop_parse_roundtrip(x in 0..100u32) {\n"
            "        assert!(x < 100);\n"
            "    }\n"
            "}\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset(
                {
                    "strata-core/tests/prop_parse.rs::prop_parse_roundtrip",
                }
            )
        )
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST003" not in _rules(violations)

    def test_test002_parametrized_test_counts_each_case(self, tmp_path: Path) -> None:
        """T-0307 litmus: a `frob:tests` directive bound to a
        `@pytest.mark.parametrize`-decorated test with 3 cases must count
        as 3 collected unit cases, not 1. Before the fix, `_valid_edges`
        returned one Edge per directive and `_test001_002_one` used
        `len(valid)` as the case count -- so a parametrized test with any
        number of collected `[case-id]` variants always reported exactly 1
        case, silently failing to clear `min_unit_cases > 1` no matter how
        many cases actually ran (lograder/aprog-public/feldspar all hit
        this and worked around it with dishonest non-parametrized twin
        tests). `min_unit_cases=3` here would fail pre-fix (effective=1)
        and passes post-fix (effective=3, one per collected case id)."""
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        test_source = (
            "@pytest.mark.parametrize('x', [1, 2, 3])\n"
            "def test_helper(x):\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n"
        )
        _write(tmp_path, "tests/test_a.py", test_source)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset(
                {
                    "tests/test_a.py::test_helper[1]",
                    "tests/test_a.py::test_helper[2]",
                    "tests/test_a.py::test_helper[3]",
                }
            )
        )
        cfg = TestPolicy(min_unit_cases=3)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST002" not in rule_ids
        assert "TEST001" not in rule_ids

    def test_case_count_direct(self) -> None:
        """Direct unit coverage of `_case_count` (T-0307): a valid edge's
        collected cases are counted individually (parametrize expansions),
        and a validated edge with no execution-based match (native
        structural fallback) still counts as exactly one case."""
        from frob.gates import _case_count
        from frob.graph import Edge, EdgeKind

        ids = frozenset(
            {
                "tests/test_x.py::test_density[1]",
                "tests/test_x.py::test_density[2]",
                "tests/test_x.py::test_density[3]",
            }
        )
        tests = CollectedTests(node_ids=ids)
        edge = Edge(
            kind=EdgeKind.TESTS,
            src="tests/test_x.py::test_density",
            target="src/frob/pkg/a.py::helper",
            origin="tests/test_x.py:1",
        )
        assert _case_count([edge], tests) == 3

        # An edge with no matching collected id at all (structural
        # fallback territory) still contributes exactly one case.
        empty_tests = CollectedTests(node_ids=frozenset())
        assert _case_count([edge], empty_tests) == 1

    def test_node_id_collected_direct(self) -> None:
        """Direct unit coverage of `_node_id_collected` itself, independent
        of the gate machinery around it."""
        from frob.gates import _node_id_collected

        ids = frozenset(
            {"tests/test_x.py::test_density[1]", "tests/test_x.py::test_density[2]"}
        )
        assert _node_id_collected("tests/test_x.py::test_density", ids)
        assert _node_id_collected("tests/test_x.py::test_density[1]", ids)
        assert not _node_id_collected("tests/test_x.py::test_other", ids)
        # a bare-prefix collision must not false-positive
        assert not _node_id_collected("tests/test_x.py::test_dens", ids)

    def test_test003_waiver_in_a_file_under_the_package_matches(
        self, tmp_path: Path
    ) -> None:
        """T-0276: TEST003's `violation.file` is a PACKAGE interface id
        (e.g. `crates/feldspar-core/src`), never a real single file --
        found while investigating why a `frob:waive TEST003 reason="..."`
        written in a rust integration test file reported `0 waived` in
        feldspar's adoption sweep. Root cause was NOT check_type gating
        `.rs` directives (disproven directly: build_graph/_load_tests are
        check_type-agnostic) -- it was that `_match_waiver`'s file-scoped
        comparison required the waiver's own file to be LITERALLY EQUAL
        to the package id string, which no real file path (always has an
        extension) can ever be. A waiver written in any file living
        under that package directory must now match."""
        from typani.option import Nothing

        from frob.gates import _apply_waivers  # noqa: PLC0415

        _write(
            tmp_path,
            "src/frob/pkg/a.py",
            '# frob:waive TEST003 reason="covered elsewhere"\n'
            "def helper(x):\n"
            "    return x\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert any(v.rule == "TEST003" for v in violations)

        kept, waived = _apply_waivers(violations, snap)
        assert not any(v.rule == "TEST003" for v in kept)
        assert any(v.rule == "TEST003" for v in waived)

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

    def test_test005_skips_test_file_symbols(self, tmp_path: Path) -> None:
        # T-0301: TEST005's per-symbol branch floor must skip test-file
        # symbols exactly like TEST001/TEST002 (_is_test_file) -- a test
        # fixture measured below the floor must not fire, matching the
        # existing skip other TEST rules already apply.
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "tests/test_a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["tests/test_a.py::helper"]
        coverage = CoverageData(
            source_sha="x", symbol_branch={record.symref: 40.0}, module_line={}
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(unit_branch_cov=90)
        )
        assert not any(
            v.rule == "TEST005" and v.file == record.id.path for v in violations
        )

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

    def test_test008_fires_on_unjoined_root(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test008_unjoined_root
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"nope.py": 0.0},
            root_join_ok=False,
            attempted_roots=("wrong/root", ""),
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        test008 = [v for v in violations if v.rule == "TEST008"]
        assert len(test008) == 1
        assert test008[0].severity == Severity.ERROR

    def test_test008_silent_when_root_joined(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test008_unjoined_root
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 100.0},
            root_join_ok=True,
            attempted_roots=("src/frob",),
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(module_line_cov=0)
        )
        assert not any(v.rule == "TEST008" for v in violations)

    def test_test008_cannot_be_waived(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_match_waiver
        # TEST008 is unwaivable BY CONSTRUCTION (_UNWAIVABLE_RULES), not
        # just by nobody thinking to try -- a same-repo `frob:waive
        # TEST008` directive must never suppress it, since this gate's
        # entire purpose is staying loud in every sibling repo it runs in.
        source = (
            '# frob:waive TEST008 reason="pretend this is fine"\n'
            "def helper(x):\n"
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from typani.option import Some  # noqa: PLC0415

        from frob.gates import CoverageData, _apply_waivers  # noqa: PLC0415

        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={},
            root_join_ok=False,
            attempted_roots=("wrong/root", ""),
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        assert any(v.rule == "TEST008" for v in violations)

        kept, waived = _apply_waivers(violations, snap)
        assert any(v.rule == "TEST008" for v in kept)
        assert not any(v.rule == "TEST008" for v in waived)

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
        # frob:ticket T-0148
        # Cobertura `<class filename>` attrs are
        # relative to whatever `--cov=` target produced the report (e.g.
        # "pkg/a.py" for a `--cov=src/frob` run), not repo-relative --
        # load_coverage re-roots them using the `<sources><source>` entry
        # Cobertura itself declares (_coverage.py::_parse_classes), rather
        # than a hardcoded prefix (a hardcode would silently zero-match in
        # any sibling repo with a different package root).
        xml = f"""<?xml version="1.0"?>
<coverage>
  <sources>
    <source>{(tmp_path / "src/frob").resolve()}</source>
  </sources>
  <packages>
    <package>
      <classes>
        <class filename="pkg/a.py" line-rate="0.5">
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
        assert data.root_join_ok

    def test_joins_via_repo_relative_source(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage
        # A non-frob layout: package lives at the repo root, no `src/`
        # tree at all (e.g. a sibling repo like typani or logand.app) --
        # proves the join is not frob-specific.
        _write(tmp_path, "mypkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["mypkg/a.py::helper"]
        start = record.span[0]
        xml = f"""<?xml version="1.0"?>
<coverage>
  <sources>
    <source>mypkg</source>
  </sources>
  <packages>
    <package>
      <classes>
        <class filename="a.py" line-rate="1.0">
          <lines>
            <line number="{start}" hits="1" branch="false"/>
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
        assert data.module_line["mypkg/a.py"] == 100.0
        assert record.symref in data.symbol_branch
        assert data.root_join_ok

    def test_multi_source_picks_the_root_that_joins(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage
        # Multiple <source> entries (a monorepo-style coverage run) --
        # only one of them actually resolves any class; that one wins.
        _write(tmp_path, "backend/svc/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["backend/svc/a.py::helper"]
        start = record.span[0]
        xml = f"""<?xml version="1.0"?>
<coverage>
  <sources>
    <source>frontend/app</source>
    <source>backend/svc</source>
  </sources>
  <packages>
    <package>
      <classes>
        <class filename="a.py" line-rate="1.0">
          <lines>
            <line number="{start}" hits="1" branch="false"/>
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
        assert data.module_line["backend/svc/a.py"] == 100.0
        assert record.symref in data.symbol_branch
        assert data.root_join_ok

    def test_multi_root_resolves_each_class_to_its_real_root(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage
        # T-0311: two <source> roots declared (a `--cov=scripts --cov=tests`
        # style run); a class filename that exists under ONLY ONE of them
        # must resolve to that root, never to the OTHER declared root just
        # because it happened to win the aggregate per-report vote (e.g. by
        # having more matching classes, or by declaration order on a tie).
        _write(tmp_path, "scripts/actgen/core.py", "def helper(x):\n    return x\n")
        _write(tmp_path, "tests/actgen/other.py", "def other(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["scripts/actgen/core.py::helper"]
        start = record.span[0]
        other_record = snap.symbols["tests/actgen/other.py::other"]
        other_start = other_record.span[0]
        xml = f"""<?xml version="1.0"?>
<coverage>
  <sources>
    <source>{(tmp_path / "tests").resolve()}</source>
    <source>{(tmp_path / "scripts").resolve()}</source>
  </sources>
  <packages>
    <package>
      <classes>
        <class filename="actgen/core.py" line-rate="0.0">
          <lines>
            <line number="{start}" hits="0" branch="false"/>
          </lines>
        </class>
        <class filename="actgen/other.py" line-rate="1.0">
          <lines>
            <line number="{other_start}" hits="1" branch="false"/>
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
        # The 0%-covered class must be labeled under "scripts/", the root
        # it actually lives under -- not "tests/" (a different declared
        # root that also happens to contain an "actgen/" subdirectory).
        assert "scripts/actgen/core.py" in data.module_line
        assert "tests/actgen/core.py" not in data.module_line
        assert data.module_line["scripts/actgen/core.py"] == 0.0
        assert "tests/actgen/other.py" in data.module_line

    def test_zero_join_is_loud_not_silent(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage
        # Every candidate root -- the declared <source> AND the bare
        # filename fallback -- fails to resolve any class: this must be
        # reported (root_join_ok=False), never a quiet empty map.
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        xml = """<?xml version="1.0"?>
<coverage>
  <sources>
    <source>completely/wrong/root</source>
  </sources>
  <packages>
    <package>
      <classes>
        <class filename="nope.py" line-rate="0.0">
          <lines>
            <line number="1" hits="0" branch="false"/>
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
        assert not data.root_join_ok
        assert len(data.attempted_roots) == 2
        assert data.symbol_branch == {}

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

    def test_orphan_hint_does_not_point_at_missing_docs_root(self, tmp_path):
        # frob:tests src/frob/gates/__init__.py::doclink_gate kind="unit"
        # T-0231: default roots=["docs/index.md", "README.md"] but neither
        # exists in this repo (sibling-repo "lithos" precedent, 256 hits) --
        # the hint must not blindly name docs/index.md as if it were there.
        from frob.gates import doclink_gate
        from frob.graph import build_graph

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "orphan.md").write_text("# Orphan\n", encoding="utf-8")

        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = doclink_gate(root, snap)
        assert len(violations) == 1
        message = violations[0].message
        assert "docs/index.md" not in message or "create it" in message
        assert "no configured docs root exists" in message or "create it" in message


class TestDocanchorGate:
    def _snap(self, root: Path):
        from frob.graph import build_graph

        return build_graph(root, root / ".frob" / "cache.db").danger_ok

    def test_resolvable_heading_and_explicit_anchor_pass(self, tmp_path):
        # frob:tests src/frob/gates/__init__.py::docanchor_gate kind="unit"
        from frob.gates import docanchor_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "docs" / "m.md").write_text(
            '# Title\n\n## Public API\n\n<a id="widget"></a>\n', encoding="utf-8"
        )
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/m.md#public-api\ndef f():\n    return 1\n\n\n"
            "# frob:doc docs/m.md#widget\ndef g():\n    return 2\n",
            encoding="utf-8",
        )
        violations = docanchor_gate(root, self._snap(root))
        assert violations == ()

    def test_unresolvable_anchor_fires(self, tmp_path):
        from frob.gates import docanchor_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "docs" / "m.md").write_text(
            "# Title\n\n## Real Heading\n", encoding="utf-8"
        )
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/m.md#nonexistent-slug\ndef f():\n    return 1\n",
            encoding="utf-8",
        )
        violations = docanchor_gate(root, self._snap(root))
        assert set(_rules(violations)) == {"DOC002"}
        assert any("nonexistent-slug" in v.message for v in violations)

    def test_unresolvable_anchor_reports_slug_and_nearest_match(self, tmp_path):
        # frob:tests src/frob/gates/__init__.py::_anchor_mismatch_message kind="unit"
        from frob.gates import docanchor_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "docs" / "m.md").write_text(
            "# Title\n\n## Real Heading\n", encoding="utf-8"
        )
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/m.md#real-headin\ndef f():\n    return 1\n",
            encoding="utf-8",
        )
        violations = docanchor_gate(root, self._snap(root))
        assert set(_rules(violations)) == {"DOC002"}
        (message,) = [v.message for v in violations]
        assert "computed slug #real-headin" in message
        assert "found: real-heading" in message
        assert "did you mean #real-heading?" in message

    def test_missing_file_fires(self, tmp_path):
        from frob.gates import docanchor_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/does_not_exist.md#anything\ndef f():\n    return 1\n",
            encoding="utf-8",
        )
        violations = docanchor_gate(root, self._snap(root))
        assert set(_rules(violations)) == {"DOC002"}
        assert any("does not exist" in v.message for v in violations)

    def test_malformed_target_missing_fragment_fires(self, tmp_path):
        from frob.gates import docanchor_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "docs" / "m.md").write_text("# Title\n", encoding="utf-8")
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/m.md\ndef f():\n    return 1\n", encoding="utf-8"
        )
        violations = docanchor_gate(root, self._snap(root))
        assert set(_rules(violations)) == {"DOC002"}
        assert any("no #anchor" in v.message for v in violations)


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


class TestCov002StrataModuleCoverage:
    # frob:ticket T-0164
    """COV002 must not demand a per-declaration `frob:ticket` edge inside a
    `.strata` file -- one edge on the owning `module` covers every `node`/
    `flow`/`assert`/... nested inside it (T-0164)."""

    def _init_repo(self, tmp_path: Path) -> None:
        """Shared git scaffolding for the COV002 strata-module tests."""
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)

    # frob:tests tests/test_gates.py::TestCov002StrataModuleCoverage.test_module_level_ticket_edge_covers_nested_declaration
    def test_module_level_ticket_edge_covers_nested_declaration(
        self, tmp_path: Path
    ) -> None:
        """A `frob:ticket` directive on `module m` covers a changed nested
        `node` declaration -- no per-declaration edge required."""
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

        self._init_repo(tmp_path)
        (tmp_path / "design").mkdir()
        base = (
            "// frob:ticket T-9001\n"
            "module m\n"
            "node client : foreign { clearance Public; }\n"
        )
        _write(tmp_path, "design/m.strata", base)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=tmp_path, check=True)

        t = new_ticket(
            tmp_path,
            TicketSpec(
                title="strata module coverage",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
            ),
        ).danger_ok
        # rewrite T-9001's id in-place so the fixture's frob:ticket directive
        # resolves to a real open ticket without hard-coding new_ticket's id.
        strata_path = tmp_path / "design" / "m.strata"
        strata_path.write_text(
            base.replace("T-9001", t.id).replace(
                "node client : foreign { clearance Public; }",
                "node client : foreign { clearance Internal; }",
            ),
            encoding="utf-8",
        )
        transition(tmp_path, t.id, TicketState.PLANNED)
        transition(tmp_path, t.id, TicketState.IN_PROGRESS)

        report = run_gates(
            GateConfig(root=str(tmp_path), base="main", gates=frozenset({"coverage"}))
        ).danger_ok
        assert not [v for v in report.violations if v.rule == "COV002"]

    # frob:tests tests/test_gates.py::TestCov002StrataModuleCoverage.test_declaration_without_module_edge_still_fires
    def test_declaration_without_module_edge_still_fires(self, tmp_path: Path) -> None:
        """No `frob:ticket` anywhere in the `.strata` file -> COV002 still
        fires on the changed nested declaration (the escape hatch is not a
        blanket exemption for `.strata` files)."""
        import subprocess

        from frob.gates import GateConfig, run_gates

        self._init_repo(tmp_path)
        (tmp_path / "design").mkdir()
        _write(
            tmp_path,
            "design/m.strata",
            "module m\nnode client : foreign { clearance Public; }\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=tmp_path, check=True)
        _write(
            tmp_path,
            "design/m.strata",
            "module m\nnode client : foreign { clearance Internal; }\n",
        )

        report = run_gates(
            GateConfig(root=str(tmp_path), base="main", gates=frozenset({"coverage"}))
        ).danger_ok
        assert any(v.rule == "COV002" for v in report.violations)


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

    # frob:tests tests/test_gates.py::TestConventionUnitBinding.test_test001_exempts_strata_flow_declarations kind="unit"
    def test_test001_exempts_strata_flow_declarations(self, tmp_path):
        """T-0168: a `flow` (or other) `.strata` declaration has no defined
        "unit test" meaning -- design conformance is proven by the sys
        gates (`frob sys audit`/self-conformance), not pytest bindings.
        TEST001 must not demand a `frob:tests` edge for it, with no
        matching test and no edge at all."""
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Nothing(), tests, TestPolicy(min_unit_cases=1)
        )
        assert not any(
            v.rule in ("TEST001", "TEST002") and v.file == "design/m.strata"
            for v in violations
        )


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

    # Bodies padded past DupConfig's default min_tokens=40 floor (dup_gate's
    # frob.toml reader only exposes enforce/threshold, not min_tokens, so
    # the fixture must clear the real default rather than a lowered one).
    _DUP_CLONE_SOURCE = (
        "def compute_total(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total = total + item\n"
        "        if total > 1000:\n"
        "            total = 1000\n"
        "        total = total - 0\n"
        "        total = total + 0\n"
        "        total = total - 0\n"
        "        total = total + 0\n"
        "        total = total - 0\n"
        "    return total\n"
        "\n"
        "\n"
        "def compute_sum(values):\n"
        "    total = 0\n"
        "    for value in values:\n"
        "        total = total + value\n"
        "        if total > 1000:\n"
        "            total = 1000\n"
        "        total = total - 0\n"
        "        total = total + 0\n"
        "        total = total - 0\n"
        "        total = total + 0\n"
        "        total = total - 0\n"
        "    return total\n"
    )

    def test_dup_gate_fires_on_planted_clone_when_enabled(self, tmp_path: Path) -> None:
        """T-0191: [dup].enforce=true wires the smart R1-R5 pipeline into the
        gate -- a planted alpha-renamed clone (compute_total/compute_sum,
        identical after R3 canonicalization) must fail the gate when one
        side is touched."""
        # frob:tests src/frob/gates/__init__.py::dup_gate
        from frob.dup import _core as dup_core
        from frob.gates import dup_gate

        if not dup_core.core_available():
            pytest.skip("frob-core native extension not installed")
        _write(tmp_path, "src/a.py", self._DUP_CLONE_SOURCE)
        _write(
            tmp_path,
            "frob.toml",
            "[dup]\nenforce = true\nthreshold = 0.8\n",
        )
        snap = _snapshot(tmp_path)
        # compute_total is the first symbol in the file (lines 1-12).
        diff = Diff(base="main", hunks=(Hunk(file="src/a.py", span=(1, 12)),))
        violations = dup_gate(tmp_path, snap, diff)
        assert any(v.rule == "DUP001" for v in violations), violations

    def test_dup_gate_planted_clone_waived_passes(self, tmp_path: Path) -> None:
        """T-0191: a `frob:waive DUP001 reason=...` directive on the touched
        clone suppresses the violation via the normal waiver path -- the
        gate itself still reports it (waiving happens post-gate), but
        `_apply_waivers` removes it from the kept set with a reason."""
        from frob.dup import _core as dup_core
        from frob.gates import _apply_waivers, dup_gate

        if not dup_core.core_available():
            pytest.skip("frob-core native extension not installed")
        waived_source = (
            "def compute_total(items):\n"
            '    # frob:waive DUP001 reason="known clone, tracked in T-0191 fixture"\n'
            "    total = 0\n"
            "    for item in items:\n"
            "        total = total + item\n"
            "        if total > 1000:\n"
            "            total = 1000\n"
            "        total = total - 0\n"
            "        total = total + 0\n"
            "        total = total - 0\n"
            "        total = total + 0\n"
            "        total = total - 0\n"
            "    return total\n"
            "\n"
            "\n"
            "def compute_sum(values):\n"
            "    total = 0\n"
            "    for value in values:\n"
            "        total = total + value\n"
            "        if total > 1000:\n"
            "            total = 1000\n"
            "        total = total - 0\n"
            "        total = total + 0\n"
            "        total = total - 0\n"
            "        total = total + 0\n"
            "        total = total - 0\n"
            "    return total\n"
        )
        _write(tmp_path, "src/a.py", waived_source)
        _write(
            tmp_path,
            "frob.toml",
            "[dup]\nenforce = true\nthreshold = 0.8\n",
        )
        snap = _snapshot(tmp_path)
        diff = Diff(base="main", hunks=(Hunk(file="src/a.py", span=(1, 13)),))
        violations = dup_gate(tmp_path, snap, diff)
        assert any(v.rule == "DUP001" for v in violations), violations

        kept, waived = _apply_waivers(violations, snap)
        assert _first_rule(kept, "DUP001") is None
        waived_dup001 = _first_rule(waived, "DUP001")
        assert waived_dup001 is not None
        assert waived_dup001.waived is not None

    def test_fuzz_gate_off_by_default(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::fuzz_gate
        # frob:tests src/frob/fuzz kind="integration"
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

    def test_perf_gate_silences_unscannable_files(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::perf_gate
        # T-0203: non-code files (md/toml/json) have no registered tree-sitter
        # grammar and are unscannable by design -- perf_gate must filter them
        # out by extension before ever calling parse_file, so no
        # UnsupportedLanguage skip line is emitted for any of them.
        from frob.gates import perf_gate

        _write(tmp_path, "src/a.py", "def scan(x):\n    return x\n")
        _write(tmp_path, "docs/guides/agent-playbook.md", "# Playbook\n\nSome text.\n")
        _write(tmp_path, "pyproject.toml", "[project]\nname = 'x'\n")
        _write(tmp_path, "data.json", '{"key": "value"}\n')
        snap = _snapshot(tmp_path)

        with caplog.at_level("DEBUG", logger="frob.gates"):
            violations = perf_gate(tmp_path, snap)

        assert violations == ()
        assert not any("skipping unparsed" in rec.message for rec in caplog.records)
        assert not any("UnsupportedLanguage" in rec.message for rec in caplog.records)

    def test_perf_gate_still_reports_genuine_parse_failure(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::perf_gate
        # T-0203: a file with a registered grammar (.py) that still fails to
        # parse is a real failure, not a by-design skip -- it must still get
        # a visible skip message. tree-sitter's python grammar is too
        # error-tolerant to reliably produce a genuine ParseFailed from
        # source text alone (T-0203 investigation), so `parse_file` is
        # patched at the `frob.gates` import site to return the Err this
        # code path exists to surface.
        from typani import Err

        from frob.lang import LangError
        from frob.lang import parse_file as real_parse_file

        _write(tmp_path, "src/broken.py", "def scan(x):\n    return x\n")
        snap = _snapshot(tmp_path)

        def _fake_parse_file(path: Path):
            if path.name == "broken.py":
                return Err(LangError.ParseFailed)
            return real_parse_file(path)

        monkeypatch.setattr("frob.lang.parse_file", _fake_parse_file)

        from frob.gates import perf_gate

        with caplog.at_level("DEBUG", logger="frob.gates"):
            perf_gate(tmp_path, snap)

        assert any(
            "skipping unparsed" in rec.message and "src/broken.py" in rec.message
            for rec in caplog.records
        )


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


_DESIGN_STRATA = """module m
node client : foreign { clearance Public; }
node api : authenticated { clearance Internal; }
node vault : trusted { clearance Secret; }
flow f_login : client -> api
boundary b_login endorse f_login : foreign -> authenticated when "jwt_verified"
"""


class TestSysGate:
    # frob:tests src/frob/gates/__init__.py::sys_gate kind="unit"
    def test_noop_no_design_dir(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        snapshot = _snapshot(tmp_path)
        assert sys_gate(tmp_path, snapshot) == ()

    def test_sys001_dangling(self, tmp_path: Path) -> None:
        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        _write(
            tmp_path,
            "src/a.py",
            "def send():\n    # frob:channel f_does_not_exist\n    pass\n",
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys001 = _by_rule(violations, "SYS001")
        assert len(sys001) == 1
        assert sys001[0].severity == Severity.ERROR

    def test_sys001_valid(self, tmp_path: Path) -> None:
        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        _write(
            tmp_path, "src/a.py", "def send():\n    # frob:channel f_login\n    pass\n"
        )
        snapshot = _snapshot(tmp_path)
        assert _by_rule(sys_gate(tmp_path, snapshot), "SYS001") == []

    def test_sys002_unbound(self, tmp_path: Path) -> None:
        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys002 = _by_rule(violations, "SYS002")
        assert {v.message.split()[2] for v in sys002} == {"b_login", "vault"}
        assert all(v.severity == Severity.WARN for v in sys002)

    def test_sys002_bound(self, tmp_path: Path) -> None:
        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        _write(
            tmp_path,
            "src/a.py",
            "def verify():\n"
            "    # frob:boundary b_login\n"
            "    pass\n\n"
            "def rotate():\n"
            "    # frob:secret vault\n"
            "    pass\n",
        )
        snapshot = _snapshot(tmp_path)
        assert _by_rule(sys_gate(tmp_path, snapshot), "SYS002") == []

    def test_sys003_import(self, tmp_path: Path, monkeypatch) -> None:
        """T-0080: SYS003 surfaces `check_import_conformance`'s tier-2
        violations through `sys_gate`. The surface grammar does not lex
        `code=` globs yet (docs/strata/surface.md#code-binding-tier-2-v0-
        implementation), so this wires a `KernelModel` built via the Python
        API directly, monkeypatching `frob.strata.load_design_ids` the way
        `test_load_tests_merges_python_and_rust_node_ids` monkeypatches
        collectors -- the design/ dir only needs to exist for `sys_gate`'s
        opt-in check.
        """
        import frob.strata as strata_mod
        from frob.strata import DesignIds, Node

        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "pkg_a/mod.py", "import pkg_b.mod\n")
        _write(tmp_path, "pkg_b/mod.py", "x = 1\n")
        model = strata_mod.KernelModel(
            nodes=(
                Node(id="a", trust="trusted", attrs=("code=pkg_a/*.py",)),
                Node(id="b", trust="trusted", attrs=("code=pkg_b/*.py",)),
            )
        )
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys003 = _by_rule(violations, "SYS003")
        assert len(sys003) == 1
        assert sys003[0].file == "pkg_a/mod.py"
        # SYS003 is WARN, not ERROR: warn-first adoption, same posture as
        # COV001 (T-0080 REJECT round 1, severity item).
        assert sys003[0].severity == Severity.WARN

    def test_sys004_load_failure(self, tmp_path: Path) -> None:
        # T-0080 REJECT round 1: a malformed .strata file must be reported
        # as its own SYS004 violation naming the file, not silently dropped.
        _write(tmp_path, "design/bad.strata", "this is not valid strata {{{")
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys004 = _by_rule(violations, "SYS004")
        assert len(sys004) == 1
        assert sys004[0].file == "design/bad.strata"
        assert sys004[0].severity == Severity.ERROR

    def test_sys004_suppresses_sys001(self, tmp_path: Path) -> None:
        # T-0080 REJECT round 1: when a sibling .strata file fails to load,
        # ids are merged with no per-file provenance, so a directive
        # referencing an id that WOULD have come from the broken file must
        # not be misdiagnosed as SYS001 dangling -- SYS001 is suppressed for
        # the whole run and SYS004 alone reports the real problem.
        _write(tmp_path, "design/good.strata", _DESIGN_STRATA)
        _write(tmp_path, "design/bad.strata", "this is not valid strata {{{")
        _write(
            tmp_path,
            "src/a.py",
            "def send():\n    # frob:channel f_login\n    pass\n",
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        assert _by_rule(violations, "SYS001") == []
        assert len(_by_rule(violations, "SYS004")) == 1

    def test_doc003_proved_claim_passes(self, tmp_path: Path, monkeypatch) -> None:
        """T-0085: a `frob:claims <view>` marker whose obligations are all
        discharged produces no DOC003 violation."""
        import frob.strata as strata_mod
        from frob.strata import Claim, DesignIds, Node, NoFlow, Rung
        from frob.strata._threat import _discharge_claim_id

        node = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = strata_mod.KernelModel(
            nodes=(node,),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="foreign", dst="Web"),
                    required_rung=Rung.L4,
                ),
            ),
        )
        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "README.md", "<!-- frob:claims owasp-top-10 -->\n")
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )
        snapshot = _snapshot(tmp_path)
        assert _by_rule(sys_gate(tmp_path, snapshot), "DOC003") == []

    def test_doc003_refutes_names_obligations(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-0085: an undischarged obligation for the claimed view is a
        DOC003 error naming the failing obligation (the CWE id)."""
        import frob.strata as strata_mod
        from frob.strata import DesignIds, Node

        model = strata_mod.KernelModel(
            nodes=(Node(id="Web", trust="trusted", may=("html_render",)),)
        )
        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "README.md", "<!-- frob:claims owasp-top-10 -->\n")
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )
        snapshot = _snapshot(tmp_path)
        doc003 = _by_rule(sys_gate(tmp_path, snapshot), "DOC003")
        assert len(doc003) == 1
        assert "CWE-79" in doc003[0].message
        assert doc003[0].file == "README.md"
        assert doc003[0].severity == Severity.ERROR

    def test_doc003_unclaimed_view_ignored(self, tmp_path: Path, monkeypatch) -> None:
        """T-0085: no `frob:claims` marker anywhere means DOC003 does not
        even evaluate the model -- an unclaimed view is silent, by design."""
        import frob.strata as strata_mod
        from frob.strata import DesignIds, Node

        model = strata_mod.KernelModel(
            nodes=(Node(id="Web", trust="trusted", may=("html_render",)),)
        )
        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "README.md", "no claims marker here\n")
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )
        snapshot = _snapshot(tmp_path)
        assert _by_rule(sys_gate(tmp_path, snapshot), "DOC003") == []

    def test_doc003_unknown_view(self, tmp_path: Path, monkeypatch) -> None:
        """T-0085: a `frob:claims` marker naming a view the catalog does
        not ship is its own DOC003 error, not a silent pass."""
        import frob.strata as strata_mod
        from frob.strata import DesignIds

        model = strata_mod.KernelModel()
        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "README.md", "<!-- frob:claims no-such-view -->\n")
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )
        snapshot = _snapshot(tmp_path)
        doc003 = _by_rule(sys_gate(tmp_path, snapshot), "DOC003")
        assert len(doc003) == 1
        assert "unknown baseline view" in doc003[0].message

    def test_doc003_marker_in_fenced_block_ignored(self, tmp_path: Path) -> None:
        """T-0085 round 2 (reviewer REJECT): a `frob:claims` marker inside a
        ```-fenced block documents the directive, it does not claim
        anything -- must not be extracted."""
        import frob.gates as gates_mod

        _write(
            tmp_path,
            "README.md",
            "# Example\n\n```markdown\n<!-- frob:claims owasp-top-10 -->\n```\n",
        )
        assert gates_mod._claims_markers(tmp_path) == []

    def test_doc003_marker_in_inline_code_ignored(self, tmp_path: Path) -> None:
        """T-0085 round 2: a `frob:claims` marker inside inline `backticks`
        on a prose line is a quotation, not a live claim."""
        import frob.gates as gates_mod

        _write(
            tmp_path,
            "README.md",
            "Write `<!-- frob:claims owasp-top-10 -->` in any doc page.\n",
        )
        assert gates_mod._claims_markers(tmp_path) == []

    def test_doc003_real_marker_with_fenced_example_extracts_once(
        self, tmp_path: Path
    ) -> None:
        """T-0085 round 2: a genuine top-level marker on a page that ALSO
        shows a fenced example of the directive extracts exactly the real
        one -- fence-awareness must not eat legitimate markers either."""
        import frob.gates as gates_mod

        _write(
            tmp_path,
            "README.md",
            "<!-- frob:claims owasp-top-10 -->\n"
            "\n"
            "Example of the directive:\n"
            "\n"
            "```markdown\n"
            "<!-- frob:claims owasp-top-10 -->\n"
            "```\n",
        )
        markers = gates_mod._claims_markers(tmp_path)
        assert markers == [("README.md", 1, "owasp-top-10")]

    def test_default_design_dir_mirror_stays_in_sync(self) -> None:
        """T-0135 review follow-up: the deliberate mirror literal must not drift.

        `frob.gates._DEFAULT_DESIGN_DIR` is a bare string duplicate of
        `frob.strata._design_load.DEFAULT_DESIGN_DIR` -- duplicated (not
        imported) so `_design_dir` never touches `frob.strata` for a repo
        with no design dir. Both imports happen INSIDE this test function
        (never at module level) so this file itself never pays the
        `frob.strata` import cost just by being collected; only this one
        test -- which exists precisely to prove the two literals agree --
        does.
        """
        import frob.gates as gates_mod
        from frob.strata import DEFAULT_DESIGN_DIR

        assert gates_mod._DEFAULT_DESIGN_DIR == DEFAULT_DESIGN_DIR

    def test_no_design_dir_never_imports_frob_strata(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0135: a repo with no design/ dir must never import frob.strata.

        frob.strata transitively imports frob/strata/_facts.py, which needs
        the strata_core native extension (T-0134 degrades that to a typed
        Err, but the point of this ticket is a repo that never opted into
        design/ at all should not even reach that machinery). Simulate the
        standalone-install worst case by making `frob.strata` itself
        unimportable, then confirm sys_gate on a design-less repo still
        returns cleanly instead of propagating the ImportError.
        """
        real_import = builtins.__import__

        def _blow_up_on_frob_strata(name, *args, **kwargs):
            if name == "frob.strata" or name.startswith("frob.strata."):
                raise ImportError("simulated: strata_core unavailable")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _blow_up_on_frob_strata)
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        snapshot = _snapshot(tmp_path)
        assert sys_gate(tmp_path, snapshot) == ()

    def test_design_dir_degrades_with_typed_error_on_native_extension_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0135: a repo WITH design/ must degrade (T-0134), never crash.

        Monkeypatches frob.strata._parse's module-level `strata_core`
        binding to None -- the state a bare `uv tool install frob` (no
        natives) leaves it in -- and confirms sys_gate on a repo that DOES
        have a design/ dir reports the parse failure as a typed SYS004
        violation instead of raising an unhandled exception.
        """
        import frob.strata._parse as parse_mod

        monkeypatch.setattr(parse_mod, "strata_core", None)
        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys004 = _by_rule(violations, "SYS004")
        assert len(sys004) == 1
        assert sys004[0].file == "design/m.strata"
