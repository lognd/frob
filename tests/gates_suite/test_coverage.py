import json
import os
import subprocess
from pathlib import Path

import pytest

from frob.gates import (
    GateConfig,
    GateError,
    Severity,
    coverage_gate,
    load_coverage,
    run_gates,
    stamp_coverage,
)
from frob.gitio import Diff, Hunk, working_diff
from frob.testing import CollectedTests
from frob.tickets import Origin, TicketKind, TicketQueue, TicketState
from tests.conftest import (
    _WIDGET_PY,
    _by_rule,
    _files,
    _first_rule,
    _git_init,
    _marker_line,
    _snapshot,
    _state_line,
    _ticket,
    _v2_ticket_file_hunk,
    _write,
    _write_ticket,
    _write_ticket_v2,
)


# frob:ticket T-0553
# frob:ticket T-0783
# frob:ticket T-2549
# frob:ticket T-2865
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

    # ------------------------------------------------------------------
    # T-1582: v2-mode mirrors of the COV002 closing-diff grace tests
    # above. v2 has no `tickets.md` monofile -- each ticket owns its own
    # `tickets/<id>/ticket.md`, so "the ticket's marker/state line is in
    # a touched hunk" collapses to "that ticket's own file has a hunk in
    # the diff" (see `_v2_ticket_file_hunk`), and `_ledger_states_at_base`
    # must resolve state from the git-tracked v2 tree at `diff.base`
    # rather than a `tickets.md` blob that never existed in a v2 repo.
    # ------------------------------------------------------------------

    def test_cov002_v2_done_ticket_covers_own_closing_diff(
        self, tmp_path: Path
    ) -> None:
        """v2 mirror of test_cov002_done_ticket_covers_own_closing_diff:
        the ticket was IN_PROGRESS at base, DONE in the working tree, and
        this diff carries a hunk on its own `tickets/T-0001/ticket.md` --
        grace must apply."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        ticket = _ticket(state=TicketState.IN_PROGRESS)
        _write_ticket_v2(tmp_path, ticket)
        _git_init(tmp_path)
        done_ticket = _ticket(state=TicketState.DONE)
        _write_ticket_v2(tmp_path, done_ticket)
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
                _v2_ticket_file_hunk("T-0001"),
            ),
        )
        queue = TicketQueue(tickets={"T-0001": done_ticket})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV002" for v in violations)

    def test_cov002_v2_grace_covers_ticket_created_and_closed_in_same_diff(
        self, tmp_path: Path
    ) -> None:
        """v2 mirror of test_cov002_grace_covers_ticket_created_and_closed_
        in_same_diff (T-0590): the ticket has no `tickets/T-0001/` blob at
        all at `diff.base` (created and closed entirely within this
        uncommitted diff) -- `_ledger_states_at_base_v2` must resolve
        `None` for it, and `_base_state_permits_grace` treats that as
        grace-eligible, same as v1's "no entry in tickets.md at base"
        case."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        _git_init(tmp_path)
        done_ticket = _ticket(state=TicketState.DONE)
        _write_ticket_v2(tmp_path, done_ticket)
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
                _v2_ticket_file_hunk("T-0001"),
            ),
        )
        queue = TicketQueue(tickets={"T-0001": done_ticket})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV002" for v in violations)

    def test_cov002_v2_marker_touch_without_state_transition_still_fires(
        self, tmp_path: Path
    ) -> None:
        """v2 mirror of test_cov002_marker_touch_without_state_transition_
        still_fires (T-0320): the ticket was ALREADY DONE at base too (a
        typo-fix-shaped re-write, not a genuine transition) -- grace must
        not apply, and COV002 still fires."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        ticket = _ticket(state=TicketState.DONE)
        _write_ticket_v2(tmp_path, ticket)
        _git_init(tmp_path)
        # Re-write the same (still-DONE) ticket file -- simulates a
        # Done-report typo fix that touches the same v2 file again.
        _write_ticket_v2(tmp_path, ticket)
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
                _v2_ticket_file_hunk("T-0001"),
            ),
        )
        queue = TicketQueue(tickets={"T-0001": ticket})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        v = _first_rule(violations, "COV002")
        assert v is not None
        assert "frob ticket new" in v.message

    def test_cov002_v2_done_ticket_without_grace_still_fires(
        self, tmp_path: Path
    ) -> None:
        """v2 mirror of test_cov002_done_ticket_without_grace_still_fires:
        a DONE ticket whose own `tickets/T-0001/ticket.md` is NOT part of
        this diff at all must not cover an unrelated later touch to the
        symbol it once covered."""
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

    def test_cov002_v2_stale_done_ticket_unrelated_touch_still_fires(
        self, tmp_path: Path
    ) -> None:
        """v2 mirror of test_cov002_stale_done_ticket_unrelated_tickets_md_
        touch_still_fires: a symbol bound to an old, already-DONE T-0001
        (not part of this diff) must still fire even though this diff DOES
        touch a different ticket's own v2 file (T-0002) -- grace must be
        scoped to the specific ticket whose OWN file is in the diff, not
        "some ticket file was touched somewhere"."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        stale_ticket = _ticket(ticket_id="T-0001", state=TicketState.DONE)
        _write_ticket_v2(tmp_path, stale_ticket)
        unrelated_ticket = _ticket(ticket_id="T-0002", state=TicketState.DONE)
        _write_ticket_v2(tmp_path, unrelated_ticket)
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::helper"]
        diff = Diff(
            base="x",
            hunks=(
                Hunk(file="src/a.py", span=record.span),
                # A v2 ticket file IS touched, but only T-0002's -- T-0001's
                # own file is nowhere in this diff.
                _v2_ticket_file_hunk("T-0002"),
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

    # invariant spec: [INV-013](invariants/INV-013.md)
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

    # frob:ticket T-2688
    def test_cov008_fires_when_diff_deletes_a_cited_test(self, tmp_path: Path) -> None:
        """MUST-FIRE fixture (T-2688's own required positive control):
        deleting a test file some ticket's evidence still cites must be
        refused at diff time, not discovered later by an unrelated COV003
        sweep."""
        _git_init(tmp_path)
        node = "tests/test_x.py::test_foo"
        _write(tmp_path, "tests/test_x.py", "def test_foo():\n    pass\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add test_x"], cwd=tmp_path, check=True
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(
            tickets={
                "T-0002": _ticket(
                    ticket_id="T-0002", state=TicketState.DONE, evidence=(node,)
                )
            }
        )
        (tmp_path / "tests" / "test_x.py").unlink()
        diff = working_diff(tmp_path, "main").danger_ok
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        v = _first_rule(violations, "COV008")
        assert v is not None
        assert "T-0002" in v.message
        assert node in v.message

    # frob:ticket T-2688
    def test_cov008_silent_on_uncited_deletion(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET fixture #1 (T-2688): deleting a test file NO
        ticket's evidence cites is the overwhelming majority of ordinary
        test cleanup and must never fire -- COV008 is not a blanket "no
        test may ever be deleted" tax."""
        _git_init(tmp_path)
        _write(tmp_path, "tests/test_x.py", "def test_foo():\n    pass\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add test_x"], cwd=tmp_path, check=True
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(
            tickets={
                "T-0002": _ticket(
                    ticket_id="T-0002",
                    state=TicketState.DONE,
                    evidence=("tests/test_y.py::test_unrelated",),
                )
            }
        )
        (tmp_path / "tests" / "test_x.py").unlink()
        diff = working_diff(tmp_path, "main").danger_ok
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV008" for v in violations)

    # frob:ticket T-2688
    def test_cov008_silent_on_rename_with_rebound_citation(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET fixture #2 (T-2688): a rename whose citation was
        ALREADY rebound to the test's new node id must stay silent -- the
        ticket's evidence no longer names the vanished old path at all, so
        there is nothing left for COV008 to match against the old path's
        disappearance."""
        _git_init(tmp_path)
        _write(tmp_path, "tests/test_x.py", "def test_foo():\n    pass\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add test_x"], cwd=tmp_path, check=True
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(
            tickets={
                "T-0002": _ticket(
                    ticket_id="T-0002",
                    state=TicketState.DONE,
                    evidence=("tests/test_y.py::test_foo",),
                )
            }
        )
        (tmp_path / "tests" / "test_x.py").unlink()
        _write(tmp_path, "tests/test_y.py", "def test_foo():\n    pass\n")
        diff = working_diff(tmp_path, "main").danger_ok
        tests = CollectedTests(node_ids=frozenset({"tests/test_y.py::test_foo"}))
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV008" for v in violations)

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
        merged, python_collection_failed = gates_mod._load_tests(tmp_path)
        assert merged.node_ids == frozenset(
            {"tests/test_x.py::test_a", "crate/src/lib.rs::tests::foo"}
        )
        assert python_collection_failed is None

        # A broken rust collector degrades to "no rust ids", not a crash and
        # not a wipe of the python ids already collected.
        monkeypatch.setattr(
            gates_mod,
            "collect_rust_tests",
            lambda root: Err(TestingError.CollectFailed),
        )
        merged2, python_collection_failed2 = gates_mod._load_tests(tmp_path)
        assert merged2.node_ids == frozenset({"tests/test_x.py::test_a"})
        assert python_collection_failed2 is None

    # frob:ticket T-1161
    def test_load_tests_captures_python_collection_failure_detail(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-1161: when `collect_python_tests` itself fails, `_load_tests`
        returns non-`None` failure detail alongside an empty python node-id
        set -- the signal `coverage_gate` consumes to report ONE COV003
        instead of one per archived evidence id."""
        from typani import Err, Ok

        import frob.gates as gates_mod
        from frob.testing import TestingError

        monkeypatch.setattr(
            gates_mod,
            "collect_python_tests",
            lambda root: Err(TestingError.CollectFailed),
        )
        monkeypatch.setattr(
            gates_mod, "python_collection_failure_detail", lambda: "exit 2\nstderr tail"
        )
        monkeypatch.setattr(
            gates_mod,
            "collect_rust_tests",
            lambda root: Ok(CollectedTests(node_ids=frozenset())),
        )
        merged, python_collection_failed = gates_mod._load_tests(tmp_path)
        assert merged.node_ids == frozenset()
        assert python_collection_failed == "exit 2\nstderr tail"

    # frob:ticket T-1161
    def test_coverage_gate_reports_one_violation_on_python_collection_failure(
        self, tmp_path: Path
    ) -> None:
        """T-1161: `coverage_gate(..., python_collection_failed=...)` reports
        exactly ONE COV003 naming the collection failure, never one per
        archived evidence id (the 6219-COV003 incident)."""
        snap = _snapshot(tmp_path)
        queue = TicketQueue(
            tickets={
                f"T-{n:04d}": _ticket(
                    ticket_id=f"T-{n:04d}",
                    state=TicketState.DONE,
                    evidence=("tests/x.py::t",),
                )
                for n in range(5)
            }
        )
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(
            tmp_path,
            snap,
            queue,
            diff,
            tests,
            python_collection_failed="exit 2\nstderr tail",
        )
        cov003 = [v for v in violations if v.rule == "COV003"]
        assert len(cov003) == 1
        assert "stderr tail" in cov003[0].message

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

    def test_cov004_matching_sha_is_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The stub-regression case: an attachment whose file exists with a
        byte-exact sha256 must NOT fire COV004. `_cov004_one` shipped as an
        unconditional-fire stub, and only the missing-file (confirmatory)
        direction above was tested, so the stub sat green until the first
        real `frob ticket attach` fired it on an identical file."""
        import hashlib

        from frob.tickets import Attachment

        snap = _snapshot(tmp_path)
        payload = b"diagnostics text\n"
        att_dir = tmp_path / "tickets" / "attachments" / "T-0003"
        att_dir.mkdir(parents=True)
        (att_dir / "01-x.txt").write_bytes(payload)
        att = Attachment(
            path="attachments/T-0003/01-x.txt",
            caption="x",
            sha256=hashlib.sha256(payload).hexdigest(),
        )
        queue = TicketQueue(
            tickets={"T-0003": _ticket(ticket_id="T-0003", attachments=(att,))}
        )
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        monkeypatch.chdir(tmp_path)
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV004" for v in violations)

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

    # frob:tests \
    # tests/gates_suite/test_coverage.py::TestCoverageGate.test_cov005_new_private_helper_sharing_anchor_with_undisturbed_public_is_clean  # noqa: E501
    # frob:ticket T-2720
    def test_cov005_new_private_helper_sharing_anchor_with_undisturbed_public_is_clean(
        self, tmp_path: Path
    ) -> None:
        """T-2720 false-positive shape (T-1614's waive audit, root cause of
        18+ `frob:waive COV005` sites in `.claude/hooks/root-write-guard.
        py`): `foo` stays public, keeps its OWN `frob:doc` directive
        unchanged across the diff -- it is NOT displaced. A brand-new,
        UNRELATED private helper `_bar_impl` is added in the same diff and
        happens to reuse the SAME shared doc anchor (this repo's own
        documented convention: one `frob:doc <page>#<anchor>` target
        covers every symbol a doc page describes). This must NOT fire
        COV005 -- `_bar_impl` was never `foo`'s directive riding along; it
        is its own, brand-new, correctly-anchored binding. Before T-2720's
        narrowing, `_cov005_file` flagged it anyway: any new private edge
        under the same (kind, target) key as some old public qualname
        fired, regardless of whether that old public qualname's OWN
        directive was still intact."""
        _write(
            tmp_path,
            "src/a.py",
            "def foo(x):\n    # frob:doc docs/x.md#anchor\n    return x\n",
        )
        _git_init(tmp_path)
        _write(
            tmp_path,
            "src/a.py",
            "def foo(x):\n"
            "    # frob:doc docs/x.md#anchor\n"
            "    return x\n"
            "\n"
            "\n"
            "def _bar_impl(y):\n"
            "    # frob:doc docs/x.md#anchor\n"
            "    return y\n",
        )
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/a.py::_bar_impl"]
        diff = Diff(base="HEAD", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.IN_PROGRESS)})
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        cov005 = [v for v in violations if v.rule == "COV005"]
        assert cov005 == [], cov005

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
    # frob:tests tests/gates_suite/test_coverage.py::TestCoverageGate.test_cov006_violation_carries_edge_src_as_symref kind="unit"  # noqa: E501
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
    # frob:tests tests/gates_suite/test_coverage.py::TestCoverageGate.test_cov006_waiver_does_not_blanket_suppress_the_whole_file kind="unit"  # noqa: E501
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
    # frob:tests \
    # tests/gates_suite/test_coverage.py::TestCoverageGate.test_is_symref_gates \
    # kind="unit"
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
    # frob:tests tests/gates_suite/test_coverage.py::TestCoverageGate.test_cov006_third_file_reachable_skips_unresolved_callee_sentinel kind="unit"  # noqa: E501
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

    # frob:ticket T-2550
    # frob:ticket T-2865
    def test_cov006_third_file_reachable_chases_relative_import_reexport(
        self, tmp_path: Path
    ) -> None:
        """T-2550 trace 1: a test reaches its bound private target through
        a public entrypoint re-exported via a RELATIVE `from .real import
        name` line (the common package-facade shape, e.g. `frob.vet.
        _capability`'s `from ._capability_scan import scan_file_
        capabilities`) -- `_cov006_module_path_to_file` needs an
        ABSOLUTE-dotted module path, and the facade's own `from ._real
        import real_entry` line names `._real` (leading dot). Before the
        `_cov006_resolve_relative_module` fix, `module_path.replace(".",
        "/")` turned that leading dot into a leading slash instead of the
        facade's own package, so the re-export hop silently failed to
        resolve to `_real.py` and the rescue never found the real `def`."""
        # frob:waive COV006 reason="T-2550 class: this test's own body calls a public \
        # entry point several hops from the private target, a shape build_call_graph \
        # structurally cannot see through; confirmed reachable by direct read"
        # frob:tests src/frob/gates/__init__.py::_cov006_resolve_relative_module
        from frob.gates import _cov006_third_file_reachable
        from frob.graph import Edge, EdgeKind

        _write(tmp_path, "src/pkg/_target_mod.py", "def _target(x):\n    return x\n")
        _write(
            tmp_path,
            "src/pkg/_real.py",
            "from ._target_mod import _target\n\n\n"
            "def real_entry(x):\n    return _target(x)\n",
        )
        _write(tmp_path, "src/pkg/facade.py", "from ._real import real_entry\n")
        _write(
            tmp_path,
            "tests/test_x.py",
            "from pkg.facade import real_entry\n\n"
            "# frob:tests src/pkg/_target_mod.py::_target\n"
            "def test_via_relative_facade():\n"
            "    assert real_entry(1) == 1\n",
        )
        edge = Edge(
            kind=EdgeKind.TESTS,
            src="tests/test_x.py::test_via_relative_facade",
            target="src/pkg/_target_mod.py::_target",
            origin="tests/test_x.py:1",
        )
        assert _cov006_third_file_reachable(tmp_path, edge) is True

    # frob:ticket T-2550
    def test_cov006_third_file_reachable_still_fires_through_relative_facade(
        self, tmp_path: Path
    ) -> None:
        """T-2550 must-still-fire control for the fix above: a test that
        imports the SAME relative-import facade shape but whose entrypoint
        genuinely never reaches the bound private target must still be
        flagged -- the relative-import resolution fix must not turn into a
        blanket rescue for every facade import regardless of real
        reachability."""
        from frob.gates import _cov006_third_file_reachable
        from frob.graph import Edge, EdgeKind

        _write(tmp_path, "src/pkg/_target_mod.py", "def _target(x):\n    return x\n")
        _write(
            tmp_path,
            "src/pkg/_real.py",
            "from ._target_mod import _target\n\n\n"
            # real_entry deliberately never calls `_target` -- the bound
            # symbol is genuinely unreached, not just hidden by relative
            # import resolution.
            "def real_entry(x):\n    return x\n",
        )
        _write(tmp_path, "src/pkg/facade.py", "from ._real import real_entry\n")
        _write(
            tmp_path,
            "tests/test_x.py",
            "from pkg.facade import real_entry\n\n"
            "# frob:tests src/pkg/_target_mod.py::_target\n"
            "def test_via_relative_facade_no_reach():\n"
            "    assert real_entry(1) == 1\n",
        )
        edge = Edge(
            kind=EdgeKind.TESTS,
            src="tests/test_x.py::test_via_relative_facade_no_reach",
            target="src/pkg/_target_mod.py::_target",
            origin="tests/test_x.py:1",
        )
        assert _cov006_third_file_reachable(tmp_path, edge) is False

    # frob:ticket T-2874
    def test_cov007_flags_doc_anchor_on_private_helper(self, tmp_path: Path) -> None:
        """T-0483: a `frob:doc` edge whose src symbol is PRIVATE fires
        COV007 -- doc anchors are for the public API surface. ERROR
        severity since T-2866/T-2873/T-2874 promoted it from WARN once
        the repo's live findings burned down to zero."""
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
        assert v.severity == Severity.ERROR
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

    # frob:ticket T-2549
    def test_cov007_silent_for_a_strata_node_whose_clearance_is_not_public(
        self, tmp_path: Path
    ) -> None:
        """T-2549: `.strata` symbols carry a SECURITY CLEARANCE in
        `RawSymbol.public` (`_walk_strata._build_symbol`), not python
        underscore privacy -- a `trusted` component node is not a private
        helper and COV007's "move it onto the public caller" remedy has no
        meaning for one."""
        # frob:tests src/frob/gates/__init__.py::_cov007
        _write(
            tmp_path,
            "design/x.strata",
            "module demo\n"
            "\n"
            "// frob:doc docs/x.md#arch\n"
            "node widgets : trusted {\n"
            "    clearance Internal;\n"
            "}\n",
        )
        _write(tmp_path, "docs/x.md", "# Arch\n")
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        diff = Diff(base="x", hunks=())
        tests = CollectedTests(node_ids=frozenset())
        violations = coverage_gate(tmp_path, snap, queue, diff, tests)
        assert not any(v.rule == "COV007" for v in violations)

    # frob:ticket T-2549
    def test_cov007_still_fires_for_a_python_private_helper_after_t2549(
        self, tmp_path: Path
    ) -> None:
        """T-2549 must-still-pass control: the narrowing above is keyed on
        the src FILE being non-python, so the python case it exists to
        catch is untouched."""
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
        assert _first_rule(violations, "COV007") is not None

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
    # tests/gates_suite/test_coverage.py::TestCoverageGate.test_todo003_fires_after_version_bump_since\
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
    # tests/gates_suite/test_coverage.py::TestCoverageGate.test_todo003_silent_when_no_version_bump_si\
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
    # tests/gates_suite/test_coverage.py::TestCoverageGate.test_todo003_silent_when_tic\
    # ket_closes
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
        # frob:tests src/frob/gates/_waive.py::_waive002_violations kind="unit"
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
# frob:ticket T-1398
# frob:ticket T-1435
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

    # frob:ticket T-1398
    def test_symbol_with_good_file_coverage_reports_real_branch_pct(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage
        # T-1398: a burn-down agent (2026-08-01, source_sha de76e283) saw
        # symbols in well-tested modules (src/frob/__main__.py at 81.2%
        # file-level line coverage) report exactly 0.0% branch coverage --
        # suspected as a broken symbol-level join. This locks the join's
        # actual behavior: a file with TWO symbols, one whose lines are all
        # hit and one whose lines are all missed, must report the FIRST
        # symbol's real (100.0%) branch percentage, not a deflated 0.0%
        # (direct investigation found no join defect -- see this ticket's
        # Done report for the full write-up and the measurement-side
        # follow-up filed instead).
        _write(
            tmp_path,
            "src/frob/pkg/a.py",
            "def covered(x):\n    return x\n\n\ndef uncovered(x):\n    return x\n",
        )
        snap = _snapshot(tmp_path)
        covered = snap.symbols["src/frob/pkg/a.py::covered"]
        uncovered = snap.symbols["src/frob/pkg/a.py::uncovered"]
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
            <line number="{covered.span[0]}" hits="1" branch="false"/>
            <line number="{covered.span[1]}" hits="1" branch="false"/>
            <line number="{uncovered.span[0]}" hits="0" branch="false"/>
            <line number="{uncovered.span[1]}" hits="0" branch="false"/>
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
        # File-level number is a healthy 50% -- matching the ticket's
        # "file coverage is good" premise.
        assert data.module_line["src/frob/pkg/a.py"] == 50.0
        # The covered symbol must report its REAL, non-deflated percentage.
        assert data.symbol_branch[covered.symref] == 100.0
        # The genuinely-uncovered symbol legitimately reports 0.0 -- this
        # is real signal (its lines truly were never hit), not an artifact
        # of a broken join; distinguishing the two is exactly what a
        # working join must do.
        assert data.symbol_branch[uncovered.symref] == 0.0

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

    # frob:ticket T-1406
    def test_module_join_fraction_excludes_files_outside_declared_cov_root(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage
        # frob:tests src/frob/gates/_coverage.py::_scope_known_paths_to_coverage_roots
        # T-1406: a real `make coverage` run's <sources> declares only
        # `src/frob` (the `--cov=` target), so a file OUTSIDE that root
        # (e.g. `tests/**`) can structurally never appear in coverage.xml
        # no matter how healthy the run is. Before this ticket,
        # module_join_fraction's denominator counted that file anyway,
        # deflating a perfectly healthy run's fraction toward
        # _DEFLATION_FLOOR for reasons unrelated to run health.
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(tmp_path, "tests/test_a.py", "def test_helper():\n    pass\n")
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
        # tests/test_a.py is a known .py module but outside the declared
        # src/frob cov root -- it must not count against the fraction.
        assert result.danger_ok.module_join_fraction == 1.0

    # frob:ticket T-1406
    def test_scope_known_paths_no_declared_roots_falls_back_unchanged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::_scope_known_paths_to_coverage_roots
        # T-1406: with no <sources> block to scope against (or every entry
        # unresolvable against this checkout), the old repo-wide denominator
        # is the only one available -- known_paths must pass through
        # unchanged rather than collapsing to nothing.
        from frob.gates._coverage import _scope_known_paths_to_coverage_roots

        known = frozenset({"src/frob/pkg/a.py", "tests/test_a.py"})
        assert _scope_known_paths_to_coverage_roots(known, ()) == known

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

    # frob:ticket T-1366
    def test_stamp_not_stale_when_files_unchanged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::is_stamp_stale kind="unit"
        from frob.gates._coverage import is_stamp_stale, load_stamp

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        (tmp_path / "coverage.xml").write_text("<coverage></coverage>")
        assert stamp_coverage(tmp_path).is_ok
        stamp = load_stamp(tmp_path)
        assert stamp is not None
        assert is_stamp_stale(tmp_path, stamp) is False

    # frob:ticket T-1366
    def test_stamp_stale_when_file_changes(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::is_stamp_stale kind="unit"
        from frob.gates._coverage import is_stamp_stale, load_stamp

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        (tmp_path / "coverage.xml").write_text("<coverage></coverage>")
        assert stamp_coverage(tmp_path).is_ok
        stamp = load_stamp(tmp_path)
        assert stamp is not None
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x + 1\n")
        assert is_stamp_stale(tmp_path, stamp) is True

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

    # frob:ticket T-1363
    def test_write_coverage_lock_refuses_downward_ratchet(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::write_coverage_lock
        # T-1363: a failed/partial run must never rewrite a committed
        # coverage-ratchet floor downward -- e.g. the real 2026-07-31
        # incident, src/frob/app/__init__.py 76.5% -> 16.2% from a failed
        # `make coverage` run. `write_coverage_lock` clamps a big drop to
        # the prior committed value unless `allow_decrease=True`.
        from frob.gates import CoverageData, load_coverage_lock, write_coverage_lock

        good = CoverageData(
            source_sha="good",
            symbol_branch={},
            module_line={"src/frob/app/__init__.py": 76.5},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        assert write_coverage_lock(tmp_path, good).is_ok
        bad = CoverageData(
            source_sha="bad-partial-run",
            symbol_branch={},
            module_line={"src/frob/app/__init__.py": 16.2},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        result = write_coverage_lock(tmp_path, bad)
        assert result.is_ok
        lock = load_coverage_lock(tmp_path)
        assert lock is not None
        assert lock["module_line"]["src/frob/app/__init__.py"] == 76.5

    # frob:ticket T-1401
    def test_write_coverage_lock_records_a_genuine_zero(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::write_coverage_lock
        # T-1401: T-1363's clamp had no carve-out for an exact 0.0, so a
        # module that genuinely stopped being executed kept its old high
        # number forever. Measured on main: the lock claimed 81.2% for
        # src/frob/__main__.py while that run's own coverage.xml recorded
        # 0 of 133 lines hit. That makes the lock hide the exact regression
        # a ratchet exists to catch, and it misled a real investigation.
        from frob.gates import CoverageData, load_coverage_lock, write_coverage_lock

        good = CoverageData(
            source_sha="good",
            symbol_branch={},
            module_line={"src/frob/__main__.py": 81.2},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        assert write_coverage_lock(tmp_path, good).is_ok
        zeroed = CoverageData(
            source_sha="module-no-longer-executed",
            symbol_branch={},
            module_line={"src/frob/__main__.py": 0.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        assert write_coverage_lock(tmp_path, zeroed).is_ok
        lock = load_coverage_lock(tmp_path)
        assert lock is not None
        assert lock["module_line"]["src/frob/__main__.py"] == 0.0

    # frob:ticket T-1401
    def test_unjoined_modules_are_enumerated_not_silently_omitted(self) -> None:
        # frob:tests src/frob/gates/_coverage.py::_unjoined_python_modules
        # T-1401 acceptance [2]: a low join fraction must name the modules
        # that failed to join. The bare ratio (0.53 on this repo) says only
        # "about half did not join" and sent one investigation chasing a
        # join defect that did not exist -- the shortfall was a denominator
        # counting tests/** that coverage.xml can never contain.
        from frob.gates._coverage import _unjoined_python_modules

        known = frozenset(
            {"src/a.py", "src/b.py", "src/c.py", "README.md", "tests/test_a.py"}
        )
        joined = {"src/a.py": 80.0, "src/c.py": 10.0}

        unjoined = _unjoined_python_modules(joined, known)

        # Names the exact missing .py modules, sorted, and never the non-.py
        # entries -- an enumeration a reader can act on, not a bare ratio.
        assert unjoined == ("src/b.py", "tests/test_a.py")
        assert "README.md" not in unjoined

    # frob:ticket T-1401
    def test_write_coverage_lock_still_clamps_a_nonzero_drop(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::write_coverage_lock
        # The carve-out above is exactly that -- a carve-out. T-1363's
        # protection against a partial run lowering the floor must survive
        # untouched for every drop that is not an exact zero.
        from frob.gates import CoverageData, load_coverage_lock, write_coverage_lock

        good = CoverageData(
            source_sha="good",
            symbol_branch={},
            module_line={"src/frob/app/__init__.py": 76.5},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        assert write_coverage_lock(tmp_path, good).is_ok
        partial = CoverageData(
            source_sha="partial",
            symbol_branch={},
            module_line={"src/frob/app/__init__.py": 16.2},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        assert write_coverage_lock(tmp_path, partial).is_ok
        lock = load_coverage_lock(tmp_path)
        assert lock is not None
        assert lock["module_line"]["src/frob/app/__init__.py"] == 76.5

    # frob:ticket T-1408
    def test_write_coverage_lock_small_drop_within_tolerance_not_clamped(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::write_coverage_lock
        # T-1408: T-1401's genuine-zero carve-out (test above) is `new_pct
        # == 0.0` exactly, never a threshold -- confirm the PRE-existing
        # `_LOCK_TOLERANCE` (2.0 points) behavior is unchanged for a small,
        # non-zero drop: a drop within tolerance writes through as-is
        # (never clamped), same as before T-1401 touched this function.
        from frob.gates import CoverageData, load_coverage_lock, write_coverage_lock

        good = CoverageData(
            source_sha="good",
            symbol_branch={},
            module_line={"src/frob/app/__init__.py": 76.5},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        assert write_coverage_lock(tmp_path, good).is_ok
        small_drop = CoverageData(
            source_sha="small-drop-within-tolerance",
            symbol_branch={},
            module_line={"src/frob/app/__init__.py": 75.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        assert write_coverage_lock(tmp_path, small_drop).is_ok
        lock = load_coverage_lock(tmp_path)
        assert lock is not None
        assert lock["module_line"]["src/frob/app/__init__.py"] == 75.0

    # frob:ticket T-1363
    def test_write_coverage_lock_allow_decrease_overrides_ratchet(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::write_coverage_lock
        # T-1363: a deliberate re-baseline (allow_decrease=True) must still
        # be able to lower the committed floor -- the ratchet guard only
        # refuses an ACCIDENTAL drop from a failed/partial measurement.
        from frob.gates import CoverageData, load_coverage_lock, write_coverage_lock

        good = CoverageData(
            source_sha="good",
            symbol_branch={},
            module_line={"src/frob/app/__init__.py": 76.5},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        assert write_coverage_lock(tmp_path, good).is_ok
        deliberate = CoverageData(
            source_sha="deliberate-rebaseline",
            symbol_branch={},
            module_line={"src/frob/app/__init__.py": 16.2},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        result = write_coverage_lock(tmp_path, deliberate, allow_decrease=True)
        assert result.is_ok
        lock = load_coverage_lock(tmp_path)
        assert lock is not None
        assert lock["module_line"]["src/frob/app/__init__.py"] == 16.2

    # frob:ticket T-1375
    def test_write_coverage_lock_records_an_audit_entry(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::write_coverage_lock
        # frob:tests src/frob/gates/_coverage.py::load_lock_audit_log
        # T-1375: a real incident found frob-coverage.lock.json modified
        # with no matching "write_coverage_lock: locked N module(s)" line
        # in either of two runs' logs -- log output alone was not durable
        # enough to attribute the write after the fact. Every successful
        # write_coverage_lock call must also append a durable, on-disk
        # audit entry naming the SAME source_sha, so a later investigation
        # can confirm (or fail to confirm) attribution without depending
        # on which terminal happened to capture the log line.
        from frob.gates import CoverageData, write_coverage_lock
        from frob.gates._coverage import load_lock_audit_log

        data = CoverageData(
            source_sha="attributable-sha",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 55.5},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        assert write_coverage_lock(tmp_path, data).is_ok

        entries = load_lock_audit_log(tmp_path)
        assert len(entries) == 1
        assert entries[0]["source_sha"] == "attributable-sha"
        assert entries[0]["module_count"] == 1
        assert isinstance(entries[0]["pid"], int)
        assert "written_at" in entries[0]

    # frob:ticket T-1375
    def test_write_coverage_lock_audit_log_appends_across_calls(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::write_coverage_lock
        # frob:tests src/frob/gates/_coverage.py::load_lock_audit_log
        # T-1375: the audit trail is append-only across the worktree's own
        # history -- a second successful write adds a second entry rather
        # than overwriting the first, so a full write history survives for
        # later investigation, not just the most recent write.
        from frob.gates import CoverageData, write_coverage_lock
        from frob.gates._coverage import load_lock_audit_log

        first = CoverageData(
            source_sha="first-sha",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 10.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        second = CoverageData(
            source_sha="second-sha",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 20.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        assert write_coverage_lock(tmp_path, first).is_ok
        assert write_coverage_lock(tmp_path, second).is_ok

        entries = load_lock_audit_log(tmp_path)
        assert [e["source_sha"] for e in entries] == ["first-sha", "second-sha"]

    # frob:ticket T-1375
    def test_load_lock_audit_log_missing_file_returns_empty(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_lock_audit_log
        # T-1375: no audit file at all (e.g. a lock committed from another
        # worktree, or written before this ticket's fix existed) reads as
        # an empty history -- "cannot confirm attribution" -- never a crash.
        from frob.gates._coverage import load_lock_audit_log

        assert load_lock_audit_log(tmp_path) == ()

    # frob:ticket T-1279
    def test_load_lock_audit_log_skips_malformed_line(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_lock_audit_log
        # A malformed line (not valid JSON) is skipped, not raised -- the
        # rest of a genuinely-append-only file must still parse.
        from frob.gates._coverage import load_lock_audit_log

        audit_path = tmp_path / ".frob" / "coverage-lock-audit.log"
        audit_path.parent.mkdir(parents=True)
        audit_path.write_text(
            '{"source_sha": "good-1", "module_count": 1}\n'
            "not-json-at-all\n"
            '{"source_sha": "good-2", "module_count": 2}\n'
        )
        entries = load_lock_audit_log(tmp_path)
        assert [e["source_sha"] for e in entries] == ["good-1", "good-2"]

    def test_write_coverage_lock_refuses_under_lease_violation(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::write_coverage_lock
        # A worktree-lease mismatch refuses the write outright (via
        # enforce_worktree_lease), never a partial/silent write.
        from frob.gates import CoverageData, GateError, write_coverage_lock

        _git_init(tmp_path)
        monkeypatch.setenv("FROB_WORKTREE", str(tmp_path / "somewhere-else"))
        data = CoverageData(
            source_sha="sha",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 10.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        result = write_coverage_lock(tmp_path, data)
        assert result.is_err
        assert result.danger_err == GateError.WorktreeLeaseViolation
        assert not (tmp_path / "frob-coverage.lock.json").exists()

    def test_load_coverage_lock_malformed_json_returns_none(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage_lock
        from frob.gates._coverage import load_coverage_lock

        (tmp_path / "frob-coverage.lock.json").write_text("not valid json {")
        assert load_coverage_lock(tmp_path) is None

    def test_load_coverage_lock_missing_returns_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_coverage_lock
        from frob.gates._coverage import load_coverage_lock

        assert load_coverage_lock(tmp_path) is None

    def test_load_stamp_missing_returns_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_stamp
        from frob.gates._coverage import load_stamp

        assert load_stamp(tmp_path) is None

    def test_load_stamp_malformed_json_returns_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::load_stamp
        from frob.gates._coverage import load_stamp

        stamp_path = tmp_path / ".frob" / "coverage-stamp"
        stamp_path.parent.mkdir(parents=True)
        stamp_path.write_text("not valid json {")
        assert load_stamp(tmp_path) is None

    # frob:ticket T-1180
    def test_stamp_coverage_refuses_below_deflation_floor(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::stamp_coverage
        # T-1180: extends TEST011's WARN-only deflation heuristic into a
        # hard stamp-time refusal -- a coverage.xml that joins too few of
        # the known modules (subprocess coverage silently dropped, the
        # `make coverage` incident this ticket exists for) must not stamp
        # at all, not stamp-then-warn. Needs >= _DEFLATION_MIN_KNOWN_MODULES
        # (20) known modules -- below that, the floor is sample-size noise
        # (see the sibling test below) and is deliberately skipped.
        for i in range(24):
            _write(tmp_path, f"src/frob/pkg/m{i}.py", "def helper(x):\n    return x\n")
        # Only 1 of 24 known modules shows up in coverage.xml -- well below
        # the 0.5 floor.
        xml = """<?xml version="1.0"?>
<coverage>
  <packages>
    <package>
      <classes>
        <class filename="src/frob/pkg/m0.py" line-rate="0.9">
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
        assert result.is_err
        assert result.danger_err == GateError.CoverageDeflated
        # Neither the stamp nor the lock was written.
        assert not (tmp_path / ".frob" / "coverage-stamp").exists()
        assert not (tmp_path / "frob-coverage.lock.json").exists()

    # frob:ticket T-1180
    def test_stamp_coverage_deflation_floor_skipped_below_min_known_modules(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::stamp_coverage
        # T-1180: a tiny repo/fixture (a handful of known modules, as most
        # of this repo's own system-test fixtures are) can legitimately
        # have a near-zero join fraction with no deflation involved --
        # there was only ever one module to begin with. Below
        # `_DEFLATION_MIN_KNOWN_MODULES` this must still stamp normally,
        # exactly like pre-T-1180 behavior (the regression this test
        # guards: T-1180's first landed version broke several existing
        # small-fixture system tests this exact way).
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        (tmp_path / "coverage.xml").write_text("<coverage></coverage>")
        snap = _snapshot(tmp_path)
        result = stamp_coverage(tmp_path, snap)
        assert result.is_ok
        assert (tmp_path / ".frob" / "coverage-stamp").exists()

    # frob:ticket T-1435
    def test_stamp_coverage_refuses_locally_scoped_run_via_provenance_drop(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::stamp_coverage
        # T-1435 (T-1407 finding 2): a locally-scoped `pytest --cov` run
        # (docs/guides/agent-playbook.md section 6b's sanctioned
        # workaround) can join 100% of the FEW modules it measured -- the
        # pre-existing `_DEFLATION_FLOOR` check alone reads this as clean,
        # because it only ever compares a run against ITSELF (its own
        # module_join_fraction). This fixture's snapshot only knows about
        # 2 modules (a small, ticket-scoped checkout), and coverage.xml
        # joins both of them fully -- but the last COMMITTED
        # frob-coverage.lock.json recorded 24 modules from a real full
        # run. The provenance check must catch that drop even though the
        # deflation floor alone would not.
        _write(tmp_path, "src/frob/pkg/m0.py", "def helper(x):\n    return x\n")
        _write(tmp_path, "src/frob/pkg/m1.py", "def helper(x):\n    return x\n")
        (tmp_path / "frob-coverage.lock.json").write_text(
            json.dumps(
                {
                    "source_sha": "priorsha",
                    "module_line": {f"src/frob/pkg/m{i}.py": 90.0 for i in range(24)},
                }
            )
        )
        xml = """<?xml version="1.0"?>
<coverage>
  <packages>
    <package>
      <classes>
        <class filename="src/frob/pkg/m0.py" line-rate="0.9">
          <lines><line number="2" hits="1" branch="false"/></lines>
        </class>
        <class filename="src/frob/pkg/m1.py" line-rate="0.9">
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
        assert result.is_err
        assert result.danger_err == GateError.CoverageDeflated
        # The committed lock must NOT be overwritten by the scoped run's
        # tiny module set -- T-1363's ratchet exists precisely so a
        # partial measurement cannot silently narrow committed history,
        # and this refusal must stop before write_coverage_lock is ever
        # reached at all.
        lock_text = (tmp_path / "frob-coverage.lock.json").read_text()
        assert json.loads(lock_text)["source_sha"] == "priorsha"
        assert len(json.loads(lock_text)["module_line"]) == 24

    # frob:ticket T-1435
    def test_stamp_coverage_provenance_check_skipped_without_committed_lock(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::stamp_coverage
        # T-1435: with no `frob-coverage.lock.json` on disk yet (a fresh
        # checkout, or the very first `make coverage` a repo ever runs),
        # there is no history to compare against -- the provenance check
        # must not fire, and stamping must succeed exactly as it did
        # before this ticket.
        _write(tmp_path, "src/frob/pkg/m0.py", "def helper(x):\n    return x\n")
        xml = """<?xml version="1.0"?>
<coverage>
  <packages>
    <package>
      <classes>
        <class filename="src/frob/pkg/m0.py" line-rate="0.9">
          <lines><line number="2" hits="1" branch="false"/></lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""
        (tmp_path / "coverage.xml").write_text(xml)
        assert not (tmp_path / "frob-coverage.lock.json").exists()
        snap = _snapshot(tmp_path)
        result = stamp_coverage(tmp_path, snap)
        assert result.is_ok
        assert (tmp_path / "frob-coverage.lock.json").exists()

    # frob:ticket T-1236
    def test_stamp_coverage_refuses_zero_canary_module(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage.py::stamp_coverage
        # T-0969/T-1180 found that `module_join_fraction` alone reads
        # clean on a run that silently dropped subprocess/CLI-entry
        # coverage: a module that never got traced still JOINS against
        # coverage.xml, just at 0% -- so the aggregate ratio can sit near
        # 1.0 even though a whole class of process went unmeasured. Every
        # module here (including the canary, src/frob/__main__.py) joins,
        # so the plain deflation floor alone would pass this fixture; only
        # the canary check (T-1236) catches it.
        for i in range(23):
            _write(tmp_path, f"src/frob/pkg/m{i}.py", "def helper(x):\n    return x\n")
        _write(tmp_path, "src/frob/__main__.py", "def main():\n    pass\n")
        classes = "\n".join(
            f'<class filename="src/frob/pkg/m{i}.py" line-rate="0.9">'
            '<lines><line number="2" hits="1" branch="false"/></lines></class>'
            for i in range(23)
        )
        xml = f"""<?xml version="1.0"?>
<coverage>
  <packages>
    <package>
      <classes>
        {classes}
        <class filename="src/frob/__main__.py" line-rate="0.0">
          <lines><line number="2" hits="0" branch="false"/></lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""
        (tmp_path / "coverage.xml").write_text(xml)
        snap = _snapshot(tmp_path)
        result = stamp_coverage(tmp_path, snap)
        assert result.is_err
        assert result.danger_err == GateError.CoverageDeflated
        assert not (tmp_path / ".frob" / "coverage-stamp").exists()
        assert not (tmp_path / "frob-coverage.lock.json").exists()

    # frob:ticket T-1236
    def test_stamp_coverage_canary_check_skipped_when_module_unknown(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage.py::stamp_coverage
        # A fixture/tiny-repo snapshot that never declares
        # src/frob/__main__.py at all must not be flagged by the canary
        # check -- it has nothing to say about a module that is not part
        # of this run's known set. Sample-size (_DEFLATION_MIN_KNOWN_
        # MODULES) is the gate that governs tiny repos in general; the
        # canary check only fires when the named module IS present and
        # reads exactly 0.0%.
        for i in range(24):
            _write(tmp_path, f"src/frob/pkg/m{i}.py", "def helper(x):\n    return x\n")
        classes = "\n".join(
            f'<class filename="src/frob/pkg/m{i}.py" line-rate="0.9">'
            '<lines><line number="2" hits="1" branch="false"/></lines></class>'
            for i in range(24)
        )
        xml = f"""<?xml version="1.0"?>
<coverage>
  <packages>
    <package>
      <classes>
        {classes}
      </classes>
    </package>
  </packages>
</coverage>
"""
        (tmp_path / "coverage.xml").write_text(xml)
        snap = _snapshot(tmp_path)
        result = stamp_coverage(tmp_path, snap)
        assert result.is_ok

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
# frob:ticket T-0545
# frob:ticket T-1180
# frob:ticket T-1363
# frob:ticket T-1371
class TestParseLineElFallbacks:
    """T-1371 widened `_parse_line_el`'s guards; these pin the fallback
    VALUES those guards compute, not merely that they do not crash. A
    guard that returns the wrong branch percentage is as broken as one
    that raises."""

    @staticmethod
    def _el(**attrs: str):
        import xml.etree.ElementTree as ET

        return ET.Element("line", attrs)

    # frob:tests src/frob/gates/_coverage.py::_parse_line_el kind="unit"
    def test_malformed_condition_coverage_with_hits_falls_back_to_full(self):
        """An unparseable `condition-coverage` on a HIT branch line must
        fall back to 100, not 0 -- the line demonstrably executed."""
        from frob.gates._coverage import _parse_line_el

        el = self._el(
            number="7",
            hits="3",
            branch="true",
            condition="x",
            **{"condition-coverage": "not-a-percentage"},
        )
        assert _parse_line_el(el) == (7, (3, 100))

    # frob:tests src/frob/gates/_coverage.py::_parse_line_el kind="unit"
    def test_malformed_condition_coverage_without_hits_falls_back_to_zero(self):
        """The same fallback on an UNHIT line must be 0, not 100 --
        otherwise a corrupt report silently reads as fully covered."""
        from frob.gates._coverage import _parse_line_el

        el = self._el(
            number="7",
            hits="0",
            branch="true",
            **{"condition-coverage": "not-a-percentage"},
        )
        assert _parse_line_el(el) == (7, (0, 0))

    # frob:tests src/frob/gates/_coverage.py::_parse_line_el kind="unit"
    def test_non_branch_line_uses_hits_only(self):
        """`branch` anything other than the literal "true" means the line
        is not a branch, so `condition-coverage` must be ignored."""
        from frob.gates._coverage import _parse_line_el

        el = self._el(
            number="4",
            hits="2",
            branch="false",
            **{"condition-coverage": "50% (1/2)"},
        )
        assert _parse_line_el(el) == (4, (2, 100))

    # frob:tests src/frob/gates/_coverage.py::_parse_line_el kind="unit"
    def test_non_integer_hits_is_none_not_a_crash(self):
        """The documented "junk -> None, never a crash" contract."""
        from frob.gates._coverage import _parse_line_el

        assert _parse_line_el(self._el(number="1", hits="lots")) is None
# frob:ticket T-1376
class TestConditionCoverageIsActuallyParsed:
    """T-1376: `branch_pct` must come from the REAL percentage, not
    degrade to hit/not-hit. Before this, `split("(")[-1]` left "1/2)",
    `int()` raised every time, and the except branch silently returned
    `100 if hits > 0 else 0` -- so on this repo's own coverage.xml the
    parser emitted only 0 and 100 while 1324 branch lines were partial."""

    @staticmethod
    def _el(**attrs: str):
        import xml.etree.ElementTree as ET

        return ET.Element("line", attrs)

    # frob:tests src/frob/gates/_coverage.py::_parse_line_el kind="unit"
    def test_partial_condition_coverage_is_read_verbatim(self):
        """The regression that matters: a half-covered branch must read 50,
        not round up to 100 just because the line was hit."""
        from frob.gates._coverage import _parse_line_el

        el = self._el(
            number="9",
            hits="1",
            branch="true",
            **{"condition-coverage": "50% (1/2)"},
        )
        assert _parse_line_el(el) == (9, (1, 50))

    # frob:tests src/frob/gates/_coverage.py::_parse_line_el kind="unit"
    def test_zero_and_full_condition_coverage_round_trip(self):
        """The two extremes must survive the same path, so a fix that only
        happens to work for 0/100 does not pass."""
        from frob.gates._coverage import _parse_line_el

        zero = self._el(
            number="1",
            hits="1",
            branch="true",
            **{"condition-coverage": "0% (0/2)"},
        )
        full = self._el(
            number="2",
            hits="4",
            branch="true",
            **{"condition-coverage": "100% (2/2)"},
        )
        assert _parse_line_el(zero) == (1, (1, 0))
        assert _parse_line_el(full) == (2, (4, 100))

    # frob:tests src/frob/gates/_coverage.py::_parse_line_el kind="unit"
    def test_three_way_partial_is_not_snapped_to_an_extreme(self):
        """A non-half partial, to catch any fix that special-cases 50."""
        from frob.gates._coverage import _parse_line_el

        el = self._el(
            number="5",
            hits="2",
            branch="true",
            **{"condition-coverage": "33% (1/3)"},
        )
        assert _parse_line_el(el) == (5, (2, 33))
# frob:ticket T-1824
class TestSuspectDeflatedSymbols:
    """`frob.gates._coverage._suspect_deflated_symbols`: the per-symbol
    deflation heuristic distinct from `_module_join_fraction`'s aggregate
    signal -- flags a symbol whose def line hit but every body line
    reads 0, the specific shape of a partial xdist worker-crash merge
    loss, corroborated by a `frob:tests` edge so a genuinely dead code
    path is never a false positive."""

    def test_def_line_hit_body_zero_flagged(self, tmp_path: Path) -> None:
        # frob:ticket T-1824
        # frob:tests src/frob/gates/_coverage.py::_suspect_deflated_symbols
        _write(
            tmp_path,
            "src/frob/pkg/a.py",
            "# frob:tests tests/test_pkg_a.py::test_helper\n"
            "def helper(x):\n    y = x + 1\n    return y\n",
        )
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::helper"]
        start, end = record.span
        hits_by_class_line = {
            "src/frob/pkg/a.py": {
                start: (1, 100),
                start + 1: (0, 0),
                end: (0, 0),
            }
        }
        from frob.gates._coverage import _suspect_deflated_symbols

        suspects = _suspect_deflated_symbols(snap, hits_by_class_line)
        assert record.symref in suspects

    def test_genuinely_dead_code_not_flagged_without_tests_edge(
        self, tmp_path: Path
    ) -> None:
        # frob:ticket T-1824
        # frob:tests src/frob/gates/_coverage.py::_suspect_deflated_symbols
        # No frob:tests edge here -- a symbol with no declared test
        # coverage must never be flagged, since a genuinely-unexercised
        # path is indistinguishable from lost worker data by the
        # per-line shape alone (this ticket's own corroboration
        # requirement).
        _write(
            tmp_path,
            "src/frob/pkg/a.py",
            "def dead(x):\n    y = x + 1\n    return y\n",
        )
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::dead"]
        start, end = record.span
        hits_by_class_line = {
            "src/frob/pkg/a.py": {
                start: (1, 100),
                start + 1: (0, 0),
                end: (0, 0),
            }
        }
        from frob.gates._coverage import _suspect_deflated_symbols

        suspects = _suspect_deflated_symbols(snap, hits_by_class_line)
        assert record.symref not in suspects

    def test_uniformly_covered_symbol_not_flagged(self, tmp_path: Path) -> None:
        # frob:ticket T-1824
        # frob:tests src/frob/gates/_coverage.py::_suspect_deflated_symbols
        _write(
            tmp_path,
            "src/frob/pkg/a.py",
            "# frob:tests tests/test_pkg_a.py::test_helper\n"
            "def helper(x):\n    y = x + 1\n    return y\n",
        )
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::helper"]
        start, end = record.span
        hits_by_class_line = {
            "src/frob/pkg/a.py": {
                start: (1, 100),
                start + 1: (1, 100),
                end: (1, 100),
            }
        }
        from frob.gates._coverage import _suspect_deflated_symbols

        suspects = _suspect_deflated_symbols(snap, hits_by_class_line)
        assert record.symref not in suspects

    def test_single_line_symbol_not_flagged(self, tmp_path: Path) -> None:
        # frob:ticket T-1824
        # frob:tests src/frob/gates/_coverage.py::_suspect_deflated_symbols
        # Only the def line itself was recorded -- nothing to compare a
        # body against, so this must not be judged either way.
        _write(
            tmp_path,
            "src/frob/pkg/a.py",
            "# frob:tests tests/test_pkg_a.py::test_helper\ndef helper(x): ...\n",
        )
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::helper"]
        start, _end = record.span
        hits_by_class_line = {"src/frob/pkg/a.py": {start: (1, 100)}}
        from frob.gates._coverage import _suspect_deflated_symbols

        suspects = _suspect_deflated_symbols(snap, hits_by_class_line)
        assert record.symref not in suspects

    def test_load_coverage_logs_warning_for_suspect_symbol(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:ticket T-1824
        # frob:tests src/frob/gates/_coverage.py::load_coverage
        # T-1824: load_coverage wires the heuristic in and logs a
        # WARNING when it fires -- not yet a gate Violation (that needs
        # frob.gates.__init__/_waive.py, outside this ticket's declared
        # scope; see the ticket's Done report), but the signal must not
        # be silently computed and discarded.
        _write(
            tmp_path,
            "src/frob/pkg/a.py",
            "# frob:tests tests/test_pkg_a.py::test_helper\n"
            "def helper(x):\n    y = x + 1\n    return y\n",
        )
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::helper"]
        start, end = record.span
        xml = f"""<?xml version="1.0"?>
<coverage>
  <sources>
    <source>{(tmp_path / "src/frob").resolve()}</source>
  </sources>
  <packages>
    <package>
      <classes>
        <class filename="pkg/a.py" line-rate="0.33">
          <lines>
            <line number="{start}" hits="1" branch="false"/>
            <line number="{start + 1}" hits="0" branch="false"/>
            <line number="{end}" hits="0" branch="false"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""
        (tmp_path / "coverage.xml").write_text(xml)
        with caplog.at_level("WARNING"):
            result = load_coverage(tmp_path, snap)
        assert result.is_ok
        assert any("per-symbol deflated" in rec.message for rec in caplog.records)


# frob:ticket T-0542
# frob:ticket T-0543
class TestCov002ScopeCoverage:
    def test_open_ticket_scope_covers_changed_symbol(self, tmp_path):
        """COV002 passes when a changed symbol's file is within an open
        ticket's declared scope -- one ticket covers a whole refactor."""
        import subprocess

        from frob.gates import GateConfig, run_gates
        from frob.tickets import (
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
    # frob:waive COV006 reason="T-1024: genuinely reachable via run_gates -> the SCOPE \
    # gate's job-table dispatch -> _scope_covers, but frob.graph.callgraph's \
    # best-effort BFS cannot trace through the gate job-table's dict-of-callables \
    # indirection; the binding is correct, the reachability heuristic just cannot see \
    # it"
    def test_ambiguous_overlapping_open_scopes_do_not_cover(self, tmp_path):
        """B10: two open, EQUALLY specific tickets whose scopes both cover
        the same file must NOT silently cover a changed symbol -- that is
        exactly the false-negative one broad open ticket used to grant
        everything under it."""
        import subprocess

        from frob.gates import GateConfig, run_gates
        from frob.tickets import (
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
    # frob:waive COV006 reason="T-1024: same reachability-heuristic gap as \
    # test_ambiguous_overlapping_open_scopes_do_not_cover above -- genuinely reachable \
    # via run_gates -> the SCOPE gate's job-table dispatch -> _scope_covers, just not \
    # provable by frob.graph.callgraph's best-effort BFS"
    def test_active_ticket_own_scope_wins_over_a_broader_open_ticket(self, tmp_path):
        """B10: the active ticket's own scope covers the symbol even when a
        second, broader open ticket ALSO happens to cover the same file --
        no ambiguity should be raised when the active ticket is one of the
        matches."""
        import subprocess

        from frob.gates import GateConfig, run_gates
        from frob.tickets import (
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
    # tests/gates_suite/test_coverage.py::TestCov002StrataModuleCoverage.test_module_le\
    # vel_ticket_edge_covers_nested_declaration
    def test_module_level_ticket_edge_covers_nested_declaration(
        self, tmp_path: Path
    ) -> None:
        """A `frob:ticket` directive on `module m` covers a changed nested
        `node` declaration -- no per-declaration edge required."""
        import subprocess

        from frob.gates import GateConfig, run_gates
        from frob.tickets import (
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
    # tests/gates_suite/test_coverage.py::TestCov002StrataModuleCoverage.test_declarati\
    # on_without_module_edge_still_fires
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
