import json
import multiprocessing
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

import frob.tickets._land_compose as _land_compose_mod
import frob.tickets._land_git_ops as _land_git_ops_mod
import frob.tickets._land_ledger_merge as _land_ledger_merge_mod
import frob.tickets._land_merge_zones as _land_merge_zones_mod
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import land, splice_ledger
from frob.tickets._models import (
    AcceptanceCriterion,
    LandError,
)
from frob.tickets._store import (
    atomic_write,
    ledger_path,
    load_all,
    write_ticket,
)
from tests._write_unchecked import _write_ticket_unchecked  # noqa: E402
from tests.ticket_land_suite.conftest import (
    _commit_all,
    _make_closeable,
    _run,
    _seed_v2_ticket,
    _spec,
    _t2114_concurrent_new_ticket,
)

pytestmark = pytest.mark.heavy_subprocess



# frob:ticket T-1194
class TestSpliceLedger:
    """`splice_ledger` -- the id-level merge tickets.md conflicts always go
    through, never git's line-level textual algorithm."""

    def test_disjoint_ids_both_kept(self, tmp_path: Path) -> None:
        ours = new_ticket(tmp_path, _spec("Ours"))
        assert ours.is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # A second, DISJOINT id on "their" side -- write it directly rather
        # than via new_ticket (two non-git tmp dirs would both allocate
        # T-0001, which is not the scenario under test: two SIDES of an
        # already-diverged ledger, one entry each).
        theirs_path = tmp_path / "theirs"
        theirs_path.mkdir()
        theirs_ticket = ours.danger_ok.model_copy(
            update={"id": "T-0002", "title": "Theirs"}
        )
        atomic_write(ledger_path(theirs_path), "# Tickets\n\n")
        assert write_ticket(theirs_path, theirs_ticket).is_ok
        theirs_text = ledger_path(theirs_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        assert "Ours" in spliced.danger_ok
        assert "Theirs" in spliced.danger_ok

    # frob:ticket T-1194
    def test_same_id_newer_state_wins(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_ledger_merge.py::splice_ledger kind="unit"
        created = new_ticket(tmp_path, _spec("Shared"))
        assert created.is_ok
        tid = created.danger_ok.id
        ours_text = ledger_path(tmp_path).read_text()

        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        assert "state: planned" in spliced.danger_ok
        assert "state: queued" not in spliced.danger_ok

    # frob:tests src/frob/tickets/_land_ledger_merge.py::splice_ledger kind="unit"
    def test_malformed_ours_propagates_as_err(self, tmp_path: Path) -> None:
        """A malformed `ours_text` (a ticket marker with no ```yaml
        frontmatter) must surface `_parse_ledger`'s error unchanged --
        `splice_ledger` never silently drops the ours side."""
        malformed_ours = "# Tickets\n\n<!-- ticket:T-0001 -->\nno frontmatter here\n"

        valid = new_ticket(tmp_path, _spec("Theirs"))
        assert valid.is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(malformed_ours, theirs_text)
        assert spliced.is_err

    # frob:tests src/frob/tickets/_land_ledger_merge.py::splice_ledger kind="unit"
    def test_malformed_theirs_propagates_as_err(self, tmp_path: Path) -> None:
        """A malformed `theirs_text` must ALSO surface as `Err` -- the
        second `_parse_ledger` call's error path is exercised
        independently of the first (both sides are fallible)."""
        valid = new_ticket(tmp_path, _spec("Ours"))
        assert valid.is_ok
        ours_text = ledger_path(tmp_path).read_text()

        malformed_theirs = "# Tickets\n\n<!-- ticket:T-0002 -->\nno frontmatter here\n"

        spliced = splice_ledger(ours_text, malformed_theirs)
        assert spliced.is_err




# frob:ticket T-1194
class TestSpliceOnlyTicket:
    """`_splice_only_ticket` (T-0479) -- the ledger splice scoped to ONE
    ticket id, the fix for the T-0475 sibling-resurrection incident."""

    # frob:tests src/frob/tickets/_land_ledger_merge.py::_splice_only_ticket kind="unit"
    def test_sibling_state_never_taken_from_worktree(self, tmp_path: Path) -> None:
        """Main has T-A queued (already requeued back from in-progress) and
        T-B queued. The worktree's stale copy still remembers T-A as
        in-progress. Landing T-B must not resurrect T-A's stale
        in-progress state -- only T-B's own block may come from the
        worktree."""
        created_a = new_ticket(tmp_path, _spec("Sibling A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id

        # Worktree's stale snapshot: T-A in-progress.
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid_a, TicketState.IN_PROGRESS).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        # Main has since requeued T-A back to queued, and separately
        # progressed T-B to planned.
        assert transition(tmp_path, tid_a, TicketState.QUEUED).is_ok
        assert transition(tmp_path, tid_b, TicketState.PLANNED).is_ok
        main_text = ledger_path(tmp_path).read_text()

        spliced = _land_git_ops_mod._splice_only_ticket(main_text, worktree_text, tid_b)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok)
        assert parsed.is_ok
        merged = parsed.danger_ok
        assert merged[tid_a].state == TicketState.QUEUED  # sibling untouched
        assert merged[tid_b].state == TicketState.PLANNED  # landed ticket's own block

    # frob:tests src/frob/tickets/_land_ledger_merge.py::_splice_only_ticket kind="unit"
    def test_landed_tickets_own_divergence_still_resolved(self, tmp_path: Path) -> None:
        """If the SAME ticket id genuinely diverges between main and the
        worktree, `_newer` still resolves it (via the scoped splice) --
        only sibling ids are excluded from consideration."""
        created = new_ticket(tmp_path, _spec("Landing"))
        assert created.is_ok
        tid = created.danger_ok.id
        main_text = ledger_path(tmp_path).read_text()

        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        spliced = _land_git_ops_mod._splice_only_ticket(main_text, worktree_text, tid)
        assert spliced.is_ok
        assert "state: planned" in spliced.danger_ok

    # frob:ticket T-0740
    # frob:ticket T-1194
    # frob:tests tests/test_ticket_land.py::TestSpliceOnlyTicket.test_render_that_would_drop_an_id_is_refused  # noqa: E501
    def test_render_that_would_drop_an_id_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0740: `_splice_only_ticket` (the T-0479 per-ticket `frob ticket
        land` path) was the one wholesale-ledger-commit site missing the
        T-0764 `_check_ledger_id_integrity` backstop that `splice_ledger`
        and `write_all`/`write_archive` all already ran. Pin the fix the
        same way `TestSpliceLedgerIdDropGuard` pins `splice_ledger`: patch
        the render step to simulate a future rendering regression that
        drops every section, and assert the scoped splice refuses rather
        than silently committing the truncated text."""
        created = new_ticket(tmp_path, _spec("A ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        main_text = ledger_path(tmp_path).read_text()

        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        def _dropping_render(tickets: dict) -> str:
            # Simulate a render bug: silently omit every ticket's section.
            return "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"

        monkeypatch.setattr(_land_ledger_merge_mod, "_render_ledger", _dropping_render)
        spliced = _land_git_ops_mod._splice_only_ticket(main_text, worktree_text, tid)
        assert spliced.is_err
        assert spliced.danger_err.name == "LedgerIntegrityViolation"

    # frob:tests src/frob/tickets/_land_ledger_merge.py::splice_ledger kind="unit"
    def test_whole_ledger_splice_never_regresses_a_sibling_from_done(
        self, tmp_path: Path
    ) -> None:
        """T-0537: `splice_ledger` (the whole-ledger merge used by `frob
        ticket merge-driver`) must never let a stale non-terminal copy of
        an already-DONE ticket win, regardless of which side
        (`ours`/`theirs`) carries it -- `_newer`'s state-rank tiebreak
        (terminal ranks highest) already makes this structurally
        impossible whenever a divergence goes THROUGH the splice; this is
        the regression-lock proving it, the exact incident class a
        hand-resolved `tickets.md` conflict (bypassing the splice
        entirely) produced instead (7 closed tickets resurrected to
        queued)."""
        created = new_ticket(tmp_path, _spec("Closed elsewhere"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]
        done_ticket = loaded.model_copy(update={"state": TicketState.DONE})
        assert write_ticket(tmp_path, done_ticket).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # theirs (a stale branch) still remembers it as queued.
        stale = done_ticket.model_copy(update={"state": TicketState.QUEUED})
        assert write_ticket(tmp_path, stale).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok)
        assert parsed.is_ok
        assert parsed.danger_ok[tid].state == TicketState.DONE



# frob:ticket T-1721
class TestCarryForwardOrRefuseSiblingEdits:
    """`_carry_forward_or_refuse_sibling_edits` / `_splice_only_ticket`'s
    `base_text` parameter (T-1721): the fix for the T-1637 field incident
    -- a legitimate sibling-ticket ledger edit made in the same worktree
    while landing a DIFFERENT ticket, silently and permanently dropped by
    T-0479's blanket main-wins sibling default, three separate times,
    before the pattern was diagnosed as structural rather than a one-off.

    All four tests share the same shape: two sibling tickets A (landing)
    and B (edited or not, on one or both sides); `base_text` is B's ledger
    state at the fork point, `main_text` is root's current state, and
    `worktree_text` is the worktree's finalized state."""

    # frob:ticket T-1721
    def _evidence_only(self, ticket, ids: tuple[str, ...]):  # noqa: ANN001, ANN202
        return ticket.model_copy(update={"evidence": ids})

    # frob:ticket T-1721
    # frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_worktree_only_edit_is_carried_forward  # noqa: E501
    def test_worktree_only_edit_is_carried_forward(self, tmp_path: Path) -> None:
        """The T-1637 shape exactly: B is DONE on both main and the
        worktree at the fork point; the worktree rebinds B's evidence
        (main never touches B again); landing A must carry B's rebind
        forward instead of reverting it to the base/main value."""
        created_a = new_ticket(tmp_path, _spec("Landing A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        loaded_b = load_all(tmp_path).danger_ok[tid_b]
        done_b = loaded_b.model_copy(
            update={
                "state": TicketState.DONE,
                "evidence": ("tests/test_x.py::test_old",),
                "body": loaded_b.body + "\n## Done report\n\nshipped\n",
            }
        )
        assert write_ticket(tmp_path, done_b).is_ok
        base_text = ledger_path(tmp_path).read_text()

        # Worktree: rebinds B's evidence (a legitimate correction, no
        # state change) while separately landing A.
        rebound_b = done_b.model_copy(
            update={"evidence": ("tests/test_x.py::test_new",)}
        )
        assert write_ticket(tmp_path, rebound_b).is_ok
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        # Main: only ever saw B's original (base) state -- never touched
        # it again. main_text == base_text for B's own section.
        main_text = base_text

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_a, base_text=base_text
        )
        assert spliced.is_ok, spliced.err
        from frob.tickets._store import _parse_ledger

        merged = _parse_ledger(spliced.danger_ok).danger_ok
        assert merged[tid_b].evidence == ("tests/test_x.py::test_new",)

    # frob:ticket T-1721
    # frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_main_only_edit_is_left_alone  # noqa: E501
    def test_main_only_edit_is_left_alone(self, tmp_path: Path) -> None:
        """Inverse of the above: main independently edited B since the
        base, the worktree never touched B at all -- main's edit must
        survive untouched (the ordinary, already-correct T-0479 case)."""
        created_a = new_ticket(tmp_path, _spec("Landing A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        base_text = ledger_path(tmp_path).read_text()

        # Worktree: never touches B again after the base snapshot.
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        # Main: independently progresses B.
        assert transition(tmp_path, tid_b, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid_b, TicketState.IN_PROGRESS).is_ok
        main_text = ledger_path(tmp_path).read_text()

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_a, base_text=base_text
        )
        assert spliced.is_ok, spliced.err
        from frob.tickets._store import _parse_ledger

        merged = _parse_ledger(spliced.danger_ok).danger_ok
        assert merged[tid_b].state == TicketState.IN_PROGRESS

    # frob:ticket T-1721
    # frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_both_sides_edit_the_same_way_converges_silently  # noqa: E501
    def test_both_sides_edit_the_same_way_converges_silently(
        self, tmp_path: Path
    ) -> None:
        """Both main and the worktree independently make the SAME edit to
        B (e.g. two agents both correctly rebind the same evidence id) --
        no conflict, both sides already agree, splice succeeds quietly."""
        created_a = new_ticket(tmp_path, _spec("Landing A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        base_text = ledger_path(tmp_path).read_text()

        loaded_b = load_all(tmp_path).danger_ok[tid_b]
        agreed_b = self._evidence_only(loaded_b, ("tests/test_x.py::test_shared",))
        assert write_ticket(tmp_path, agreed_b).is_ok
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()
        # main independently converges to the identical evidence value.
        main_text = (
            ledger_path(tmp_path)
            .read_text()
            .replace("state: planned", "state: queued", 1)
        )

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_a, base_text=base_text
        )
        assert spliced.is_ok, spliced.err

    # frob:ticket T-1721
    # frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_both_sides_edit_differently_refuses  # noqa: E501
    def test_both_sides_edit_differently_refuses(self, tmp_path: Path) -> None:
        """The genuine conflict this ticket exists to stop silently
        resolving: main and the worktree each independently rebind B's
        evidence to a DIFFERENT new id since the same base. Neither side
        is stale -- both made a real, independent edit. Must refuse
        (`SiblingLedgerEditConflict`), not silently pick one."""
        created_a = new_ticket(tmp_path, _spec("Landing A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        base_text = ledger_path(tmp_path).read_text()

        loaded_b = load_all(tmp_path).danger_ok[tid_b]
        worktree_b = self._evidence_only(loaded_b, ("tests/test_x.py::test_worktree",))
        assert write_ticket(tmp_path, worktree_b).is_ok
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        main_b = self._evidence_only(loaded_b, ("tests/test_x.py::test_main",))
        assert _write_ticket_unchecked(tmp_path, main_b).is_ok
        main_text = ledger_path(tmp_path).read_text()

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_a, base_text=base_text
        )
        assert spliced.is_err
        assert spliced.danger_err.name == "SiblingLedgerEditConflict"

    # frob:ticket T-1721
    # frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_no_base_available_falls_back_to_done_report_heuristic  # noqa: E501
    def test_no_base_available_falls_back_to_done_report_heuristic(
        self, tmp_path: Path
    ) -> None:
        """`base_text=None` (git could not resolve a merge-base) must
        degrade to the pre-T-1721 `_preserve_sibling_done_reports`
        heuristic, never a hard failure -- same shape
        `TestSiblingDoneReportPreserved` already pins for the no-base
        code path."""
        created_a = new_ticket(tmp_path, _spec("Landing A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        main_text = ledger_path(tmp_path).read_text()

        loaded_b = load_all(tmp_path).danger_ok[tid_b]
        worktree_b = loaded_b.model_copy(
            update={"body": loaded_b.body + "\n## Done report\n\nshipped\n"}
        )
        assert write_ticket(tmp_path, worktree_b).is_ok
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_a, base_text=None
        )
        assert spliced.is_ok, spliced.err
        from frob.tickets._store import _parse_ledger

        merged = _parse_ledger(spliced.danger_ok).danger_ok
        assert "## Done report" in merged[tid_b].body


# frob:ticket T-1194
class TestSiblingDoneReportPreserved:
    """T-0577: a real multi-ticket-worktree incident -- landing T-0386 in a
    worktree that ALSO carried sibling tickets T-0387/T-0388 (in-progress,
    review-gated, each with its own substantive Done report already
    written) spliced main's bare `queued` blocks for those siblings over
    the worktree's richer copies, erasing their Done reports and
    regressing their state. `_splice_only_ticket` must keep whichever side
    carries a substantive Done report when the OTHER side has none, even
    for a sibling id it does not otherwise touch."""

    # frob:tests src/frob/tickets/_land_ledger_merge.py::_splice_only_ticket kind="unit"
    def test_sibling_done_report_survives_landing_another_ticket(
        self, tmp_path: Path
    ) -> None:
        created_landed = new_ticket(tmp_path, _spec("Landed ticket"))
        assert created_landed.is_ok
        tid_landed = created_landed.danger_ok.id
        created_sibling = new_ticket(tmp_path, _spec("Sibling with done report"))
        assert created_sibling.is_ok
        tid_sibling = created_sibling.danger_ok.id

        # Worktree: sibling driven to in-progress with a substantive Done
        # report already written (review-gated, awaiting its OWN land).
        _make_closeable(tmp_path, tid_sibling)
        worktree_text = ledger_path(tmp_path).read_text()

        # Main: sibling is still a bare queued block (never advanced there
        # -- this worktree is the only place it has been worked).
        loaded = load_all(tmp_path).danger_ok
        bare_sibling = loaded[tid_sibling].model_copy(
            update={
                "state": TicketState.QUEUED,
                "evidence": (),
                "body": loaded[tid_sibling].body.split("## Done report")[0],
            }
        )
        merged = dict(loaded)
        merged[tid_sibling] = bare_sibling
        from frob.tickets._store import _render_ledger

        main_text = _render_ledger(merged)

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_landed
        )
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid_sibling].state == TicketState.IN_PROGRESS
        assert "## Done report" in parsed[tid_sibling].body
        assert parsed[tid_sibling].evidence == ("tests/test_x.py::test_ok",)

    # frob:tests src/frob/tickets/_land_ledger_merge.py::_splice_only_ticket kind="unit"
    def test_sibling_requeue_on_main_still_wins_when_neither_side_has_a_done_report(
        self, tmp_path: Path
    ) -> None:
        """The T-0479/T-0475 case must stay fixed: a sibling with NO Done
        report on either side, stale in-progress in the worktree and
        requeued on main, still resolves to main's requeued state -- the
        T-0577 preservation rule only fires when the worktree side actually
        carries a Done report main lacks, never as a blanket "worktree
        wins" rule."""
        created_landed = new_ticket(tmp_path, _spec("Landed ticket"))
        assert created_landed.is_ok
        tid_landed = created_landed.danger_ok.id
        created_sibling = new_ticket(tmp_path, _spec("Sibling requeued"))
        assert created_sibling.is_ok
        tid_sibling = created_sibling.danger_ok.id

        assert transition(tmp_path, tid_sibling, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid_sibling, TicketState.IN_PROGRESS).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        assert transition(tmp_path, tid_sibling, TicketState.QUEUED).is_ok
        main_text = ledger_path(tmp_path).read_text()

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_landed
        )
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid_sibling].state == TicketState.QUEUED


# frob:ticket T-0682
class TestSpliceLedgerRicherStatePreference:
    """T-0682: the git-merge-driver path (`splice_ledger`, invoked by the
    registered `tickets.md` merge driver for ANY `git merge`/`pull`/`rebase`
    -- not just `frob ticket land`'s own already-ticket-scoped internal
    splice) previously ranked a same-id divergence by state-rank alone,
    so a divergence where the Done-report side happened to sit at a LOWER
    state-rank than the reportless side still lost -- observed twice in the
    field landing T-0633/T-0637, where each land's merge-main-into-worktree
    stage regressed the landing ticket's own block back toward main's bare
    state (the Done report text itself survived only because it lives in
    the body, not the frontmatter `state:` field the rank comparison acted
    on).

    `_newer`'s fix is a QUALIFIED preference, not a blanket "report always
    wins": a first pass at this ticket made Done-report presence an
    unconditional override, which a reviewer caught as the INVERSE bug --
    a STALE report on a lower-rank block (e.g. a ticket requeued back down
    without its old report body ever getting stripped) would then beat a
    genuinely more-advanced, reportless side. The reported side now wins
    over a reportless one ONLY IF the reportless side does not STRICTLY
    outrank it; a strictly-higher-rank reportless side still wins. These
    tests mirror T-0577's two-direction shape, but against `splice_ledger`
    (the whole-ledger merge) directly rather than the ticket-scoped
    `_splice_only_ticket`."""

    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_report_side_still_wins_when_it_also_outranks_the_reportless_side  # noqa: E501
    def test_report_side_still_wins_when_it_also_outranks_the_reportless_side(
        self, tmp_path: Path
    ) -> None:
        """The original T-0682 field incident: `ours` (the worktree side,
        in a `merge main into worktree`) is `in-progress` (rank 2) with a
        substantive Done report; `theirs` (main) is a bare `queued` (rank
        0). The reported side is ALSO the higher-rank side here, so it
        wins under both the old (buggy) and new (qualified) rule -- this
        pins the incident that motivated the fix in the first place."""
        created = new_ticket(tmp_path, _spec("Landing ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(tmp_path).danger_ok[tid]
        with_report = loaded.model_copy(
            update={
                "body": loaded.body
                + "\n## Done report\n\nSubstantive report text here.\n"
            }
        )
        assert write_ticket(tmp_path, with_report).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        theirs = with_report.model_copy(
            update={
                "state": TicketState.QUEUED,
                "body": with_report.body.split("## Done report")[0],
            }
        )
        assert _write_ticket_unchecked(tmp_path, theirs).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "## Done report" in parsed[tid].body

    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_stale_report_on_lower_rank_still_loses_to_a_strictly_outranking_reportless_side  # noqa: E501
    def test_stale_report_on_lower_rank_still_loses_to_a_strictly_outranking_reportless_side(  # noqa: E501
        self, tmp_path: Path
    ) -> None:
        """The reviewer-caught inverse case: `ours` is a bare `queued`
        (rank 0) that still carries a STALE Done report (e.g. requeued
        back down without the report ever being stripped); `theirs` is
        `in-progress` (rank 2, strictly higher) with no report at all --
        genuine further rework since. An unqualified "report always wins"
        rule would resurrect the stale queued+report block here; the
        qualification must let the strictly-outranking reportless side
        win instead."""
        created = new_ticket(tmp_path, _spec("Landing ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]
        stale_with_report = loaded.model_copy(
            update={
                "body": loaded.body
                + "\n## Done report\n\nSubstantive report text here.\n"
            }
        )
        assert write_ticket(tmp_path, stale_with_report).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        theirs = stale_with_report.model_copy(
            update={
                "state": TicketState.IN_PROGRESS,
                "body": stale_with_report.body.split("## Done report")[0],
            }
        )
        assert _write_ticket_unchecked(tmp_path, theirs).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "## Done report" not in parsed[tid].body

    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_stale_report_on_lower_rank_still_loses_regardless_of_which_side_it_is_on  # noqa: E501
    def test_stale_report_on_lower_rank_still_loses_regardless_of_which_side_it_is_on(
        self, tmp_path: Path
    ) -> None:
        """Same divergence as the previous test, but with the stale report
        on `theirs` instead of `ours` -- the qualification is symmetric,
        not an accidental artifact of argument order."""
        created = new_ticket(tmp_path, _spec("Landing ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]
        stale_with_report = loaded.model_copy(
            update={
                "body": loaded.body
                + "\n## Done report\n\nSubstantive report text here.\n"
            }
        )
        assert write_ticket(tmp_path, stale_with_report).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        ours = stale_with_report.model_copy(
            update={
                "state": TicketState.IN_PROGRESS,
                "body": stale_with_report.body.split("## Done report")[0],
            }
        )
        assert _write_ticket_unchecked(tmp_path, ours).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "## Done report" not in parsed[tid].body

    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_neither_side_reporting_still_falls_back_to_state_rank  # noqa: E501
    def test_neither_side_reporting_still_falls_back_to_state_rank(
        self, tmp_path: Path
    ) -> None:
        """The T-0577/T-0537 non-regression guard stays intact: when
        NEITHER side carries a substantive Done report, the comparison
        falls back to plain state-rank exactly as before -- this is not a
        blanket "richer body always wins" rule."""
        created = new_ticket(tmp_path, _spec("Closed elsewhere"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]
        done_ticket = loaded.model_copy(update={"state": TicketState.DONE})
        assert write_ticket(tmp_path, done_ticket).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        stale = done_ticket.model_copy(update={"state": TicketState.QUEUED})
        assert write_ticket(tmp_path, stale).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.DONE



# frob:ticket T-0764
class TestSpliceLedgerPrefersEvidenceRichSideOnRankTie:
    """T-0764: the T-0753 field incident -- an in-flight worktree ticket
    with `start` + recorded evidence + a bound acceptance criterion but NO
    Done report yet, tied in state-rank (`in-progress`) with main's bare,
    reportless `in-progress` copy of the same id (e.g. after an
    archive/concurrent-ledger-rewrite reset the worktree's own view).
    Before T-0764 this fell straight to the old arbitrary `b`-wins
    tiebreak; now the evidence/acceptance-richer side must win."""

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie.test_evidence_and_acceptance_rich_side_wins_a_same_rank_reportless_tie  # noqa: E501
    def test_evidence_and_acceptance_rich_side_wins_a_same_rank_reportless_tie(
        self, tmp_path: Path
    ) -> None:
        created = new_ticket(
            tmp_path,
            TicketSpec(
                title="Landing ticket",
                kind=TicketKind.BUG,
                origin=Origin.AGENT,
                acceptance=(AcceptanceCriterion(text="GIVEN..WHEN..THEN.."),),
            ),
        )
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(tmp_path).danger_ok[tid]

        rich = loaded.model_copy(
            update={
                "evidence": ("tests/test_widget.py::test_x",),
                "acceptance": (
                    AcceptanceCriterion(
                        text="GIVEN..WHEN..THEN..",
                        evidence=("tests/test_widget.py::test_x",),
                    ),
                ),
            }
        )
        assert write_ticket(tmp_path, rich).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # `theirs`: same id, same rank, no Done report on EITHER side, but
        # bare -- no evidence, no bound acceptance -- exactly the
        # archive/concurrent-rewrite reset shape from the T-0753 incident.
        bare = loaded.model_copy(update={"evidence": (), "acceptance": ()})
        assert _write_ticket_unchecked(tmp_path, bare).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].evidence == ("tests/test_widget.py::test_x",)
        assert parsed[tid].acceptance[0].evidence == ("tests/test_widget.py::test_x",)

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie.test_acceptance_binding_unioned_even_when_the_reportless_higher_rank_side_wins  # noqa: E501
    def test_acceptance_binding_unioned_even_when_the_reportless_higher_rank_side_wins(
        self, tmp_path: Path
    ) -> None:
        """The `_union_acceptance` twin of D-09's `_union_evidence`: even
        when the WINNING side is picked for some other reason (here, a
        strictly higher rank), a criterion binding the LOSING side already
        had must not be silently dropped."""
        created = new_ticket(
            tmp_path,
            TicketSpec(
                title="Landing ticket",
                kind=TicketKind.BUG,
                origin=Origin.AGENT,
                acceptance=(AcceptanceCriterion(text="GIVEN..WHEN..THEN.."),),
            ),
        )
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]

        # `ours`: bare queued (rank 0) but with the criterion already bound.
        bound_but_low_rank = loaded.model_copy(
            update={
                "evidence": ("tests/test_widget.py::test_x",),
                "acceptance": (
                    AcceptanceCriterion(
                        text="GIVEN..WHEN..THEN..",
                        evidence=("tests/test_widget.py::test_x",),
                    ),
                ),
            }
        )
        assert write_ticket(tmp_path, bound_but_low_rank).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # `theirs`: strictly higher rank (in-progress), unbound criterion,
        # no Done report -- this side wins on rank, but must inherit the
        # OTHER side's binding rather than dropping it.
        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid, TicketState.IN_PROGRESS).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "tests/test_widget.py::test_x" in parsed[tid].evidence
        assert parsed[tid].acceptance[0].evidence == ("tests/test_widget.py::test_x",)



# frob:ticket T-1194
class TestSpliceLedgerIdDropGuard:
    """The structural guard the T-0367 incident demands: `splice_ledger`
    refuses loudly rather than silently committing a merge that drops an
    id (markerless-block class) or produces unparseable output."""

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard.test_a_side_only_id_missing_from_theirs_survives_the_splice  # noqa: E501
    def test_a_side_only_id_missing_from_theirs_survives_the_splice(
        self, tmp_path: Path
    ) -> None:
        """Sanity: an id present on only ONE side (never archived) is not
        itself an integrity violation -- the normal union-by-id case."""
        created = new_ticket(tmp_path, _spec("Ours-only ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        ours_text = ledger_path(tmp_path).read_text()
        theirs_text = "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert tid in parsed

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard.test_malformed_side_is_refused_not_silently_treated_as_empty  # noqa: E501
    def test_malformed_side_is_refused_not_silently_treated_as_empty(
        self, tmp_path: Path
    ) -> None:
        """A hand-corrupted input ledger (a marker present but its yaml
        frontmatter fence broken) fails `_parse_ledger` up front --
        `splice_ledger` must propagate that `Err`, never silently treat the
        unparseable side as if it carried zero tickets (which would make
        every id on the OTHER, well-formed side look like a one-sided
        addition instead of a real divergence needing a human's eyes)."""
        created = new_ticket(tmp_path, _spec("A ticket"))
        assert created.is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # Marker present, but no ```yaml fence follows it at all.
        theirs_text = "# Tickets\n\n<!-- ticket:T-9999 -->\nno yaml fence here\n"

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_err

    # frob:ticket T-0764
    # frob:ticket T-1194
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard.test_render_that_would_drop_an_id_is_refused  # noqa: E501
    def test_render_that_would_drop_an_id_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Direct unit-level pin on the guard itself: if the render step
        (patched here to simulate a future rendering regression) drops an
        id `_merge_ledger_tickets` produced, `splice_ledger` must refuse
        rather than commit the truncated text."""
        created = new_ticket(tmp_path, _spec("A ticket"))
        assert created.is_ok
        ours_text = ledger_path(tmp_path).read_text()
        theirs_text = "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"

        def _dropping_render(tickets: dict) -> str:
            # Simulate a render bug: silently omit every ticket's section.
            return "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"

        monkeypatch.setattr(_land_ledger_merge_mod, "_render_ledger", _dropping_render)
        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_err
        assert spliced.danger_err.name == "LedgerIntegrityViolation"


class TestLedgerBothSidesAppend:
    """Incident class 2: main gets a new ticket appended AFTER the worktree
    branched, and the worktree independently appends its own new ticket --
    a textual same-region conflict in tickets.md that must resolve as
    "keep both", not as a real conflict requiring a human."""

    def test_both_sides_append_merges_cleanly(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-g", str(wt)], repo)

        created_wt = new_ticket(
            wt, _spec("Worktree ticket", scope=("src/wt_thing.py",))
        )
        assert created_wt.is_ok
        wt_tid = created_wt.danger_ok.id
        _make_closeable(wt, wt_tid)
        (wt / "src" / "wt_thing.py").write_text("# from worktree\n")
        _commit_all(wt, "worktree ticket + feature")

        # Main independently gains a new ticket AFTER the worktree branched.
        created_main = new_ticket(repo, _spec("Main-side ticket"), no_commit=True)
        assert created_main.is_ok
        main_tid = created_main.danger_ok.id
        _commit_all(repo, "main-side ticket")

        result = land(repo, wt_tid, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id

        landed = load_all(repo)
        assert landed.is_ok
        assert final_id in landed.danger_ok
        assert main_tid in landed.danger_ok
        assert landed.danger_ok[final_id].state == TicketState.DONE


class TestLedgerV2LandMergeStory:
    """T-1258: ledger v2's native-git merge story for `frob ticket land` --
    disjoint `tickets/T-####/` directories merge with zero custom
    resolution (AC2), and a genuine same-ticket-file conflict surfaces as
    an ordinary git conflict, never a silent splice (AC3)."""

    def test_disjoint_v2_tickets_land_with_no_custom_merge(self, v2_repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = v2_repo.parent / "wt-v2-a"
        _run(["git", "worktree", "add", "-b", "feature-v2-a", str(wt)], v2_repo)

        created = new_ticket(wt, _spec("Add widget v2", scope=("src/widget.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "widget.py").write_text("# new widget\n")
        _commit_all(wt, "add widget v2")

        # Main gains a DIFFERENT ticket's own directory after the worktree
        # branched -- a real merge, disjoint ticket dirs on both sides.
        other = _seed_v2_ticket(v2_repo, "T-3005", scope=("src/other.py",))
        assert other.id == "T-3005"
        _commit_all(v2_repo, "main gains sibling v2 ticket T-3005")

        result = land(v2_repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        # No monofile splice happened -- there is no monofile in v2 mode.
        assert report.ledger_spliced is False

        landed = load_all(v2_repo)
        assert landed.is_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE
        assert "T-3005" in landed.danger_ok
        assert (v2_repo / "tickets" / "T-3005" / "ticket.md").exists()
        assert (v2_repo / "src" / "widget.py").exists()
        assert not (v2_repo / "tickets.md").exists()

    def test_same_ticket_conflict_surfaces_loudly_no_splice(
        self, v2_repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        #
        # T-2289 superseded this test's original AC3 claim ("a same-
        # ticket conflict is always left conflicted, never resolved by
        # picking a side") for the ONE case where "picking a side" is
        # actually the playbook's own mechanical rule: a conflict where
        # the LANDING ticket's own row diverges from main's. That case is
        # now auto-resolved by keeping the newer state (`_newer`,
        # T-2289's `_resolve_self_conflict_by_newer_state`) instead of
        # requiring manual `git merge` resolution -- see
        # `TestSelfConflictAutoResolve` in
        # tests/unit/test_land_sibling_regression.py for the dedicated
        # must-pass/must-fail pair. AC3's "never resolved by picking a
        # side" claim still holds for every OTHER kind of conflict (a
        # genuine sibling's own row, any file outside a ticket's own
        # directory) -- unchanged by this fix.
        wt = v2_repo.parent / "wt-v2-b"
        _run(["git", "worktree", "add", "-b", "feature-v2-b", str(wt)], v2_repo)

        # Worktree finalizes T-3000 AND retitles it as part of the same edit.
        _make_closeable(wt, "T-3000")
        wt_ticket = load_all(wt).danger_ok["T-3000"]
        assert write_ticket(
            wt, wt_ticket.model_copy(update={"title": "Renamed by worktree"})
        ).is_ok
        _commit_all(wt, "worktree finalizes and retitles T-3000")

        # Main independently retitles the SAME ticket's SAME field, after
        # the branch point -- a genuine same-line textual conflict on
        # tickets/T-3000/ticket.md. T-2079 landed `enforce_ticket_
        # ownership`, which correctly refuses a `write_ticket` call from
        # main against a ticket currently leased to the worktree (the
        # T-1617 shape this scenario would otherwise BE) -- so this needs
        # to land the SAME textual edit as a raw file write instead, the
        # way an out-of-band edit (a direct commit, a cherry-pick, a
        # different tool entirely) would actually reach main's checkout
        # without ever going through frob's own ownership-guarded API.
        ticket_path = v2_repo / "tickets" / "T-3000" / "ticket.md"
        original_text = ticket_path.read_text()
        assert "title: Seed" in original_text
        ticket_path.write_text(
            original_text.replace("title: Seed", "title: Renamed by main", 1)
        )
        _commit_all(v2_repo, "main retitles T-3000")

        # T-2289: the worktree's copy (in_progress, evidence + Done
        # report) strictly outranks main's stale copy (still queued) --
        # `_newer` picks the worktree's side, so this now auto-resolves
        # and the dry-run reports clean instead of refusing.
        result = land(v2_repo, "T-3000", wt, dry_run=True)
        assert result.is_ok, (
            f"self-conflict on T-3000's own row failed to auto-resolve: "
            f"{result.danger_err if result.is_err else None}"
        )




# frob:ticket T-1036
class TestSquashSpliceLedgerChurn:
    """T-1036 regression: a concurrent single-ticket write against `root`
    landing in the window between `land`'s squash-merge and its own
    ledger splice must survive, never be silently overwritten by the
    splice's (previously stale) base-text snapshot."""

    # frob:tests tests/test_ticket_land.py::TestSquashSpliceLedgerChurn.test_concurrent_write_between_squash_and_splice_survives_land  # noqa: E501
    # T-3144: this test's own monkeypatch target was stale (patched
    # `_land_squash`'s `run_argv`, but T-3121's disposable-stage flip
    # moved the actual `git merge --squash` call into `_land_compose`'s
    # own copy, called directly from `_land.py`) -- fixed below to target
    # the real call site.
    #
    # T-3163 fixed the real production regression this test targets
    # (root's `ledger_lock` now spans the WHOLE disposable-worktree
    # compose, so a concurrent sibling write during that window can no
    # longer race the splice). That widening exposed a SEPARATE,
    # pre-existing test-infra artifact (T-3174): `_t2114_concurrent_
    # new_ticket` used to run in a `multiprocessing.get_context("fork")`
    # child. Once `ledger_lock` is held by the PARENT at the fork point,
    # the forked child inherits a COPY of `_lock_local`'s thread-local
    # `held` dict (already containing the parent's (path -> (fd, depth))
    # entry) AND the same open-file-description `fd` for the lock file
    # (POSIX flock state belongs to the open file description, not the
    # process) -- so the child's own `ledger_lock()` call finds the
    # inherited entry and takes the "already held, bump depth" reentrancy
    # branch without ever contending for the lock, even though it is a
    # genuinely separate OS process with no legitimate claim to it. Using
    # `spawn` instead (a genuinely independent process, no inherited fd
    # or thread-local state -- verified standalone against T-3163's fixed
    # production code before landing this) makes the simulation honest to
    # the real-world concurrent-writer case again, and the test passes.
    def test_concurrent_write_between_squash_and_splice_survives_land(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-race", str(wt)], repo)
        created = new_ticket(wt, _spec("Race widget", scope=("src/widget.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "widget.py").write_text("# race widget\n")
        _commit_all(wt, "add race widget")

        # T-3121 (T-3144 fallout): `git merge --squash` now runs inside
        # `_land_compose.compose_squash_in_disposable_worktree` (called
        # directly from `_land.py`, against a DISPOSABLE stage worktree,
        # never `_land_squash`'s own copy of `run_argv`) -- patching
        # `_land_squash_mod.run_argv` alone never observes this call
        # post T-3121.
        real_run_argv = _land_compose_mod.run_argv
        result_path = repo.parent / "t2114-concurrent-result.json"
        injected: dict[str, Any] = {"done": False, "proc": None}

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            result = real_run_argv(argv, **kwargs)
            # Fire exactly once, right after the squash-merge -- the
            # earliest possible moment `root`'s working tree has the
            # worktree's finalized branch content, and (before this
            # ticket's fix) exactly the window `_squash_and_splice_ledger`
            # used to build its splice from a snapshot taken BEFORE this
            # point, silently discarding anything written here. T-2114:
            # spawn the concurrent write in a SEPARATE PROCESS and return
            # immediately (non-blocking) instead of calling `new_ticket`
            # synchronously in-process -- see `_t2114_concurrent_new_
            # ticket`'s own docstring for why the synchronous, in-process
            # version deadlocked.
            if (
                not injected["done"]
                and "merge" in argv
                and "--squash" in argv
                and result.is_ok
                and result.danger_ok.returncode == 0
            ):
                injected["done"] = True
                # T-3174: `spawn`, not `fork` -- see the class docstring
                # above `test_concurrent_write_between_squash_and_splice_
                # survives_land` for why a forked child spuriously skips
                # real lock contention against a parent that already
                # holds `ledger_lock` at the fork point.
                ctx = multiprocessing.get_context("spawn")
                proc = ctx.Process(
                    target=_t2114_concurrent_new_ticket, args=(repo, result_path)
                )
                proc.start()
                injected["proc"] = proc
            return result

        monkeypatch.setattr(_land_compose_mod, "run_argv", _fake_run_argv)

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert injected["done"] is True

        proc = injected["proc"]
        assert proc is not None
        proc.join(timeout=60)
        assert not proc.is_alive(), "concurrent new_ticket() child never finished"
        payload = json.loads(result_path.read_text())
        assert payload["ok"], payload
        sibling_id = payload["id"]

        landed = load_all(repo)
        assert landed.is_ok
        assert sibling_id in landed.danger_ok
        assert landed.danger_ok[result.danger_ok.final_id].state == TicketState.DONE



# frob:ticket T-1002
class TestUnionZoneMerge:
    """T-1002: append-only union-merge for the three chronic conflict
    hotspots (`[gates.severity]`, `_KNOWN_GATE_RULES`, `docs/audits/*.md`
    remediation logs) -- concurrent distinct appends compose with zero
    manual resolution; a true same-key contradiction still refuses."""

    def test_keyed_lines_union_composes(self) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestUnionZoneMerge.test_keyed_lines_union_composes
        ours = '# comment for A\nRULEA = "error"\n'
        theirs = '# comment for B\nRULEB = "warn"\n'
        merged = _land_merge_zones_mod._union_keyed_chunks(
            ours, theirs, re.compile(r"^(?P<key>[A-Za-z0-9]+)\s*=")
        )
        assert merged is not None
        assert 'RULEA = "error"' in merged
        assert 'RULEB = "warn"' in merged

    def test_keyed_lines_union_refuses(self) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestUnionZoneMerge.test_keyed_lines_union_refuses
        ours = 'RULEA = "error"\n'
        theirs = 'RULEA = "warn"\n'
        merged = _land_merge_zones_mod._union_keyed_chunks(
            ours, theirs, re.compile(r"^(?P<key>[A-Za-z0-9]+)\s*=")
        )
        assert merged is None

    def test_resolve_stages(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestUnionZoneMerge.test_resolve_stages
        target = repo / "frob.toml"
        target.write_text(
            "[gates.severity]\n"
            "# frob-zone-start gates.severity T-1002\n"
            "<<<<<<< HEAD\n"
            'RULEA = "error"\n'
            "=======\n"
            'RULEB = "warn"\n'
            ">>>>>>> main\n"
            "# frob-zone-end gates.severity T-1002\n"
        )
        _commit_all(repo, "conflict marker fixture")
        resolved = _land_merge_zones_mod._resolve_union_zone_conflicts(
            repo, {"frob.toml"}
        )
        assert resolved.is_ok
        assert resolved.danger_ok == frozenset()
        content = target.read_text()
        assert 'RULEA = "error"' in content
        assert 'RULEB = "warn"' in content
        assert "<<<<<<<" not in content

    def test_append_only_union_concatenates(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestUnionZoneMerge.test_append_only_union_concatenates  # noqa: E501
        ours = "## Remediation log (T-A)\nfixed thing A\n"
        theirs = "## Remediation log (T-B)\nfixed thing B\n"
        merged = _land_merge_zones_mod._union_append_only(ours, theirs)
        assert "T-A" in merged and "T-B" in merged


# frob:ticket T-1332
class TestRenameAwareWaiveDeletionAttribution:
    """T-1332 acceptance [1]: `_waive_deletions_in_diff` reads the
    pre-image path off the hunk's file header (`--- a/<path>`), which for
    a pure rename+edit is the file's OLD name, not the new one a scope
    glob would actually match -- untested on both the uncommitted (T-1323)
    and committed (T-1326) checks before this ticket."""

    # frob:ticket T-1332
    def test_committed_waiver_deleted_inside_a_rename_attributes_to_old_path(
        self, repo: Path
    ) -> None:
        """A `frob:waive` deleted in the SAME commit that renames its file
        (`git mv old new` + edit) must be attributed to a real path this
        guard can evaluate scope-ownership against -- proving WHICH path
        (old or new) `_committed_out_of_scope_waive_deletions` actually
        uses, per the ticket's own "test proves which" acceptance wording.
        Declaring the OLD path in scope must suffice to allow the land
        (this is the behavior as implemented: the hunk's pre-image path is
        what `git diff --no-color -U0` reports as the file the `-` line
        belongs to)."""
        # frob:tests \
        # tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution.test_commi\
        # tted_waiver_deleted_inside_a_rename_attributes_to_old_path
        (repo / "src" / "old.py").write_text(
            '# frob:waive PERF001 reason="stale, being removed by this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add old.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-rename-1", str(wt)], repo)

        created = new_ticket(
            wt, _spec("Retire stale waiver via rename", scope=("src/old.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        _run(["git", "mv", "src/old.py", "src/new.py"], wt)
        (wt / "src" / "new.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "rename old.py to new.py, dropping the stale waiver")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    # frob:ticket T-1332
    def test_committed_waiver_deleted_inside_a_rename_out_of_scope_still_refuses(
        self, repo: Path
    ) -> None:
        """The mirror of the test above: when NEITHER the old nor the new
        path is in the landing ticket's scope, a waiver dropped inside a
        rename must still refuse -- proving the rename does not
        accidentally become a laundering vector (a rename any agent could
        perform to dodge the guard) on top of proving which path is
        checked."""
        # frob:tests \
        # tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution.test_commi\
        # tted_waiver_deleted_inside_a_rename_out_of_scope_still_refuses
        (repo / "src" / "old.py").write_text(
            '# frob:waive PERF001 reason="genuinely needed, not this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add old.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-rename-2", str(wt)], repo)

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        _run(["git", "mv", "src/old.py", "src/new.py"], wt)
        (wt / "src" / "new.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "unrelated rename that happens to drop a waiver")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_err
        assert result.danger_err == LandError.OutOfScopeWaiveDeletion

    # frob:ticket T-1332
    def test_uncommitted_waiver_deleted_inside_a_rename_attributes_to_old_path(
        self, repo: Path
    ) -> None:
        """The UNCOMMITTED (T-1323) mirror of the committed-history rename
        test above: `git mv` + edit left dirty (not yet committed) must
        still be attributed correctly when the OLD path is in scope."""
        # frob:tests \
        # tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution.test_uncom\
        # mitted_waiver_deleted_inside_a_rename_attributes_to_old_path
        (repo / "src" / "old.py").write_text(
            '# frob:waive PERF001 reason="stale, being removed by this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add old.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-rename-3", str(wt)], repo)

        created = new_ticket(
            wt, _spec("Retire stale waiver via rename", scope=("src/old.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        _run(["git", "mv", "src/old.py", "src/new.py"], wt)
        (wt / "src" / "new.py").write_text("def g():\n    pass\n")
        # Left uncommitted, unlike the committed-history test above.

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err
