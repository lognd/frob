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
    closed_ticket_ids,
    new_ticket,
    replay_evidence_from_done_report,
    set_done_report,
    transition,
)
from frob.tickets._models import (
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
    slugify,
    tickets_dir,
    write_archive,
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


class TestStoreMode:
    def test_fresh_repo_defaults_to_single(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::_store_mode kind="unit"
        assert _store_mode(tmp_path) == "single"

    def test_ledger_present_is_single(self, tmp_path: Path) -> None:
        (tmp_path / "tickets.md").write_text("# Tickets\n")
        assert _store_mode(tmp_path) == "single"

    def test_only_legacy_dir_files_is_dir(self, tmp_path: Path) -> None:
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
