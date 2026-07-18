"""Tests for frob.tickets: queue loading, state machine, doable, failure log, attach."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pytest

from frob.tickets import (
    AttachmentSource,
    FailureEntry,
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketState,
    add_evidence,
    archive,
    attach,
    doable,
    load_active,
    load_queue,
    new_ticket,
    record_failure,
    transition,
)
from frob.tickets._store import serialize_ticket


def _ticket(
    *,
    ticket_id: str = "T-0001",
    title: str = "Sample ticket",
    state: TicketState = TicketState.QUEUED,
    created: date = date(2026, 1, 1),
    blocked_by: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
    body: str = "## Description\nsomething\n",
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=title,
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=created,
        blocked_by=blocked_by,
        parent=None,
        scope=(),
        evidence=evidence,
        attachments=(),
        body=body,
    )


def _write(root: Path, ticket: Ticket, slug: str = "sample-ticket") -> Path:
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    path = tickets_dir / f"{ticket.id}-{slug}.md"
    path.write_text(serialize_ticket(ticket), encoding="utf-8")
    return path


class TestQueue:
    def test_round_trip_load(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::load_queue
        ticket = _ticket(body="## Description\ntrailing spaces   \n\nmore text\n")
        _write(tmp_path, ticket)
        result = load_queue(tmp_path)
        assert result.is_ok
        queue = result.danger_ok
        assert set(queue.tickets) == {"T-0001"}
        assert queue.tickets["T-0001"].body == ticket.body

    def test_body_preserved_verbatim(self, tmp_path: Path) -> None:
        body = "## Description\nline one\n   indented\ttab\n\n\nlast line\n"
        ticket = _ticket(body=body)
        _write(tmp_path, ticket)
        result = load_queue(tmp_path)
        assert result.danger_ok.tickets["T-0001"].body == body

    def test_malformed_frontmatter_is_err(self, tmp_path: Path) -> None:
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        (tickets_dir / "T-0001-bad.md").write_text("not frontmatter at all\n")
        result = load_queue(tmp_path)
        assert result.is_err
        assert result.danger_err is TicketError.MalformedFrontmatter

    def test_unknown_frontmatter_key_is_err(self, tmp_path: Path) -> None:
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        text = (
            "---\n"
            "id: T-0001\n"
            "title: Sample\n"
            "state: queued\n"
            "kind: feature\n"
            "origin: human\n"
            "created: 2026-01-01\n"
            "blocked_by: []\n"
            "parent: null\n"
            "scope: []\n"
            "evidence: []\n"
            "attachments: []\n"
            "bogus_field: oops\n"
            "---\n"
            "body\n"
        )
        (tickets_dir / "T-0001-sample.md").write_text(text)
        result = load_queue(tmp_path)
        assert result.is_err
        assert result.danger_err is TicketError.MalformedFrontmatter

    def test_duplicate_id_is_err(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(ticket_id="T-0001"), slug="a")
        _write(tmp_path, _ticket(ticket_id="T-0001", title="Other"), slug="b")
        result = load_queue(tmp_path)
        assert result.is_err
        assert result.danger_err is TicketError.DuplicateId


class TestNewTicket:
    def test_allocates_sequential_id(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::new_ticket
        _write(tmp_path, _ticket(ticket_id="T-0001"))
        from frob.tickets import TicketSpec

        spec = TicketSpec(
            title="Second ticket", kind=TicketKind.BUG, origin=Origin.AGENT
        )
        result = new_ticket(tmp_path, spec)
        assert result.is_ok
        assert result.danger_ok.id == "T-0002"
        assert result.danger_ok.state == TicketState.QUEUED

    def test_first_ticket_gets_0001(self, tmp_path: Path) -> None:
        from frob.tickets import TicketSpec

        spec = TicketSpec(title="First!", kind=TicketKind.FEATURE, origin=Origin.HUMAN)
        result = new_ticket(tmp_path, spec)
        assert result.is_ok
        assert result.danger_ok.id == "T-0001"


class TestStateMachine:
    @pytest.mark.parametrize(
        "start,to",
        [
            (TicketState.QUEUED, TicketState.PLANNED),
            (TicketState.QUEUED, TicketState.DROPPED),
            (TicketState.PLANNED, TicketState.DROPPED),
            (TicketState.BLOCKED, TicketState.DROPPED),
        ],
    )
    def test_legal_transitions(
        self, tmp_path: Path, start: TicketState, to: TicketState
    ) -> None:
        # frob:tests src/frob/tickets/__init__.py::transition
        _write(tmp_path, _ticket(state=start))
        result = transition(tmp_path, "T-0001", to)
        assert result.is_ok, result.err
        assert result.danger_ok.state == to

    def test_transition_queued_to_planned_unit(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::transition kind="unit"
        _write(tmp_path, _ticket(state=TicketState.QUEUED))
        result = transition(tmp_path, "T-0001", TicketState.PLANNED)
        assert result.is_ok, result.err
        assert result.danger_ok.state == TicketState.PLANNED

    def test_planned_to_in_progress(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(state=TicketState.PLANNED))
        result = transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)
        assert result.is_ok
        assert result.danger_ok.state == TicketState.IN_PROGRESS

    def test_in_progress_to_blocked(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(state=TicketState.IN_PROGRESS))
        result = transition(tmp_path, "T-0001", TicketState.BLOCKED)
        assert result.is_ok

    def test_blocked_to_in_progress(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(state=TicketState.BLOCKED))
        result = transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)
        assert result.is_ok

    def test_in_progress_to_queued_yield(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(state=TicketState.IN_PROGRESS))
        result = transition(tmp_path, "T-0001", TicketState.QUEUED)
        assert result.is_ok

    def test_in_progress_to_dropped(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(state=TicketState.IN_PROGRESS))
        result = transition(tmp_path, "T-0001", TicketState.DROPPED)
        assert result.is_ok

    def test_in_progress_to_done_with_evidence_and_report(self, tmp_path: Path) -> None:
        body = "## Description\nx\n\n## Done report\nAll good.\n"
        _write(
            tmp_path,
            _ticket(
                state=TicketState.IN_PROGRESS,
                evidence=("tests/x.py::test_a",),
                body=body,
            ),
        )
        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_ok
        assert result.danger_ok.state == TicketState.DONE

    @pytest.mark.parametrize(
        "start,to",
        [
            (TicketState.QUEUED, TicketState.IN_PROGRESS),
            (TicketState.QUEUED, TicketState.DONE),
            (TicketState.QUEUED, TicketState.BLOCKED),
            (TicketState.PLANNED, TicketState.DONE),
            (TicketState.PLANNED, TicketState.QUEUED),
            (TicketState.PLANNED, TicketState.BLOCKED),
            (TicketState.IN_PROGRESS, TicketState.PLANNED),
            (TicketState.BLOCKED, TicketState.DONE),
            (TicketState.BLOCKED, TicketState.QUEUED),
            (TicketState.DONE, TicketState.QUEUED),
            (TicketState.DROPPED, TicketState.QUEUED),
        ],
    )
    def test_illegal_transitions(
        self, tmp_path: Path, start: TicketState, to: TicketState
    ) -> None:
        _write(tmp_path, _ticket(state=start))
        result = transition(tmp_path, "T-0001", to)
        assert result.is_err
        assert result.danger_err is TicketError.InvalidTransition

    def test_done_without_evidence_errs(self, tmp_path: Path) -> None:
        body = "## Description\nx\n\n## Done report\nAll good.\n"
        _write(tmp_path, _ticket(state=TicketState.IN_PROGRESS, evidence=(), body=body))
        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_err
        assert result.danger_err is TicketError.MissingEvidence

    def test_done_without_report_section_errs(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            _ticket(
                state=TicketState.IN_PROGRESS,
                evidence=("tests/x.py::test_a",),
                body="## Description\nx\n",
            ),
        )
        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_err
        assert result.danger_err is TicketError.MissingEvidence

    def test_start_with_open_blocker_errs(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            _ticket(
                ticket_id="T-0001", state=TicketState.PLANNED, blocked_by=("T-0002",)
            ),
            slug="a",
        )
        _write(
            tmp_path,
            _ticket(ticket_id="T-0002", state=TicketState.QUEUED, title="Blocker"),
            slug="b",
        )
        result = transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)
        assert result.is_err
        assert result.danger_err is TicketError.BlockerOpen

    def test_blocker_done_unblocks(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            _ticket(
                ticket_id="T-0001", state=TicketState.PLANNED, blocked_by=("T-0002",)
            ),
            slug="a",
        )
        _write(
            tmp_path,
            _ticket(ticket_id="T-0002", state=TicketState.DONE, title="Blocker"),
            slug="b",
        )
        result = transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)
        assert result.is_ok

    def test_blocker_dropped_unblocks(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            _ticket(
                ticket_id="T-0001", state=TicketState.PLANNED, blocked_by=("T-0002",)
            ),
            slug="a",
        )
        _write(
            tmp_path,
            _ticket(ticket_id="T-0002", state=TicketState.DROPPED, title="Blocker"),
            slug="b",
        )
        result = transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)
        assert result.is_ok

    def test_unknown_ticket_not_found(self, tmp_path: Path) -> None:
        (tmp_path / "tickets").mkdir()
        result = transition(tmp_path, "T-9999", TicketState.PLANNED)
        assert result.is_err
        assert result.danger_err is TicketError.NotFound


class TestDoable:
    def test_ordering_by_created_then_id(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::doable
        _write(
            tmp_path,
            _ticket(ticket_id="T-0002", created=date(2026, 1, 1), title="B"),
            slug="b",
        )
        _write(
            tmp_path,
            _ticket(ticket_id="T-0001", created=date(2026, 1, 2), title="A"),
            slug="a",
        )
        _write(
            tmp_path,
            _ticket(ticket_id="T-0003", created=date(2026, 1, 1), title="C"),
            slug="c",
        )
        queue = load_queue(tmp_path).danger_ok
        result = doable(queue)
        assert [t.id for t in result] == ["T-0002", "T-0003", "T-0001"]

    def test_blocked_excluded(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            _ticket(
                ticket_id="T-0001", state=TicketState.QUEUED, blocked_by=("T-0002",)
            ),
            slug="a",
        )
        _write(
            tmp_path,
            _ticket(ticket_id="T-0002", state=TicketState.QUEUED, title="Blocker"),
            slug="b",
        )
        queue = load_queue(tmp_path).danger_ok
        result = doable(queue)
        ids = {t.id for t in result}
        assert "T-0001" not in ids
        assert "T-0002" in ids

    def test_planned_included(self, tmp_path: Path) -> None:
        _write(
            tmp_path, _ticket(ticket_id="T-0001", state=TicketState.PLANNED), slug="a"
        )
        queue = load_queue(tmp_path).danger_ok
        result = doable(queue)
        assert [t.id for t in result] == ["T-0001"]

    def test_in_progress_excluded(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            _ticket(ticket_id="T-0001", state=TicketState.IN_PROGRESS),
            slug="a",
        )
        queue = load_queue(tmp_path).danger_ok
        assert doable(queue) == ()


class TestFailureLog:
    def test_appends_creates_section(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::record_failure
        _write(tmp_path, _ticket(body="## Description\nx\n"))
        entry = FailureEntry(
            date=date(2026, 1, 5), attempt=1, summary="wl-paste has no socket"
        )
        result = record_failure(tmp_path, "T-0001", entry)
        assert result.is_ok
        body = result.danger_ok.body
        assert "## Failure log" in body
        assert "2026-01-05 attempt 1: wl-paste has no socket" in body

    def test_appends_existing_section_preserves_rest(self, tmp_path: Path) -> None:
        body = "## Description\nx\n\n## Failure log\n- 2026-01-01 attempt 1: first try\n\n## Plan\nsteps\n"
        _write(tmp_path, _ticket(body=body))
        entry = FailureEntry(date=date(2026, 1, 6), attempt=2, summary="second try")
        result = record_failure(tmp_path, "T-0001", entry)
        assert result.is_ok
        new_body = result.danger_ok.body
        assert "- 2026-01-01 attempt 1: first try" in new_body
        assert "- 2026-01-06 attempt 2: second try" in new_body
        assert "## Plan\nsteps" in new_body
        assert new_body.index("first try") < new_body.index("second try")
        assert new_body.index("## Failure log") < new_body.index("## Plan")

    def test_unknown_ticket_not_found(self, tmp_path: Path) -> None:
        (tmp_path / "tickets").mkdir()
        entry = FailureEntry(date=date(2026, 1, 6), attempt=1, summary="x")
        result = record_failure(tmp_path, "T-9999", entry)
        assert result.is_err
        assert result.danger_err is TicketError.NotFound


class TestAttach:
    def test_file_source_copies_and_records_sha256(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::attach
        _write(tmp_path, _ticket())
        src = tmp_path / "mockup.png"
        data = b"fake-png-bytes"
        src.write_bytes(data)
        result = attach(
            tmp_path, "T-0001", AttachmentSource(path=src), "paste flow mockup"
        )
        assert result.is_ok
        attachment = result.danger_ok
        assert attachment.sha256 == hashlib.sha256(data).hexdigest()
        assert attachment.caption == "paste flow mockup"
        dest = tmp_path / "tickets" / attachment.path
        assert dest.exists()
        assert dest.read_bytes() == data

        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].attachments == (attachment,)

    def test_index_increments(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket())
        src = tmp_path / "a.png"
        src.write_bytes(b"one")
        first = attach(tmp_path, "T-0001", AttachmentSource(path=src), "first")
        assert first.is_ok
        assert first.danger_ok.path.split("/")[-1].startswith("01-")

        src2 = tmp_path / "b.png"
        src2.write_bytes(b"two")
        second = attach(tmp_path, "T-0001", AttachmentSource(path=src2), "second")
        assert second.is_ok
        assert second.danger_ok.path.split("/")[-1].startswith("02-")

    def test_large_file_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        _write(tmp_path, _ticket())
        src = tmp_path / "big.png"
        src.write_bytes(b"x" * (1024 * 1024 + 1))
        with caplog.at_level("WARNING"):
            result = attach(tmp_path, "T-0001", AttachmentSource(path=src), "big one")
        assert result.is_ok
        assert any(">1MB" in rec.message for rec in caplog.records)

    def test_unknown_ticket_not_found(self, tmp_path: Path) -> None:
        (tmp_path / "tickets").mkdir()
        src = tmp_path / "a.png"
        src.write_bytes(b"x")
        result = attach(tmp_path, "T-9999", AttachmentSource(path=src), "cap")
        assert result.is_err
        assert result.danger_err is TicketError.NotFound


class TestEvidence:
    def test_resolvable_ids_appended(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::add_evidence
        _write(tmp_path, _ticket())
        collected = frozenset({"tests/test_x.py::test_a", "tests/test_x.py::test_b"})
        result = add_evidence(
            tmp_path, "T-0001", ["tests/test_x.py::test_a"], collected
        )
        assert result.is_ok
        assert result.danger_ok.evidence == ("tests/test_x.py::test_a",)

        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].evidence == ("tests/test_x.py::test_a",)

    def test_parametrized_bare_name_matches(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket())
        collected = frozenset({"tests/test_x.py::test_a[case0]"})
        result = add_evidence(
            tmp_path, "T-0001", ["tests/test_x.py::test_a"], collected
        )
        assert result.is_ok
        assert result.danger_ok.evidence == ("tests/test_x.py::test_a",)

    def test_unresolvable_id_rejected(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket())
        collected = frozenset({"tests/test_x.py::test_a"})
        result = add_evidence(
            tmp_path, "T-0001", ["tests/test_x.py::test_missing"], collected
        )
        assert result.is_err
        assert result.danger_err is TicketError.UnknownEvidence
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].evidence == ()

    def test_mixed_batch_rejected_wholesale(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket())
        collected = frozenset({"tests/test_x.py::test_a"})
        result = add_evidence(
            tmp_path,
            "T-0001",
            ["tests/test_x.py::test_a", "tests/test_x.py::test_missing"],
            collected,
        )
        assert result.is_err
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].evidence == ()

    def test_dedupes_against_existing_evidence(self, tmp_path: Path) -> None:
        ticket = _ticket(evidence=("tests/test_x.py::test_a",))
        _write(tmp_path, ticket)
        collected = frozenset({"tests/test_x.py::test_a", "tests/test_x.py::test_b"})
        result = add_evidence(
            tmp_path,
            "T-0001",
            ["tests/test_x.py::test_a", "tests/test_x.py::test_b"],
            collected,
        )
        assert result.is_ok
        assert result.danger_ok.evidence == (
            "tests/test_x.py::test_a",
            "tests/test_x.py::test_b",
        )

    def test_unknown_ticket_not_found(self, tmp_path: Path) -> None:
        (tmp_path / "tickets").mkdir()
        result = add_evidence(tmp_path, "T-9999", ["x"], frozenset({"x"}))
        assert result.is_err
        assert result.danger_err is TicketError.NotFound


class TestArchive:
    def test_moves_done_and_dropped_only(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::archive
        # frob:tests src/frob/tickets/__init__.py::load_active
        _write(tmp_path, _ticket(ticket_id="T-0001", state=TicketState.DONE), "done")
        _write(
            tmp_path,
            _ticket(ticket_id="T-0002", state=TicketState.DROPPED),
            "dropped",
        )
        _write(tmp_path, _ticket(ticket_id="T-0003", state=TicketState.QUEUED), "open")
        result = archive(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 2

        active = load_active(tmp_path).danger_ok
        assert set(active.tickets) == {"T-0003"}

        from frob.tickets._store import load_archive

        archived = load_archive(tmp_path).danger_ok
        assert set(archived) == {"T-0001", "T-0002"}

    def test_idempotent_second_run_moves_nothing(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(ticket_id="T-0001", state=TicketState.DONE), "done")
        first = archive(tmp_path)
        assert first.danger_ok == 1
        second = archive(tmp_path)
        assert second.is_ok
        assert second.danger_ok == 0

    def test_nothing_to_archive_is_zero(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(ticket_id="T-0001", state=TicketState.QUEUED), "open")
        result = archive(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 0

    def test_load_queue_merges_active_and_archive(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(ticket_id="T-0001", state=TicketState.DONE), "done")
        archive(tmp_path)
        _write(tmp_path, _ticket(ticket_id="T-0002", state=TicketState.QUEUED), "open")

        merged = load_queue(tmp_path)
        assert merged.is_ok
        assert set(merged.danger_ok.tickets) == {"T-0001", "T-0002"}

        active_only = load_active(tmp_path)
        assert set(active_only.danger_ok.tickets) == {"T-0002"}

    def test_blocked_by_archived_ticket_resolves_closed(self, tmp_path: Path) -> None:
        # A blocker that has since been archived (done) must still let the
        # blocked ticket start -- it must not look like an unknown/open
        # blocker just because it moved out of the active ledger.
        _write(tmp_path, _ticket(ticket_id="T-0001", state=TicketState.DONE), "done")
        archive(tmp_path)
        from frob.tickets._store import write_ticket as _write_ticket

        _write_ticket(
            tmp_path,
            _ticket(
                ticket_id="T-0002", state=TicketState.QUEUED, blocked_by=("T-0001",)
            ),
        )
        planned = transition(tmp_path, "T-0002", TicketState.PLANNED)
        assert planned.is_ok
        started = transition(tmp_path, "T-0002", TicketState.IN_PROGRESS)
        assert started.is_ok


class TestSingleFileLedger:
    def _spec(self, title="a ticket"):
        from frob.tickets import Origin, TicketKind, TicketSpec

        return TicketSpec(
            title=title,
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            scope=("src/x.py",),
            body="Body line.\n",
        )

    def test_new_tickets_land_in_single_tickets_md(self, tmp_path):
        from frob.tickets import load_queue, new_ticket

        a = new_ticket(tmp_path, self._spec("first")).danger_ok
        b = new_ticket(tmp_path, self._spec("second")).danger_ok
        assert (tmp_path / "tickets.md").exists()
        assert not (tmp_path / "tickets").exists()
        q = load_queue(tmp_path).danger_ok
        assert set(q.tickets) == {a.id, b.id}
        assert q.tickets[a.id].title == "first"
        assert q.tickets[b.id].scope == ("src/x.py",)

    def test_ledger_round_trips_body_and_transitions(self, tmp_path):
        from frob.tickets import TicketState, load_queue, new_ticket, transition

        t = new_ticket(tmp_path, self._spec()).danger_ok
        transition(tmp_path, t.id, TicketState.PLANNED)
        transition(tmp_path, t.id, TicketState.IN_PROGRESS)
        q = load_queue(tmp_path).danger_ok
        assert q.tickets[t.id].state == TicketState.IN_PROGRESS
        assert "Body line." in q.tickets[t.id].body

    def test_malformed_ledger_is_hard_err(self, tmp_path):
        from frob.tickets import TicketError, load_queue

        (tmp_path / "tickets.md").write_text(
            "# Tickets\n\n<!-- ticket:T-0001 -->\nno yaml fence here\n",
            encoding="utf-8",
        )
        result = load_queue(tmp_path)
        assert result.is_err
        assert result.danger_err == TicketError.MalformedFrontmatter

    def test_migrate_collapses_dir_into_ledger(self, tmp_path):
        from datetime import date

        from frob.tickets import load_queue, migrate
        from frob.tickets._models import Origin as O
        from frob.tickets._models import Ticket, TicketKind, TicketState
        from frob.tickets._store import serialize_ticket, tickets_dir

        d = tickets_dir(tmp_path)
        d.mkdir()
        for n, title in [(1, "alpha"), (2, "beta")]:
            tk = Ticket(
                id=f"T-{n:04d}",
                title=title,
                state=TicketState.QUEUED,
                kind=TicketKind.BUG,
                origin=O.HUMAN,
                created=date.today(),
                blocked_by=(),
                parent=None,
                scope=(),
                evidence=(),
                attachments=(),
                body=f"body {title}\n",
            )
            (d / f"T-{n:04d}-{title}.md").write_text(
                serialize_ticket(tk), encoding="utf-8"
            )
        n = migrate(tmp_path).danger_ok
        assert n == 2
        assert (tmp_path / "tickets.md").exists()
        assert not list(d.glob("T-*.md"))
        q = load_queue(tmp_path).danger_ok
        assert {t.title for t in q.tickets.values()} == {"alpha", "beta"}

    def test_legacy_dir_still_reads_when_no_ledger(self, tmp_path):
        from datetime import date

        from frob.tickets import load_queue
        from frob.tickets._models import Origin as O
        from frob.tickets._models import Ticket, TicketKind, TicketState
        from frob.tickets._store import serialize_ticket, tickets_dir

        d = tickets_dir(tmp_path)
        d.mkdir()
        tk = Ticket(
            id="T-0001",
            title="legacy",
            state=TicketState.QUEUED,
            kind=TicketKind.DOCS,
            origin=O.HUMAN,
            created=date.today(),
            blocked_by=(),
            parent=None,
            scope=(),
            evidence=(),
            attachments=(),
            body="x\n",
        )
        (d / "T-0001-legacy.md").write_text(serialize_ticket(tk), encoding="utf-8")
        q = load_queue(tmp_path).danger_ok
        assert q.tickets["T-0001"].title == "legacy"


class TestSchemaExtras:
    def _spec(self, **kw):
        from frob.tickets import Origin, TicketKind, TicketSpec

        kw.setdefault("title", "t")
        kw.setdefault("kind", TicketKind.FEATURE)
        kw.setdefault("origin", Origin.AGENT)
        return TicketSpec(**kw)

    def test_incident_gets_postmortem_template(self, tmp_path):
        from frob.tickets import TicketKind, load_queue, new_ticket

        t = new_ticket(tmp_path, self._spec(kind=TicketKind.INCIDENT)).danger_ok
        q = load_queue(tmp_path).danger_ok
        body = q.tickets[t.id].body
        assert "## Root cause (blameless)" in body
        assert "## Action items" in body

    def test_acceptance_and_threat_round_trip(self, tmp_path):
        from frob.tickets import Stride, TicketKind, load_queue, new_ticket

        t = new_ticket(
            tmp_path,
            self._spec(
                kind=TicketKind.SECURITY,
                acceptance=("given X when Y then Z",),
                threat=Stride.TAMPERING,
            ),
        ).danger_ok
        q = load_queue(tmp_path).danger_ok
        assert q.tickets[t.id].acceptance == ("given X when Y then Z",)
        assert q.tickets[t.id].threat == Stride.TAMPERING

    def test_renumber_makes_ids_contiguous(self, tmp_path):
        from frob.tickets import (
            load_queue,
            new_ticket,
            renumber,
        )
        from frob.tickets._store import write_all

        new_ticket(tmp_path, self._spec(title="a")).danger_ok
        b = new_ticket(tmp_path, self._spec(title="b")).danger_ok
        new_ticket(tmp_path, self._spec(title="c")).danger_ok
        # simulate a gap: drop b, leaving T-0001 and T-0003
        q = load_queue(tmp_path).danger_ok
        remaining = {k: v for k, v in q.tickets.items() if k != b.id}
        write_all(tmp_path, remaining)
        n = renumber(tmp_path).danger_ok
        assert n >= 1
        ids = set(load_queue(tmp_path).danger_ok.tickets)
        assert ids == {"T-0001", "T-0002"}

    def test_renumber_rewrites_blocked_by(self, tmp_path):
        from frob.tickets import load_queue, new_ticket, renumber
        from frob.tickets._store import write_all

        a = new_ticket(tmp_path, self._spec(title="a")).danger_ok
        b = new_ticket(tmp_path, self._spec(title="b", blocked_by=(a.id,))).danger_ok
        q = load_queue(tmp_path).danger_ok
        # drop a, then re-add b blocked by old a id, forcing renumber remap
        write_all(tmp_path, {k: v for k, v in q.tickets.items()})
        # introduce a gap by removing a and keeping b (blocked_by references a)
        only_b = {b.id: q.tickets[b.id]}
        write_all(tmp_path, only_b)
        renumber(tmp_path).danger_ok
        q2 = load_queue(tmp_path).danger_ok
        assert "T-0001" in q2.tickets


def test_tickets_queue_workflow_integration(tmp_path: Path) -> None:
    # frob:tests src/frob/tickets kind="integration"
    # Exercises the ticket workflow across store + state machine: create two
    # tickets (one blocking the other), confirm doable ordering respects the
    # open blocker, then drive the blocker through its legal transitions and
    # confirm the dependent becomes doable.
    from frob.tickets import TicketSpec

    blocker = new_ticket(
        tmp_path,
        TicketSpec(title="blocker", kind=TicketKind.FEATURE, origin=Origin.HUMAN),
    ).danger_ok
    dependent = new_ticket(
        tmp_path,
        TicketSpec(
            title="dependent",
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            blocked_by=(blocker.id,),
        ),
    ).danger_ok

    queue = load_queue(tmp_path).danger_ok
    doable_ids = {t.id for t in doable(queue)}
    assert blocker.id in doable_ids
    assert dependent.id not in doable_ids  # open blocker hides it

    assert transition(tmp_path, blocker.id, TicketState.PLANNED).is_ok
    assert transition(tmp_path, blocker.id, TicketState.IN_PROGRESS).is_ok
    # cannot close without evidence + Done report
    assert transition(tmp_path, blocker.id, TicketState.DROPPED).is_ok

    queue2 = load_queue(tmp_path).danger_ok
    assert dependent.id in {t.id for t in doable(queue2)}
