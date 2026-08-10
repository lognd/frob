"""`frob ticket new --parent PARENT_ID` priority inheritance (T-1960).

WHY: WIRE001 follow-up tickets -- the half of a fix that makes a shipped-
but-unwired detector actually real -- inherited no priority from the
ticket whose waiver named them, so a HIGH-priority hole (T-1921/T-1937/
T-1938, all high) silently became a MEDIUM-priority follow-up (T-1942/
T-1956/T-1957) and starved behind newer high-priority work. Per the
ticket's own explicit non-goal, this is NOT a blanket escalation: a
medium parent still yields a medium follow-up. `--priority` always wins
when given explicitly, even against a differently-prioritized parent."""

from __future__ import annotations

from pathlib import Path

from frob.app.config import AppConfig
from frob.app.ticket_runner import _new
from frob.tickets import Origin, Priority, TicketKind, TicketSpec, load_queue, new_ticket


def _seed_ticket(tmp_path: Path, *, priority: Priority) -> str:
    """Seed a single ticket at the given priority, standing in for a WIRE001
    waiver's own parent ticket. Mirrors
    tests/unit/test_ticket_file_flags.py's own `_make_ticket` helper."""
    spec = TicketSpec(
        title="parent",
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        priority=priority,
    )
    result = new_ticket(tmp_path, spec)
    return result.danger_ok.id


class TestNewTicketPriorityInheritance:
    """`frob ticket new --parent PARENT_ID` (T-1960)."""

    def test_high_priority_parent_yields_high_priority_follow_up(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance.test_high_priority_parent_yields_high_priority_follow_up  # noqa: E501
        """T-1960's own real-incident shape: a HIGH-priority ticket's
        WIRE001 waiver names a follow-up filed with `--parent`. Before the
        fix, this fell through to the pre-existing `Priority.MEDIUM`
        default -- the exact defect measured 3 times (T-1921/T-1937/
        T-1938 -> T-1942/T-1956/T-1957)."""
        parent_id = _seed_ticket(tmp_path, priority=Priority.HIGH)
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="wire the thing in",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_parent=parent_id,
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        follow_up = queue.tickets["T-0002"]
        assert follow_up.priority == Priority.HIGH

    def test_medium_priority_parent_yields_medium_priority_follow_up(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance.test_medium_priority_parent_yields_medium_priority_follow_up  # noqa: E501
        """No blanket escalation (the ticket's own explicit non-goal): a
        medium-priority parent still yields a medium-priority follow-up,
        identical to the pre-fix default -- this must NOT regress into
        every follow-up becoming high."""
        parent_id = _seed_ticket(tmp_path, priority=Priority.MEDIUM)
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="wire the other thing in",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_parent=parent_id,
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        follow_up = queue.tickets["T-0002"]
        assert follow_up.priority == Priority.MEDIUM

    def test_explicit_priority_overrides_parent_inheritance(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance.test_explicit_priority_overrides_parent_inheritance  # noqa: E501
        """An explicit `--priority` always wins over a `--parent`'s
        priority, even when they disagree -- inheritance is only a
        DEFAULT, never a forced override of the caller's own stated
        intent."""
        parent_id = _seed_ticket(tmp_path, priority=Priority.HIGH)
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="explicitly low despite a high parent",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_parent=parent_id,
            ticket_priority="low",
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        follow_up = queue.tickets["T-0002"]
        assert follow_up.priority == Priority.LOW

    def test_no_parent_falls_back_to_medium_default_unchanged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance.test_no_parent_falls_back_to_medium_default_unchanged  # noqa: E501
        """No `--parent` at all: the pre-existing `Priority.MEDIUM` default
        is completely unaffected by this change."""
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="standalone ticket",
            ticket_kind="bug",
            ticket_path=tmp_path,
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.priority == Priority.MEDIUM

    def test_unresolvable_parent_falls_back_to_medium_default(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance.test_unresolvable_parent_falls_back_to_medium_default  # noqa: E501
        """A `--parent` naming a ticket id that does not exist must not
        crash `frob ticket new` -- it degrades to the same MEDIUM default
        as no `--parent` at all."""
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="orphaned parent reference",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_parent="T-9999",
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.priority == Priority.MEDIUM
