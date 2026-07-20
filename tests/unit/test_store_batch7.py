"""Direct-call coverage for `src/frob/tickets/_store.py`'s remaining
symbol-branch waivers on `migrate_to_ledger` and `atomic_write` (T-0160
batch 7): pushing both past the 90% branch floor so their `frob:waive
TEST005` directives can be removed.

`migrate_to_ledger`'s two uncovered branches were the `atomic_write`-fails
propagation path and the per-file `OSError` during cleanup unlink (warned,
not fatal). `atomic_write`'s were the bytes-content write mode and the
nested `os.unlink` failure inside its own `except OSError` handler.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from typani import Err

from frob.tickets._models import Origin, Ticket, TicketError, TicketKind, TicketState
from frob.tickets._store import _serialize_ticket, atomic_write, migrate_to_ledger


def _base_ticket(ticket_id: str = "T-0001") -> Ticket:
    """A minimal valid `Ticket` for round-tripping through the store."""
    return Ticket(
        id=ticket_id,
        title="a ticket",
        kind=TicketKind.FEATURE,
        state=TicketState.QUEUED,
        origin=Origin.HUMAN,
        created=dt.date(2026, 7, 17),
        body="body text",
    )


class TestMigrateToLedger:
    def test_atomic_write_failure_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`migrate_to_ledger` must return the `atomic_write` Err unchanged,
        not swallow it and report a bogus success count."""
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        (tickets_dir / "T-0001-a.md").write_text(
            _serialize_ticket(_base_ticket("T-0001")), encoding="utf-8"
        )

        import frob.tickets._store as store_mod

        monkeypatch.setattr(
            store_mod, "atomic_write", lambda *a, **k: Err(TicketError.WriteFailed)
        )
        result = migrate_to_ledger(tmp_path)
        assert result.is_err
        assert result.danger_err is TicketError.WriteFailed
        # The source file must survive an aborted migration.
        assert (tickets_dir / "T-0001-a.md").exists()

    def test_source_unlink_failure_is_warned_not_fatal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """A source `tickets/*.md` file that cannot be removed after a
        successful ledger write logs a warning but does not fail the
        migration -- the ledger write already succeeded and is the
        source of truth going forward."""
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        target = tickets_dir / "T-0001-a.md"
        target.write_text(_serialize_ticket(_base_ticket("T-0001")), encoding="utf-8")

        import frob.tickets._store as store_mod

        real_unlink = Path.unlink

        def _boom_unlink(self: Path, *a, **k):  # noqa: ANN002, ANN003, ANN202
            if self == target:
                raise OSError("permission denied")
            return real_unlink(self, *a, **k)

        monkeypatch.setattr(store_mod.Path, "unlink", _boom_unlink)
        with caplog.at_level("WARNING"):
            result = migrate_to_ledger(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 1
        assert "could not remove migrated" in caplog.text
        assert (tmp_path / "tickets.md").exists()


class TestAtomicWrite:
    def test_bytes_content_write_mode(self, tmp_path: Path) -> None:
        """`content` may be raw bytes (e.g. binary attachments) -- the
        write mode/encoding selection must branch on that, not assume text."""
        target = tmp_path / "img.bin"
        result = atomic_write(target, b"\x89PNG\r\n\x1a\n")
        assert result.is_ok
        assert target.read_bytes() == b"\x89PNG\r\n\x1a\n"

    def test_nested_unlink_failure_after_write_error_is_swallowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When both the primary write (`os.replace`) AND the cleanup
        `os.unlink` of the temp file fail, the second failure must not mask
        the original `WriteFailed` Err (the inner `except OSError: pass`)."""
        import frob.tickets._store as store_mod

        def _boom_replace(*_a, **_kw):  # noqa: ANN002, ANN003, ANN202
            raise OSError("disk full")

        def _boom_unlink(*_a, **_kw):  # noqa: ANN002, ANN003, ANN202
            raise OSError("temp file already gone")

        monkeypatch.setattr(store_mod.os, "replace", _boom_replace)
        monkeypatch.setattr(store_mod.os, "unlink", _boom_unlink)
        result = atomic_write(tmp_path / "x.txt", "content")
        assert result.is_err
        assert result.danger_err is TicketError.WriteFailed
