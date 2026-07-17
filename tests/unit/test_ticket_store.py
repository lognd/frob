"""Direct unit tests for frob.tickets._store's backend-agnostic storage helpers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.tickets._models import Origin, Ticket, TicketError, TicketKind, TicketState
from frob.tickets._store import (
    atomic_write,
    attachments_dir,
    ledger_path,
    load_all,
    migrate_to_ledger,
    parse_ticket_file,
    serialize_ticket,
    slugify,
    store_mode,
    tickets_dir,
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
        # frob:tests src/frob/tickets/_store.py::store_mode kind="unit"
        assert store_mode(tmp_path) == "single"

    def test_ledger_present_is_single(self, tmp_path: Path) -> None:
        (tmp_path / "tickets.md").write_text("# Tickets\n")
        assert store_mode(tmp_path) == "single"

    def test_only_legacy_dir_files_is_dir(self, tmp_path: Path) -> None:
        d = tmp_path / "tickets"
        d.mkdir()
        (d / "T-0001-x.md").write_text(serialize_ticket(_ticket()))
        assert store_mode(tmp_path) == "dir"


class TestSerializeAndParse:
    def test_round_trip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::serialize_ticket kind="unit"
        # frob:tests src/frob/tickets/_store.py::parse_ticket_file kind="unit"
        ticket = _ticket()
        text = serialize_ticket(ticket)
        path = tmp_path / "T-0001-sample-ticket.md"
        path.write_text(text, encoding="utf-8")

        result = parse_ticket_file(path)
        assert result.is_ok
        assert result.danger_ok == ticket

    def test_malformed_file_is_err(self, tmp_path: Path) -> None:
        path = tmp_path / "T-0001-bad.md"
        path.write_text("not frontmatter at all\n")
        result = parse_ticket_file(path)
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


class TestMigrateToLedger:
    def test_moves_legacy_files_into_ledger(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::migrate_to_ledger kind="unit"
        d = tmp_path / "tickets"
        d.mkdir()
        ticket = _ticket()
        legacy_path = d / "T-0001-sample-ticket.md"
        legacy_path.write_text(serialize_ticket(ticket), encoding="utf-8")

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
