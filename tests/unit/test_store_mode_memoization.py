"""T-4649: `_store_mode` memoization -- regression tests for the
quadratic re-glob defect (`src/frob/tickets/_store.py::_store_mode` re-globbed
the whole `tickets/` tree, active AND archive, on EVERY call with no caching;
`doable()`/`read_all_leases()` called it once per lease per candidate ticket,
O(tickets x leases), minutes on this repo's own 1000+-ticket live ledger under
fleet load). Kept in its own file rather than `tests/unit/test_ticket_store.py`
because that file is under a live cross-ticket lease (T-4632) at the time this
fix landed.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
from frob.tickets._store import _serialize_ticket, _store_mode


def _ticket(ticket_id: str = "T-0001", title: str = "Sample ticket") -> Ticket:
    """Minimal valid `Ticket` fixture, mirroring `test_ticket_store.py`'s
    own `_ticket` helper (duplicated here rather than imported, since that
    module is under a live cross-ticket lease at the time of this fix)."""
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


class TestStoreModeMemo:
    """Positive-control tests: each plants a mutation the cache MUST detect
    (a fresh ticket dir appearing, or a different root), not just a
    "second call returns the same answer" timing assertion that a broken
    cache (e.g. one that never invalidates) would also pass."""

    def test_memoized(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests src/frob/tickets/_store.py::_store_mode kind="unit"
        d = tmp_path / "tickets"
        d.mkdir()
        (d / "T-0001-x.md").write_text(_serialize_ticket(_ticket()))
        assert _store_mode(tmp_path) == "dir"

        calls = {"n": 0}
        real_glob = Path.glob

        def _counting_glob(self: Path, pattern: str) -> object:
            calls["n"] += 1
            return real_glob(self, pattern)

        monkeypatch.setattr(Path, "glob", _counting_glob)
        for _ in range(5):
            assert _store_mode(tmp_path) == "dir"
        # a cache hit does not re-glob at all: no directory mtime changed
        # between calls, so every one of these 5 calls after the first
        # (already-warm) call is served from `_store_mode_cache` alone.
        assert calls["n"] == 0

    # frob:tests src/frob/tickets/_store.py::_store_mode_cache_signal
    def test_invalidates_new(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::_store_mode kind="unit"
        # positive control: plant a v2 ticket AFTER the first (cached) call
        # and confirm _store_mode's answer flips from "single" to "v2" --
        # proves the mtime-keyed cache actually invalidates on a real
        # ledger change, not just that it returns a stale answer fast.
        (tmp_path / "tickets.md").write_text("# Tickets\n")
        assert _store_mode(tmp_path) == "single"

        ticket_dir = tmp_path / "tickets" / "T-0042"
        ticket_dir.mkdir(parents=True)
        (ticket_dir / "ticket.md").write_text(_serialize_ticket(_ticket("T-0042")))
        assert _store_mode(tmp_path) == "v2"

    def test_store_mode_cache_invalidates_on_archive(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::_store_mode kind="unit"
        # T-1256's all-archived-still-reads-as-v2 rule, exercised through the
        # cache: archiving the only active ticket touches tickets/archive/'s
        # own mtime, which the cache signal must pick up.
        active_dir = tmp_path / "tickets" / "T-0001"
        active_dir.mkdir(parents=True)
        (active_dir / "ticket.md").write_text(_serialize_ticket(_ticket()))
        assert _store_mode(tmp_path) == "v2"

        archive_dir = tmp_path / "tickets" / "archive" / "T-0001"
        archive_dir.mkdir(parents=True)
        (archive_dir / "ticket.md").write_text(_serialize_ticket(_ticket()))
        (active_dir / "ticket.md").unlink()
        active_dir.rmdir()
        assert _store_mode(tmp_path) == "v2"

    def test_store_mode_cache_is_per_root(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_store.py::_store_mode kind="unit"
        root_a = tmp_path / "a"
        root_b = tmp_path / "b"
        (root_a / "tickets").mkdir(parents=True)
        (root_b / "tickets").mkdir(parents=True)
        (root_a / "tickets" / "T-0001-x.md").write_text(_serialize_ticket(_ticket()))
        (root_b / "tickets.md").write_text("# Tickets\n")
        assert _store_mode(root_a) == "dir"
        assert _store_mode(root_b) == "single"
