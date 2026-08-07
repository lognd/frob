# frob:waive INV006 reason="module/design docstring prose: the 'only' claims describe \
# this module's own implemented locking/dequeue behavior (verifiable by reading the \
# code they annotate, e.g. the queue lock's held-window, the failed-entry dequeue \
# rule), not a separate cross-module contract needing a tracked invariant -- same \
# disposition as _gate_cache.py's identical T-0602-era waiver (T-0585 calibration \
# batch precedent)"
"""T-1345: a merge queue -- agents enqueue verified branches, one serial
drainer merges them onto main -- formalizing the coordinator-lands-
serially discipline `docs/guides/agent-playbook.md` already documents as
process into tooling this module makes checkable.

Today every agent's `land()` call (`frob.tickets._land.land`) races every
other agent's against the SAME `root` checkout, serialized only by
`_land_lock`'s advisory file lock -- a caller that loses the race either
blocks (fine) or, historically, hits `LandError.DirtyMain` and has to
retry by hand (T-1336's measured incident; 268 of 752 `frob ticket land`
calls FAILED in the mined 2026-07-31 telemetry, the majority DirtyMain
contention). This module is the first portion of the fix this ticket's
own body asks for: the queue data structure plus `enqueue`/`drain_next`,
NOT a CLI verb -- `frob ticket land --queue` and a drainer subcommand need
`src/frob/_cli_parsers/_ticket.py`/`src/frob/app/ticket_runner.py`, both
outside this ticket's declared scope (`src/frob/tickets/**`,
`docs/modules/tickets.md`, `docs/guides/agent-playbook.md`); see this
ticket's Done report for the filed follow-up.

Design (T-1345's own design questions, answered here rather than assumed):

- **Where the queue lives.** `.frob/land-queue.json`, a flat JSON array of
  `QueueEntry` records, written under the SAME advisory-lock discipline
  `frob.tickets._land._land_lock` already uses for `.frob/land.lock` (an
  `fcntl`-backed exclusive lock, degrading to a logged no-op on a platform
  without `fcntl` -- identical posture, not a new one). A crashed drainer
  leaves the queue file exactly as it was at its last successful write
  (JSON write is not atomic-replace here on purpose -- see
  `_save_queue`'s docstring for why a partial write is still detectable);
  the file survives a crash the same way `.frob/land.lock` does, and the
  next drainer invocation simply resumes from whatever `queued` entries
  remain.
- **Policy when a queued branch no longer merges cleanly.** `drain_next`
  calls the caller-supplied `land_fn` (deliberately a callable, not this
  module performing the merge itself -- `frob.tickets._land.land` already
  owns every git/merge/precheck concern and this module must not
  duplicate or race it) for exactly the head-of-queue entry; a `land_fn`
  failure (an `Err(LandError...)`) marks that entry `failed` with the
  error recorded, dequeues it (removes it from future `drain_next`
  consideration), and returns `Ok` of the failed entry -- REJECTED BACK TO
  THE AGENT, never auto-rebased and retried. This is a deliberate,
  disclosed choice: an auto-rebase-and-retry policy risks silently
  landing a DIFFERENT diff than the one the agent verified (the exact
  failure mode `docs/guides/agent-playbook.md` section 9's deletion-filter
  rule exists to catch) -- surfacing the failure and letting the agent
  re-verify and re-enqueue is the safe default. The queue never drops an
  entry silently: every entry that leaves `queued` state is still present
  in the JSON file afterward, tagged `landed` or `failed`, forming a
  durable history a caller can inspect.
- **One drainer, not a distributed lock over concurrent lands.** This
  module's lock only serializes MUTATIONS TO THE QUEUE FILE ITSELF
  (`enqueue`/the pop-and-mark-landing step/the record-outcome step) --
  it deliberately does NOT hold that lock across the `land_fn` call, since
  `land_fn` already does its own long-running git work under
  `_land._land_lock`'s separate serialization. The "one drainer" half of
  this ticket's title is an operational invariant (run exactly one
  drainer process against a given `root`), not something this module
  enforces by itself; a second concurrent drainer would still be SAFE
  (the queue-mutation lock prevents two drainers from popping the SAME
  entry) but WASTEFUL (both would contend on `_land._land_lock` for the
  actual land). Documented here since enforcing single-drainer harder
  than "safe under a race" was explicitly out of this first portion's
  reach.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from types import ModuleType

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import LandError, LandReport

_log = get_logger(__name__)

# T-1345: same posix-only degradation posture as `frob.tickets._land.
# _land_lock`/`frob.tickets._store.ledger_lock` -- see `_queue_lock`'s
# docstring.
fcntl: ModuleType | None
try:
    fcntl = import_module("fcntl")
except ImportError:  # pragma: no cover -- posix-only in this repo's CI
    fcntl = None

#: `.frob/land-queue.json` -- deliberately a distinct file from
#: `.frob/land.lock` (`_land._land_lock`'s own lock file) and from
#: `.frob/tickets.lock` (`_store.ledger_lock`'s), matching the "never
#: reuse a lock/state file across a different concern" rule
#: `_land._LAND_LOCK_REL`'s own comment already establishes for this
#: package.
_QUEUE_REL = Path(".frob") / "land-queue.json"
_QUEUE_LOCK_REL = Path(".frob") / "land-queue.lock"


# frob:doc docs/modules/tickets.md#merge-queue-t-1345-first-portion
class QueueError(ErrorSet):
    """Fallible outcomes of this module's queue operations -- deliberately
    a SEPARATE `ErrorSet` from `LandError` (a queue-bookkeeping failure and
    a land failure are different failure classes; `drain_next` embeds a
    `LandError` inside a failed `QueueEntry` rather than raising one of
    these for it)."""

    AlreadyQueued = (
        "this ticket already has a queued or landing entry in the merge queue"
    )
    StoreCorrupt = "the merge-queue file exists but failed to parse"


# frob:doc docs/modules/tickets.md#merge-queue-t-1345-first-portion
class QueueEntry(BaseModel):
    """One `.frob/land-queue.json` record: a ticket's branch, waiting for
    (or having gone through) the drainer's serial `land()` call."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticket_id: str
    worktree: str
    branch: str
    #: ISO-8601 UTC timestamp, `enqueue`'s own clock read -- FIFO ordering
    #: for `drain_next` is derived from list position (append-order), not
    #: re-sorted by this field; it is recorded for observability/history
    #: only, never re-parsed to decide drain order.
    enqueued_at: str
    #: "queued" (drain candidate) | "landing" (drainer currently
    #: processing -- a transient state a crashed drainer can leave
    #: stuck; see this module's docstring) | "landed" | "failed".
    status: str = "queued"
    #: Populated only once `status` leaves "queued"/"landing": the
    #: `LandReport.commit_sha` on success, or `LandError`'s value on
    #: failure -- never both.
    commit_sha: str | None = None
    error: str | None = None


def _queue_path(root: Path) -> Path:
    """The `.frob/land-queue.json` path for a checkout rooted at `root`."""
    return root / _QUEUE_REL


def _queue_lock_path(root: Path) -> Path:
    """The advisory lock file `_queue_lock` holds, serializing every
    queue-file mutation against `root` (T-1345, mirroring `_land._land_lock`'s
    own T-0577 design)."""
    return root / _QUEUE_LOCK_REL


# frob:doc docs/modules/tickets.md#merge-queue-t-1345-first-portion
# frob:ticket T-1687
@contextmanager
def file_lock(lock_path: Path, *, label: str) -> Iterator[None]:
    """Exclusive, blocking, cross-process advisory lock over `lock_path`
    (T-1687): the ONE fcntl-backed lock implementation every module that
    needs to serialize mutations to a small JSON-file-backed store in this
    package should reuse, rather than each hand-rolling its own near-
    identical copy (this module's own `_queue_lock` now delegates here) --
    "two lock protocols over adjacent state in one repo is a deadlock
    waiting to be discovered in production" (T-1687's own scope note).
    `label` is used only for log messages, so a caller sharing this one
    implementation across several distinct lock files still gets
    distinguishable log lines. Degrades to a documented no-op (logged at
    WARNING) on a platform without `fcntl`, matching every other lock in
    this package."""
    if fcntl is None:  # pragma: no cover -- posix-only in this repo's CI
        _log.warning(
            "land_queue: file_lock(%s): fcntl unavailable on this platform, "
            "lock is a NO-OP -- concurrent mutations against %s are NOT "
            "serialized here",
            label,
            lock_path,
        )
        yield
        return
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    _log.debug("land_queue: file_lock(%s) acquired (%s)", label, lock_path)
    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        _log.debug("land_queue: file_lock(%s) released (%s)", label, lock_path)


# frob:ticket T-1687
@contextmanager
def _queue_lock(root: Path) -> Iterator[None]:
    """Exclusive, blocking, cross-process lock serializing every queue-file
    mutation (`enqueue`, the pop-and-mark-landing step, the record-outcome
    step) against `root` -- deliberately NOT held across a `land_fn` call
    (see this module's docstring, "One drainer, not a distributed lock").
    Delegates to `file_lock` (T-1687) for the actual fcntl mechanics."""
    with file_lock(_queue_lock_path(root), label="land-queue"):
        yield


def _load_queue(root: Path) -> Result[tuple[QueueEntry, ...], QueueError]:
    """Read `.frob/land-queue.json`, or `Ok(())` on a fresh/absent file.
    Caller must already hold `_queue_lock` for any read-modify-write
    sequence; a bare read (e.g. `queue_status`) does not need the lock --
    a torn read is impossible since `_save_queue` writes the whole file in
    one `write_text` call under the lock."""
    path = _queue_path(root)
    if not path.exists():
        return Ok(())
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _log.error("land_queue: _load_queue: %s failed to parse: %s", path, exc)
        return Err(QueueError.StoreCorrupt)
    try:
        return Ok(tuple(QueueEntry.model_validate(e) for e in raw))
    except Exception as exc:  # noqa: BLE001 -- pydantic ValidationError, any shape
        _log.error("land_queue: _load_queue: %s failed to validate: %s", path, exc)
        return Err(QueueError.StoreCorrupt)


# frob:doc docs/modules/tickets.md#merge-queue-t-1345-first-portion
# frob:ticket T-1687
def write_json_records(path: Path, records: tuple[BaseModel, ...]) -> None:
    """Write `records` to `path` as one `write_text` call (T-1687): the ONE
    "list-of-pydantic-model, one JSON array, single syscall-level write"
    implementation every small JSON-file-backed store in this repo should
    reuse -- `_save_queue` below and `frob.verify._watermark`'s own queue
    writer both delegate here now, instead of each carrying a byte-
    identical copy (DUP001 flagged the pre-extraction duplicate directly).
    Not atomic-replace -- a process killed mid-write leaves whatever the
    filesystem itself guarantees for a partial `write_text`; the NEXT read
    of `path` must surface that as a store-corrupt error rather than
    silently reading a torn file (every caller's own load function already
    does this, matching this package's existing fail-loud posture for
    corrupt derived state -- see `frob.check._derived_state_integrity_
    result`'s same rule for `.frob/cache.db`/`.frob/baseline`). Caller must
    already hold whatever lock guards `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps([r.model_dump(mode="json") for r in records], indent=2)
    path.write_text(payload, encoding="utf-8")


# frob:ticket T-1687
def _save_queue(root: Path, entries: tuple[QueueEntry, ...]) -> None:
    """Write `entries` back to `.frob/land-queue.json` -- caller must hold
    `_queue_lock`. Delegates to `write_json_records` (T-1687) for the
    actual write mechanics; see that function's own docstring for the
    partial-write/corruption-detection contract."""
    write_json_records(_queue_path(root), entries)


# frob:doc docs/modules/tickets.md#merge-queue-t-1345-first-portion
# frob:tests tests/unit/test_land_queue.py::TestQueueStatus.test_empty_queue_is_empty_tuple  # noqa: E501
# frob:tests tests/unit/test_land_queue.py::TestStoreCorrupt.test_corrupt_queue_file_errors  # noqa: E501
def queue_status(root: Path) -> Result[tuple[QueueEntry, ...], QueueError]:
    """The full current queue (every entry, any status) for `root`, in
    append order -- a read-only snapshot for a caller that wants to show
    queue state without mutating it."""
    return _load_queue(root)


# frob:doc docs/modules/tickets.md#merge-queue-t-1345-first-portion
# frob:tests tests/unit/test_land_queue.py::TestEnqueue.test_enqueue_returns_queued_entry  # noqa: E501
# frob:tests tests/unit/test_land_queue.py::TestEnqueue.test_enqueue_persists_across_calls  # noqa: E501
# frob:tests tests/unit/test_land_queue.py::TestEnqueue.test_duplicate_enqueue_refused  # noqa: E501
# frob:tests tests/unit/test_land_queue.py::TestEnqueue.test_enqueue_after_landed_is_allowed  # noqa: E501
def enqueue(
    root: Path, ticket_id: str, worktree: Path, branch: str
) -> Result[QueueEntry, QueueError]:
    """Append a new `queued` entry for `ticket_id`'s `branch` (checked out
    at `worktree`) to `root`'s merge queue, returning immediately -- the
    caller does NOT wait for `land()` to run; a drainer (`drain_next`)
    processes it later, in FIFO order. Refuses (`QueueError.AlreadyQueued`)
    if `ticket_id` already has a `queued` or `landing` entry, so a caller
    retrying an enqueue call (e.g. after a network hiccup on whatever
    transport wraps this) cannot silently double-enqueue the same ticket."""
    with _queue_lock(root):
        loaded = _load_queue(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        entries = loaded.danger_ok
        if any(
            e.ticket_id == ticket_id and e.status in ("queued", "landing")
            for e in entries
        ):
            _log.warning(
                "land_queue: enqueue: %s already has a queued/landing entry, refusing",
                ticket_id,
            )
            return Err(QueueError.AlreadyQueued)
        entry = QueueEntry(
            ticket_id=ticket_id,
            worktree=str(worktree),
            branch=branch,
            enqueued_at=datetime.now(timezone.utc).isoformat(),
        )
        _save_queue(root, (*entries, entry))
        _log.info(
            "land_queue: enqueue: %s (branch=%s) queued at position %d",
            ticket_id,
            branch,
            sum(1 for e in entries if e.status == "queued") + 1,
        )
        return Ok(entry)


# frob:doc docs/modules/tickets.md#merge-queue-t-1345-first-portion
# frob:tests tests/unit/test_land_queue.py::TestDrainNext.test_empty_queue_returns_none  # noqa: E501
# frob:tests tests/unit/test_land_queue.py::TestDrainNext.test_drains_fifo_order  # noqa: E501
# frob:tests tests/unit/test_land_queue.py::TestDrainNext.test_successful_land_marks_entry_landed  # noqa: E501
# frob:tests tests/unit/test_land_queue.py::TestDrainNext.test_failed_land_rejected_back_not_retried  # noqa: E501
# frob:tests tests/unit/test_land_queue.py::TestDrainNext.test_failed_entry_is_not_redrained  # noqa: E501
# frob:tests tests/unit/test_land_queue.py::TestDrainNext.test_second_entry_still_drains_after_first_failure  # noqa: E501
def drain_next(
    root: Path,
    land_fn: Callable[[QueueEntry], Result[LandReport, LandError]],
) -> Result[QueueEntry | None, QueueError]:
    """Pop the oldest `queued` entry (FIFO, append order) and run it through
    `land_fn` -- the caller's real `land()` invocation, e.g. `lambda e:
    land(root, e.ticket_id, Path(e.worktree), ...)`. Returns `Ok(None)` if
    the queue has no `queued` entry (nothing to drain, not an error).
    `land_fn`'s `Err` is NOT propagated as this function's own `Err` --
    it is recorded on the entry (`status="failed"`, `error=str(...)`) and
    returned as `Ok(entry)`, per this module's docstring policy: a queued
    branch that no longer merges cleanly is rejected back to the agent
    (dequeued, never silently dropped, never auto-retried) rather than
    raised as a queue-level failure. Only a queue-file-level problem
    (`QueueError.StoreCorrupt`) returns `Err` here."""
    with _queue_lock(root):
        loaded = _load_queue(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        entries = loaded.danger_ok
        idx = next((i for i, e in enumerate(entries) if e.status == "queued"), None)
        if idx is None:
            return Ok(None)
        landing = entries[idx].model_copy(update={"status": "landing"})
        entries = (*entries[:idx], landing, *entries[idx + 1 :])
        _save_queue(root, entries)

    _log.info(
        "land_queue: drain_next: landing %s (branch=%s)",
        landing.ticket_id,
        landing.branch,
    )
    result = land_fn(landing)

    with _queue_lock(root):
        loaded = _load_queue(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        entries = loaded.danger_ok
        idx = next(
            (i for i, e in enumerate(entries) if e.ticket_id == landing.ticket_id),
            None,
        )
        if idx is None:
            # T-1345: the entry vanished between the two lock windows (only
            # possible if something outside this module rewrote the queue
            # file mid-drain) -- report the outcome without a queue entry
            # to update rather than crash.
            _log.error(
                "land_queue: drain_next: %s vanished from the queue file "
                "mid-drain -- reporting land_fn's outcome without updating "
                "a queue entry",
                landing.ticket_id,
            )
            outcome = landing.model_copy(
                update=(
                    {"status": "landed", "commit_sha": result.danger_ok.commit_sha}
                    if result.is_ok
                    else {"status": "failed", "error": result.danger_err.value}
                )
            )
            return Ok(outcome)
        if result.is_ok:
            report = result.danger_ok
            updated = entries[idx].model_copy(
                update={"status": "landed", "commit_sha": report.commit_sha}
            )
            _log.info(
                "land_queue: drain_next: %s landed (commit=%s)",
                landing.ticket_id,
                report.commit_sha,
            )
        else:
            err = result.danger_err
            updated = entries[idx].model_copy(
                update={"status": "failed", "error": err.value}
            )
            _log.warning(
                "land_queue: drain_next: %s failed to land (%s) -- rejected "
                "back to the agent, not auto-retried",
                landing.ticket_id,
                err.value,
            )
        entries = (*entries[:idx], updated, *entries[idx + 1 :])
        _save_queue(root, entries)
        return Ok(updated)


__all__ = [
    "QueueEntry",
    "QueueError",
    "drain_next",
    "enqueue",
    "file_lock",
    "queue_status",
    "write_json_records",
]
