"""Direct unit tests for frob.tickets._store's backend-agnostic storage helpers."""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pytest

from frob.tickets import (
    TicketSpec,
    add_evidence,
    attach,
    closed_ticket_ids,
    new_ticket,
    replay_evidence_from_done_report,
    set_done_report,
    transition,
)
from frob.tickets._models import (
    AttachmentSource,
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketQueue,
    TicketState,
    replace_done_report_section,
)
from frob.tickets._store import (
    _lock_path,
    _parse_ticket_file,
    _serialize_ticket,
    _store_mode,
    archive_path,
    atomic_write,
    attachments_dir,
    ledger_lock,
    ledger_path,
    load_all,
    load_archive,
    migrate_to_ledger,
    read_done_report,
    sanitize_narrative_for_ledger,
    slugify,
    tickets_dir,
    v2_attachments_dir,
    v2_done_report_path,
    v2_ticket_dir,
    v2_ticket_path,
    write_all,
    write_archive,
    write_done_report,
    write_ticket,
)


def _ticket(ticket_id: str = "T-0001", title: str = "Sample ticket") -> Ticket:
    return Ticket(
        id=ticket_id,
        title=title,
        state=TicketState.QUEUED,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=(),
        evidence=(),
        attachments=(),
        body="## Description\nsomething\n",
    )


# T-1553: classes below that exercise the single-mode (v1 monofile)
# store path directly against a bare `tmp_path`; the fresh-repo default
# flipped to v2, so these pin v1 explicitly via the autouse fixture.
_V1_PINNED_CLASSES = frozenset(
    {
        "TestWriteTicket",
        "TestWriteTicketUnchecked",
        "TestArchiveLedger",
        "TestLoadArchiveCache",
        "TestSetDoneReport",
        "TestReplayEvidenceFromDoneReport",
    }
)


# frob:ticket T-1553
# frob:waive WIRE001 reason="autouse=True pytest fixture -- invoked implicitly by \
# pytest's own fixture-injection machinery on every test in this module, never by a \
# literal name() call WIRE001's text scan looks for; same detector-gap class as \
# T-1502/T-1527" follow_up="T-1534"
@pytest.fixture(autouse=True)
def _pin_v1_mode_on_bare_tmp_path(
    request: pytest.FixtureRequest, tmp_path: Path
) -> None:
    """T-1553: pin `tmp_path` to v1/'single' mode for the classes in
    `_V1_PINNED_CLASSES`, which exercise the monofile store path against
    a bare `tmp_path`; every other class either seeds its own mode
    explicitly (v2 dirs, legacy dir-mode) or asserts mode detection
    itself and must see the directory untouched."""
    cls = request.cls
    if cls is not None and cls.__name__ in _V1_PINNED_CLASSES:
        (tmp_path / "tickets.md").write_text("# Tickets\n", encoding="utf-8")


class TestSlugify:
    def test_lowercases_and_hyphenates(self) -> None:
        # frob:tests src/frob/tickets/_store.py::slugify kind="unit"
        assert slugify("Fix The Thing!") == "fix-the-thing"

    def test_strips_leading_trailing_hyphens(self) -> None:
        assert slugify("  !!weird title??  ") == "weird-title"

    def test_empty_title_is_untitled(self) -> None:
        assert slugify("   ") == "untitled"


class TestPathHelpers:
    def test_tickets_dir_is_repo_relative(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::tickets_dir kind="unit"
        assert tickets_dir(tmp_path) == tmp_path / "tickets"

    def test_ledger_path_is_tickets_md_at_root(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::ledger_path kind="unit"
        assert ledger_path(tmp_path) == tmp_path / "tickets.md"

    def test_attachments_dir_nests_under_ticket_id(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::attachments_dir kind="unit"
        assert attachments_dir(tmp_path, "T-0042") == (
            tmp_path / "tickets" / "attachments" / "T-0042"
        )


# frob:ticket T-1254
class TestV2DoneReport:
    def _v2_ticket(self, tmp_path: Path, ticket_id: str = "T-0001") -> None:
        d = tmp_path / "tickets" / ticket_id
        d.mkdir(parents=True)
        (d / "ticket.md").write_text(_serialize_ticket(_ticket(ticket_id)))

    def test_write_then_read_back_byte_for_byte(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestV2DoneReport.test_write_then_read_back_byte_for_byte  # noqa: E501
        self._v2_ticket(tmp_path)
        report = "## Done report\n\nimplemented the thing\n\n### Evidence\nnone\n"
        written = write_done_report(tmp_path, "T-0001", report)
        assert written.is_ok
        assert v2_done_report_path(tmp_path, "T-0001").exists()

        read_back = read_done_report(tmp_path, "T-0001")
        assert read_back == report

    def test_done_report_is_a_distinct_file_from_ticket_md(
        self, tmp_path: Path
    ) -> None:
        self._v2_ticket(tmp_path)
        write_done_report(tmp_path, "T-0001", "## Done report\n\nx\n")
        ticket_path = v2_ticket_path(tmp_path, "T-0001")
        report_path = v2_done_report_path(tmp_path, "T-0001")
        assert ticket_path != report_path
        assert "Done report" not in ticket_path.read_text(encoding="utf-8")

    def test_missing_report_is_none(self, tmp_path: Path) -> None:
        self._v2_ticket(tmp_path)
        assert read_done_report(tmp_path, "T-0001") is None


# frob:ticket T-1254
class TestV2Attachments:
    def test_attachment_written_under_ticket_dir(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestV2Attachments.test_attachment_written_under_ticket_dir  # noqa: E501
        d = tmp_path / "tickets" / "T-0001"
        d.mkdir(parents=True)
        (d / "ticket.md").write_text(_serialize_ticket(_ticket()))
        assert _store_mode(tmp_path) == "v2"

        src = tmp_path / "mockup.png"
        src.write_bytes(b"fake-png-bytes")
        result = attach(tmp_path, "T-0001", AttachmentSource(path=src), "mockup")
        assert result.is_ok
        attachment = result.danger_ok

        expected_dir = v2_attachments_dir(tmp_path, "T-0001")
        assert expected_dir.exists()
        written_files = list(expected_dir.iterdir())
        assert len(written_files) == 1
        assert written_files[0].read_bytes() == b"fake-png-bytes"

        # Attachment.path stays relative to tickets_dir(root) (COV004's own
        # convention, src/frob/gates/__init__.py) -- reconstructs to the
        # same v2 path via `Path("tickets") / attachment.path`.
        assert (tmp_path / "tickets" / attachment.path) == written_files[0]

        reloaded = load_all(tmp_path)
        assert reloaded.is_ok
        assert len(reloaded.danger_ok["T-0001"].attachments) == 1


class TestStoreMode:
    def test_fresh_repo_defaults_to_v2(self, tmp_path: Path) -> None:
        """T-1553 flipped the fresh-repo fallback: a directory with no
        store markers at all now defaults to v2."""
        # frob:tests src/frob/tickets/_store.py::_store_mode kind="unit"
        assert _store_mode(tmp_path) == "v2"

    def test_ledger_present_is_single(self, tmp_path: Path) -> None:
        (tmp_path / "tickets.md").write_text("# Tickets\n")
        assert _store_mode(tmp_path) == "single"

    def test_only_legacy_dir_files_is_dir(self, tmp_path: Path) -> None:
        d = tmp_path / "tickets"
        d.mkdir()
        (d / "T-0001-x.md").write_text(_serialize_ticket(_ticket()))
        assert _store_mode(tmp_path) == "dir"


# frob:ticket T-1254
class TestV2StoreMode:
    def test_v2_tree_present_is_v2(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::_store_mode kind="unit"
        ticket_dir = tmp_path / "tickets" / "T-0042"
        ticket_dir.mkdir(parents=True)
        (ticket_dir / "ticket.md").write_text(_serialize_ticket(_ticket("T-0042")))
        assert _store_mode(tmp_path) == "v2"

    def test_v2_takes_priority_over_stray_ledger(self, tmp_path: Path) -> None:
        (tmp_path / "tickets.md").write_text("# Tickets\n")
        ticket_dir = tmp_path / "tickets" / "T-0042"
        ticket_dir.mkdir(parents=True)
        (ticket_dir / "ticket.md").write_text(_serialize_ticket(_ticket("T-0042")))
        assert _store_mode(tmp_path) == "v2"

    def test_v2_takes_priority_over_stray_dir_mode_files(self, tmp_path: Path) -> None:
        d = tmp_path / "tickets"
        d.mkdir()
        (d / "T-0001-x.md").write_text(_serialize_ticket(_ticket()))
        ticket_dir = d / "T-0042"
        ticket_dir.mkdir()
        (ticket_dir / "ticket.md").write_text(_serialize_ticket(_ticket("T-0042")))
        assert _store_mode(tmp_path) == "v2"

    def test_flat_dir_file_does_not_look_like_v2(self, tmp_path: Path) -> None:
        """A legacy `tickets/T-0001-slug.md` FILE never matches the v2
        glob (`T-*/ticket.md`, which requires a subdirectory) -- the two
        modes structurally cannot collide."""
        d = tmp_path / "tickets"
        d.mkdir()
        (d / "T-0001-x.md").write_text(_serialize_ticket(_ticket()))
        assert _store_mode(tmp_path) == "dir"


class TestSerializeAndParse:
    def test_round_trip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::_serialize_ticket kind="unit"
        # frob:tests src/frob/tickets/_store.py::_parse_ticket_file kind="unit"
        ticket = _ticket()
        text = _serialize_ticket(ticket)
        path = tmp_path / "T-0001-sample-ticket.md"
        path.write_text(text, encoding="utf-8")

        result = _parse_ticket_file(path)
        assert result.is_ok
        assert result.danger_ok == ticket

    def test_malformed_file_is_err(self, tmp_path: Path) -> None:
        path = tmp_path / "T-0001-bad.md"
        path.write_text("not frontmatter at all\n")
        result = _parse_ticket_file(path)
        assert result.is_err
        assert result.danger_err == TicketError.MalformedFrontmatter


class TestLoadAllAndWriteTicket:
    def test_write_then_load_single_mode(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::write_ticket kind="unit"
        # frob:tests src/frob/tickets/_store.py::load_all kind="unit"
        ticket = _ticket()
        written = write_ticket(tmp_path, ticket)
        assert written.is_ok

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok.keys() == {"T-0001"}
        assert loaded.danger_ok["T-0001"].id == ticket.id
        assert loaded.danger_ok["T-0001"].title == ticket.title
        assert loaded.danger_ok["T-0001"].body.strip() == ticket.body.strip()

    def test_load_all_empty_repo_is_empty_dict(self, tmp_path: Path) -> None:
        result = load_all(tmp_path)
        assert result.is_ok
        assert result.danger_ok == {}

    def test_component_and_labels_round_trip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::write_ticket kind="unit"
        # frob:tests src/frob/tickets/_store.py::load_all kind="unit"
        # T-0454: schema-addition round-trip test, same precedent T-0411's
        # priority field established for a new Ticket field.
        ticket = _ticket().model_copy(
            update={"component": "tickets", "labels": ("board", "epic")}
        )
        written = write_ticket(tmp_path, ticket)
        assert written.is_ok

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].component == "tickets"
        assert loaded.danger_ok["T-0001"].labels == ("board", "epic")


# frob:ticket T-1536
class TestWriteTicket:
    """Post-splice integrity guard for `write_ticket`'s single-mode path
    (T-1536): a `ticket.body` that forges a fake ledger marker for a
    sibling id, or that would otherwise drop a sibling on re-parse, must
    refuse to persist rather than corrupt the shared ledger."""

    # frob:ticket T-1536
    def test_marker_lookalike_body_line_refuses_write(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestWriteTicket.test_marker_lookalike_body_line_refuses_write  # noqa: E501
        sibling = _ticket("T-0002")
        assert write_ticket(tmp_path, sibling).is_ok

        # T-1536 incident shape: a done-report narrative that happens to
        # quote another ticket's literal marker line verbatim (e.g. an
        # incident report describing a corrupted ledger span) forges a
        # fake section boundary for T-0002 the next time the file is
        # parsed -- this write must refuse rather than persist that.
        poisoned = _ticket().model_copy(
            update={
                "body": (
                    "## Description\nsomething\n\n"
                    "## Done report\n\n"
                    "quoting the incident verbatim:\n"
                    "<!-- ticket:T-0002 -->\n"
                    "not real frontmatter, just narrative prose\n"
                )
            }
        )
        result = write_ticket(tmp_path, poisoned)
        assert result.is_err
        assert result.danger_err == TicketError.LedgerIntegrityViolation

        # The ledger on disk must be unchanged -- T-0002 still loads clean.
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok.keys() == {"T-0002"}

    # frob:ticket T-1536
    def test_ordinary_body_still_writes_clean(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestWriteTicket.test_ordinary_body_still_writes_clean  # noqa: E501
        ticket = _ticket()
        result = write_ticket(tmp_path, ticket)
        assert result.is_ok
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok.keys() == {"T-0001"}

    # frob:ticket T-1637
    # frob:ticket T-1679
    def test_content_loss_refuses_by_default(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestWriteTicket.test_content_loss_refuses_by_default  # noqa: E501
        """T-1679 flipped the T-1637 guard's default: a write that would
        replace an existing evidence list AND Done report with nothing now
        REFUSES by default, not just warns -- the whole point of a guard
        is to prevent the thing it detects, and the old warn-only default
        would still have let the T-1636 field incident (12 evidence ids +
        a 12KB Done report discarded) happen today, just with a log line."""
        done = _ticket().model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": "## Description\nsomething\n\n## Done report\n\nshipped\n",
            }
        )
        assert write_ticket(tmp_path, done).is_ok

        # The T-1636 shape: a fresh Ticket for the SAME id, evidence and
        # Done report both gone (e.g. a hand-rolled refile that rebuilt
        # the ticket from scratch instead of renumbering it).
        stripped = _ticket().model_copy(update={"body": "## Description\nsomething\n"})
        result = write_ticket(tmp_path, stripped)
        assert result.is_err
        assert result.danger_err == TicketError.DoneReportOrEvidenceDiscarded

        # Refused means UNCHANGED on disk -- the Done report/evidence
        # must still be there.
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].evidence == ("tests/test_x.py::test_ok",)
        assert "## Done report" in loaded.danger_ok["T-0001"].body

    # frob:ticket T-1679
    def test_non_strict_opt_out_warns_loudly_instead_of_refusing(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestWriteTicket.test_non_strict_opt_out_warns_loudly_instead_of_refusing  # noqa: E501
        """`strict_no_content_loss=False` is the explicit, disclosed opt-
        out (T-1679) for a caller with a specific reason to want the OLD
        T-1637 warn-and-proceed behavior instead of the new strict
        default -- still logs the same loud warning, just does not
        refuse."""
        done = _ticket().model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": "## Description\nsomething\n\n## Done report\n\nshipped\n",
            }
        )
        assert write_ticket(tmp_path, done).is_ok

        with caplog.at_level("WARNING"):
            stripped = _ticket().model_copy(
                update={"body": "## Description\nsomething\n"}
            )
            result = write_ticket(tmp_path, stripped, strict_no_content_loss=False)
        assert result.is_ok
        assert any("content-loss guard" in record.message for record in caplog.records)

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].evidence == ()
        assert "## Done report" not in loaded.danger_ok["T-0001"].body

    # frob:ticket T-1637
    def test_keeping_evidence_or_done_report_is_never_refused(
        self, tmp_path: Path
    ) -> None:
        """Only a write that discards BOTH evidence and the Done report
        trips the guard -- normal transitions (state change, scope edit,
        evidence CONTENT change without emptying it) must never refuse."""
        # frob:tests tests/unit/test_ticket_store.py::TestWriteTicket.test_keeping_evidence_or_done_report_is_never_refused  # noqa: E501
        done = _ticket().model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": "## Description\nsomething\n\n## Done report\n\nshipped\n",
            }
        )
        assert write_ticket(tmp_path, done).is_ok

        # Keeps the Done report, only clears evidence -- fine.
        keeps_report = done.model_copy(update={"evidence": ()})
        assert write_ticket(tmp_path, keeps_report).is_ok

        # Keeps evidence, only drops the Done report heading -- fine.
        keeps_evidence = done.model_copy(update={"body": "## Description\nsomething\n"})
        assert write_ticket(tmp_path, keeps_evidence).is_ok

    # frob:ticket T-1637
    def test_first_write_for_a_new_id_is_never_refused(self, tmp_path: Path) -> None:
        """No prior on-disk content for this id -- `_check_no_content_loss`
        has nothing to compare against, so a brand-new ticket with empty
        evidence and no Done report (the normal `new_ticket` shape) must
        write clean."""
        # frob:tests tests/unit/test_ticket_store.py::TestWriteTicket.test_first_write_for_a_new_id_is_never_refused  # noqa: E501
        fresh = _ticket()
        assert fresh.evidence == ()
        result = write_ticket(tmp_path, fresh)
        assert result.is_ok


# frob:ticket T-1679
class TestWriteTicketUnchecked:
    """`_write_ticket_unchecked` -- the explicit, self-documenting escape
    hatch for a genuine "construct a deliberately poorer ticket snapshot
    on purpose" caller (T-1679), replacing the pre-T-1679 pattern of
    calling plain `write_ticket` and relying on its default being lax."""

    def test_skips_the_content_loss_guard_entirely(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestWriteTicketUnchecked.test_skips_the_content_loss_guard_entirely  # noqa: E501
        from frob.tickets._store import _write_ticket_unchecked

        done = _ticket().model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": "## Description\nsomething\n\n## Done report\n\nshipped\n",
            }
        )
        assert write_ticket(tmp_path, done).is_ok

        # The exact T-1636 content-loss shape -- plain write_ticket would
        # now refuse this (strict-by-default, T-1679); the unchecked
        # primitive proceeds without even a warning, as test fixtures
        # simulating a stale/regressed ledger side legitimately need.
        stripped = _ticket().model_copy(update={"body": "## Description\nsomething\n"})
        result = _write_ticket_unchecked(tmp_path, stripped)
        assert result.is_ok

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].evidence == ()
        assert "## Done report" not in loaded.danger_ok["T-0001"].body


# frob:ticket T-1254
class TestV2WriteTicket:
    def test_write_then_load_v2_mode(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestV2WriteTicket.test_write_then_load_v2_mode  # noqa: E501
        (tmp_path / "tickets" / "T-0099").mkdir(parents=True)
        (tmp_path / "tickets" / "T-0099" / "ticket.md").write_text(
            _serialize_ticket(_ticket("T-0099"))
        )
        assert _store_mode(tmp_path) == "v2"

        ticket = _ticket()
        written = write_ticket(tmp_path, ticket)
        assert written.is_ok
        assert v2_ticket_path(tmp_path, "T-0001").exists()

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok.keys() == {"T-0001", "T-0099"}
        assert loaded.danger_ok["T-0001"].title == ticket.title

    def test_ticket_dir_named_by_id_not_slug(self, tmp_path: Path) -> None:
        """Design section 1: the directory name IS the id, never a
        slugified title -- a retitle must never rename the path."""
        (tmp_path / "tickets" / "T-0001").mkdir(parents=True)
        (tmp_path / "tickets" / "T-0001" / "ticket.md").write_text(
            _serialize_ticket(_ticket())
        )
        ticket = _ticket(title="A Completely Different Title")
        written = write_ticket(tmp_path, ticket)
        assert written.is_ok
        assert v2_ticket_dir(tmp_path, "T-0001") == tmp_path / "tickets" / "T-0001"
        assert v2_ticket_path(tmp_path, "T-0001").exists()

    def test_write_all_v2_prunes_removed_ticket(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::write_all kind="unit"
        (tmp_path / "tickets" / "T-0001").mkdir(parents=True)
        (tmp_path / "tickets" / "T-0001" / "ticket.md").write_text(
            _serialize_ticket(_ticket())
        )
        (tmp_path / "tickets" / "T-0002").mkdir(parents=True)
        (tmp_path / "tickets" / "T-0002" / "ticket.md").write_text(
            _serialize_ticket(_ticket("T-0002"))
        )
        assert _store_mode(tmp_path) == "v2"

        result = write_all(tmp_path, {"T-0001": _ticket()})
        assert result.is_ok
        assert v2_ticket_path(tmp_path, "T-0001").exists()
        assert not v2_ticket_dir(tmp_path, "T-0002").exists()


# frob:ticket T-1561
class TestWriteArchivedTicket:
    """`write_archived_ticket` (T-1561): the archive-side analog of
    `write_ticket` -- the primitive `evidence --replace --archived`
    needs to repair a stale binding on an already-archived ticket
    without resurrecting it into active storage."""

    def test_v2_mode_writes_under_archive_dir(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_ticket_store.py::TestWriteArchivedTicket.test_v2_mode_writes_\
        # under_archive_dir kind="unit"
        from frob.tickets._store import v2_archive_dir, write_archived_ticket

        # Any v2 marker (active or archived) flips _store_mode to v2.
        (tmp_path / "tickets" / "archive" / "T-0099").mkdir(parents=True)
        (tmp_path / "tickets" / "archive" / "T-0099" / "ticket.md").write_text(
            _serialize_ticket(_ticket("T-0099"))
        )
        assert _store_mode(tmp_path) == "v2"

        ticket = _ticket()
        result = write_archived_ticket(tmp_path, ticket)
        assert result.is_ok
        assert (v2_archive_dir(tmp_path, "T-0001") / "ticket.md").exists()
        assert not v2_ticket_dir(tmp_path, "T-0001").exists()

        archived = load_archive(tmp_path)
        assert archived.is_ok
        assert archived.danger_ok.keys() == {"T-0001", "T-0099"}

    def test_single_mode_splices_into_archive_file(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_ticket_store.py::TestWriteArchivedTicket.test_single_mode_spl\
        # ices_into_archive_file kind="unit"
        from frob.tickets._store import write_archived_ticket

        # Pin v1/'single' mode explicitly (fresh-repo default is v2,
        # T-1553).
        atomic_write(ledger_path(tmp_path), "# Tickets\n\n")
        assert _store_mode(tmp_path) == "single"

        ticket = _ticket()
        result = write_archived_ticket(tmp_path, ticket)
        assert result.is_ok
        assert "<!-- ticket:" not in ledger_path(tmp_path).read_text(encoding="utf-8")
        text = archive_path(tmp_path).read_text(encoding="utf-8")
        assert "<!-- ticket:T-0001 -->" in text

        archived = load_archive(tmp_path)
        assert archived.is_ok
        assert archived.danger_ok.keys() == {"T-0001"}
        # The active ledger is never touched -- nothing resurrected there.
        active = load_all(tmp_path)
        assert active.is_ok
        assert active.danger_ok == {}

    # frob:ticket T-1583
    def test_v2_write_archive_round_trips_through_load_archive(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_store.py::TestWriteArchivedTicket.test_v2_write_archiv\
        # e_round_trips_through_load_archive kind="unit"
        """T-1583: `write_archive` wrote the `tickets-archive.md` monofile
        even in v2 mode, where `load_archive` globs `tickets/archive/**`
        and never reads it -- `archive()` then dropped those same ids from
        active storage, losing them from every read path."""
        from frob.tickets._store import write_archive

        v2_ticket_dir(tmp_path, "T-0100").mkdir(parents=True)
        (v2_ticket_dir(tmp_path, "T-0100") / "ticket.md").write_text(
            _serialize_ticket(_ticket("T-0100"))
        )
        assert _store_mode(tmp_path) == "v2"

        assert write_archive(
            tmp_path, {"T-0001": _ticket(), "T-0002": _ticket("T-0002")}
        ).is_ok
        assert not archive_path(tmp_path).exists()

        archived = load_archive(tmp_path)
        assert archived.is_ok
        assert archived.danger_ok.keys() == {"T-0001", "T-0002"}

    # frob:ticket T-1583
    def test_v2_write_archive_prunes_ids_absent_from_the_map(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_store.py::TestWriteArchivedTicket.test_v2_write_archiv\
        # e_prunes_ids_absent_from_the_map kind="unit"
        """`write_archive`'s contract is wholesale REPLACE, so the v2
        branch must prune an archived id the new map omits -- otherwise
        `renumber`'s rewrite would leave the old id behind as a ghost."""
        from frob.tickets._store import v2_archive_dir, write_archive

        v2_archive_dir(tmp_path, "T-0009").mkdir(parents=True)
        (v2_archive_dir(tmp_path, "T-0009") / "ticket.md").write_text(
            _serialize_ticket(_ticket("T-0009"))
        )
        assert _store_mode(tmp_path) == "v2"

        assert write_archive(tmp_path, {"T-0001": _ticket()}).is_ok
        assert not v2_archive_dir(tmp_path, "T-0009").exists()

        archived = load_archive(tmp_path)
        assert archived.is_ok
        assert archived.danger_ok.keys() == {"T-0001"}

    def test_single_mode_preserves_sibling_archived_ticket(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_store.py::TestWriteArchivedTicket.test_single_mode_pre\
        # serves_sibling_archived_ticket kind="unit"
        from frob.tickets._store import write_archive, write_archived_ticket

        atomic_write(ledger_path(tmp_path), "# Tickets\n\n")
        assert write_archive(tmp_path, {"T-0002": _ticket("T-0002")}).is_ok

        updated = _ticket().model_copy(update={"title": "T-0001 rebound"})
        result = write_archived_ticket(tmp_path, updated)
        assert result.is_ok

        archived = load_archive(tmp_path)
        assert archived.is_ok
        assert archived.danger_ok.keys() == {"T-0001", "T-0002"}
        assert archived.danger_ok["T-0001"].title == "T-0001 rebound"


class TestMigrateToLedger:
    def test_moves_legacy_files_into_ledger(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::migrate_to_ledger kind="unit"
        d = tmp_path / "tickets"
        d.mkdir()
        ticket = _ticket()
        legacy_path = d / "T-0001-sample-ticket.md"
        legacy_path.write_text(_serialize_ticket(ticket), encoding="utf-8")

        result = migrate_to_ledger(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 1
        assert not legacy_path.exists()
        assert ledger_path(tmp_path).exists()

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok.keys() == {"T-0001"}
        assert loaded.danger_ok["T-0001"].id == ticket.id
        assert loaded.danger_ok["T-0001"].title == ticket.title
        assert loaded.danger_ok["T-0001"].body.strip() == ticket.body.strip()

    def test_no_legacy_files_is_zero(self, tmp_path: Path) -> None:
        result = migrate_to_ledger(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 0


class TestArchiveLedger:
    def test_archive_path_at_root(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::archive_path kind="unit"
        assert archive_path(tmp_path) == tmp_path / "tickets-archive.md"

    def test_load_archive_missing_file_is_empty(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::load_archive kind="unit"
        result = load_archive(tmp_path)
        assert result.is_ok
        assert result.danger_ok == {}

    def test_write_then_load_archive_round_trips(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::write_archive kind="unit"
        ticket = _ticket(ticket_id="T-0002", title="Archived one")
        written = write_archive(tmp_path, {"T-0002": ticket})
        assert written.is_ok
        assert archive_path(tmp_path).exists()

        loaded = load_archive(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok.keys() == {"T-0002"}
        assert loaded.danger_ok["T-0002"].title == "Archived one"

    def test_archive_format_matches_ledger_marker(self, tmp_path: Path) -> None:
        write_archive(tmp_path, {"T-0001": _ticket()})
        text = archive_path(tmp_path).read_text(encoding="utf-8")
        assert "<!-- ticket:T-0001 -->" in text
        assert "```yaml" in text


# frob:ticket T-1636
class TestYamlLoader:
    """Direct tests of `_yaml_loader`'s CSafeLoader/SafeLoader selection."""

    # frob:ticket T-1373
    # frob:ticket T-1636
    # T-1636: retargeted from the class docstring (COV006 -- a
    # class symbol has no call-graph node of its own to traverse from) onto
    # this method, which calls `_yaml_loader()` directly below.
    # frob:tests src/frob/tickets/_store.py::_yaml_loader kind="unit"
    def test_prefers_csafeloader_when_libyaml_present(self, monkeypatch) -> None:
        """T-1373: this predates T-1333, which deliberately falls back to
        `SafeLoader` whenever a coverage tracer is live -- so under `make
        coverage` the unconditional assertion was false BY DESIGN. Pin the
        no-tracer case explicitly instead of inheriting whichever tracer
        the ambient run happens to have installed."""
        import sys

        import yaml

        from frob.tickets._store import _yaml_loader

        if not yaml.__with_libyaml__:
            pytest.skip("libyaml not installed in this environment")
        monkeypatch.setattr(sys, "gettrace", lambda: None)
        assert _yaml_loader() is yaml.CSafeLoader

    def test_falls_back_to_safeloader_without_libyaml(self, monkeypatch) -> None:
        import yaml

        from frob.tickets._store import _yaml_loader

        monkeypatch.setattr(yaml, "__with_libyaml__", False)
        assert _yaml_loader() is yaml.SafeLoader

    def test_detects_coverage_tracer_by_module_name(self, monkeypatch) -> None:
        """T-1333: a `sys.gettrace()` callable whose `__module__` starts
        with 'coverage' is recognized as a coverage.py tracer."""
        import sys

        from frob.tickets._store import _coverage_tracer_active

        def fake_tracer(frame, event, arg):
            return fake_tracer

        fake_tracer.__module__ = "coverage.pytracer"

        monkeypatch.setattr(sys, "gettrace", lambda: fake_tracer)
        assert _coverage_tracer_active() is True

    def test_no_active_tracer_is_not_coverage(self, monkeypatch) -> None:
        """No active `sys.gettrace()` tracer means no coverage tracer."""
        import sys

        from frob.tickets._store import _coverage_tracer_active

        monkeypatch.setattr(sys, "gettrace", lambda: None)
        assert _coverage_tracer_active() is False

    def test_falls_back_to_safeloader_under_active_coverage_tracer(
        self, monkeypatch
    ) -> None:
        """T-1333: even with libyaml present, an active coverage.py tracer
        forces the pure-Python SafeLoader to avoid the CSafeLoader
        corruption bug."""
        import sys

        import yaml

        from frob.tickets._store import _yaml_loader

        def fake_tracer(frame, event, arg):
            return fake_tracer

        fake_tracer.__module__ = "coverage.pytracer"

        monkeypatch.setattr(yaml, "__with_libyaml__", True)
        monkeypatch.setattr(sys, "gettrace", lambda: fake_tracer)
        assert _yaml_loader() is yaml.SafeLoader


class TestLoadArchiveCache:
    # frob:tests src/frob/tickets/_store.py::load_archive kind="unit"
    """Direct tests of `load_archive`'s content-hash-keyed parsed cache."""

    def test_skips_reparse_when_content_hash_unchanged(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from frob.tickets import _store

        write_archive(tmp_path, {"T-0003": _ticket(ticket_id="T-0003")})
        first = load_archive(tmp_path)
        assert first.is_ok

        calls = {"n": 0}
        original = _store._parse_ledger

        def _counting_parse(text: str):
            calls["n"] += 1
            return original(text)

        monkeypatch.setattr(_store, "_parse_ledger", _counting_parse)
        second = load_archive(tmp_path)
        assert second.is_ok
        assert second.danger_ok.keys() == {"T-0003"}
        assert calls["n"] == 0, "cache hit must not reparse the ledger text"

    def test_reparses_when_archive_content_changes(self, tmp_path: Path) -> None:
        write_archive(tmp_path, {"T-0004": _ticket(ticket_id="T-0004", title="One")})
        first = load_archive(tmp_path)
        assert first.is_ok
        assert first.danger_ok["T-0004"].title == "One"

        write_archive(tmp_path, {"T-0004": _ticket(ticket_id="T-0004", title="Two")})
        second = load_archive(tmp_path)
        assert second.is_ok
        assert second.danger_ok["T-0004"].title == "Two"


class TestAtomicWrite:
    def test_writes_text_content(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::atomic_write kind="unit"
        path = tmp_path / "sub" / "out.txt"
        result = atomic_write(path, "hello\n")
        assert result.is_ok
        assert path.read_text(encoding="utf-8") == "hello\n"

    def test_writes_bytes_content(self, tmp_path: Path) -> None:
        path = tmp_path / "out.bin"
        result = atomic_write(path, b"\x00\x01\x02")
        assert result.is_ok
        assert path.read_bytes() == b"\x00\x01\x02"

    def test_no_leftover_temp_file(self, tmp_path: Path) -> None:
        path = tmp_path / "out.txt"
        atomic_write(path, "content")
        leftovers = [p for p in tmp_path.iterdir() if p.name != "out.txt"]
        assert leftovers == []

    # frob:ticket T-0458
    def test_no_partial_file_on_simulated_interrupt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Simulate a crash between temp-write and rename (os.replace raises):
        the destination must be left EXACTLY as it was before the call (never
        a torn/partial write), and the temp file must not linger (T-0458)."""
        path = tmp_path / "tickets.md"
        path.write_text("original content\n", encoding="utf-8")

        real_replace = os.replace

        def _boom(src: str, dst: str) -> None:
            raise OSError("simulated crash mid-rename")

        monkeypatch.setattr(os, "replace", _boom)
        result = atomic_write(path, "NEW CONTENT THAT SHOULD NEVER LAND\n")
        monkeypatch.setattr(os, "replace", real_replace)

        assert result.is_err
        assert result.danger_err == TicketError.WriteFailed
        assert path.read_text(encoding="utf-8") == "original content\n"
        leftovers = [p for p in tmp_path.iterdir() if p.name != "tickets.md"]
        assert leftovers == [], f"a partial/temp file leaked: {leftovers}"

    # frob:ticket T-0456
    def test_fsyncs_file_before_replace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0456: `atomic_write` must durably flush the temp file (fsync)
        BEFORE the rename that makes it visible under `path`, so a power
        loss right after the rename cannot surface stale/unflushed data."""
        path = tmp_path / "tickets.md"
        events: list[str] = []

        real_fsync = os.fsync
        real_replace = os.replace

        def _record_fsync(fd: int) -> None:
            events.append("fsync")
            real_fsync(fd)

        def _record_replace(src: str, dst: str) -> None:
            events.append("replace")
            real_replace(src, dst)

        monkeypatch.setattr(os, "fsync", _record_fsync)
        monkeypatch.setattr(os, "replace", _record_replace)
        result = atomic_write(path, "content\n")

        assert result.is_ok
        assert events == ["fsync", "replace"]

    # frob:ticket T-0456
    def test_fsync_failure_is_write_failed_not_a_partial_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An `fsync` failure (e.g. ENOSPC/EIO) must behave exactly like a
        `os.replace` failure: Err(WriteFailed), destination untouched, no
        leftover temp file (T-0456, same contract as
        test_no_partial_file_on_simulated_interrupt)."""
        path = tmp_path / "tickets.md"
        path.write_text("original content\n", encoding="utf-8")

        def _boom(fd: int) -> None:
            raise OSError("simulated fsync failure")

        monkeypatch.setattr(os, "fsync", _boom)
        result = atomic_write(path, "NEW CONTENT THAT SHOULD NEVER LAND\n")

        assert result.is_err
        assert result.danger_err == TicketError.WriteFailed
        assert path.read_text(encoding="utf-8") == "original content\n"
        leftovers = [p for p in tmp_path.iterdir() if p.name != "tickets.md"]
        assert leftovers == [], f"a partial/temp file leaked: {leftovers}"


# frob:ticket T-0458
class TestLockPath:
    def test_lock_path_under_frob_dir(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestLockPath.test_lock_path_under_frob_dir  # noqa: E501
        assert _lock_path(tmp_path) == tmp_path / ".frob" / "tickets.lock"


# frob:ticket T-0458
class TestLedgerLock:
    def test_lock_file_created_under_frob_dir(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestLedgerLock.test_lock_file_created_under_frob_dir  # noqa: E501
        assert _lock_path(tmp_path) == tmp_path / ".frob" / "tickets.lock"
        with ledger_lock(tmp_path):
            pass
        assert _lock_path(tmp_path).exists()

    def test_reentrant_in_same_thread(self, tmp_path: Path) -> None:
        """Nested `with ledger_lock():` in the SAME thread must not deadlock
        -- `write_ticket` locking internally while called from inside an
        outer `ledger_lock` block (as `new_ticket` does) is the exact shape
        this covers."""
        with ledger_lock(tmp_path):
            with ledger_lock(tmp_path):
                write_ticket(tmp_path, _ticket())
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert "T-0001" in loaded.danger_ok

    def test_two_threads_serialize(self, tmp_path: Path) -> None:
        """Two threads racing to hold the lock never overlap: while one
        holds it, the other observes it held (a crude but real cross-thread
        mutual-exclusion check, not just "no exception raised")."""
        order: list[str] = []
        barrier = threading.Barrier(2)

        def worker(name: str) -> None:
            barrier.wait()
            with ledger_lock(tmp_path):
                order.append(f"{name}-enter")
                order.append(f"{name}-exit")

        threads = [
            threading.Thread(target=worker, args=("a",)),
            threading.Thread(target=worker, args=("b",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        # Each thread's enter/exit pair must be contiguous (never interleaved
        # with the other thread's enter/exit) -- proof the lock actually
        # serialized the critical sections.
        assert order in (
            ["a-enter", "a-exit", "b-enter", "b-exit"],
            ["b-enter", "b-exit", "a-enter", "a-exit"],
        )


# frob:ticket T-0458
class TestReplaceDoneReportSection:
    def test_appends_when_absent(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestReplaceDoneReportSection.test_appends_when_absent  # noqa: E501
        body = "## Description\nsomething\n"
        result = replace_done_report_section(body, "## Done report\n\nfoo\n")
        assert "## Description" in result
        assert "## Done report" in result
        assert "foo" in result
        assert result.index("## Description") < result.index("## Done report")

    def test_replaces_existing_section(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestReplaceDoneReportSection.test_replaces_existing_section  # noqa: E501
        body = (
            "## Description\nkeep me\n\n"
            "## Done report\n\nOLD STALE REPORT\n\n"
            "## Failure log\nkeep this too\n"
        )
        result = replace_done_report_section(body, "## Done report\n\nNEW REPORT\n")
        assert "keep me" in result
        assert "keep this too" in result
        assert "OLD STALE REPORT" not in result
        assert "NEW REPORT" in result
        # Section ordering preserved: Description, Done report, Failure log.
        assert (
            result.index("## Description")
            < result.index("## Done report")
            < result.index("## Failure log")
        )

    def test_only_one_done_report_heading_after_replace(self) -> None:
        body = "## Done report\n\nfirst\n"
        result = replace_done_report_section(body, "## Done report\n\nsecond\n")
        assert result.count("## Done report") == 1
        assert "second" in result
        assert "first" not in result

    # frob:ticket T-0493
    def test_stray_empty_heading_before_real_one_collapses_to_one(self) -> None:
        """T-0493 regression: a stray, EMPTY '## Done report' heading sitting
        before a real, substantive one (the corrupted shape that made
        `close` fail with MissingEvidence, reading only the empty first
        section) must collapse to a single heading on the next write, not
        persist forever."""
        body = "## Description\nkeep me\n\n## Done report\n\n## Done report\n\nreal content\n"
        result = replace_done_report_section(body, "## Done report\n\nnew narrative\n")
        assert result.count("## Done report") == 1
        assert "real content" not in result
        assert "new narrative" in result
        assert "keep me" in result


# frob:ticket T-1536
class TestSanitizeNarrativeForLedger:
    """T-1536: any line in caller-authored narrative that would otherwise
    round-trip as a literal `<!-- ticket:T-#### -->` ledger marker must be
    defused before it ever reaches a splice/render call -- the root-cause
    fix for the 2026-08-05 T-1315/T-1318/T-1350 duplicate-anchor incident."""

    # frob:ticket T-1536
    def test_defuses_marker_lookalike_line(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger.test_defuses_marker_lookalike_line  # noqa: E501
        why = "Incident repro:\n<!-- ticket:T-1315 -->\nsome narrative text\n"
        out = sanitize_narrative_for_ledger(why)
        assert "<!-- ticket:T-1315 -->" not in out
        # Still human-readable -- only the exact-match token is broken.
        assert "T-1315" in out
        assert "ticket:T-1315" in out

    # frob:ticket T-1536
    def test_unbalanced_fence_around_marker_lookalike_still_defused(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger.test_unbalanced_fence_around_marker_lookalike_still_defused  # noqa: E501
        # The exact incident shape: a why-file narrative quoting a corrupt
        # ledger span, complete with an unclosed ```yaml fence -- the fence
        # imbalance itself is irrelevant to this function; the marker
        # lookalike line is what must be defused.
        why = (
            "the corrupt span looked like:\n"
            "<!-- ticket:T-1315 -->\n"
            "```yaml\n"
            "id: T-1318\n"
            "unrelated report text with no closing fence\n"
        )
        out = sanitize_narrative_for_ledger(why)
        assert "<!-- ticket:T-1315 -->" not in out

    # frob:ticket T-1536
    def test_no_marker_lookalike_line_passes_through_unchanged(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger.test_no_marker_lookalike_line_passes_through_unchanged  # noqa: E501
        why = "Ordinary narrative text mentioning T-1315 inline, no bare marker line.\n"
        assert sanitize_narrative_for_ledger(why) == why

    # frob:ticket T-1536
    def test_defused_line_no_longer_matches_the_real_marker_pattern(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger.test_defused_line_no_longer_matches_the_real_marker_pattern  # noqa: E501
        from frob.tickets._store import _LEDGER_MARKER_RE

        why = "<!-- ticket:T-0042 -->\n"
        out = sanitize_narrative_for_ledger(why)
        assert _LEDGER_MARKER_RE.search(out) is None


def _ticket_evidence(
    evidence: tuple[str, ...] = (), ticket_id: str = "T-0001"
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title="With evidence",
        state=TicketState.IN_PROGRESS,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        evidence=evidence,
        body="## Description\nsomething\n",
    )


# frob:ticket T-0458
class TestRenderEvidenceBlock:
    def test_no_evidence_renders_placeholder(self) -> None:
        from frob.tickets import render_evidence_block

        assert render_evidence_block(()) == "(no evidence recorded)"

    def test_mixed_cmd_and_pytest_ids(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestRenderEvidenceBlock.test_mixed_cmd_and_pytest_ids  # noqa: E501
        from frob.tickets import render_evidence_block

        evidence = (
            "tests/test_x.py::test_y",
            "cmd:echo hi exit=0 sha256=" + "a" * 12,
        )
        block = render_evidence_block(evidence)
        assert "tests/test_x.py::test_y" in block
        assert "verified passing when recorded" in block
        assert "cmd evidence, exit=0" in block


# frob:ticket T-0458
class TestComputeChangedLines:
    def test_non_git_root_returns_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestComputeChangedLines.test_non_git_root_returns_empty  # noqa: E501
        from frob.tickets import compute_changed_lines

        assert compute_changed_lines(tmp_path, base_ref="main") == ()

    def test_unknown_base_ref_returns_empty_not_raises(self, tmp_path: Path) -> None:
        from frob.tickets import compute_changed_lines

        # tmp_path is not even a git repo, so any base_ref degrades to ()
        # rather than raising -- the Changed block is best-effort.
        assert compute_changed_lines(tmp_path, base_ref="does-not-exist") == ()


# frob:ticket T-0458
class TestRenderChangedBlock:
    def test_no_lines_renders_placeholder(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestRenderChangedBlock.test_no_lines_renders_placeholder  # noqa: E501
        from frob.tickets import render_changed_block

        assert render_changed_block(()) == "(no changed files detected)"

    def test_lines_rendered_fenced(self) -> None:
        from frob.tickets import render_changed_block

        block = render_changed_block(("src/x.py | 3 ++-",))
        assert block.startswith("```\n")
        assert "src/x.py | 3 ++-" in block
        assert block.endswith("\n```")


# frob:ticket T-0458
# frob:ticket T-1536
class TestComposeDoneReport:
    def test_composes_all_three_sections(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_composes_all_three_sections  # noqa: E501
        from frob.tickets import compose_done_report

        report = compose_done_report(
            "narrative here", ("src/x.py | 1 +",), ("tests/x.py::test_y",)
        )
        assert report.startswith("## Done report")
        assert "narrative here" in report
        assert "### Changed" in report
        assert "src/x.py | 1 +" in report
        assert "### Evidence" in report
        assert "tests/x.py::test_y" in report

    def test_blank_why_gets_placeholder(self) -> None:
        from frob.tickets import compose_done_report

        report = compose_done_report("   ", (), ())
        assert "(no narrative supplied)" in report

    def test_strips_duplicate_leading_heading_from_why(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_strips_duplicate_leading_heading_from_why  # noqa: E501
        from frob.tickets import compose_done_report

        report = compose_done_report(
            "## Done report\n\nnarrative here", ("src/x.py | 1 +",), ()
        )
        assert report.count("Done report") == 1
        assert report.startswith("## Done report")
        assert "narrative here" in report

    # frob:ticket T-1536
    def test_marker_lookalike_line_in_why_is_defused(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_marker_lookalike_line_in_why_is_defused  # noqa: E501
        """T-1536 regression: the exact incident shape -- a `why` narrative
        quoting another ticket's literal ledger marker verbatim, with an
        unbalanced code fence around it (the corrupt-span repro text an
        agent's Done report would plausibly include) -- must never survive
        into the composed section as a real, marker-matching line."""
        from frob.tickets import compose_done_report
        from frob.tickets._store import _LEDGER_MARKER_RE

        why = (
            "root cause repro:\n"
            "<!-- ticket:T-1315 -->\n"
            "```yaml\n"
            "id: T-1318\n"
            "unrelated report text, fence never closed\n"
        )
        report = compose_done_report(why, (), ())
        assert _LEDGER_MARKER_RE.search(report) is None
        assert "T-1315" in report  # still legible, just not a real marker

    def test_leaves_non_leading_heading_in_narrative_alone(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_leaves_non_leading_heading_in_narrative_alone  # noqa: E501
        from frob.tickets import compose_done_report

        report = compose_done_report(
            "narrative mentions ## Done report mid-text", (), ()
        )
        assert report.count("Done report") == 2


# frob:ticket T-0458
class TestSetDoneReport:
    def test_composes_and_writes_atomically(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestSetDoneReport.test_composes_and_writes_atomically  # noqa: E501
        write_ticket(tmp_path, _ticket_evidence(evidence=("tests/x.py::test_y",)))

        result = set_done_report(
            tmp_path, "T-0001", why="implemented the thing", base_ref="does-not-exist"
        )
        assert result.is_ok
        ticket = result.danger_ok
        assert "## Done report" in ticket.body
        assert "implemented the thing" in ticket.body
        assert "tests/x.py::test_y" in ticket.body
        assert "### Changed" in ticket.body
        assert "### Evidence" in ticket.body

        reloaded = load_all(tmp_path)
        assert reloaded.is_ok
        assert "implemented the thing" in reloaded.danger_ok["T-0001"].body

    def test_caller_never_touches_markdown(self, tmp_path: Path) -> None:
        """The whole point (T-0458): a caller supplies ONLY `why` -- no
        markdown, no block boundaries, no Changed/Evidence text -- and the
        write still lands with both auto-filled sections present."""
        write_ticket(tmp_path, _ticket_evidence())
        result = set_done_report(tmp_path, "T-0001", why="just the narrative")
        assert result.is_ok
        assert "### Changed" in result.danger_ok.body
        assert "### Evidence" in result.danger_ok.body

    def test_unknown_ticket_is_not_found(self, tmp_path: Path) -> None:
        result = set_done_report(tmp_path, "T-9999", why="x")
        assert result.is_err
        assert result.danger_err == TicketError.NotFound

    def test_second_call_replaces_first_report(self, tmp_path: Path) -> None:
        write_ticket(tmp_path, _ticket_evidence())
        set_done_report(tmp_path, "T-0001", why="first attempt")
        second = set_done_report(tmp_path, "T-0001", why="second, corrected attempt")
        assert second.is_ok
        body = second.danger_ok.body
        assert body.count("## Done report") == 1
        assert "second, corrected attempt" in body
        assert "first attempt" not in body

    def test_v2_mode_writes_done_report_md_not_body(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestSetDoneReport.test_v2_mode_writes_done_report_md_not_body  # noqa: E501
        d = tmp_path / "tickets" / "T-0001"
        d.mkdir(parents=True)
        (d / "ticket.md").write_text(_serialize_ticket(_ticket_evidence()))
        assert _store_mode(tmp_path) == "v2"

        result = set_done_report(
            tmp_path, "T-0001", why="v2 done report", base_ref="does-not-exist"
        )
        assert result.is_ok
        # ticket.md ON DISK is untouched -- no '## Done report' spliced in;
        # that separation is the whole point of the v2 split.
        on_disk = (d / "ticket.md").read_text(encoding="utf-8")
        assert "## Done report" not in on_disk

        # T-1587: the ticket handed BACK does carry the report in `body`,
        # matching what the next load_all produces -- every consumer
        # (close, evidence recovery, TICK006) reads it from there.
        assert "## Done report" in result.danger_ok.body
        assert "v2 done report" in result.danger_ok.body
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].body == result.danger_ok.body

        report_text = read_done_report(tmp_path, "T-0001")
        assert report_text is not None
        assert "## Done report" in report_text
        assert "v2 done report" in report_text
        assert "### Evidence" in report_text


# frob:ticket T-1587
class TestV2FullLifecycleDoneReport:
    """T-1587's own suggested follow-up: an integration test that runs the
    full `new -> start -> evidence -> done-report -> close` cycle against a
    v2 repo end to end, rather than each half (write/read) checked in
    isolation. The unit layer alone missed the original bug -- `write_
    done_report`'s v2 branch and `load_all`'s v2 branch were each
    individually correct on their own terms, and only their COMBINATION
    (a load right after a report write) exposed the gap `_merge_sibling_
    done_report` closes."""

    def test_close_does_not_refuse_recent_report(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestV2FullLifecycleDoneReport.test_close_does_not_refuse_recent_report  # noqa: E501
        """The exact field incident this ticket names: `frob ticket close`
        refusing a ticket whose Done report was written seconds earlier,
        in a v2 repo, because `Ticket.body` (what the DONE-transition
        guard reads) never carried it."""
        spec = TicketSpec(
            title="v2 lifecycle", kind=TicketKind.DOCS, origin=Origin.HUMAN
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id
        assert _store_mode(tmp_path) == "v2"

        planned = transition(tmp_path, ticket_id, TicketState.PLANNED)
        assert planned.is_ok
        started = transition(tmp_path, ticket_id, TicketState.IN_PROGRESS)
        assert started.is_ok

        evidenced = add_evidence(
            tmp_path,
            ticket_id,
            ["tests/test_x.py::test_y"],
            collected=frozenset({"tests/test_x.py::test_y"}),
            passed=frozenset({"tests/test_x.py::test_y"}),
        )
        assert evidenced.is_ok

        # `write_done_report`'s v2 branch stores the report ONLY in
        # tickets/<id>/done-report.md -- ticket.md on disk is untouched.
        reported = set_done_report(tmp_path, ticket_id, why="did the thing")
        assert reported.is_ok
        on_disk_ticket_md = (tmp_path / "tickets" / ticket_id / "ticket.md").read_text(
            encoding="utf-8"
        )
        assert "## Done report" not in on_disk_ticket_md
        assert (tmp_path / "tickets" / ticket_id / "done-report.md").exists()

        # The bug: a load right here (what `transition(..., DONE)` does
        # internally) used to see NO Done report at all, so this refused
        # with MissingEvidence despite the report existing on disk.
        closed = transition(tmp_path, ticket_id, TicketState.DONE)
        assert closed.is_ok, f"close refused a report written seconds earlier: {closed}"
        assert closed.danger_ok.state is TicketState.DONE

        # And the closed ticket, read back fresh (the land ledger merge's
        # own vantage point), still carries the report -- TICK006/land
        # never go blind on the very next load either.
        reloaded = load_all(tmp_path)
        assert reloaded.is_ok
        assert "## Done report" in reloaded.danger_ok[ticket_id].body
        assert "did the thing" in reloaded.danger_ok[ticket_id].body


# frob:ticket T-0357
class TestReplayEvidenceFromDoneReport:
    def test_recovers_ids_when_structured_evidence_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport.test_recovers_ids_when_structured_evidence_empty  # noqa: E501
        """The T-0357 recovery path: a hand `git merge --no-ff` that lands
        the Done report prose but drops the structured `evidence:` field
        must still let `transition(..., DONE)` succeed by recovering the
        ids straight out of the rendered '### Evidence' section."""
        write_ticket(tmp_path, _ticket_evidence(evidence=("tests/x.py::test_y",)))
        set_done_report(
            tmp_path, "T-0001", why="did the thing", base_ref="does-not-exist"
        )
        # Simulate the bug: structured evidence lost, Done report text intact.
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        ticket = loaded.danger_ok["T-0001"]
        assert "tests/x.py::test_y" in ticket.body
        stripped = ticket.model_copy(update={"evidence": ()})
        write_ticket(tmp_path, stripped)

        result = replay_evidence_from_done_report(tmp_path, "T-0001")
        assert result.is_ok
        assert result.danger_ok.evidence == ("tests/x.py::test_y",)

        reloaded = load_all(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok["T-0001"].evidence == ("tests/x.py::test_y",)

    def test_noop_when_evidence_already_present(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport.test_noop_when_evidence_already_present  # noqa: E501
        write_ticket(tmp_path, _ticket_evidence(evidence=("tests/x.py::test_y",)))
        result = replay_evidence_from_done_report(tmp_path, "T-0001")
        assert result.is_ok
        assert result.danger_ok.evidence == ("tests/x.py::test_y",)

    def test_missing_evidence_when_nothing_recoverable(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport.test_missing_evidence_when_nothing_recoverable  # noqa: E501
        write_ticket(tmp_path, _ticket_evidence(evidence=()))
        result = replay_evidence_from_done_report(tmp_path, "T-0001")
        assert result.is_err
        assert result.danger_err == TicketError.MissingEvidence

    def test_transition_to_done_auto_replays_lost_evidence(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport.test_transition_to_done_auto_replays_lost_evidence  # noqa: E501
        """The end-to-end T-0357 fix: `transition(..., DONE)` on a ticket
        whose structured evidence was lost (but Done report prose survived)
        succeeds by auto-replaying, rather than failing MissingEvidence."""
        write_ticket(
            tmp_path,
            _ticket_evidence(evidence=("tests/x.py::test_y",)),
        )
        set_done_report(
            tmp_path, "T-0001", why="did the thing", base_ref="does-not-exist"
        )
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        stripped = loaded.danger_ok["T-0001"].model_copy(update={"evidence": ()})
        write_ticket(tmp_path, stripped)

        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_ok
        assert result.danger_ok.evidence == ("tests/x.py::test_y",)


def _ticket_state(
    ticket_id: str, state: TicketState, *, created: date = date(2026, 1, 1)
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=f"{ticket_id} ticket",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=created,
        body="## Description\nsomething\n",
    )


# frob:ticket T-0409
class TestClosedTicketIds:
    def test_returns_done_and_dropped_only(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestClosedTicketIds.test_returns_done_and_dropped_only  # noqa: E501
        queue = TicketQueue(
            tickets={
                "T-0001": _ticket_state("T-0001", TicketState.DONE),
                "T-0002": _ticket_state("T-0002", TicketState.DROPPED),
                "T-0003": _ticket_state("T-0003", TicketState.QUEUED),
                "T-0004": _ticket_state("T-0004", TicketState.IN_PROGRESS),
            }
        )
        assert closed_ticket_ids(queue) == ("T-0001", "T-0002")

    def test_orders_oldest_first(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestClosedTicketIds.test_orders_oldest_first  # noqa: E501
        queue = TicketQueue(
            tickets={
                "T-0002": _ticket_state(
                    "T-0002", TicketState.DONE, created=date(2026, 2, 1)
                ),
                "T-0001": _ticket_state(
                    "T-0001", TicketState.DONE, created=date(2026, 1, 1)
                ),
            }
        )
        assert closed_ticket_ids(queue) == ("T-0001", "T-0002")

    def test_empty_queue_is_empty(self) -> None:
        # frob:tests tests/unit/test_ticket_store.py::TestClosedTicketIds.test_empty_queue_is_empty  # noqa: E501
        assert closed_ticket_ids(TicketQueue(tickets={})) == ()


# frob:ticket T-0458
class TestRaceFreeIdAllocation:
    def test_concurrent_new_ticket_never_collides(self, tmp_path: Path) -> None:
        """Two rapid `new_ticket` calls (here, many concurrent threads) must
        never allocate the same id -- the T-0465 duplicate-T-0427 incident
        this ticket exists to make structurally impossible."""

        def make(i: int):  # noqa: ANN202
            spec = TicketSpec(
                title=f"race-{i}", kind=TicketKind.FEATURE, origin=Origin.HUMAN
            )
            return new_ticket(tmp_path, spec)

        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(make, range(24)))

        assert all(r.is_ok for r in results), [
            r.danger_err for r in results if r.is_err
        ]
        ids = [r.danger_ok.id for r in results]
        assert len(ids) == len(set(ids)), f"duplicate id(s) allocated: {ids}"

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert len(loaded.danger_ok) == 24
