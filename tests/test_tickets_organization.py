"""Tests for T-0454's ticket organization model: component/labels fields,
set_component, mutate_labels, board_view, epic_rollup
(docs/modules/tickets.md#data-models)."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.tickets import (
    BOARD_STATES,
    Origin,
    Priority,
    Ticket,
    TicketError,
    TicketKind,
    TicketQueue,
    TicketSpec,
    TicketState,
    board_view,
    epic_rollup,
    mutate_labels,
    new_ticket,
    set_component,
)
from frob.tickets._store import _serialize_ticket, load_all, write_ticket


def _ticket(
    *,
    ticket_id: str,
    state: TicketState = TicketState.QUEUED,
    priority: Priority = Priority.MEDIUM,
    parent: str | None = None,
    component: str | None = None,
    labels: tuple[str, ...] = (),
    created: date = date(2026, 1, 1),
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
        scope=(),
        evidence=(),
        attachments=(),
        acceptance=(),
        threat=None,
        component=component,
        labels=labels,
        body="",
    )


class TestFieldRoundTrip:
    """component/labels survive `_serialize_ticket`/`write_ticket` + a fresh
    load, the same T-0411 priority-field precedent for a schema addition
    (T-0454)."""

    def test_serialize_parse_round_trip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::_serialize_ticket kind="unit"
        from frob.tickets._store import _parse_ticket_file

        ticket = _ticket(
            ticket_id="T-0001", component="gates", labels=("perf", "flaky")
        )
        text = _serialize_ticket(ticket)
        path = tmp_path / "T-0001-ticket-t-0001.md"
        path.write_text(text, encoding="utf-8")

        result = _parse_ticket_file(path)
        assert result.is_ok
        assert result.danger_ok.component == "gates"
        assert result.danger_ok.labels == ("perf", "flaky")

    def test_write_ticket_ledger_round_trip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::write_ticket kind="unit"
        ticket = _ticket(ticket_id="T-0001", component="tickets", labels=("a", "b"))
        written = write_ticket(tmp_path, ticket)
        assert written.is_ok

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].component == "tickets"
        assert loaded.danger_ok["T-0001"].labels == ("a", "b")

    def test_comma_joined_label_splits(self) -> None:
        # frob:tests src/frob/tickets/_models.py::_split_scope_entries kind="unit"
        # frob:waive COV006 reason="T-1024: genuinely reachable -- constructing a Ticket runs the labels field's @field_validator (_normalize_labels), which calls _split_scope_entries (T-0454's reuse of the scope-splitting helper for labels too); frob.graph.callgraph's best-effort BFS cannot trace through pydantic's validator-decorator dispatch"  # noqa: E501
        ticket = _ticket(ticket_id="T-0001", labels=("a,b",))
        assert ticket.labels == ("a", "b")

    def test_new_ticket_carries_component_and_labels(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_new_renumber.py::new_ticket kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(
            title="a ticket",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            component="dup",
            labels=("x", "y"),
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        assert created.danger_ok.component == "dup"
        assert created.danger_ok.labels == ("x", "y")


class TestSetComponent:
    def test_updates_component_field(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::set_component kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = set_component(tmp_path, ticket_id, "vet")
        assert result.is_ok
        assert result.danger_ok.component == "vet"

    def test_clears_to_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::set_component kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(
            title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN, component="vet"
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = set_component(tmp_path, ticket_id, None)
        assert result.is_ok
        assert result.danger_ok.component is None


class TestMutateLabels:
    def test_add_and_remove_labels(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::mutate_labels kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(
            title="a ticket",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            labels=("a", "b"),
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = mutate_labels(tmp_path, ticket_id, add=("c",), remove=("a",))
        assert result.is_ok
        assert result.danger_ok.labels == ("b", "c")

    def test_empty_call_is_error(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::mutate_labels kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = mutate_labels(tmp_path, ticket_id)
        assert result.is_err
        assert result.danger_err == TicketError.LabelChangeEmpty


class TestBoardView:
    def test_columns_in_fixed_order(self) -> None:
        # frob:tests src/frob/tickets/__init__.py::board_view kind="unit"
        queue = TicketQueue(tickets={})
        columns = board_view(queue)
        assert tuple(col.state for col in columns) == BOARD_STATES

    def test_priority_ordered_within_column(self) -> None:
        # frob:tests src/frob/tickets/__init__.py::board_view kind="unit"
        low = _ticket(
            ticket_id="T-1001", priority=Priority.LOW, created=date(2020, 1, 1)
        )
        high = _ticket(
            ticket_id="T-1002", priority=Priority.HIGH, created=date(2026, 1, 1)
        )
        queue = TicketQueue(tickets={low.id: low, high.id: high})
        columns = board_view(queue)
        queued = next(c for c in columns if c.state is TicketState.QUEUED)
        assert [t.id for t in queued.tickets] == ["T-1002", "T-1001"]

    def test_component_filter(self) -> None:
        # frob:tests src/frob/tickets/__init__.py::board_view kind="unit"
        gates_ticket = _ticket(ticket_id="T-1001", component="gates")
        dup_ticket = _ticket(ticket_id="T-1002", component="dup")
        queue = TicketQueue(
            tickets={gates_ticket.id: gates_ticket, dup_ticket.id: dup_ticket}
        )
        columns = board_view(queue, component="gates")
        queued = next(c for c in columns if c.state is TicketState.QUEUED)
        assert [t.id for t in queued.tickets] == ["T-1001"]

    def test_label_filter(self) -> None:
        # frob:tests src/frob/tickets/__init__.py::board_view kind="unit"
        perf_ticket = _ticket(ticket_id="T-1001", labels=("perf",))
        flaky_ticket = _ticket(ticket_id="T-1002", labels=("flaky",))
        queue = TicketQueue(
            tickets={perf_ticket.id: perf_ticket, flaky_ticket.id: flaky_ticket}
        )
        columns = board_view(queue, label="perf")
        queued = next(c for c in columns if c.state is TicketState.QUEUED)
        assert [t.id for t in queued.tickets] == ["T-1001"]


class TestEpicRollup:
    def test_not_found_is_err(self) -> None:
        # frob:tests src/frob/tickets/__init__.py::epic_rollup kind="unit"
        queue = TicketQueue(tickets={})
        result = epic_rollup(queue, "T-9999")
        assert result.is_err
        assert result.danger_err == TicketError.NotFound

    def test_counts_done_and_total(self) -> None:
        # frob:tests src/frob/tickets/__init__.py::epic_rollup kind="unit"
        epic = _ticket(ticket_id="T-0001")
        story = _ticket(ticket_id="T-0002", parent="T-0001")
        task_done = _ticket(ticket_id="T-0003", parent="T-0002", state=TicketState.DONE)
        task_queued = _ticket(ticket_id="T-0004", parent="T-0002")
        queue = TicketQueue(
            tickets={
                epic.id: epic,
                story.id: story,
                task_done.id: task_done,
                task_queued.id: task_queued,
            }
        )
        result = epic_rollup(queue, "T-0001")
        assert result.is_ok
        rollup = result.danger_ok
        assert rollup.total == 3  # story + both tasks, transitively
        assert rollup.done == 1
        assert rollup.percent_complete == (1 / 3) * 100.0

    def test_blocked_leaf_surfaced(self) -> None:
        # frob:tests src/frob/tickets/__init__.py::epic_rollup kind="unit"
        epic = _ticket(ticket_id="T-0001")
        blocked_leaf = _ticket(
            ticket_id="T-0002", parent="T-0001", state=TicketState.BLOCKED
        )
        queue = TicketQueue(tickets={epic.id: epic, blocked_leaf.id: blocked_leaf})
        result = epic_rollup(queue, "T-0001")
        assert result.is_ok
        assert result.danger_ok.blocked_leaves == ("T-0002",)

    def test_childless_epic_is_zero_percent_not_a_crash(self) -> None:
        # frob:tests src/frob/tickets/_models.py::EpicRollup.percent_complete kind="unit"  # noqa: E501
        epic = _ticket(ticket_id="T-0001")
        queue = TicketQueue(tickets={epic.id: epic})
        result = epic_rollup(queue, "T-0001")
        assert result.is_ok
        assert result.danger_ok.total == 0
        assert result.danger_ok.percent_complete == 0.0
