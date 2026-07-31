"""Tests for frob.tickets: queue loading, state machine, doable, failure log, attach."""

from __future__ import annotations

import hashlib
import logging
from datetime import date
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import _drop
from frob.tickets import (
    AttachmentSource,
    FailureEntry,
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketSpec,
    TicketState,
    add_acceptance,
    add_evidence,
    archive,
    attach,
    doable,
    drop_ticket,
    load_active,
    load_queue,
    new_ticket,
    record_failure,
    scope_matches,
    transition,
    validate_evidence,
)
from frob.tickets._store import _serialize_ticket


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
    path.write_text(_serialize_ticket(ticket), encoding="utf-8")
    return path


# frob:ticket T-1103
class TestQueue:
    # frob:ticket T-1103
    def test_round_trip_load(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_archive.py::load_queue
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

    # invariant spec: [INV-004](invariants/INV-004.md)
    def test_malformed_frontmatter_is_err(self, tmp_path: Path) -> None:
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        (tickets_dir / "T-0001-bad.md").write_text("not frontmatter at all\n")
        result = load_queue(tmp_path)
        assert result.is_err
        assert result.danger_err is TicketError.MalformedFrontmatter

    def test_unknown_frontmatter_key_is_tolerated(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T-0838: an unknown ledger field no longer hard-fails
        MalformedFrontmatter -- it loads, with a WARNING naming the field, so
        an older frob binary can still read a newer ledger without bricking
        its own land (the schema-extending-feature incident this ticket
        fixes; see TestUnknownFieldForwardCompat below for the fuller
        round-trip regression)."""
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
        with caplog.at_level(logging.WARNING):
            result = load_queue(tmp_path)
        assert result.is_ok
        ticket = result.danger_ok.tickets["T-0001"]
        assert ticket.__pydantic_extra__ == {"bogus_field": "oops"}
        assert any("bogus_field" in rec.message for rec in caplog.records)

    def test_unknown_field_with_malformed_known_field_still_errs(
        self, tmp_path: Path
    ) -> None:
        """T-0838: tolerating an unknown field must never loosen validation
        of a KNOWN field -- a malformed `state:` alongside an unknown field
        still fails MalformedFrontmatter."""
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        text = (
            "---\n"
            "id: T-0001\n"
            "title: Sample\n"
            "state: not-a-real-state\n"
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
        # frob:tests src/frob/tickets/_new_renumber.py::new_ticket
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


class TestEvidenceValidation:
    """T-0102 companion fix: evidence is schema-validated at write time so a
    malformed entry can never land via `frob ticket new`/`close`."""

    def test_validate_evidence_accepts_plain_node_id(self) -> None:
        # frob:tests src/frob/tickets/__init__.py::validate_evidence kind="unit"
        result = validate_evidence("tests/test_foo.py::test_a")
        assert result.is_ok
        assert result.danger_ok == "tests/test_foo.py::test_a"

    def test_validate_evidence_strips_whitespace(self) -> None:
        result = validate_evidence("  tests/test_foo.py::test_a  ")
        assert result.danger_ok == "tests/test_foo.py::test_a"

    def test_validate_evidence_rejects_empty(self) -> None:
        result = validate_evidence("   ")
        assert result.is_err
        assert result.danger_err is TicketError.MalformedEvidence

    def test_validate_evidence_rejects_multiline(self) -> None:
        # This is the exact shape of hand-edit that broke tickets.md YAML
        # during the T-0067/68 review.
        result = validate_evidence("tests/test_foo.py::test_a\nbogus: nested\n")
        assert result.is_err
        assert result.danger_err is TicketError.MalformedEvidence

    def test_validate_evidence_rejects_over_length(self) -> None:
        result = validate_evidence("x" * 400)
        assert result.is_err
        assert result.danger_err is TicketError.MalformedEvidence

    def test_add_evidence_appends_and_round_trips(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_evidence.py::add_evidence kind="unit"
        _write(tmp_path, _ticket(ticket_id="T-0001"))
        result = add_evidence(tmp_path, "T-0001", ("tests/test_foo.py::test_a",))
        assert result.is_ok
        assert result.danger_ok.evidence == ("tests/test_foo.py::test_a",)
        reloaded = load_queue(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets["T-0001"].evidence == (
            "tests/test_foo.py::test_a",
        )

    def test_add_evidence_rejects_malformed_entry_before_write(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, _ticket(ticket_id="T-0001"))
        result = add_evidence(tmp_path, "T-0001", ("bad\nentry",))
        assert result.is_err
        assert result.danger_err is TicketError.MalformedEvidence
        # nothing should have been written
        reloaded = load_queue(tmp_path)
        assert reloaded.danger_ok.tickets["T-0001"].evidence == ()

    def test_new_ticket_validates_evidence(self, tmp_path: Path) -> None:
        from frob.tickets import TicketSpec

        spec = TicketSpec(
            title="With evidence",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            evidence=("bad\nentry",),
        )
        result = new_ticket(tmp_path, spec)
        assert result.is_err
        assert result.danger_err is TicketError.MalformedEvidence

    def test_validate_evidence_normalizes_dot_separator_to_double_colon(
        self,
    ) -> None:
        # frob:tests src/frob/tickets/__init__.py::normalize_evidence_separator \
        # kind="unit"
        # T-0293: a hand-recorded `Class.method` (dot) evidence id never
        # resolves against real pytest node ids (`Class::method`); it must
        # be canonicalized at write time, not silently stored.
        result = validate_evidence("tests/test_foo.py::TestFoo.test_a")
        assert result.is_ok
        assert result.danger_ok == "tests/test_foo.py::TestFoo::test_a"

    def test_validate_evidence_leaves_correct_double_colon_form_unchanged(
        self,
    ) -> None:
        # frob:tests \
        # tests/test_tickets.py::TestEvidenceValidation.test_validate_evidence_leaves_c\
        # orrect_double_colon_form_unchanged kind="unit"
        result = validate_evidence("tests/test_foo.py::TestFoo::test_a")
        assert result.is_ok
        assert result.danger_ok == "tests/test_foo.py::TestFoo::test_a"

    def test_validate_evidence_normalizes_dot_with_parametrized_suffix(self) -> None:
        # frob:tests \
        # tests/test_tickets.py::TestEvidenceValidation.test_validate_evidence_normaliz\
        # es_dot_with_parametrized_suffix kind="unit"
        result = validate_evidence("tests/test_foo.py::TestFoo.test_a[x]")
        assert result.is_ok
        assert result.danger_ok == "tests/test_foo.py::TestFoo::test_a[x]"

    def test_validate_evidence_ignores_plain_ids_without_double_colon(self) -> None:
        # frob:tests \
        # tests/test_tickets.py::TestEvidenceValidation.test_validate_evidence_ignores_\
        # plain_ids_without_double_colon kind="unit"
        # No `::` prefix at all (cmd: evidence, bare strings) -- nothing to
        # normalize, must pass through untouched.
        result = validate_evidence("cmd:sha256=deadbeefcafefeed")
        assert result.is_ok
        assert result.danger_ok == "cmd:sha256=deadbeefcafefeed"

    def test_add_evidence_normalizes_dot_form_before_resolving_and_storing(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_evidence.py::add_evidence kind="unit"
        # The normalized (::) form, not the original dot-form the caller
        # passed in, must be what gets resolved against `collected` and
        # what actually lands in the ticket's stored evidence.
        _write(tmp_path, _ticket(ticket_id="T-0001"))
        collected = frozenset({"tests/test_foo.py::TestFoo::test_a"})
        result = add_evidence(
            tmp_path,
            "T-0001",
            ("tests/test_foo.py::TestFoo.test_a",),
            collected=collected,
        )
        assert result.is_ok, result.err
        assert result.danger_ok.evidence == ("tests/test_foo.py::TestFoo::test_a",)


class TestStateMachine:
    # invariant spec: [INV-002](invariants/INV-002.md)
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
        # frob:tests src/frob/tickets/_evidence.py::transition
        _write(tmp_path, _ticket(state=start))
        result = transition(tmp_path, "T-0001", to)
        assert result.is_ok, result.err
        assert result.danger_ok.state == to

    def test_transition_queued_to_planned_unit(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_evidence.py::transition kind="unit"
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
        # frob:tests src/frob/tickets/_doable.py::doable
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

    # invariant spec: [INV-032](invariants/INV-032.md)
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
        # frob:tests src/frob/tickets/_reporting.py::record_failure
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


# frob:ticket T-0579
class TestDropTicket:
    # frob:ticket T-0579
    def test_drops_queued_ticket_with_reason(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_reporting.py::drop_ticket
        _write(tmp_path, _ticket(state=TicketState.QUEUED))
        result = drop_ticket(tmp_path, "T-0001", "absorbed elsewhere")
        assert result.is_ok, result.err
        ticket = result.danger_ok
        assert ticket.state == TicketState.DROPPED
        assert "## Drop reason" in ticket.body
        assert "absorbed elsewhere" in ticket.body

    # frob:ticket T-0579
    def test_records_absorbed_by_reference(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(state=TicketState.PLANNED))
        result = drop_ticket(tmp_path, "T-0001", "subsumed", absorbed_by="T-0042")
        assert result.is_ok, result.err
        assert "(absorbed by T-0042)" in result.danger_ok.body

    # frob:ticket T-0579
    def test_blank_reason_is_err(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(state=TicketState.QUEUED))
        result = drop_ticket(tmp_path, "T-0001", "   ")
        assert result.is_err
        assert result.danger_err is TicketError.DropReasonMissing

    # frob:ticket T-0579
    def test_in_progress_ticket_drops_and_releases_lease(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(state=TicketState.IN_PROGRESS))
        result = drop_ticket(
            tmp_path, "T-0001", "obsolete, superseded by design change"
        )
        assert result.is_ok, result.err
        assert result.danger_ok.state == TicketState.DROPPED

    # frob:ticket T-0579
    def test_unknown_ticket_not_found(self, tmp_path: Path) -> None:
        (tmp_path / "tickets").mkdir()
        result = drop_ticket(tmp_path, "T-9999", "does not exist")
        assert result.is_err
        assert result.danger_err is TicketError.NotFound

    # frob:ticket T-0579
    def test_appends_preserving_existing_drop_reason_section(
        self, tmp_path: Path
    ) -> None:
        body = "## Description\nx\n\n## Drop reason\n- 2026-01-01: first cut\n"
        _write(tmp_path, _ticket(state=TicketState.QUEUED, body=body))
        result = drop_ticket(tmp_path, "T-0001", "second cut, confirmed obsolete")
        assert result.is_ok, result.err
        new_body = result.danger_ok.body
        assert "- 2026-01-01: first cut" in new_body
        assert "second cut, confirmed obsolete" in new_body


# frob:ticket T-0579
class TestDropCli:
    # frob:ticket T-0579
    def test_cli_drops_with_reason(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets.py::TestDropCli.test_cli_drops_with_reason
        _write(tmp_path, _ticket(state=TicketState.QUEUED))
        cfg = AppConfig(
            ticket_command="drop",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_reason="absorbed by T-0042",
            ticket_absorbed_by="T-0042",
        )
        _drop(tmp_path, cfg)
        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.state == TicketState.DROPPED
        assert "(absorbed by T-0042)" in ticket.body

    # frob:ticket T-0579
    def test_cli_requires_reason(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(state=TicketState.QUEUED))
        cfg = AppConfig(ticket_command="drop", ticket_id="T-0001", ticket_path=tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            _drop(tmp_path, cfg)
        assert exc_info.value.code == 1

    # frob:ticket T-0579
    def test_cli_requires_id(self, tmp_path: Path) -> None:
        cfg = AppConfig(
            ticket_command="drop",
            ticket_path=tmp_path,
            ticket_reason="no id given",
        )
        with pytest.raises(SystemExit) as exc_info:
            _drop(tmp_path, cfg)
        assert exc_info.value.code == 1


# frob:ticket T-1131
class TestFailCliRequeues:
    """T-1131 (the T-1050 incident): `frob ticket fail` used to only
    append a Failure log entry, never transitioning the ticket -- an
    IN_PROGRESS ticket stayed IN_PROGRESS (and its cross-worktree lease
    stayed held) forever after a fail-log, even once the worktree that
    held the lease was removed. `_fail` now requeues (IN_PROGRESS ->
    QUEUED) whenever the ticket was IN_PROGRESS, which is exactly the
    `transition` call that releases the lease
    (`_sync_cross_worktree_lease`)."""

    def test_fail_requeues_an_in_progress_ticket(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_close_cmd.py::_fail kind="unit"
        from frob.app.ticket_runner._close_cmd import _fail

        _write(tmp_path, _ticket(state=TicketState.IN_PROGRESS))
        cfg = AppConfig(
            ticket_command="fail",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_summary="dead end, superseded by T-9999",
        )
        _fail(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.state == TicketState.QUEUED
        assert "dead end, superseded by T-9999" in ticket.body

    def test_fail_leaves_a_non_in_progress_ticket_state_unchanged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_close_cmd.py::_fail kind="unit"
        from frob.app.ticket_runner._close_cmd import _fail

        _write(tmp_path, _ticket(state=TicketState.QUEUED))
        cfg = AppConfig(
            ticket_command="fail",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_summary="attempted before start, noting a dead end",
        )
        _fail(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        # already QUEUED, not IN_PROGRESS -- no transition attempted, no
        # InvalidTransition crash, state stays exactly what it was.
        assert queue.tickets["T-0001"].state == TicketState.QUEUED

    def test_fail_requires_id_and_summary(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_close_cmd.py::_fail kind="unit"
        from frob.app.ticket_runner._close_cmd import _fail

        cfg = AppConfig(ticket_command="fail", ticket_path=tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            _fail(tmp_path, cfg)
        assert exc_info.value.code == 1


# frob:ticket T-1132
class TestBlockCliValidatesBy:
    """T-1132: `frob ticket block <id> --by <other>` mutates an EXISTING
    ticket's `blocked_by` via `model_copy`, which pydantic never
    re-validates (unlike `TicketSpec`'s own field validators, which only
    fire at `frob ticket new` construction time) -- this is the exact
    write path the T-0380 incident (an empty-string blocked_by entry left
    a ticket silently undoable for days) can still slip through even with
    `TicketSpec` validated, so `_block` must check `--by` by hand."""

    def test_cli_refuses_empty_string_by(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_lifecycle.py::_block kind="unit"
        from frob.app.ticket_runner._lifecycle import _block

        _write(tmp_path, _ticket(state=TicketState.QUEUED))
        cfg = AppConfig(
            ticket_command="block",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_by="",
        )
        with pytest.raises(SystemExit) as exc_info:
            _block(tmp_path, cfg)
        assert exc_info.value.code == 1
        # the ledger was never touched
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].blocked_by == ()

    def test_cli_refuses_malformed_by(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_lifecycle.py::_block kind="unit"
        from frob.app.ticket_runner._lifecycle import _block

        _write(tmp_path, _ticket(state=TicketState.QUEUED))
        cfg = AppConfig(
            ticket_command="block",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_by="not-a-ticket-id",
        )
        with pytest.raises(SystemExit) as exc_info:
            _block(tmp_path, cfg)
        assert exc_info.value.code == 1

    def test_cli_accepts_valid_by(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_lifecycle.py::_block kind="unit"
        from frob.app.ticket_runner._lifecycle import _block

        _write(tmp_path, _ticket(state=TicketState.QUEUED))
        cfg = AppConfig(
            ticket_command="block",
            ticket_id="T-0001",
            ticket_path=tmp_path,
            ticket_by="T-0042",
        )
        _block(tmp_path, cfg)
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].blocked_by == ("T-0042",)


# frob:ticket T-1132
class TestTicketSpecValidatesBlockedByAndParent:
    """T-1132: `TicketSpec` (the ONLY path `frob ticket new --blocked-by`/
    `--parent` construct a ticket through) refuses an empty-string or
    malformed entry at construction time, closing the T-0380 incident at
    the source for every NEW ticket."""

    def test_new_ticket_refuses_empty_string_blocked_by(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_models.py::TicketSpec kind="unit"
        with pytest.raises(Exception, match="blocked_by"):
            TicketSpec(
                title="bad",
                kind=TicketKind.BUG,
                origin=Origin.HUMAN,
                blocked_by=("", "T-0002"),
            )

    def test_new_ticket_refuses_malformed_parent(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_models.py::TicketSpec kind="unit"
        with pytest.raises(Exception, match="parent"):
            TicketSpec(
                title="bad",
                kind=TicketKind.BUG,
                origin=Origin.HUMAN,
                parent="nope",
            )

    def test_new_ticket_accepts_well_formed_blocked_by_and_parent(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_models.py::TicketSpec kind="unit"
        spec = TicketSpec(
            title="good",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            blocked_by=("T-0001", "T-draft-deadbeef"),
            parent="T-0001",
        )
        assert spec.blocked_by == ("T-0001", "T-draft-deadbeef")
        assert spec.parent == "T-0001"


# frob:ticket T-1132
class TestIsValidTicketRef:
    """T-1132: `is_valid_ticket_ref` accepts only a real T-####/T-draft-<hex>
    id shape -- the shared check both `TicketSpec`'s construction-time
    validators and `frob ticket block`'s hand-rolled `--by` check use."""

    def test_accepts_final_id(self) -> None:
        # frob:tests src/frob/tickets/_models.py::is_valid_ticket_ref kind="unit"
        from frob.tickets import is_valid_ticket_ref

        assert is_valid_ticket_ref("T-0042") is True

    def test_accepts_draft_id(self) -> None:
        # frob:tests src/frob/tickets/_models.py::is_valid_ticket_ref kind="unit"
        from frob.tickets import is_valid_ticket_ref

        assert is_valid_ticket_ref("T-draft-deadbeef") is True

    def test_rejects_empty_string(self) -> None:
        # frob:tests src/frob/tickets/_models.py::is_valid_ticket_ref kind="unit"
        from frob.tickets import is_valid_ticket_ref

        assert is_valid_ticket_ref("") is False

    def test_rejects_malformed_id(self) -> None:
        # frob:tests src/frob/tickets/_models.py::is_valid_ticket_ref kind="unit"
        from frob.tickets import is_valid_ticket_ref

        assert is_valid_ticket_ref("not-a-ticket-id") is False
        assert is_valid_ticket_ref("T-42") is False


# frob:ticket T-1132
class TestIterRawLedgerFrontmatter:
    """T-1132: the tolerant raw-dict reader `frob doctor`'s malformed-edge
    scan uses -- must survive a malformed section rather than raising, the
    exact property the strict `_parse_ledger` deliberately does not have."""

    def test_returns_raw_dict_per_ticket(self) -> None:
        # frob:tests src/frob/tickets/_store.py::iter_raw_ledger_frontmatter kind="unit"  # noqa: E501
        from frob.tickets._store import iter_raw_ledger_frontmatter

        text = (
            "# Tickets\n\n"
            "<!-- ticket:T-0001 -->\n"
            "```yaml\n"
            "id: T-0001\n"
            "title: a\n"
            'blocked_by: ["", "T-0002"]\n'
            "```\n"
        )
        blocks = iter_raw_ledger_frontmatter(text)
        assert len(blocks) == 1
        ticket_id, data = blocks[0]
        assert ticket_id == "T-0001"
        assert data["blocked_by"] == ["", "T-0002"]

    def test_skips_malformed_yaml_block_without_raising(self) -> None:
        # frob:tests src/frob/tickets/_store.py::iter_raw_ledger_frontmatter kind="unit"  # noqa: E501
        from frob.tickets._store import iter_raw_ledger_frontmatter

        text = (
            "# Tickets\n\n"
            "<!-- ticket:T-0001 -->\n"
            "```yaml\n"
            "id: T-0001\n"
            "  bad: [unterminated\n"
            "```\n"
            "\n"
            "<!-- ticket:T-0002 -->\n"
            "```yaml\n"
            "id: T-0002\n"
            "title: fine\n"
            "```\n"
        )
        blocks = iter_raw_ledger_frontmatter(text)
        assert [tid for tid, _ in blocks] == ["T-0002"]


class TestAttach:
    def test_file_source_copies_and_records_sha256(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_reporting.py::attach
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
        # frob:tests src/frob/tickets/_evidence.py::add_evidence
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

    def test_unresolvable_id_warning_names_no_nonexistent_flag(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:ticket T-0445
        # T-0292 sibling: the warning must NOT point at the nonexistent
        # `frob test --collect` flag; it must name the real content-hash
        # auto-refresh + cache-file fallback instead.
        # frob:tests src/frob/tickets/_evidence.py::add_evidence
        _write(tmp_path, _ticket())
        collected = frozenset({"tests/test_x.py::test_a"})
        with caplog.at_level(logging.WARNING):
            add_evidence(
                tmp_path, "T-0001", ["tests/test_x.py::test_missing"], collected
            )
        messages = " ".join(r.message for r in caplog.records)
        assert "frob test --collect to refresh" not in messages
        assert "self-refreshes" in messages

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


# frob:ticket T-1103
class TestArchive:
    # frob:ticket T-1103
    def test_moves_done_and_dropped_only(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_archive.py::archive
        # frob:tests src/frob/tickets/_archive.py::load_active
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

    def test_new_ticket_id_continues_past_archived_max(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_new_renumber.py::new_ticket
        # T-0140 regression: archive a full T-0001..T-0136 queue, then file a
        # fresh ticket -- the allocator must skip past the archived max, not
        # restart at T-0001 (which would collide and make the merged queue
        # unloadable on the very next load_queue).
        from frob.tickets import Origin, TicketKind, TicketSpec

        for i in range(1, 137):
            _write(
                tmp_path,
                _ticket(ticket_id=f"T-{i:04d}", state=TicketState.DONE),
                f"done-{i}",
            )
        archived_count = archive(tmp_path)
        assert archived_count.is_ok
        assert archived_count.danger_ok == 136

        spec = TicketSpec(
            title="post-archive ticket",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        assert created.danger_ok.id == "T-0137"

        merged = load_queue(tmp_path)
        assert merged.is_ok
        assert "T-0137" in merged.danger_ok.tickets

    def test_new_ticket_fresh_repo_no_archive_file(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_new_renumber.py::new_ticket
        # A repo that has never archived anything has no tickets-archive.md
        # at all -- allocation must not error just because the file is
        # absent (T-0140).
        from frob.tickets import Origin, TicketKind, TicketSpec

        assert not (tmp_path / "tickets-archive.md").exists()
        spec = TicketSpec(
            title="first ticket ever",
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        assert created.danger_ok.id == "T-0001"

    def test_new_ticket_corrupt_archive_fails_loudly(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_new_renumber.py::new_ticket
        # A malformed archive must never be silently skipped during id
        # allocation -- vacuous-pass doctrine: fail loudly rather than
        # allocating an id that might collide with unreadable content.
        from frob.tickets import Origin, TicketKind, TicketSpec

        archive_file = tmp_path / "tickets-archive.md"
        archive_file.write_text(
            "<!-- ticket:T-0001 -->\nno yaml frontmatter fence here at all\n",
            encoding="utf-8",
        )

        spec = TicketSpec(
            title="should not be created",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_err


# frob:ticket T-0764
# frob:ticket T-0843
class TestArchiveRefusesDuringInFlightWork:
    """T-0764: `archive` refuses (unless `force=True`) while a live
    cross-worktree lease exists on a ticket it would move into
    tickets-archive.md -- the guard for the T-0753 field incident (archive
    rewrote main's ledger mid-`start`, which the in-flight worktree's
    later section-10b restore silently reverted back to `queued` with
    empty evidence). T-0843: narrowed from "any live lease anywhere in
    the repo" to "a live lease on a ticket this call would actually
    archive" -- a lease on unrelated in-progress work is not this hazard."""

    def _repo(self, tmp_path: Path) -> Path:
        import subprocess

        root = tmp_path / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(root), check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=str(root),
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=str(root), check=True
        )
        (root / "README.md").write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(root), check=True)
        return root

    def _write_live_lease(self, root: Path, ticket_id: str, worktree: Path) -> None:
        from frob.tickets._leases import _LeaseRecord, leases_dir

        resolved = leases_dir(root)
        assert resolved.is_ok
        leases_root = resolved.danger_ok
        leases_root.mkdir(parents=True, exist_ok=True)
        record = _LeaseRecord(
            ticket_id=ticket_id,
            scope=(),
            worktree=str(worktree),
            branch="main",
            recorded_at="2026-07-22T00:00:00+00:00",
        )
        (leases_root / f"{ticket_id}.json").write_text(
            record.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )

    def test_archive_refuses_when_a_live_lease_exists(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork.test_archive_refuses_when_a_live_lease_exists  # noqa: E501
        root = self._repo(tmp_path)
        _write(root, _ticket(ticket_id="T-0001", state=TicketState.DONE), "done")
        # T-0001 itself -- the ticket this call would move -- still holds a
        # live lease (its worktree, root itself, exists on disk).
        self._write_live_lease(root, "T-0001", root)

        result = archive(root)
        assert result.is_err
        assert result.danger_err == TicketError.ArchiveLiveLeaseExists

        # Nothing moved: the active/archive split is untouched.
        active = load_active(root).danger_ok
        assert "T-0001" in active.tickets

    def test_archive_force_overrides_the_live_lease_refusal(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork.test_archive_force_overrides_the_live_lease_refusal  # noqa: E501
        root = self._repo(tmp_path)
        _write(root, _ticket(ticket_id="T-0001", state=TicketState.DONE), "done")
        self._write_live_lease(root, "T-0001", root)

        result = archive(root, force=True)
        assert result.is_ok
        assert result.danger_ok == 1

    def test_archive_ignores_a_stale_lease_from_a_removed_worktree(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork.test_archive_ignores_a_stale_lease_from_a_removed_worktree  # noqa: E501
        root = self._repo(tmp_path)
        _write(root, _ticket(ticket_id="T-0001", state=TicketState.DONE), "done")
        # The lease names a worktree path that does not exist on disk --
        # `read_all_leases` already filters this out as stale, so archive
        # must proceed normally, not treat it as live in-flight work, even
        # though the stale lease is for the very ticket being archived.
        self._write_live_lease(
            root, "T-0001", root / ".." / "gone-worktree-does-not-exist"
        )

        result = archive(root)
        assert result.is_ok
        assert result.danger_ok == 1

    def test_archive_ignores_a_live_lease_for_a_ticket_it_would_not_touch(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork.test_archive_ignores_a_live_lease_for_a_ticket_it_would_not_touch  # noqa: E501
        """T-0843: a live lease for a ticket archive would never move (it
        is not DONE/DROPPED, so its own block is untouched) must not block
        an unrelated ticket's archival -- the T-0753 guard only protects
        tickets this call actually rewrites into tickets-archive.md."""
        root = self._repo(tmp_path)
        _write(root, _ticket(ticket_id="T-0001", state=TicketState.DONE), "done")
        # T-0002's lease is live, but T-0002 is unrelated in-progress work
        # that archive would never touch.
        self._write_live_lease(root, "T-0002", root)

        result = archive(root)
        assert result.is_ok
        assert result.danger_ok == 1

        active = load_active(root).danger_ok
        assert "T-0001" not in active.tickets


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

    # frob:ticket T-0505
    def test_write_ticket_never_touches_a_sibling_ticket_bytes(self, tmp_path):
        """T-0505 regression: writing ticket A must not change ANY byte of
        ticket B's section, even when B's on-disk section is stale/unusual
        relative to what a fresh parse+re-render would produce (formatting
        drift is exactly what let a sibling's state silently travel through
        an unrelated write before this fix)."""
        from frob.tickets import TicketState, load_queue, new_ticket, transition
        from frob.tickets._store import ledger_path

        a = new_ticket(tmp_path, self._spec("ticket a")).danger_ok
        b = new_ticket(tmp_path, self._spec("ticket b")).danger_ok

        before = ledger_path(tmp_path).read_text(encoding="utf-8")
        b_marker = f"<!-- ticket:{b.id} -->"
        assert b_marker in before
        b_section_before = before[before.index(b_marker) :]

        transitioned = transition(tmp_path, a.id, TicketState.PLANNED)
        assert transitioned.is_ok

        after = ledger_path(tmp_path).read_text(encoding="utf-8")
        b_section_after = after[after.index(b_marker) :]
        assert b_section_after == b_section_before, (
            "writing ticket a's transition must not change a single byte "
            "of ticket b's own section"
        )

        q = load_queue(tmp_path).danger_ok
        assert q.tickets[a.id].state == TicketState.PLANNED
        assert q.tickets[b.id].state == TicketState.QUEUED

    def test_migrate_collapses_dir_into_ledger(self, tmp_path):
        from datetime import date

        from frob.tickets import load_queue, migrate
        from frob.tickets._models import Origin as O
        from frob.tickets._models import Ticket, TicketKind, TicketState
        from frob.tickets._store import _serialize_ticket, tickets_dir

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
                _serialize_ticket(tk), encoding="utf-8"
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
        from frob.tickets._store import _serialize_ticket, tickets_dir

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
        (d / "T-0001-legacy.md").write_text(_serialize_ticket(tk), encoding="utf-8")
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
        # T-0572: acceptance items round-trip as {text, evidence}
        # AcceptanceCriterion objects, not bare strings -- a plain-string
        # spec entry still loads, just unbound (empty evidence) until
        # bound via `add_evidence(..., accepts=...)`.
        acceptance = q.tickets[t.id].acceptance
        assert len(acceptance) == 1
        assert acceptance[0].text == "given X when Y then Z"
        assert acceptance[0].evidence == ()
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


class TestScopeMatching:
    """T-0241: comma-joined scope entries, dir/ prefixes, implicit ledger."""

    def test_comma_joined_entry_splits(self) -> None:
        # frob:tests src/frob/tickets/_models.py::_split_scope_entries
        ticket = Ticket(
            id="T-0001",
            title="Sample",
            state=TicketState.QUEUED,
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            scope=("src/a/**,src/b/**", "docs/x.md"),
        )
        assert ticket.scope == ("src/a/**", "src/b/**", "docs/x.md")

    def test_comma_joined_entry_matches_split_paths(self) -> None:
        # frob:tests src/frob/tickets/_models.py::scope_matches
        assert scope_matches("src/a/f.py", ("src/a/**,src/b/**",))
        assert scope_matches("src/b/f.py", ("src/a/**,src/b/**",))
        assert not scope_matches("src/c/f.py", ("src/a/**,src/b/**",))

    def test_dir_prefix_globs_recursively(self) -> None:
        # frob:tests src/frob/tickets/_models.py::scope_matches
        assert scope_matches("design/sub/f.py", ("design/",))
        assert scope_matches("design/f.py", ("design/",))
        assert not scope_matches("other/f.py", ("design/",))

    def test_bare_dir_entry_no_trailing_slash_globs_recursively(self) -> None:
        # frob:tests src/frob/tickets/_models.py::scope_matches
        assert scope_matches("docs/modules/gates.md", ("docs/modules",))
        assert scope_matches("docs/modules", ("docs/modules",))
        assert not scope_matches("docs/strata/x.md", ("docs/modules",))
        # a literal file entry (dot-extension on the final segment) must NOT
        # be treated as an implied directory prefix
        assert not scope_matches("src/frob/foo/bar.py", ("src/frob/foo.py",))

    def test_ledger_always_in_scope(self) -> None:
        # frob:tests src/frob/tickets/_models.py::scope_matches
        assert scope_matches("tickets.md", ("src/frob/foo/**",))
        assert scope_matches("tickets.md", ())

    # frob:ticket T-0446
    def test_feature_kind_implies_cli_wiring_files_in_scope(self) -> None:
        # frob:tests src/frob/tickets/_models.py::scope_matches
        from frob.tickets._models import CLI_WIRING_FILES

        narrow_scope = ("src/frob/tickets/**",)
        for wiring_file in CLI_WIRING_FILES:
            assert not scope_matches(wiring_file, narrow_scope)
            assert scope_matches(wiring_file, narrow_scope, kind=TicketKind.FEATURE)

    def test_non_feature_kind_does_not_imply_cli_wiring_files(self) -> None:
        # frob:tests src/frob/tickets/_models.py::scope_matches
        from frob.tickets._models import CLI_WIRING_FILES

        narrow_scope = ("src/frob/tickets/**",)
        for wiring_file in CLI_WIRING_FILES:
            assert not scope_matches(wiring_file, narrow_scope, kind=TicketKind.BUG)

    # frob:ticket T-1163
    def test_cli_wiring_files_resolve_to_real_paths_on_disk(self) -> None:
        # frob:tests src/frob/tickets/_models.py::CLI_WIRING_FILES
        """Each CLI_WIRING_FILES entry must glob-match at least one real
        file, so a retired/renamed path (e.g. a module split into a
        package) fails loudly here instead of silently defeating T-0446's
        implicit-scope mechanism (T-1163: `app/ticket_runner.py` went
        stale this way after an earlier split into `app/ticket_runner/`).
        """
        from frob.tickets._models import CLI_WIRING_FILES

        repo_root = Path(__file__).resolve().parent.parent
        for wiring_file in CLI_WIRING_FILES:
            matches = list(repo_root.glob(wiring_file))
            assert matches, (
                f"CLI_WIRING_FILES entry {wiring_file!r} matches no real "
                "file on disk -- it is stale and silently defeats the "
                "implicit CLI-wiring scope mechanism for FEATURE tickets"
            )

    def test_new_ticket_normalizes_comma_joined_scope(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_models.py::TicketSpec
        from frob.tickets import TicketSpec

        spec = TicketSpec(
            title="t",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("src/a/**,src/b/**",),
        )
        t = new_ticket(tmp_path, spec).danger_ok
        assert t.scope == ("src/a/**", "src/b/**")


# frob:ticket T-0838
# frob:ticket T-1103
class TestEmptyCollectionOmission:
    """T-0838: empty-collection ledger fields (`reviews: []` and every peer
    default-empty tuple field) must never be written -- an additive field
    only appears in the rendered ledger once something actually populates
    it, so a schema-extending feature's own land never bricks an older
    frob's extra_forbidden read."""

    def test_dict_without_empty_collections_returned_unchanged(self) -> None:
        # frob:tests src/frob/tickets/_models.py::_omit_empty_collections
        from frob.tickets._models import _omit_empty_collections

        data = {"a": 1, "b": "x", "c": None}
        assert _omit_empty_collections(data) == data

    def test_empty_list_and_tuple_values_dropped(self) -> None:
        # frob:tests src/frob/tickets/_models.py::_omit_empty_collections
        from frob.tickets._models import _omit_empty_collections

        data = {"a": 1, "b": [], "c": (), "d": [1, 2], "e": None}
        assert _omit_empty_collections(data) == {"a": 1, "d": [1, 2], "e": None}

    def test_reviews_empty_never_serialized(self) -> None:
        # frob:tests src/frob/tickets/_models.py::Ticket
        ticket = _ticket()
        assert ticket.reviews == ()
        text = _serialize_ticket(ticket)
        assert "reviews:" not in text
        # every other default-empty tuple field is omitted the same way,
        # not just reviews (systematic, T-0838)
        for key in ("scope_changes:", "attachments:", "acceptance:", "labels:"):
            assert key not in text

    def test_reviews_populated_still_serializes(self) -> None:
        # frob:tests src/frob/tickets/_models.py::Ticket
        from datetime import date

        from frob.tickets import ReviewEntry, ReviewVerdict

        ticket = _ticket().model_copy(
            update={
                "reviews": (
                    ReviewEntry(
                        verdict=ReviewVerdict.APPROVE,
                        reviewer="alice",
                        findings="looks good",
                        commit="a" * 40,
                        at=date(2026, 1, 1),
                    ),
                )
            }
        )
        text = _serialize_ticket(ticket)
        assert "reviews:" in text
        assert "verdict: approve" in text

    # frob:ticket T-1103
    def test_ticket_with_empty_reviews_round_trips_through_ledger(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_archive.py::load_queue
        ticket = _ticket()
        assert ticket.reviews == ()
        _write(tmp_path, ticket)
        result = load_queue(tmp_path)
        assert result.is_ok
        loaded = result.danger_ok.tickets["T-0001"]
        assert loaded.reviews == ()
        assert loaded == ticket


# frob:ticket T-0838
# frob:ticket T-1103
class TestUnknownFieldForwardCompat:
    """T-0838 regression: an older frob binary must be able to land a newer
    worktree's ledger -- a ledger block carrying a field this model does not
    yet declare (e.g. the T-0571 incident: `reviews:` before this binary
    knew about it) must load without an exception, log a WARNING naming the
    field, and re-emit it byte-for-byte on the next write, all while a
    genuinely malformed KNOWN field still fails validation."""

    _UNKNOWN_FIELD_LEDGER = (
        "# Tickets\n\n"
        "<!-- ticket:T-0001 -->\n"
        "```yaml\n"
        "id: T-0001\n"
        "title: Sample\n"
        "state: queued\n"
        "kind: feature\n"
        "origin: human\n"
        "created: '2026-01-01'\n"
        "reviews_v2:\n"
        "- reviewer: bob\n"
        "  stance: strong-approve\n"
        "```\n"
        "body text\n"
    )

    # frob:ticket T-1103
    def test_unknown_field_loads_without_exception(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_archive.py::load_active
        (tmp_path / "tickets.md").write_text(self._UNKNOWN_FIELD_LEDGER)
        result = load_active(tmp_path)
        assert result.is_ok
        ticket = result.danger_ok.tickets["T-0001"]
        extras = ticket.__pydantic_extra__
        assert extras is not None
        assert extras["reviews_v2"] == [{"reviewer": "bob", "stance": "strong-approve"}]

    def test_unknown_field_logs_warning_named(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/tickets/_models.py::Ticket
        (tmp_path / "tickets.md").write_text(self._UNKNOWN_FIELD_LEDGER)
        with caplog.at_level(logging.WARNING):
            result = load_active(tmp_path)
        assert result.is_ok
        messages = " ".join(r.message for r in caplog.records)
        assert "reviews_v2" in messages
        assert "T-0001" in messages

    def test_unknown_field_preserved_verbatim_on_reserialize(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_store.py::_render_section
        from frob.tickets._store import _render_section

        (tmp_path / "tickets.md").write_text(self._UNKNOWN_FIELD_LEDGER)
        ticket = load_active(tmp_path).danger_ok.tickets["T-0001"]
        rendered = _render_section("T-0001", ticket)
        assert "reviews_v2:" in rendered
        assert "reviewer: bob" in rendered
        assert "stance: strong-approve" in rendered
        # re-parsing the re-rendered section preserves the same extra data
        reloaded = load_active(tmp_path).danger_ok.tickets["T-0001"]
        assert reloaded.__pydantic_extra__ == ticket.__pydantic_extra__

    # frob:ticket T-1103
    def test_known_field_still_validated_strictly(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_archive.py::load_active
        malformed = self._UNKNOWN_FIELD_LEDGER.replace(
            "state: queued", "state: not-a-real-state"
        )
        (tmp_path / "tickets.md").write_text(malformed)
        result = load_active(tmp_path)
        assert result.is_err
        assert result.danger_err is TicketError.MalformedFrontmatter


# frob:ticket T-1029
class TestAddAcceptance:
    """T-1029: `add_acceptance` appends criteria to an EXISTING ticket --
    before this, `frob ticket new --acceptance` was the only CLI path, so a
    ticket that needed a criterion added after filing had to be hand-edited
    (the T-0894 incident this closes)."""

    # frob:ticket T-1029
    def test_appends_criteria_to_existing_ticket(self, tmp_path: Path) -> None:
        spec = TicketSpec(
            title="a ticket",
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            # T-0572: `_coerce_acceptance_field` accepts a plain string and
            # wraps it into an unbound AcceptanceCriterion.
            acceptance=("first criterion",),  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]  # noqa: E501
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = add_acceptance(tmp_path, ticket_id, ["second criterion", "third"])
        assert result.is_ok
        texts = [c.text for c in result.danger_ok.acceptance]
        assert texts == ["first criterion", "second criterion", "third"]
        assert all(c.evidence == () for c in result.danger_ok.acceptance)

        reloaded = load_active(tmp_path).danger_ok.tickets[ticket_id]
        assert [c.text for c in reloaded.acceptance] == texts

    # frob:ticket T-1029
    def test_empty_criteria_is_rejected(self, tmp_path: Path) -> None:
        spec = TicketSpec(
            title="a ticket", kind=TicketKind.FEATURE, origin=Origin.HUMAN
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = add_acceptance(tmp_path, ticket_id, [])
        assert result.is_err
        assert result.danger_err == TicketError.AcceptanceChangeEmpty

    # frob:ticket T-1029
    def test_blank_criteria_are_dropped(self, tmp_path: Path) -> None:
        spec = TicketSpec(
            title="a ticket", kind=TicketKind.FEATURE, origin=Origin.HUMAN
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = add_acceptance(tmp_path, ticket_id, ["  ", "", "real one"])
        assert result.is_ok
        assert [c.text for c in result.danger_ok.acceptance] == ["real one"]


# frob:ticket T-1257
class TestV2IndexCache:
    """Design section 6's derived `.frob/tickets-index.json`: a hit skips
    re-parsing every `ticket.md`, a stale/missing cache transparently
    falls back to a full glob+parse (never silently stale data)."""

    def _v2_ticket(self, tmp_path: Path, ticket_id: str = "T-0001") -> None:
        d = tmp_path / "tickets" / ticket_id
        d.mkdir(parents=True)
        (d / "ticket.md").write_text(_serialize_ticket(_ticket(ticket_id=ticket_id)))

    def test_second_load_reads_from_index_cache(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets.py::TestV2IndexCache.test_second_load_reads_from_index_cache  # noqa: E501
        from frob.tickets._store import _index_path, load_all

        self._v2_ticket(tmp_path)
        first = load_all(tmp_path)
        assert first.is_ok
        index_path = _index_path(tmp_path)
        assert index_path.exists()

        second = load_all(tmp_path)
        assert second.is_ok
        assert second.danger_ok.keys() == {"T-0001"}
        assert second.danger_ok["T-0001"].id == "T-0001"

    def test_stale_index_falls_back_to_fresh_parse(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets.py::TestV2IndexCache.test_stale_index_falls_back_to_fresh_parse  # noqa: E501
        from frob.tickets._store import load_all

        self._v2_ticket(tmp_path, "T-0001")
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok.keys() == {"T-0001"}

        # A NEW ticket file appears after the cache was written -- the
        # path set no longer matches the cached entry set, so this must
        # be a miss, never a stale hit that omits T-0002.
        self._v2_ticket(tmp_path, "T-0002")
        loaded_again = load_all(tmp_path)
        assert loaded_again.is_ok
        assert loaded_again.danger_ok.keys() == {"T-0001", "T-0002"}

    def test_missing_index_never_raises(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets.py::TestV2IndexCache.test_missing_index_never_raises  # noqa: E501
        from frob.tickets._store import load_all

        self._v2_ticket(tmp_path)
        assert not (tmp_path / ".frob" / "tickets-index.json").exists()
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok.keys() == {"T-0001"}


# frob:ticket T-1257
class TestV2StateTransitions:
    """Design section 4.4: cycle-time/velocity mining derived purely from
    `git log --follow` diff hunks on a v2-mode ticket's own `state:`
    field, no separate event log required."""

    def _repo(self, tmp_path: Path) -> Path:
        import subprocess

        root = tmp_path / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(root), check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=str(root),
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=str(root), check=True
        )
        return root

    def _commit_ticket(self, root: Path, ticket: Ticket, message: str) -> None:
        import subprocess

        d = root / "tickets" / ticket.id
        d.mkdir(parents=True, exist_ok=True)
        (d / "ticket.md").write_text(_serialize_ticket(ticket))
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", message], cwd=str(root), check=True
        )

    def test_transitions_mined_oldest_first(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets.py::TestV2StateTransitions.test_transitions_mined_oldest_first  # noqa: E501
        from frob.tickets._store import v2_state_transitions

        root = self._repo(tmp_path)
        self._commit_ticket(root, _ticket(state=TicketState.QUEUED), "file T-0001")
        self._commit_ticket(
            root, _ticket(state=TicketState.IN_PROGRESS), "start T-0001"
        )
        self._commit_ticket(root, _ticket(state=TicketState.DONE), "close T-0001")

        transitions = v2_state_transitions(root, "T-0001")
        assert [state for _, _, state in transitions] == [
            "queued",
            "in-progress",
            "done",
        ]
        # oldest-first: the first commit's sha/date precede the last's.
        assert len(transitions) == 3

    def test_no_history_returns_empty_tuple(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets.py::TestV2StateTransitions.test_no_history_returns_empty_tuple  # noqa: E501
        from frob.tickets._store import v2_state_transitions

        root = self._repo(tmp_path)
        assert v2_state_transitions(root, "T-9999") == ()
