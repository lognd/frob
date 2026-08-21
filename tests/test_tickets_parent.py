"""Tests for T-2770's `set_parent` (`frob ticket set-parent <id>
<parent-id>`): the mutate-in-place parent-edge setter `frob ticket new
--parent` never got a correction path for, mirroring `set_tier`'s T-1069
shape but with real structural validation (existence, cycle,
tier-inversion, self-parent) `set_tier` deliberately does not need.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketError,
    TicketKind,
    TicketSpec,
    TicketState,
    TicketTier,
    new_ticket,
    set_parent,
)
from frob.tickets._store import (
    _serialize_ticket,
    load_all,
    load_archive,
    v2_archive_dir,
    v2_ticket_dir,
    write_ticket,
)


def _ticket(
    *,
    ticket_id: str,
    state: TicketState = TicketState.QUEUED,
    priority: Priority = Priority.MEDIUM,
    parent: str | None = None,
    tier: TicketTier = TicketTier.TICKET,
    created: date = date(2026, 1, 1),
) -> Ticket:
    """Minimal `Ticket` builder for this module's own fixtures -- same
    shape as `test_tickets_tiers.py`'s own `_ticket` helper."""
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
        sprint=None,
        scope=(),
        evidence=(),
        attachments=(),
        acceptance=(),
        threat=None,
        body="",
    )


class TestSetParent:
    """`set_parent` (T-2770): the accountable, single-writer way to
    correct a ticket's `parent` edge, refusing every structurally invalid
    edge rather than silently accepting it (the whole point over a hand
    edit of `tickets/T-####/ticket.md`)."""

    def test_reparents_leaf_to_epic(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_reparents_leaf_to_epic  # noqa: E501
        # Positive control: a legitimate epic -> ticket edge succeeds.
        # Mirrors the measured T-2770 customer -- T-2384 (epic) gaining a
        # tier=ticket child filed with parent=null.
        epic = new_ticket(
            tmp_path,
            TicketSpec(
                title="an epic",
                kind=TicketKind.FEATURE,
                origin=Origin.HUMAN,
                tier=TicketTier.EPIC,
            ),
        )
        assert epic.is_ok
        epic_id = epic.danger_ok.id

        child = new_ticket(
            tmp_path,
            TicketSpec(title="a leaf ticket", kind=TicketKind.FEATURE, origin=Origin.HUMAN),
        )
        assert child.is_ok
        child_id = child.danger_ok.id
        assert child.danger_ok.tier is TicketTier.TICKET

        result = set_parent(tmp_path, child_id, epic_id, reason="correcting filing")
        assert result.is_ok
        assert result.danger_ok.parent == epic_id

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok[child_id].parent == epic_id

    def test_self_parent_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_self_parent_refuses  # noqa: E501
        ticket = _ticket(ticket_id="T-0001")
        assert write_ticket(tmp_path, ticket).is_ok

        result = set_parent(tmp_path, "T-0001", "T-0001", reason="test")
        assert result.is_err
        assert result.danger_err is TicketError.ParentSelfReference

    def test_nonexistent_parent_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_nonexistent_parent_refuses  # noqa: E501
        ticket = _ticket(ticket_id="T-0001")
        assert write_ticket(tmp_path, ticket).is_ok

        result = set_parent(tmp_path, "T-0001", "T-9999", reason="test")
        assert result.is_err
        assert result.danger_err is TicketError.ParentNotFound

    def test_direct_cycle_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_direct_cycle_refuses  # noqa: E501
        # A parent B (B tier epic, A tier ticket); re-pointing B's parent
        # at A would close a direct ring.
        a = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET, parent="T-0002")
        b = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC, parent=None)
        assert write_ticket(tmp_path, a).is_ok
        assert write_ticket(tmp_path, b).is_ok

        result = set_parent(tmp_path, "T-0002", "T-0001", reason="test")
        assert result.is_err
        assert result.danger_err is TicketError.ParentCycle

    def test_longer_ring_cycle_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_longer_ring_cycle_refuses  # noqa: E501
        # A -> B -> C (parent chain); re-pointing C's parent at A closes a
        # 3-node ring, not just a direct 2-node one.
        a = _ticket(ticket_id="T-0001", tier=TicketTier.EPIC, parent=None)
        b = _ticket(ticket_id="T-0002", tier=TicketTier.STORY, parent="T-0001")
        c = _ticket(ticket_id="T-0003", tier=TicketTier.TICKET, parent="T-0002")
        assert write_ticket(tmp_path, a).is_ok
        assert write_ticket(tmp_path, b).is_ok
        assert write_ticket(tmp_path, c).is_ok

        result = set_parent(tmp_path, "T-0001", "T-0003", reason="test")
        assert result.is_err
        assert result.danger_err is TicketError.ParentCycle

    def test_tier_inversion_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_tier_inversion_refuses  # noqa: E501
        # A tier=ticket cannot parent a tier=epic.
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET)
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        assert write_ticket(tmp_path, leaf).is_ok
        assert write_ticket(tmp_path, epic).is_ok

        result = set_parent(tmp_path, "T-0002", "T-0001", reason="test")
        assert result.is_err
        assert result.danger_err is TicketError.ParentTierInversion

    def test_epic_can_parent_epic(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_epic_can_parent_epic  # noqa: E501
        # Positive control: same-tier chaining is allowed, not just
        # strictly-descending tiers -- the exact T-2384->T-1382 shape
        # (both tier=epic) T-2770's own measured customer needs.
        grandparent_epic = _ticket(ticket_id="T-0001", tier=TicketTier.EPIC)
        child_epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        assert write_ticket(tmp_path, grandparent_epic).is_ok
        assert write_ticket(tmp_path, child_epic).is_ok

        result = set_parent(
            tmp_path, "T-0002", "T-0001", reason="nest epic under epic"
        )
        assert result.is_ok
        assert result.danger_ok.parent == "T-0001"

    def test_story_cannot_parent_epic(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_story_cannot_parent_epic  # noqa: E501
        # A lower tier (story) cannot parent a higher one (epic), same
        # rule as ticket-cannot-parent-epic, one rank up.
        story = _ticket(ticket_id="T-0001", tier=TicketTier.STORY)
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        assert write_ticket(tmp_path, story).is_ok
        assert write_ticket(tmp_path, epic).is_ok

        result = set_parent(tmp_path, "T-0002", "T-0001", reason="test")
        assert result.is_err
        assert result.danger_err is TicketError.ParentTierInversion

    def test_reason_missing_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_reason_missing_refuses  # noqa: E501
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET)
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        assert write_ticket(tmp_path, leaf).is_ok
        assert write_ticket(tmp_path, epic).is_ok

        result = set_parent(tmp_path, "T-0001", "T-0002", reason="")
        assert result.is_err
        assert result.danger_err is TicketError.ParentTicketReasonMissing

    def test_moving_an_existing_parent_drops_the_old_edge(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_moving_an_existing_parent_drops_the_old_edge  # noqa: E501
        old_epic = _ticket(ticket_id="T-0001", tier=TicketTier.EPIC)
        new_epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        leaf = _ticket(ticket_id="T-0003", tier=TicketTier.TICKET, parent="T-0001")
        assert write_ticket(tmp_path, old_epic).is_ok
        assert write_ticket(tmp_path, new_epic).is_ok
        assert write_ticket(tmp_path, leaf).is_ok

        result = set_parent(tmp_path, "T-0003", "T-0002", reason="re-file under T-0002")
        assert result.is_ok
        assert result.danger_ok.parent == "T-0002"

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0003"].parent == "T-0002"

    def test_archived_ticket_routes_to_archive_path(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_archived_ticket_routes_to_archive_path  # noqa: E501
        # Mirrors T-2678's set_body fix: re-parenting an ARCHIVED ticket
        # must amend tickets/archive/<id>/ticket.md in place, never
        # materialize a fresh tickets/<id>/ active-tree duplicate.
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        assert write_ticket(tmp_path, epic).is_ok

        archived_leaf = _ticket(ticket_id="T-1688", tier=TicketTier.TICKET)
        (tmp_path / "tickets" / "archive" / "T-1688").mkdir(parents=True)
        (tmp_path / "tickets" / "archive" / "T-1688" / "ticket.md").write_text(
            _serialize_ticket(archived_leaf)
        )

        result = set_parent(tmp_path, "T-1688", "T-0002", reason="correcting filing")
        assert result.is_ok
        assert result.danger_ok.parent == "T-0002"

        archived_path = v2_archive_dir(tmp_path, "T-1688") / "ticket.md"
        assert archived_path.exists()
        assert "T-0002" in archived_path.read_text(encoding="utf-8")

        # Must-NOT-fire control: no fresh active-side copy was created.
        assert not v2_ticket_dir(tmp_path, "T-1688").exists()

        archived = load_archive(tmp_path)
        assert archived.is_ok
        assert archived.danger_ok["T-1688"].parent == "T-0002"
