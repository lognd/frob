"""Tests for T-1738's `frob ticket wave`: partition the doable set into N
mutually scope-disjoint groups for parallel dispatch
(docs/modules/tickets.md#public-api)."""

from __future__ import annotations

from datetime import date

from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState
from frob.tickets._doable import wave


def _ticket(
    *,
    ticket_id: str,
    scope: tuple[str, ...],
    created: date = date(2026, 1, 1),
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=TicketState.QUEUED,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=created,
        blocked_by=(),
        parent=None,
        scope=scope,
        evidence=(),
        attachments=(),
        body="## Description\nsomething\n",
    )


def _queue(*tickets: Ticket) -> TicketQueue:
    return TicketQueue(tickets={t.id: t for t in tickets})


class TestWave:
    def test_disjoint_scopes_pack_into_separate_groups(self) -> None:
        # frob:tests \
        # tests/test_tickets_wave.py::TestWave.test_disjoint_scopes_pack_into_separate_\
        # groups
        a = _ticket(ticket_id="T-0001", scope=("src/a.py",))
        b = _ticket(ticket_id="T-0002", scope=("src/b.py",))
        result = wave(_queue(a, b), None, agents=2)
        assert len(result.groups) == 2
        assert not result.remainder
        placed_ids = {t.id for g in result.groups for t in g.tickets}
        assert placed_ids == {"T-0001", "T-0002"}

    def test_colliding_scopes_share_one_group(self) -> None:
        # frob:tests \
        # tests/test_tickets_wave.py::TestWave.test_colliding_scopes_share_one_group
        a = _ticket(ticket_id="T-0001", scope=("src/shared.py",))
        b = _ticket(ticket_id="T-0002", scope=("src/shared.py",))
        result = wave(_queue(a, b), None, agents=2)
        # Only one group can be safely opened: both tickets touch the same
        # file, so putting them in different groups would let two agents
        # collide. wave() must not fabricate a second, colliding group.
        assert len(result.groups) == 1
        assert not result.remainder
        assert {t.id for t in result.groups[0].tickets} == {"T-0001", "T-0002"}

    def test_unplaceable_ticket_lands_in_remainder_with_reason(self) -> None:
        # frob:tests \
        # tests/test_tickets_wave.py::TestWave.test_unplaceable_ticket_lands_in_remaind\
        # er_with_reason
        a = _ticket(ticket_id="T-0001", scope=("src/a.py",), created=date(2026, 1, 1))
        b = _ticket(ticket_id="T-0002", scope=("src/b.py",), created=date(2026, 1, 2))
        c = _ticket(
            ticket_id="T-0003",
            scope=("src/a.py", "src/b.py"),
            created=date(2026, 1, 3),
        )
        # a and b are placed into two separate groups (agents=2). c collides
        # with BOTH, so it cannot join either without breaking cross-group
        # disjointness, and no third group is allowed -- it must land in
        # the remainder, not silently dropped or forced into one group.
        result = wave(_queue(a, b, c), None, agents=2)
        assert len(result.groups) == 2
        assert len(result.remainder) == 1
        reason = result.remainder[0]
        assert reason.ticket.id == "T-0003"
        assert reason.colliding_ticket_id in {"T-0001", "T-0002"}
        assert reason.glob in {"src/a.py", "src/b.py"}

    def test_deterministic_for_repeated_calls(self) -> None:
        # frob:tests \
        # tests/test_tickets_wave.py::TestWave.test_deterministic_for_repeated_calls
        a = _ticket(ticket_id="T-0001", scope=("src/a.py",))
        b = _ticket(ticket_id="T-0002", scope=("src/b.py",))
        c = _ticket(ticket_id="T-0003", scope=("src/c.py",))
        queue = _queue(a, b, c)
        first = wave(queue, None, agents=2)
        second = wave(queue, None, agents=2)
        first_shape = [tuple(t.id for t in g.tickets) for g in first.groups]
        second_shape = [tuple(t.id for t in g.tickets) for g in second.groups]
        assert first_shape == second_shape

    def test_fewer_groups_than_agents_is_not_an_error(self) -> None:
        # frob:tests \
        # tests/test_tickets_wave.py::TestWave.test_fewer_groups_than_agents_is_not_an_\
        # error
        a = _ticket(ticket_id="T-0001", scope=("src/a.py",))
        result = wave(_queue(a), None, agents=5)
        assert len(result.groups) == 1
        assert not result.remainder
