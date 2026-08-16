"""T-1687: the durable, commit-keyed verification record the T-1686
watermark epic builds on -- a persisted VERIFY QUEUE (append-only intent
log, one entry per land) and a persisted WATERMARK ("main is verified
through commit X"), independent of any worker that drains the queue.

THE FOUNDATION, NOT THE WORKER. This module owns only the data model and
its read/write primitives -- record an intent, read the queue, read/
advance the watermark. It does NOT decide when to verify, what "verify"
means, or how a land calls in; that is T-1688 (the daemon-side coalescing
worker) and later leaves in the T-1686 epic. Landing the durable record
first, standalone, is deliberate (T-1687's own ticket body): retrofitting
a durable record under a running worker is strictly harder than building
the worker on top of one that already exists.

WHY TOUCHED SYMBOLS, NOT FILE PATHS. Tier-2 attribution (T-1686's own
design: "a finding anchored at symbol S attributes to the commit whose
touched symbol set REACHES S in the reference graph") is a graph
reachability query over symbol ids. A file path cannot answer that query
once a symbol moves between files -- a path-keyed intent record would
misreport a pure code-move as if it were a new regression the moment
`frob.graph` re-resolves the finding's owning file. `VerifyQueueEntry.
touched_symbols` is therefore a tuple of symref-shaped symbol ids (the
SAME id shape `frob.graph.GraphSnapshot.symbols` keys on and `frob:tests`/
`frob:doc` edges already reference), never a path list. Computing that set
from a real `Diff`/`GraphSnapshot` pair is deliberately OUT of this
module's scope (a caller with graph access, e.g. `frob.tickets._land` or
its CLI wiring in a later leaf, resolves and passes the set in) -- this
module never imports `frob.graph` itself, only validates the SHAPE of
what it is handed (a tuple of non-empty strings) and persists it verbatim.

TWO INDEPENDENT FILES, ONE LOCK DISCIPLINE. `.frob/verify-queue.json` (the
intent log) and `.frob/verify-watermark.json` (the single current
watermark) are separate files with separate locks, mirroring
`frob.tickets._land`'s own "never reuse a lock/state file across a
different concern" rule -- but BOTH locks are `frob.tickets._land_queue.
file_lock` (T-1687 extracted it there for exactly this reuse), not a
second hand-rolled fcntl implementation. Appending to the queue and
advancing the watermark are independent operations that never need to
hold both locks at once.

APPEND-ONLY, COMPACTED BELOW THE WATERMARK, NEVER REWRITTEN IN PLACE. A
normal `record_intent` call only ever appends. `compact_queue` is the one
operation that shortens the file, and it only ever drops entries at or
before the CURRENT watermark's commit (already-verified, already
accounted for) -- it never rewrites or reorders a still-pending entry.
Both operations still write the whole file in one `write_text` call under
`file_lock`, the same "not atomic-replace, but never torn under normal
operation, and a genuinely killed-mid-write process is caught by
`WatermarkError.StoreCorrupt` on the next read rather than silently
misread" posture `frob.tickets._land_queue._save_queue`'s own docstring
already documents and this module deliberately matches rather than
inventing a third write discipline.

"CANNOT VERIFY" IS NEVER "VERIFIED". `load_watermark` treats a missing
watermark file (a fresh repo, nothing verified yet) and a CORRUPT
watermark file identically at the read boundary: both come back as
`Ok(None)` -- "nothing verified" -- never as a stale-but-present record a
caller could mistake for current truth. The corrupt case additionally
logs at WARNING (never silently) so the corruption itself is visible even
though the read degrades safely. `queue_status`, by contrast, propagates
a corrupt QUEUE file as `Err(WatermarkError.StoreCorrupt)` rather than
degrading to an empty tuple -- an unreadable intent log must never be
misread as "no pending work", which is itself a "how far is main
verified" claim just as dangerous as a stale watermark; `record_intent`/
`compact_queue` (both mutators) refuse outright on that `Err` rather than
risk silently discarding or duplicating intent records on top of an
unreadable file.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._land_queue import file_lock, write_json_records

_log = get_logger(__name__)

# frob:doc \
# docs/modules/tickets-verify-sweep.md#verification-watermark-t-1687-foundation-of-the-\
# t-1686-epic
#: Bumped whenever `VerifyQueueEntry`/`Watermark`'s own field shape
#: changes -- persisted alongside each record (T-1687's own "versioned,
#: forward-compatible on read" constraint) so a future reader can tell an
#: old-shape record apart from a genuinely corrupt one instead of
#: conflating the two.
SCHEMA_VERSION = 1

_QUEUE_REL = Path(".frob") / "verify-queue.json"
_QUEUE_LOCK_REL = Path(".frob") / "verify-queue.lock"
_WATERMARK_REL = Path(".frob") / "verify-watermark.json"
_WATERMARK_LOCK_REL = Path(".frob") / "verify-watermark.lock"


# frob:doc \
# docs/modules/tickets-verify-sweep.md#verification-watermark-t-1687-foundation-of-the-\
# t-1686-epic
class WatermarkError(ErrorSet):
    """Fallible outcomes of this module's queue/watermark operations."""

    StoreCorrupt = (
        "the verify-queue or verify-watermark file exists but failed to parse"
    )
    EmptyTouchedSymbols = "touched_symbols must name at least one real symbol id"


# frob:doc \
# docs/modules/tickets-verify-sweep.md#verification-watermark-t-1687-foundation-of-the-\
# t-1686-epic
class VerifyQueueEntry(BaseModel):
    """One `.frob/verify-queue.json` record: a land's own intent to be
    verified -- the commit it produced, the ticket responsible, and the
    SYMBOL ids (never file paths, see this module's docstring) it
    touched, so a later batch verification can attribute any finding at
    the newest commit back to the specific land(s) that could have caused
    it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = SCHEMA_VERSION
    commit_sha: str
    ticket_id: str
    #: Symref-shaped symbol ids (`frob.graph.GraphSnapshot.symbols` keys),
    #: NEVER file paths -- see this module's own docstring, "WHY TOUCHED
    #: SYMBOLS, NOT FILE PATHS".
    touched_symbols: tuple[str, ...]
    #: ISO-8601 UTC timestamp, `record_intent`'s own clock read.
    enqueued_at: str
    #: The profile in force at land time (`fortress`/`standard`/`rapid`,
    #: `frob.tickets._profile.ProfileName`'s own values) -- recorded as a
    #: plain `str`, not that enum, so this module never has to import
    #: `frob.tickets._profile` just to persist a label; T-1686's later
    #: leaves are the ones that act on it.
    profile: str


# frob:doc \
# docs/modules/tickets-verify-sweep.md#verification-watermark-t-1687-foundation-of-the-\
# t-1686-epic
class Watermark(BaseModel):
    """`.frob/verify-watermark.json`'s single current record: "main is
    verified through commit X, as of time T, by run R, against baseline
    B". Advances only on a fully green batch verification (T-1686's own
    design) -- this module does not itself decide when that is true, only
    persists the claim once a caller (the drainer worker) has decided it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = SCHEMA_VERSION
    commit_sha: str
    verified_at: str
    run_id: str
    baseline_digest: str


def _queue_path(root: Path) -> Path:
    """The `.frob/verify-queue.json` path for a checkout rooted at `root`."""
    return root / _QUEUE_REL


def _queue_lock_path(root: Path) -> Path:
    """The advisory lock file guarding every `.frob/verify-queue.json`
    mutation against `root`."""
    return root / _QUEUE_LOCK_REL


def _watermark_path(root: Path) -> Path:
    """The `.frob/verify-watermark.json` path for a checkout rooted at
    `root`."""
    return root / _WATERMARK_REL


def _watermark_lock_path(root: Path) -> Path:
    """The advisory lock file guarding every `.frob/verify-watermark.json`
    mutation against `root`."""
    return root / _WATERMARK_LOCK_REL


def _load_queue_raw(root: Path) -> Result[tuple[VerifyQueueEntry, ...], WatermarkError]:
    """Read `.frob/verify-queue.json`, or `Ok(())` on a fresh/absent file.
    A corrupt file is `Err(WatermarkError.StoreCorrupt)` -- see this
    module's docstring for why a queue read never silently degrades to
    "empty" the way `load_watermark` degrades a corrupt watermark to
    `None`. Caller must already hold the queue's `file_lock` for any
    read-modify-write sequence."""
    path = _queue_path(root)
    if not path.exists():
        return Ok(())
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _log.error("watermark: _load_queue_raw: %s failed to parse: %s", path, exc)
        return Err(WatermarkError.StoreCorrupt)
    try:
        return Ok(tuple(VerifyQueueEntry.model_validate(e) for e in raw))
    except Exception as exc:  # noqa: BLE001 -- pydantic ValidationError, any shape
        _log.error("watermark: _load_queue_raw: %s failed to validate: %s", path, exc)
        return Err(WatermarkError.StoreCorrupt)


def _save_queue(root: Path, entries: tuple[VerifyQueueEntry, ...]) -> None:
    """Write `entries` back to `.frob/verify-queue.json` -- caller must
    hold the queue's `file_lock`. Delegates to `frob.tickets._land_queue.
    write_json_records` (T-1687) for the actual write mechanics -- the
    SAME implementation `_land_queue._save_queue` uses, not a second copy
    (DUP001 flagged the pre-extraction duplicate directly)."""
    write_json_records(_queue_path(root), entries)


# frob:doc \
# docs/modules/tickets-verify-sweep.md#verification-watermark-t-1687-foundation-of-the-\
# t-1686-epic
# frob:tests \
# tests/unit/verify/test_watermark.py::TestQueueStatus.test_empty_queue_is_empty_tuple
# frob:tests \
# tests/unit/verify/test_watermark.py::TestQueueStatus.test_corrupt_queue_errors
def queue_status(root: Path) -> Result[tuple[VerifyQueueEntry, ...], WatermarkError]:
    """The full current verify queue (every entry, oldest first, append
    order) for `root` -- a read-only snapshot. Propagates
    `WatermarkError.StoreCorrupt` on a corrupt file rather than degrading
    to empty; see this module's own docstring for why."""
    return _load_queue_raw(root)


# frob:doc \
# docs/modules/tickets-verify-sweep.md#verification-watermark-t-1687-foundation-of-the-\
# t-1686-epic
# frob:tests tests/unit/verify/test_watermark.py::TestRecordIntent.test_appends_one_entry_with_resolvable_symbols  # noqa: E501
# frob:tests tests/unit/verify/test_watermark.py::TestRecordIntent.test_persists_across_calls_in_order  # noqa: E501
# frob:tests tests/unit/verify/test_watermark.py::TestRecordIntent.test_empty_touched_symbols_refused  # noqa: E501
# frob:tests tests/unit/verify/test_watermark.py::TestRecordIntent.test_corrupt_queue_refuses_to_append  # noqa: E501
# frob:ticket T-1736
def record_intent(
    root: Path,
    *,
    commit_sha: str,
    ticket_id: str,
    touched_symbols: tuple[str, ...],
    profile: str,
) -> Result[VerifyQueueEntry, WatermarkError]:
    """Append exactly one `VerifyQueueEntry` for `commit_sha` to `root`'s
    verify queue, written BEFORE the caller's land returns (the same
    "an unverified commit must never be a silent one" posture T-1684's
    `record_rapid_debt` already established for the rapid-profile debt
    log). Refuses (`WatermarkError.EmptyTouchedSymbols`) on an empty
    `touched_symbols` tuple -- a land that touches nothing has nothing for
    tier-2 attribution to reach, and a silently-accepted empty set here
    would make every future finding at this commit unattributable by
    construction, not just hard to attribute. Does NOT deduplicate against
    an existing `commit_sha` -- a real repo can, in principle, see the
    same commit sha land twice (a rebase-and-reapply, a cherry-pick), and
    this module's job is to record what happened, not to guess whether a
    second entry for the same sha is intentional."""
    if not touched_symbols:
        _log.warning(
            "watermark: record_intent: %s (commit=%s) has an empty "
            "touched_symbols set -- refusing",
            ticket_id,
            commit_sha,
        )
        return Err(WatermarkError.EmptyTouchedSymbols)
    with file_lock(_queue_lock_path(root), label="verify-queue"):
        loaded = _load_queue_raw(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        entries = loaded.danger_ok
        entry = VerifyQueueEntry(
            commit_sha=commit_sha,
            ticket_id=ticket_id,
            touched_symbols=touched_symbols,
            enqueued_at=datetime.now(timezone.utc).isoformat(),
            profile=profile,
        )
        _save_queue(root, (*entries, entry))
        _log.info(
            "watermark: record_intent: %s (commit=%s, profile=%s) recorded "
            "%d touched symbol(s); queue depth now %d",
            ticket_id,
            commit_sha,
            profile,
            len(touched_symbols),
            len(entries) + 1,
        )
        return Ok(entry)


# frob:doc \
# docs/modules/tickets-verify-sweep.md#verification-watermark-t-1687-foundation-of-the-\
# t-1686-epic
# frob:tests \
# tests/unit/verify/test_watermark.py::TestLoadWatermark.test_missing_file_is_none
# frob:tests tests/unit/verify/test_watermark.py::TestLoadWatermark.test_round_trips
# frob:tests tests/unit/verify/test_watermark.py::TestLoadWatermark.test_corrupt_file_reads_as_none_not_verified  # noqa: E501
def load_watermark(root: Path) -> Result[Watermark | None, WatermarkError]:
    """`root`'s current watermark, or `None` if none has ever been set OR
    the stored record is corrupt/unparsable -- see this module's own
    docstring, ""CANNOT VERIFY" IS NEVER "VERIFIED"": a caller must never
    be able to tell a fresh repo apart from a corrupted one and read the
    corrupted one as more-verified-than-a-fresh-repo by accident, so both
    degrade to the identical `Ok(None)`. The corrupt case additionally
    logs at WARNING -- degrading safely does not mean degrading silently."""
    path = _watermark_path(root)
    if not path.exists():
        return Ok(None)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _log.warning(
            "watermark: load_watermark: %s failed to parse (%s) -- reading "
            "as 'nothing verified', never as 'everything verified'",
            path,
            exc,
        )
        return Ok(None)
    try:
        return Ok(Watermark.model_validate(raw))
    except Exception as exc:  # noqa: BLE001 -- pydantic ValidationError, any shape
        _log.warning(
            "watermark: load_watermark: %s failed to validate (%s) -- "
            "reading as 'nothing verified', never as 'everything verified'",
            path,
            exc,
        )
        return Ok(None)


# frob:doc \
# docs/modules/tickets-verify-sweep.md#verification-watermark-t-1687-foundation-of-the-\
# t-1686-epic
# frob:tests tests/unit/verify/test_watermark.py::TestAdvanceWatermark.test_advance_then_load_round_trips  # noqa: E501
# frob:tests tests/unit/verify/test_watermark.py::TestAdvanceWatermark.test_advance_overwrites_prior_watermark  # noqa: E501
def advance_watermark(
    root: Path,
    *,
    commit_sha: str,
    run_id: str,
    baseline_digest: str,
) -> Result[Watermark, WatermarkError]:
    """Set `root`'s watermark to `commit_sha`, unconditionally overwriting
    whatever was recorded before (this module trusts the caller's own
    "fully green batch" decision -- see this module's docstring, "THE
    FOUNDATION, NOT THE WORKER"; nothing here re-derives or second-guesses
    that decision). Always succeeds unless the write itself fails at the
    OS level (`OSError` is not caught here -- an unwritable `.frob/`
    directory is an environment problem the caller must see, not a
    `WatermarkError` this module's own error catalog should paper over)."""
    watermark = Watermark(
        commit_sha=commit_sha,
        verified_at=datetime.now(timezone.utc).isoformat(),
        run_id=run_id,
        baseline_digest=baseline_digest,
    )
    with file_lock(_watermark_lock_path(root), label="verify-watermark"):
        path = _watermark_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(watermark.model_dump(mode="json"), indent=2), encoding="utf-8"
        )
    _log.info(
        "watermark: advance_watermark: main verified through %s (run=%s, baseline=%s)",
        commit_sha,
        run_id,
        baseline_digest,
    )
    return Ok(watermark)


# frob:doc \
# docs/modules/tickets-verify-sweep.md#verification-watermark-t-1687-foundation-of-the-\
# t-1686-epic
# frob:tests tests/unit/verify/test_watermark.py::TestCompactQueue.test_drops_entries_at_or_before_watermark  # noqa: E501
# frob:tests tests/unit/verify/test_watermark.py::TestCompactQueue.test_keeps_entries_after_watermark  # noqa: E501
# frob:tests tests/unit/verify/test_watermark.py::TestCompactQueue.test_watermark_commit_absent_from_queue_is_a_noop  # noqa: E501
# frob:tests \
# tests/unit/verify/test_watermark.py::TestCompactQueue.test_no_watermark_yet_is_a_noop
def compact_queue(root: Path) -> Result[int, WatermarkError]:
    """Drop every queue entry at-or-before the current watermark's
    `commit_sha` (append order -- the watermark's own commit is always the
    NEWEST entry in the batch it verified, per T-1686's own design: "the
    worker drains the queue TO ITS TIP, verifies once at the newest
    commit"), returning the count removed. A no-op (`Ok(0)`) if there is
    no watermark yet, or the watermark's `commit_sha` is not present in
    the queue at all (already compacted, or the watermark was set by a
    caller outside this module's own accounting -- either way, nothing
    HERE is safe to drop). This is the ONE operation that shortens
    `.frob/verify-queue.json`; `record_intent` only ever appends -- see
    this module's own docstring, "APPEND-ONLY, COMPACTED BELOW THE
    WATERMARK, NEVER REWRITTEN IN PLACE"."""
    watermark_result = load_watermark(root)
    if watermark_result.is_err:
        return Err(watermark_result.danger_err)
    watermark = watermark_result.danger_ok
    if watermark is None:
        _log.debug("watermark: compact_queue: no watermark yet, nothing to compact")
        return Ok(0)
    with file_lock(_queue_lock_path(root), label="verify-queue"):
        loaded = _load_queue_raw(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        entries = loaded.danger_ok
        idx = next(
            (i for i, e in enumerate(entries) if e.commit_sha == watermark.commit_sha),
            None,
        )
        if idx is None:
            _log.debug(
                "watermark: compact_queue: watermark commit %s not present in "
                "the queue -- nothing to compact",
                watermark.commit_sha,
            )
            return Ok(0)
        kept = entries[idx + 1 :]
        removed = len(entries) - len(kept)
        _save_queue(root, kept)
        _log.info(
            "watermark: compact_queue: dropped %d entr(y/ies) at or before "
            "verified commit %s; %d entr(y/ies) remain",
            removed,
            watermark.commit_sha,
            len(kept),
        )
        return Ok(removed)


__all__ = [
    "SCHEMA_VERSION",
    "VerifyQueueEntry",
    "Watermark",
    "WatermarkError",
    "advance_watermark",
    "compact_queue",
    "load_watermark",
    "queue_status",
    "record_intent",
]
