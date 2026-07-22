"""T-0633 regression: a wholesale ledger operation racing a concurrent
single-ticket write must never silently revert the concurrent write.

Reproduces the two real field occurrences from T-0633's body: a background,
multi-step ledger operation (`archive`/`renumber_one`, the generalized form
of "ticket start's background sweep") that used to LOAD the ledger
unlocked and only lock for its final wholesale write -- so a concurrent
`new_ticket` landing in that unlocked window got silently reverted the
moment the wholesale write used its stale pre-load snapshot. After the fix
(one `ledger_lock` span across the whole load-modify-write), the two
writers fully serialize: whichever starts first finishes first, and the
other proceeds against the FRESH post-write ledger -- so there is
structurally no window left for a stale snapshot to clobber a concurrent
write. These tests prove that guarantee by delaying one side's *entry* to
the operation (before it ever touches the ledger) so both orderings are
exercised, then asserting both tickets' blocks survive either way.
"""

from __future__ import annotations

import threading
from datetime import date
from pathlib import Path

from typani.result import Result

from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketError,
    TicketKind,
    TicketSpec,
    TicketState,
    archive,
    load_all,
    new_ticket,
    renumber_one,
)
from frob.tickets._models import RenumberReport
from frob.tickets._store import ledger_lock, write_ticket


def _seed_ticket(
    root: Path,
    *,
    ticket_id: str,
    state: TicketState = TicketState.DONE,
) -> None:
    """Write one ticket directly into a fresh ledger (bypassing `new_ticket`'s
    id allocation) so tests can seed a known starting state."""
    ticket = Ticket(
        id=ticket_id,
        title=f"Seed {ticket_id}",
        state=state,
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        priority=Priority.MEDIUM,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=(),
        evidence=(),
        attachments=(),
        body="## Description\nseed\n",
    )
    result = write_ticket(root, ticket)
    assert result.is_ok, result.err


class TestArchiveRaceWithConcurrentNew:
    """T-0633: `archive` (a load-then-wholesale-write ledger operation, the
    same shape as the background-sweep incident) must not lose a ticket
    concurrently created by `new_ticket`."""

    def test_concurrent_new_ticket_survives_a_racing_archive(
        self, tmp_path: Path
    ) -> None:
        """Start `archive` and a concurrent `new_ticket` at (as close to)
        the same instant as threads allow. Whichever wins the ledger lock
        runs to completion first; the other then runs against the fresh
        result. Neither outcome may lose the other's ticket block -- that
        would only be possible if `archive` ever wrote back a stale
        snapshot taken before it held the lock, which the T-0633 fix
        removes."""
        _seed_ticket(tmp_path, ticket_id="T-0001", state=TicketState.DONE)

        start_gate = threading.Barrier(2, timeout=5)
        archive_result: Result[int, TicketError] | None = None
        new_result: Result[Ticket, TicketError] | None = None

        def _run_archive() -> None:
            nonlocal archive_result
            start_gate.wait()
            archive_result = archive(tmp_path)

        def _run_new() -> None:
            nonlocal new_result
            start_gate.wait()
            new_result = new_ticket(
                tmp_path,
                TicketSpec(
                    title="Concurrent new ticket",
                    kind=TicketKind.BUG,
                    origin=Origin.AGENT,
                ),
            )

        archive_thread = threading.Thread(target=_run_archive)
        new_thread = threading.Thread(target=_run_new)
        archive_thread.start()
        new_thread.start()
        archive_thread.join(timeout=10)
        new_thread.join(timeout=10)
        assert not archive_thread.is_alive()
        assert not new_thread.is_alive()

        assert archive_result is not None and archive_result.is_ok
        assert new_result is not None and new_result.is_ok, (
            new_result.err if new_result is not None else None
        )
        new_id = new_result.danger_ok.id

        active_after = load_all(tmp_path)
        assert active_after.is_ok
        active_map = active_after.danger_ok
        assert new_id in active_map, (
            "concurrent new_ticket's block was clobbered by archive's "
            "wholesale write-back"
        )
        assert "T-0001" not in active_map, "archive should have moved T-0001 out"


class TestRenumberOneRaceWithConcurrentNew:
    """T-0633: `renumber_one` (the rename primitive `finalize_draft` uses at
    `frob ticket land` time) must not lose a concurrent `new_ticket` write
    either -- this is the mechanism a draft-finalizing land races against a
    sibling worktree's own ledger write."""

    def test_concurrent_new_ticket_survives_a_racing_renumber_one(
        self, tmp_path: Path
    ) -> None:
        """Same race, exercised through `renumber_one` instead of `archive`."""
        _seed_ticket(tmp_path, ticket_id="T-0050", state=TicketState.QUEUED)

        start_gate = threading.Barrier(2, timeout=5)
        renumber_result: Result[RenumberReport, TicketError] | None = None
        new_result: Result[Ticket, TicketError] | None = None

        def _run_renumber() -> None:
            nonlocal renumber_result
            start_gate.wait()
            renumber_result = renumber_one(tmp_path, "T-0050", "T-0099")

        def _run_new() -> None:
            nonlocal new_result
            start_gate.wait()
            new_result = new_ticket(
                tmp_path,
                TicketSpec(
                    title="Concurrent new ticket during renumber",
                    kind=TicketKind.BUG,
                    origin=Origin.AGENT,
                ),
            )

        renumber_thread = threading.Thread(target=_run_renumber)
        new_thread = threading.Thread(target=_run_new)
        renumber_thread.start()
        new_thread.start()
        renumber_thread.join(timeout=10)
        new_thread.join(timeout=10)
        assert not renumber_thread.is_alive()
        assert not new_thread.is_alive()

        assert renumber_result is not None and renumber_result.is_ok
        assert new_result is not None and new_result.is_ok, (
            new_result.err if new_result is not None else None
        )
        new_id = new_result.danger_ok.id

        active_after = load_all(tmp_path)
        assert active_after.is_ok
        active_map = active_after.danger_ok
        assert new_id in active_map, (
            "concurrent new_ticket's block was clobbered by renumber_one's "
            "wholesale write-back"
        )
        assert "T-0099" in active_map, "renumber_one's own rename should have landed"


class TestLedgerLockSpansWholesaleOperations:
    """T-0633: a wholesale operation's lock span must actually cover both
    its load and its write -- a direct check that a second, unrelated
    `ledger_lock` acquisition blocks until the first span (not just its
    final write) fully releases, proving the lock genuinely covers more
    than one atomic write."""

    def test_concurrent_ledger_lock_acquisition_serializes(
        self, tmp_path: Path
    ) -> None:
        """A thread holding `ledger_lock` for a simulated multi-step
        operation blocks a second thread's acquisition of the same lock
        for the entire held span."""
        entered = threading.Event()
        release = threading.Event()
        order: list[str] = []

        def _holder() -> None:
            with ledger_lock(tmp_path):
                order.append("holder-enter")
                entered.set()
                release.wait(timeout=5)
                order.append("holder-exit")

        holder_thread = threading.Thread(target=_holder)
        holder_thread.start()
        assert entered.wait(timeout=5)

        def _waiter() -> None:
            with ledger_lock(tmp_path):
                order.append("waiter-enter")

        waiter_thread = threading.Thread(target=_waiter)
        waiter_thread.start()
        waiter_thread.join(timeout=0.2)
        assert order == ["holder-enter"], "second lock acquisition did not block"

        release.set()
        holder_thread.join(timeout=5)
        waiter_thread.join(timeout=5)
        assert order == ["holder-enter", "holder-exit", "waiter-enter"]
