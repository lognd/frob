"""Tests for T-2577 M3: milestone as the PRIMARY `doable` sort axis,
own-or-inherited effective milestone, and the `--milestone`-shaped filter
semantics (docs/modules/tickets-data-storage.md#milestone-as-the-doable-
sort-axis-and-inheritance-t-2577-m3).

Positive controls this file deliberately includes (per T-2577's own body):
a later-milestone ticket still APPEARS in `doable()`'s result (sorted
last, never absent -- the hide-instead-of-sort regression this exists to
catch), an inherited milestone renders distinct from a declared one, and
a "1.10.0" vs "1.9.0" case holds (string comparison gets this backwards).
"""

from __future__ import annotations

from datetime import date

from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketKind,
    TicketQueue,
    TicketState,
    TicketTier,
    _doable_sort_key,
    doable,
    effective_milestone,
)
from frob.tickets._doable import MilestoneSource


def _ticket(
    *,
    ticket_id: str,
    state: TicketState = TicketState.QUEUED,
    priority: Priority = Priority.MEDIUM,
    created: date = date(2026, 1, 1),
    tier: TicketTier = TicketTier.TICKET,
    parent: str | None = None,
    milestone: str | None = None,
) -> Ticket:
    """Same minimal-fixture shape `test_tickets_priority.py::_ticket` uses,
    plus `milestone` -- kept as its own local helper (not imported) since
    the two test files' fixture needs diverge slightly and duplicating one
    tiny constructor is cheaper than coupling two unrelated test modules."""
    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=created,
        priority=priority,
        blocked_by=(),
        parent=parent,
        tier=tier,
        scope=(),
        evidence=(),
        attachments=(),
        acceptance=(),
        threat=None,
        body="",
        milestone=milestone,
    )


class TestEffectiveMilestone:
    """`effective_milestone(queue, ticket)` -- own-or-inherited value, and
    whether it was declared or inherited."""

    def test_own_milestone_is_declared(self) -> None:
        """A ticket with its own `milestone` set never looks at `parent`."""
        t = _ticket(ticket_id="T-1", milestone="1.0.0")
        queue = TicketQueue(tickets={t.id: t})
        assert effective_milestone(queue, t) == ("1.0.0", MilestoneSource.DECLARED)

    def test_inherits_from_parent_story(self) -> None:
        """No own milestone, but the immediate parent (a story) has one:
        inherited, `declared=False`."""
        story = _ticket(ticket_id="T-STORY", tier=TicketTier.STORY, milestone="1.1.0")
        leaf = _ticket(ticket_id="T-LEAF", parent=story.id)
        queue = TicketQueue(tickets={story.id: story, leaf.id: leaf})
        assert effective_milestone(queue, leaf) == ("1.1.0", MilestoneSource.INHERITED)

    def test_inherits_from_grandparent_epic(self) -> None:
        """Story has no milestone of its own, but the epic above IT does --
        the walk keeps climbing past one milestone-less ancestor."""
        epic = _ticket(ticket_id="T-EPIC", tier=TicketTier.EPIC, milestone="2.0.0")
        story = _ticket(ticket_id="T-STORY", tier=TicketTier.STORY, parent=epic.id)
        leaf = _ticket(ticket_id="T-LEAF", parent=story.id)
        queue = TicketQueue(tickets={epic.id: epic, story.id: story, leaf.id: leaf})
        assert effective_milestone(queue, leaf) == ("2.0.0", MilestoneSource.INHERITED)

    def test_nearest_ancestor_wins_over_farther_one(self) -> None:
        """Both the story AND the epic declare a milestone -- the NEARER
        one (the story) wins, per T-2577's "nearest ancestor" rule."""
        epic = _ticket(ticket_id="T-EPIC", tier=TicketTier.EPIC, milestone="3.0.0")
        story = _ticket(
            ticket_id="T-STORY",
            tier=TicketTier.STORY,
            parent=epic.id,
            milestone="3.1.0",
        )
        leaf = _ticket(ticket_id="T-LEAF", parent=story.id)
        queue = TicketQueue(tickets={epic.id: epic, story.id: story, leaf.id: leaf})
        assert effective_milestone(queue, leaf) == ("3.1.0", MilestoneSource.INHERITED)

    def test_no_milestone_anywhere_in_chain_is_none(self) -> None:
        """No milestone on the ticket or any ancestor: `(None, False)`, not
        an error -- the common pre-M2-backfill case."""
        story = _ticket(ticket_id="T-STORY", tier=TicketTier.STORY)
        leaf = _ticket(ticket_id="T-LEAF", parent=story.id)
        queue = TicketQueue(tickets={story.id: story, leaf.id: leaf})
        assert effective_milestone(queue, leaf) == (None, None)

    def test_cycle_does_not_infinite_loop(self) -> None:
        """A malformed cyclic `parent` chain terminates instead of hanging
        (`parent` is deliberately unvalidated against cycles at the model
        layer, same T-1132 reasoning `validate_milestone` documents)."""
        a = _ticket(ticket_id="T-A", parent="T-B")
        b = _ticket(ticket_id="T-B", parent="T-A")
        queue = TicketQueue(tickets={a.id: a, b.id: b})
        assert effective_milestone(queue, a) == (None, None)


class TestDoableSortKey:
    """`_doable_sort_key(t, queue)` -- milestone-primary ordering."""

    def test_earlier_milestone_outranks_critical_later_milestone(self) -> None:
        """A LOW-priority v1.0 ticket must sort before a CRITICAL v1.1
        ticket while 1.0 is still shipping -- the exact scenario T-2577's
        own body names."""
        low_v1 = _ticket(ticket_id="T-1001", priority=Priority.LOW, milestone="1.0.0")
        critical_v1_1 = _ticket(
            ticket_id="T-1002", priority=Priority.CRITICAL, milestone="1.1.0"
        )
        queue = TicketQueue(
            tickets={low_v1.id: low_v1, critical_v1_1.id: critical_v1_1}
        )
        result = doable(queue, root=None, ignore_lease=True)
        assert [t.id for t in result] == ["T-1001", "T-1002"]

    def test_later_milestone_still_appears_sorted_last_never_absent(self) -> None:
        """Positive control: a later-milestone ticket is NOT hidden from
        `doable()`'s result -- it appears, sorted last. Catches a
        hide-instead-of-sort regression (T-2391's silent-zero pattern)."""
        v1 = _ticket(ticket_id="T-3001", milestone="1.0.0")
        v2 = _ticket(ticket_id="T-3002", milestone="2.0.0")
        queue = TicketQueue(tickets={v1.id: v1, v2.id: v2})
        result = doable(queue, root=None, ignore_lease=True)
        ids = [t.id for t in result]
        assert "T-3002" in ids, "later-milestone ticket must not be hidden"
        assert ids == ["T-3001", "T-3002"]

    def test_unmilestoned_sorts_after_every_declared_milestone(self) -> None:
        """An unmilestoned ticket sorts AFTER a declared-milestone one,
        deterministically -- not arbitrarily -- regardless of priority."""
        unmilestoned = _ticket(
            ticket_id="T-4001", priority=Priority.CRITICAL, milestone=None
        )
        milestoned = _ticket(
            ticket_id="T-4002", priority=Priority.LOW, milestone="1.0.0"
        )
        queue = TicketQueue(
            tickets={unmilestoned.id: unmilestoned, milestoned.id: milestoned}
        )
        result = doable(queue, root=None, ignore_lease=True)
        assert [t.id for t in result] == ["T-4002", "T-4001"]

    def test_semver_numeric_not_lexical_ordering(self) -> None:
        """ "1.10.0" must outrank "1.9.0" -- a lexical compare gets this
        backwards ("1.10.0" < "1.9.0" as strings)."""
        v1_9 = _ticket(ticket_id="T-5001", milestone="1.9.0")
        v1_10 = _ticket(ticket_id="T-5002", milestone="1.10.0")
        queue = TicketQueue(tickets={v1_9.id: v1_9, v1_10.id: v1_10})
        result = doable(queue, root=None, ignore_lease=True)
        assert [t.id for t in result] == ["T-5001", "T-5002"]

    def test_no_queue_falls_back_to_own_milestone_only(self) -> None:
        """`queue=None` (every pre-T-2577 caller: `board_view`,
        `_brief.py`) uses `t.milestone` alone -- no ancestor walk -- so the
        function stays a drop-in single-arg call for callers outside this
        ticket's scope."""
        t = _ticket(ticket_id="T-6001", milestone="1.0.0")
        key_with_none_queue = _doable_sort_key(t, None)
        key_with_no_arg = _doable_sort_key(t)
        assert key_with_none_queue == key_with_no_arg
