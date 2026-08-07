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


# frob:ticket T-1151
class TestSetComponent:
    # frob:ticket T-1151
    def test_updates_component_field(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::set_component kind="unit"
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

    # frob:ticket T-1151
    def test_clears_to_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::set_component kind="unit"
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


# frob:ticket T-1171
class TestMutateLabels:
    def test_add_and_remove_labels(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_reporting.py::mutate_labels kind="unit"
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
        # frob:tests src/frob/tickets/_reporting.py::mutate_labels kind="unit"
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


class TestForceOverrideAudit:
    """T-1762: `--force` bypasses of a tracked safety guard now cost a
    required reason plus an append-only `force-overrides.jsonl` record --
    the T-1733 escape-hatch-accountability principle applied to `--force`
    (docs/modules/tickets.md#data-models)."""

    def test_record_force_override_requires_reason(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_force_override.py::record_force_override
        from frob.tickets._force_override import (
            ForceOverrideError,
            record_force_override,
        )

        result = record_force_override(
            tmp_path,
            command="ticket archive",
            guard="T-0843 live-cross-worktree-lease refusal",
            target="T-0001",
            reason="   ",
        )
        assert result.is_err
        assert result.danger_err is ForceOverrideError.ReasonMissing
        assert not (tmp_path / "force-overrides.jsonl").exists()

    # frob:waive SELFAUDIT001 reason="T-1762: reads back tmp_path's own force- \
    # overrides.jsonl fixture written earlier in this same test -- the testsuite \
    # node's ordinary tmp_path round-trip shape, not a new capability class"
    def test_record_force_override_appends_a_line(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_force_override.py::record_force_override
        import json

        from frob.tickets._force_override import record_force_override

        result = record_force_override(
            tmp_path,
            command="ticket land --finish",
            guard="T-1715 worktree-in-use refusal",
            target="T-1762:/tmp/wt",
            reason="independently confirmed the process holding it is dead",
            actor="tester",
        )
        assert result.is_ok
        lines = (tmp_path / "force-overrides.jsonl").read_text().splitlines()
        assert len(lines) == 1
        row = json.loads(lines[0])
        assert row["command"] == "ticket land --finish"
        assert row["guard"] == "T-1715 worktree-in-use refusal"
        assert row["target"] == "T-1762:/tmp/wt"
        assert row["actor"] == "tester"
        assert "independently confirmed" in row["reason"]

        # a second call appends, never rewrites -- the trail is a log, not
        # a table keyed on the most recent override.
        record_force_override(
            tmp_path,
            command="ticket archive",
            guard="T-0843 live-cross-worktree-lease refusal",
            target="T-0002",
            reason="second override, different guard entirely",
            actor="tester",
        )
        assert len((tmp_path / "force-overrides.jsonl").read_text().splitlines()) == 2

    def test_archive_force_with_no_live_lease_needs_no_reason(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_archive.py::_archive
        """`--force` with nothing to actually override is a no-op
        guard-wise -- it must not demand a reason for bypassing a guard
        that would not have fired anyway."""
        from typani import Ok

        from frob.app.ticket_runner._archive import _archive

        # `_archive` imports `archive`/`read_all_leases`/
        # `commit_full_ledger_change` lazily from their own source modules
        # inside its own body -- patch there, not on the runner module, so
        # the lazy import picks up the patch.
        import frob.tickets as tickets_mod
        import frob.tickets._leases as leases_mod

        monkeypatch.setattr(tickets_mod, "archive", lambda root, *, force: Ok(0))
        monkeypatch.setattr(leases_mod, "read_all_leases", lambda root: [])
        monkeypatch.setattr(
            leases_mod, "commit_full_ledger_change", lambda *a, **k: Ok(None)
        )

        # should not raise / sys.exit -- no reason was needed or given.
        _archive(tmp_path, force=True, no_commit=True)

    def test_archive_force_with_live_lease_and_no_reason_refuses(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_archive.py::_archive
        import pytest

        from frob.app.ticket_runner._archive import _archive
        import frob.tickets._leases as leases_mod

        class _FakeLease:
            ticket_id = "T-0001"

        monkeypatch.setattr(leases_mod, "read_all_leases", lambda root: [_FakeLease()])

        with pytest.raises(SystemExit):
            _archive(tmp_path, force=True, no_commit=True)
        assert not (tmp_path / "force-overrides.jsonl").exists()


# frob:ticket T-1613
class TestRunsLast:
    """`runs_last` (T-1613): a ticket marked runs-last stays structurally
    undoable -- excluded from `doable`, refused by `start` -- while ANY
    OTHER non-runs-last ticket in the ledger is non-terminal (queued/
    planned/in-progress/blocked). Filing a fresh ordinary ticket while a
    runs-last ticket is IN_PROGRESS warns loudly (does not block)."""

    # frob:ticket T-1613
    @staticmethod
    def _init_repo(tmp_path: Path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "a@b.c"], cwd=tmp_path, check=True
        )
        subprocess.run(["git", "config", "user.name", "a"], cwd=tmp_path, check=True)

    # frob:ticket T-1613
    def test_set_runs_last_updates_field(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::set_runs_last kind="unit"
        from frob.tickets import set_runs_last

        self._init_repo(tmp_path)
        spec = TicketSpec(title="a ticket", kind=TicketKind.FEATURE, origin=Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = set_runs_last(tmp_path, ticket_id, True)
        assert result.is_ok
        assert result.danger_ok.runs_last is True

    # frob:ticket T-1613
    def test_doable_excludes_runs_last_while_other_ticket_open(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_doable.py::_doable_candidates kind="unit"
        from frob.tickets import doable, load_queue, set_runs_last

        self._init_repo(tmp_path)
        runs_last_spec = TicketSpec(
            title="audit", kind=TicketKind.FEATURE, origin=Origin.HUMAN
        )
        created = new_ticket(tmp_path, runs_last_spec)
        assert created.is_ok
        runs_last_id = created.danger_ok.id
        set_result = set_runs_last(tmp_path, runs_last_id, True)
        assert set_result.is_ok

        other_spec = TicketSpec(
            title="ordinary work", kind=TicketKind.FEATURE, origin=Origin.HUMAN
        )
        other_created = new_ticket(tmp_path, other_spec)
        assert other_created.is_ok

        queue = load_queue(tmp_path)
        assert queue.is_ok
        candidates = doable(queue.danger_ok, tmp_path, ignore_lease=True)
        assert runs_last_id not in {t.id for t in candidates}

    # frob:ticket T-1613
    def test_doable_includes_runs_last_once_all_other_tickets_terminal(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_doable.py::_doable_candidates kind="unit"
        from frob.tickets import doable, drop_ticket, load_queue, set_runs_last

        self._init_repo(tmp_path)
        runs_last_spec = TicketSpec(
            title="audit", kind=TicketKind.FEATURE, origin=Origin.HUMAN
        )
        created = new_ticket(tmp_path, runs_last_spec)
        assert created.is_ok
        runs_last_id = created.danger_ok.id
        set_result = set_runs_last(tmp_path, runs_last_id, True)
        assert set_result.is_ok

        other_spec = TicketSpec(
            title="ordinary work", kind=TicketKind.FEATURE, origin=Origin.HUMAN
        )
        other_created = new_ticket(tmp_path, other_spec)
        assert other_created.is_ok
        other_id = other_created.danger_ok.id

        dropped = drop_ticket(tmp_path, other_id, reason="test")
        assert dropped.is_ok

        queue = load_queue(tmp_path)
        assert queue.is_ok
        candidates = doable(queue.danger_ok, tmp_path, ignore_lease=True)
        assert runs_last_id in {t.id for t in candidates}

    # frob:ticket T-1613
    def test_start_refuses_runs_last_while_other_ticket_open(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_evidence.py::_transition_guard kind="unit"
        from frob.tickets import TicketError, TicketState, set_runs_last, transition

        self._init_repo(tmp_path)
        runs_last_spec = TicketSpec(
            title="audit", kind=TicketKind.FEATURE, origin=Origin.HUMAN
        )
        created = new_ticket(tmp_path, runs_last_spec)
        assert created.is_ok
        runs_last_id = created.danger_ok.id
        set_result = set_runs_last(tmp_path, runs_last_id, True)
        assert set_result.is_ok

        other_spec = TicketSpec(
            title="ordinary work", kind=TicketKind.FEATURE, origin=Origin.HUMAN
        )
        other_created = new_ticket(tmp_path, other_spec)
        assert other_created.is_ok

        planned = transition(tmp_path, runs_last_id, TicketState.PLANNED)
        assert planned.is_ok
        result = transition(tmp_path, runs_last_id, TicketState.IN_PROGRESS)
        assert result.is_err
        assert result.danger_err is TicketError.RunsLastBlocked

    # frob:ticket T-1613
    def test_multiple_runs_last_tickets_do_not_block_each_other(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_doable.py::_doable_candidates kind="unit"
        from frob.tickets import doable, load_queue, set_runs_last

        self._init_repo(tmp_path)
        spec_a = TicketSpec(title="audit a", kind=TicketKind.FEATURE, origin=Origin.HUMAN)
        created_a = new_ticket(tmp_path, spec_a)
        assert created_a.is_ok
        id_a = created_a.danger_ok.id
        assert set_runs_last(tmp_path, id_a, True).is_ok

        spec_b = TicketSpec(title="audit b", kind=TicketKind.FEATURE, origin=Origin.HUMAN)
        created_b = new_ticket(tmp_path, spec_b)
        assert created_b.is_ok
        id_b = created_b.danger_ok.id
        assert set_runs_last(tmp_path, id_b, True).is_ok

        queue = load_queue(tmp_path)
        assert queue.is_ok
        candidates = {t.id for t in doable(queue.danger_ok, tmp_path, ignore_lease=True)}
        assert id_a in candidates
        assert id_b in candidates

    # frob:ticket T-1613
    def test_filing_new_ticket_while_runs_last_in_progress_warns(
        self, tmp_path: Path, caplog
    ) -> None:
        # frob:tests src/frob/tickets/_new_renumber.py::new_ticket kind="unit"
        import logging

        from frob.tickets import TicketState, set_runs_last, transition

        self._init_repo(tmp_path)
        runs_last_spec = TicketSpec(
            title="audit", kind=TicketKind.FEATURE, origin=Origin.HUMAN
        )
        created = new_ticket(tmp_path, runs_last_spec)
        assert created.is_ok
        runs_last_id = created.danger_ok.id
        assert set_runs_last(tmp_path, runs_last_id, True).is_ok
        planned = transition(tmp_path, runs_last_id, TicketState.PLANNED)
        assert planned.is_ok
        started = transition(tmp_path, runs_last_id, TicketState.IN_PROGRESS)
        assert started.is_ok

        caplog.set_level(logging.WARNING)
        other_spec = TicketSpec(
            title="new work", kind=TicketKind.BUG, origin=Origin.HUMAN
        )
        other_created = new_ticket(tmp_path, other_spec)
        assert other_created.is_ok
        assert any(
            runs_last_id in record.getMessage() and "IN_PROGRESS" in record.getMessage()
            for record in caplog.records
        )
