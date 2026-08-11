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

import shutil
import threading
from datetime import date
from pathlib import Path

import pytest
from typani.result import Result

import frob.tickets._draft_finalize
import frob.tickets._new_renumber
from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketError,
    TicketKind,
    TicketSpec,
    TicketState,
    archive,
    finalize_draft,
    finalize_draft_for_land,
    load_all,
    new_ticket,
    renumber_one,
)
from frob.tickets._models import RenumberReport
from frob.tickets._provisional import DRAFT_PREFIX
from frob.tickets._store import ledger_lock, write_ticket

# T-1635: this module's races all rendezvous two threads via a short
# Barrier/Event wait before joining them with an equally short timeout.
# Both were originally 5s/10s, tuned for an unloaded machine -- under a
# `pytest-xdist -n auto` full-suite run (a dozen sibling workers'
# processes/threads contending for the same CPUs), plain thread
# scheduling delay alone can push a thread's arrival at the rendezvous
# past a 5s wait, raising `BrokenBarrierError` in the thread body (which
# then silently leaves the `nonlocal` result variable `None`, observed
# failing as `AssertionError: None` rather than a timeout message) even
# though `archive`/`renumber_one`'s locking itself was never at fault.
# Widened to a generous CI-safety margin; still far under anything a
# genuine deadlock in the code under test would need to hide behind.
_CONCURRENCY_TIMEOUT_S = 30


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

        start_gate = threading.Barrier(2, timeout=_CONCURRENCY_TIMEOUT_S)
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
        archive_thread.join(timeout=_CONCURRENCY_TIMEOUT_S)
        new_thread.join(timeout=_CONCURRENCY_TIMEOUT_S)
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

        start_gate = threading.Barrier(2, timeout=_CONCURRENCY_TIMEOUT_S)
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
        renumber_thread.join(timeout=_CONCURRENCY_TIMEOUT_S)
        new_thread.join(timeout=_CONCURRENCY_TIMEOUT_S)
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
                release.wait(timeout=_CONCURRENCY_TIMEOUT_S)
                order.append("holder-exit")

        holder_thread = threading.Thread(target=_holder)
        holder_thread.start()
        assert entered.wait(timeout=_CONCURRENCY_TIMEOUT_S)

        def _waiter() -> None:
            with ledger_lock(tmp_path):
                order.append("waiter-enter")

        waiter_thread = threading.Thread(target=_waiter)
        waiter_thread.start()
        waiter_thread.join(timeout=0.2)
        assert order == ["holder-enter"], "second lock acquisition did not block"

        release.set()
        holder_thread.join(timeout=_CONCURRENCY_TIMEOUT_S)
        waiter_thread.join(timeout=_CONCURRENCY_TIMEOUT_S)
        assert order == ["holder-enter", "holder-exit", "waiter-enter"]


class TestFinalizeDraftAllocationRace:
    """T-1090: two sibling `frob ticket land` calls each renumbering their own
    residue draft (the T-1086-vs-T-0684 field incident, third occurrence
    2026-07-28) must never allocate the SAME final id -- `finalize_draft`'s
    id computation must be atomic with its commit, under one held
    `ledger_lock` span, so a concurrent finalizer always recomputes against
    the fresh post-write ledger rather than a stale pre-write snapshot."""

    def test_two_concurrent_finalize_draft_calls_get_distinct_ids(
        self, tmp_path: Path
    ) -> None:
        """Two draft tickets, finalized from two threads released at the
        same instant (a `Barrier`, forcing genuine interleaving rather than
        an accidental ordering) against the SAME root: both must land
        distinct final ids and both blocks must survive in the ledger --
        neither one's block may vanish or get clobbered by the other's
        allocation."""
        _seed_ticket(tmp_path, ticket_id="T-0050", state=TicketState.QUEUED)
        draft_a = f"{DRAFT_PREFIX}aaaaaaaa"
        draft_b = f"{DRAFT_PREFIX}bbbbbbbb"
        _seed_ticket(tmp_path, ticket_id=draft_a, state=TicketState.DONE)
        _seed_ticket(tmp_path, ticket_id=draft_b, state=TicketState.DONE)

        start_gate = threading.Barrier(2, timeout=_CONCURRENCY_TIMEOUT_S)
        result_a: Result[str, TicketError] | None = None
        result_b: Result[str, TicketError] | None = None

        def _run_a() -> None:
            nonlocal result_a
            start_gate.wait()
            result_a = finalize_draft(tmp_path, draft_a)

        def _run_b() -> None:
            nonlocal result_b
            start_gate.wait()
            result_b = finalize_draft(tmp_path, draft_b)

        thread_a = threading.Thread(target=_run_a)
        thread_b = threading.Thread(target=_run_b)
        thread_a.start()
        thread_b.start()
        thread_a.join(timeout=_CONCURRENCY_TIMEOUT_S)
        thread_b.join(timeout=_CONCURRENCY_TIMEOUT_S)
        assert not thread_a.is_alive()
        assert not thread_b.is_alive()

        assert result_a is not None and result_a.is_ok, (
            result_a.err if result_a is not None else None
        )
        assert result_b is not None and result_b.is_ok, (
            result_b.err if result_b is not None else None
        )
        final_a = result_a.danger_ok
        final_b = result_b.danger_ok

        assert final_a != final_b, (
            "two concurrent finalize_draft calls allocated the SAME final "
            f"id ({final_a!r}) -- one block silently dropped the other"
        )

        active_after = load_all(tmp_path)
        assert active_after.is_ok
        active_map = active_after.danger_ok
        assert final_a in active_map, "draft_a's finalized block did not survive"
        assert final_b in active_map, "draft_b's finalized block did not survive"
        assert draft_a not in active_map
        assert draft_b not in active_map


# frob:ticket T-1669
# frob:tests tests/test_tickets_ledger_concurrency.py::TestPromoteVsLandFinalizeAllocationRace.test_promote_and_land_finalize_never_allocate_the_same_id  # noqa: E501
class TestPromoteVsLandFinalizeAllocationRace:
    """T-1669: `finalize_draft` (the `frob ticket promote` / Tier-A auto-fix
    path, always called against a single `root`) and `finalize_draft_for_land`
    (the `frob ticket land` path, called against a WORKTREE with `root` as
    its separate main-ledger view) are two DIFFERENT call paths that both
    allocate a final `T-####` id. `TestFinalizeDraftAllocationRace` above
    only proves the first path is race-free against ITSELF -- both calls in
    that test share the same `ledger_lock(root)` span. It says nothing
    about the second path, which reads `main_root`'s id ceiling WITHOUT
    holding `main_root`'s `ledger_lock` at all (by design -- see
    `finalize_draft_for_land`'s own docstring for why a worktree cannot
    safely take main's `ledger_lock` across a git-tracked merge).

    This is exactly the failure this drive measured for real (T-1669's own
    body): a draft promoted directly on main via `frob ticket promote`
    (or Tier-A's `fix_tick002_renumber`) racing a concurrent `frob ticket
    land`'s own draft finalization can compute and claim the SAME next id,
    each in its own tree (main vs. the landing worktree) -- so neither
    write itself ever errors, and the collision only ever surfaces later,
    as a squash-time refusal that forces a human/agent to hand-renumber
    (measured twice in one land this session, T-2060 -- ids T-2041 and
    T-2045 each claimed out from under it)."""

    def test_promote_and_land_finalize_never_allocate_the_same_id(
        self, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        """Simulates the exact race: a `finalize_draft` call (promote) is
        paused mid-critical-section (after it has computed its next id but
        before it commits the rename) while a concurrent `finalize_draft_
        for_land` call (land, against a SEPARATE worktree directory reading
        the SAME main root) is given a window to run. Before T-1669's fix
        (wiring `frob.tickets._store.allocator_lock` into both paths), the
        land-side call has no lock forcing it to wait for the paused
        promote call to finish and free the id it already claimed -- it
        reads the same pre-write ceiling and computes the IDENTICAL final
        id. After the fix, the land-side call blocks on `allocator_lock`
        until promote's write completes, then computes the next id fresh."""
        main_root = tmp_path_factory.mktemp("main")
        worktree = tmp_path_factory.mktemp("worktree")

        _seed_ticket(main_root, ticket_id="T-0050", state=TicketState.QUEUED)
        draft_promote = f"{DRAFT_PREFIX}c0ffee01"
        _seed_ticket(main_root, ticket_id=draft_promote, state=TicketState.DONE)

        # worktree starts as a copy of main's ledger, plus its OWN local
        # draft -- exactly the shape a real landing worktree has (its own
        # draft, main's ledger merged in at warm-up).
        shutil.copytree(main_root, worktree, dirs_exist_ok=True)
        draft_land = f"{DRAFT_PREFIX}c0ffee02"
        _seed_ticket(worktree, ticket_id=draft_land, state=TicketState.DONE)

        entered = threading.Event()
        release = threading.Event()
        call_count = {"n": 0}

        real_next_ticket_id = frob.tickets._draft_finalize._next_ticket_id

        def _pausing_next_ticket_id(tickets: dict) -> str:
            call_count["n"] += 1
            computed = real_next_ticket_id(tickets)
            if call_count["n"] == 1:
                # This is the promote call: hold whatever critical section
                # it is inside (locked or not) open long enough for a
                # concurrent, unguarded land-side call to read the SAME
                # pre-write ledger snapshot.
                entered.set()
                release.wait(timeout=_CONCURRENCY_TIMEOUT_S)
            return computed

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            "frob.tickets._draft_finalize._next_ticket_id",
            _pausing_next_ticket_id,
        )
        try:
            result_promote: Result[str, TicketError] | None = None
            result_land: Result[str, TicketError] | None = None

            def _run_promote() -> None:
                nonlocal result_promote
                result_promote = finalize_draft(main_root, draft_promote)

            def _run_land() -> None:
                nonlocal result_land
                result_land = finalize_draft_for_land(
                    worktree, draft_land, main_root
                )

            thread_promote = threading.Thread(target=_run_promote)
            thread_land = threading.Thread(target=_run_land)

            thread_promote.start()
            assert entered.wait(timeout=_CONCURRENCY_TIMEOUT_S), (
                "promote's finalize_draft never reached its id computation"
            )

            thread_land.start()
            # Give the land-side call a real window to run to completion
            # unguarded (pre-fix) while promote is still paused -- plenty
            # of margin over the filesystem-only work either side does.
            thread_land.join(timeout=2.0)
            release.set()

            thread_promote.join(timeout=_CONCURRENCY_TIMEOUT_S)
            thread_land.join(timeout=_CONCURRENCY_TIMEOUT_S)
        finally:
            monkeypatch.undo()

        assert not thread_promote.is_alive()
        assert not thread_land.is_alive()

        assert result_promote is not None and result_promote.is_ok, (
            result_promote.err if result_promote is not None else None
        )
        assert result_land is not None and result_land.is_ok, (
            result_land.err if result_land is not None else None
        )
        final_promote = result_promote.danger_ok
        final_land = result_land.danger_ok

        assert final_promote != final_land, (
            "finalize_draft (promote) and finalize_draft_for_land (land) "
            f"allocated the SAME final id ({final_promote!r}) against the "
            "same main root -- the exact T-2060 collision (T-1669)"
        )


# frob:ticket T-2092
class TestRenumberVsNewTicketAllocationRace:
    """T-2092: `renumber_one` (v2-mode dispatches to `renumber_one_v2`, the
    live default per T-1553) is a THIRD id-allocating call path that T-1669
    never wired into `allocator_lock` -- unlike `finalize_draft`/
    `finalize_draft_for_land`, which share it, `renumber_one_v2` only ever
    took a per-ticket `ticket_lock`, and `new_ticket`'s own allocation only
    ever took `ledger_lock`. Neither lock overlaps the other, so a renumber
    targeting id X and a concurrent `new_ticket` independently allocating
    the SAME id X can both report success, with `new_ticket`'s own
    unconditional `atomic_write` (no existence check) silently clobbering
    whichever one wrote second -- exactly the T-2083/T-2090 field incident
    that silently deleted a whole ticket, reproduced here in one process
    without needing git merge machinery at all: `new_ticket` computing its
    id from a snapshot taken before the renumber's rename lands is enough
    on its own."""

    def test_renumber_and_concurrent_new_ticket_never_allocate_the_same_id(
        self, tmp_path: Path
    ) -> None:
        """Pause `new_ticket`'s id computation (`_allocate_and_check_
        ticket_id`) right after it decides its next id but before it
        writes -- while paused, let a concurrent `renumber_one(old,
        new_id)` targeting that SAME id run to completion. Release
        `new_ticket` to finish writing. Before the fix, `new_ticket`'s
        write goes through unguarded and overwrites the just-renumbered
        ticket's file with its own content -- both operations report
        `Ok`, and the on-disk content for that id ends up being
        `new_ticket`'s, not the renumbered ticket's: a silent, undetected
        loss identical in shape to the T-2083/T-2090 incident. After the
        fix (`allocator_lock` held by both paths), whichever call reaches
        the lock second re-validates against the FRESH post-write state
        and either targets a different id or refuses with `DuplicateId`
        -- never a silent overwrite."""
        _seed_ticket(tmp_path, ticket_id="T-0050", state=TicketState.QUEUED)

        entered = threading.Event()
        release = threading.Event()

        real_allocate = frob.tickets._new_renumber._allocate_and_check_ticket_id

        def _pausing_allocate(root: Path) -> Result[str, TicketError]:
            result = real_allocate(root)
            entered.set()
            release.wait(timeout=_CONCURRENCY_TIMEOUT_S)
            return result

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            "frob.tickets._new_renumber._allocate_and_check_ticket_id",
            _pausing_allocate,
        )
        try:
            new_result: Result[Ticket, TicketError] | None = None
            renumber_result: Result[RenumberReport, TicketError] | None = None

            def _run_new() -> None:
                nonlocal new_result
                new_result = new_ticket(
                    tmp_path,
                    TicketSpec(
                        title="Concurrent new ticket during renumber",
                        kind=TicketKind.BUG,
                        origin=Origin.AGENT,
                    ),
                )

            def _run_renumber() -> None:
                nonlocal renumber_result
                renumber_result = renumber_one(tmp_path, "T-0050", "T-0051")

            thread_new = threading.Thread(target=_run_new)
            thread_new.start()
            assert entered.wait(timeout=_CONCURRENCY_TIMEOUT_S), (
                "new_ticket never reached its id-allocation pause point"
            )

            thread_renumber = threading.Thread(target=_run_renumber)
            thread_renumber.start()
            # Give renumber a real window to run to completion
            # UNGUARDED (pre-fix) while new_ticket is still paused --
            # post-fix it instead blocks acquiring allocator_lock, which
            # this short join simply times out waiting for, harmlessly.
            thread_renumber.join(timeout=2.0)
            release.set()
            thread_renumber.join(timeout=_CONCURRENCY_TIMEOUT_S)
            thread_new.join(timeout=_CONCURRENCY_TIMEOUT_S)
        finally:
            monkeypatch.undo()

        assert not thread_new.is_alive()
        assert not thread_renumber.is_alive()

        assert new_result is not None and new_result.is_ok, (
            new_result.err if new_result is not None else None
        )
        new_id = new_result.danger_ok.id

        # The failure mode this reproduces is not that either call errors --
        # it is that BOTH report Ok while claiming the same id, with one
        # silently overwriting the other's on-disk content. Assert directly
        # against that: if renumber also reports Ok, it must not have
        # landed on the same id `new_ticket` holds, AND the ticket content
        # actually on disk for `new_id` must still be `new_ticket`'s own
        # title, not silently replaced by the renumbered ticket's.
        if renumber_result is not None and renumber_result.is_ok:
            report = renumber_result.danger_ok
            assert report.new_id != new_id, (
                "renumber_one and a concurrent new_ticket both allocated "
                f"id {new_id!r} -- the exact T-2092 silent-collision shape"
            )

        active_after = load_all(tmp_path)
        assert active_after.is_ok
        active_map = active_after.danger_ok
        assert new_id in active_map, "new_ticket's own block did not survive"
        surviving = active_map[new_id]
        assert surviving.title == "Concurrent new ticket during renumber", (
            f"id {new_id!r} on disk holds title {surviving.title!r} -- "
            "new_ticket's write was silently clobbered by the concurrent "
            "renumber, exactly the T-2092/T-2083 incident shape"
        )
