"""Tests for frob.app.ticket_runner._lifecycle's `_block`/`_unblock` CLI pair
(T-2681)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._lifecycle import _block, _unblock
from frob.tickets import Origin, Ticket, TicketKind, TicketState, load_queue
from frob.tickets._store import _serialize_ticket


def _ticket(
    *,
    ticket_id: str = "T-0001",
    blocked_by: tuple[str, ...] = (),
) -> Ticket:
    """A minimal QUEUED ticket, same shape `tests/test_tickets.py::_ticket`
    already established -- kept as a small local copy rather than a
    cross-module import since this file's own declared scope (T-2681) does
    not cover `tests/test_tickets.py`."""
    return Ticket(
        id=ticket_id,
        title="Sample ticket",
        state=TicketState.QUEUED,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=blocked_by,
        parent=None,
        scope=(),
        evidence=(),
        attachments=(),
        body="## Description\nsomething\n",
    )


def _write(root: Path, ticket: Ticket, slug: str = "sample-ticket") -> Path:
    """Same flat-file-under-`tickets/` write shape
    `tests/test_tickets.py::_write` uses -- `load_queue`/`_load_one`
    auto-detect this store layout."""
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    path = tickets_dir / f"{ticket.id}-{slug}.md"
    path.write_text(_serialize_ticket(ticket), encoding="utf-8")
    return path


# frob:ticket T-2681
class TestUnblock:
    """`frob ticket unblock <id> --by <blocker>` -- the missing inverse of
    `frob ticket block`. Mirrors `TestBlock`'s own coverage shape one test
    at a time: a real removal, the not-currently-blocked refusal (the
    membership-check mirror of `_block`'s duplicate-append refusal), and
    the malformed-`--by` refusal `_block` already carries."""

    # frob:ticket T-2681
    def test_unblock_removes_edge(self, tmp_path: Path) -> None:
        """The real-world case (T-2076/T-1599): a genuinely obsolete
        `blocked_by` edge is cleared through the CLI, no store-API
        hand-rolling required. A second, untouched blocker on the same
        ticket survives -- `unblock` removes exactly the named edge, not
        the whole `blocked_by` tuple."""
        _write(tmp_path, _ticket(blocked_by=("T-0002", "T-0003")))
        cfg = AppConfig(
            ticket_command="unblock", ticket_id="T-0001", ticket_by="T-0002"
        )
        _unblock(tmp_path, cfg)
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].blocked_by == ("T-0003",)

    # frob:ticket T-2681
    def test_unblock_refuses_when_not_present(self, tmp_path: Path) -> None:
        """MUST-FAIL POSITIVE CONTROL: `--by` naming a ticket that is NOT
        currently in `blocked_by` refuses loudly (SystemExit(1)) rather
        than silently no-op-ing -- the inverted mirror of `_block`'s own
        T-2216 duplicate-append refusal. `blocked_by` is left byte-for-
        byte untouched."""
        _write(tmp_path, _ticket(blocked_by=("T-0003",)))
        cfg = AppConfig(
            ticket_command="unblock", ticket_id="T-0001", ticket_by="T-0002"
        )
        with pytest.raises(SystemExit) as exc_info:
            _unblock(tmp_path, cfg)
        assert exc_info.value.code == 1
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].blocked_by == ("T-0003",)

    # frob:ticket T-2681
    def test_unblock_refuses_invalid_ref(self, tmp_path: Path) -> None:
        """MUST-FAIL POSITIVE CONTROL: a malformed `--by` (not a `T-####`/
        `T-draft-<hex>` ref) refuses before ever touching the ledger --
        the same `is_valid_ticket_ref` guard `_block` applies on its own
        `--by`, now applied symmetrically on the removal path."""
        _write(tmp_path, _ticket(blocked_by=("T-0002",)))
        cfg = AppConfig(
            ticket_command="unblock", ticket_id="T-0001", ticket_by="not-a-ref"
        )
        with pytest.raises(SystemExit) as exc_info:
            _unblock(tmp_path, cfg)
        assert exc_info.value.code == 1
        queue = load_queue(tmp_path).danger_ok
        assert queue.tickets["T-0001"].blocked_by == ("T-0002",)


# frob:ticket T-2681
class TestBlockThenUnblockRoundTrip:
    """`_block` then `_unblock` on the SAME edge round-trips back to the
    starting `blocked_by` -- the two CLI verbs are genuine inverses, not
    just independently-correct in isolation."""

    # frob:ticket T-2681
    def test_block_then_unblock_round_trips(self, tmp_path: Path) -> None:
        _write(tmp_path, _ticket(blocked_by=()))
        block_cfg = AppConfig(
            ticket_command="block", ticket_id="T-0001", ticket_by="T-0002"
        )
        _block(tmp_path, block_cfg)
        after_block = load_queue(tmp_path).danger_ok
        assert after_block.tickets["T-0001"].blocked_by == ("T-0002",)

        unblock_cfg = AppConfig(
            ticket_command="unblock", ticket_id="T-0001", ticket_by="T-0002"
        )
        _unblock(tmp_path, unblock_cfg)
        after_unblock = load_queue(tmp_path).danger_ok
        assert after_unblock.tickets["T-0001"].blocked_by == ()
