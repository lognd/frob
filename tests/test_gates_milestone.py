"""Tests for T-2576 M2: `effective_milestone`'s configured-default terminal
fallback (`frob.tickets._doable`) and the MILE003 gate built on top of it
(`frob.gates._milestone`), per the ticket's own SCOPE REDESIGN --
docs/modules/tickets-data-storage.md#mile003-t-2576-m2.

Positive controls this file deliberately includes (per the redesign's own
body): an open ticket with no declared/inherited milestone resolves to
the configured default and is DISTINGUISHABLE as DEFAULTED (not DECLARED,
not INHERITED); a declared value is never overridden by the default; an
inherited value is never overridden by the default; with no
`default_milestone` configured, MILE003 fires rather than silently
assuming a value; and a terminal (done/dropped) ticket never fires.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.gates._milestone import milestone_gate
from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketKind,
    TicketQueue,
    TicketState,
    TicketTier,
)
from frob.tickets._doable import MilestoneSource, effective_milestone


def _ticket(
    *,
    ticket_id: str,
    state: TicketState = TicketState.QUEUED,
    tier: TicketTier = TicketTier.TICKET,
    parent: str | None = None,
    milestone: str | None = None,
    runs_last: bool = False,
    blocked_by: tuple[str, ...] = (),
    runs_last_parallel_safe: bool = False,
) -> Ticket:
    """Minimal fixture, same shape `test_tickets_milestone_sort.py::_ticket`
    uses -- kept as its own local copy rather than a shared import, same
    "two unrelated test modules should not couple on a tiny constructor"
    reasoning that file's own docstring gives. Extended (T-2579) with
    `runs_last`/`blocked_by`/`runs_last_parallel_safe` for MILE004's own
    fixtures; every pre-T-2579 call site is unaffected by the new
    defaults."""
    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        priority=Priority.MEDIUM,
        blocked_by=blocked_by,
        parent=parent,
        tier=tier,
        scope=(),
        evidence=(),
        attachments=(),
        acceptance=(),
        threat=None,
        body="",
        milestone=milestone,
        runs_last=runs_last,
        runs_last_parallel_safe=runs_last_parallel_safe,
    )


def _write_frob_toml(tmp_path: Path, *, default_milestone: str | None) -> None:
    """A minimal `frob.toml` with (or, `default_milestone=None`, without)
    a `[tickets].default_milestone` key -- `_default_milestone`'s own
    `tomllib.load(...).get("tickets", {})` shape."""
    if default_milestone is None:
        tmp_path.joinpath("frob.toml").write_text("")
    else:
        tmp_path.joinpath("frob.toml").write_text(
            f'[tickets]\ndefault_milestone = "{default_milestone}"\n'
        )


class TestEffectiveMilestoneDefault:
    """`effective_milestone(queue, ticket, root)` -- the T-2576 M2 terminal
    default fallback layered on top of M3's declared/inherited walk."""

    def test_no_declared_or_inherited_falls_back_to_configured_default(
        self, tmp_path: Path
    ) -> None:
        """No milestone on the ticket or any ancestor, but the repo
        configures a default: resolves to it, tagged DEFAULTED -- distinct
        from DECLARED and INHERITED (the whole point of the third state)."""
        _write_frob_toml(tmp_path, default_milestone="1.0.0")
        t = _ticket(ticket_id="T-1")
        queue = TicketQueue(tickets={t.id: t})
        assert effective_milestone(queue, t, tmp_path) == (
            "1.0.0",
            MilestoneSource.DEFAULTED,
        )

    def test_declared_value_is_not_overridden_by_default(
        self, tmp_path: Path
    ) -> None:
        """A ticket with its own milestone set keeps it verbatim even when
        the repo default differs -- the default must never win over a
        real, explicit choice."""
        _write_frob_toml(tmp_path, default_milestone="9.9.9")
        t = _ticket(ticket_id="T-1", milestone="1.0.0")
        queue = TicketQueue(tickets={t.id: t})
        assert effective_milestone(queue, t, tmp_path) == (
            "1.0.0",
            MilestoneSource.DECLARED,
        )

    def test_inherited_value_is_not_overridden_by_default(
        self, tmp_path: Path
    ) -> None:
        """A ticket inheriting from an ancestor keeps INHERITED, unchanged
        from M3, even when the repo configures a (different) default --
        M3's own resolution stays the nearer answer."""
        _write_frob_toml(tmp_path, default_milestone="9.9.9")
        story = _ticket(
            ticket_id="T-STORY", tier=TicketTier.STORY, milestone="1.1.0"
        )
        leaf = _ticket(ticket_id="T-LEAF", parent=story.id)
        queue = TicketQueue(tickets={story.id: story, leaf.id: leaf})
        assert effective_milestone(queue, leaf, tmp_path) == (
            "1.1.0",
            MilestoneSource.INHERITED,
        )

    def test_no_default_configured_stays_unresolved(self, tmp_path: Path) -> None:
        """No declared/inherited value AND no configured default: `(None,
        None)`, never a silently-assumed value -- this is what keeps
        MILE003 free to fire when the repo has not opted into a default."""
        _write_frob_toml(tmp_path, default_milestone=None)
        t = _ticket(ticket_id="T-1")
        queue = TicketQueue(tickets={t.id: t})
        assert effective_milestone(queue, t, tmp_path) == (None, None)

    def test_no_root_skips_default_lookup(self) -> None:
        """`root=None` (every pre-T-2576 caller) preserves M3's exact
        two-state behavior verbatim -- the default is opt-in per call
        site, never forced onto a caller that never passes `root`."""
        t = _ticket(ticket_id="T-1")
        queue = TicketQueue(tickets={t.id: t})
        assert effective_milestone(queue, t) == (None, None)


class TestMile003:
    """`milestone_gate(root, queue)` -- MILE003, an OPEN ticket whose
    effective milestone cannot be resolved."""

    def test_fires_on_open_ticket_with_no_resolvable_milestone(
        self, tmp_path: Path
    ) -> None:
        """No default configured, no declared/inherited value: MILE003
        fires ERROR, naming the ticket."""
        _write_frob_toml(tmp_path, default_milestone=None)
        t = _ticket(ticket_id="T-1")
        queue = TicketQueue(tickets={t.id: t})
        violations = milestone_gate(tmp_path, queue)
        assert [v.rule for v in violations] == ["MILE003"]
        assert "T-1" in violations[0].message

    def test_silent_once_stamped(self, tmp_path: Path) -> None:
        """Positive control (this ticket's own original body): stamping
        the ticket's own milestone silences MILE003."""
        _write_frob_toml(tmp_path, default_milestone=None)
        t = _ticket(ticket_id="T-1", milestone="1.0.0")
        queue = TicketQueue(tickets={t.id: t})
        assert milestone_gate(tmp_path, queue) == ()

    def test_silent_on_configured_default(self, tmp_path: Path) -> None:
        """The M2 redesign's whole point: a configured default silences
        MILE003 with ZERO ticket-file writes."""
        _write_frob_toml(tmp_path, default_milestone="1.0.0")
        t = _ticket(ticket_id="T-1")
        queue = TicketQueue(tickets={t.id: t})
        assert milestone_gate(tmp_path, queue) == ()

    def test_silent_on_inherited_value(self, tmp_path: Path) -> None:
        """An inheriting leaf is silent even with no repo default
        configured -- M3's own resolution already satisfies MILE003."""
        _write_frob_toml(tmp_path, default_milestone=None)
        story = _ticket(
            ticket_id="T-STORY", tier=TicketTier.STORY, milestone="1.1.0"
        )
        leaf = _ticket(ticket_id="T-LEAF", parent=story.id)
        queue = TicketQueue(tickets={story.id: story, leaf.id: leaf})
        assert milestone_gate(tmp_path, queue) == ()

    def test_terminal_ticket_never_fires(self, tmp_path: Path) -> None:
        """A DONE/DROPPED ticket with no milestone never fires -- it does
        not sequence again, matching the abandoned backfill's own
        terminal-ticket exclusion reasoning."""
        _write_frob_toml(tmp_path, default_milestone=None)
        done = _ticket(ticket_id="T-1", state=TicketState.DONE)
        dropped = _ticket(ticket_id="T-2", state=TicketState.DROPPED)
        queue = TicketQueue(tickets={done.id: done, dropped.id: dropped})
        assert milestone_gate(tmp_path, queue) == ()

    def test_no_default_configured_still_fires(self, tmp_path: Path) -> None:
        """Explicit required case (redesign body, last positive control):
        with NO `default_milestone` configured at all (no `frob.toml`
        present), MILE003 still fires -- without this, the default would
        just be a way to make the gate never fire."""
        # No frob.toml written at all -- `_default_milestone` degrades to
        # "no default" on a missing file, same as an empty one.
        t = _ticket(ticket_id="T-1")
        queue = TicketQueue(tickets={t.id: t})
        violations = milestone_gate(tmp_path, queue)
        assert [v.rule for v in violations] == ["MILE003"]


class TestMile004:
    """MILE004 (T-2579 M4b): multiple `runs_last` tickets sharing one
    milestone must be either ordered (`blocked_by`) or explicitly
    declared parallel-safe on BOTH sides -- ambiguity is an ERROR.
    Every fixture declares its own `milestone` directly (DECLARED
    source) so MILE003 never also fires and confuses these assertions."""

    def test_two_unordered_runs_last_in_one_milestone_fires(
        self, tmp_path: Path
    ) -> None:
        """The base case: two runs_last tickets, same milestone, no
        ordering and no parallel-safe declaration -- MILE004 must fire."""
        a = _ticket(ticket_id="T-1", runs_last=True, milestone="1.0.0")
        b = _ticket(ticket_id="T-2", runs_last=True, milestone="1.0.0")
        queue = TicketQueue(tickets={a.id: a, b.id: b})
        violations = [v for v in milestone_gate(tmp_path, queue) if v.rule == "MILE004"]
        assert len(violations) == 1
        assert "T-1" in violations[0].message
        assert "T-2" in violations[0].message

    def test_blocked_by_edge_resolves_the_pair(self, tmp_path: Path) -> None:
        """The identical pair, but T-2 now `blocked_by` T-1 -- a real
        ordering edge must silence MILE004 for this pair."""
        a = _ticket(ticket_id="T-1", runs_last=True, milestone="1.0.0")
        b = _ticket(
            ticket_id="T-2", runs_last=True, milestone="1.0.0", blocked_by=("T-1",)
        )
        queue = TicketQueue(tickets={a.id: a, b.id: b})
        violations = [v for v in milestone_gate(tmp_path, queue) if v.rule == "MILE004"]
        assert violations == []

    def test_declared_parallel_safe_resolves_the_pair(self, tmp_path: Path) -> None:
        """The identical pair, both declared `runs_last_parallel_safe` --
        an explicit two-sided decision must silence MILE004."""
        a = _ticket(
            ticket_id="T-1",
            runs_last=True,
            milestone="1.0.0",
            runs_last_parallel_safe=True,
        )
        b = _ticket(
            ticket_id="T-2",
            runs_last=True,
            milestone="1.0.0",
            runs_last_parallel_safe=True,
        )
        queue = TicketQueue(tickets={a.id: a, b.id: b})
        violations = [v for v in milestone_gate(tmp_path, queue) if v.rule == "MILE004"]
        assert violations == []

    def test_one_sided_parallel_safe_still_fires(self, tmp_path: Path) -> None:
        """A ONE-sided declaration is not a decision -- must still fire.
        Not one of the ticket's four named controls, but the natural
        must-fail complement to the two-sided control above."""
        a = _ticket(
            ticket_id="T-1",
            runs_last=True,
            milestone="1.0.0",
            runs_last_parallel_safe=True,
        )
        b = _ticket(ticket_id="T-2", runs_last=True, milestone="1.0.0")
        queue = TicketQueue(tickets={a.id: a, b.id: b})
        violations = [v for v in milestone_gate(tmp_path, queue) if v.rule == "MILE004"]
        assert len(violations) == 1

    def test_single_runs_last_ticket_never_fires(self, tmp_path: Path) -> None:
        """A lone runs_last ticket in a milestone has no sibling to pair
        with -- MILE004 must never fire."""
        a = _ticket(ticket_id="T-1", runs_last=True, milestone="1.0.0")
        other = _ticket(ticket_id="T-2", milestone="1.0.0")
        queue = TicketQueue(tickets={a.id: a, other.id: other})
        violations = [v for v in milestone_gate(tmp_path, queue) if v.rule == "MILE004"]
        assert violations == []

    def test_different_milestones_never_pair(self, tmp_path: Path) -> None:
        """Two runs_last tickets in DIFFERENT milestones never pair --
        MILE004 is scoped per-milestone, same as `_other_open_tickets`
        (T-2578)."""
        a = _ticket(ticket_id="T-1", runs_last=True, milestone="1.0.0")
        b = _ticket(ticket_id="T-2", runs_last=True, milestone="2.0.0")
        queue = TicketQueue(tickets={a.id: a, b.id: b})
        violations = [v for v in milestone_gate(tmp_path, queue) if v.rule == "MILE004"]
        assert violations == []

    def test_terminal_sibling_excluded(self, tmp_path: Path) -> None:
        """A DONE runs_last sibling is excluded from pairing -- it no
        longer needs ordering against anything."""
        a = _ticket(ticket_id="T-1", runs_last=True, milestone="1.0.0")
        b = _ticket(
            ticket_id="T-2", runs_last=True, milestone="1.0.0", state=TicketState.DONE
        )
        queue = TicketQueue(tickets={a.id: a, b.id: b})
        violations = [v for v in milestone_gate(tmp_path, queue) if v.rule == "MILE004"]
        assert violations == []
