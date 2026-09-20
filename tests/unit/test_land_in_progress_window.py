"""T-3612: `refuse_if_land_in_progress` is scoped to the ledger-splice
critical section, not a land's whole wall-clock duration.

Before this ticket, `refuse_if_land_in_progress` (`frob.tickets._leases`)
probed `land.lock` (plus a T-1619 `/proc` process scan) -- held for a
land's ENTIRE run, precheck through squash-commit, typically 4-45
minutes measured. Every OTHER ledger-writing verb (new/drop/body/scope/
fail/evidence/done-report/accept) shares this one choke point, so a land
in its slow phase (gates, tests) starved every filing verb for that whole
window even though the only step that genuinely races a filing verb's
own write is the land's ledger SPLICE -- a short critical section already
run under `tickets.lock` (`frob.tickets._store.ledger_lock`), the SAME
lock a filing verb's own write acquires.

This module holds down the narrowed contract with two real held-lock
scenarios (a background thread genuinely holding the OS `flock`, not a
monkeypatched stand-in -- `flock` contention is scoped to an open file
DESCRIPTION, not a process, so a second `os.open` + `flock` attempt from
a different thread in this SAME process observes real contention exactly
as a second, different process would):

1. `land.lock` held, `tickets.lock` free (a land's slow phase) -- the
   probe succeeds; the old whole-land check would have refused here.
2. `tickets.lock` held (a land's splice, or any other ledger write) --
   the probe refuses, naming the correlated `land.lock` holder in its
   log line when one exists.
3. A held `tickets.lock` that is released partway through the bounded
   wait -- the probe blocks briefly, then succeeds, never corrupting
   anything (each side only ever taking the SAME lock non-blocking/
   blocking respectively, the existing `flock` single-writer discipline
   this ticket does not touch).

A `land()`-vs-`land()` collision is NOT this module's concern: `land()`
serializes against a second `land()` via `_land_lock` directly (a real
blocking `flock` acquire on `land.lock`), never through `refuse_if_land_
in_progress` at all -- `land`/`merge-driver`/`sweep-async` are dispatch-
layer `_LAND_LOCK_EXEMPT_VERBS` and never call it. `TestSecondLandStill
Refused` below locks THAT existing, untouched mechanism down instead, so
a regression that accidentally routed `land()` through the narrowed
check would still be caught."""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from frob.process._lock import portable_flock_acquire, portable_flock_release
from frob.tickets._land import LandLockTimeout, _land_lock
from frob.tickets._leases import (
    LAND_LOCK_REL,
    TICKETS_LEDGER_LOCK_REL,
    LeaseError,
    refuse_if_land_in_progress,
)


def _write_land_lock_holder_json(root: Path, *, pid: int, ticket_id: str) -> None:
    """Write a `land.lock`-shaped holder record at `root` without
    actually acquiring the lock -- this module's scenarios hold real
    `flock`s directly (see the module docstring) but still want a
    holder record present for the correlation-logging assertions, the
    same split real-lock/recorded-metadata shape `land.lock` itself
    uses (mirrors `frob.tickets._land._land_lock_holder_metadata`'s
    dict shape, written the same way `_land_lock` itself writes it)."""
    path = root / LAND_LOCK_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "pid": pid,
        "session_id": f"pid-{pid}",
        "started_at": datetime.now(UTC).isoformat(),
        "ticket_id": ticket_id,
    }
    path.write_text(json.dumps(metadata) + "\n", encoding="utf-8")


class _HeldLock:
    """A real, held, non-blocking-acquired OS `flock` on `path`, taken on
    a background thread and released on `__exit__` -- the fixture every
    scenario below builds on. Runs in a helper THREAD (not the test's own
    thread) because `flock` contention is scoped to the open file
    description this opens, not to this process, so a second `os.open` +
    `flock` attempt made directly from the test body below (a different
    file description, same or different thread -- either way) observes
    genuine contention."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None

    def __enter__(self) -> "_HeldLock":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self._path), os.O_CREAT | os.O_RDWR, 0o644)
        assert portable_flock_acquire(self._fd, exclusive=True, blocking=True)
        return self

    def release(self) -> None:
        if self._fd is not None:
            portable_flock_release(self._fd)
            os.close(self._fd)
            self._fd = None

    def __exit__(self, *exc: object) -> None:
        self.release()


@pytest.mark.skipif(os.name == "nt", reason="fcntl-backed flock probe, POSIX (T-3612)")
# frob:ticket T-4628
class TestLandInProgressWindowNarrowedToSplice:
    """`refuse_if_land_in_progress`'s new contract: probe `tickets.lock`,
    never `land.lock`, for the refusal decision itself (T-3612)."""

    # frob:ticket T-4628
    def test_land_lock_held_but_tickets_lock_free_allows_the_write(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Asserts a write during a land's slow phase (`land.lock` held
        for the whole run, `tickets.lock` untouched between splices)
        succeeds immediately under the narrowed splice-only check, and
        logs the allowed-during-land write at INFO naming the correlated
        holder's pid. See T-3612 for the design rationale."""
        root = tmp_path
        pid = os.getpid()
        _write_land_lock_holder_json(root, pid=pid, ticket_id="T-9001")
        with caplog.at_level("INFO"), _HeldLock(root / LAND_LOCK_REL):
            result = refuse_if_land_in_progress(root, wait_timeout_s=0.0)
        assert result.is_ok
        assert "write allowed during in-progress land" in caplog.text
        assert str(pid) in caplog.text
        assert "T-9001" in caplog.text

    def test_tickets_lock_held_refuses_naming_the_correlated_land_holder(
        self, tmp_path: Path
    ) -> None:
        """A land's splice (or any other ledger write) holding
        `tickets.lock`: refused, `Err(LeaseError.LandInProgress)` --
        the actual race this ticket keeps closed. `land.lock`'s holder
        record (written independently, matching the real shape where a
        land holds BOTH locks at once during its splice) is available for
        the refusal's best-effort correlation log line."""
        root = tmp_path
        _write_land_lock_holder_json(root, pid=os.getpid(), ticket_id="T-9002")
        with _HeldLock(root / TICKETS_LEDGER_LOCK_REL):
            result = refuse_if_land_in_progress(root, wait_timeout_s=0.0)
        assert result.is_err
        assert result.danger_err is LeaseError.LandInProgress

    def test_tickets_lock_held_with_no_land_lock_at_all_still_refuses(
        self, tmp_path: Path
    ) -> None:
        """`tickets.lock` held by a NON-land ledger write (no `land.lock`
        present at all): still refused -- the splice-window check reads
        `tickets.lock` itself, not `land.lock`'s presence, so a filing
        verb racing a concurrent filing verb's write is caught exactly
        the same as one racing a land's splice."""
        root = tmp_path
        with _HeldLock(root / TICKETS_LEDGER_LOCK_REL):
            result = refuse_if_land_in_progress(root, wait_timeout_s=0.0)
        assert result.is_err
        assert result.danger_err is LeaseError.LandInProgress

    def test_no_lock_held_at_all_allows_the_write(self, tmp_path: Path) -> None:
        """A free repository (no land, no concurrent write): `Ok(None)`,
        matching every caller's behavior before this ticket."""
        root = tmp_path
        result = refuse_if_land_in_progress(root, wait_timeout_s=0.0)
        assert result.is_ok

    def test_tickets_lock_released_partway_through_the_wait_then_succeeds(
        self, tmp_path: Path
    ) -> None:
        """A splice genuinely in flight when the filing verb first probes:
        blocks briefly (this call's own bounded `wait_timeout_s`), the
        splice's `_HeldLock` releases mid-wait, and the SAME call
        succeeds without the caller retrying -- "blocks briefly then
        succeeds", never a hang and never a corrupted ledger (the two
        sides only ever contend on the identical `flock`, never write
        without holding it)."""
        root = tmp_path
        held = _HeldLock(root / TICKETS_LEDGER_LOCK_REL)
        held.__enter__()

        def _release_soon() -> None:
            time.sleep(0.3)
            held.release()

        releaser = threading.Thread(target=_release_soon, daemon=True)
        releaser.start()
        try:
            started = time.monotonic()
            result = refuse_if_land_in_progress(
                root, wait_timeout_s=5.0, poll_interval_s=0.05
            )
            elapsed = time.monotonic() - started
        finally:
            releaser.join(timeout=5.0)
            held.release()  # no-op if already released, idempotent-safe

        assert result.is_ok
        assert elapsed < 5.0, "should succeed well before the wait budget elapses"


@pytest.mark.skipif(os.name == "nt", reason="POSIX flock, T-3612")
class TestSecondLandStillRefused:
    """`land()`-vs-`land()` exclusivity is untouched by this ticket: it
    was never routed through `refuse_if_land_in_progress`, and still
    isn't -- `_land_lock` itself, a real blocking `flock` on `land.lock`,
    is the whole mechanism."""

    def test_second_land_lock_acquire_times_out_while_the_first_holds_it(
        self, tmp_path: Path
    ) -> None:
        """A second `_land_lock(root, ...)` acquire, while a first one
        (a `land()` in progress) still holds `land.lock`, refuses with
        `LandLockTimeout` -- exactly as before T-3612; this ticket never
        touches `_land_lock`/`land()`'s own self-exclusion."""
        root = tmp_path
        with _land_lock(root, "T-9101", timeout=60.0):
            with pytest.raises(LandLockTimeout):
                with _land_lock(root, "T-9102", timeout=0.2):
                    pass  # pragma: no cover -- must never be reached


@pytest.mark.skipif(os.name == "nt", reason="fcntl-backed flock probe, POSIX (T-3612)")
# frob:ticket T-4628
class TestWholeLandVerbClassification:
    """Asserts `whole_land=True` (passed by the dispatch layer for
    `renumber`/`promote`/`archive`/`migrate`, see
    `_LAND_WHOLE_LAND_VERBS`) applies the `land.lock`-duration probe for
    those four verbs, since they rewrite many ticket files across their
    own multi-file transaction with no single `tickets.lock` span
    covering the whole rewrite, while every other verb keeps the
    narrowed splice-only check. See T-4556/T-3612 for the design
    rationale.

    This is this ticket's BUG002 repro: `test_renumber_refused_while_
    only_land_lock_held` fails at the parent commit with a `TypeError`
    (unexpected keyword argument) rather
    than the assertion it makes here -- FAILED_AT_PARENT, not "passed
    but asserted the wrong thing"."""

    def test_renumber_refused_while_only_land_lock_held(self, tmp_path: Path) -> None:
        """A land's slow phase (`land.lock` held, `tickets.lock` free):
        a whole-land-classified verb (`renumber`, standing in for
        `promote`/`archive`/`migrate`, all four routed identically by
        the dispatch layer) is refused -- unlike a splice-only verb,
        which the sibling test below shows succeeds in this exact same
        scenario."""
        root = tmp_path
        _write_land_lock_holder_json(root, pid=os.getpid(), ticket_id="T-9201")
        with _HeldLock(root / LAND_LOCK_REL):
            result = refuse_if_land_in_progress(
                root, wait_timeout_s=0.0, whole_land=True
            )
        assert result.is_err
        assert result.danger_err is LeaseError.LandInProgress

    def test_splice_only_verb_allowed_while_only_land_lock_held(
        self, tmp_path: Path
    ) -> None:
        """The SAME scenario (`land.lock` held, `tickets.lock` free) as
        the sibling test above, but `whole_land=False` (every verb OTHER
        than renumber/promote/archive/migrate, e.g. `evidence`/`body`/
        `scope`): succeeds -- T-3612's narrowed splice-only probe is
        unaffected by this ticket for every verb that does not opt into
        `whole_land=True`."""
        root = tmp_path
        _write_land_lock_holder_json(root, pid=os.getpid(), ticket_id="T-9202")
        with _HeldLock(root / LAND_LOCK_REL):
            result = refuse_if_land_in_progress(
                root, wait_timeout_s=0.0, whole_land=False
            )
        assert result.is_ok


@pytest.mark.skipif(os.name == "nt", reason="fcntl-backed flock probe, POSIX (T-3612)")
class TestDispatchLayerWholeLandClassification:
    """T-4556: the dispatch-layer guard itself
    (`frob.app.ticket_runner._refuse_if_land_in_progress_for_dispatch`)
    routes `renumber`/`promote`/`archive`/`migrate` through
    `whole_land=True` and every other mutating verb through the
    unchanged splice-only check -- exercised end to end here (not just
    at the `refuse_if_land_in_progress` unit level above) so a future
    change to `_LAND_WHOLE_LAND_VERBS` or its wiring is caught even if
    it never touches the lower-level function's own tests.

    Monkeypatches `frob.tickets._leases.refuse_if_land_in_progress`
    itself (the dispatch guard's own local import re-reads this module
    attribute on every call, so patching it here is observed) purely to
    force `wait_timeout_s=0.0` -- the dispatch guard never exposes that
    parameter itself, and calling it unpatched would wait out the real,
    multi-second-to-minutes T-1961 wait budget before refusing, exactly
    as it must in production. The real, un-mocked `refuse_if_land_in_
    progress` behavior for both `whole_land` values is already locked
    down by `TestWholeLandVerbClassification` above; this class checks
    only that the dispatch layer passes the RIGHT `whole_land` value for
    the RIGHT verb."""

    @staticmethod
    def _force_zero_wait(monkeypatch: pytest.MonkeyPatch) -> None:
        """Shared setup for both tests below: pins `wait_timeout_s=0.0`
        on every `refuse_if_land_in_progress` call the dispatch guard
        makes, so a genuine refusal returns immediately instead of
        idling through the real T-1961 wait budget."""
        import frob.tickets._leases as leases_module

        real = leases_module.refuse_if_land_in_progress

        def _zero_wait(root: Path, *, whole_land: bool = False) -> object:
            return real(root, wait_timeout_s=0.0, whole_land=whole_land)

        monkeypatch.setattr(leases_module, "refuse_if_land_in_progress", _zero_wait)

    def test_renumber_exits_while_only_land_lock_held(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`renumber`, dispatched through the real pre-dispatch guard,
        with only `land.lock` held (`tickets.lock` free): refused via
        `sys.exit(1)`, matching every other mutating verb's refusal
        shape in this module."""
        from frob.app.ticket_runner import _refuse_if_land_in_progress_for_dispatch

        self._force_zero_wait(monkeypatch)
        root = tmp_path
        _write_land_lock_holder_json(root, pid=os.getpid(), ticket_id="T-9301")
        with _HeldLock(root / LAND_LOCK_REL):
            with pytest.raises(SystemExit) as exc_info:
                _refuse_if_land_in_progress_for_dispatch(root, "renumber")
        assert exc_info.value.code == 1

    def test_evidence_proceeds_while_only_land_lock_held(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`evidence` (a splice-only verb, unclassified as whole-land):
        proceeds without exiting in the exact same scenario the sibling
        test above refuses -- the classification is per-verb, not
        global."""
        from frob.app.ticket_runner import _refuse_if_land_in_progress_for_dispatch

        self._force_zero_wait(monkeypatch)
        root = tmp_path
        _write_land_lock_holder_json(root, pid=os.getpid(), ticket_id="T-9302")
        with _HeldLock(root / LAND_LOCK_REL):
            _refuse_if_land_in_progress_for_dispatch(root, "evidence")
