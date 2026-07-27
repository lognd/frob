"""Tests for frob.gates: drift, coverage, scope, pre-work, invariant, test gates."""
# frob:waive SCOPE001 reason="T-0541 scope is src/frob/gates/ only; tests/** lease is \
# held by in-progress T-0160's multi-pass backlog, so scope-add is blocked here"

from __future__ import annotations

import builtins
import json
import os
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
    Violation,
    active_ticket,
    compliance_gate,
    coverage_gate,
    debt_gate,
    delta_violations,
    deprecated_gate,
    drift_gate,
    exclude_hazard_gate,
    fmt_gate,
    inv003_gate,
    inv004_gate,
    inv006_gate,
    invariant_gate,
    is_baseline_stale,
    known_gate_rule_ids,
    list_debt,
    list_deprecated,
    load_baseline,
    load_coverage,
    prework_gate,
    record_prework,
    run_gates,
    scope_gate,
    stamp_baseline,
    stamp_coverage,
    sys_gate,
    tickets_gate,
    violation_fingerprint,
)
from frob.gates import (
    test_gate as run_test_gate,
)
from frob.gates._docblocks import doc004_gate
from frob.gates._pii_structural import pii_structural_gate
from frob.gates._ratchet import (
    load_ratchet_lock,
    ratchet_enabled_rules,
    resolve_ratchet_severity,
    snapshot_ratchet,
)
from frob.gates._rule_id_scan import (
    generated_gate_rule_ids,
    scan_emitted_rule_ids,
)
from frob.gates.invariants import InvariantError, _Criticality, load_invariants
from frob.gitio import Diff, Hunk, working_diff
from frob.graph import build_graph
from frob.graph._models import LockEntry, LockFile
from frob.strata import CMPL_REGISTRY_UNIT_IDS
from frob.testing import CollectedTests
from frob.tickets import Origin, Priority, Ticket, TicketKind, TicketQueue, TicketState
from frob.tickets._store import write_ticket


# frob:ticket T-0415
def _module_level_process_violation(root: Path, tag: str) -> tuple[Violation, ...]:
    """Picklable process-pool test gate (T-0415): a module-level function
    (required -- `ProcessPoolExecutor` cannot pickle a local closure) that
    returns one `Violation` whose message embeds the worker's own pid, so a
    test can prove the job actually executed in a separate process rather
    than merely running serially in-process."""
    import os

    return (
        Violation(
            rule="TESTPROC",
            severity=Severity.WARN,
            file=str(root),
            line=1,
            message=f"{tag}:{os.getpid()}",
        ),
    )


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# frob:ticket T-0807
def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run `argv` in `cwd`, raising on a nonzero exit -- a thin `subprocess.run`
    wrapper for the real-git-repo fixtures T-0807's linked-worktree/lease
    tests need (mirrors `tests/test_tickets_leases.py::_run`)."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


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
    kind: TicketKind = TicketKind.FEATURE,
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title="Sample",
        state=state,
        kind=kind,
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


# frob:ticket T-0564
def _state_line(root: Path, ticket_id: str) -> int:
    """The 1-indexed line number of `ticket_id`'s YAML `state:` field in
    `root/tickets.md` -- deliberately BELOW the marker line, for building a
    `Hunk` span that targets the state-transition line without ever
    overlapping the marker line itself (T-0564 regression coverage)."""
    marker = f"<!-- ticket:{ticket_id} -->"
    lines = (root / "tickets.md").read_text(encoding="utf-8").splitlines()
    in_block = False
    for i, line in enumerate(lines, start=1):
        if marker in line:
            in_block = True
            continue
        if in_block and line.startswith("state:"):
            return i
    raise AssertionError(f"state: line for {ticket_id} not found in tickets.md")


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


# T-0265: a `frob:tests` directive whose target is written with pytest's
# `Class::method` collect-only separator, on a test that ALSO names itself
# (self-referential) -- the mismatched separator means the string differs
# from the graph's own dotted `Class.method` qualname, so the edge is
# genuinely dangling (T-0237/`TestTest010KindValidation.test_dangling_
# tests_endpoint_still_caught_by_drift002` already documents that a
# `frob:tests` edge's CODE-side endpoint not resolving is DRIFT002's job,
# no TESTS-specific resolver needed -- a self-referential target is not
# special-cased at all: this repo's own widespread convention of a test
# naming itself via a CORRECTLY-formed dotted target is exactly as valid
# as any other `frob:tests` edge, see every `TestDebtGate`/
# `TestDeprecatedGate` method above). What WAS missing is that a caller
# who narrows `gates` to a small subset (the shape a ticket-scoped
# pre-flight check uses) never evaluated `drift` at all, so this same
# dangling edge could be invisible on that path while a wider selection
# caught it -- fixed in `frob.gates._build_jobs` (drift now always runs
# regardless of the caller's `gates` selection).
class TestSelfReferentialTestsDirectiveScopeAgreement:
    """T-0265 regression: a dangling self-referential `frob:tests` target
    must be caught the same way regardless of which gate subset a caller
    selects -- a narrowly-scoped run must never disagree with a wider one."""

    #: A test naming itself with pytest's `Class::method` collect-only
    #: separator instead of the graph's own dotted `Class.method` qualname
    #: -- the two strings differ, so this is a genuinely dangling edge.
    _MISMATCHED_SEPARATOR_SOURCE = (
        "class TestFoo:\n"
        "    # frob:tests tests/test_x.py::TestFoo::test_self\n"
        "    def test_self(self) -> None:\n"
        "        assert True\n"
    )

    def test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates.py::TestSelfReferentialTestsDirectiveScopeAgreement.test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff  # noqa: E501
        # Same fixture, evaluated through BOTH paths: a caller that narrows
        # `gates` to a small subset (the shape a ticket-scoped pre-flight
        # check uses) and a wider selection. Proves the SHARED mechanism --
        # `run_gates` always folding `drift` into the job set -- is what
        # closes the gap.
        _git_init(tmp_path)
        _write(tmp_path, "tests/test_x.py", self._MISMATCHED_SEPARATOR_SOURCE)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add self-tests"], cwd=tmp_path, check=True
        )

        narrow_cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope"})
        )
        narrow_result = run_gates(narrow_cfg)
        assert narrow_result.is_ok

        # "Full" here is deliberately still a thread-only gate selection
        # (drift + scope), not a bare `GateConfig()` default -- the
        # unrestricted default additionally selects `_PROCESS_POOL_GATES`
        # (archgate/sys/clones/perf/pii_structural/secrets/dead_symbols),
        # and `_run_combined_jobs` forks that `ProcessPoolExecutor` from
        # inside an still-active `ThreadPoolExecutor` block -- a real,
        # pre-existing fork/thread-safety hazard (a fork while another
        # thread holds e.g. the logging lock can deadlock the child) that
        # is unrelated to this ticket's scope and reproduced independently
        # under heavy parallel test load. Restricting to thread-only gates
        # here keeps this regression deterministic while still proving the
        # exact claim T-0265 cares about: a caller that narrows `gates` no
        # longer disagrees with a wider selection on whether DRIFT002 fires.
        full_cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "drift"})
        )
        full_result = run_gates(full_cfg)
        assert full_result.is_ok

        # Both paths now agree: DRIFT002 fires either way -- the
        # narrow, ticket-scoped-shaped selection is no longer green while
        # the wider run is red for the identical tree.
        narrow_rules = _rules(narrow_result.danger_ok.violations)
        full_rules = _rules(full_result.danger_ok.violations)
        assert "DRIFT002" in narrow_rules
        assert "DRIFT002" in full_rules


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


# frob:ticket T-0553
# frob:ticket T-0783
class TestCoverageGate:
    def test_cov001_broken_doc_edge_does_not_suppress_finding(
        self, tmp_path: Path
    ) -> None:
        # T-0233: a frob:doc edge pointing at a nonexistent anchor must not
        # count as "documented" for COV001 -- before the fix, any frob:doc
        # edge (broken or not) satisfied _documented_srcs and silently
        # suppressed the COV001 finding for that symbol.
        _write(
            tmp_path,
            "src/a.py",
            "class Widget:\n"
            '    """A widget."""\n\n'
            "    def render(self, value: int) -> str:\n"
            '        """Render the widget."""\n'
            "        # frob:doc docs/x.md#nonexistent-anchor\n"
            "        return str(value)\n",
        )
        _write(tmp_path, "docs/x.md", "# Widget\n")
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        render_cov001 = [
            v for v in violations if v.rule == "COV001" and "Widget.render" in v.message
        ]
        assert render_cov001 != []

    def test_cov001_undocumented_public_symbol(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert any(v.rule == "COV001" for v in violations)

    # frob:tests src/frob/gates/__init__.py::_cov003_evidence_violation
    # frob:ticket T-0292
    def test_cov003_remediation_hint_names_no_nonexistent_flag(
        self, tmp_path: Path
    ) -> None:
        """T-0292: the COV003 message used to tell users to run
        `frob test --collect`, a flag `frob test` has never accepted
        (argparse would reject it). The hint must not name any `frob test`
        flag other than ones `_add_test_parser` actually registers."""
        import argparse
        import re

        from frob.__main__ import _add_test_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        _add_test_parser(sub)
        test_parser = sub.choices["test"]
        real_flags = {
            opt for action in test_parser._actions for opt in action.option_strings
        }

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
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        v = _first_rule(violations, "COV003")
        assert v is not None
        sorted_real_flags = sorted(real_flags)
        for flag in re.findall(r"--[a-z][a-z-]*", v.message):
            assert flag in real_flags, (
                f"COV003 message references {flag!r}, which is not a real "
                f"`frob test` flag: {sorted_real_flags}"
            )

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
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        cov001 = [v for v in violations if v.rule == "COV001" and "helper" in v.message]
        assert len(cov001) == 1
        assert "no frob:doc edge" in cov001[0].message
        assert "undocumented" not in cov001[0].message

    def test_cov001_passes_when_documented(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::coverage_gate
        # T-0233: _WIDGET_PY's frob:doc edge must actually resolve (docs/x.md
        # with a #widget anchor) or COV001 now correctly fires on it too.
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        _write(tmp_path, "docs/x.md", "# Widget\n")
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        # only the method carries a frob:doc edge; the enclosing class is
        # still undocumented, so only assert on the documented symbol
        render_cov001 = [
            v for v in violations if v.rule == "COV001" and "Widget.render" in v.message
        ]
        assert render_cov001 == []

    def test_cov001_exempts_generated_file_with_marker(self, tmp_path: Path) -> None:
        # T-0234: a file carrying a recognized generated-file marker (here,
        # this repo's own "# generated by: ..." convention) must not draw a
        # COV001 finding -- nobody hand-documents machine-generated code.
        _write(
            tmp_path,
            "src/a.py",
            "# generated by: frob exports src/a\ndef helper(x):\n    return x\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV001" and "helper" in v.message for v in violations)

    def test_cov001_still_fires_without_generated_marker(self, tmp_path: Path) -> None:
        # Control for test_cov001_exempts_generated_file_with_marker: an
        # otherwise-identical file with no marker still owes COV001.
        _write(tmp_path, "src/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert any(v.rule == "COV001" and "helper" in v.message for v in violations)

    def test_cov002_unticketed_diff_hunk(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
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
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV002" for v in violations)

    def test_cov002_done_ticket_covers_own_closing_diff(self, tmp_path: Path) -> None:
        """T-0214: closing the covering ticket in the same uncommitted diff
        that edits the symbol it covers must not turn into a COV002 hard
        error -- the catch-22 this ticket fixes. THIS ticket's own
        `<!-- ticket:T-0001 -->` marker falling inside the touched
        `tickets.md` hunk span is the grace-window signal (not merely
        `tickets.md` being touched anywhere), AND (T-0320) the ticket must
        have genuinely been open at the diff's base commit -- here it was
        (state=IN_PROGRESS at base, DONE in the working tree), so grace
        applies."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        ticket = _ticket(state=TicketState.IN_PROGRESS)
        _write_ticket(tmp_path, ticket)
        _git_init(tmp_path)
        done_ticket = _ticket(state=TicketState.DONE)
        _write_ticket(tmp_path, done_ticket)
        marker_line = _marker_line(tmp_path, "T-0001")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        base_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        diff = Diff(
            base=base_sha,
            hunks=(
                Hunk(file="src/a.py", span=record.span),
                Hunk(file="tickets.md", span=(marker_line, marker_line)),
            ),
        )
        queue = TicketQueue(tickets={"T-0001": done_ticket})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV002" for v in violations)

    # frob:ticket T-0590
    def test_cov002_grace_covers_ticket_created_and_closed_in_same_diff(
        self, tmp_path: Path
    ) -> None:
        """T-0590: a ticket that was CREATED (via `frob ticket new`) and then
        CLOSED entirely within the current uncommitted diff -- e.g. a
        worktree agent's own `frob ticket new` + work + `frob ticket close`
        cycle that has not yet landed to `main` -- has NO entry for that
        ticket id in `tickets.md` at the diff's base commit at all (not
        merely a non-open state); `_ledger_states_at_base` correctly returns
        `None` for it. The pre-fix check (`state_at_base in _OPEN_STATES`)
        treated `None` the same as "already closed before this diff" and
        denied grace, reproducing the sequential-same-worktree-close COV002
        regression this ticket investigates: closing tickets that were
        themselves only ever created inside the current (not-yet-landed)
        branch lost their own closing-diff coverage. Base here has no
        `tickets.md` at all (mirrors a fresh worktree diverged from a `main`
        that predates this ticket's own creation)."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        _git_init(tmp_path)
        done_ticket = _ticket(state=TicketState.DONE)
        _write_ticket(tmp_path, done_ticket)
        marker_line = _marker_line(tmp_path, "T-0001")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        base_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        diff = Diff(
            base=base_sha,
            hunks=(
                Hunk(file="src/a.py", span=record.span),
                Hunk(file="tickets.md", span=(marker_line, marker_line)),
            ),
        )
        queue = TicketQueue(tickets={"T-0001": done_ticket})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV002" for v in violations)

    # frob:ticket T-0965
    def test_cov002_scope_grace_covers_ticket_created_and_closed_in_same_diff(
        self, tmp_path: Path
    ) -> None:
        """T-0965: the T-0590 same-diff grace window extends to SCOPE-based
        coverage too, not just a direct `frob:ticket` edge. A ticket that
        covered a whole file by declared `scope` (no per-symbol directive on
        `helper`) and was created AND closed entirely within the current
        uncommitted diff must still cover its scoped symbols -- otherwise
        the instant such a ticket closes to `DONE`, every symbol it covered
        only by scope starts failing COV002 even though the closing
        ticket's own commit is still part of the exact same unlanded diff
        COV002 evaluates (the false positive T-0965 investigates)."""
        source = "def helper(x):\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        _git_init(tmp_path)
        done_ticket = _ticket(state=TicketState.DONE, scope=("src/a.py",))
        _write_ticket(tmp_path, done_ticket)
        marker_line = _marker_line(tmp_path, "T-0001")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        base_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        diff = Diff(
            base=base_sha,
            hunks=(
                Hunk(file="src/a.py", span=record.span),
                Hunk(file="tickets.md", span=(marker_line, marker_line)),
            ),
        )
        queue = TicketQueue(tickets={"T-0001": done_ticket})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV002" for v in violations)

    # frob:ticket T-0965
    def test_cov002_scope_grace_without_same_diff_close_still_fires(
        self, tmp_path: Path
    ) -> None:
        """T-0965 regression guard: a ticket that covers `src/a.py` by scope
        but is ALREADY `DONE` before this diff (not a same-diff close) must
        NOT extend grace -- otherwise every symbol in a file a long-closed
        ticket happened to scope would be permanently uncovered."""
        source = "def helper(x):\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        done_ticket = _ticket(state=TicketState.DONE, scope=("src/a.py",))
        _write_ticket(tmp_path, done_ticket)
        _git_init(tmp_path)
        # Touch the ticket's own section again (still DONE) -- simulates an
        # unrelated later edit to tickets.md that happens to touch this
        # ticket's marker hunk, not a genuine open -> DONE transition.
        _write_ticket(tmp_path, done_ticket)
        marker_line = _marker_line(tmp_path, "T-0001")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        base_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        diff = Diff(
            base=base_sha,
            hunks=(
                Hunk(file="src/a.py", span=record.span),
                Hunk(file="tickets.md", span=(marker_line, marker_line)),
            ),
        )
        queue = TicketQueue(tickets={"T-0001": done_ticket})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert any(v.rule == "COV002" for v in violations)

    # frob:ticket T-0965
    def test_open_scopes_grace_requires_both_root_and_diff(
        self, tmp_path: Path
    ) -> None:
        """T-0965 mutant-pin: `_open_scopes`'s grace extension must require
        BOTH `root` and `diff` (an And, not an Or) -- passing only one must
        quietly skip the extension, never attempt it. Under an Or mutant,
        supplying only `root` (diff=None) would still enter the extension
        branch and crash on `diff.base`, and supplying only `diff`
        (root=None) would crash resolving the base ledger with a `None`
        root -- both distinguish the mutant from the real And semantics
        without needing a git repo at all."""
        from frob.gates import _open_scopes

        done_ticket = _ticket(state=TicketState.DONE, scope=("src/a.py",))
        queue = TicketQueue(tickets={"T-0001": done_ticket})
        diff = Diff(base="deadbeef", hunks=())
        assert _open_scopes(queue, root=str(tmp_path), diff=None) == []
        assert _open_scopes(queue, root=None, diff=diff) == []

    # frob:ticket T-0564
    def test_cov002_grace_matches_hunk_anywhere_in_ticket_block(
        self, tmp_path: Path
    ) -> None:
        """T-0564: the ticket's own `state:` line (NOT its marker line)
        falling inside the touched `tickets.md` hunk must still grant grace
        -- a state transition (queued -> done) or an evidence-list
        insertion typically lands several lines below the marker/id/title
        lines, inside the same YAML block, so scoping the hunk-overlap
        check to the exact marker line alone would wrongly deny grace to a
        ticket whose own closing diff plainly IS present."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        ticket = _ticket(state=TicketState.IN_PROGRESS)
        _write_ticket(tmp_path, ticket)
        _git_init(tmp_path)
        done_ticket = _ticket(state=TicketState.DONE)
        _write_ticket(tmp_path, done_ticket)
        state_line = _state_line(tmp_path, "T-0001")
        marker_line = _marker_line(tmp_path, "T-0001")
        assert state_line != marker_line
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        base_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        diff = Diff(
            base=base_sha,
            hunks=(
                Hunk(file="src/a.py", span=record.span),
                # Hunk touches only the state: line, not the marker line.
                Hunk(file="tickets.md", span=(state_line, state_line)),
            ),
        )
        queue = TicketQueue(tickets={"T-0001": done_ticket})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV002" for v in violations)

    def test_cov002_marker_touch_without_state_transition_still_fires(
        self, tmp_path: Path
    ) -> None:
        """T-0320: a ticket that was ALREADY `DONE` at the diff's base
        commit does not get COV002 grace merely because its marker line is
        edited again (e.g. a typo fix or evidence append to its Done
        report) -- marker-in-hunk alone is a proxy for "closing", not proof
        of an open -> DONE transition, so a symbol bound to it and touched
        without a covering open ticket must still fire."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        ticket = _ticket(state=TicketState.DONE)
        _write_ticket(tmp_path, ticket)
        _git_init(tmp_path)
        # Touch the ticket's own section again (still DONE) -- simulates a
        # Done-report typo fix that happens to touch the marker's hunk.
        _write_ticket(tmp_path, ticket)
        marker_line = _marker_line(tmp_path, "T-0001")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        base_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        diff = Diff(
            base=base_sha,
            hunks=(
                Hunk(file="src/a.py", span=record.span),
                Hunk(file="tickets.md", span=(marker_line, marker_line)),
            ),
        )
        queue = TicketQueue(tickets={"T-0001": ticket})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        v = _first_rule(violations, "COV002")
        assert v is not None
        assert "frob ticket new" in v.message

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
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
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
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
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
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert any(v.rule == "COV003" for v in violations)

    def test_cov003_names_unbuilt_native_as_remedy(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_missing_native_remedy kind="unit"
        # T-0333: when a declared native is unbuilt, its importorskip-gated
        # tests never collect, so bound evidence cannot resolve -- the COV003
        # message must name the native and its build command, not blame the id.
        from frob.testing import NativeSpec

        snap = _snapshot(tmp_path)
        queue = TicketQueue(
            tickets={
                "T-0002": _ticket(
                    ticket_id="T-0002",
                    state=TicketState.DONE,
                    evidence=("tests/unit/strata/test_kernel.py::test_prop",),
                )
            }
        )
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(
            node_ids=frozenset(),
            missing_natives=(NativeSpec(name="strata_core", build_cmd="make core"),),
        )
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        cov003 = [v for v in violations if v.rule == "COV003"]
        assert cov003
        assert "strata_core" in cov003[0].message
        assert "make core" in cov003[0].message
        # and it must NOT point at the nonexistent flag it used to
        assert "frob test --collect to refresh" not in cov003[0].message

    def test_cov003_honest_remedy_when_no_native_missing(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_cov003_evidence_violation kind="unit"
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
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        cov003 = [v for v in violations if v.rule == "COV003"]
        assert cov003
        # T-0292: the hint must NOT name the nonexistent `frob test --collect`
        # flag; it names the real content-hash auto-refresh + cache-file
        # fallback instead.
        assert "--collect" not in cov003[0].message
        assert "refreshes automatically" in cov003[0].message

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
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV003" for v in violations)

    def test_cov003_passes_for_parametrized_evidence_with_dot_in_case_id(
        self, tmp_path: Path
    ) -> None:
        """T-0324 regression: an evidence id naming ONE specific
        `@pytest.mark.parametrize` case whose case text itself contains a
        dot (e.g. a version string `3.11.4`, exactly what `frob ticket
        evidence` recorded from T-0222's auto-generated fixture ids) must
        resolve. Before the fix, `_symref_to_nodeid`'s blanket
        `qualname.replace('.', '::')` corrupted dots INSIDE the `[...]`
        case suffix too, so the bracket-less base resolved (`_evidence_
        collected`'s prefix-match branch) but the specific bracketed case
        id did not -- exactly the split reported."""
        snap = _snapshot(tmp_path)
        node = "tests/test_x.py::test_needle_present[015-python-3.11.4]"
        queue = TicketQueue(
            tickets={
                "T-0002": _ticket(
                    ticket_id="T-0002", state=TicketState.DONE, evidence=(node,)
                )
            }
        )
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV003" for v in violations)

    def test_cov003_passes_for_file_level_evidence(self, tmp_path: Path) -> None:
        """T-0298: a done ticket may cite a bare test FILE as its evidence
        (`tests/test_vet.py`, no `::`) -- root-cause of a 25-error
        main-red incident (2026-07-19), where a refactor touching ~20
        files recorded exactly this shape and COV003 could never resolve
        it. Resolves iff >=1 collected node id lives under that file."""
        snap = _snapshot(tmp_path)
        queue = TicketQueue(
            tickets={
                "T-0002": _ticket(
                    ticket_id="T-0002",
                    state=TicketState.DONE,
                    evidence=("tests/test_vet.py",),
                )
            }
        )
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(
            node_ids=frozenset(
                {"tests/test_vet.py::test_a", "tests/test_vet.py::test_b"}
            )
        )
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV003" for v in violations)

    def test_cov003_passes_for_directory_level_evidence(self, tmp_path: Path) -> None:
        """T-0298: a bare directory (`tests/unit/deploy`, no `::`) resolves
        the same way a file does -- any collected node id under it counts."""
        snap = _snapshot(tmp_path)
        queue = TicketQueue(
            tickets={
                "T-0002": _ticket(
                    ticket_id="T-0002",
                    state=TicketState.DONE,
                    evidence=("tests/unit/deploy",),
                )
            }
        )
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(
            node_ids=frozenset({"tests/unit/deploy/test_x.py::test_y"})
        )
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV003" for v in violations)

    def test_cov003_rejects_empty_directory_level_evidence(
        self, tmp_path: Path
    ) -> None:
        """T-0298: file-/directory-level resolution must NOT be vacuous --
        a path with zero collected node ids under it (nothing landed there,
        or the directory does not correspond to any real test) still
        fails COV003, honest per the ticket's requirement."""
        snap = _snapshot(tmp_path)
        queue = TicketQueue(
            tickets={
                "T-0002": _ticket(
                    ticket_id="T-0002",
                    state=TicketState.DONE,
                    evidence=("tests/unit/nonexistent",),
                )
            }
        )
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(
            node_ids=frozenset({"tests/unit/deploy/test_x.py::test_y"})
        )
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert any(v.rule == "COV003" for v in violations)

    def test_cov003_prefers_node_level_over_path_level(self, tmp_path: Path) -> None:
        """T-0298: node-level resolution stays available and preferred --
        a precise `path::func` evidence id still resolves exactly as
        before, unaffected by the new path-level fallback existing."""
        snap = _snapshot(tmp_path)
        node = "tests/test_vet.py::test_a"
        queue = TicketQueue(
            tickets={
                "T-0002": _ticket(
                    ticket_id="T-0002", state=TicketState.DONE, evidence=(node,)
                )
            }
        )
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset({node, "tests/test_vet.py::test_b"}))
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
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
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
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
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert any(v.rule == "COV004" for v in violations)

    def test_cov005_directive_rebound_to_private_symbol_flags(
        self, tmp_path: Path
    ) -> None:
        """T-0297: extracting a private helper directly above `foo` and
        landing `foo`'s trailing `frob:ticket` on the new helper instead
        must fire COV005 -- the directive is now bound to `_foo_impl`
        (private) where it bound `foo` (public) at HEAD."""
        _write(
            tmp_path,
            "src/a.py",
            "def foo(x):\n    # frob:ticket T-0001\n    return x\n",
        )
        _git_init(tmp_path)
        _write(
            tmp_path,
            "src/a.py",
            "def _foo_impl(x):\n"
            "    # frob:ticket T-0001\n"
            "    return x\n"
            "\n"
            "\n"
            "def foo(x):\n"
            "    return _foo_impl(x)\n",
        )
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::_foo_impl"]
        diff = Diff(base="HEAD", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.IN_PROGRESS)})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        v = _first_rule(violations, "COV005")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "_foo_impl" in v.message
        assert "T-0001" in v.message

    def test_cov005_same_symbol_no_rebind_is_clean(self, tmp_path: Path) -> None:
        """A directive that stays bound to the same (still public) symbol
        across the diff must not fire COV005, even though the body changed."""
        _write(
            tmp_path,
            "src/a.py",
            "def foo(x):\n    # frob:ticket T-0001\n    return x\n",
        )
        _git_init(tmp_path)
        _write(
            tmp_path,
            "src/a.py",
            "def foo(x):\n    # frob:ticket T-0001\n    return x + 1\n",
        )
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::foo"]
        diff = Diff(base="HEAD", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.IN_PROGRESS)})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV005" for v in violations)

    def test_cov005_no_old_blob_is_clean(self, tmp_path: Path) -> None:
        """A brand-new (never-committed) file has no "before" to compare
        against `diff.base`, so COV005 must not fire on it (only COV001
        covers a new file's own missing-doc obligation)."""
        _git_init(tmp_path)
        _write(
            tmp_path,
            "src/a.py",
            "def _foo_impl(x):\n    # frob:ticket T-0001\n    return x\n",
        )
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::_foo_impl"]
        diff = Diff(base="HEAD", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.IN_PROGRESS)})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV005" for v in violations)

    def test_cov006_flags_test_with_no_call_graph_reachability(
        self, tmp_path: Path
    ) -> None:
        """T-0483: a `frob:tests` edge bound to a PRIVATE symbol whose named
        test body never calls it (no `frob.graph.callgraph` reachability)
        must fire COV006."""
        # frob:tests src/frob/gates/__init__.py::_cov006
        _write(tmp_path, "src/a.py", "def _helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "# frob:tests src/a.py::_helper\n"
            "def test_helper_broken():\n"
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        v = _first_rule(violations, "COV006")
        assert v is not None
        assert v.severity == Severity.WARN
        assert "_helper" in v.message

    def test_cov006_silent_when_test_calls_the_bound_symbol(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_cov006
        _write(tmp_path, "src/a.py", "def _helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "# frob:tests src/a.py::_helper\n"
            "def test_helper_ok():\n"
            "    assert _helper(1) == 1\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV006" for v in violations)

    def test_cov006_silent_when_test_reaches_via_same_file_public_wrapper(
        self, tmp_path: Path
    ) -> None:
        """T-0506: a test that only calls a PUBLIC wrapper in the same file
        as the bound private target -- which itself calls that target --
        must NOT fire COV006, even though `build_call_graph`'s shared
        substrate has no direct edge for the wrapper's first hop."""
        # frob:tests src/frob/gates/__init__.py::_cov006_public_wrapper_reachable
        _write(
            tmp_path,
            "src/a.py",
            "def wrapper(x):\n    return _helper(x)\n\n\ndef _helper(x):\n    return x\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "# frob:tests src/a.py::_helper\n"
            "def test_wrapper_ok():\n"
            "    assert wrapper(1) == 1\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV006" for v in violations)

    def test_cov006_still_fires_when_no_public_wrapper_reaches_the_target(
        self, tmp_path: Path
    ) -> None:
        """T-0506: the one-hop public-wrapper rescue is non-vacuous -- a
        test that calls an UNRELATED public symbol in the same file (one
        that never calls the bound private target) must still fire
        COV006."""
        # frob:tests src/frob/gates/__init__.py::_cov006_public_wrapper_reachable
        _write(
            tmp_path,
            "src/a.py",
            "def unrelated(x):\n    return x\n\n\ndef _helper(x):\n    return x\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "# frob:tests src/a.py::_helper\n"
            "def test_unrelated_only():\n"
            "    assert unrelated(1) == 1\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert _first_rule(violations, "COV006") is not None

    def test_cov006_silent_when_test_reaches_via_two_hop_wrapper_chain(
        self, tmp_path: Path
    ) -> None:
        """T-0516: the T-0506 rescue only checked the wrapper's DIRECT
        callees; a test that reaches its bound private target through a
        public wrapper calling a private INTERMEDIATE helper (which then
        calls the target) must also be rescued, not just the one-hop
        wrapper-calls-target-directly shape."""
        # frob:tests src/frob/gates/__init__.py::_cov006_public_wrapper_reachable
        _write(
            tmp_path,
            "src/a.py",
            "def wrapper(x):\n"
            "    return _middle(x)\n\n\n"
            "def _middle(x):\n"
            "    return _helper(x)\n\n\n"
            "def _helper(x):\n"
            "    return x\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "# frob:tests src/a.py::_helper\n"
            "def test_wrapper_ok():\n"
            "    assert wrapper(1) == 1\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV006" for v in violations)

    def test_cov006_silent_when_wrapper_called_via_import_alias(
        self, tmp_path: Path
    ) -> None:
        """T-0516: a test that imports the public wrapper under a local
        `as` alias (e.g. to dodge pytest collecting a `test_*`-prefixed
        import as its own test item) and calls the ALIAS must still be
        rescued -- the alias is resolved back to the wrapper's real short
        name before matching."""
        # frob:tests src/frob/gates/__init__.py::_cov006_public_wrapper_reachable
        _write(
            tmp_path,
            "src/a.py",
            "def test_wrapper(x):\n    return _helper(x)\n\n\ndef _helper(x):\n    return x\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "from src.a import test_wrapper as run_wrapper\n\n"
            "# frob:tests src/a.py::_helper\n"
            "def test_alias_ok():\n"
            "    assert run_wrapper(1) == 1\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV006" for v in violations)

    # frob:ticket T-0525
    # frob:tests tests/test_gates.py::TestCoverageGate.test_cov006_violation_carries_edge_src_as_symref kind="unit"  # noqa: E501
    def test_cov006_violation_carries_edge_src_as_symref(self, tmp_path: Path) -> None:
        """T-0525: a COV006 finding's `symref` is the offending `frob:tests`
        edge's own `src` (the test's symref), not `None` -- this is what
        lets `_match_waiver` do symbol-exact matching instead of falling
        back to file-scope, where a single waiver anywhere in the file
        used to silently suppress every COV006 finding in it (T-0148's
        precedent for TEST005, applied here)."""
        _write(tmp_path, "src/a.py", "def _helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "# frob:tests src/a.py::_helper\n"
            "def test_helper_broken():\n"
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        v = _first_rule(violations, "COV006")
        assert v is not None
        assert v.symref == "tests/test_a.py::test_helper_broken"

    # frob:ticket T-0525
    # frob:tests tests/test_gates.py::TestCoverageGate.test_cov006_waiver_does_not_blanket_suppress_the_whole_file kind="unit"  # noqa: E501
    def test_cov006_waiver_does_not_blanket_suppress_the_whole_file(
        self, tmp_path: Path
    ) -> None:
        """T-0525 regression: two independent, unsound `frob:tests` edges
        in the SAME test file each produce their own COV006 finding; a
        `frob:waive COV006` comment bound to only ONE of the two tests
        must suppress only that one -- NOT both, the T-0148-class
        blanket-waiver bug this ticket fixes for COV006 specifically
        (previously verified live: one waiver comment in tests/test_gates.py
        silently absorbed all 7 COV006 findings then present in that
        file)."""
        _write(
            tmp_path,
            "src/a.py",
            "def _helper_one(x):\n"
            "    return x\n"
            "\n"
            "\n"
            "def _helper_two(x):\n"
            "    return x\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "# frob:tests src/a.py::_helper_one\n"
            '# frob:waive COV006 reason="deliberately unsound for this test"\n'
            "def test_helper_one_broken():\n"
            "    assert True\n"
            "\n"
            "\n"
            "# frob:tests src/a.py::_helper_two\n"
            "def test_helper_two_broken():\n"
            "    assert True\n",
        )
        from frob.gates import _apply_waivers  # noqa: PLC0415 - internal, test-only

        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        kept, waived = _apply_waivers(violations, snap)
        kept_cov006 = [v for v in kept if v.rule == "COV006"]
        waived_cov006 = [v for v in waived if v.rule == "COV006"]
        assert len(waived_cov006) == 1
        assert waived_cov006[0].symref == "tests/test_a.py::test_helper_one_broken"
        assert len(kept_cov006) == 1
        assert kept_cov006[0].symref == "tests/test_a.py::test_helper_two_broken"

    def test_cov006_never_fires_for_a_public_target(self, tmp_path: Path) -> None:
        """`build_call_graph` never records an edge to a PUBLIC callee, so
        checking a public target would ALWAYS look "unreachable" -- COV006
        must skip public targets entirely rather than emit a spurious
        finding on every legitimately-tested public function."""
        # frob:tests src/frob/gates/__init__.py::_cov006
        _write(tmp_path, "src/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "# frob:tests src/a.py::helper\ndef test_helper():\n    assert True\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV006" for v in violations)

    # frob:ticket T-0814
    # frob:tests tests/test_gates.py::TestCoverageGate.test_is_symref_gates kind="unit"
    def test_is_symref_gates(self) -> None:
        """T-0814: `_is_symref` distinguishes a real `path::qualname`
        call-graph node from a non-symref sentinel like
        `UNRESOLVED_CALLEE` -- the guard every closure consumer in this
        module must apply before `split("::", 1)[1]`."""
        from frob.gates import _is_symref
        from frob.graph.callgraph import UNRESOLVED_CALLEE

        assert _is_symref("src/a.py::_helper") is True
        assert _is_symref(UNRESOLVED_CALLEE) is False
        assert _is_symref("no-double-colon-here") is False

    # frob:ticket T-0814
    # frob:tests tests/test_gates.py::TestCoverageGate.test_cov006_third_file_reachable_skips_unresolved_callee_sentinel kind="unit"  # noqa: E501
    def test_cov006_third_file_reachable_skips_unresolved_callee_sentinel(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-0814 (T-0809 reviewer condition b): `_cov006_third_file_reachable`
        iterates `closure(...)`'s output and used to do
        `helper_symref.split("::", 1)[1]` unconditionally -- a bare
        `UNRESOLVED_CALLEE` sentinel entry (no `::`) IndexErrors that.
        Forcing `closure` to always return the sentinel proves the
        function now skips it and returns cleanly instead of raising."""
        import frob.graph.callgraph as callgraph_mod
        from frob.gates import _cov006_third_file_reachable
        from frob.graph import Edge, EdgeKind
        from frob.graph.callgraph import UNRESOLVED_CALLEE

        _write(tmp_path, "src/a.py", "def _target(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_x.py",
            "# frob:tests src/a.py::_target\ndef test_foo():\n    _stuff()\n",
        )
        edge = Edge(
            kind=EdgeKind.TESTS,
            src="tests/test_x.py::test_foo",
            target="src/a.py::_target",
            origin="tests/test_x.py:1",
        )

        real_closure = callgraph_mod.closure

        def _closure_always_sentinel(*args, **kwargs):
            """Test double: real closure output plus a poisoned sentinel
            entry, so every consumer sees a non-symref member."""
            return real_closure(*args, **kwargs) + (UNRESOLVED_CALLEE,)

        monkeypatch.setattr(callgraph_mod, "closure", _closure_always_sentinel)

        # Must not raise IndexError; the sentinel names no real helper so
        # this rescue finds nothing further to widen the search with.
        assert _cov006_third_file_reachable(tmp_path, edge) is False

    def test_cov007_flags_doc_anchor_on_private_helper(self, tmp_path: Path) -> None:
        """T-0483: a `frob:doc` edge whose src symbol is PRIVATE fires
        COV007 -- doc anchors are for the public API surface."""
        # frob:tests src/frob/gates/__init__.py::_cov007
        _write(
            tmp_path,
            "src/a.py",
            "def _helper(x):\n"
            '    """helper"""\n'
            "    # frob:doc docs/x.md#helper\n"
            "    return x\n",
        )
        _write(tmp_path, "docs/x.md", "# Helper\n")
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        v = _first_rule(violations, "COV007")
        assert v is not None
        assert v.severity == Severity.WARN
        assert "_helper" in v.message

    def test_cov007_silent_for_doc_anchor_on_public_symbol(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_cov007
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV007" for v in violations)

    def test_todo002_unbound_directive(self, tmp_path: Path) -> None:
        """A `frob:todo` edge bound to a missing ticket is TODO002 (dangling
        reference), distinct from TODO001 (bare, wholly untracked comment)."""
        source = "def helper(x):\n    # frob:todo T-9999\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert any(v.rule == "TODO002" for v in violations)
        assert not any(v.rule == "TODO001" for v in violations)

    def test_todo001_bare_comment_in_touched_file(self, tmp_path: Path) -> None:
        source = "def helper(x):\n    # TODO: fix this later\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(1, 3)),))
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert any(v.rule == "TODO001" and "bare TODO" in v.message for v in violations)
        assert not any(v.rule == "TODO002" for v in violations)

    def test_todo002_edge_to_closed_ticket(self, tmp_path: Path) -> None:
        """A `frob:todo` bound to a CLOSED ticket is also TODO002 (work was
        accounted for once, but the reference is now stale)."""
        source = "def helper(x):\n    # frob:todo T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.DONE)})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert any(v.rule == "TODO002" for v in violations)
        assert not any(v.rule == "TODO001" for v in violations)

    # frob:ticket T-0783
    def _write_pyproject_version(self, tmp_path: Path, version: str) -> None:
        """A minimal `pyproject.toml` declaring `version` -- `_current_
        version`/`_pyproject_version_at`'s single read target."""
        _write(
            tmp_path,
            "pyproject.toml",
            f'[project]\nname = "sample"\nversion = "{version}"\n',
        )

    # frob:ticket T-0783
    # frob:tests \
    # tests/test_gates.py::TestCoverageGate.test_todo003_fires_after_version_bump_since\
    # _deferral_landed  # noqa: E501
    def test_todo003_fires_after_version_bump_since_deferral_landed(
        self, tmp_path: Path
    ) -> None:
        """T-0783 acceptance: a `frob:todo` comment lands under v0.1.0,
        pyproject bumps to v0.2.0 in a later commit that never touches the
        deferral line, the target ticket is still open -- TODO003 fires,
        naming the deferred-since version and the current one."""
        self._write_pyproject_version(tmp_path, "0.1.0")
        source = "def helper(x):\n    # frob:todo T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        _git_init(tmp_path)
        self._write_pyproject_version(tmp_path, "0.2.0")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "chore: bump version"],
            cwd=tmp_path,
            check=True,
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        todo003 = [v for v in violations if v.rule == "TODO003"]
        assert len(todo003) == 1
        assert todo003[0].severity == Severity.WARN
        assert "T-0001" in todo003[0].message
        assert "v0.1.0" in todo003[0].message
        assert "v0.2.0" in todo003[0].message

    # frob:ticket T-0783
    # frob:tests \
    # tests/test_gates.py::TestCoverageGate.test_todo003_silent_when_no_version_bump_si\
    # nce_deferral  # noqa: E501
    def test_todo003_silent_when_no_version_bump_since_deferral(
        self, tmp_path: Path
    ) -> None:
        """Adversarial: the deferral comment landed under the SAME version
        still on disk -- no release has shipped since, so TODO003 must
        stay silent (it has not crossed a boundary yet)."""
        self._write_pyproject_version(tmp_path, "0.1.0")
        source = "def helper(x):\n    # frob:todo T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        _git_init(tmp_path)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "TODO003" for v in violations)

    # frob:ticket T-0783
    # frob:tests \
    # tests/test_gates.py::TestCoverageGate.test_todo003_silent_when_ticket_closes  # \
    # noqa: E501
    def test_todo003_silent_when_ticket_closes(self, tmp_path: Path) -> None:
        """Acceptance (T-0783): once the deferred-to ticket closes, the
        finding clears -- `_todo003_long_deferred` only considers edges
        whose target is still in `_OPEN_STATES`, same population TODO002
        already excludes for the inverse reason."""
        self._write_pyproject_version(tmp_path, "0.1.0")
        source = "def helper(x):\n    # frob:todo T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        _git_init(tmp_path)
        self._write_pyproject_version(tmp_path, "0.2.0")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "chore: bump version"],
            cwd=tmp_path,
            check=True,
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.DONE)})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "TODO003" for v in violations)

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
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert _first_rule(violations, "COV001") is not None

        from frob.gates import _apply_waivers  # noqa: PLC0415 - internal, test-only

        kept, waived = _apply_waivers(violations, snap)
        assert _first_rule(kept, "COV001") is None
        waived_cov001 = _first_rule(waived, "COV001")
        assert waived_cov001 is not None
        assert waived_cov001.waived is not None

    # frob:ticket T-0553
    def test_cov001_waiver_does_not_blanket_suppress_sibling_symbol(
        self, tmp_path: Path
    ) -> None:
        """T-0553 (B11): a `frob:waive COV001` placed above ONE public
        symbol must not also suppress COV001 for a DIFFERENT public symbol
        in the same file -- before this fix, COV001's `Violation` carried
        no `symref`, so `_match_waiver` fell back to file-scoped matching
        and one directive silently waived every undocumented symbol in the
        file, not just the one it was written above."""
        source = (
            "def waived_helper(x):\n"
            '    # frob:waive COV001 reason="legacy code, ticket filed"\n'
            '    """A public helper waived from doc obligations."""\n'
            "    return x\n"
            "\n"
            "def unwaived_helper(x):\n"
            '    """A different public helper, never waived."""\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)

        from frob.gates import _apply_waivers  # noqa: PLC0415 - internal, test-only

        kept, waived = _apply_waivers(violations, snap)
        waived_symrefs = {v.symref for v in waived if v.rule == "COV001"}
        kept_symrefs = {v.symref for v in kept if v.rule == "COV001"}
        assert "src/a.py::waived_helper" in waived_symrefs
        assert "src/a.py::unwaived_helper" in kept_symrefs

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
        # T-0101: a waiver on an arch category with no gate channel (e.g.
        # god-class) can never be matched by _apply_waivers -- WAIVE002 must
        # say so loudly rather than silently doing nothing. long-function is
        # NOT in this set as of T-0289 -- see the next test.
        source = (
            'def helper(x):\n    # frob:waive god-class reason="huge but ok"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates import _waive002_violations  # noqa: PLC0415

        violations = _waive002_violations(snap, frozenset())
        v = _first_rule(violations, "WAIVE002")
        assert v is not None
        # T-0753: promoted WARN -> ERROR.
        assert v.severity == Severity.ERROR
        assert "frob-arch" in v.message

    def test_waive002_does_not_flag_arch001_as_ineffective(
        self, tmp_path: Path
    ) -> None:
        # T-0289: long-function is channeled into a real ARCH001 Violation
        # (frob.gates._arch.arch_gate), so a `frob:waive ARCH001
        # reason="..."` is a real, effective directive -- WAIVE002 must NOT
        # flag it, unlike the still-unwaivable arch categories above.
        source = (
            'def helper(x):\n    # frob:waive ARCH001 reason="justified"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates import _waive002_violations  # noqa: PLC0415

        violations = _waive002_violations(snap, frozenset())
        assert _first_rule(violations, "WAIVE002") is None

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


# frob:ticket T-0851
class TestFmt001Gate:
    """T-0851: FMT001, the T-0441 follow-up -- a diff-touched `frob:`
    directive comment line over the configured line length gets a `frob
    fmt <path>` remediation hint; an ordinary long comment or long code
    line (neither is a `frob:` directive run) does not."""

    # frob:ticket T-0851
    def test_directive_run_over_limit_flagged(self, tmp_path: Path) -> None:
        """A single-physical-line `frob:waive` directive over the default
        88-col limit is FMT001, naming `frob fmt <path>` as the fix."""
        long_reason = "x" * 70
        source = (
            "def helper(x):\n"
            f'    # frob:waive INV006 reason="{long_reason}"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(2, 2)),))
        violations = fmt_gate(tmp_path, diff)
        hit = next((v for v in violations if v.rule == "FMT001"), None)
        assert hit is not None
        assert hit.file == "src/a.py"
        assert hit.line == 2
        assert "frob fmt src/a.py" in hit.message

    # frob:ticket T-0851
    def test_ordinary_long_comment_not_flagged(self, tmp_path: Path) -> None:
        """An over-limit comment line that is NOT a `frob:` directive
        (near-miss #1) never fires FMT001 -- `frob fmt` would not touch it
        either, so a hint naming it as the fix would be false."""
        long_comment = "y" * 90
        source = f"def helper(x):\n    # {long_comment}\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(2, 2)),))
        violations = fmt_gate(tmp_path, diff)
        assert not any(v.rule == "FMT001" for v in violations)

    # frob:ticket T-0851
    def test_long_code_line_not_flagged(self, tmp_path: Path) -> None:
        """An over-limit CODE line (near-miss #2, no comment marker at all)
        never fires FMT001."""
        source = "def helper(x):\n    y = " + "1" * 90 + "\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(2, 2)),))
        violations = fmt_gate(tmp_path, diff)
        assert not any(v.rule == "FMT001" for v in violations)

    # frob:ticket T-0851
    def test_untouched_line_not_flagged(self, tmp_path: Path) -> None:
        """An over-limit directive line the diff does NOT touch is not
        flagged -- FMT001 is diff-scoped, same posture as TODO001."""
        long_reason = "x" * 70
        source = (
            "def helper(x):\n"
            f'    # frob:waive INV006 reason="{long_reason}"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(3, 3)),))
        violations = fmt_gate(tmp_path, diff)
        assert not any(v.rule == "FMT001" for v in violations)

    # frob:ticket T-0851
    def test_short_directive_not_flagged(self, tmp_path: Path) -> None:
        """A `frob:` directive line that already fits within the limit is
        not flagged, even when touched."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(2, 2)),))
        violations = fmt_gate(tmp_path, diff)
        assert not any(v.rule == "FMT001" for v in violations)


class TestDupPipelineClosureConsumers:
    """T-0814: `frob.dup._pipeline`'s raw `CallGraph.calls` consumers share
    the same non-symref-entry assumption as the `frob.gates` COV006
    closure consumers (T-0809 reviewer condition b) -- covered here,
    scoped to `tests/test_gates.py` per T-0814's declared scope."""

    # frob:ticket T-0814
    # frob:tests tests/test_gates.py::TestDupPipelineClosureConsumers.test_is_symref_dup kind="unit"  # noqa: E501
    def test_is_symref_dup(self) -> None:
        """T-0814: `frob.dup._pipeline._is_symref` mirrors `frob.gates`'s
        helper of the same name -- both files are outside a shared home
        (`frob/graph/callgraph.py`) per T-0814's declared scope, so each
        keeps its own copy of this one-line predicate."""
        from frob.dup._pipeline import _is_symref
        from frob.graph.callgraph import UNRESOLVED_CALLEE

        assert _is_symref("src/a.py::_helper") is True
        assert _is_symref(UNRESOLVED_CALLEE) is False

    # frob:ticket T-0814
    # frob:tests tests/test_gates.py::TestDupPipelineClosureConsumers.test_callee_name_map_skips_unresolved_callee_sentinel kind="unit"  # noqa: E501
    def test_callee_name_map_skips_unresolved_callee_sentinel(self) -> None:
        """T-0814: `_callee_name_map` iterates `graph.calls.get(caller, ())`
        and used to do `callee_symref.split("::", 1)[1]` unconditionally --
        a bare `UNRESOLVED_CALLEE` sentinel entry (no `::`) IndexErrors
        that. A `CallGraph` carrying the sentinel alongside a real callee
        must not raise, and the real callee must still resolve -- the
        sentinel is skipped, not silently swallowing real entries too."""
        from frob.dup._pipeline import _callee_name_map
        from frob.graph.callgraph import UNRESOLVED_CALLEE, CallGraph

        graph = CallGraph(
            calls={
                "src/a.py::caller": ("src/a.py::_real_helper", UNRESOLVED_CALLEE),
            }
        )
        result = _callee_name_map(graph, "src/a.py::caller")
        assert result == {"_real_helper": "src/a.py::_real_helper"}


class TestDsl001:
    """T-0404 finding 5: a malformed `frob:` directive not already claimed
    by WAIVE001/TEST010/DEBT001 must still be surfaced, not silently
    dropped."""

    def test_malformed_frob_doc_directive_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_dsl001_violations kind="unit"
        # A bare `frob:doc` with no target parses to a MalformedDirective
        # ("missing target for verb 'doc'") -- before DSL001 existed this
        # produced NO violation at all.
        source = "def helper(x):\n    # frob:doc\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates import _dsl001_violations  # noqa: PLC0415

        violations = _dsl001_violations(snap)
        assert any(v.rule == "DSL001" for v in violations)
        assert violations[0].severity == Severity.ERROR

    def test_waive_reason_and_tests_kind_not_double_flagged(
        self, tmp_path: Path
    ) -> None:
        # A malformed frob:waive (no reason) and a malformed frob:tests
        # (bad kind=) are already surfaced by WAIVE001/TEST010 -- DSL001
        # must not ALSO flag them (no double-reporting the same directive).
        source = (
            "def helper(x):\n"
            "    # frob:waive COV001\n"
            '    # frob:tests helper kind="bogus"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates import _dsl001_violations  # noqa: PLC0415

        assert _dsl001_violations(snap) == ()


class TestParseFailureGate:
    """T-0558: a swallowed frob.lang parse/IO failure must be an ERROR
    violation (PARSE001), not just a log line.

    frob:ticket T-0558
    frob:ticket T-0561
    """

    # frob:ticket T-0561
    def test_parse_failure_is_an_error_violation(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_parse_failures.py::parse_failure_gate kind="unit"
        from frob.gates._parse_failures import parse_failure_gate
        from frob.graph._models import ParseFailure

        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        snap = _snapshot(tmp_path)
        snap = snap.model_copy(
            update={
                "parse_failures": (
                    ParseFailure(file="src/broken.py", reason="ParseFailed"),
                )
            }
        )
        violations = parse_failure_gate(snap)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "PARSE001"
        assert v.severity == Severity.ERROR
        assert v.file == "src/broken.py"

    # frob:ticket T-0561
    def test_no_parse_failures_is_clean(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_parse_failures.py::parse_failure_gate kind="unit"
        from frob.gates._parse_failures import parse_failure_gate
        from frob.lang import reset_parse_cache

        # T-0905/T-0902: reset frob.lang's process-lifetime partial-parse
        # set before asserting "clean" -- an earlier test in this xdist
        # worker that parsed a syntax-error fixture (any test calling
        # build_graph directly, bypassing frob.check's own once-per-run
        # reset) would otherwise leak a stale PARSE002 entry in here.
        reset_parse_cache()
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        snap = _snapshot(tmp_path)
        assert parse_failure_gate(snap) == ()

    # frob:ticket T-0902
    def test_partial_parse_is_an_error_violation(self, tmp_path: Path) -> None:
        """T-0905/T-0902: a syntax error partway through a file (tree-sitter
        salvages a PARTIAL tree, not a hard failure) must fire PARSE002,
        symmetric with PARSE001's hard-failure handling -- the missing
        tail symbols are silently dropped from the salvaged tree
        otherwise, and no other gate would ever notice."""
        # frob:tests src/frob/gates/_parse_failures.py::parse_failure_gate kind="unit"
        from frob.gates._parse_failures import parse_failure_gate
        from frob.lang import reset_parse_cache

        reset_parse_cache()
        _write(
            tmp_path,
            "src/broken.py",
            "def good_one():\n    pass\n\ndef broken(:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        assert "src/broken.py::good_one" in snap.symbols

        violations = parse_failure_gate(snap)
        reset_parse_cache()
        hits = [v for v in violations if v.rule == "PARSE002"]
        assert len(hits) == 1
        assert hits[0].severity == Severity.ERROR
        assert "broken.py" in hits[0].file

    # frob:ticket T-0942
    def test_partial_parse_in_graph_excluded_path_is_silent(
        self, tmp_path: Path
    ) -> None:
        """T-0942: a graph-excluded path (frob.toml [graph].exclude, e.g. a
        deliberately-broken parser fixture) contributes no symbols to the
        obligation graph, so PARSE002's missing-symbols claim is vacuous
        there -- and in-file waivers cannot bind on excluded paths. The
        gate must stay silent for it while still firing on a non-excluded
        partial parse in the same run."""
        # frob:tests src/frob/gates/_parse_failures.py::parse_failure_gate kind="unit"
        from frob.gates._parse_failures import parse_failure_gate
        from frob.lang import reset_parse_cache

        reset_parse_cache()
        _write(
            tmp_path,
            "frob.toml",
            '[graph]\nexclude = ["fixtures/**"]\n',
        )
        _write(
            tmp_path,
            "fixtures/broken_fixture.py",
            "def good_one():\n    pass\n\ndef broken(:\n    pass\n",
        )
        _write(
            tmp_path,
            "src/broken.py",
            "def good_one():\n    pass\n\ndef broken(:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = parse_failure_gate(snap)
        reset_parse_cache()
        hits = [v for v in violations if v.rule == "PARSE002"]
        assert len(hits) == 1
        assert "src/broken.py" in hits[0].file

    # frob:ticket T-0902
    def test_no_partial_parses_is_clean(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_parse_failures.py::parse_failure_gate kind="unit"
        from frob.gates._parse_failures import parse_failure_gate
        from frob.lang import reset_parse_cache

        reset_parse_cache()
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        snap = _snapshot(tmp_path)
        violations = parse_failure_gate(snap)
        reset_parse_cache()
        assert not any(v.rule == "PARSE002" for v in violations)


class TestDeadSymbolGate:
    """T-0422: an unreferenced private symbol (written but never wired) is
    the symbol-level analog of REF001's anti-orphan file gate.

    frob:ticket T-0422
    """

    # frob:ticket T-0422
    def test_unwired_private_function_is_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _never_called() -> None:\n    pass\n\n\ndef foo() -> None:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert any(
            v.rule == "DEAD001" and "_never_called" in v.message for v in violations
        )
        assert all(v.severity == Severity.WARN for v in violations)

    # frob:ticket T-0422
    def test_called_private_helper_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _helper() -> int:\n"
            "    return 1\n"
            "\n\n"
            "def foo() -> int:\n"
            "    return _helper()\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert not any("_helper" in v.message for v in violations)

    # frob:ticket T-0422
    def test_dunder_method_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "class Foo:\n    def __init__(self) -> None:\n        pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert not any("__init__" in v.message for v in violations)

    # frob:ticket T-0422
    def test_test_function_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "class Foo:\n    def _test_never_called_directly(self) -> None:\n        pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert not any("_test_never_called_directly" in v.message for v in violations)

    # frob:ticket T-0422
    def test_tests_edge_target_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _never_called() -> None:\n"
            '    # frob:tests tests/test_a.py::test_never_called kind="unit"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert not any("_never_called" in v.message for v in violations)


# frob:ticket T-0813
class TestProtocolSummaryGate:
    """T-0813: the production `mark_unresolved=True` wiring into
    `compute_protocol_summaries` -- a `frob:requires`/`frob:transition`-
    tagged symbol whose transitive call closure hits an unresolved private
    callee is PROTO001; a clean or untagged one is not."""

    def test_unresolved_callee_poisons_a_protocol_tagged_symbol(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> None:\n"
            '    # frob:requires proto="Lock" state="held"\n'
            "    _do_work()\n"
            "\n\n"
            "def _do_work() -> None:\n"
            "    _missing_helper()\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next((v for v in violations if v.rule == "PROTO001"), None)
        assert v is not None
        assert "src/a.py::enter" in v.message
        assert v.severity == Severity.WARN

    def test_clean_protocol_tagged_symbol_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> None:\n"
            '    # frob:requires proto="Lock" state="held"\n'
            "    _do_work()\n"
            "\n\n"
            "def _do_work() -> None:\n"
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO001" for v in violations)

    def test_untagged_symbol_with_unresolved_call_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> None:\n"
            '    # frob:requires proto="Lock" state="held"\n'
            "    pass\n"
            "\n\n"
            "def untagged() -> None:\n"
            "    _missing_helper()\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO001" for v in violations)

    def test_real_repo_scan_runs_end_to_end_without_crashing(self) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="integration"
        # T-0813: the honest "real repo scan" smoke test -- runs the actual
        # production entrypoint (build_call_graph(mark_unresolved=True) +
        # compute_protocol_summaries) over this repo's OWN real graph
        # snapshot, not a hand-fabricated fixture. Nothing in this repo's
        # production code carries a frob:requires/frob:transition directive
        # yet (T-0744's declaration surface has no first production
        # consumer besides this gate's own tests), so 0 violations is the
        # correct, honest result today -- the assertion that matters is
        # that a real repo scan, including every UNRESOLVED_CALLEE the
        # dunder/cross-package exemption (T-0813) had to be built to
        # filter, completes without the IndexError/crash class T-0809's
        # own Done report disclosed as the reason mark_unresolved defaulted
        # to False.
        from frob.gates._protocol_summary import protocol_summary_gate

        root = Path(__file__).resolve().parents[1]
        snap = _snapshot(root)
        violations = protocol_summary_gate(root, snap)
        assert isinstance(violations, tuple)


# frob:ticket T-0746
# frob:ticket T-0841
class TestProtocolVerificationGate:
    """T-0746: PROTO002 (state-requirement violation) and PROTO003 (invalid
    transition), the ERROR-tier verification rules sharing PROTO001's
    per-package `protocol_summary_gate` scan. T-0841 adds the Rust/
    TypeScript real-repo-scan cases."""

    def test_state_never_established_is_an_error(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next((v for v in violations if v.rule == "PROTO002"), None)
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "src/a.py::enter" in v.message
        assert "Net" in v.message and "active" in v.message

    def test_state_established_by_a_reachable_transition_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def net_init() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n"
            "\n\n"
            "def enter() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO002" for v in violations)

    def test_state_equal_to_initial_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:protocol Net states="idle,active" initial="idle"\n'
            "def enter() -> None:\n"
            '    # frob:requires proto="Net" state="idle"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO002" for v in violations)

    def test_poisoned_summary_at_a_requires_symbol_is_an_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    _do_work()\n"
            "\n\n"
            "def _do_work() -> None:\n"
            "    _missing_helper()\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next((v for v in violations if v.rule == "PROTO002"), None)
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "poisoned" in v.message

    def test_invalid_transition_precondition_never_established_is_an_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def net_close() -> None:\n"
            '    # frob:transition proto="Net" from="active" to="closed"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next((v for v in violations if v.rule == "PROTO003"), None)
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "src/a.py::net_close" in v.message
        assert "active" in v.message

    def test_valid_transition_chain_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:protocol Net states="idle,active,closed" initial="idle"\n'
            "def net_init() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n"
            "\n\n"
            "def net_close() -> None:\n"
            '    # frob:transition proto="Net" from="active" to="closed"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO003" for v in violations)

    def test_python_with_block_discharges_the_requirement(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    with Net() as _n:\n"
            "        pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        error = next(
            (
                v
                for v in violations
                if v.rule == "PROTO002" and v.severity == Severity.ERROR
            ),
            None,
        )
        assert error is None
        discharge = next((v for v in violations if v.rule == "PROTO002"), None)
        assert discharge is not None
        assert discharge.severity == Severity.WARN
        assert "python-with" in discharge.message

    # frob:ticket T-0841
    def test_rust_file_state_never_established_is_an_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # T-0841: PROTO002 now real-repo-scans Rust files too, not just
        # Python -- proves the gate's own `.py`-only filter is lifted.
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.rs",
            '// frob:requires proto="Net" state="active"\nfn enter() {\n}\n',
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next((v for v in violations if v.rule == "PROTO002"), None)
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "src/a.rs::enter" in v.message

    # frob:ticket T-0841
    def test_rust_drop_impl_discharges_the_requirement(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # T-0841: `_discharge` dispatches to `rust_drop_discharge` for a
        # `.rs` file -- the real cross-language discharge wiring this
        # ticket adds (T-0746 built the predicate, only Python was wired).
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.rs",
            '// frob:requires proto="Net" state="active"\n'
            "fn enter() {\n"
            "}\n"
            "impl Drop for Net {\n"
            "    fn drop(&mut self) {}\n"
            "}\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        error = next(
            (
                v
                for v in violations
                if v.rule == "PROTO002" and v.severity == Severity.ERROR
            ),
            None,
        )
        assert error is None
        discharge = next((v for v in violations if v.rule == "PROTO002"), None)
        assert discharge is not None
        assert discharge.severity == Severity.WARN
        assert "rust-drop" in discharge.message

    # frob:ticket T-0841
    def test_typescript_using_discharges_the_requirement(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.ts",
            '// frob:requires proto="Net" state="active"\n'
            "function enter(): void {\n"
            "  using n = Net();\n"
            "}\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        error = next(
            (
                v
                for v in violations
                if v.rule == "PROTO002" and v.severity == Severity.ERROR
            ),
            None,
        )
        assert error is None
        discharge = next((v for v in violations if v.rule == "PROTO002"), None)
        assert discharge is not None
        assert discharge.severity == Severity.WARN
        assert "typescript-using" in discharge.message


# frob:ticket T-0840
class TestProtocolOrderingGate:
    """T-0840: PROTO004, the per-call-site ordering check that narrows
    PROTO002/PROTO003's existential ("established SOMEWHERE in the
    closure") approximation using `build_ordered_call_graph`'s source-
    text-ordered call sequences."""

    # frob:ticket T-0840
    def test_call_before_establishing_transition_is_an_ordering_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # The crisp T-0840 case: `caller` calls `_consume` (requires
        # Net:active) BEFORE `_establish` (transitions Net idle->active)
        # -- a real ordering bug. PROTO002's existential check alone
        # would NOT catch this (state IS established somewhere in the
        # closure, just too late) -- see the companion test below.
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def caller() -> None:\n"
            "    _consume()\n"
            "    _establish()\n"
            "\n\n"
            "def _consume() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    pass\n"
            "\n\n"
            "def _establish() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        # PROTO002's own existential check does not fire here -- disclosed
        # limitation this ticket narrows, not replaces.
        assert not any(v.rule == "PROTO002" for v in violations)
        v = next((v for v in violations if v.rule == "PROTO004"), None)
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "src/a.py::caller" in v.message
        assert "src/a.py::_consume" in v.message
        assert "Net" in v.message and "active" in v.message

    # frob:ticket T-0840
    def test_call_after_establishing_transition_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # Same functions, correct order: no PROTO004.
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def caller() -> None:\n"
            "    _establish()\n"
            "    _consume()\n"
            "\n\n"
            "def _consume() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    pass\n"
            "\n\n"
            "def _establish() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO004" for v in violations)

    # frob:ticket T-0840
    def test_python_with_block_discharges_the_ordering_violation(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # The same language-excuse discharge PROTO002/PROTO003 get,
        # checked against the CALLER's own file.
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def caller() -> None:\n"
            "    with Net() as _n:\n"
            "        _consume()\n"
            "        _establish()\n"
            "\n\n"
            "def _consume() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    pass\n"
            "\n\n"
            "def _establish() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        error = next(
            (
                v
                for v in violations
                if v.rule == "PROTO004" and v.severity == Severity.ERROR
            ),
            None,
        )
        assert error is None
        discharge = next((v for v in violations if v.rule == "PROTO004"), None)
        assert discharge is not None
        assert discharge.severity == Severity.WARN
        assert "python-with" in discharge.message


# frob:ticket T-0746
class TestProtocolLanguageExcuseDischarge:
    """T-0746: the per-language discharge predicates
    (`frob.arch._protocol_excuse`) each rule's language-excuse doctrine
    reduces to -- built and directly tested here even where a real
    cross-file repo-scan wiring for that language is not built yet
    (Rust/C++/TypeScript/GC, disclosed T-0839 follow-up; see
    docs/modules/gates.md#proto002-proto003-t-0746)."""

    def test_rust_drop_impl_discharges(self) -> None:
        # frob:tests \
        # tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_rust_drop_impl_\
        # discharges
        from frob.arch._protocol_excuse import rust_drop_discharge

        source = "struct Net;\nimpl Drop for Net {\n    fn drop(&mut self) {}\n}\n"
        result = rust_drop_discharge(source, "Net")
        assert result.discharged
        assert result.mechanism == "rust-drop"

    def test_rust_mem_forget_revokes_the_drop_discharge(self) -> None:
        # frob:tests \
        # tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_rust_mem_forget\
        # _revokes_the_drop_discharge
        from frob.arch._protocol_excuse import rust_drop_discharge

        source = (
            "struct Net;\n"
            "impl Drop for Net {\n    fn drop(&mut self) {}\n}\n"
            "fn leak(n: Net) {\n    mem::forget(n);\n}\n"
        )
        result = rust_drop_discharge(source, "Net")
        assert not result.discharged
        assert "forget" in result.reason

    def test_rust_manually_drop_revokes_the_discharge(self) -> None:
        # frob:tests \
        # tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_rust_manually_d\
        # rop_revokes_the_discharge
        from frob.arch._protocol_excuse import rust_drop_discharge

        source = (
            "struct Net;\n"
            "impl Drop for Net {\n    fn drop(&mut self) {}\n}\n"
            "struct Holder(ManuallyDrop<Net>);\n"
        )
        result = rust_drop_discharge(source, "Net")
        assert not result.discharged
        assert "ManuallyDrop" in result.reason

    def test_rust_no_drop_impl_is_not_discharged(self) -> None:
        # frob:tests \
        # tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_rust_no_drop_im\
        # pl_is_not_discharged
        from frob.arch._protocol_excuse import rust_drop_discharge

        result = rust_drop_discharge("struct Net;\n", "Net")
        assert not result.discharged

    def test_cpp_raii_destructor_discharges(self) -> None:
        # frob:tests \
        # tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_cpp_raii_destru\
        # ctor_discharges
        from frob.arch._protocol_excuse import cpp_raii_discharge

        source = "class Net {\npublic:\n    ~Net() {}\n};\n"
        result = cpp_raii_discharge(source, "Net")
        assert result.discharged
        assert result.mechanism == "cpp-raii"

    def test_cpp_no_destructor_is_not_discharged(self) -> None:
        # frob:tests \
        # tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_cpp_no_destruct\
        # or_is_not_discharged
        from frob.arch._protocol_excuse import cpp_raii_discharge

        result = cpp_raii_discharge("class Net {\n};\n", "Net")
        assert not result.discharged

    def test_python_with_block_discharges(self) -> None:
        # frob:tests \
        # tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_python_with_blo\
        # ck_discharges
        from frob.arch._protocol_excuse import python_with_discharge

        result = python_with_discharge("with Net() as n:\n    pass\n", "Net")
        assert result.discharged
        assert result.mechanism == "python-with"

    def test_python_no_with_block_is_not_discharged(self) -> None:
        # frob:tests \
        # tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_python_no_with_\
        # block_is_not_discharged
        from frob.arch._protocol_excuse import python_with_discharge

        result = python_with_discharge("Net().connect()\n", "Net")
        assert not result.discharged

    def test_typescript_using_discharges(self) -> None:
        # frob:tests \
        # tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_typescript_usin\
        # g_discharges
        from frob.arch._protocol_excuse import typescript_using_discharge

        result = typescript_using_discharge("using n = Net();\n", "Net")
        assert result.discharged
        assert result.mechanism == "typescript-using"

    def test_typescript_try_finally_discharges(self) -> None:
        # frob:tests \
        # tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_typescript_try_\
        # finally_discharges
        from frob.arch._protocol_excuse import typescript_using_discharge

        source = "try {\n  n.use();\n} finally {\n  n.close();\n}\n"
        result = typescript_using_discharge(source, "n")
        assert result.discharged
        assert result.mechanism == "typescript-try-finally"

    def test_typescript_bare_call_is_not_discharged(self) -> None:
        # frob:tests \
        # tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_typescript_bare\
        # _call_is_not_discharged
        from frob.arch._protocol_excuse import typescript_using_discharge

        result = typescript_using_discharge("net.connect();\n", "net")
        assert not result.discharged

    def test_gc_finalizer_never_discharges(self) -> None:
        # frob:tests \
        # tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_gc_finalizer_ne\
        # ver_discharges
        from frob.arch._protocol_excuse import gc_finalizer_discharge

        result = gc_finalizer_discharge("Net")
        assert not result.discharged
        assert result.mechanism == "gc-finalizer"


# frob:ticket T-0747
class TestCleanupObligationGate:
    """T-0747: PROTO005, cleanup obligations -- release-postdominates-
    acquisition on all exits (including exceptional, via T-0686's
    may-raise sets), escape transfer, and per-protocol cleanup="always"
    deinit-never-called."""

    def test_early_return_before_release_call_is_an_error(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def open_conn() -> int:\n"
            "    # frob:acquire conn\n"
            "    fd = 1\n"
            "    if fd < 0:\n"
            "        return -1\n"
            "    _close(fd)\n"
            "    return 0\n"
            "\n\n"
            "def _close(fd: int) -> None:\n"
            "    # frob:release conn\n"
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next((v for v in violations if v.rule == "PROTO005"), None)
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "src/a.py::open_conn" in v.message
        assert "conn" in v.message

    def test_release_before_return_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def open_conn() -> int:\n"
            "    # frob:acquire conn\n"
            "    fd = 1\n"
            "    _close(fd)\n"
            "    return 0\n"
            "\n\n"
            "def _close(fd: int) -> None:\n"
            "    # frob:release conn\n"
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO005" for v in violations)

    def test_escape_transfer_discharges_the_obligation(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def open_conn() -> int:\n"
            "    # frob:acquire conn\n"
            "    # frob:escapes conn\n"
            "    if True:\n"
            "        return -1\n"
            "    return 1\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO005" for v in violations)

    def test_self_contained_acquire_and_release_is_trusted(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def open_and_close() -> int:\n"
            "    # frob:acquire conn\n"
            "    # frob:release conn\n"
            "    if True:\n"
            "        return -1\n"
            "    return 0\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO005" for v in violations)

    def test_python_with_block_discharges_the_acquisition(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> int:\n"
            "    # frob:acquire conn\n"
            "    with conn() as _c:\n"
            "        if bad():\n"
            "            return -1\n"
            "    return 0\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        error = next(
            (
                v
                for v in violations
                if v.rule == "PROTO005" and v.severity == Severity.ERROR
            ),
            None,
        )
        assert error is None
        discharge = next((v for v in violations if v.rule == "PROTO005"), None)
        assert discharge is not None
        assert discharge.severity == Severity.WARN
        assert "python-with" in discharge.message

    def test_process_exit_ok_policy_discharges_a_terminator_guarded_return(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # Same "early return before release" shape as the crisp true-
        # positive test above, but this acquisition's own frob:protocol
        # declares cleanup="process-exit-ok" and the early return is
        # itself preceded by a process-terminating call -- discharged
        # silently by the declared policy, per the module docstring's
        # per-protocol-policy clause.
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:protocol Res states="idle,active" initial="idle" '
            'cleanup="process-exit-ok"\n'
            "def open_conn() -> int:\n"
            "    # frob:acquire conn\n"
            "    fd = 1\n"
            "    if fd < 0:\n"
            "        exit(1)\n"
            "        return -1\n"
            "    _close(fd)\n"
            "    return 0\n"
            "\n\n"
            "def _close(fd: int) -> None:\n"
            "    # frob:release conn\n"
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO005" for v in violations)

    def test_exceptional_exit_with_no_release_anywhere_is_an_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # Reuses T-0686's compute_may_raise: open_conn calls a same-module
        # function that unconditionally raises, and NOTHING in open_conn's
        # own body ever releases "conn" -- an exceptional exit skips
        # cleanup.
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def open_conn() -> None:\n"
            "    # frob:acquire conn\n"
            "    _maybe_raise()\n"
            "    return\n"
            "\n\n"
            "def _maybe_raise() -> None:\n"
            '    raise ValueError("bad")\n',
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next(
            (
                v
                for v in violations
                if v.rule == "PROTO005" and "may raise" in v.message
            ),
            None,
        )
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "src/a.py::open_conn" in v.message

    def test_deinit_never_called_for_cleanup_always_protocol_is_an_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:protocol Net states="idle,active,closed" initial="idle" '
            'cleanup="always"\n'
            "def net_init() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next(
            (
                v
                for v in violations
                if v.rule == "PROTO005" and "deinit-never-called" in v.message
            ),
            None,
        )
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "Net" in v.message and "closed" in v.message

    def test_deinit_reachable_for_cleanup_always_protocol_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:protocol Net states="idle,active,closed" initial="idle" '
            'cleanup="always"\n'
            "def net_init() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n"
            "\n\n"
            "def net_close() -> None:\n"
            '    # frob:transition proto="Net" from="active" to="closed"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(
            v.rule == "PROTO005" and "deinit-never-called" in v.message
            for v in violations
        )


# frob:ticket T-0731
# frob:ticket T-0601
class TestDebtGate:
    """T-0412: frob:debt vs frob:waive -- malformed directive (DEBT001),
    non-open ticket (DEBT002), expired until boundary (DEBT003)."""

    def test_debt002_closed_ticket_is_reported(self, tmp_path: Path) -> None:
        """T-0412: a frob:debt bound to a closed ticket is DEBT002 -- a debt
        must point at real, OPEN, owed work."""
        # frob:tests \
        # tests/test_gates.py::TestDebtGate.test_debt002_closed_ticket_is_reported
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.DONE)})
        violations = debt_gate(
            snap, queue, current_date="2026-01-01", current_version="0.1.0"
        )
        v = _first_rule(violations, "DEBT002")
        assert v is not None
        assert v.severity == Severity.ERROR

    def test_debt002_open_ticket_is_silent(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates.py::TestDebtGate.test_debt002_open_ticket_is_silent
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = debt_gate(
            snap, queue, current_date="2026-01-01", current_version="0.1.0"
        )
        assert not any(v.rule == "DEBT002" for v in violations)

    def test_debt003_expired_by_date_is_reported(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates.py::TestDebtGate.test_debt003_expired_by_date_is_reported
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001" '
            'until="2026-01-01"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = debt_gate(
            snap, queue, current_date="2026-06-01", current_version="0.1.0"
        )
        v = _first_rule(violations, "DEBT003")
        assert v is not None
        assert v.severity == Severity.ERROR

    def test_debt003_not_yet_expired_is_silent(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates.py::TestDebtGate.test_debt003_not_yet_expired_is_silent
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001" '
            'until="2099-01-01"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = debt_gate(
            snap, queue, current_date="2026-01-01", current_version="0.1.0"
        )
        assert not any(v.rule == "DEBT003" for v in violations)

    def test_debt003_expired_by_version_is_reported(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates.py::TestDebtGate.test_debt003_expired_by_version_is_reported
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001" '
            'until="1.0.0"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = debt_gate(
            snap, queue, current_date="2026-01-01", current_version="1.2.0"
        )
        v = _first_rule(violations, "DEBT003")
        assert v is not None

    def test_debt001_malformed_directive_is_reported(self, tmp_path: Path) -> None:
        """T-0412: frob:debt requires BOTH reason= and ticket= -- missing
        either is DEBT001, mirroring WAIVE001's shape for frob:waive."""
        # frob:tests \
        # tests/test_gates.py::TestDebtGate.test_debt001_malformed_directive_is_reported
        source = 'def helper(x):\n    # frob:debt TEST005 reason="coverage gap"\n    return x\n'
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = debt_gate(
            snap, queue, current_date="2026-01-01", current_version="0.1.0"
        )
        v = _first_rule(violations, "DEBT001")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "ticket" in v.message

    def test_clean_debt_produces_no_violations(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates.py::TestDebtGate.test_clean_debt_produces_no_violations
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001" '
            'until="2099-01-01"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = debt_gate(
            snap, queue, current_date="2026-01-01", current_version="0.1.0"
        )
        assert violations == ()

    def test_lists_every_debt_entry(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates.py::TestDebtGate.test_lists_every_debt_entry
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001" '
            'until="2099-01-01"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        entries = list_debt(snap, current_date="2026-01-01", current_version="0.1.0")
        assert len(entries) == 1
        entry = entries[0]
        assert entry.rule == "TEST005"
        assert entry.ticket == "T-0001"
        assert entry.until == "2099-01-01"
        assert entry.expired is False

    def test_release_gate_fails_while_debt_is_open(self, tmp_path: Path) -> None:
        """T-0412's central requirement: a release must never ship with ANY
        open frob:debt, expired or not."""
        # frob:tests \
        # tests/test_gates.py::TestDebtGate.test_release_gate_fails_while_debt_is_open
        from frob.gates import release_gate
        from frob.release import stamp

        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "0.1.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "0.1.0").is_ok
        violations = release_gate(tmp_path, snap)
        assert any(v.rule == "REL001" and "frob:debt" in v.message for v in violations)

    # frob:ticket T-0731
    def test_release_gate_bump_fires_without_frob_agent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0731: with `FROB_AGENT` unset (a coordinator shell), REL001
        still demands the version bump exactly as before."""
        # frob:tests tests/test_gates.py::TestDebtGate.test_release_gate_bump_fires_without_frob_agent  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp

        monkeypatch.delenv("FROB_AGENT", raising=False)
        _write(tmp_path, "src/a.py", "def a(x: int) -> int:\n    return x\n")
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "1.0.0").is_ok

        _write(
            tmp_path,
            "src/a.py",
            "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n",
        )
        (tmp_path / ".frob" / "cache.db").unlink()
        snap2 = _snapshot(tmp_path)
        violations = release_gate(tmp_path, snap2)
        assert any(
            v.rule == "REL001" and "public API changed" in v.message for v in violations
        )

    # frob:ticket T-0731
    def test_release_gate_bump_suppressed_under_frob_agent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0731: with `FROB_AGENT` set (every dispatched worktree agent),
        the version-bump/changelog half of REL001 is suppressed -- the
        bump is a land-time step `frob ticket land` computes, never
        something an agent must do itself."""
        # frob:tests tests/test_gates.py::TestDebtGate.test_release_gate_bump_suppressed_under_frob_agent  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp

        _write(tmp_path, "src/a.py", "def a(x: int) -> int:\n    return x\n")
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "1.0.0").is_ok

        _write(
            tmp_path,
            "src/a.py",
            "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n",
        )
        (tmp_path / ".frob" / "cache.db").unlink()
        snap2 = _snapshot(tmp_path)

        monkeypatch.setenv("FROB_AGENT", "test-agent-1")
        violations = release_gate(tmp_path, snap2)
        assert not any(
            v.rule == "REL001" and "public API changed" in v.message for v in violations
        )
        assert not any(
            v.rule == "REL001" and "no CHANGELOG.md entry" in v.message
            for v in violations
        )

    # frob:ticket T-0807
    def test_rel001_not_land_owned_root_checkout_no_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0807: a plain root-checkout `frob check` run (real git repo, no
        `--ticket`, no live lease, `FROB_AGENT` unset) is NOT land-owned --
        REL001 still errors exactly as before T-0807."""
        # frob:tests tests/test_gates.py::TestDebtGate.test_rel001_not_land_owned_root_checkout_no_ticket  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp

        monkeypatch.delenv("FROB_AGENT", raising=False)
        _run(["git", "init", "-q", "-b", "main"], tmp_path)
        _run(["git", "config", "user.email", "test@example.com"], tmp_path)
        _run(["git", "config", "user.name", "Test"], tmp_path)
        _write(tmp_path, "src/a.py", "def a(x: int) -> int:\n    return x\n")
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "1.0.0").is_ok
        _run(["git", "add", "-A"], tmp_path)
        _run(["git", "commit", "-q", "-m", "init"], tmp_path)

        _write(
            tmp_path,
            "src/a.py",
            "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n",
        )
        (tmp_path / ".frob" / "cache.db").unlink()
        snap2 = _snapshot(tmp_path)

        violations = release_gate(tmp_path, snap2, None)
        assert any(
            v.rule == "REL001"
            and v.severity is Severity.ERROR
            and "public API changed" in v.message
            for v in violations
        )

    # frob:ticket T-0807
    def test_rel001_land_owned_via_linked_worktree_no_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0807: a check run from a LINKED worktree is land-owned even
        with no `--ticket` in play -- the bump reports as an informational
        `WARN`, never an `ERROR`."""
        # frob:tests tests/test_gates.py::TestDebtGate.test_rel001_land_owned_via_linked_worktree_no_ticket  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp

        monkeypatch.delenv("FROB_AGENT", raising=False)
        main_root = tmp_path / "main"
        main_root.mkdir()
        _run(["git", "init", "-q", "-b", "main"], main_root)
        _run(["git", "config", "user.email", "test@example.com"], main_root)
        _run(["git", "config", "user.name", "Test"], main_root)
        _write(main_root, "src/a.py", "def a(x: int) -> int:\n    return x\n")
        _write(
            main_root, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n'
        )
        snap = _snapshot(main_root)
        assert stamp(main_root, snap, "1.0.0").is_ok
        _run(["git", "add", "-A"], main_root)
        _run(["git", "commit", "-q", "-m", "init"], main_root)

        worktree_root = tmp_path / "wt"
        _run(
            ["git", "worktree", "add", "-q", "-b", "T-0807-wt", str(worktree_root)],
            main_root,
        )
        _write(
            worktree_root,
            "src/a.py",
            "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n",
        )
        snap2 = _snapshot(worktree_root)

        violations = release_gate(worktree_root, snap2, None)
        assert not any(
            v.rule == "REL001" and v.severity is Severity.ERROR for v in violations
        )
        # T-0894 review fix: the note must name the TARGET version (>= 1.1.0
        # for a minor bump off 1.0.0), not just the bump class -- a reviewer
        # otherwise sees "public API changed (minor)" with no idea what
        # `frob ticket land` will actually bump to.
        assert any(
            v.rule == "REL001"
            and v.severity is Severity.WARN
            and "public API changed" in v.message
            and "land will bump to >= 1.1.0" in v.message
            for v in violations
        )

    # frob:ticket T-0807
    # frob:ticket T-0601
    def test_rel001_land_owned_via_ticket_lease(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0807: a check run with `--ticket T-XXXX` whose lease pins to
        THIS root (no linked worktree required -- e.g. a single-checkout
        repo with an in-progress ticket) is also land-owned via the lease."""
        # frob:tests tests/test_gates.py::TestDebtGate.test_rel001_land_owned_via_ticket_lease  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp
        from frob.tickets._leases import _LeaseRecord, leases_dir

        monkeypatch.delenv("FROB_AGENT", raising=False)
        _run(["git", "init", "-q", "-b", "main"], tmp_path)
        _run(["git", "config", "user.email", "test@example.com"], tmp_path)
        _run(["git", "config", "user.name", "Test"], tmp_path)
        _write(tmp_path, "src/a.py", "def a(x: int) -> int:\n    return x\n")
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "1.0.0").is_ok
        _run(["git", "add", "-A"], tmp_path)
        _run(["git", "commit", "-q", "-m", "init"], tmp_path)

        leases_root_result = leases_dir(tmp_path)
        assert leases_root_result.is_ok
        leases_root = leases_root_result.danger_ok
        leases_root.mkdir(parents=True, exist_ok=True)
        record = _LeaseRecord(
            ticket_id="T-0900",
            scope=("src/a.py",),
            worktree=str(tmp_path.resolve()),
            branch="main",
            recorded_at="2026-07-23T00:00:00+00:00",
        )
        (leases_root / "T-0900.json").write_text(
            record.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )

        _write(
            tmp_path,
            "src/a.py",
            "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n",
        )
        (tmp_path / ".frob" / "cache.db").unlink()
        snap2 = _snapshot(tmp_path)

        violations = release_gate(tmp_path, snap2, "T-0900")
        assert not any(
            v.rule == "REL001" and v.severity is Severity.ERROR for v in violations
        )
        assert any(
            v.rule == "REL001" and v.severity is Severity.WARN for v in violations
        )

    # frob:ticket T-0807
    def test_rel001_linked_worktree_detected(self, tmp_path: Path) -> None:
        """T-0807: `_rel001_is_linked_worktree` is `True` for a linked
        worktree and `False` for the main checkout it was created from."""
        # frob:tests tests/test_gates.py::TestDebtGate.test_rel001_linked_worktree_detected  # noqa: E501
        from frob.gates import _rel001_is_linked_worktree

        main_root = tmp_path / "main"
        main_root.mkdir()
        _run(["git", "init", "-q", "-b", "main"], main_root)
        _run(["git", "config", "user.email", "test@example.com"], main_root)
        _run(["git", "config", "user.name", "Test"], main_root)
        (main_root / "README.md").write_text("x\n", encoding="utf-8")
        _run(["git", "add", "-A"], main_root)
        _run(["git", "commit", "-q", "-m", "init"], main_root)

        worktree_root = tmp_path / "wt"
        _run(
            ["git", "worktree", "add", "-q", "-b", "T-0807-detect", str(worktree_root)],
            main_root,
        )

        assert _rel001_is_linked_worktree(main_root) is False
        assert _rel001_is_linked_worktree(worktree_root) is True


class TestDeprecatedGate:
    """T-0576: frob:deprecated -- frob:debt generalized to a public API's
    own sunset. Malformed directive (DEPR001), non-open ticket (DEPR002),
    still-in-window warning (DEPR003), past-sunset error (DEPR004)."""

    def test_depr001_malformed_directive_is_reported(self, tmp_path: Path) -> None:
        """T-0576: frob:deprecated requires BOTH sunset= and ticket= --
        missing either is DEPR001, mirroring DEBT001's shape."""
        # frob:tests tests/test_gates.py::TestDeprecatedGate.test_depr001_malformed_directive_is_reported  # noqa: E501
        source = 'def helper(x):\n    # frob:deprecated 0.1.0 ticket="T-0001"\n    return x\n'
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = deprecated_gate(snap, queue, current_date="2026-01-01")
        v = _first_rule(violations, "DEPR001")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "sunset" in v.message

    def test_depr001_malformed_sunset_is_reported(self, tmp_path: Path) -> None:
        """T-0576: a `sunset=` that is not a YYYY-MM-DD date is also DEPR001."""
        # frob:tests tests/test_gates.py::TestDeprecatedGate.test_depr001_malformed_sunset_is_reported  # noqa: E501
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="soon" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = deprecated_gate(snap, queue, current_date="2026-01-01")
        v = _first_rule(violations, "DEPR001")
        assert v is not None
        assert v.severity == Severity.ERROR

    def test_depr002_closed_ticket_is_reported(self, tmp_path: Path) -> None:
        """T-0576: a frob:deprecated bound to a closed ticket is DEPR002 --
        the ticket closed but the directive (presumably the symbol) is
        still here."""
        # frob:tests tests/test_gates.py::TestDeprecatedGate.test_depr002_closed_ticket_is_reported  # noqa: E501
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.DONE)})
        violations = deprecated_gate(snap, queue, current_date="2026-01-01")
        v = _first_rule(violations, "DEPR002")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert not any(v.rule in ("DEPR003", "DEPR004") for v in violations)

    def test_depr003_in_window_warns(self, tmp_path: Path) -> None:
        """T-0576: an open, not-yet-sunset frob:deprecated is a WARNING --
        visible, but does not fail `frob check`."""
        # frob:tests \
        # tests/test_gates.py::TestDeprecatedGate.test_depr003_in_window_warns
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = deprecated_gate(snap, queue, current_date="2026-01-01")
        v = _first_rule(violations, "DEPR003")
        assert v is not None
        assert v.severity == Severity.WARN
        assert not any(v.rule == "DEPR004" for v in violations)

    def test_depr004_past_sunset_errors(self, tmp_path: Path) -> None:
        """T-0576: an open frob:deprecated past its sunset date escalates
        from a warning to DEPR004, an ERROR."""
        # frob:tests tests/test_gates.py::TestDeprecatedGate.test_depr004_past_sunset_errors  # noqa: E501
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2026-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = deprecated_gate(snap, queue, current_date="2026-06-01")
        v = _first_rule(violations, "DEPR004")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert not any(v.rule == "DEPR003" for v in violations)

    def test_clean_deprecated_produces_no_violations(self, tmp_path: Path) -> None:
        """T-0576: a well-formed, open, still-in-window deprecation whose
        ticket is open produces only the DEPR003 warning, nothing else."""
        # frob:tests tests/test_gates.py::TestDeprecatedGate.test_clean_deprecated_produces_no_violations  # noqa: E501
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = deprecated_gate(snap, queue, current_date="2026-01-01")
        assert _rules(violations) == ["DEPR003"]

    def test_lists_every_deprecated_entry(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates.py::TestDeprecatedGate.test_lists_every_deprecated_entry  # noqa: E501
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        entries = list_deprecated(snap, current_date="2026-01-01")
        assert len(entries) == 1
        entry = entries[0]
        assert entry.since == "0.1.0"
        assert entry.ticket == "T-0001"
        assert entry.sunset == "2099-01-01"
        assert entry.expired is False

    def test_release_gate_fails_while_deprecated_is_past_sunset(
        self, tmp_path: Path
    ) -> None:
        """T-0576: a release must never ship while a frob:deprecated is past
        its sunset -- unlike frob:debt, a still-in-window one does not
        block a release."""
        # frob:tests tests/test_gates.py::TestDeprecatedGate.test_release_gate_fails_while_deprecated_is_past_sunset  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp

        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2020-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "0.1.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "0.1.0").is_ok
        violations = release_gate(tmp_path, snap)
        assert any(
            v.rule == "REL001" and "frob:deprecated" in v.message for v in violations
        )

    def test_release_gate_silent_while_deprecated_in_window(
        self, tmp_path: Path
    ) -> None:
        """T-0576: unlike frob:debt (blocks release for ANY open debt), a
        deprecation still inside its warning window does not block a
        release."""
        # frob:tests tests/test_gates.py::TestDeprecatedGate.test_release_gate_silent_while_deprecated_in_window  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp

        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "0.1.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "0.1.0").is_ok
        violations = release_gate(tmp_path, snap)
        assert not any(
            v.rule == "REL001" and "frob:deprecated" in v.message for v in violations
        )

    def test_deprecated_is_registered_in_all_gates(self) -> None:
        """T-0797: DEPR001-004 were implemented (T-0576) but 'deprecated' was
        never added to `_ALL_GATES`, so no real `frob check` run ever
        evaluated them (catalogued-is-not-enforced). Locks the registration
        so this cannot silently regress again."""
        # frob:tests tests/test_gates.py::TestDeprecatedGate.test_deprecated_is_registered_in_all_gates  # noqa: E501
        from frob.gates import _ALL_GATES

        assert "deprecated" in _ALL_GATES

    def test_deprecated_fires_through_real_gate_dispatch(self, tmp_path: Path) -> None:
        """T-0797: an end-to-end `run_gates` pass (no `--only` filter, the
        default gate selection) over a `frob:deprecated` directive still
        inside its warning window must surface DEPR003 -- proving the gate
        is actually wired into dispatch, not just callable in isolation."""
        # frob:tests tests/test_gates.py::TestDeprecatedGate.test_deprecated_fires_through_real_gate_dispatch  # noqa: E501
        _git_init(tmp_path)
        _write_ticket(tmp_path, _ticket(state=TicketState.QUEUED))
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
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
        v = _first_rule(report.violations, "DEPR003")
        assert v is not None
        assert v.severity == Severity.WARN


# frob:ticket T-0906
# frob:ticket T-0584
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

    # frob:ticket T-0906
    def test_scope001_fires_when_no_scope_declared(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0906/H1 (docs/audits/gates-vacuous.md): an empty ticket.scope
        # used to short-circuit scope_gate to a silent, unconditional pass
        # -- the least-declared-intent ticket got the LEAST enforcement.
        # It must now get the SAME (loud) SCOPE001 enforcement as any other
        # out-of-scope file.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=())
        diff = Diff(base="x", hunks=(Hunk(file="src/anything.py", span=(1, 1)),))
        violations = scope_gate(diff, ticket, snap)
        assert any(v.rule == "SCOPE001" for v in violations)

    # frob:ticket T-0906
    def test_scope001_empty_scope_ledger_still_implicitly_in_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0906: the ledger stays implicitly in scope even for a ticket
        # with no declared scope at all -- recording a Done report must
        # never itself trip SCOPE001.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=())
        diff = Diff(base="x", hunks=(Hunk(file="tickets.md", span=(1, 1)),))
        assert scope_gate(diff, ticket, snap) == ()

    # frob:ticket T-0899
    def test_scope001_empty_scope_never_returns_bare_empty_tuple_for_a_real_diff(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0899, the regression-gate pair for T-0906/H1: an in-progress
        # ticket carrying scope=() must never again silently coexist with
        # scope_gate returning the bare `()` no-violation sentinel for a
        # non-empty, out-of-scope diff -- multiple touched files must each
        # produce their own SCOPE001, not a single silently-cleared pass.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=())
        diff = Diff(
            base="x",
            hunks=(
                Hunk(file="src/one.py", span=(1, 1)),
                Hunk(file="src/two.py", span=(1, 1)),
            ),
        )
        violations = scope_gate(diff, ticket, snap)
        assert violations != ()
        assert {v.file for v in violations} == {"src/one.py", "src/two.py"}
        assert all(v.rule == "SCOPE001" for v in violations)

    def test_scope001_comma_joined_entry_splits_and_matches(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0241: a single 'a/,b/,c/' scope entry used to become one fnmatch
        # pattern that matched nothing; the Ticket model now splits it.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/a/**,src/b/**",))
        diff = Diff(base="x", hunks=(Hunk(file="src/b/f.py", span=(1, 1)),))
        assert scope_gate(diff, ticket, snap) == ()

    def test_scope001_dir_prefix_globs_recursively(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0241: a bare 'design/' scope entry now matches anything under it.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("design/",))
        diff = Diff(base="x", hunks=(Hunk(file="design/sub/f.py", span=(1, 1)),))
        assert scope_gate(diff, ticket, snap) == ()

    def test_scope001_ledger_implicitly_in_scope(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0241: tickets.md is always implicitly in every ticket's scope.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/a/**",))
        diff = Diff(base="x", hunks=(Hunk(file="tickets.md", span=(1, 1)),))
        assert scope_gate(diff, ticket, snap) == ()

    # frob:ticket T-0446
    def test_scope001_feature_ticket_cli_wiring_files_implicitly_in_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0446: a FEATURE ticket adding a new subcommand structurally
        # needs to touch the CLI dispatch/config/runner wiring files no
        # matter what scope it declared -- these must never trip SCOPE001.
        from frob.tickets._models import CLI_WIRING_FILES

        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/frob/tickets/**",), kind=TicketKind.FEATURE)
        diff = Diff(
            base="x",
            hunks=tuple(Hunk(file=f, span=(1, 1)) for f in sorted(CLI_WIRING_FILES)),
        )
        assert scope_gate(diff, ticket, snap) == ()

    def test_scope001_non_feature_ticket_cli_wiring_files_still_out_of_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0446: the exemption is FEATURE-only -- a bug ticket touching
        # the CLI dispatch table unannounced is real scope creep, not the
        # structural-necessity case T-0446 fixes.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/frob/tickets/**",), kind=TicketKind.BUG)
        diff = Diff(base="x", hunks=(Hunk(file="src/frob/__main__.py", span=(1, 1)),))
        assert any(v.rule == "SCOPE001" for v in scope_gate(diff, ticket, snap))

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

    def test_scope001_merge_commit_with_no_ticket_ref_falls_back_to_parent(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0527: a plain `git merge` conflict-resolution commit carries NO
        # ticket reference of its own in its subject (the default merge
        # message), yet `git blame` attributes the reconciled hunk to that
        # merge commit rather than either parent. The exemption must not
        # treat this as an unattributed touch -- it should fall back to the
        # merge commit's PARENTS' subjects to recover the ticket reference
        # that actually attributes the reconciled content.
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
        subprocess.run(["git", "checkout", "-q", "main"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "conflict-source"],
            cwd=tmp_path,
            check=True,
        )
        _write(tmp_path, "src/a/mod.py", "def f():\n    return 2\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat(a): conflicting change (T-0001)"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(["git", "checkout", "-q", "work"], cwd=tmp_path, check=True)
        merge = subprocess.run(
            ["git", "merge", "-q", "--no-ff", "conflict-source"],
            cwd=tmp_path,
            check=False,
        )
        assert merge.returncode != 0  # a real conflict, not a trivial merge
        _write(tmp_path, "src/a/mod.py", "def f():\n    return 3\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Merge branch 'conflict-source'"],
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

        violations = scope_gate(diff, ticket_b, snap, root=tmp_path, queue=queue)
        assert not any(v.file == "src/a/mod.py" for v in violations)

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

    # frob:ticket T-0584
    def test_pre001_passes_with_partial_sweep_matching_digest(
        self, tmp_path: Path
    ) -> None:
        """A partial sweep (budget exceeded mid-scan, T-0584) whose digest
        still matches the ticket's current scope is provisionally clean --
        PRE001 must not re-demand the very sweep that timed out."""
        from typani.option import Some

        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/**",))

        from frob.gates import _scope_digest  # noqa: PLC0415

        digest = _scope_digest(ticket, snap)
        sweep = PreworkSweep(
            date=date(2026, 1, 1),
            dup_findings=0,
            xref_hits=(),
            digest=digest,
            partial=True,
            pending_patterns=("src/**",),
        )
        violations = prework_gate(ticket, snap, Some(sweep))
        assert violations == ()

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

    # frob:ticket T-0584
    def test_prework_sweep_default_partial_is_false_and_treated_as_final(
        self, tmp_path: Path
    ) -> None:
        """`PreworkSweep` constructed WITHOUT `partial=` (T-0584's field
        default) must behave as a COMPLETE sweep, not a partial one: `PRE001`
        must accept it outright with no "resume with `frob ticket sweep`"
        debug path taken, and it must round-trip through record/load with
        `partial` still False and no pending patterns. If the field's
        default ever flipped to `True`, a freshly-recorded "complete" sweep
        would misreport itself as partial forever."""
        from typani.option import Some

        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/**",))

        from frob.gates import _scope_digest  # noqa: PLC0415
        from frob.gates._prework import load_prework  # noqa: PLC0415

        digest = _scope_digest(ticket, snap)
        sweep = PreworkSweep(
            date=date(2026, 1, 1), dup_findings=0, xref_hits=(), digest=digest
        )
        assert sweep.partial is False
        assert sweep.pending_patterns == ()

        result = record_prework(tmp_path, ticket.id, sweep)
        assert result.is_ok
        loaded = load_prework(tmp_path, ticket.id)
        assert loaded is not None
        assert loaded.partial is False

        violations = prework_gate(ticket, snap, Some(sweep))
        assert violations == ()


# frob:ticket T-0998
class TestScope002ClosureGate:
    """`frob.gates._scope002_violations` (SCOPE002, T-0998): scope-
    declaration-time doc-edge + code-edge + private-helper closure
    validation over a ticket's declared scope, WARN-only turn-on."""

    def test_warns_on_unscoped_doc_target(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_scope002_violations
        from frob.gates import _scope002_violations  # noqa: PLC0415

        _write(
            tmp_path,
            "src/a.py",
            "# frob:doc docs/x.md#foo\ndef foo() -> None:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/a.py",))
        violations = _scope002_violations(ticket, snap, tmp_path)
        assert any(v.rule == "SCOPE002" for v in violations)
        found = [v for v in violations if v.rule == "SCOPE002"][0]
        assert found.severity == Severity.WARN
        assert "docs/x.md" in found.message

    def test_warns_on_unscoped_private_helper(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_scope002_violations
        from frob.gates import _scope002_violations  # noqa: PLC0415

        _write(
            tmp_path,
            "src/pkg/a.py",
            "def public_fn() -> None:\n    _helper()\n",
        )
        _write(tmp_path, "src/pkg/b.py", "def _helper() -> None:\n    pass\n")
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/pkg/a.py",))
        violations = _scope002_violations(ticket, snap, tmp_path)
        assert any(
            v.rule == "SCOPE002" and "src/pkg/b.py" in v.message for v in violations
        )

    def test_warns_on_unscoped_test_target(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_scope002_violations
        from frob.gates import _scope002_violations  # noqa: PLC0415

        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "# frob:tests src/a.py::foo\ndef test_foo() -> None:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/a.py",))
        violations = _scope002_violations(ticket, snap, tmp_path)
        assert any(
            v.rule == "SCOPE002" and "tests/test_a.py" in v.message for v in violations
        )

    def test_silent_on_closed_scope(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_scope002_violations
        from frob.gates import _scope002_violations  # noqa: PLC0415

        _write(
            tmp_path,
            "src/a.py",
            "# frob:doc docs/x.md#foo\ndef foo() -> None:\n    pass\n",
        )
        _write(tmp_path, "docs/x.md", "# X\n<!-- frob:describes src/a.py::foo -->\n")
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/a.py", "docs/x.md"))
        violations = _scope002_violations(ticket, snap, tmp_path)
        assert violations == ()


# frob:ticket T-0584
class TestPreworkSweepBounds:
    """T-0240: the sweep's xref half used to call `xref(symbol, root)` --
    ALWAYS the full repo root, ignoring the per-pattern scan path it had
    already computed -- and derived its search term from a raw glob-syntax
    stem (`Path(pattern).stem`), producing nonsense terms like `"**"`. Both
    made `frob ticket start`/`sweep` unbounded and slow on real scopes.
    These pin the fix: excludes/skip-dirs are honored (reusing
    `frob.excludes`, not a second copy of the rule) and every xref hit is a
    real, graph-known symbol name."""

    def test_sweep_ticket_honors_graph_excludes(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_prework.py::sweep_ticket
        (tmp_path / "frob.toml").write_text('[graph]\nexclude = ["vendor/**"]\n')
        _write(tmp_path, "vendor/big.py", "def vendored_widget():\n    pass\n")
        _write(tmp_path, "src/keep.py", "def kept_widget():\n    pass\n")
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("vendor/**", "src/**"))

        from frob.gates._prework import sweep_ticket

        result = sweep_ticket(tmp_path, ticket)
        assert result.is_ok
        sweep = result.danger_ok
        assert "vendored_widget" not in sweep.xref_hits
        assert "kept_widget" in sweep.xref_hits

    def test_sweep_ticket_skips_builtin_skip_dirs(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_prework.py::sweep_ticket
        _write(tmp_path, ".venv/pkg/mod.py", "def hidden_widget():\n    pass\n")
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=(".venv/pkg/**",))

        from frob.gates._prework import sweep_ticket

        result = sweep_ticket(tmp_path, ticket)
        assert result.is_ok
        assert result.danger_ok.xref_hits == ()

    def test_sweep_ticket_xref_hits_are_real_symbols(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_prework.py::sweep_ticket
        _write(tmp_path, "src/mod.py", "def real_widget():\n    pass\n")
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/**",))

        from frob.gates._prework import sweep_ticket

        result = sweep_ticket(tmp_path, ticket)
        assert result.is_ok
        sweep = result.danger_ok
        assert sweep.xref_hits == ("real_widget",)
        assert "**" not in sweep.xref_hits

    # frob:ticket T-0584
    def test_sweep_ticket_partial_on_budget_exceeded(self, tmp_path: Path) -> None:
        """A `budget_seconds=0` deadline is exceeded before the first scope
        pattern is scanned -- the sweep must record `partial=True` with
        every pattern still pending, rather than blocking to completion or
        erroring out."""
        # frob:tests src/frob/gates/_prework.py::sweep_ticket
        _write(tmp_path, "src/a/mod.py", "def a_widget():\n    pass\n")
        _write(tmp_path, "src/b/mod.py", "def b_widget():\n    pass\n")
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/a/**", "src/b/**"))

        from frob.gates._prework import sweep_ticket

        result = sweep_ticket(tmp_path, ticket, budget_seconds=0.0)
        assert result.is_ok
        sweep = result.danger_ok
        assert sweep.partial is True
        assert set(sweep.pending_patterns) == {"src/a/**", "src/b/**"}
        assert sweep.xref_hits == ()

    # frob:ticket T-0584
    def test_sweep_ticket_resumes_pending_patterns(self, tmp_path: Path) -> None:
        """A follow-up call with a real budget picks up exactly the patterns
        the prior partial sweep left pending, and does not re-derive hits
        for patterns it already recorded."""
        # frob:tests src/frob/gates/_prework.py::sweep_ticket
        _write(tmp_path, "src/a/mod.py", "def a_widget():\n    pass\n")
        _write(tmp_path, "src/b/mod.py", "def b_widget():\n    pass\n")
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/a/**", "src/b/**"))

        from frob.gates._prework import sweep_ticket

        first = sweep_ticket(tmp_path, ticket, budget_seconds=0.0)
        assert first.is_ok
        assert first.danger_ok.partial is True

        resumed = sweep_ticket(tmp_path, ticket, budget_seconds=None)
        assert resumed.is_ok
        sweep = resumed.danger_ok
        assert sweep.partial is False
        assert sweep.pending_patterns == ()
        assert set(sweep.xref_hits) == {"a_widget", "b_widget"}


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


# frob:ticket T-0543
class TestInvariantGate:
    def test_inv001_no_evidence(self, tmp_path: Path) -> None:
        from frob.gates.invariants import Invariant

        snap = _snapshot(tmp_path)
        inv = Invariant(
            id="INV-001", statement="x", criticality=_Criticality.HIGH, evidence=()
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
            criticality=_Criticality.HIGH,
            evidence=("tests/test_x.py::test_y",),
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = invariant_gate((inv,), snap, tests)
        assert any(v.rule == "INV001" for v in violations)

    # frob:tests src/frob/gates/__init__.py::invariant_gate
    # frob:ticket T-0543
    def test_inv001_passes_with_collected_evidence(self, tmp_path: Path) -> None:
        """The evidence test lives in the SAME FILE as the invariant's
        anchor (B12's same-file binding route) -- a genuine binding, not
        merely a collected node id."""
        source = (
            "def f(x):\n"
            "    # frob:invariant INV-001\n"
            "    return x\n"
            "\n"
            "def test_y():\n"
            "    assert f(1) == 1\n"
        )
        _write(tmp_path, "tests/test_x.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates.invariants import Invariant

        node = "tests/test_x.py::test_y"
        inv = Invariant(
            id="INV-001", statement="x", criticality=_Criticality.HIGH, evidence=(node,)
        )
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = invariant_gate((inv,), snap, tests)
        assert violations == ()

    # frob:tests src/frob/gates/__init__.py::_invariant_evidence_proves_anchor
    # frob:ticket T-0543
    def test_inv001_collected_but_unbound_evidence_warns_inv005(
        self, tmp_path: Path
    ) -> None:
        """B12 counterexample: a collected test node id that has NO edge
        to, and lives in a different file than, the invariant's anchor
        used to clear INV001 by mere existence (`def test_y(): pass`
        anywhere in the repo). It still passes INV001 (a legacy-adoption
        mass-break across this repo's own invariants is out of budget --
        see `invariant_gate`'s docstring) but now WARNs via the new INV005
        instead of silently proving nothing."""
        source = "def f(x):\n    # frob:invariant INV-001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        _write(tmp_path, "tests/test_unrelated.py", "def test_y():\n    pass\n")
        snap = _snapshot(tmp_path)
        from frob.gates.invariants import Invariant

        node = "tests/test_unrelated.py::test_y"
        inv = Invariant(
            id="INV-001", statement="x", criticality=_Criticality.HIGH, evidence=(node,)
        )
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = invariant_gate((inv,), snap, tests)
        assert not any(v.rule == "INV001" for v in violations)
        assert any(v.rule == "INV005" for v in violations)

    # frob:tests src/frob/gates/__init__.py::_evidence_binds_to_symrefs
    # frob:ticket T-0543
    def test_inv001_passes_via_explicit_tests_edge_to_anchor(
        self, tmp_path: Path
    ) -> None:
        """B12: an evidence test bound to the anchor via an explicit
        `frob:tests` edge (not merely same-file) also satisfies INV001."""
        source = "def f(x):\n    # frob:invariant INV-001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        _write(
            tmp_path,
            "tests/test_a.py",
            "# frob:tests src/a.py::f\ndef test_f():\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        from frob.gates.invariants import Invariant

        node = "tests/test_a.py::test_f"
        inv = Invariant(
            id="INV-001", statement="x", criticality=_Criticality.HIGH, evidence=(node,)
        )
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = invariant_gate((inv,), snap, tests)
        assert violations == ()

    def test_inv002_no_anchor(self, tmp_path: Path) -> None:
        from frob.gates.invariants import Invariant

        snap = _snapshot(tmp_path)
        node = "tests/test_x.py::test_y"
        inv = Invariant(
            id="INV-001", statement="x", criticality=_Criticality.HIGH, evidence=(node,)
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
            criticality=_Criticality.HIGH,
            evidence=("POL-thing",),
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = invariant_gate((inv,), snap, tests, frozenset({"POL-thing"}))
        assert not any(v.rule == "INV001" for v in violations)


class TestInv003Gate:
    # frob:tests src/frob/gates/__init__.py::inv003_gate
    def test_exclusivity_claim_without_marker_warns(self, tmp_path: Path) -> None:
        # T-0509: INV003 is scoped to INV003_SPEC_DIRS (docs/modules,
        # docs/strata), not all of docs/**.md -- fixture must live there.
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\nThe only writer of this file is the daemon.\n",
        )
        violations = inv003_gate(tmp_path, ())
        assert len(violations) == 1
        assert violations[0].rule == "INV003"
        assert violations[0].severity == Severity.WARN
        assert violations[0].file == "docs/modules/x.md"

    def test_exclusivity_claim_with_bound_known_invariant_is_silent(
        self, tmp_path: Path
    ) -> None:
        from frob.gates.invariants import Invariant

        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\n<!-- frob:invariant INV-001 -->\n"
            "The only writer of this file is the daemon.\n",
        )
        inv = Invariant(
            id="INV-001", statement="x", criticality=_Criticality.HIGH, evidence=()
        )
        violations = inv003_gate(tmp_path, (inv,))
        assert violations == ()

    def test_marker_naming_unknown_invariant_still_warns(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\n<!-- frob:invariant INV-999 -->\n"
            "The only writer of this file is the daemon.\n",
        )
        violations = inv003_gate(tmp_path, ())
        assert len(violations) == 1

    def test_no_exclusivity_language_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "docs/modules/x.md", "# X\n\nThe daemon writes this file.\n")
        violations = inv003_gate(tmp_path, ())
        assert violations == ()

    def test_missing_docs_dir_is_silent(self, tmp_path: Path) -> None:
        assert inv003_gate(tmp_path, ()) == ()

    def test_claim_without_verb_in_sentence_is_silent(self, tmp_path: Path) -> None:
        """T-0509: a bare heading/fragment containing the trigger word but
        no claim-verb in the same sentence is not a claim (e.g. a
        '## Schema' style heading, or a dangling noun phrase)."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\n## Only child nodes\n\nSee below.\n",
        )
        assert inv003_gate(tmp_path, ()) == ()

    def test_claim_in_code_fence_is_silent(self, tmp_path: Path) -> None:
        """T-0509: `_strip_markdown_noise` drops fenced code before
        scanning -- a code sample using "only" in a comment is not prose."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\n```python\n# only the daemon is allowed to write here\n```\n",
        )
        assert inv003_gate(tmp_path, ()) == ()

    def test_outside_spec_dirs_is_silent(self, tmp_path: Path) -> None:
        """T-0509: INV003 is scoped to `INV003_SPEC_DIRS`
        (docs/modules, docs/strata) -- a claim in another docs/ subtree
        (e.g. docs/design) is out of scope for this gate."""
        _write(
            tmp_path,
            "docs/design/x.md",
            "# X\n\nThe only writer of this file is the daemon.\n",
        )
        assert inv003_gate(tmp_path, ()) == ()

    def test_markdown_waive_marker_with_reason_is_silent(self, tmp_path: Path) -> None:
        """T-0509: a `<!-- frob:waive INV003 reason="..." -->` marker
        dispositions a genuine-but-unprovable exclusivity claim without
        requiring a fake bound invariant."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            '# X\n\n<!-- frob:waive INV003 reason="design intent, not enforced" -->\n'
            "The only writer of this file is the daemon.\n",
        )
        assert inv003_gate(tmp_path, ()) == ()

    def test_markdown_waive_marker_without_reason_still_warns(
        self, tmp_path: Path
    ) -> None:
        """T-0509: a waiver marker with no `reason=` is not honored --
        same honesty requirement as the code-side `frob:waive` WAIVE001."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\n<!-- frob:waive INV003 -->\n"
            "The only writer of this file is the daemon.\n",
        )
        violations = inv003_gate(tmp_path, ())
        assert len(violations) == 1

    def test_illustrative_example_reason_does_not_self_waive(
        self, tmp_path: Path
    ) -> None:
        """T-0522: gates.md's OWN INV003 documentation necessarily spells
        out the marker syntax by illustrative example, using a literal
        `reason="..."` placeholder -- this must not be mistaken for a
        real, reasoned waiver of that same file's genuine findings. Uses
        the exact example text from docs/modules/gates.md."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\nMarkdown-side `frob:waive` support: "
            '`<!-- frob:waive INV003 reason="..." -->` anywhere in a file '
            "dispositions that file's INV003 findings.\n\n"
            "The only writer of this file is the daemon.\n",
        )
        violations = inv003_gate(tmp_path, ())
        assert len(violations) == 1


class TestInv004Gate:
    # frob:tests src/frob/gates/__init__.py::inv004_gate
    def test_section_with_normative_language_and_no_invariant_is_advisory(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\nThe daemon must never write to this file directly.\n",
        )
        violations = inv004_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "INV004"
        assert violations[0].severity == Severity.WARN
        assert violations[0].file == "docs/modules/x.md"

    def test_section_with_any_invariant_marker_is_silent(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# X\n\n<!-- frob:invariant INV-999 -->\n"
            "The daemon must never write to this file directly.\n",
        )
        # A marker naming an UNKNOWN invariant still counts here (T-0452's
        # signal is "anchors zero invariants at all", the coarser inverse
        # of INV003's "anchors a REAL one").
        violations = inv004_gate(tmp_path)
        assert violations == ()

    def test_section_with_no_normative_language_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "docs/modules/x.md", "# X\n\nThe daemon writes this file.\n")
        assert inv004_gate(tmp_path) == ()

    def test_two_sections_only_flags_the_underspecified_one(
        self, tmp_path: Path
    ) -> None:
        """T-0515: file-granularity -- two claim-bearing, unbound sections
        in the same file produce ONE advisory, not one per section (the
        T-0452 per-section scan was the source of most of the 573-warning
        pool this ticket burned down)."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# A\n\nThe daemon must never write to this file directly.\n"
            "# B\n\nThis section always holds too.\n",
        )
        violations = inv004_gate(tmp_path)
        assert len(violations) == 1
        assert "'# A" in violations[0].message

    def test_any_bound_invariant_anywhere_in_file_silences_every_section(
        self, tmp_path: Path
    ) -> None:
        """T-0515: file-granularity means a marker in section B silences
        an unbound claim in section A too -- the file as a whole is no
        longer "anchors zero invariants"."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            "# A\n\nThe daemon must never write to this file directly.\n"
            "# B\n\n<!-- frob:invariant INV-001 -->\n"
            "This section always holds too.\n",
        )
        assert inv004_gate(tmp_path) == ()

    def test_missing_docs_dir_is_silent(self, tmp_path: Path) -> None:
        assert inv004_gate(tmp_path) == ()

    def test_outside_spec_dirs_is_silent(self, tmp_path: Path) -> None:
        """T-0515: INV004 is now scoped to `INV003_SPEC_DIRS`, matching
        INV003 -- a narrative doc outside docs/modules and docs/strata
        making a passing normative remark is not the failure mode."""
        _write(
            tmp_path,
            "docs/design/notes.md",
            "# X\n\nThe daemon must never write to this file directly.\n",
        )
        assert inv004_gate(tmp_path) == ()

    def test_markdown_waive_marker_with_reason_is_silent(self, tmp_path: Path) -> None:
        """T-0509/T-0515: a `<!-- frob:waive INV004 reason="..." -->`
        marker anywhere in the file dispositions it without a fake bound
        invariant."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            '# X\n\n<!-- frob:waive INV004 reason="design note, not a gate" -->\n'
            "The daemon must never write to this file directly.\n",
        )
        assert inv004_gate(tmp_path) == ()

    def test_markdown_waive_marker_without_reason_still_warns(
        self, tmp_path: Path
    ) -> None:
        """T-0515: an empty `reason=""` does not count as a waiver, same
        honesty requirement as code-side WAIVE001."""
        _write(
            tmp_path,
            "docs/modules/x.md",
            '# X\n\n<!-- frob:waive INV004 reason="" -->\n'
            "The daemon must never write to this file directly.\n",
        )
        violations = inv004_gate(tmp_path)
        assert len(violations) == 1

    def test_claim_without_verb_in_sentence_is_silent(self, tmp_path: Path) -> None:
        """T-0509: a heading using trigger vocabulary with no claim-verb
        in the same sentence is not a claim."""
        _write(
            tmp_path, "docs/modules/x.md", "# X\n\n## Always current\n\nSee below.\n"
        )
        assert inv004_gate(tmp_path) == ()


# frob:ticket T-0408
class TestInv006Gate:
    """T-0408: INV006 extends the same claim-vocabulary scan INV003 runs
    over docs (`INV003_SPEC_DIRS`) to SOURCE trees (`INV006_SRC_DIRS`) --
    the coverage-completeness gap the ticket named (a huge system's own
    docstring/comment guarantee claims were entirely outside either
    doc-only gate's reach)."""

    # frob:tests src/frob/gates/__init__.py::inv006_gate
    # frob:ticket T-0408
    def test_exclusivity_claim_in_source_without_anchor_warns(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            "src/pkg.py",
            '"""Module docstring."""\n\n'
            "def only_writer() -> None:\n"
            '    """The only writer of this file is the daemon."""\n',
        )
        snapshot = _snapshot(tmp_path)
        violations = inv006_gate(tmp_path, snapshot)
        assert len(violations) == 1
        assert violations[0].rule == "INV006"
        assert violations[0].severity == Severity.WARN
        assert violations[0].file == "src/pkg.py"

    # frob:ticket T-0408
    def test_exclusivity_claim_with_bound_invariant_anchor_is_silent(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            "src/pkg.py",
            '"""Module docstring."""\n\n'
            "# frob:invariant INV-001\n"
            "def only_writer() -> None:\n"
            '    """The only writer of this file is the daemon."""\n',
        )
        snapshot = _snapshot(tmp_path)
        violations = inv006_gate(tmp_path, snapshot)
        assert violations == ()

    # frob:ticket T-0408
    def test_waived_with_reason_is_silent(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/pkg.py",
            '"""Module docstring."""\n\n'
            '# frob:waive INV006 reason="genuine design intent, not enforced"\n'
            "def only_writer() -> None:\n"
            '    """The only writer of this file is the daemon."""\n',
        )
        snapshot = _snapshot(tmp_path)
        violations = inv006_gate(tmp_path, snapshot)
        assert violations == ()

    # frob:ticket T-0408
    def test_no_exclusivity_language_is_silent(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/pkg.py",
            '"""Module docstring."""\n\ndef writer() -> None:\n'
            '    """The daemon writes this file."""\n',
        )
        snapshot = _snapshot(tmp_path)
        assert inv006_gate(tmp_path, snapshot) == ()

    # frob:ticket T-0408
    def test_outside_src_dirs_is_silent(self, tmp_path: Path) -> None:
        """T-0408: INV006 is scoped to `INV006_SRC_DIRS`
        (src, strata-core/src, frob-core/src) -- a claim in tests/ or
        docs/ is out of scope for this source-side gate."""
        _write(
            tmp_path,
            "tests/test_x.py",
            '"""Module docstring."""\n\ndef only_writer() -> None:\n'
            '    """The only writer of this file is the daemon."""\n',
        )
        snapshot = _snapshot(tmp_path)
        assert inv006_gate(tmp_path, snapshot) == ()

    # frob:ticket T-0408
    def test_missing_src_dir_is_silent(self, tmp_path: Path) -> None:
        snapshot = _snapshot(tmp_path)
        assert inv006_gate(tmp_path, snapshot) == ()

    # frob:ticket T-0594
    def test_ratchet_fresh_finding_errors_when_rule_enabled(
        self, tmp_path: Path
    ) -> None:
        """T-0594: `[gates.ratchet] rules = ["INV006"]` with no baseline
        entry for this file -- `resolve_ratchet_severity` resolves a NEW
        finding to error, not the gate's static WARN."""
        _write(
            tmp_path,
            "src/pkg.py",
            '"""Module docstring."""\n\n'
            "def only_writer() -> None:\n"
            '    """The only writer of this file is the daemon."""\n',
        )
        _write(tmp_path, "frob.toml", '[gates.ratchet]\nrules = ["INV006"]\n')
        snapshot = _snapshot(tmp_path)
        violations = inv006_gate(tmp_path, snapshot)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR

    # frob:ticket T-0594
    def test_ratchet_baselined_finding_stays_warn(self, tmp_path: Path) -> None:
        """T-0594: the same finding, but its key (`src/pkg.py`) is already
        baselined in `frob-ratchet.lock.json` -- `resolve_ratchet_severity`
        resolves it to warn, matching the pre-ratchet gate posture."""
        _write(
            tmp_path,
            "src/pkg.py",
            '"""Module docstring."""\n\n'
            "def only_writer() -> None:\n"
            '    """The only writer of this file is the daemon."""\n',
        )
        _write(tmp_path, "frob.toml", '[gates.ratchet]\nrules = ["INV006"]\n')
        snapshot_ratchet(tmp_path, "INV006", ["src/pkg.py"])
        snapshot = _snapshot(tmp_path)
        violations = inv006_gate(tmp_path, snapshot)
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARN

    # frob:ticket T-0594
    def test_ratchet_rule_not_enabled_stays_static_warn(self, tmp_path: Path) -> None:
        """T-0594: no `[gates.ratchet]` opt-in at all -- INV006 keeps
        reporting its unconditional static WARN, unaffected by ratchet
        wiring existing in the codebase (opt-in, not opt-out)."""
        _write(
            tmp_path,
            "src/pkg.py",
            '"""Module docstring."""\n\n'
            "def only_writer() -> None:\n"
            '    """The only writer of this file is the daemon."""\n',
        )
        snapshot = _snapshot(tmp_path)
        violations = inv006_gate(tmp_path, snapshot)
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARN

    # frob:ticket T-0594
    def test_this_repos_frob_toml_and_ratchet_lock_calibrate(self) -> None:
        """T-0594 calibration: this repo's OWN committed `frob.toml`
        (`[gates.ratchet] rules = ["INV006"]`) and `frob-ratchet.lock.json`
        (the 29 findings baselined when ratcheting was enabled) resolve
        every currently-baselined INV006 finding to WARN when run against
        the real tree -- i.e. wiring this in did not turn `frob check`
        red on its own pre-existing findings."""
        root = Path(__file__).resolve().parent.parent
        assert "INV006" in ratchet_enabled_rules(root)
        lock = load_ratchet_lock(root)
        pool = lock.pool_for("INV006")
        assert pool is not None
        assert len(pool.entries) > 0
        for entry in pool.entries:
            assert resolve_ratchet_severity("INV006", entry.key, lock) == "warn"
        assert resolve_ratchet_severity("INV006", "src/pkg/not_baselined.py", lock) == (
            "error"
        )


class TestPlace001Gate:
    """T-0504: PLACE001 replaces the dropped T-0470 "distance from the
    class's own span start" prototype (proven noisy against this repo's
    own per-field pydantic idiom) with a materially different signal --
    a nearby real symbol the directive plausibly missed via `following`,
    not raw distance. See `_place001_missed_symbol`'s docstring."""

    # frob:tests src/frob/gates/__init__.py::coverage_gate
    def test_missed_following_binding_fires(self, tmp_path: Path) -> None:
        """A directive separated from its intended `def` by more blank
        lines than `_find_following_symbol`'s window (3), with NOTHING
        but blank lines in between, is a genuine placement miss."""
        _write(
            tmp_path,
            "src/a.py",
            "class Foo:\n"
            "    # frob:ticket T-0001\n"
            "\n"
            "\n"
            "\n"
            "\n"
            "    def bar(self):\n"
            "        return 1\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        v = _first_rule(violations, "PLACE001")
        assert v is not None
        assert v.severity == Severity.WARN
        assert "Foo" in v.message
        assert "bar" in v.message

    def test_per_field_pydantic_idiom_is_silent(self, tmp_path: Path) -> None:
        """T-0470's counterexample: a directive above one field deep in a
        class, with more real field-assignment code (not blank lines)
        before the next real method, must NOT fire -- this is exactly
        the shape the dropped raw-distance prototype false-positived on
        (`AppConfig`'s `frob:waive SCOPE001` 150+ lines past the class
        line)."""
        _write(
            tmp_path,
            "src/a.py",
            "class AppConfig:\n"
            "    name: str\n"
            '    # frob:waive SCOPE001 reason="test"\n'
            "    value: int = 0\n"
            "    another: str = ''\n"
            "    more: int = 1\n"
            "    yet_more: bool = False\n"
            "    def other(self):\n"
            "        return self.value\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert _first_rule(violations, "PLACE001") is None

    def test_directive_directly_above_def_is_silent(self, tmp_path: Path) -> None:
        """A directive that resolves via `following` in the ordinary way
        (immediately above its `def`) never class-falls-back at all, so
        PLACE001 has nothing to say about it."""
        _write(
            tmp_path,
            "src/a.py",
            "class Foo:\n    # frob:ticket T-0001\n    def bar(self):\n        return 1\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert _first_rule(violations, "PLACE001") is None

    def test_no_nearby_symbol_at_all_is_silent(self, tmp_path: Path) -> None:
        """A class-fallback directive with no real symbol within the
        lookahead window at all has nothing to flag as "missed"."""
        _write(
            tmp_path,
            "src/a.py",
            "class Foo:\n    # frob:ticket T-0001\n    x = 1\n",
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert _first_rule(violations, "PLACE001") is None


class TestExcludeHazardGate:
    # frob:tests src/frob/gates/_exclude_hazard.py::exclude_hazard_gate
    def test_entry_shadowing_tracked_dir_fires(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", "x = 1\n")
        _git_init(tmp_path)
        (tmp_path / ".git" / "info" / "exclude").write_text("src/pkg/\n")
        violations = exclude_hazard_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "EXCL001"
        assert violations[0].severity == Severity.ERROR
        assert "src/pkg" in violations[0].message

    def test_entry_matching_no_tracked_path_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", "x = 1\n")
        _git_init(tmp_path)
        (tmp_path / ".git" / "info" / "exclude").write_text("*.pyc\nbuild/\n")
        assert exclude_hazard_gate(tmp_path) == ()

    def test_comment_and_negated_lines_are_ignored(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", "x = 1\n")
        _git_init(tmp_path)
        (tmp_path / ".git" / "info" / "exclude").write_text("# src/pkg/\n!src/pkg/\n")
        assert exclude_hazard_gate(tmp_path) == ()

    def test_exact_tracked_file_entry_fires(self, tmp_path: Path) -> None:
        _write(tmp_path, "README.md", "hi\n")
        _git_init(tmp_path)
        (tmp_path / ".git" / "info" / "exclude").write_text("README.md\n")
        violations = exclude_hazard_gate(tmp_path)
        assert len(violations) == 1

    def test_empty_exclude_file_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", "x = 1\n")
        _git_init(tmp_path)
        assert exclude_hazard_gate(tmp_path) == ()

    def test_non_git_root_is_silent(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/pkg/a.py", "x = 1\n")
        assert exclude_hazard_gate(tmp_path) == ()


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

    def test_unreadable_file_is_malformed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An `OSError` reading the invariant file is `Err(Malformed)`, not
        a crash -- proves `_frontmatter_dict`'s read-failure branch."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text(
            "---\nid: INV-001\nstatement: x\ncriticality: high\nevidence: []\n---\n"
        )
        real_read_text = Path.read_text

        def _boom(self: Path, *a, **kw):  # noqa: ANN001, ANN002, ANN003
            if self.name == "INV-001.md":
                raise OSError("permission denied")
            return real_read_text(self, *a, **kw)

        monkeypatch.setattr(Path, "read_text", _boom)
        result = load_invariants(tmp_path)
        assert result.is_err
        assert result.danger_err == InvariantError.Malformed

    # frob:waive DUP001 reason="parallel test methods within test_gates.py (6 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_no_frontmatter_block_is_malformed(self, tmp_path: Path) -> None:
        """A file with no `---`-delimited frontmatter block at all is
        `Err(Malformed)` -- proves the no-match regex branch."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text("just prose, no yaml\n")
        result = load_invariants(tmp_path)
        assert result.is_err
        assert result.danger_err == InvariantError.Malformed

    # frob:waive DUP001 reason="parallel test methods within test_gates.py (6 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_bad_yaml_frontmatter_is_malformed(self, tmp_path: Path) -> None:
        """Unparseable YAML inside the frontmatter block is `Err(Malformed)`
        -- proves the `yaml.YAMLError` branch."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text(
            "---\nid: [unterminated\n---\nprose\n"
        )
        result = load_invariants(tmp_path)
        assert result.is_err
        assert result.danger_err == InvariantError.Malformed

    # frob:waive DUP001 reason="parallel test methods within test_gates.py (6 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_non_mapping_frontmatter_is_malformed(self, tmp_path: Path) -> None:
        """A frontmatter block that parses to a YAML scalar/list, not a
        mapping, is `Err(Malformed)` -- proves the not-a-dict branch."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text(
            "---\n- one\n- two\n---\nprose\n"
        )
        result = load_invariants(tmp_path)
        assert result.is_err
        assert result.danger_err == InvariantError.Malformed

    # frob:waive DUP001 reason="parallel test methods within test_gates.py (6 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_empty_statement_is_malformed(self, tmp_path: Path) -> None:
        """An empty `statement` field fails `_validate_invariant_shape`'s
        non-empty check."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text(
            "---\nid: INV-001\nstatement: ''\ncriticality: high\nevidence: []\n---\n"
        )
        result = load_invariants(tmp_path)
        assert result.is_err
        assert result.danger_err == InvariantError.Malformed

    # frob:waive DUP001 reason="parallel test methods within test_gates.py (6 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_evidence_not_a_list_is_malformed(self, tmp_path: Path) -> None:
        """A non-list `evidence` field is `Err(Malformed)` -- proves
        `_build_invariant`'s evidence-shape branch."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text(
            "---\nid: INV-001\nstatement: x\ncriticality: high\nevidence: notalist\n---\n"
        )
        result = load_invariants(tmp_path)
        assert result.is_err
        assert result.danger_err == InvariantError.Malformed

    # frob:waive DUP001 reason="parallel test methods within test_gates.py (6 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_bad_criticality_is_malformed(self, tmp_path: Path) -> None:
        """A `criticality` value outside the `_Criticality` enum is
        `Err(Malformed)` -- proves the criticality-membership branch."""
        (tmp_path / "invariants").mkdir()
        (tmp_path / "invariants" / "INV-001.md").write_text(
            "---\nid: INV-001\nstatement: x\ncriticality: catastrophic\nevidence: []\n---\n"
        )
        result = load_invariants(tmp_path)
        assert result.is_err
        assert result.danger_err == InvariantError.Malformed


# frob:ticket T-0549
# frob:waive COV002 reason="T-0549 is closed and committed on this stacked, unmerged \
# branch; T-draft-f5d48e02 files the underlying gap (the T-0214/ T-0320 closed-ticket \
# grace window only checks the exact marker LINE, which does not fall inside this \
# diff's narrow unified=0 hunks even though T-0549's own state transition plainly is \
# in the diff)"
class TestTestGate:
    # frob:waive DUP001 reason="parallel test methods within test_gates.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_test001_public_symbol_no_unit_edge(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::test_gate
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert any(v.rule == "TEST001" for v in violations)

    # frob:ticket T-0589
    # frob:tests tests/test_gates.py::TestTestGate.test_test001_zero_branch_coverage_flags_when_opted_in kind="unit"  # noqa: E501
    def test_test001_zero_branch_coverage_flags_when_opted_in(
        self, tmp_path: Path
    ) -> None:
        """T-0589: with `require_branch_coverage_for_test001=True`, a
        symbol that satisfies TEST001 by name/edge match ALONE, but whose
        `coverage.xml` shows the symbol's file was measured and the symbol
        itself never ran (0% branch coverage, the T-0557 dead-code signal),
        still fires TEST001 -- the def-myfunc-pass-shaped B1 gap TEST015
        only ever WARNed about, now blocking when this policy flag is on."""
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        node = "tests/test_a.py::test_helper"
        tests = CollectedTests(node_ids=frozenset({node}))
        coverage = Some(
            CoverageData(
                source_sha="x",
                symbol_branch={"src/frob/pkg/a.py::helper": 0.0},
                module_line={"src/frob/pkg/a.py": 90.0},
            )
        )
        cfg = TestPolicy(min_unit_cases=1, require_branch_coverage_for_test001=True)
        violations = run_test_gate(snap, (), coverage, tests, cfg)
        v = next(
            (v for v in violations if v.rule == "TEST001"),
            None,
        )
        assert v is not None, violations
        assert "0% measured branch coverage" in v.message

    # frob:ticket T-0589
    # frob:tests tests/test_gates.py::TestTestGate.test_test001_zero_branch_coverage_silent_when_flag_off kind="unit"  # noqa: E501
    def test_test001_zero_branch_coverage_silent_when_flag_off(
        self, tmp_path: Path
    ) -> None:
        """T-0589: the SAME zero-branch-coverage symbol as the sibling test
        above must NOT fire TEST001 when
        `require_branch_coverage_for_test001` is left at its default
        (`False`) -- the new check is opt-in, not a silent global
        behavior change, since promoting it repo-wide requires the
        compat survey this ticket's own body calls for."""
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        node = "tests/test_a.py::test_helper"
        tests = CollectedTests(node_ids=frozenset({node}))
        coverage = Some(
            CoverageData(
                source_sha="x",
                symbol_branch={"src/frob/pkg/a.py::helper": 0.0},
                module_line={"src/frob/pkg/a.py": 90.0},
            )
        )
        cfg = TestPolicy(min_unit_cases=1)
        assert cfg.require_branch_coverage_for_test001 is False
        violations = run_test_gate(snap, (), coverage, tests, cfg)
        assert not any(v.rule == "TEST001" for v in violations)

    # frob:ticket T-0589
    # frob:tests tests/test_gates.py::TestTestGate.test_test001_nonzero_branch_coverage_stays_silent_when_opted_in kind="unit"  # noqa: E501
    def test_test001_nonzero_branch_coverage_stays_silent_when_opted_in(
        self, tmp_path: Path
    ) -> None:
        """T-0589: a symbol WITH nonzero measured branch coverage must not
        fire the new check even with the flag on -- the promoted check
        targets zero coverage specifically (a test that never actually
        called the symbol), not any coverage below the TEST005 floor
        (that remains TEST005's own, separate, WARN-severity job)."""
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        node = "tests/test_a.py::test_helper"
        tests = CollectedTests(node_ids=frozenset({node}))
        coverage = Some(
            CoverageData(
                source_sha="x",
                symbol_branch={"src/frob/pkg/a.py::helper": 42.0},
                module_line={"src/frob/pkg/a.py": 90.0},
            )
        )
        cfg = TestPolicy(min_unit_cases=1, require_branch_coverage_for_test001=True)
        violations = run_test_gate(snap, (), coverage, tests, cfg)
        assert not any(v.rule == "TEST001" for v in violations)

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

    def test_test001_002_explicit_unit_edge_honored_regardless_of_test_name(
        self, tmp_path: Path
    ) -> None:
        """Regression for T-0336 (root-caused while adding
        `tests/test_graph.py::TestGeneratedSource` for T-0234's
        `is_generated_source`): `_test_edges` used to index unit TESTS
        edges by `edge.target` only, but the directive convention used
        throughout this codebase for "written directly above the source
        function, naming its covering test" (`docs/modules/testing.md`)
        binds `src` to the source symbol and `target` to the test id --
        `record.symref` (the source) can then only ever match `edge.src`,
        never `edge.target`, so a target-only index can structurally never
        find it. `zebra_helper` is deliberately tested by
        `test_alpha_omega_case`, a name that shares no token with
        `zebra_helper` -- `_inferred_unit_cases`' naming-convention fallback
        cannot match it, so TEST001/002 can only stay clean here via the
        explicit `frob:tests ... kind="unit"` edge being both found
        (`_unit_test_edges` indexing `edge.src`) and honored as real
        execution evidence (`_valid_edges` checking `edge.target` too)."""
        from typani.option import Nothing

        source = (
            '# frob:tests tests/test_a.py::test_alpha_omega_case kind="unit"\n'
            "def zebra_helper(x):\n    return x\n"
        )
        _write(tmp_path, "src/frob/pkg/a.py", source)
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_alpha_omega_case():\n    assert True\n",
        )
        snap = _snapshot(tmp_path)
        node = "tests/test_a.py::test_alpha_omega_case"
        tests = CollectedTests(node_ids=frozenset({node}))
        cfg = TestPolicy(min_unit_cases=1)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST001" not in rule_ids
        assert "TEST002" not in rule_ids

    # frob:waive DUP001 reason="parallel test methods within test_gates.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_test003_interface_without_integration(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert any(v.rule == "TEST003" for v in violations)

    # frob:tests \
    # tests/test_gates.py::TestTestGate.test_test003_exempts_strata_design_files \
    # kind="unit"
    def test_test003_exempts_strata_design_files(self, tmp_path: Path) -> None:
        """T-0225: `design/*.strata` must not be counted as a TEST003
        "interface package" -- it owns no pytest surface, so
        "0 integration tests" is a category error, not a real gap. The
        design-file obligation is TEST009's e2e floor instead."""
        from typani.option import Nothing

        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert not any(v.rule == "TEST003" and v.file == "design" for v in violations)

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

    def test_test003_satisfied_by_parametrized_case_with_dot_in_case_id(
        self, tmp_path: Path
    ) -> None:
        """T-0324 regression, TEST003 side of the same bug: a `frob:tests`
        directive bound to a parametrized test whose ONLY collected cases
        carry a dot inside their `[...]` case text (e.g. `[3.11]`, a float
        or version-string parametrize value) must still satisfy TEST003 --
        `_symref_to_nodeid` must not corrupt those in-bracket dots into
        `::` while converting the directive's own dotted qualname."""
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/thermo.py", "def helper(x):\n    return x\n")
        test_source = (
            '# frob:tests src/frob/pkg/thermo.py kind="integration"\n'
            "@pytest.mark.parametrize('x', [3.11, 4.22])\n"
            "def test_density(x):\n"
            "    assert True\n"
        )
        _write(tmp_path, "tests/test_thermo.py", test_source)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset(
                {
                    "tests/test_thermo.py::test_density[3.11]",
                    "tests/test_thermo.py::test_density[4.22]",
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

    # frob:ticket T-0549
    # frob:tests src/frob/gates/__init__.py::_case_count kind="unit"
    def test_test002_noop_parametrize_does_not_inflate_case_count(
        self, tmp_path: Path
    ) -> None:
        """T-0549 counterexample: a `frob:tests` directive bound to a
        `@pytest.mark.parametrize`-decorated test whose body asserts
        NOTHING must not clear `min_unit_cases` just because it collected
        many `[case-id]` variants. Before the fix, `_case_count` credited
        one case per collected variant unconditionally -- a 10-variant
        no-op test cleared `min_unit_cases=3` the same as a genuinely
        assertion-bearing one (B7 in docs/audits/gates-accounting.md).
        Post-fix, a no-op parametrized test is capped to 1 case (like the
        structural fallback), so TEST002 still fires."""
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        test_source = (
            "@pytest.mark.parametrize('x', [1, 2, 3])\n"
            "def test_helper(x):\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    helper(x)\n"  # calls helper, asserts nothing
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
        assert "TEST002" in rule_ids
        assert "TEST001" not in rule_ids  # an edge does exist, just thin

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

    # frob:ticket T-0549
    # frob:tests src/frob/gates/__init__.py::_case_count kind="unit"
    def test_case_count_root_none_skips_assertion_check(self) -> None:
        """T-0549: `root=None` (the default) is the pre-T-0549 behavior
        exactly -- `_case_count` never touches the filesystem and cannot
        discount a no-op test, matching every caller that has no root to
        check against (and this file's own node ids, which name no file
        that exists on disk)."""
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
        assert _case_count([edge], tests, root=None) == 3

    # frob:ticket T-0549
    # frob:tests src/frob/gates/__init__.py::_case_count kind="unit"
    def test_case_count_root_aware_caps_noop_parametrize(self, tmp_path: Path) -> None:
        """T-0549: with a real `root`, a parametrized test function with no
        assertion-shaped construct in its body is capped to 1 case no
        matter how many `[case-id]` variants collected; a real assertion
        in the same shape of function still counts every variant."""
        from frob.gates import _case_count
        from frob.graph import Edge, EdgeKind

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_noop(x):\n    helper(x)\n",
        )
        ids = frozenset(
            {
                "tests/test_a.py::test_noop[1]",
                "tests/test_a.py::test_noop[2]",
                "tests/test_a.py::test_noop[3]",
            }
        )
        tests = CollectedTests(node_ids=ids)
        edge = Edge(
            kind=EdgeKind.TESTS,
            src="tests/test_a.py::test_noop",
            target="src/frob/pkg/a.py::helper",
            origin="tests/test_a.py:1",
        )
        assert _case_count([edge], tests, root=tmp_path) == 1

        _write(
            tmp_path,
            "tests/test_b.py",
            "def test_real(x):\n    assert helper(x) == x\n",
        )
        ids_real = frozenset(
            {
                "tests/test_b.py::test_real[1]",
                "tests/test_b.py::test_real[2]",
                "tests/test_b.py::test_real[3]",
            }
        )
        tests_real = CollectedTests(node_ids=ids_real)
        edge_real = Edge(
            kind=EdgeKind.TESTS,
            src="tests/test_b.py::test_real",
            target="src/frob/pkg/a.py::helper",
            origin="tests/test_b.py:1",
        )
        assert _case_count([edge_real], tests_real, root=tmp_path) == 3

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

    def test_match_waiver_prefix_reach_gated_to_package_scoped_rules(self) -> None:
        """T-0470 counterexample: BEFORE this fix, `_match_waiver`'s
        directory-prefix branch ran for every symref-less violation
        regardless of rule -- any rule whose `violation.file` happened to
        be directory-shaped (no extension) inherited unbounded prefix
        reach it was never reviewed for. A non-package-scoped rule (i.e.
        not in `_PACKAGE_SCOPED_RULES`) with a directory-shaped `file`
        must now match ONLY a waiver whose own site is that exact
        file/directory string -- never a waiver nested somewhere under
        it via the prefix fallback."""
        # frob:tests src/frob/gates/__init__.py::_match_waiver
        from frob.gates import _match_waiver
        from frob.graph import Edge, EdgeKind

        directory_shaped_violation = Violation(
            rule="SYS002",  # not in _PACKAGE_SCOPED_RULES
            severity=Severity.WARN,
            file="design/boundary/foo",
            line=0,
            message="x",
        )
        nested_waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="design/boundary/foo/bar.py",
            target="SYS002",
            origin="design/boundary/foo/bar.py:1",
            attrs={"reason": "x"},
        )
        assert (
            _match_waiver(directory_shaped_violation, {"SYS002": [nested_waiver]})
            is None
        )

        # The package-scoped rules keep their prefix reach unchanged.
        package_violation = Violation(
            rule="TEST003",
            severity=Severity.ERROR,
            file="src/frob/pkg",
            line=0,
            message="x",
        )
        package_waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/frob/pkg/a.py",
            target="TEST003",
            origin="src/frob/pkg/a.py:1",
            attrs={"reason": "x"},
        )
        assert (
            _match_waiver(package_violation, {"TEST003": [package_waiver]})
            == package_waiver
        )

    def test_waive003_flags_waiver_reaching_multiple_packages(self) -> None:
        """T-0470: one `frob:waive TEST003` written in a file nested under
        `src/frob/pkg/sub` also reaches the ANCESTOR package `src/frob/pkg`
        via the same directory-prefix fallback -- both are real TEST003
        violations the same directive silently suppresses. WAIVE003 must
        flag that as over-broad."""
        # frob:tests src/frob/gates/__init__.py::_waive003_violations
        from frob.gates import _waive003_violations
        from frob.graph import Edge, EdgeKind, GraphSnapshot

        violations = (
            Violation(
                rule="TEST003",
                severity=Severity.ERROR,
                file="src/frob/pkg",
                line=0,
                message="x",
            ),
            Violation(
                rule="TEST003",
                severity=Severity.ERROR,
                file="src/frob/pkg/sub",
                line=0,
                message="x",
            ),
        )
        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/frob/pkg/sub/deep.py",
            target="TEST003",
            origin="src/frob/pkg/sub/deep.py:1",
            attrs={"reason": "x"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        found = _waive003_violations(violations, snap)
        assert len(found) == 1
        assert found[0].rule == "WAIVE003"
        assert "src/frob/pkg" in found[0].message
        assert "src/frob/pkg/sub" in found[0].message

        # A waiver that reaches only ONE package is not over-broad.
        single = _waive003_violations(violations[:1], snap)
        assert single == ()

    def test_waive004_fires_on_valid_rule_zero_findings(self) -> None:
        """T-0753: a waiver targeting a real, matchable rule id but whose
        site produces ZERO findings under that rule this run is the stale
        class WAIVE002 cannot see (the rule id is known; only the site is
        stale) -- WAIVE004 must flag it."""
        # frob:tests src/frob/gates/__init__.py::_waive004_violations
        from frob.gates import _waive004_violations
        from frob.graph import Edge, EdgeKind, GraphSnapshot

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py::helper",
            target="COV001",
            origin="src/a.py:2",
            attrs={"reason": "x"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        # No COV001 violation at all this run -- the waiver matches nothing.
        found = _waive004_violations((), snap, frozenset())
        assert len(found) == 1
        assert found[0].rule == "WAIVE004"
        assert found[0].severity == Severity.WARN
        assert "COV001" in found[0].message

    def test_waive004_stays_silent_on_a_genuinely_needed_waiver(self) -> None:
        """T-0753: a waiver whose site DOES still produce a matching finding
        must never fire WAIVE004 -- only a truly stale/unnecessary waiver is
        in scope."""
        from frob.gates import _waive004_violations
        from frob.graph import Edge, EdgeKind, GraphSnapshot

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py::helper",
            target="COV001",
            origin="src/a.py:2",
            attrs={"reason": "x"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        live_violation = Violation(
            rule="COV001",
            severity=Severity.ERROR,
            file="src/a.py",
            line=2,
            symref="src/a.py::helper",
            message="still missing a doc anchor",
        )
        found = _waive004_violations((live_violation,), snap, frozenset())
        assert found == ()

    def test_waive004_skips_a_waive002_unrecognized_rule(self) -> None:
        """T-0753: an edge WAIVE002 already flags as targeting an
        unrecognized rule id has no findings to compare against by
        construction -- WAIVE004 must not pile a second, redundant finding
        onto the same directive."""
        from frob.gates import _waive004_violations
        from frob.graph import Edge, EdgeKind, GraphSnapshot

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py::helper",
            target="NOTAREALRULE",
            origin="src/a.py:2",
            attrs={"reason": "typo"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        found = _waive004_violations((), snap, frozenset())
        assert found == ()

    def test_waive005_expired_until_is_error(self) -> None:
        """T-0753: `frob:waive`'s optional `until="YYYY-MM-DD"` boundary
        having passed forces a hard ERROR demanding re-review, mirroring
        DEBT003/DEPR004's expiry escalation."""
        # frob:tests src/frob/gates/__init__.py::_waive005_violations
        from frob.gates import _waive005_violations
        from frob.graph import Edge, EdgeKind, GraphSnapshot

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py::helper",
            target="COV001",
            origin="src/a.py:2",
            attrs={"reason": "x", "until": "2020-01-01"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        found = _waive005_violations(snap, current_date="2026-07-22")
        assert len(found) == 1
        assert found[0].rule == "WAIVE005"
        assert found[0].severity == Severity.ERROR
        assert "2020-01-01" in found[0].message

    def test_waive005_future_until_passes(self) -> None:
        """A `frob:waive ... until=` boundary still in the future must not
        fire WAIVE005."""
        from frob.gates import _waive005_violations
        from frob.graph import Edge, EdgeKind, GraphSnapshot

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py::helper",
            target="COV001",
            origin="src/a.py:2",
            attrs={"reason": "x", "until": "2099-01-01"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        assert _waive005_violations(snap, current_date="2026-07-22") == ()

    def test_waive_until_bad_date_is_malformed(self, tmp_path: Path) -> None:
        """T-0753: a `frob:waive ... until="..."` that is not a
        `YYYY-MM-DD` date is rejected at parse time, mirroring
        `frob:deprecated`'s `sunset=` validation (T-0576)."""
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="x" until="not-a-date"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        assert any(
            "frob:waive" in md.reason and "until" in md.reason for md in snap.malformed
        )

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

    # frob:ticket T-0557
    def test_test005_unmeasured_symbol_in_measured_file_flags_as_zero(
        self, tmp_path: Path
    ) -> None:
        """T-0557 (B4): a symbol with NO entry in `symbol_branch` -- never
        executed at all -- must still be flagged at 0% branch coverage when
        its FILE genuinely was measured (has a `module_line` entry).
        Previously `_test005_symbols` skipped any symbol absent from
        `symbol_branch`, silently clearing dead code that a test suite never
        calls into even once."""
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def dead(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::dead"]
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 90.0},
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(unit_branch_cov=90)
        )
        v = next(
            (
                v
                for v in violations
                if v.rule == "TEST005" and v.symref == record.symref
            ),
            None,
        )
        assert v is not None
        assert "0.0%" in v.message

    # frob:ticket T-0557
    def test_test005_symbol_in_unmeasured_file_still_skipped(
        self, tmp_path: Path
    ) -> None:
        """T-0557 (B4) counterpart: a symbol whose FILE never appears in
        coverage.xml at all (no `module_line` entry -- excluded from
        measurement, e.g. never imported by the suite) must still be
        skipped, not flagged at 0% -- that is a measurement gap, not proof
        the symbol itself fails the floor."""
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def unmeasured(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::unmeasured"]
        coverage = CoverageData(source_sha="x", symbol_branch={}, module_line={})
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(unit_branch_cov=90)
        )
        assert not any(
            v.rule == "TEST005" and v.symref == record.symref for v in violations
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

    def test_test011_fires_on_stale_mtime(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test011_freshness
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={},
            stale_by_mtime=True,
            module_join_fraction=1.0,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        test011 = [v for v in violations if v.rule == "TEST011"]
        assert len(test011) == 1
        assert test011[0].severity == Severity.WARN
        assert "predates" in test011[0].message

    def test_test011_fires_on_low_join_fraction(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test011_freshness
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={},
            stale_by_mtime=False,
            module_join_fraction=0.1,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        test011 = [v for v in violations if v.rule == "TEST011"]
        assert len(test011) == 1
        assert test011[0].severity == Severity.WARN
        assert "deflated" in test011[0].message

    def test_test011_silent_when_fresh_and_fully_joined(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test011_freshness
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        assert not any(v.rule == "TEST011" for v in violations)

    # frob:ticket T-0545
    def test_test012_missing_lock_warns(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test012_lock
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 90.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        test012 = [v for v in violations if v.rule == "TEST012"]
        assert len(test012) == 1
        assert test012[0].severity == Severity.WARN
        assert "no committed coverage lock" in test012[0].message

    # frob:ticket T-0545
    def test_test012_drifted_module_warns(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test012_lock
        from typani.option import Some

        from frob.gates import CoverageData, write_coverage_lock

        snap = _snapshot(tmp_path)
        locked = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 90.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        write_coverage_lock(tmp_path, locked)
        live = CoverageData(
            source_sha="y",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 10.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(live), tests, TestPolicy())
        test012 = [v for v in violations if v.rule == "TEST012"]
        assert len(test012) == 1
        assert "src/frob/pkg/a.py" in test012[0].message

    # frob:ticket T-0545
    def test_test012_matching_lock_is_clean(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test012_lock
        from typani.option import Some

        from frob.gates import CoverageData, write_coverage_lock

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 90.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        write_coverage_lock(tmp_path, coverage)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        assert not any(v.rule == "TEST012" for v in violations)

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

    def test_changelog_mentions_rejects_substring_in_prose(
        self, tmp_path: Path
    ) -> None:
        """T-0403 B14: `version` appearing anywhere in the file (unrelated
        prose, a longer version number's prefix) must NOT satisfy the
        changelog check -- only a real heading entry for that exact
        version does.
        """
        from frob.gates import _changelog_mentions  # noqa: PLC0415

        (tmp_path / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [1.2.34] - 2026-01-01\nbumped past 1.2.3 to fix a bug\n",
            encoding="utf-8",
        )
        # "1.2.3" is a substring of both the heading "1.2.34" and the prose
        # line, but there is no real heading entry for "1.2.3" itself.
        assert _changelog_mentions(tmp_path, "1.2.3") is False

    def test_changelog_mentions_accepts_real_heading_entry(
        self, tmp_path: Path
    ) -> None:
        """A genuine `## [version]` heading entry does satisfy the check."""
        from frob.gates import _changelog_mentions  # noqa: PLC0415

        (tmp_path / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [1.2.3] - 2026-01-01\nfixed things\n",
            encoding="utf-8",
        )
        assert _changelog_mentions(tmp_path, "1.2.3") is True

    def test_test006_stale_on_new_file_not_in_stamp(self, tmp_path: Path) -> None:
        """T-0403 B15: a file added after the last stamp has no entry in
        `file_hashes` at all -- it must be reported stale, not silently
        skipped (a prior version only compared hashes for paths already
        present in the stamp, so brand-new files' coverage went unmeasured
        while TEST006 stayed green).
        """
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(tmp_path, "src/frob/pkg/b.py", "def other(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        # Stamp only knows about a.py -- b.py was added afterward.
        a_hash = snap.file_hashes["src/frob/pkg/a.py"]
        stamp = {
            "source_sha": "x",
            "file_hashes": {"src/frob/pkg/a.py": a_hash},
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


# frob:ticket T-0545
class TestCoverageLoad:
    def test_missing_coverage_xml(self, tmp_path: Path) -> None:
        result = load_coverage(tmp_path)
        assert result.is_err

    def test_malformed_coverage_xml(self, tmp_path: Path) -> None:
        (tmp_path / "coverage.xml").write_text("not xml <<<")
        result = load_coverage(tmp_path)
        assert result.is_err

    # frob:waive DUP001 reason="parallel test methods within test_gates.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
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

    def test_load_coverage_flags_stale_by_mtime(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage
        # T-0464: a coverage.xml written BEFORE the source it claims to
        # measure must be flagged, since `source_sha` alone (the sha of
        # coverage.xml itself) cannot detect this -- it always looks
        # "fresh" relative to its own content.
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        xml = (
            '<?xml version="1.0"?><coverage><sources>'
            f"<source>{(tmp_path / 'src/frob').resolve()}</source>"
            "</sources><packages><package><classes>"
            '<class filename="pkg/a.py" line-rate="1.0">'
            '<lines><line number="1" hits="1" branch="false"/></lines>'
            "</class></classes></package></packages></coverage>"
        )
        xml_path = tmp_path / "coverage.xml"
        xml_path.write_text(xml)
        # Back-date coverage.xml so it predates the source file above.
        old = (tmp_path / "src/frob/pkg/a.py").stat().st_mtime - 3600
        os.utime(xml_path, (old, old))
        result = load_coverage(tmp_path, snap)
        assert result.is_ok
        assert result.danger_ok.stale_by_mtime

    def test_load_coverage_fresh_by_mtime(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        xml = (
            '<?xml version="1.0"?><coverage><sources>'
            f"<source>{(tmp_path / 'src/frob').resolve()}</source>"
            "</sources><packages><package><classes>"
            '<class filename="pkg/a.py" line-rate="1.0">'
            '<lines><line number="1" hits="1" branch="false"/></lines>'
            "</class></classes></package></packages></coverage>"
        )
        (tmp_path / "coverage.xml").write_text(xml)  # written after the source
        result = load_coverage(tmp_path, snap)
        assert result.is_ok
        assert not result.danger_ok.stale_by_mtime

    def test_load_coverage_module_join_fraction_deflated(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage
        # T-0464: coverage.xml that only measured one of two known modules
        # (the fingerprint of dropped subprocess coverage) must report a
        # module_join_fraction below 1.0, even though root_join_ok is True
        # (SOME data did join).
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(tmp_path, "src/frob/pkg/b.py", "def other(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        xml = (
            '<?xml version="1.0"?><coverage><sources>'
            f"<source>{(tmp_path / 'src/frob').resolve()}</source>"
            "</sources><packages><package><classes>"
            '<class filename="pkg/a.py" line-rate="1.0">'
            '<lines><line number="1" hits="1" branch="false"/></lines>'
            "</class></classes></package></packages></coverage>"
        )
        (tmp_path / "coverage.xml").write_text(xml)
        result = load_coverage(tmp_path, snap)
        assert result.is_ok
        assert result.danger_ok.module_join_fraction == 0.5

    def test_load_coverage_module_join_fraction_full(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        xml = (
            '<?xml version="1.0"?><coverage><sources>'
            f"<source>{(tmp_path / 'src/frob').resolve()}</source>"
            "</sources><packages><package><classes>"
            '<class filename="pkg/a.py" line-rate="1.0">'
            '<lines><line number="1" hits="1" branch="false"/></lines>'
            "</class></classes></package></packages></coverage>"
        )
        (tmp_path / "coverage.xml").write_text(xml)
        result = load_coverage(tmp_path, snap)
        assert result.is_ok
        assert result.danger_ok.module_join_fraction == 1.0

    # frob:waive DUP001 reason="parallel test methods within test_gates.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
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

    # frob:waive DUP001 reason="parallel test methods within test_gates.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
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

    # frob:ticket T-0545
    def test_stamp_coverage_refreshes_committed_lock(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::stamp_coverage
        # frob:tests src/frob/gates/_coverage.py::load_coverage_lock
        # T-0545: passing a snapshot makes stamp_coverage also write the
        # committed frob-coverage.lock.json, with no separate CLI call.
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        xml = """<?xml version="1.0"?>
<coverage>
  <packages>
    <package>
      <classes>
        <class filename="src/frob/pkg/a.py" line-rate="0.9">
          <lines><line number="2" hits="1" branch="false"/></lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""
        (tmp_path / "coverage.xml").write_text(xml)
        snap = _snapshot(tmp_path)
        result = stamp_coverage(tmp_path, snap)
        assert result.is_ok

        from frob.gates._coverage import load_coverage_lock

        lock = load_coverage_lock(tmp_path)
        assert lock is not None
        assert lock["module_line"]["src/frob/pkg/a.py"] == 90.0
        assert not (tmp_path / "frob-coverage.lock.json").is_relative_to(
            tmp_path / ".frob"
        )

    # frob:ticket T-0997
    def test_stamp_coverage_lock_excludes_graph_excluded_modules(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::stamp_coverage
        # frob:tests src/frob/gates/_coverage.py::exclude_filtered_coverage
        # T-0997: `stamp_coverage`'s lock write must apply the SAME
        # `[graph] exclude` filter the TEST012 gate check applies to the
        # live coverage.xml it diffs against -- previously the lock kept
        # every `<class>` entry unfiltered (including scaffold `.j2`
        # templates coverage.xml happened to list), so TEST012 flagged
        # those paths as permanent, unfixable drift no re-stamp could clear.
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "frob.toml",
            '[graph]\nexclude = ["src/frob/scaffold/data/**"]\n',
        )
        xml = """<?xml version="1.0"?>
<coverage>
  <packages>
    <package>
      <classes>
        <class filename="src/frob/pkg/a.py" line-rate="0.9">
          <lines><line number="2" hits="1" branch="false"/></lines>
        </class>
        <class filename="src/frob/scaffold/data/tmpl.py.j2" line-rate="0.5">
          <lines><line number="1" hits="1" branch="false"/></lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""
        (tmp_path / "coverage.xml").write_text(xml)
        snap = _snapshot(tmp_path)
        result = stamp_coverage(tmp_path, snap)
        assert result.is_ok

        from frob.gates._coverage import load_coverage_lock

        lock = load_coverage_lock(tmp_path)
        assert lock is not None
        assert "src/frob/pkg/a.py" in lock["module_line"]
        assert "src/frob/scaffold/data/tmpl.py.j2" not in lock["module_line"]

    # frob:ticket T-0545
    def test_coverage_lock_diff_flags_drift_and_missing_module(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::coverage_lock_diff
        from frob.gates import CoverageData
        from frob.gates._coverage import coverage_lock_diff

        lock = {"module_line": {"a.py": 90.0, "b.py": 50.0}}
        live = CoverageData(source_sha="y", module_line={"a.py": 91.0})
        assert coverage_lock_diff(lock, live) == ("b.py",)

        live_drifted = CoverageData(
            source_sha="y", module_line={"a.py": 10.0, "b.py": 50.0}
        )
        assert coverage_lock_diff(lock, live_drifted) == ("a.py",)


# frob:ticket T-0541
# frob:ticket T-0542
# frob:ticket T-0543
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

    # frob:tests src/frob/gates/__init__.py::_build_ticket_scoped_jobs
    # frob:ticket T-0541
    # frob:ticket T-0542
    # frob:ticket T-0543
    def test_run_gates_blocks_scope_and_prework_when_no_ticket_touches_source(
        self, tmp_path: Path
    ) -> None:
        """B9: an off-convention branch (or `main`) with no `--ticket` and a
        diff that touches real source must not silently skip SCOPE001/
        PRE001 -- it must block instead."""
        _git_init(tmp_path)
        _write(tmp_path, "src/pkg/a.py", "def helper(x):\n    return x\n")
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "prework"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert "scope" not in report.stats.skipped
        assert "prework" not in report.stats.skipped
        assert any(v.rule == "SCOPE001" for v in report.violations)
        assert any(v.rule == "PRE001" for v in report.violations)

    # frob:tests src/frob/gates/__init__.py::_build_ticket_scoped_jobs
    # frob:ticket T-0541
    # frob:ticket T-0542
    # frob:ticket T-0543
    def test_run_gates_still_skips_scope_and_prework_for_ledger_only_diff(
        self, tmp_path: Path
    ) -> None:
        """B9's fix must not fire on a `tickets.md`-only diff (ledger
        maintenance, e.g. archiving closed tickets, is a legitimate
        no-ticket main-branch operation)."""
        _git_init(tmp_path)
        _write(tmp_path, "tickets.md", "# tickets\n")
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "prework"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert "scope" in report.stats.skipped
        assert "prework" in report.stats.skipped

    # frob:tests src/frob/gates/__init__.py::_build_ticket_scoped_jobs
    # frob:ticket T-0541
    def test_run_gates_blocks_prework_when_diff_load_fails_with_no_ticket(
        self, tmp_path: Path
    ) -> None:
        """B9 remainder: a repo with no git history at all (detached-HEAD-
        shaped: `working_diff` has no merge-base and fails outright) and no
        derivable ticket must still block PRE001 loudly, not silently skip
        it. Before this fix, `_load_diff`'s degraded-empty placeholder made
        `no_ticket_blocks` see zero touched files, so PRE001 skipped even
        though the diff genuinely failed to load -- the exact B9 escape,
        reached through the diff-load-failure door instead of the
        off-convention-branch-name door. SCOPE001 already had a matching
        unconditional `diff_load_failed` check; PRE001 did not."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text("def f(x):\n    return x\n")
        cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "prework"})
        )
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        assert "prework" not in report.stats.skipped
        pre001 = _first_rule(report.violations, "PRE001")
        assert pre001 is not None
        assert "failed to load" in pre001.message


class TestRunJobsTimingAttribution:
    """T-0232: `_run_jobs` must attribute each job its OWN cost, not a
    number smeared across every job sharing the thread pool."""

    def test_cpu_bound_neighbor_does_not_inflate_a_cheap_jobs_timing(self) -> None:
        """Pin the regression this ticket was filed against: run one
        deliberately CPU-heavy job (busy-loops, holds the GIL) alongside
        several genuinely cheap jobs on the same `ThreadPoolExecutor`, as
        `_run_jobs` does for real gates. Wall-clock timing (the old
        behavior) would have every cheap job's *elapsed* converge toward
        the heavy job's -- the exact "secrets=39.71s sys=39.71s
        tickets=39.69s" symptom this ticket reports. CPU-time attribution
        must not: each cheap job's own reported cost stays small and
        distinct from the heavy job's, regardless of how long the run
        takes in total.
        """
        from collections.abc import Callable

        from frob.gates import _run_jobs

        def heavy() -> tuple[Violation, ...]:
            # Pure-Python busy work: holds the GIL, no I/O yields.
            total = 0
            for i in range(30_000_000):
                total += i
            return ()

        def cheap() -> tuple[Violation, ...]:
            return ()

        jobs: dict[str, Callable[[], tuple[Violation, ...]]] = {
            "heavy": heavy,
            "cheap_a": cheap,
            "cheap_b": cheap,
            "cheap_c": cheap,
        }
        _, _, timing = _run_jobs(jobs)

        assert timing["heavy"] > 0.05
        for name in ("cheap_a", "cheap_b", "cheap_c"):
            # A cheap job's OWN cpu time stays near zero; under the old
            # wall-clock scheme this would have been pulled up toward
            # timing["heavy"] by GIL contention.
            assert timing[name] < timing["heavy"] / 2, (
                f"{name} timing {timing[name]:.3f}s was pulled toward the "
                f"heavy job's {timing['heavy']:.3f}s -- attribution is "
                "shared/wrong again"
            )


# frob:ticket T-0947
class TestProcessPoolGates:
    """T-0415: CPU-bound gates (archgate, sys, clones, perf, pii_structural,
    secrets -- docs/audits/perf.md H3) run in a `ProcessPoolExecutor`
    instead of the shared thread pool, so the GIL no longer serializes
    them. `_run_combined_jobs` must (a) actually dispatch process jobs to a
    worker process, and (b) merge results back in `_CANONICAL_GATE_ORDER`
    regardless of pool/completion order, so output stays deterministic.

    T-0947 added `test_open_process_pool_preloads_forkserver_when_available`
    to this class -- covering `_open_process_pool`'s `forkserver`+preload
    cold-start fix -- without otherwise changing this class's pre-existing
    T-0415 tests."""

    def test_process_job_runs_in_a_separate_process(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_run_combined_jobs
        # frob:tests src/frob/gates/__init__.py::_run_process_gate
        # frob:waive COV006 reason="two \
        # sound-but-invisible-to-the-name-based-call-graph shapes in this file \
        # (T-0516): (1) this test submits _run_process_gate to a ProcessPoolExecutor \
        # by function reference (ppool.submit(_run_process_gate, ...)), not a \
        # name-call token in the test's own body; (2) \
        # test_canonical_gate_order_matches_all_gates and its siblings in \
        # TestGateOrderSetEquality below check _CANONICAL_GATE_ORDER/_ALL_GATES \
        # set-equality directly and never call _merge_canonical_order, the consumer \
        # whose correctness that invariant protects -- module-level constants have no \
        # symref for the graph to track. T-0525 gave COV006 a per-edge symref, so this \
        # waiver now only covers THIS edge (test's own frob:tests -> \
        # _merge_canonical_order binding); test_all_gates_is_subset_of_canonical_order \
        # below carries its own matching frob:waive COV006 (same reasoning, not a \
        # blanket reach); test_canonical_order_names_no_nonexistent_gate needs none -- \
        # its frob:tests directive lives inside its docstring, not a `#` comment, so \
        # it never creates a real TESTS edge for COV006 to flag in the first place \
        # (verified: a waiver placed there fired WAIVE004, 0 matching findings) (the \
        # T-0516 calibration ticket this comment used to point at)"
        import os

        from frob.gates import _ProcessJob, _run_combined_jobs

        process_jobs = {
            "archgate": _ProcessJob(
                _module_level_process_violation, (tmp_path, "archgate")
            ),
            "sys": _ProcessJob(_module_level_process_violation, (tmp_path, "sys")),
        }
        violations, counts, timing = _run_combined_jobs({}, process_jobs)
        assert counts["archgate"] == 1
        assert counts["sys"] == 1
        assert "archgate" in timing
        assert "sys" in timing
        pids = {v.message.split(":")[1] for v in violations}
        assert str(os.getpid()) not in pids, (
            "process-pool job ran in the parent process, not a worker -- "
            "no real parallelism"
        )

    def test_combined_jobs_merge_in_canonical_order(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_run_combined_jobs
        """Merge order must follow `_CANONICAL_GATE_ORDER` (drift before
        sys before archgate), not submission or completion order across
        the two pools -- this is what keeps `frob check` output byte-
        identical to the pre-T-0415 single-pool run."""
        from collections.abc import Callable

        from frob.gates import _ProcessJob, _run_combined_jobs

        def cheap_thread() -> tuple[Violation, ...]:
            return (
                Violation(
                    rule="A",
                    severity=Severity.WARN,
                    file="x",
                    line=1,
                    message="thread-drift",
                ),
            )

        thread_jobs: dict[str, Callable[[], tuple[Violation, ...]]] = {
            "drift": cheap_thread
        }
        process_jobs = {
            "sys": _ProcessJob(_module_level_process_violation, (tmp_path, "sys")),
            "archgate": _ProcessJob(
                _module_level_process_violation, (tmp_path, "archgate")
            ),
        }
        violations, _, _ = _run_combined_jobs(thread_jobs, process_jobs)
        assert violations[0].rule == "A"
        tags = [v.message.split(":")[0] for v in violations[1:]]
        # _CANONICAL_GATE_ORDER places "sys" before "archgate".
        assert tags == ["sys", "archgate"]

    def test_run_gates_output_is_identical_across_repeated_runs(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::run_gates
        """End-to-end determinism proof (T-0415 constraint 2): selecting a
        mix of thread-pool and process-pool gates and running `run_gates`
        twice on the same tree must produce byte-identical violation
        tuples (same content, same order) despite the process pool's
        results arriving in whatever order the OS schedules them."""
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _git_init(tmp_path)
        selected = frozenset({"drift", "coverage", "sys", "archgate", "secrets"})
        cfg = GateConfig(root=str(tmp_path), base="main", gates=selected)

        first = run_gates(cfg)
        second = run_gates(cfg)
        assert first.is_ok
        assert second.is_ok
        report1 = first.danger_ok
        report2 = second.danger_ok
        assert report1.violations == report2.violations
        assert report1.stats.counts == report2.stats.counts

    def test_combined_parallel_path_matches_fully_serial_path(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_run_combined_jobs
        # frob:tests src/frob/gates/__init__.py::_build_jobs
        """T-0415's explicit correctness requirement: the parallel path
        (thread pool + process pool via `_run_combined_jobs`) must produce
        the same violation SET as calling every job function serially,
        in-process, one at a time -- no double-work, no dropped results,
        no reordering-induced content drift. Compares as a sorted
        multiset (rule, file, line, message) since a purely serial
        for-loop naturally visits jobs in dict order, which already
        matches `_CANONICAL_GATE_ORDER` for `_build_jobs`'s output, but
        the assertion is written order-independent to test content, not
        incidental iteration order."""
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _git_init(tmp_path)
        selected = frozenset({"drift", "coverage", "sys", "archgate", "secrets"})
        cfg = GateConfig(root=str(tmp_path), base="main", gates=selected)

        from frob.gates import _build_jobs, _load_inputs, _run_combined_jobs

        inputs = _load_inputs(cfg)
        assert inputs.is_ok
        st = inputs.danger_ok
        thread_jobs, process_jobs, _skipped = _build_jobs(selected, st)

        parallel_violations, _, _ = _run_combined_jobs(thread_jobs, process_jobs)

        serial_violations: list[Violation] = [
            v for job in thread_jobs.values() for v in job()
        ] + [v for pj in process_jobs.values() for v in pj.func(*pj.args)]

        def key(v: Violation) -> tuple:
            return (v.rule, v.file, v.line, v.message)

        parallel_sorted = sorted(parallel_violations, key=key)
        serial_sorted = sorted(serial_violations, key=key)
        assert parallel_sorted == serial_sorted
        assert len(parallel_violations) == len(serial_violations)

    def test_open_process_pool_preloads_forkserver_when_available(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-0947
        # frob:tests src/frob/gates/__init__.py::_open_process_pool
        # frob:tests src/frob/gates/__init__.py::_process_pool_start_method
        """T-0947: `_open_process_pool` must pick `forkserver` (with
        `_FORKSERVER_PRELOAD` set on the context) whenever this platform's
        `multiprocessing.get_all_start_methods()` offers it, and must
        actually call `set_forkserver_preload` on THAT context object
        (asserted via the context's own `_preload` attribute, not just
        absence of an exception) -- a `==` -> `!=` mutation on the
        start-method check would silently skip the preload call on every
        platform that supports `forkserver` (this repo's own CI/dev
        platform included) while still passing every OTHER test in this
        class, since none of them inspect the constructed pool's own
        `mp_context`."""
        import multiprocessing
        import multiprocessing.forkserver as mp_forkserver

        from frob.gates import (
            _FORKSERVER_PRELOAD,
            _open_process_pool,
            _process_pool_start_method,
            _ProcessJob,
        )

        process_jobs = {
            "clones": _ProcessJob(_module_level_process_violation, (tmp_path, "x")),
        }
        ppool = _open_process_pool(process_jobs)
        try:
            ctx = ppool._mp_context
            expected_method = _process_pool_start_method()
            assert ctx.get_start_method() == expected_method  # ty: ignore[unresolved-attribute]
            if expected_method == "forkserver":
                # `set_forkserver_preload` stores its argument on the
                # process-wide `multiprocessing.forkserver._forkserver`
                # singleton's own `_preload_modules` list, not on the
                # context object itself -- reading it back proves the
                # preload call actually ran rather than merely that no
                # exception was raised.
                assert list(
                    mp_forkserver._forkserver._preload_modules  # ty: ignore[unresolved-attribute]
                ) == list(_FORKSERVER_PRELOAD)
        finally:
            ppool.shutdown(wait=True)
        assert "forkserver" in multiprocessing.get_all_start_methods()


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

    def test_sec110_promoted_to_error_gates_a_real_repo_toml(self, tmp_path):
        # frob:tests src/frob/gates/__init__.py::_apply_severity_overrides kind="unit"
        # T-0973 before-fails/after-passes fixture: proves the SEC110
        # WARN -> ERROR promotion in this repo's own frob.toml actually
        # changes gate outcome, not merely that the override table parses.
        # FAIL: with no [gates.severity] entry for SEC110 (the pre-T-0973
        # posture), an unwaived SEC110 finding stays WARN and never blocks
        # `frob check`.
        from frob.gates import Severity, Violation, _apply_severity_overrides

        (tmp_path / "frob.toml").write_text("", encoding="utf-8")
        finding = (
            Violation(
                rule="SEC110",
                severity=Severity.WARN,
                file="src/frob/example.py",
                line=1,
                message="reads os.environ.get(...)",
            ),
        )
        before = _apply_severity_overrides(finding, tmp_path)
        assert before[0].severity == Severity.WARN, (
            "FAIL case: no override leaves SEC110 at WARN"
        )

        # PASS: this repo's real frob.toml (with T-0973's SEC110 = "error"
        # line in place) promotes the same finding to ERROR.
        repo_root = Path(__file__).resolve().parents[1]
        after = _apply_severity_overrides(finding, repo_root)
        assert after[0].severity == Severity.ERROR, (
            "PASS case: repo frob.toml now gates SEC110 at ERROR"
        )


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


# frob:ticket T-0542
# frob:ticket T-0543
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

    # frob:tests src/frob/gates/__init__.py::_scope_covers
    # frob:ticket T-0542
    # frob:ticket T-0543
    def test_ambiguous_overlapping_open_scopes_do_not_cover(self, tmp_path):
        """B10: two open, EQUALLY specific tickets whose scopes both cover
        the same file must NOT silently cover a changed symbol -- that is
        exactly the false-negative one broad open ticket used to grant
        everything under it."""
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

        for title in ("refactor-a", "refactor-b"):
            t = new_ticket(
                tmp_path,
                TicketSpec(
                    title=title,
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
        assert any(v.rule == "COV002" for v in report.violations)

    # frob:tests src/frob/gates/__init__.py::_scope_covers
    # frob:ticket T-0542
    # frob:ticket T-0543
    def test_active_ticket_own_scope_wins_over_a_broader_open_ticket(self, tmp_path):
        """B10: the active ticket's own scope covers the symbol even when a
        second, broader open ticket ALSO happens to cover the same file --
        no ambiguity should be raised when the active ticket is one of the
        matches."""
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

        active = new_ticket(
            tmp_path,
            TicketSpec(
                title="active",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                scope=("src/**",),
            ),
        ).danger_ok
        transition(tmp_path, active.id, TicketState.PLANNED)
        transition(tmp_path, active.id, TicketState.IN_PROGRESS)
        other = new_ticket(
            tmp_path,
            TicketSpec(
                title="other",
                kind=TicketKind.FEATURE,
                origin=Origin.AGENT,
                scope=("src/**",),
            ),
        ).danger_ok
        transition(tmp_path, other.id, TicketState.PLANNED)
        transition(tmp_path, other.id, TicketState.IN_PROGRESS)
        (tmp_path / "src" / "m.py").write_text("def f():\n    return 2\n")

        report = run_gates(
            GateConfig(
                root=str(tmp_path),
                base="main",
                gates=frozenset({"coverage"}),
                ticket=active.id,
            )
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

    # frob:tests \
    # tests/test_gates.py::TestCov002StrataModuleCoverage.test_module_level_ticket_edge\
    # _covers_nested_declaration
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

    # frob:tests \
    # tests/test_gates.py::TestCov002StrataModuleCoverage.test_declaration_without_modu\
    # le_edge_still_fires
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


# frob:ticket T-0550
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

    # frob:ticket T-0550
    # frob:ticket T-0719
    # frob:tests src/frob/gates/__init__.py::coverage_gate kind="unit"
    def test_diff_dependent_gates_block_loudly_on_failed_diff(self, tmp_path):
        """T-0550/B8 counterexample, narrowed by T-0719: a REAL git repo
        whose `working_diff` genuinely fails (here, a bad `--base` that
        cannot resolve to a merge-base) must still fire COV002 as a loud,
        diff-load-failure violation, never silently pass -- this is the
        T-0550 protection T-0719 explicitly must not weaken. `tmp_path` is
        `git init`ed with a real commit so the failure is unambiguously
        "a real repo's diff broke", not "there is no repo at all" (see
        `test_diff_dependent_gates_pass_quietly_on_a_genuinely_gitless_root`
        below for that other, now-distinguished, case). Kept under its
        original T-0550 name -- not renamed -- because T-0550's archived
        Done report cites this exact pytest node id as evidence
        (tickets-archive.md); this test's scenario changed (no-repo-at-all
        -> real-repo-bad-base) to stay a true positive for the assertion it
        still makes (COV002 fires loudly), but the id itself had to stay
        stable."""
        import subprocess

        from frob.gates import GateConfig, run_gates

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text("def undocumented(x):\n    return x\n")
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t.t", "-c", "user.name=t", "add", "-A"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=t@t.t",
                "-c",
                "user.name=t",
                "commit",
                "-q",
                "-m",
                "seed",
            ],
            cwd=tmp_path,
            check=True,
        )

        report = run_gates(
            GateConfig(
                root=str(tmp_path),
                base="does-not-resolve-to-anything",
                gates=frozenset({"coverage"}),
            )
        )
        assert report.is_ok, report.err
        cov002 = [v for v in report.danger_ok.violations if v.rule == "COV002"]
        assert cov002, "COV002 must not silently pass on a real repo's failed diff load"
        assert "failed to load" in cov002[0].message

    # frob:ticket T-0719
    # frob:tests src/frob/gates/__init__.py::coverage_gate kind="unit"
    def test_diff_dependent_gates_pass_quietly_on_a_genuinely_gitless_root(
        self, tmp_path
    ):
        """T-0719: a genuinely git-less `root` (no `.git` anywhere above it,
        e.g. a system-test fixture that never calls `git init`) is not the
        same failure shape as a real repo's broken diff -- there is
        structurally no touched set to enforce COV002 against, so it must
        be treated the same as a clean/empty diff (no violation), not the
        loud diff-load-failure violation
        `test_diff_dependent_gates_block_loudly_on_failed_diff` above pins
        for a real repo."""
        from frob.gates import GateConfig, run_gates

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text("def undocumented(x):\n    return x\n")

        report = run_gates(
            GateConfig(root=str(tmp_path), base="main", gates=frozenset({"coverage"}))
        )
        assert report.is_ok, report.err
        cov002 = [v for v in report.danger_ok.violations if v.rule == "COV002"]
        assert not cov002, (
            f"COV002 must not hard-error on a genuinely git-less root: {cov002}"
        )


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

    # frob:tests \
    # tests/test_gates.py::TestConventionUnitBinding.test_test001_exempts_strata_flow_d\
    # eclarations kind="unit"
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

    # frob:tests \
    # tests/test_gates.py::TestConventionUnitBinding.test_test009_fires_on_unbound_desi\
    # gn_file kind="unit"
    def test_test009_fires_on_unbound_design_file(self, tmp_path):
        """T-0225: a `.strata` design file with no `frob:tests kind="e2e"`
        edge owes TEST009 -- the e2e-binding obligation that replaces the
        TEST003 package check design files were wrongly held to."""
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert any(
            v.rule == "TEST009" and v.file == "design/m.strata" for v in violations
        )

    # frob:tests \
    # tests/test_gates.py::TestConventionUnitBinding.test_test009_exempts_test_fixture_\
    # strata kind="unit"
    def test_test009_exempts_test_fixture_strata(self, tmp_path):
        """T-0225 follow-up: a `.strata` file under a tests dir (a litmus /
        parser fixture) is test DATA, not a deployable design model, so it
        does NOT owe a TEST009 e2e binding -- `_design_files` excludes it via
        `_is_test_file`, killing the ~70-warning fixture flood."""
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "tests/unit/strata/litmus/fixture.strata", _DESIGN_STRATA)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert not any(v.rule == "TEST009" for v in violations)

    # frob:tests \
    # tests/test_gates.py::TestConventionUnitBinding.test_test009_satisfied_by_e2e_edg\
    # e kind="unit"
    def test_test009_satisfied_by_e2e_edge(self, tmp_path):
        """T-0225: a `frob:tests ... kind="e2e"` edge bound to the design
        file's module (or one of its declared ids) and backed by a
        collected test node id satisfies TEST009."""
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        _write(
            tmp_path,
            "tests/test_m_e2e.py",
            '# frob:tests design/m.strata::m.f_login kind="e2e"\n'
            "def test_login_flow_e2e():\n"
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_m_e2e.py::test_login_flow_e2e"})
        )
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert not any(
            v.rule == "TEST009" and v.file == "design/m.strata" for v in violations
        )


class TestTest010KindValidation:
    """T-0237: a `frob:tests` directive's `kind=` attribute is not
    gate-verified -- `frob.graph.dsl` already refuses to turn an invalid
    `kind=` into an edge at all (a `MalformedDirective`, never silently
    defaulted), but nothing surfaced that as a reported violation until
    TEST010."""

    # frob:tests \
    # tests/test_gates.py::TestTest010KindValidation.test_invalid_kind_reported \
    # kind="unit"
    def test_invalid_kind_reported(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="drift"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        v = _first_rule(violations, "TEST010")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert v.file == "tests/test_a.py"
        assert "drift" in v.message

    # frob:tests \
    # tests/test_gates.py::TestTest010KindValidation.test_valid_kind_not_reported \
    # kind="unit"
    def test_valid_kind_not_reported(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset({"tests/test_a.py::test_helper"}))
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST010" not in _rules(violations)

    # frob:tests \
    # tests/test_gates.py::TestTest010KindValidation.test_dangling_tests_endpoint_still\
    # _caught_by_drift002 kind="unit"
    def test_dangling_tests_endpoint_still_caught_by_drift002(
        self, tmp_path: Path
    ) -> None:
        """T-0237's other reported gap -- a `frob:tests` edge whose CODE-side
        endpoint no longer resolves -- turns out to already be caught by the
        existing, edge-kind-agnostic DRIFT002 mechanism (`_vanished_endpoint`
        checks every edge's `src`/`target`, not just `frob:describes`); this
        pins that down as a regression guard rather than adding a duplicate
        TESTS-specific resolver."""
        from frob.gates import drift_gate
        from frob.graph._models import LockFile

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::gone kind="unit"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        violations = drift_gate(snap, LockFile())
        v = _first_rule(violations, "DRIFT002")
        assert v is not None
        assert "src/frob/pkg/a.py::gone" in v.message


# frob:ticket T-0552
# frob:ticket T-0730
class TestTest013NativeUnverified:
    """T-0552 (docs/audits/gates-accounting.md B3/E3): a `frob:tests` edge
    whose ONLY credit toward TEST001-004 is the c/cpp structural (name/
    path) fallback (T-0730 retired TS from this fallback -- see
    `TestNativeTestCollectors`) -- frob runs no collector that actually
    executes it -- must be surfaced as a loud, filterable TEST013 finding,
    not stay silently indistinguishable from a real, executed test."""

    # frob:ticket T-0552
    def test_fires_on_structural_only_edge(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates.py::TestTest013NativeUnverified.test_fires_on_structural_only_edge  # noqa: E501
        from typani.option import Nothing

        _write(
            tmp_path,
            "src/pkg/thing.c",
            "void some_public_func(void) {}\n\n"
            '// frob:tests src/pkg/thing.c::some_public_func kind="unit"\n'
            "void test_something(void) {}\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())  # frob never ran this
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        test013 = [v for v in violations if v.rule == "TEST013"]
        assert len(test013) == 1
        assert test013[0].severity == Severity.WARN
        assert "test_something" in test013[0].message
        assert "unverified" in test013[0].message

    # frob:ticket T-0552
    def test_silent_on_executed_edge(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates.py::TestTest013NativeUnverified.test_silent_on_executed_edge  # noqa: E501
        # A python edge with real collected execution evidence (pytest node
        # id) must never be mistaken for the native-unverified case -- the
        # extension check in `_edge_is_native_unverified` is what keeps
        # TEST013 scoped to languages frob genuinely cannot execute.
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset({"tests/test_a.py::test_helper"}))
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST013" not in _rules(violations)


# frob:ticket T-0730
class TestNativeTestCollectors:
    """T-0730: `_load_tests` now consumes `collect_ts_tests` (vitest) and
    `collect_cpp_tests` (ctest) node ids alongside python/rust (T-0587
    built the collectors; this wires them into `frob.gates`), and TS is
    retired from `_NATIVE_TEST_EXTENSIONS`'s structural fallback now that a
    real vitest node id can resolve a TS `frob:tests` edge exactly the way
    a pytest/cargo node id already does."""

    # frob:ticket T-0730
    def test_ts_no_longer_in_native_extensions(self) -> None:
        # frob:tests tests/test_gates.py::TestNativeTestCollectors.test_ts_no_longer_in_native_extensions  # noqa: E501
        import frob.gates as gates_mod

        assert ".ts" not in gates_mod._NATIVE_TEST_EXTENSIONS
        assert ".tsx" not in gates_mod._NATIVE_TEST_EXTENSIONS
        # C/C++ stays -- collect_cpp_tests's node ids anchor to the build
        # dir, not the source file, so no exact/prefix match is possible
        # yet (T-0730's Done report, follow-on draft ticket).
        assert ".cpp" in gates_mod._NATIVE_TEST_EXTENSIONS

    # frob:ticket T-0730
    def test_load_tests_merges_all_four_collectors(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/test_gates.py::TestNativeTestCollectors.test_load_tests_merges_all_four_collectors  # noqa: E501
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
        monkeypatch.setattr(
            gates_mod,
            "collect_ts_tests",
            lambda root: Ok(
                CollectedTests(node_ids=frozenset({"src/thing.test.ts::does a thing"}))
            ),
        )
        monkeypatch.setattr(
            gates_mod,
            "collect_cpp_tests",
            lambda root: Ok(CollectedTests(node_ids=frozenset({"build::MyTest"}))),
        )
        merged = gates_mod._load_tests(tmp_path)
        assert merged.node_ids == frozenset(
            {
                "tests/test_x.py::test_a",
                "crate/src/lib.rs::tests::foo",
                "src/thing.test.ts::does a thing",
                "build::MyTest",
            }
        )

        # A broken vitest collector degrades to "no ts ids", not a crash
        # and not a wipe of the other three languages' already-collected
        # ids.
        monkeypatch.setattr(
            gates_mod,
            "collect_ts_tests",
            lambda root: Err(TestingError.CollectFailed),
        )
        merged2 = gates_mod._load_tests(tmp_path)
        assert merged2.node_ids == frozenset(
            {
                "tests/test_x.py::test_a",
                "crate/src/lib.rs::tests::foo",
                "build::MyTest",
            }
        )

    # frob:ticket T-0730
    def test_ts_directive_resolves_via_real_vitest_node_id(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates.py::TestNativeTestCollectors.test_ts_directive_resolves_via_real_vitest_node_id  # noqa: E501
        """A TS `frob:tests` directive naming a real collected vitest node id
        resolves as genuine execution evidence (`_valid_edges`'s FIRST
        branch, `_symref_to_nodeid`/`_node_id_collected`) -- not the
        structural fallback, which TS no longer participates in at all."""
        from typani.option import Nothing

        _write(
            tmp_path,
            "src/thing.ts",
            "export function doThing(): number {\n  return 0;\n}\n",
        )
        _write(
            tmp_path,
            "src/thing.test.ts",
            '// frob:tests src/thing.ts::doThing kind="unit"\n'
            "export function testDoesAThing(): void {\n"
            "  doThing();\n"
            "}\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"src/thing.test.ts::testDoesAThing"})
        )
        cfg = TestPolicy(min_unit_cases=1)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST001" not in rule_ids
        assert "TEST002" not in rule_ids
        assert "TEST013" not in rule_ids

    # frob:ticket T-0730
    def test_ts_structural_only_edge_no_longer_credited(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates.py::TestNativeTestCollectors.test_ts_structural_only_edge_no_longer_credited  # noqa: E501
        """Acceptance (T-0730): a TS `frob:tests` edge that only LOOKS like
        test code by name/path, with NO real collected vitest evidence, no
        longer gets any TEST001-004 credit at all -- the structural
        fallback `_edge_is_native_unverified` used to grant TS (T-0552) is
        retired for `.ts`. The edge still exists (so TEST001, "no edge at
        all", stays clean), but it now counts zero cases instead of the one
        the retired fallback used to grant, so it is a genuine TEST002
        finding rather than a silent pass or a TEST013 warning."""
        from typani.option import Nothing

        _write(
            tmp_path,
            "src/thing.ts",
            "export function doThing(): number {\n  return 0;\n}\n\n"
            '// frob:tests src/thing.ts::doThing kind="unit"\n'
            "export function testDoThing(): void {}\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())  # frob never ran this
        cfg = TestPolicy(min_unit_cases=1)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST001" not in rule_ids
        assert "TEST002" in rule_ids
        assert "TEST013" not in rule_ids


# frob:ticket T-0547
class TestTest014AmbiguousConventionMatch:
    """T-0547 (docs/audits/gates-accounting.md B6/E6): `_inferred_unit_cases`
    matches by snake-cased leaf name alone, no module/path binding -- two
    different public functions named the same thing in different files can
    both clear TEST001 off one test that only actually exercises one."""

    # frob:ticket T-0547
    def test_fires_on_cross_file_same_test_collision(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates.py::TestTest014AmbiguousConventionMatch.test_fires_on_cross_file_same_test_collision  # noqa: E501
        # The audit's own repro: two `def parse()` in different modules,
        # neither carrying an explicit frob:tests edge, one `test_parse`
        # covering (by convention) both.
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg_a/mod.py", "def parse(x):\n    return x\n")
        _write(tmp_path, "src/frob/pkg_b/mod.py", "def parse(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_parse.py",
            "def test_parse():\n    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset({"tests/test_parse.py::test_parse"}))
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        test014 = [v for v in violations if v.rule == "TEST014"]
        assert len(test014) == 1
        assert test014[0].severity == Severity.WARN
        assert "pkg_a/mod.py::parse" in test014[0].message
        assert "pkg_b/mod.py::parse" in test014[0].message

    # frob:ticket T-0547
    def test_silent_when_symbol_has_explicit_edge(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates.py::TestTest014AmbiguousConventionMatch.test_silent_when_symbol_has_explicit_edge  # noqa: E501
        # An explicit frob:tests edge on either colliding symbol removes it
        # from the ambiguous naming-convention pool entirely.
        from typani.option import Nothing

        _write(
            tmp_path,
            "src/frob/pkg_a/mod.py",
            '# frob:tests tests/test_parse.py::test_parse kind="unit"\n'
            "def parse(x):\n    return x\n",
        )
        _write(tmp_path, "src/frob/pkg_b/mod.py", "def parse(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_parse.py",
            "def test_parse():\n    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset({"tests/test_parse.py::test_parse"}))
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST014" not in _rules(violations)

    # frob:ticket T-0547
    def test_silent_when_no_leaf_name_collision(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates.py::TestTest014AmbiguousConventionMatch.test_silent_when_no_leaf_name_collision  # noqa: E501
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg_a/mod.py", "def parse(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_parse.py",
            "def test_parse():\n    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset({"tests/test_parse.py::test_parse"}))
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST014" not in _rules(violations)


# frob:ticket T-0548
class TestTest015VacuousCredit:
    """T-0548 (docs/audits/gates-accounting.md B1/E1): TEST001, the only
    blocking per-symbol test gate, is satisfied by a single collected test
    node id whose name matches -- nothing inspects whether it asserts
    anything. `def test_myfunc(): pass` clears TEST001 today; TEST015
    reuses T-0549's existing assertion heuristic to make that loud."""

    # frob:ticket T-0548
    def test_fires_on_no_op_test_body(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates.py::TestTest015VacuousCredit.test_fires_on_no_op_test_body  # noqa: E501
        # The audit's own repro: a public function whose only covering
        # test, matched by naming convention, has an empty (no-op) body.
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(tmp_path, "tests/test_helper.py", "def test_helper():\n    pass\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_helper.py::test_helper"})
        )
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        test015 = [v for v in violations if v.rule == "TEST015"]
        assert len(test015) == 1
        assert test015[0].severity == Severity.WARN
        assert "src/frob/pkg/a.py::helper" in test015[0].message
        assert "test_helper" in test015[0].message

    # frob:ticket T-0548
    def test_silent_when_any_matching_test_asserts(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates.py::TestTest015VacuousCredit.test_silent_when_any_matching_test_asserts  # noqa: E501
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_helper.py",
            "def test_helper():\n    assert helper_result() == 1\n"
            "def helper_result():\n    return 1\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_helper.py::test_helper"})
        )
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST015" not in _rules(violations)

    # frob:ticket T-0548
    def test_silent_when_no_test_matches_at_all(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates.py::TestTest015VacuousCredit.test_silent_when_no_test_matches_at_all  # noqa: E501
        # No matching test at all is TEST001's own job (already ERROR) --
        # TEST015 only concerns credit that WAS granted, so it must stay
        # silent here rather than double-report the same gap.
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST015" not in _rules(violations)
        assert "TEST001" in _rules(violations)


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


# frob:ticket T-0399
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

    # frob:ticket T-0399
    def test_dup_gate_fails_closed_when_enforced_but_core_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0399 (gates-quality audit finding 2): [dup].enforce=true with
        frob-core unavailable must emit a blocking DUP003 ERROR, not
        silently return no violations -- a requested-but-unavailable
        control fails CLOSED."""
        # frob:tests src/frob/gates/__init__.py::dup_gate
        import frob.dup as dup_module
        from frob.gates import dup_gate

        monkeypatch.setattr(dup_module, "core_available", lambda: False)
        _write(tmp_path, "src/a.py", "def foo():\n    return 1\n")
        _write(tmp_path, "frob.toml", "[dup]\nenforce = true\n")
        snap = _snapshot(tmp_path)
        diff = Diff(base="main", hunks=())
        violations = dup_gate(tmp_path, snap, diff)
        assert len(violations) == 1
        assert violations[0].rule == "DUP003"
        assert violations[0].severity == Severity.ERROR

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
    # T-0233: the frob:doc edge above must actually resolve, or COV001 now
    # correctly flags `documented` too.
    _write(tmp_path, "docs/pkg.md", "# Api\n")
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

    def test_sys004_names_stale_native_as_likely_remedy(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # T-0347 (T-0248 follow-up, T-0166 incident precedent): a `.strata`
        # load failure caused by a grammar-ahead-of-native mismatch must
        # name `make core` as the likely remedy, not just say "fix the
        # .strata file" -- that message alone sent a reviewer chasing a
        # nonexistent syntax error during T-0166.
        import frob.strata as strata_mod
        from frob.strata import StaleNative
        from frob.testing._models import NativeSpec

        _write(tmp_path, "design/bad.strata", "this is not valid strata {{{")
        _write(tmp_path, "src/a.py", "def f(): pass\n")
        fake_stale = StaleNative(
            spec=NativeSpec(name="strata_core", build_cmd="make core"),
            source_dir="strata-core",
            artifact_mtime=1.0,
            source_mtime=2.0,
        )
        monkeypatch.setattr(strata_mod, "stale_natives", lambda root: (fake_stale,))
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys004 = _by_rule(violations, "SYS004")
        assert len(sys004) == 1
        assert "make core" in sys004[0].message
        assert "strata_core" in sys004[0].message

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

    # frob:waive DUP001 reason="parallel test methods within test_gates.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
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

    # frob:waive DUP001 reason="parallel test methods within test_gates.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
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


_SELFAUDIT_DESIGN_STRATA_UNDECLARED = """module m
node widget : trusted { code "src/frob/widget/**"; }
"""


class TestSelfAuditGate:
    """T-0756 SELFAUDIT001: sys_gate's production entrypoint folds frob's
    own self-conformance (SYS100-102)/resource-contention (SYS2xx)/
    reliability (REL2xx) audit surface into the ordinary gate pipeline
    (docs/modules/gates.md#self-audit-at-land-selfaudit001-t-0756). Each test is written to
    prove the PRODUCTION invocation (`sys_gate`, the function `frob check`
    itself calls) actually fires SELFAUDIT001 -- not a direct call into
    `frob.strata.check_self_conformance`, which `tests/unit/strata/
    test_selfconform.py` already covers at the pure-function level."""

    # frob:tests src/frob/gates/__init__.py::sys_gate kind="unit"
    def test_selfaudit001_folds_selfconform_violation(self, tmp_path: Path) -> None:
        """GIVEN a node declaring a `code=` glob over a file that exercises
        a capability (`requests.get`, net) with NO matching `may`
        declaration, WHEN `sys_gate` (the production `frob check` entry
        point) runs THEN it FAILS with an unwaived SELFAUDIT001 ERROR
        naming the underlying SYS100 finding -- proving the fold actually
        fires through production, not just through `check_self_
        conformance` called directly."""
        _write(tmp_path, "design/m.strata", _SELFAUDIT_DESIGN_STRATA_UNDECLARED)
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        selfaudit = _by_rule(violations, "SELFAUDIT001")
        assert len(selfaudit) >= 1
        assert selfaudit[0].severity == Severity.ERROR
        assert "SYS100" in selfaudit[0].message
        assert "widget" in selfaudit[0].message

    # frob:tests src/frob/gates/__init__.py::sys_gate kind="unit"
    def test_selfaudit001_clean_model_no_violations(self, tmp_path: Path) -> None:
        """GIVEN a design model whose declared `may` capabilities are
        exactly what the bound code exercises WHEN `sys_gate` runs THEN it
        PASSES with zero SELFAUDIT001 findings -- the after-fix half of the
        same before/after fixture proof."""
        design = (
            "module m\n"
            'node widget : trusted { code "src/frob/widget/**"; may "net"; }\n'
        )
        _write(tmp_path, "design/m.strata", design)
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        assert _by_rule(violations, "SELFAUDIT001") == []

    # frob:tests src/frob/gates/__init__.py::sys_gate kind="unit"
    def test_selfaudit001_suppressed_on_design_load_error(self, tmp_path: Path) -> None:
        """A `.strata` file that fails to parse suppresses SELFAUDIT001
        entirely (matches DOC003/SYS001's suppression posture) -- a broken
        model cannot be honestly self-audited."""
        _write(tmp_path, "design/m.strata", "module m\nnode !!! broken\n")
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        assert _by_rule(violations, "SELFAUDIT001") == []
        assert _by_rule(violations, "SYS004") != []


def _complex_function_source(fn_name: str) -> str:
    """A python module with one function long enough to trip the 30-line
    default `max_function_lines` but short enough to stay under the
    calibrated 60-line threshold (T-0373), and structurally complex enough
    (>=8 branches) to pass `_py_is_complex`'s cyclomatic-proxy filter."""
    lines = [f"def {fn_name}(cfg):", "    result = {}"]
    for i in range(8):
        lines.append(f'    if cfg.get("flag_{i}"):')
        lines.append(f'        result["k{i}"] = {i}')
    for i in range(20):
        lines.append(f'    step_{i} = cfg.get("step_{i}", "default")')
    lines.append("    return result, " + ", ".join(f"step_{i}" for i in range(20)))
    return "\n".join(lines) + "\n"


class TestArchGateThresholds:
    """T-0373: arch_gate reads its long-function threshold from frob.toml's
    [arch] table (via frob.app.config.load_arch_config) instead of always
    using frob.arch.analyze_project's own conservative 30-line default."""

    def test_arch_gate_uses_calibrated_default_not_library_default(
        self, tmp_path: Path
    ) -> None:
        """No frob.toml at all: `frob.arch.analyze_project`'s own bare
        30-line default still flags the ~39-line complex function, but
        `arch_gate` -- which threads `load_arch_config`'s calibrated
        60-line default through -- does not. Proof the gate no longer
        silently uses `analyze_project`'s conservative defaults."""
        from frob.arch import analyze_project
        from frob.gates._arch import arch_gate

        _write(tmp_path, "src/mod.py", _complex_function_source("do_work"))

        raw_result = analyze_project(tmp_path / "src")
        assert "long-function" in {s.category for s in raw_result.suggestions}

        violations = arch_gate(tmp_path)
        assert not _by_rule(violations, "ARCH001")

    def test_arch001_respects_explicit_frob_toml_override(self, tmp_path: Path) -> None:
        """A frob.toml [arch] max_function_lines=20 override (well below
        both the library's 30-line default and the calibrated 60-line
        default) still fires ARCH001 -- proof arch_gate actually reads
        frob.toml, not just a hardcoded calibrated constant."""
        from frob.gates._arch import arch_gate

        _write(tmp_path, "src/mod.py", _complex_function_source("do_work"))
        _write(tmp_path, "frob.toml", "[arch]\nmax_function_lines = 20\n")
        violations = arch_gate(tmp_path)
        assert _by_rule(violations, "ARCH001")


class TestGateOrderSetEquality:
    """T-0438/T-0839: `_CANONICAL_GATE_ORDER` (T-0415's deterministic merge
    order) and `_ALL_GATES` (the set of every selectable gate name) must
    name the exact same gates. If a new gate is added to one but not the
    other, a gate could silently drop from `frob check` output (missing
    from the canonical order means it never gets merged back in) or
    `run_gates` could reject a gate name that was never made orderable --
    either way a quiet accounting bug, not a loud one, without this
    set-equality pin. T-0839 splits the single set-equality assertion into
    both drift directions individually so a failure names exactly which
    side drifted, and adds `_merge_canonical_order`'s own loud-failure
    behavior alongside it."""

    def test_canonical_gate_order_matches_all_gates(self) -> None:
        # frob:tests src/frob/gates/__init__.py::_merge_canonical_order
        # (the consumer of _CANONICAL_GATE_ORDER whose correctness this
        # set-equality invariant protects; the two constants are module-level
        # data the graph does not track as symbols, so bind to the function)
        # frob:waive COV006 reason="T-0525: module-level constant set-equality, never \
        # a call to _merge_canonical_order -- same \
        # sound-but-invisible-to-the-call-graph shape as \
        # TestProcessPoolGates.test_process_job_runs_in_a_separate_process above; \
        # symbol-exact now (T-0525), so this waiver covers only this test's own edge"
        from frob.gates import _ALL_GATES, _CANONICAL_GATE_ORDER

        assert set(_CANONICAL_GATE_ORDER) == _ALL_GATES, (
            "_CANONICAL_GATE_ORDER and _ALL_GATES have drifted apart -- "
            "every gate in _ALL_GATES must appear exactly once in "
            "_CANONICAL_GATE_ORDER so merge order stays deterministic and "
            "no gate silently drops from frob check output"
        )
        assert len(_CANONICAL_GATE_ORDER) == len(set(_CANONICAL_GATE_ORDER)), (
            "_CANONICAL_GATE_ORDER contains a duplicate gate name"
        )

    def test_all_gates_is_subset_of_canonical_order(self) -> None:
        # frob:tests src/frob/gates/__init__.py::_merge_canonical_order
        # frob:waive COV006 reason="T-0525: module-level constant set-difference, \
        # never a call to _merge_canonical_order -- same shape as \
        # test_canonical_gate_order_matches_all_gates above, symbol-exact so this \
        # waiver covers only this test's own edge"
        """T-0839 drift direction 1: every gate in `_ALL_GATES` (selectable,
        can produce real violations) must appear in `_CANONICAL_GATE_ORDER`
        -- this is exactly the T-0788 "compliance" incident: a gate added to
        `_ALL_GATES` but never added to the order tuple, whose findings
        `_merge_canonical_order` would silently drop."""
        from frob.gates import _ALL_GATES, _CANONICAL_GATE_ORDER

        missing_from_order = _ALL_GATES - set(_CANONICAL_GATE_ORDER)
        assert not missing_from_order, (
            f"gate(s) {sorted(missing_from_order)} are in _ALL_GATES but "
            "missing from _CANONICAL_GATE_ORDER -- their violations would "
            "be silently dropped from frob check output"
        )

    def test_canonical_order_names_no_nonexistent_gate(self) -> None:
        """T-0839 drift direction 2: every gate named in
        `_CANONICAL_GATE_ORDER` must actually exist in `_ALL_GATES` -- a
        stale/typo'd order entry naming a gate nothing ever registers is a
        harmless no-op today, but a silent one, and the inverse drift of
        the T-0788 incident.
        # frob:tests src/frob/gates/__init__.py::_merge_canonical_order
        """
        from frob.gates import _ALL_GATES, _CANONICAL_GATE_ORDER

        nonexistent = set(_CANONICAL_GATE_ORDER) - _ALL_GATES
        assert not nonexistent, (
            f"gate(s) {sorted(nonexistent)} are named in "
            "_CANONICAL_GATE_ORDER but do not exist in _ALL_GATES -- remove "
            "the stale entry or register the gate"
        )


class TestMergeCanonicalOrder:
    """T-0839: `_merge_canonical_order` must raise loudly on a gate name it
    cannot place, rather than silently dropping that gate's violations --
    the failure mode hit live when T-0788's "compliance" gate was briefly
    absent from `_CANONICAL_GATE_ORDER`."""

    @staticmethod
    def _violation(rule: str) -> Violation:
        return Violation(
            rule=rule,
            severity=Severity.ERROR,
            file="src/example.py",
            line=1,
            message=f"{rule}: synthetic test violation",
        )

    def test_unknown_gate_key_raises_with_name(self) -> None:
        # frob:tests src/frob/gates/__init__.py::_merge_canonical_order
        from frob.gates import GateOrderDriftError, _merge_canonical_order

        raw: dict[str, tuple[Violation, ...]] = {
            "not_a_real_gate": (self._violation("FAKE001"),)
        }
        with pytest.raises(GateOrderDriftError) as exc_info:
            _merge_canonical_order(raw)
        assert "not_a_real_gate" in str(exc_info.value)

    def test_all_current_gates_merge_without_raising(self) -> None:
        """Every name in `_ALL_GATES` must merge cleanly today -- this is
        the regression guard for the T-0788 incident itself: had this test
        existed then, it would have failed the moment "compliance" was
        added to `_ALL_GATES` without a matching order-tuple entry."""
        # frob:tests src/frob/gates/__init__.py::_merge_canonical_order
        from frob.gates import _ALL_GATES, _merge_canonical_order

        raw: dict[str, tuple[Violation, ...]] = {
            name: (self._violation("SYN001"),) for name in _ALL_GATES
        }
        merged = _merge_canonical_order(raw)
        assert len(merged) == len(_ALL_GATES)


class TestDoc004ConsoleCommandDrift:
    """T-0443: DOC004's console/bash `<prog> <subcommand>` tier is driven
    entirely by `frob.toml`'s `[[docblocks.commands]]` array -- `prog` plus
    a `module:callable` dotted path to an `argparse.ArgumentParser` factory
    this gate imports and walks at check time. No frob-specific subcommand
    list is hardcoded anywhere in `frob.gates._docblocks`; these tests use
    frob's OWN real CLI factory (`frob.__main__:_build_parser`) as the
    configured source, proving the tier derives from the live registry
    rather than a second, hand-maintained copy of it."""

    _CONFIG = (
        '[[docblocks.commands]]\nprog = "frob"\n'
        'parser = "frob.__main__:_build_parser"\n'
    )

    def test_nonexistent_subcommand_is_stale(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", self._CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            "```console\n$ frob nonexistent-subcommand --flag\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        stale = _by_rule(violations, "DOC004")
        assert stale
        assert any(
            v.severity == Severity.ERROR and "nonexistent-subcommand" in v.message
            for v in stale
        )

    def test_real_subcommand_anchored_passes(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", self._CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            "<!-- frob:doc docs/guide.md -->\n\n"
            "```console\n$ frob check --delta\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert all(v.severity != Severity.ERROR for v in _by_rule(violations, "DOC004"))

    def test_real_subcommand_unanchored_warns_unbound(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", self._CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            "```console\n$ frob check --delta\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        warned = _by_rule(violations, "DOC004")
        assert warned
        assert all(v.severity == Severity.WARN for v in warned)

    def test_waive_suppresses_console_stale(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", self._CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            '<!-- frob:waive DOC004 reason="illustrative, not real" -->\n\n'
            "```console\n$ frob nonexistent-subcommand\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _by_rule(violations, "DOC004") == []

    def test_no_config_means_no_console_checking(self, tmp_path: Path) -> None:
        """No `[[docblocks.commands]]` entries at all -- fail-open, same
        posture as every other namespace source in this module: a project
        that has not opted in gets zero console/bash checking, never a
        crash on a plain shell example."""
        _git_init(tmp_path)
        _write(
            tmp_path,
            "docs/guide.md",
            "```console\n$ frob nonexistent-subcommand\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _by_rule(violations, "DOC004") == []


# frob:ticket T-0499
# frob:ticket T-0972
class TestKnownGateRuleIds:
    """`known_gate_rule_ids()` is the public accessor strata's
    `caught_by` verification (THREAT006/COMPLIANCE004) needs to resolve
    rule-id-shaped references against; production callsites (T-0499)
    thread it in instead of silently defaulting to empty."""

    def test_returns_known_rule_id(self) -> None:
        """A real, stable gate rule id is present in the returned set."""
        assert "SEC001" in known_gate_rule_ids()

    def test_is_frozenset(self) -> None:
        """Return type is an immutable frozenset, not a mutable copy a
        caller could accidentally mutate shared state through."""
        assert isinstance(known_gate_rule_ids(), frozenset)

    # frob:ticket T-0924
    # T-0924: paid the allowlist down to empty -- every id T-0901 carried
    # here (COMPLIANCE001-004/HOST001/HOST002/HOST-BLAST/KRB001-004/
    # LINT001-005/PII001-004/RELWAIVE002/THREAT001-005) is now registered
    # in `_KNOWN_GATE_RULES` instead, so the drift-lock below actually
    # guards this batch rather than exempting it. PARSE002 (landed on main
    # concurrently with this pass) was folded straight into
    # `_KNOWN_GATE_RULES` instead of parked here, since it is exactly this
    # ticket's own defect class.
    #
    # frob:ticket T-0964
    # frob:ticket T-0966
    # T-0964 extended the drift-lock below to also resolve `rule=
    # CONST_NAME` references (not just inline `rule="..."` literals),
    # which surfaced a real, pre-existing gap: SYS100-102/SYS200-203 were
    # genuinely emitted via module-level constants in _selfconform.py/
    # _contention.py but were not yet added to `_KNOWN_GATE_RULES`. T-0966
    # added all seven entries there.
    #
    # frob:ticket T-1010
    # T-1010 inverted this registry: the scan itself (previously
    # duplicated inline here) is now importable production code
    # (`frob.gates._rule_id_scan`), and `_KNOWN_GATE_RULES` is the
    # generated-and-verified artifact it derives from. The former
    # `_KNOWN_ISSUE_ALLOWLIST` (an ad hoc "not yet registered" parking
    # lot, always empty in practice once the two historical batches above
    # were paid down) is retired in favor of `_rule_id_scan.
    # RETIRED_RULE_IDS`, which excludes ids at the SOURCE of generation
    # instead of at the point of comparison -- one manual knob, not two.
    # This test is now a generator-freshness check, not a hand-rolled scan.

    # frob:ticket T-0901
    # frob:ticket T-0924
    # frob:ticket T-0964
    # frob:ticket T-0972
    # frob:ticket T-1010
    # frob:tests \
    # tests/test_gates.py::TestKnownGateRuleIds.test_every_emitted_rule_literal_is_known
    def test_every_emitted_rule_literal_is_known(self) -> None:
        """Generator-freshness drift-lock (T-1010, inverting the T-0964
        scan): every rule id `frob.gates._rule_id_scan.
        generated_gate_rule_ids()` reports live -- every `rule="..."`/
        `rule=CONST_NAME` construction under `_rule_id_scan.SCANNED_BASES`,
        minus `_rule_id_scan.RETIRED_RULE_IDS` -- must be a member of
        `known_gate_rule_ids()`. A gate/rule added without a matching
        `_KNOWN_GATE_RULES` entry fails loud immediately instead of
        silently reproducing the PARSE001/TICK005/REG011/PII011/PII012/
        SYSWAIVE002/THREAT006/PROTO004/DEC000 omission class (T-0903/
        T-0923/T-0901), including the T-0964 variant where the id is only
        ever referenced via a module-level constant rather than an inline
        literal."""
        repo_root = Path(__file__).resolve().parents[1]
        generated = generated_gate_rule_ids(repo_root)
        known = known_gate_rule_ids()
        found = scan_emitted_rule_ids(repo_root)
        unknown = {
            rule_id: found[rule_id] for rule_id in generated if rule_id not in known
        }
        assert not unknown, (
            "rule id(s) constructed in src/frob/gates or src/frob/strata "
            "but missing from _KNOWN_GATE_RULES (paste in the entry "
            "frob.gates._rule_id_scan.generated_gate_rule_ids() now "
            f"reports): {unknown}"
        )

    # frob:ticket T-1010
    # frob:tests \
    # tests/test_gates.py::TestKnownGateRuleIds.test_scan_finds_a_synthetic_rule_id
    def test_scan_finds_a_synthetic_rule_id(self, tmp_path: Path) -> None:
        """A fresh gate emitting a rule id via an inline `rule="..."`
        literal is picked up by `scan_emitted_rule_ids` with no hand edit
        to any registry -- the acceptance shape T-1010 exists to
        guarantee."""
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "_synthetic.py").write_text(
            'def synthetic_gate():\n    return Violation(rule="ZZZTEST001")\n'
        )

        found = scan_emitted_rule_ids(tmp_path)

        assert "ZZZTEST001" in found
        assert found["ZZZTEST001"] == "src/frob/gates/_synthetic.py:2"

    # frob:ticket T-1010
    # frob:tests \
    # tests/test_gates.py::TestKnownGateRuleIds.test_scan_resolves_const_name_reference
    def test_scan_resolves_const_name_reference(self, tmp_path: Path) -> None:
        """A `rule=CONST_NAME` reference resolved against a module-level
        `CONST_NAME = "RULE123"` assignment -- the T-0964 class this
        scanner must keep covering, not just inline literals."""
        strata_dir = tmp_path / "src" / "frob" / "strata"
        strata_dir.mkdir(parents=True)
        (strata_dir / "_synthetic.py").write_text(
            'ZZZ_CONST = "ZZZTEST002"\n\n\ndef synthetic_gate():\n'
            "    return Violation(rule=ZZZ_CONST)\n"
        )

        found = scan_emitted_rule_ids(tmp_path)

        assert found.get("ZZZTEST002") == "src/frob/strata/_synthetic.py:5"

    # frob:ticket T-1010
    # frob:tests \
    # tests/test_gates.py::TestKnownGateRuleIds.test_retired_id_stays_excluded
    def test_retired_id_stays_excluded(self, tmp_path: Path) -> None:
        """An id on the retired list stays out of
        `generated_gate_rule_ids()`'s output even though the scan itself
        would otherwise find it -- the one manual exclusion knob T-1010
        leaves in place."""
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "_synthetic.py").write_text(
            'def synthetic_gate():\n    return Violation(rule="ZZZTEST003")\n'
        )

        found = scan_emitted_rule_ids(tmp_path)
        assert "ZZZTEST003" in found

        generated = generated_gate_rule_ids(tmp_path, retired=frozenset({"ZZZTEST003"}))

        assert "ZZZTEST003" not in generated


# frob:ticket T-0459
class TestRenderLintGate:
    """RENDER001: bare stdout write outside frob.render
    (docs/modules/render.md#renderer)."""

    def _init_repo(self, tmp_path: Path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)

    def _commit(self, tmp_path: Path) -> None:
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-qm", "c"], cwd=tmp_path, check=True)

    # frob:tests tests/test_gates.py::TestRenderLintGate.test_bare_print_fires
    def test_bare_print_fires(self, tmp_path: Path) -> None:
        """A bare `print(...)` in a runner-shaped file fires RENDER001."""
        from frob.gates._render_lint import render_lint_gate

        self._init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob" / "app"
        pkg.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "offender_runner.py").write_text("def run():\n    print('hello')\n")
        self._commit(tmp_path)

        violations = render_lint_gate(tmp_path)

        hits = _by_rule(violations, "RENDER001")
        offender_hits = [v for v in hits if v.file == "src/frob/app/offender_runner.py"]
        assert len(offender_hits) == 1
        assert offender_hits[0].line == 2

    # frob:tests tests/test_gates.py::TestRenderLintGate.test_render_package_exempt
    def test_render_package_exempt(self, tmp_path: Path) -> None:
        """`src/frob/render/` itself is the one sanctioned home for these
        calls (`Renderer._emit`'s own `print`) and is never scanned."""
        from frob.gates._render_lint import render_lint_gate

        self._init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob" / "render"
        pkg.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "_renderer.py").write_text(
            "def _emit(line, stream):\n    print(line, file=stream)\n"
        )
        self._commit(tmp_path)

        violations = render_lint_gate(tmp_path)

        assert _by_rule(violations, "RENDER001") == []

    # frob:tests tests/test_gates.py::TestRenderLintGate.test_stderr_directed_print_is_silent  # noqa: E501
    def test_stderr_directed_print_is_silent(self, tmp_path: Path) -> None:
        """A `print(..., file=sys.stderr)` call is never flagged --
        INV-RENDER-SOLE-STDOUT governs stdout only."""
        from frob.gates._render_lint import render_lint_gate

        self._init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob" / "app"
        pkg.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "offender_runner.py").write_text(
            "import sys\n\n\ndef run():\n    print('oops', file=sys.stderr)\n"
        )
        self._commit(tmp_path)

        violations = render_lint_gate(tmp_path)

        assert _by_rule(violations, "RENDER001") == []

    # frob:tests tests/test_gates.py::TestRenderLintGate.test_unparseable_file_fires_parse001  # noqa: E501
    # frob:ticket T-0897
    def test_unparseable_file_fires_parse001(self, tmp_path: Path) -> None:
        """A file with a Python syntax error fires PARSE001 instead of
        being silently dropped from the scan with zero Violation (T-0897)."""
        from frob.gates._render_lint import render_lint_gate

        self._init_repo(tmp_path)
        pkg = tmp_path / "src" / "frob" / "app"
        pkg.mkdir(parents=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "broken_runner.py").write_text("def run(:\n    pass\n")
        self._commit(tmp_path)

        violations = render_lint_gate(tmp_path)

        hits = _by_rule(violations, "PARSE001")
        offender_hits = [v for v in hits if v.file == "src/frob/app/broken_runner.py"]
        assert len(offender_hits) == 1
        assert offender_hits[0].severity == Severity.ERROR


# frob:ticket T-0726
class TestTick006PhantomFiling:
    """TICK006 (T-0726): a Done report's affirmative "filed" claim whose
    id resolves to no ledger block, distinguished from prose that merely
    mentions another ticket's id and from explicit filing negations."""

    def _queue(self, *tickets: Ticket) -> TicketQueue:
        """A `TicketQueue` of `tickets`, keyed by id."""
        return TicketQueue(tickets={t.id: t for t in tickets})

    # frob:tests tests/test_gates.py::TestTick006PhantomFiling.test_phantom_filed_colon_fires  # noqa: E501
    def test_phantom_filed_colon_fires(self, tmp_path: Path) -> None:
        """`Filed: T-draft-deadbeef` (a real T-0726/T-0577-class draft-loss
        shape) resolving to no block, active or archived, is TICK006."""
        ticket = _ticket(
            ticket_id="T-0001",
            body=(
                "## Description\nsome bug\n\n"
                "## Done report\n\n"
                "Filed: `T-draft-deadbeef` (a follow-up bug, scope foo.py "
                "-- renumbers to a real T-#### id when this worktree "
                "merges to main).\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick006 = [v for v in violations if v.rule == "TICK006"]
        assert len(tick006) == 1
        assert "T-draft-deadbeef" in tick006[0].message
        assert tick006[0].severity == Severity.ERROR

    # frob:tests tests/test_gates.py::TestTick006PhantomFiling.test_phantom_filed_as_fires  # noqa: E501
    def test_phantom_filed_as_fires(self, tmp_path: Path) -> None:
        """The T-0707 incident class: `filed as T-0999` where T-0999 was
        never actually filed anywhere -- an invented filing trail."""
        ticket = _ticket(
            ticket_id="T-0002",
            body=(
                "## Done report\n\n"
                "The out-of-scope discovery above was filed as T-0999 "
                "(never actually created).\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick006 = [v for v in violations if v.rule == "TICK006"]
        assert len(tick006) == 1
        assert "T-0999" in tick006[0].message

    # frob:tests tests/test_gates.py::TestTick006PhantomFiling.test_filed_colon_real_active_id_is_silent  # noqa: E501
    def test_filed_colon_real_active_id_is_silent(self, tmp_path: Path) -> None:
        """`Filed: T-0003` where T-0003 is a real block in the ACTIVE
        queue does not fire -- this is exactly what a correct filing
        claim looks like."""
        followup = _ticket(ticket_id="T-0003", body="## Description\nx\n")
        # Real Done-report grammar, verbatim shape from tickets-archive.md
        # (T-0077's own Done report): "Filed: T-0129 (wire `.strata`
        # into frob.graph/outline/... -- out of T-0077's scope)."
        reporter = _ticket(
            ticket_id="T-0004",
            body=(
                "## Done report\n\n"
                "Filed: T-0003 (wire `.strata` into frob.graph/outline/"
                "xref/testing/policy/cycle_runner/arch's raw_tree call so "
                "map/outline/xref/COV obligations reach `.strata` symbols "
                "end to end -- out of T-0004's scope).\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(followup, reporter))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/test_gates.py::TestTick006PhantomFiling.test_filed_colon_none_is_silent  # noqa: E501
    def test_filed_colon_none_is_silent(self, tmp_path: Path) -> None:
        """`Filed: none` -- the common "nothing to file" Done-report
        shape -- names no id at all and must never fire."""
        ticket = _ticket(
            ticket_id="T-0005",
            body=(
                "## Done report\n\n"
                "Filed: none (no out-of-scope work found; the change was "
                "entirely inside T-0005's declared scope).\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/test_gates.py::TestTick006PhantomFiling.test_filed_as_real_archived_id_is_silent  # noqa: E501
    def test_filed_as_real_archived_id_is_silent(self, tmp_path: Path) -> None:
        """`filed as **T-0137**` resolves against `tickets-archive.md`,
        not only the active queue -- an id archived long ago is still a
        real filing, never a phantom."""
        from frob.tickets._store import write_archive

        archived = _ticket(ticket_id="T-0137", body="## Description\narchived\n")
        write_archive(tmp_path, {"T-0137": archived}).danger_ok
        ticket = _ticket(
            ticket_id="T-0006",
            body=(
                "## Done report\n\n"
                "`strata-core/**` is outside this ticket's scope, so this "
                "was filed as **T-0137** rather than patched around.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/test_gates.py::TestTick006PhantomFiling.test_negation_not_filed_is_silent  # noqa: E501
    def test_negation_not_filed_is_silent(self, tmp_path: Path) -> None:
        """ "not filed as a new ticket" (verbatim phrase used repeatedly in
        this repo's ledger) is an explicit negation and must never fire,
        even when a phantom-shaped id sits nearby in the same sentence."""
        ticket = _ticket(
            ticket_id="T-0007",
            body=(
                "## Done report\n\n"
                "That is out of T-0007's scope; not filed as a new ticket "
                "this pass because the discovery T-draft-deadbeef "
                "duplicates existing tracked work.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/test_gates.py::TestTick006PhantomFiling.test_negation_no_ticket_filed_is_silent  # noqa: E501
    def test_negation_no_ticket_filed_is_silent(self, tmp_path: Path) -> None:
        """ "no new ticket filed" is an explicit negation and must never
        fire."""
        ticket = _ticket(
            ticket_id="T-0008",
            body=(
                "## Done report\n\n"
                "Tracked under T-0008's own pattern (no new ticket filed; "
                "T-draft-deadbeef is only a scratch note, not a real id).\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/test_gates.py::TestTick006PhantomFiling.test_description_prose_mentioning_other_ticket_is_silent  # noqa: E501
    def test_description_prose_mentioning_other_ticket_is_silent(
        self, tmp_path: Path
    ) -> None:
        """Ordinary narrative in a ticket's Description -- BEFORE any Done
        report heading -- routinely names another (possibly phantom-
        shaped) ticket id in prose; this is extremely common and must
        never fire, since it is not a filing claim about this ticket's
        own work at all."""
        ticket = _ticket(
            ticket_id="T-0009",
            body=(
                "## Description\n\n"
                "NOTE: T-0570's Done report references this as "
                "T-draft-1327a057 (and mislabels it as T-0571); the draft "
                "did not survive land, so this ticket is its real "
                "replacement.\n\n"
                "## Done report\n\nFiled: none.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/test_gates.py::TestTick006PhantomFiling.test_no_done_report_heading_is_silent  # noqa: E501
    def test_no_done_report_heading_is_silent(self, tmp_path: Path) -> None:
        """A ticket with no Done report at all (still in progress) has
        nothing for TICK006 to scan, regardless of what its Description
        says."""
        ticket = _ticket(
            ticket_id="T-0010",
            state=TicketState.IN_PROGRESS,
            body="## Description\nFiled: T-draft-deadbeef (not real).\n",
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK006" for v in violations)

    # frob:tests tests/test_gates.py::TestTick006PhantomFiling.test_filed_bare_draft_without_colon_fires  # noqa: E501
    def test_filed_bare_draft_without_colon_fires(self, tmp_path: Path) -> None:
        """The T-0577 draft-loss shape: `Filed T-draft-<hex> (mints a real
        T-#### id at land)` with no colon after "Filed" -- a real filing
        grammar used repeatedly in this ledger -- still fires when the
        draft never survived land, since that is TICK006's whole point
        (a currently-unresolvable phantom, to be waived per-instance if
        it is a disclosed historical draft-loss case)."""
        ticket = _ticket(
            ticket_id="T-0011",
            body=(
                "## Done report\n\n"
                "Filed T-draft-deadbeef (mints a real T-#### id at land) "
                "for a follow-up entity kind.\n"
            ),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick006 = [v for v in violations if v.rule == "TICK006"]
        assert len(tick006) == 1
        assert "T-draft-deadbeef" in tick006[0].message


# frob:ticket T-0820
class TestTick007UndispatchedStale:
    """TICK007 (T-0820): the `frob check` half of T-0752's undispatched-
    stale-CRITICAL/HIGH alarm -- `tickets_gate` reuses
    `frob.tickets.undispatched_stale` verbatim over the dispatchable
    (unblocked, unleased) set and WARNs per alarmed ticket, mirroring
    `frob ticket doable`'s UNDISPATCHED row marker as a mechanical gate
    finding instead of a display-only nicety."""

    # frob:ticket T-0820
    def _queue(self, *tickets: Ticket) -> TicketQueue:
        """A `TicketQueue` of `tickets`, keyed by id."""
        return TicketQueue(tickets={t.id: t for t in tickets})

    # frob:ticket T-0820
    def _priority_ticket(
        self,
        *,
        ticket_id: str,
        priority: Priority,
        created: date,
        state: TicketState = TicketState.QUEUED,
        blocked_by: tuple[str, ...] = (),
    ) -> Ticket:
        """A minimal queued `Ticket` at `priority`/`created`, optionally
        `blocked_by` an id, no scope -- the shape `undispatched_stale`
        needs, with every other field defaulted the same way
        `test_tickets_priority.py`'s `_ticket` helper does. `Ticket` is
        frozen (`model_config = ConfigDict(frozen=True, ...)`), so
        `blocked_by` must be set here, not assigned after construction."""
        return Ticket(
            id=ticket_id,
            title=f"ticket {ticket_id}",
            state=state,
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            created=created,
            priority=priority,
            blocked_by=blocked_by,
            parent=None,
            scope=(),
            evidence=(),
            attachments=(),
            acceptance=(),
            threat=None,
            body="",
        )

    # frob:ticket T-0820
    # frob:tests tests/test_gates.py::TestTick007UndispatchedStale.test_stale_critical_fires  # noqa: E501
    def test_stale_critical_fires(self, tmp_path: Path) -> None:
        """A CRITICAL ticket filed long ago (far past the 4h default
        threshold), still queued and unblocked, is TICK007."""
        ticket = self._priority_ticket(
            ticket_id="T-4001",
            priority=Priority.CRITICAL,
            created=date(2026, 1, 1),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick007 = [v for v in violations if v.rule == "TICK007"]
        assert len(tick007) == 1
        assert "T-4001" in tick007[0].message
        assert tick007[0].severity == Severity.WARN

    # frob:ticket T-0820
    # frob:tests tests/test_gates.py::TestTick007UndispatchedStale.test_fresh_critical_is_silent  # noqa: E501
    def test_fresh_critical_is_silent(self, tmp_path: Path) -> None:
        """A CRITICAL ticket filed today has not crossed the 4h threshold
        yet (whole-day granularity means same-day is 0h elapsed) -- no
        TICK007."""
        ticket = self._priority_ticket(
            ticket_id="T-4002",
            priority=Priority.CRITICAL,
            created=date.today(),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK007" for v in violations)

    # frob:ticket T-0820
    # frob:tests tests/test_gates.py::TestTick007UndispatchedStale.test_medium_priority_never_fires  # noqa: E501
    def test_medium_priority_never_fires(self, tmp_path: Path) -> None:
        """MEDIUM/LOW carry no default threshold (T-0752: "a queue always
        has some") -- an ancient MEDIUM ticket never alarms TICK007."""
        ticket = self._priority_ticket(
            ticket_id="T-4003",
            priority=Priority.MEDIUM,
            created=date(2020, 1, 1),
        )
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK007" for v in violations)

    # frob:ticket T-0820
    # frob:tests tests/test_gates.py::TestTick007UndispatchedStale.test_blocked_ticket_is_silent  # noqa: E501
    def test_blocked_ticket_is_silent(self, tmp_path: Path) -> None:
        """A CRITICAL ticket blocked on an open blocker is not in the
        dispatchable set at all (`doable()` excludes it), so it never
        reaches `undispatched_stale` and cannot fire TICK007."""
        blocker = self._priority_ticket(
            ticket_id="T-4004",
            priority=Priority.HIGH,
            created=date(2026, 1, 1),
        )
        blocked = self._priority_ticket(
            ticket_id="T-4005",
            priority=Priority.CRITICAL,
            created=date(2026, 1, 1),
            blocked_by=(blocker.id,),
        )
        violations = tickets_gate(tmp_path, self._queue(blocker, blocked))
        tick007 = [v for v in violations if v.rule == "TICK007"]
        assert not any("T-4005" in v.message for v in tick007)

    # frob:ticket T-0820
    # frob:tests tests/test_gates.py::TestTick007UndispatchedStale.test_real_repo_scan_runs_end_to_end_without_crashing  # noqa: E501
    def test_real_repo_scan_runs_end_to_end_without_crashing(self) -> None:
        """The honest "real repo scan" smoke test (T-0813 precedent): runs
        `tickets_gate` over this repo's OWN live `tickets.md`, not a
        fabricated fixture, and just proves TICK007's `doable()` +
        `has_live_lease()` + `undispatched_stale()` plumbing completes
        without crashing against real ticket data (blockers, leases,
        scopes, every priority) -- it deliberately does NOT assert
        fires-or-not, since the live queue's staleness state churns
        between sessions (a CRITICAL/HIGH ticket dispatched an hour before
        this test runs vs. one left sitting are both legitimate states);
        every violation, if any, must simply carry the TICK007 rule id and
        a WARN severity."""
        from frob.tickets import load_queue

        root = Path(__file__).resolve().parents[1]
        queue = load_queue(root).danger_ok
        violations = tickets_gate(root, queue)
        tick007 = [v for v in violations if v.rule == "TICK007"]
        for v in tick007:
            assert v.severity == Severity.WARN
            assert v.rule == "TICK007"


# frob:ticket T-0842
class TestTick008UnknownLedgerFields:
    """TICK008 (T-0842): the T-0838 typo-hazard follow-up -- a ticket
    carrying unknown/extra ledger field(s) (`extra="allow"` captured them
    into `__pydantic_extra__` instead of hard-failing `MalformedFrontmatter`)
    must be a mechanical `frob check` finding on the checked ledger, not
    just a WARNING log line nothing gates on. WARN severity, not ERROR --
    an initial ERROR pass was rejected in adversarial review: `frob ticket
    land`'s claim re-verification spawns `frob check` from the ROOT
    checkout's OLD `src` tree (playbook section 2), so while a schema-
    extending ticket is itself landing, root's stale `Ticket` model
    captures that ticket's own new field as an extra and an ERROR would
    red the land via `ClaimDivergence` -- a `frob:waive` cannot route
    around it either, since the same stale binary evaluates the waiver.
    See `_tick008_unknown_ledger_fields`'s docstring for the full trace."""

    def _queue(self, *tickets: Ticket) -> TicketQueue:
        """A `TicketQueue` of `tickets`, keyed by id."""
        return TicketQueue(tickets={t.id: t for t in tickets})

    def _ticket_with_extra(self, ticket_id: str, **extra: object) -> Ticket:
        """A minimal valid `Ticket` plus arbitrary unknown `extra` fields --
        `Ticket.model_config` is `extra="allow"`, so these land in
        `__pydantic_extra__` rather than raising. Goes through
        `model_validate` (a single `dict[str, object]` argument) rather than
        keyword-splatting into the constructor, so the mypy/ty-visible
        signature stays exact for every known field."""
        data: dict[str, object] = {
            "id": ticket_id,
            "title": f"ticket {ticket_id}",
            "state": TicketState.QUEUED,
            "kind": TicketKind.FEATURE,
            "origin": Origin.HUMAN,
            "created": date(2026, 1, 1),
            **extra,
        }
        return Ticket.model_validate(data)

    # frob:tests tests/test_gates.py::TestTick008UnknownLedgerFields.test_fires_on_unknown_field  # noqa: E501
    def test_fires_on_unknown_field(self, tmp_path: Path) -> None:
        """A ticket with a genuinely unknown field fires TICK008, naming
        both the ticket id and the unknown field, at WARN (not ERROR --
        see the class docstring for why ERROR was rejected)."""
        ticket = self._ticket_with_extra("T-9001", not_a_real_field="x")
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick008 = _by_rule(violations, "TICK008")
        assert len(tick008) == 1
        assert "T-9001" in tick008[0].message
        assert "not_a_real_field" in tick008[0].message
        assert tick008[0].severity == Severity.WARN

    # frob:tests tests/test_gates.py::TestTick008UnknownLedgerFields.test_fuzzy_hint_on_near_miss_typo  # noqa: E501
    def test_fuzzy_hint_on_near_miss_typo(self, tmp_path: Path) -> None:
        """A near-miss typo of a known field name (`priorty` for
        `priority`, the exact incident T-0838's reviewer flagged) gets a
        fuzzy-match hint naming the likely intended field."""
        ticket = self._ticket_with_extra("T-9002", priorty="low")
        violations = tickets_gate(tmp_path, self._queue(ticket))
        tick008 = _by_rule(violations, "TICK008")
        assert len(tick008) == 1
        assert "priorty" in tick008[0].message
        assert "did you mean 'priority'" in tick008[0].message

    # frob:tests tests/test_gates.py::TestTick008UnknownLedgerFields.test_silent_on_clean_ledger  # noqa: E501
    def test_silent_on_clean_ledger(self, tmp_path: Path) -> None:
        """A ticket with only known fields carries no `__pydantic_extra__`
        and never fires TICK008."""
        ticket = self._ticket_with_extra("T-9003")
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK008" for v in violations)

    # frob:tests tests/test_gates.py::TestTick008UnknownLedgerFields.test_real_repo_ledger_is_tick008_clean  # noqa: E501
    def test_real_repo_ledger_is_tick008_clean(self) -> None:
        """The real-repo smoke test the ticket demands: this repo's own
        live `tickets.md`/`tickets-archive.md` must produce ZERO TICK008
        findings today -- a nonzero result here means a genuinely stale
        known field somewhere in the live ledger, which this ticket's
        Description says to STOP and report rather than calibrate around."""
        from frob.tickets import load_queue

        root = Path(__file__).resolve().parents[1]
        queue = load_queue(root).danger_ok
        violations = tickets_gate(root, queue)
        tick008 = _by_rule(violations, "TICK008")
        assert tick008 == []

    # frob:tests tests/test_gates.py::TestTick008UnknownLedgerFields.test_waivable  # noqa: E501
    def test_waivable(self) -> None:
        """TICK008 is waivable like TICK004/TICK006/TICK007 (not added to
        `_UNWAIVABLE_RULES`) -- a genuinely temporary, disclosed exception
        (`frob:waive TICK008 reason=...`) stays available, matching the
        rest of the TICK family."""
        from frob.gates import _UNWAIVABLE_RULES

        assert "TICK008" not in _UNWAIVABLE_RULES


# frob:ticket T-0762
class TestPiiStructuralCrossLanguage:
    """T-0352: PII010/SEC110 field-shape and env-access equivalents over
    TypeScript/Rust source (`frob.gates._pii_structural`'s Python-only
    T-0207 scan extended to the other two `frob.lang`-supported grammars
    named in the ticket body). Every fixture is a real git-tracked file
    parsed via `frob.lang.raw_tree` (the ticket's "reuse the existing
    tree-sitter parses" mandate) -- not a hand-rolled second parser."""

    def _write(self, root: Path, rel: str, text: str) -> None:
        """Write `text` to `root/rel`, creating parent dirs as needed."""
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_interface_email_field_fires  # noqa: E501
    def test_ts_interface_email_field_fires(self, tmp_path: Path) -> None:
        """A TS `interface` field named `email` is the field-shape
        equivalent of a pydantic `BaseModel` field -- fires PII010."""
        self._write(
            tmp_path,
            "user.ts",
            "interface User {\n  email: string;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("email" in v.message and "user.ts" in v.file for v in pii010)

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_type_alias_password_field_fires  # noqa: E501
    def test_ts_type_alias_password_field_fires(self, tmp_path: Path) -> None:
        """A TS `type` alias object-type field named `password` fires
        PII010 -- the `type_alias_declaration`/`object_type` equivalent of
        an interface field."""
        self._write(
            tmp_path,
            "profile.ts",
            "type Profile = {\n  password: string;\n};\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("password" in v.message and "profile.ts" in v.file for v in pii010)

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_class_field_token_fires  # noqa: E501
    def test_ts_class_field_token_fires(self, tmp_path: Path) -> None:
        """A TS `class` field named `token` fires PII010 -- the class-body
        `public_field_definition` equivalent."""
        self._write(
            tmp_path,
            "account.ts",
            "class Account {\n  token: string;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("token" in v.message and "account.ts" in v.file for v in pii010)

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_clean_interface_is_silent  # noqa: E501
    def test_ts_clean_interface_is_silent(self, tmp_path: Path) -> None:
        """A TS interface with no PII-shaped field names fires nothing."""
        self._write(
            tmp_path,
            "widget.ts",
            "interface Widget {\n  width: number;\n  height: number;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not _by_rule(violations, "PII010")

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_index_signature_reported_not_skipped  # noqa: E501
    def test_ts_index_signature_reported_not_skipped(self, tmp_path: Path) -> None:
        """T-0352 NO-FAIL-SILENT: a TS index signature (`[key: string]: T`)
        has no statically-readable field name -- it must be REPORTED as an
        unresolvable field shape, never silently dropped from the scan."""
        self._write(
            tmp_path,
            "dynamic.ts",
            "interface Weird {\n  [key: string]: string;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("unresolvable" in v.message for v in pii010)

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_process_env_fires  # noqa: E501
    def test_ts_process_env_fires(self, tmp_path: Path) -> None:
        """`process.env.SECRET_KEY` fires SEC110 -- the TS equivalent of
        `os.environ[...]`/`os.getenv(...)`."""
        self._write(
            tmp_path,
            "config.ts",
            "const key = process.env.SECRET_KEY;\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        sec110 = _by_rule(violations, "SEC110")
        assert any("process.env" in v.message and "config.ts" in v.file for v in sec110)

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_process_env_subscript_fires  # noqa: E501
    def test_ts_process_env_subscript_fires(self, tmp_path: Path) -> None:
        """`process.env["API_TOKEN"]` (subscript form) fires SEC110."""
        self._write(
            tmp_path,
            "config2.ts",
            'const key = process.env["API_TOKEN"];\n',
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        sec110 = _by_rule(violations, "SEC110")
        assert any("API_TOKEN" in v.message and "config2.ts" in v.file for v in sec110)

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_import_meta_env_fires  # noqa: E501
    def test_ts_import_meta_env_fires(self, tmp_path: Path) -> None:
        """`import.meta.env.VITE_SECRET` (Vite-style bundler env access)
        fires SEC110 -- the ticket-named `import.meta.env` equivalent."""
        self._write(
            tmp_path,
            "vite.ts",
            "const key = import.meta.env.VITE_SECRET;\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        sec110 = _by_rule(violations, "SEC110")
        assert any(
            "import.meta.env" in v.message and "vite.ts" in v.file for v in sec110
        )

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_dynamic_env_key_still_fires  # noqa: E501
    def test_ts_dynamic_env_key_still_fires(self, tmp_path: Path) -> None:
        """T-0352 NO-FAIL-SILENT: `process.env[someDynamicKey]` (a
        non-literal subscript key) cannot be statically named -- it must
        still fire SEC110 rather than be silently skipped for lack of a
        resolvable name, mirroring `_scan_python_env_access`'s existing
        posture for a dynamic `os.environ[key]`."""
        self._write(
            tmp_path,
            "dynamic_env.ts",
            "const someDynamicKey = 'X';\nconst key = process.env[someDynamicKey];\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        sec110 = _by_rule(violations, "SEC110")
        assert any("dynamic_env.ts" in v.file for v in sec110)

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_allowlisted_env_var_is_silent  # noqa: E501
    def test_ts_allowlisted_env_var_is_silent(self, tmp_path: Path) -> None:
        """`process.env.PATH` is an allowlisted, definitionally-non-secret
        var (`_ENV_VAR_ALLOWLIST`, shared table) -- silent."""
        self._write(tmp_path, "clean_env.ts", "const p = process.env.PATH;\n")
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any("clean_env.ts" in v.file for v in _by_rule(violations, "SEC110"))

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_rust_struct_ssn_field_fires  # noqa: E501
    def test_rust_struct_ssn_field_fires(self, tmp_path: Path) -> None:
        """A Rust `struct` named field `ssn` fires PII010 -- the
        `field_declaration_list` equivalent of a Python dataclass field."""
        self._write(
            tmp_path,
            "user.rs",
            "struct User {\n    ssn: String,\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("ssn" in v.message and "user.rs" in v.file for v in pii010)

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_rust_clean_struct_is_silent  # noqa: E501
    def test_rust_clean_struct_is_silent(self, tmp_path: Path) -> None:
        """A Rust struct with no PII-shaped field names fires nothing."""
        self._write(
            tmp_path,
            "widget.rs",
            "struct Widget {\n    width: i32,\n    height: i32,\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not _by_rule(violations, "PII010")

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_rust_env_var_fires  # noqa: E501
    def test_rust_env_var_fires(self, tmp_path: Path) -> None:
        """`std::env::var("API_KEY")` fires SEC110 -- the Rust equivalent
        of `os.getenv(...)`."""
        self._write(
            tmp_path,
            "config.rs",
            'fn main() {\n    let k = std::env::var("API_KEY").unwrap();\n}\n',
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        sec110 = _by_rule(violations, "SEC110")
        assert any(
            "std::env::var" in v.message and "config.rs" in v.file for v in sec110
        )

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_rust_unqualified_env_var_fires  # noqa: E501
    def test_rust_unqualified_env_var_fires(self, tmp_path: Path) -> None:
        """`env::var("SECRET")` (direct-import form, no `std::` prefix)
        fires SEC110 too -- mirrors `_scan_python_env_access`'s
        direct-import `getenv(...)` handling."""
        self._write(
            tmp_path,
            "config2.rs",
            'fn main() {\n    let k = env::var("SECRET").unwrap();\n}\n',
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        sec110 = _by_rule(violations, "SEC110")
        assert any("config2.rs" in v.file for v in sec110)

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_rust_allowlisted_env_var_is_silent  # noqa: E501
    def test_rust_allowlisted_env_var_is_silent(self, tmp_path: Path) -> None:
        """`std::env::var("PATH")` is allowlisted -- silent."""
        self._write(
            tmp_path,
            "clean_env.rs",
            'fn main() {\n    let p = std::env::var("PATH").unwrap();\n}\n',
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any("clean_env.rs" in v.file for v in _by_rule(violations, "SEC110"))

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_rust_tuple_struct_field_not_matched  # noqa: E501
    def test_rust_tuple_struct_field_not_matched(self, tmp_path: Path) -> None:
        """Adversarial: a Rust TUPLE struct (`Point(i32, i32)`) has no
        source field names at all -- `_rust_struct_field_names` only reads
        `field_declaration_list` (named) bodies, so a tuple struct is
        silent regardless of its type names (no name to match against
        `FIELD_SIGNATURES` in the first place, not a false negative on a
        real PII field)."""
        self._write(tmp_path, "point.rs", "struct Point(i32, i32);\n")
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any("point.rs" in v.file for v in _by_rule(violations, "PII010"))

    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_and_rust_findings_joined_against_declared_surface  # noqa: E501
    def test_ts_and_rust_findings_joined_against_declared_surface(
        self, tmp_path: Path
    ) -> None:
        """T-0351's std.pii/std.secrets join applies identically to a
        TS/Rust finding -- `_load_declared_surface` is keyed on rel_path
        alone, language-agnostic, so a design directory with no models at
        all still leaves both languages' findings firing exactly as if
        T-0351 never ran (empty-surface degrade, shared code path)."""
        self._write(tmp_path, "user.ts", "interface User {\n  email: string;\n}\n")
        self._write(tmp_path, "user.rs", "struct User {\n    email: String,\n}\n")
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010_files = {v.file for v in _by_rule(violations, "PII010")}
        assert "user.ts" in pii010_files
        assert "user.rs" in pii010_files

    # frob:ticket T-0762
    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_secret_wrapper_type_field_fires  # noqa: E501
    def test_ts_secret_wrapper_type_field_fires(self, tmp_path: Path) -> None:
        """T-0762: a TS field typed as a known secret-wrapper type
        (`SecretString`) fires PII010 even though its own NAME (`apiKey`)
        does not itself contain a name-kind keyword token."""
        self._write(
            tmp_path,
            "creds.ts",
            "interface Creds {\n  wrapped: SecretString;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("SecretString" in v.message and "creds.ts" in v.file for v in pii010)

    # frob:ticket T-0762
    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_branded_email_type_field_fires  # noqa: E501
    def test_ts_branded_email_type_field_fires(self, tmp_path: Path) -> None:
        """T-0762: a TS field typed as a branded/nominal `Email` type fires
        PII010 -- the TYPE-kind signal, independent of the field's own
        NAME."""
        self._write(
            tmp_path,
            "contact.ts",
            "interface Contact {\n  primary: Email;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("Email" in v.message and "contact.ts" in v.file for v in pii010)

    # frob:ticket T-0762
    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_ts_plain_string_field_type_does_not_fire  # noqa: E501
    def test_ts_plain_string_field_type_does_not_fire(self, tmp_path: Path) -> None:
        """Adversarial (T-0762 acceptance): a plain `string`-typed field
        with a non-PII-shaped name does not fire -- TYPE-kind matching
        must not over-fire on the ordinary built-in type."""
        self._write(
            tmp_path,
            "clean_type.ts",
            "interface Widget {\n  label: string;\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any(
            "clean_type.ts" in v.file for v in _by_rule(violations, "PII010")
        )

    # frob:ticket T-0762
    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_rust_secrecy_secretstring_type_field_fires  # noqa: E501
    def test_rust_secrecy_secretstring_type_field_fires(self, tmp_path: Path) -> None:
        """T-0762: a Rust field typed `secrecy::SecretString` fires PII010
        -- the ticket-named `secrecy` crate wrapper, matched via the scoped
        type-identifier walk regardless of the field's own NAME."""
        self._write(
            tmp_path,
            "vault.rs",
            "struct Vault {\n    wrapped: secrecy::SecretString,\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("SecretString" in v.message and "vault.rs" in v.file for v in pii010)

    # frob:ticket T-0762
    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_rust_secret_newtype_type_field_fires  # noqa: E501
    def test_rust_secret_newtype_type_field_fires(self, tmp_path: Path) -> None:
        """T-0762: a Rust field typed `secrecy::Secret<String>` fires
        PII010 -- a generic-wrapped scoped type name still surfaces its
        inner identifier to the type-identifier walk."""
        self._write(
            tmp_path,
            "vault2.rs",
            "struct Vault2 {\n    wrapped: secrecy::Secret<String>,\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        pii010 = _by_rule(violations, "PII010")
        assert any("vault2.rs" in v.file for v in pii010)

    # frob:ticket T-0762
    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_rust_plain_string_field_type_does_not_fire  # noqa: E501
    def test_rust_plain_string_field_type_does_not_fire(self, tmp_path: Path) -> None:
        """Adversarial (T-0762 acceptance): a plain `String`-typed Rust
        field with a non-PII-shaped name does not fire."""
        self._write(
            tmp_path,
            "clean_type.rs",
            "struct Widget {\n    label: String,\n}\n",
        )
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any(
            "clean_type.rs" in v.file for v in _by_rule(violations, "PII010")
        )

    # frob:ticket T-0897
    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_unparseable_python_file_fires_parse001  # noqa: E501
    def test_unparseable_python_file_fires_parse001(self, tmp_path: Path) -> None:
        """A `.py` file with a syntax error fires PARSE001 instead of
        being silently dropped from the PII010/SEC110 scan with zero
        Violation (T-0897)."""
        self._write(tmp_path, "broken.py", "class C(:\n    pass\n")
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        hits = _by_rule(violations, "PARSE001")
        offender_hits = [v for v in hits if v.file == "broken.py"]
        assert len(offender_hits) == 1
        assert offender_hits[0].severity == Severity.ERROR

    # frob:ticket T-0897
    # frob:tests tests/test_gates.py::TestPiiStructuralCrossLanguage.test_unparseable_file_under_graph_exclude_is_silent  # noqa: E501
    def test_unparseable_file_under_graph_exclude_is_silent(
        self, tmp_path: Path
    ) -> None:
        """A `.py` file under a `[graph].exclude` glob (frob.toml) that is
        deliberately, permanently unparseable (the `tests/fixtures/**`
        posture: kept out of frob's own obligation surface, module
        docstrings across the repo document this) does NOT fire PARSE001
        -- only files frob's own graph would otherwise obligate do
        (T-0897)."""
        (tmp_path / "frob.toml").write_text(
            '[graph]\nexclude = ["tests/fixtures/**"]\n'
        )
        self._write(tmp_path, "tests/fixtures/broken.py", "class C(:\n    pass\n")
        _git_init(tmp_path)
        violations = pii_structural_gate(tmp_path)
        hits = [v for v in _by_rule(violations, "PARSE001") if "broken.py" in v.file]
        assert hits == []


# frob:ticket T-0788
class TestComplianceGate:
    """COMPLIANCE005 (T-0788): `compliance_gate` is the `frob check`
    dispatch of `frob.strata._compliance.check_cmpl_registry` (built by
    T-0607, which could not register or dispatch it -- out of that
    ticket's declared scope). Verifies the rule id is a real, registered
    gate rule and that the dispatch wiring fires/stays silent on the
    right dispositions, mirroring `tests/unit/strata/test_compliance.py`'s
    `TestCmplRegistry` fixture shapes at the gate layer."""

    # frob:ticket T-0788
    def _write_compliance_yaml(self, tmp_path: Path, entries_yaml: str) -> Path:
        """A minimal `docs/design/registry/compliance.yaml` under `tmp_path`
        with `entries_yaml` spliced into its `entries:` list."""
        registry_dir = tmp_path / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "compliance.yaml").write_text(
            "entries:\n" + entries_yaml, encoding="utf-8"
        )
        return registry_dir

    # frob:ticket T-0788
    # frob:tests tests/test_gates.py::TestComplianceGate.test_compliance005_registered_in_known_gate_rules  # noqa: E501
    def test_compliance005_registered_in_known_gate_rules(self) -> None:
        """COMPLIANCE005 is in the live `_KNOWN_GATE_RULES` union -- the
        exact gap T-0607 disclosed (the rule existed in code but was not a
        real, registered gate rule id anywhere `frob check` consults)."""
        assert "COMPLIANCE005" in known_gate_rule_ids()

    # frob:ticket T-0788
    # frob:tests tests/test_gates.py::TestComplianceGate.test_compliance005_fires_on_deferred_disposition  # noqa: E501
    def test_compliance005_fires_on_deferred_disposition(self, tmp_path: Path) -> None:
        """A `CMPL_REGISTRY_UNIT_IDS` member left `deferred:*` fires
        COMPLIANCE005 through the real `frob check` dispatch path, not
        just the underlying strata check called directly."""
        entry_id = sorted(CMPL_REGISTRY_UNIT_IDS)[0]
        registry_dir = self._write_compliance_yaml(
            tmp_path,
            f'  - id: "{entry_id}"\n'
            '    title: "t"\n'
            '    disposition: "deferred:T-0001"\n',
        )
        violations = compliance_gate(tmp_path, registry_dir)
        cmpl005 = [v for v in violations if v.rule == "COMPLIANCE005"]
        assert len(cmpl005) == 1
        assert entry_id in cmpl005[0].message
        assert cmpl005[0].severity == Severity.ERROR

    # frob:ticket T-0788
    # frob:tests tests/test_gates.py::TestComplianceGate.test_compliance005_silent_on_handled_by_and_out_of_scope  # noqa: E501
    def test_compliance005_silent_on_handled_by_and_out_of_scope(
        self, tmp_path: Path
    ) -> None:
        """`handled_by:*` and `out_of_scope:*` are both accepted --
        COMPLIANCE005 does not fire through the gate dispatch either."""
        ids = sorted(CMPL_REGISTRY_UNIT_IDS)
        registry_dir = self._write_compliance_yaml(
            tmp_path,
            f'  - id: "{ids[0]}"\n'
            '    title: "t"\n'
            '    disposition: "handled_by:COMPLIANCE005"\n'
            f'  - id: "{ids[1]}"\n'
            '    title: "t"\n'
            '    disposition: "out_of_scope:reason text"\n',
        )
        violations = compliance_gate(tmp_path, registry_dir)
        assert not any(v.rule == "COMPLIANCE005" for v in violations)

    # frob:ticket T-0788
    # frob:tests tests/test_gates.py::TestComplianceGate.test_compliance005_missing_registry_dir_is_silent  # noqa: E501
    def test_compliance005_missing_registry_dir_is_silent(self, tmp_path: Path) -> None:
        """No `compliance.yaml` at all (a repo with no compliance
        registry) makes no COMPLIANCE005 claim -- matches `registry_gate`'s
        own missing-directory posture, not a false-positive load error."""
        violations = compliance_gate(tmp_path)
        assert violations == ()

    # frob:ticket T-0788
    # frob:tests tests/test_gates.py::TestComplianceGate.test_compliance005_real_repo_registry_passes  # noqa: E501
    def test_compliance005_real_repo_registry_passes(self) -> None:
        """The honest "real repo scan" smoke test (T-0813/T-0820
        precedent): runs `compliance_gate` over this repo's OWN live
        `docs/design/registry/compliance.yaml` -- every one of the 17
        `CMPL_REGISTRY_UNIT_IDS` units T-0607 re-dispositioned must still
        carry a `handled_by`/`out_of_scope` disposition, so this must be
        silent (0 COMPLIANCE005 findings) against real repo state."""
        root = Path(__file__).resolve().parents[1]
        violations = compliance_gate(root)
        assert not any(v.rule == "COMPLIANCE005" for v in violations)

    # frob:ticket T-0894
    # frob:tests tests/test_gates.py::TestComplianceGate.test_compliance006_silent_on_never_adopted_registry  # noqa: E501
    def test_compliance006_silent_on_never_adopted_registry(
        self, tmp_path: Path
    ) -> None:
        """A `tmp_path` git repo that never committed `compliance.yaml` at
        all stays silent -- COMPLIANCE006 must not fire on a genuinely
        never-adopted registry, only on one that existed and was deleted."""
        _git_init(tmp_path)
        violations = compliance_gate(tmp_path)
        assert not any(v.rule == "COMPLIANCE006" for v in violations)

    # frob:ticket T-0894
    # frob:tests tests/test_gates.py::TestComplianceGate.test_compliance006_fires_on_deleted_registry_after_adoption  # noqa: E501
    def test_compliance006_fires_on_deleted_registry_after_adoption(
        self, tmp_path: Path
    ) -> None:
        """T-0894: `compliance.yaml` committed once, then deleted, must
        fire COMPLIANCE006 (unwaivable) rather than silently degrading to
        the "never adopted" empty-tuple posture COMPLIANCE005 alone gives
        it."""
        _git_init(tmp_path)
        registry_dir = self._write_compliance_yaml(
            tmp_path,
            "  - id: CMPL-TEST-1\n    disposition: 'handled_by:SEC003'\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "adopt compliance registry"],
            cwd=tmp_path,
            check=True,
        )
        (registry_dir / "compliance.yaml").unlink()

        from frob.gates import _UNWAIVABLE_RULES

        violations = compliance_gate(tmp_path)
        assert any(v.rule == "COMPLIANCE006" for v in violations)
        assert "COMPLIANCE006" in _UNWAIVABLE_RULES


# frob:ticket T-0688
class TestExhaustiveHandlingGate:
    """T-0688: frob.gates._exhaustive_handling.exhaustive_handling_gate --
    EXHAUST001/EXHAUST002 over frob.arch._mayraise.compute_may_raise's
    per-function may-raise sets. A function is a "boundary" only once it
    has at least one except clause of its own; a boundary that leaks
    Unknown with no catch-all fires EXHAUST001, a boundary that leaks a
    named type not declared via `# frob:raises <Type>` fires EXHAUST002."""

    # frob:tests \
    # tests/test_gates.py::TestExhaustiveHandlingGate.test_partial_catch_of_named_type_\
    # fires_exhaust002
    def test_partial_catch_of_named_type_fires_exhaust002(self, tmp_path: Path) -> None:
        """`boundary` catches only ValueError but `risky` (which it calls)
        raises TypeError -- the leaked TypeError is named in EXHAUST002."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def risky():\n"
                "    raise TypeError('bad')\n"
                "\n"
                "def boundary():\n"
                "    try:\n"
                "        risky()\n"
                "    except ValueError:\n"
                "        pass\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        found = _by_rule(violations, "EXHAUST002")
        assert found
        assert any(v.symref == "mod.py::boundary" for v in found)
        assert any("TypeError" in v.message for v in found)

    # frob:tests \
    # tests/test_gates.py::TestExhaustiveHandlingGate.test_unknown_without_catch_all_fi\
    # res_exhaust001
    def test_unknown_without_catch_all_fires_exhaust001(self, tmp_path: Path) -> None:
        """`boundary` calls an unresolvable function (contributes Unknown)
        and only catches ValueError -- no catch-all discharges Unknown, so
        EXHAUST001 fires."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def boundary():\n"
                "    try:\n"
                "        some_unresolved_call()\n"
                "    except ValueError:\n"
                "        pass\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        found = _by_rule(violations, "EXHAUST001")
        assert found
        assert any(v.symref == "mod.py::boundary" for v in found)

    # frob:tests \
    # tests/test_gates.py::TestExhaustiveHandlingGate.test_catch_all_of_unknown_does_no\
    # t_fire_exhaust001
    def test_catch_all_of_unknown_does_not_fire_exhaust001(
        self, tmp_path: Path
    ) -> None:
        """Same shape as above but the boundary's own catch is a real
        catch-all (`except Exception:`) -- Unknown is discharged, no
        EXHAUST001."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def boundary():\n"
                "    try:\n"
                "        some_unresolved_call()\n"
                "    except Exception:\n"
                "        pass\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        assert not _by_rule(violations, "EXHAUST001")

    # frob:tests \
    # tests/test_gates.py::TestExhaustiveHandlingGate.test_declared_frob_raises_directi\
    # ve_discharges_exhaust002
    def test_declared_frob_raises_directive_discharges_exhaust002(
        self, tmp_path: Path
    ) -> None:
        """A `# frob:raises TypeError` directive directly above `boundary`
        declares the leaked TypeError as intentional propagation -- no
        EXHAUST002, unlike the undeclared case above."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def risky():\n"
                "    raise TypeError('bad')\n"
                "\n"
                "# frob:raises TypeError\n"
                "def boundary():\n"
                "    try:\n"
                "        risky()\n"
                "    except ValueError:\n"
                "        pass\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        assert not _by_rule(violations, "EXHAUST002")

    # frob:tests \
    # tests/test_gates.py::TestExhaustiveHandlingGate.test_function_with_no_catches_is_\
    # not_a_boundary
    def test_function_with_no_catches_is_not_a_boundary(self, tmp_path: Path) -> None:
        """`caller` calls `risky` (which raises TypeError) but has no
        `except` clause of its own -- it is plain propagation, not a
        declared boundary, so neither EXHAUST001 nor EXHAUST002 fires."""
        from frob.gates._exhaustive_handling import exhaustive_handling_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "def risky():\n"
                "    raise TypeError('bad')\n"
                "\n"
                "def caller():\n"
                "    risky()\n"
            ),
        )
        violations = exhaustive_handling_gate(tmp_path)
        assert not _by_rule(violations, "EXHAUST001")
        assert not _by_rule(violations, "EXHAUST002")


# frob:ticket T-0690
class TestFfiBoundaryGate:
    """T-0690: frob.gates._ffi_boundary.ffi_boundary_gate -- FFI001 cross-
    checks a pyo3 `.pyi` stub's declared `frob:raises` against the Rust
    source's own observed raised-type set (paired via a `frob:describes
    <path>.rs` pragma in the stub's module docstring); FFI002 demands a
    `# frob:callee-raises` declaration on every call made through a
    ctypes-loaded library handle."""

    # frob:tests \
    # tests/test_gates.py::TestFfiBoundaryGate.test_pyo3_drift_fires_ffi001
    def test_pyo3_drift_fires_ffi001(self, tmp_path: Path) -> None:
        """The Rust side constructs PyValueError but the `.pyi` stub's
        `frob:raises` omits it -- FFI001 names both sides."""
        from frob.gates._ffi_boundary import ffi_boundary_gate

        (tmp_path / "crate").mkdir()
        _write(
            tmp_path,
            "crate/lib.rs",
            (
                "#[pyfunction]\n"
                "fn foo(x: i64) -> PyResult<i64> {\n"
                "    if x < 0 {\n"
                '        return Err(PyValueError::new_err("bad"));\n'
                "    }\n"
                "    Ok(x)\n"
                "}\n"
            ),
        )
        _write(
            tmp_path,
            "crate.pyi",
            (
                '"""Stub.\n'
                "\n"
                "frob:describes crate/lib.rs\n"
                '"""\n'
                "\n"
                "def foo(x: int) -> int: ...\n"
            ),
        )
        violations = ffi_boundary_gate(tmp_path, tmp_path)
        found = _by_rule(violations, "FFI001")
        assert found
        assert any("ValueError" in v.message for v in found)
        assert any(v.symref == "crate.pyi::foo" for v in found)

    # frob:tests \
    # tests/test_gates.py::TestFfiBoundaryGate.test_pyo3_declared_matches_no_drift
    def test_pyo3_declared_matches_no_drift(self, tmp_path: Path) -> None:
        """Same Rust side, but the `.pyi` stub declares `# frob:raises
        ValueError` above `def foo` -- no FFI001."""
        from frob.gates._ffi_boundary import ffi_boundary_gate

        (tmp_path / "crate").mkdir()
        _write(
            tmp_path,
            "crate/lib.rs",
            (
                "#[pyfunction]\n"
                "fn foo(x: i64) -> PyResult<i64> {\n"
                "    if x < 0 {\n"
                '        return Err(PyValueError::new_err("bad"));\n'
                "    }\n"
                "    Ok(x)\n"
                "}\n"
            ),
        )
        _write(
            tmp_path,
            "crate.pyi",
            (
                '"""Stub.\n'
                "\n"
                "frob:describes crate/lib.rs\n"
                '"""\n'
                "\n"
                "# frob:raises ValueError\n"
                "def foo(x: int) -> int: ...\n"
            ),
        )
        violations = ffi_boundary_gate(tmp_path, tmp_path)
        assert not _by_rule(violations, "FFI001")

    # frob:tests \
    # tests/test_gates.py::TestFfiBoundaryGate.test_ctypes_call_without_declaration_fir\
    # es_ffi002
    def test_ctypes_call_without_declaration_fires_ffi002(self, tmp_path: Path) -> None:
        """A call through a ctypes.CDLL-loaded handle with no callee-raises
        comment (`# frob` + `:callee-raises`) on its own line fires
        FFI002."""
        from frob.gates._ffi_boundary import ffi_boundary_gate

        _write(
            tmp_path,
            "mod.py",
            ('import ctypes\nlib = ctypes.CDLL("libfoo.so")\nlib.do_thing(1)\n'),
        )
        violations = ffi_boundary_gate(tmp_path, tmp_path)
        found = _by_rule(violations, "FFI002")
        assert found
        assert any("do_thing" in v.message for v in found)

    # frob:tests \
    # tests/test_gates.py::TestFfiBoundaryGate.test_ctypes_call_with_empty_declaration_\
    # clean
    def test_ctypes_call_with_empty_declaration_clean(self, tmp_path: Path) -> None:
        """The same call, but with a bare `# frob:callee-raises` comment
        (the valid "raises nothing, errno convention" declaration) on its
        own line -- no FFI002."""
        from frob.gates._ffi_boundary import ffi_boundary_gate

        _write(
            tmp_path,
            "mod.py",
            (
                "import ctypes\n"
                'lib = ctypes.CDLL("libfoo.so")\n'
                "lib.do_thing(1)  # frob:callee-raises\n"
            ),
        )
        violations = ffi_boundary_gate(tmp_path, tmp_path)
        assert not _by_rule(violations, "FFI002")


# frob:ticket T-0688
class TestErrorsAsValuesAdvisory:
    """T-0688: frob.arch._exceptions.check_errors_as_values -- a PUBLIC
    function/method whose recoverable may-raise set (computed via
    frob.arch._mayraise.compute_may_raise) has no same-module caller
    visibly handling it recommends a typani Result[T, E], the raise sites
    named as the sketch."""

    # frob:tests \
    # tests/test_gates.py::TestErrorsAsValuesAdvisory.test_public_raiser_with_no_handli\
    # ng_caller_recommends_result
    def test_public_raiser_with_no_handling_caller_recommends_result(
        self,
    ) -> None:
        from frob.arch._exceptions import check_errors_as_values
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        risky = NormalizedFunction(
            name="risky",
            line=1,
            body_line_count=2,
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
        )
        caller = NormalizedFunction(
            name="caller",
            line=5,
            body_line_count=2,
            calls=[NormalizedCall(callee="risky", line=6)],
        )
        module = NormalizedModule(
            path="mod.py", language="python", functions=[risky, caller]
        )
        suggestions = check_errors_as_values(module)
        matches = [
            s for s in suggestions if s.category == "errors-as-values-recommended"
        ]
        assert matches
        assert any(s.symref == "mod.py::risky" for s in matches)

    # frob:tests \
    # tests/test_gates.py::TestErrorsAsValuesAdvisory.test_public_raiser_with_handling_\
    # caller_not_flagged
    def test_public_raiser_with_handling_caller_not_flagged(self) -> None:
        from frob.arch._exceptions import check_errors_as_values
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        risky = NormalizedFunction(
            name="risky",
            line=1,
            body_line_count=2,
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
        )
        caller = NormalizedFunction(
            name="caller",
            line=5,
            body_line_count=4,
            calls=[NormalizedCall(callee="risky", line=7)],
            catches=[NormalizedCatch(line=8, exception_type="ValueError")],
        )
        module = NormalizedModule(
            path="mod.py", language="python", functions=[risky, caller]
        )
        suggestions = check_errors_as_values(module)
        assert not any(
            s.category == "errors-as-values-recommended" for s in suggestions
        )

    # frob:tests \
    # tests/test_gates.py::TestErrorsAsValuesAdvisory.test_private_raiser_not_flagged
    def test_private_raiser_not_flagged(self) -> None:
        from frob.arch._exceptions import check_errors_as_values
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        risky = NormalizedFunction(
            name="_risky",
            line=1,
            body_line_count=2,
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
        )
        module = NormalizedModule(path="mod.py", language="python", functions=[risky])
        suggestions = check_errors_as_values(module)
        assert not any(
            s.category == "errors-as-values-recommended" for s in suggestions
        )

    # frob:tests \
    # tests/test_gates.py::TestErrorsAsValuesAdvisory.test_only_ubiquitous_or_unknown_r\
    # aises_not_flagged
    def test_only_ubiquitous_or_unknown_raises_not_flagged(self) -> None:
        """`risky` calls an unresolvable function only (contributes solely
        `UNKNOWN`, no `_RECOVERABLE_EXCEPTION_TYPES` member) -- never
        flagged, since this advisory never recommends a Result signature
        off an unidentified failure mode alone."""
        from frob.arch._exceptions import check_errors_as_values
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        risky = NormalizedFunction(
            name="risky",
            line=1,
            body_line_count=2,
            calls=[NormalizedCall(callee="some_unresolved_call", line=2)],
        )
        module = NormalizedModule(path="mod.py", language="python", functions=[risky])
        suggestions = check_errors_as_values(module)
        assert not any(
            s.category == "errors-as-values-recommended" for s in suggestions
        )
