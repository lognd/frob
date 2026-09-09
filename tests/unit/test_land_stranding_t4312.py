"""T-4312: closing/dropping any ticket can strand a LIVE directive naming
it -- T-4305 (a `frob:waive WIRE001 ... follow_up="T-4274"` orphaned by
T-4274's own close, breaking WIRE002) and T-4316 (a `frob:todo T-4298`
orphaned by T-4298's own close, breaking TODO002) were the same mechanism
firing twice in one day for two unrelated directive families. These tests
force the condition end to end: create a ticket, add a directive naming
it, close it, and assert the warning names the exact site -- plus the
unit-level dispatch table (`_strand_reference_for_edge`) that generalizes
past WIRE001 to the full stranding-capable family set.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from frob.graph import Edge, EdgeKind
from frob.tickets import TicketState, new_ticket
from frob.tickets._land import _strand_reference_for_edge, _stranding_warning_lines
from frob.tickets._store import atomic_write, ledger_path

# T-4312: reuse tests/unit/test_land_root_resolution.py's own git-fixture helpers
# (_run/_git_init/_commit_all/_spec/_make_closeable) rather than defining a fourth
# byte-identical copy -- DUP001 already flags this exact shape as duplicated across
# ~20 test modules, and every one of those files (unlike this brand-new one) is
# already named in design/frob.strata's testsuite exec/fs.write via-lists, so
# reusing their code keeps this file's own capability surface at zero new sites.
from tests.unit.test_land_root_resolution import (
    _commit_all,
    _git_init,
    _make_closeable,
    _spec,
)


def _edge(kind: EdgeKind, target: str, origin: str, **attrs: str) -> Edge:
    return Edge(src="pkg.mod.fn", kind=kind, target=target, origin=origin, attrs=attrs)


class TestStrandReferenceForEdge:
    """Unit coverage for the dispatch table itself -- the T-4312
    generalization past WIRE001-only."""

    def test_waive_wire001_follow_up_is_found(self) -> None:
        edge = _edge(
            EdgeKind.WAIVE, "WIRE001", "src/x.py:10", follow_up="T-9001", reason="r"
        )
        ref, kind_label, rule, remedy = _strand_reference_for_edge(edge)
        assert ref == "T-9001"
        assert kind_label.startswith("frob:waive WIRE001")
        assert rule == "WIRE002"
        assert remedy

    def test_waive_non_wire001_is_silent(self) -> None:
        edge = _edge(EdgeKind.WAIVE, "DUP001", "src/x.py:10", reason="r")
        ref, _, _, _ = _strand_reference_for_edge(edge)
        assert ref is None

    def test_waive_permanent_test_helper_is_silent(self) -> None:
        edge = _edge(
            EdgeKind.WAIVE,
            "WIRE001",
            "tests/test_x.py:5",
            permanent="true",
        )
        edge = edge.model_copy(update={"src": "tests/test_x.py::_helper"})
        ref, _, _, _ = _strand_reference_for_edge(edge)
        assert ref is None

    def test_todo_directive_is_found(self) -> None:
        edge = _edge(EdgeKind.TODO, "T-9001", "src/y.py:20")
        ref, kind_label, rule, remedy = _strand_reference_for_edge(edge)
        assert ref == "T-9001"
        assert kind_label == "frob:todo"
        assert rule == "TODO002"
        assert remedy

    def test_implicit_todo_from_debt_pairing_is_silent(self) -> None:
        """An implicit frob:todo (synthesized by dsl.py's
        `_debt_todo_coherence` for an unpaired `frob:debt`) shares its
        `origin` with the DEBT edge itself -- reporting both would name
        the same site twice for the same remedy."""
        edge = _edge(EdgeKind.TODO, "T-9001", "src/y.py:20", implicit="debt")
        ref, _, _, _ = _strand_reference_for_edge(edge)
        assert ref is None

    def test_debt_ticket_is_found(self) -> None:
        edge = _edge(EdgeKind.DEBT, "PERF004", "src/z.py:30", ticket="T-9001")
        ref, kind_label, rule, remedy = _strand_reference_for_edge(edge)
        assert ref == "T-9001"
        assert "frob:debt" in kind_label
        assert rule == "DEBT002"
        assert remedy

    def test_deprecated_ticket_is_found(self) -> None:
        edge = _edge(EdgeKind.DEPRECATED, "old_fn", "src/w.py:40", ticket="T-9001")
        ref, kind_label, rule, remedy = _strand_reference_for_edge(edge)
        assert ref == "T-9001"
        assert "frob:deprecated" in kind_label
        assert rule == "DEPR002"
        assert remedy

    def test_unrelated_edge_kinds_are_silent(self) -> None:
        for kind in (EdgeKind.TICKET, EdgeKind.DOC, EdgeKind.TESTS, EdgeKind.INVARIANT):
            edge = _edge(kind, "T-9001", "src/x.py:1")
            ref, _, _, _ = _strand_reference_for_edge(edge)
            assert ref is None, f"{kind} unexpectedly named a strandable ticket ref"


class TestStrandingWarningLines:
    """`_stranding_warning_lines` produces one self-contained, actionable
    line per site -- file, line, directive, gate rule, remedy, all
    together (T-4312's own design point: a bare 'something now dangles'
    costs another investigation)."""

    def test_message_names_file_line_directive_rule_and_remedy(self) -> None:
        from frob.tickets._land import _StrandedDirective

        site = _StrandedDirective(
            file="src/x.py",
            line=10,
            kind='frob:waive WIRE001 follow_up="..."',
            gate_rule="WIRE002",
            remedy='add permanent="true", or repoint follow_up=',
        )
        (line,) = _stranding_warning_lines("T-9001", (site,))
        assert "src/x.py:10" in line
        assert "WIRE002" in line
        assert "T-9001" in line
        assert "remedy:" in line

    def test_no_sites_produces_no_lines(self) -> None:
        assert _stranding_warning_lines("T-9001", ()) == ()


# ---------------------------------------------------------------------------
# End-to-end: force the actual condition through `transition()` -- create a
# ticket, add a live directive naming it, close it, assert the warning
# fires naming that exact site; assert a close with nothing referencing it
# stays silent.
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "main"
    _git_init(root)
    atomic_write(ledger_path(root), "# Tickets\n\n")
    (root / "src").mkdir()
    _commit_all(root, "init")
    return root


class TestTransitionWarnsOnStranding:
    """The verification the ticket's own body demands: force the
    condition, don't just assert the machinery in isolation."""

    def test_drop_warns_on_stranded_waive_follow_up(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T-4312's WARN reaches `frob ticket drop` too. Deliberately NOT
        exercised via `close`/DONE here: `frob.tickets._live_tracker.
        live_tracker_citations` (T-0854/T-1559) already REFUSES a direct
        close whose diff leaves a pre-existing `follow_up=` citation of
        the closing ticket untouched -- a stronger, pre-existing guard for
        exactly this one family that this ticket's own generalization does
        not need to duplicate on the DONE path. `drop_ticket` is NOT
        covered by that guard (`_transition_guard` only invokes
        `live_tracker_citations` for `to == TicketState.DONE`), so it is
        the real gap this test forces."""
        from frob.tickets._reporting import drop_ticket

        target = new_ticket(repo, _spec("target of a follow_up")).danger_ok
        holder = new_ticket(repo, _spec("holds the waiver")).danger_ok
        assert atomic_write(
            repo / "src" / "waiver.py",
            "def f():\n"
            "    pass\n"
            "\n"
            f'# frob:waive WIRE001 reason="x" follow_up="{target.id}"\n'
            "def g():\n"
            "    pass\n",
        ).is_ok
        _commit_all(repo, "add waiver site")

        with caplog.at_level(logging.WARNING):
            result = drop_ticket(repo, target.id, "no longer needed")
        assert result.is_ok

        matches = [
            r
            for r in caplog.records
            if "strands a directive" in r.message and target.id in r.message
        ]
        assert matches, f"expected a stranding warning naming {target.id}; got: " + str(
            [r.message for r in caplog.records]
        )
        assert any("waiver.py" in r.message for r in matches)
        assert any("WIRE002" in r.message for r in matches)
        # holder's own id must never appear as the stranded reference here
        assert not any(
            holder.id in r.message and "strands a directive" in r.message
            for r in caplog.records
        )

    def test_close_warns_on_stranded_todo(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        from frob.tickets import transition

        target = new_ticket(repo, _spec("target of a todo")).danger_ok
        assert atomic_write(
            repo / "src" / "todo_site.py",
            f"# frob:todo {target.id}\ndef stub():\n    raise NotImplementedError\n",
        ).is_ok
        _commit_all(repo, "add todo site")
        _make_closeable(repo, target.id)

        with caplog.at_level(logging.WARNING):
            result = transition(repo, target.id, TicketState.DONE)
        assert result.is_ok

        matches = [
            r
            for r in caplog.records
            if "strands a directive" in r.message and target.id in r.message
        ]
        assert matches
        assert any("todo_site.py" in r.message for r in matches)
        assert any("TODO002" in r.message for r in matches)

    def test_close_with_no_referencing_directives_is_silent(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        from frob.tickets import transition

        lonely = new_ticket(repo, _spec("nothing references this")).danger_ok
        assert atomic_write(repo / "src" / "plain.py", "def h():\n    return 1\n").is_ok
        _commit_all(repo, "add plain file")
        _make_closeable(repo, lonely.id)

        with caplog.at_level(logging.WARNING):
            result = transition(repo, lonely.id, TicketState.DONE)
        assert result.is_ok

        matches = [r for r in caplog.records if "strands a directive" in r.message]
        assert matches == []

    def test_drop_warns_on_stranded_todo(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        from frob.tickets._reporting import drop_ticket

        target = new_ticket(repo, _spec("target dropped instead")).danger_ok
        assert atomic_write(
            repo / "src" / "drop_site.py", f"# frob:todo {target.id}\n"
        ).is_ok
        _commit_all(repo, "add todo site for drop")

        with caplog.at_level(logging.WARNING):
            result = drop_ticket(repo, target.id, "no longer needed")
        assert result.is_ok

        matches = [
            r
            for r in caplog.records
            if "strands a directive" in r.message and target.id in r.message
        ]
        assert matches
        assert any("TODO002" in r.message for r in matches)
