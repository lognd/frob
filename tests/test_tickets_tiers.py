"""Tests for T-0715's ticket organization model foundation: the `tier`
(epic|story|ticket) field, structural doable/close rules built on it, and
the `sprint` field it ships alongside (docs/modules/tickets.md#data-models).
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketError,
    TicketKind,
    TicketQueue,
    TicketSpec,
    TicketState,
    TicketTier,
    doable,
    new_ticket,
    set_sprint,
    set_tier,
    sprint_view,
    transition,
)
from frob.tickets._store import _serialize_ticket, load_all, write_ticket


def _ticket(
    *,
    ticket_id: str,
    state: TicketState = TicketState.QUEUED,
    priority: Priority = Priority.MEDIUM,
    parent: str | None = None,
    tier: TicketTier = TicketTier.TICKET,
    sprint: str | None = None,
    created: date = date(2026, 1, 1),
    evidence: tuple[str, ...] = (),
    body: str = "",
) -> Ticket:
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
        sprint=sprint,
        scope=(),
        evidence=evidence,
        attachments=(),
        acceptance=(),
        threat=None,
        body=body,
    )


class TestTierField:
    """`tier` defaults to TICKET (T-0715 backward compat) and round-trips
    through serialize/parse and the ledger."""

    def test_default_tier_is_ticket(self) -> None:
        # frob:tests src/frob/tickets/_models.py::Ticket kind="unit"
        ticket = _ticket(ticket_id="T-0001")
        assert ticket.tier is TicketTier.TICKET

    def test_serialize_parse_round_trip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::_serialize_ticket kind="unit"
        from frob.tickets._store import _parse_ticket_file

        ticket = _ticket(ticket_id="T-0001", tier=TicketTier.EPIC, sprint="sprint-14")
        text = _serialize_ticket(ticket)
        path = tmp_path / "T-0001-ticket-t-0001.md"
        path.write_text(text, encoding="utf-8")

        result = _parse_ticket_file(path)
        assert result.is_ok
        assert result.danger_ok.tier is TicketTier.EPIC
        assert result.danger_ok.sprint == "sprint-14"

    def test_write_ticket_ledger_round_trip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::write_ticket kind="unit"
        ticket = _ticket(ticket_id="T-0001", tier=TicketTier.STORY, sprint="2026-W30")
        written = write_ticket(tmp_path, ticket)
        assert written.is_ok

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].tier is TicketTier.STORY
        assert loaded.danger_ok["T-0001"].sprint == "2026-W30"

    def test_new_ticket_carries_tier_and_sprint(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_new_renumber.py::new_ticket kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(
            title="a story",
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            tier=TicketTier.STORY,
            sprint="sprint-14",
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        assert created.danger_ok.tier is TicketTier.STORY
        assert created.danger_ok.sprint == "sprint-14"


# frob:ticket T-1108
class TestDoableLeafOnly:
    """`doable` only ever surfaces tier=TICKET tickets (T-0715): an
    epic/story with no blockers of its own must never be dispatchable
    work."""

    # frob:ticket T-1108
    def test_epic_and_story_never_surface(self) -> None:
        # frob:tests src/frob/tickets/_doable.py::doable kind="unit"
        epic = _ticket(ticket_id="T-0001", tier=TicketTier.EPIC)
        story = _ticket(ticket_id="T-0002", tier=TicketTier.STORY, parent="T-0001")
        leaf = _ticket(ticket_id="T-0003", tier=TicketTier.TICKET, parent="T-0002")
        queue = TicketQueue(tickets={epic.id: epic, story.id: story, leaf.id: leaf})
        result = doable(queue, ignore_lease=True)
        assert [t.id for t in result] == ["T-0003"]


class TestCloseOpenDescendantGuard:
    """An EPIC/STORY refuses to transition to DONE while any descendant
    (via the `parent` chain) is still open (T-0715)."""

    def test_epic_close_refused_with_open_descendant(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::transition kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        epic = _ticket(
            ticket_id="T-0001",
            tier=TicketTier.EPIC,
            state=TicketState.IN_PROGRESS,
            evidence=("tests/x.py::test_a",),
            body="## Done report\nsome real content here.\n",
        )
        leaf = _ticket(ticket_id="T-0002", tier=TicketTier.TICKET, parent="T-0001")
        write_ticket(tmp_path, epic)
        write_ticket(tmp_path, leaf)

        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_err
        assert result.danger_err == TicketError.OpenDescendant

    def test_epic_close_allowed_once_descendant_done(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::transition kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        epic = _ticket(
            ticket_id="T-0001",
            tier=TicketTier.EPIC,
            state=TicketState.IN_PROGRESS,
            evidence=("tests/x.py::test_a",),
            body="## Done report\nsome real content here.\n",
        )
        leaf = _ticket(
            ticket_id="T-0002",
            tier=TicketTier.TICKET,
            parent="T-0001",
            state=TicketState.DONE,
        )
        write_ticket(tmp_path, epic)
        write_ticket(tmp_path, leaf)

        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_ok
        assert result.danger_ok.state is TicketState.DONE

    def test_plain_ticket_close_unaffected_by_guard(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::transition kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        leaf = _ticket(
            ticket_id="T-0001",
            tier=TicketTier.TICKET,
            state=TicketState.IN_PROGRESS,
            evidence=("tests/x.py::test_a",),
            body="## Done report\nsome real content here.\n",
        )
        write_ticket(tmp_path, leaf)

        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_ok


# frob:ticket T-1069
class TestSetTier:
    """`set_tier` (T-1069), the `frob ticket tier <id> <value>` primitive --
    same single-writer, ledger-locked shape as `set_priority`/`set_kind`/
    `set_component`/`set_sprint`, the mutate-in-place counterpart T-0715's
    `new --tier` never got."""

    # frob:ticket T-1069
    def test_updates_tier_field(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::set_tier kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(
            title="a ticket", kind=TicketKind.FEATURE, origin=Origin.HUMAN
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id
        assert created.danger_ok.tier is TicketTier.TICKET

        result = set_tier(tmp_path, ticket_id, TicketTier.EPIC)
        assert result.is_ok
        assert result.danger_ok.tier is TicketTier.EPIC

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok[ticket_id].tier is TicketTier.EPIC

    # frob:ticket T-1069
    def test_unknown_ticket_id_is_err(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::set_tier kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        result = set_tier(tmp_path, "T-9999", TicketTier.STORY)
        assert result.is_err

    # frob:ticket T-1069
    def test_structural_rules_apply_to_new_tier_on_next_read(
        self, tmp_path: Path
    ) -> None:
        """A ticket retiered to EPIC via `set_tier` (not created as one)
        picks up the open-descendant close guard on its very next read --
        the rule keys off the CURRENT tier field, not how the ticket was
        originally created."""
        # frob:tests src/frob/tickets/__init__.py::set_tier kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        parent = _ticket(
            ticket_id="T-0001",
            tier=TicketTier.TICKET,
            state=TicketState.IN_PROGRESS,
            evidence=("tests/x.py::test_a",),
            body="## Done report\nsome real content here.\n",
        )
        leaf = _ticket(ticket_id="T-0002", tier=TicketTier.TICKET, parent="T-0001")
        write_ticket(tmp_path, parent)
        write_ticket(tmp_path, leaf)

        retiered = set_tier(tmp_path, "T-0001", TicketTier.EPIC)
        assert retiered.is_ok
        assert retiered.danger_ok.tier is TicketTier.EPIC

        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_err
        assert result.danger_err == TicketError.OpenDescendant


class TestSprintAssign:
    """`set_sprint` (T-0715), the `frob ticket sprint assign` primitive --
    same single-writer, ledger-locked shape as `set_component`."""

    def test_updates_sprint_field(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::set_sprint kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = set_sprint(tmp_path, ticket_id, "sprint-14")
        assert result.is_ok
        assert result.danger_ok.sprint == "sprint-14"

    def test_clears_to_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::set_sprint kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(
            title="a ticket",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            sprint="sprint-14",
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = set_sprint(tmp_path, ticket_id, None)
        assert result.is_ok
        assert result.danger_ok.sprint is None


class TestSprintShow:
    """`sprint_view` (T-0715), the `frob ticket sprint show` primitive:
    every ticket committed to a sprint label plus a state rollup and
    closed-count velocity."""

    def test_state_rollup_and_velocity(self) -> None:
        # frob:tests src/frob/tickets/__init__.py::sprint_view kind="unit"
        done = _ticket(ticket_id="T-0001", sprint="sprint-1", state=TicketState.DONE)
        queued = _ticket(
            ticket_id="T-0002", sprint="sprint-1", state=TicketState.QUEUED
        )
        other_sprint = _ticket(ticket_id="T-0003", sprint="sprint-2")
        queue = TicketQueue(tickets={t.id: t for t in (done, queued, other_sprint)})
        report = sprint_view(queue, "sprint-1")
        assert [t.id for t in report.tickets] == ["T-0001", "T-0002"]
        assert report.rollup == {TicketState.DONE: 1, TicketState.QUEUED: 1}
        assert report.closed == 1

    def test_no_tickets_in_sprint_is_empty_not_a_crash(self) -> None:
        # frob:tests src/frob/tickets/__init__.py::sprint_view kind="unit"
        queue = TicketQueue(tickets={})
        report = sprint_view(queue, "sprint-nonexistent")
        assert report.tickets == ()
        assert report.rollup == {}
        assert report.closed == 0
