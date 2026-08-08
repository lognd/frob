"""Shared test fixtures for `tests/unit/verify/**` (T-1689): a minimal
`SymbolRecord`/`VerifyQueueEntry` builder pair every `frob.verify.*` test
module needs to construct a synthetic `GraphSnapshot`/queue batch --
factored out here so `test_attribution.py`'s and `test_selection.py`'s
copies do not silently drift apart (DUP001)."""

from __future__ import annotations

from frob.graph import Digests, SymbolId, SymbolRecord
from frob.lang import SymbolKind
from frob.verify._watermark import VerifyQueueEntry


def make_symbol(path: str, qualname: str, start: int, end: int) -> SymbolRecord:
    """A minimal public `FUNCTION` `SymbolRecord` at `path::qualname`,
    spanning lines `[start, end]` -- the shape every `frob.verify.*`
    test's synthetic `GraphSnapshot` needs, with placeholder digests
    (never compared against real source, only presence/span matter)."""
    return SymbolRecord(
        id=SymbolId(path=path, qualname=qualname),
        kind=SymbolKind.FUNCTION,
        public=True,
        digests=Digests(sig="s", body="b", doc="d"),
        span=(start, end),
    )


def make_queue_entry(
    commit: str, ticket: str, touched: tuple[str, ...]
) -> VerifyQueueEntry:
    """A minimal `VerifyQueueEntry` for `commit`/`ticket` touching
    `touched` -- the shape every batch-of-entries test in this directory
    builds repeatedly."""
    return VerifyQueueEntry(
        commit_sha=commit,
        ticket_id=ticket,
        touched_symbols=touched,
        enqueued_at="2026-08-08T00:00:00+00:00",
        profile="rapid",
    )
