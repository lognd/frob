"""Test-fixture-only `write_ticket` escape hatch (T-1711 relocation).

`frob.tickets._store._write_ticket_unchecked` used to live in `src/` even
though it has (and by design must always have) zero production callers --
it exists purely for test fixtures that deliberately construct a "poorer"
ticket snapshot to exercise `splice_ledger`'s own merge-preference logic
(T-1637/T-1679's content-loss guard). That put it in `src/`'s WIRE001/
WIRE002 accountability net for no real benefit: every waiver needed a
`follow_up="T-####"` ticket that would re-orphan the moment it closed
(the exact WIRE002 churn class T-1592's `permanent="true"` test-tree
exemption exists to end, see `frob.gates._wire._wire002_is_permanent_
test_helper_waiver`). Moving the primitive here, under `tests/`, makes
that exemption apply directly: a private (`_`-prefixed) symbol in a
`tests/`-tree file needs no follow-up ticket, because "no production
caller" is the intended, permanent design here, not a pending TODO.
"""

from __future__ import annotations

from pathlib import Path

from typani.result import Result

from frob.tickets._models import Ticket, TicketError
from frob.tickets._store import _write_ticket_impl


# frob:ticket T-1711
# frob:tests tests/unit/test_ticket_store.py::TestWriteTicketUnchecked.test_skips_the_content_loss_guard_entirely  # noqa: E501
def _write_ticket_unchecked(root: Path, ticket: Ticket) -> Result[None, TicketError]:
    """`write_ticket` with the T-1637/T-1679 content-loss guard skipped
    ENTIRELY -- not even the warn-only degrade, no log line at all. The
    explicit, self-documenting escape hatch T-1679 introduced so a genuine
    "construct a deliberately poorer ticket snapshot" caller (test fixtures
    simulating a stale/regressed ledger side for `splice_ledger`'s own
    merge-preference tests -- the concrete case that made a hard-refuse-by-
    default break real, correct code before this primitive existed) says so
    plainly at the call site, instead of `write_ticket` itself needing a
    weaker default to accommodate it. NEVER call this from a production
    write path -- every real caller wants `write_ticket`'s guard, strict or
    not; this is a test-fixture-only primitive, leading underscore and
    all. (T-1711: relocated here from `frob.tickets._store` -- it needs
    `_write_ticket_impl`, the private mode-dispatched write `write_ticket`
    itself performs after its own guard passes, which this module imports
    directly.)"""
    return _write_ticket_impl(root, ticket)
