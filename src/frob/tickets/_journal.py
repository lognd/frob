"""Intent journal for multi-step ticket ops (T-0456).

`frob ticket land` mutates more than one artifact in sequence (worktree
merge, ledger splice/close, squash-apply onto `root`, optional version
bump + native rebuild) -- a crash or power loss partway through leaves the
tree in whatever intermediate state the last completed step left it in,
with no record that an operation was ever in flight. `write_intent` records
a small JSON marker under `<root>/.frob/journal/<ticket-id>.json` BEFORE
`land` starts mutating anything and `clear_intent` removes it when `land`
returns for ANY reason (success or a clean, handled `Err`) -- so the marker
surviving past the calling process's lifetime means the process died
mid-operation without ever reaching its own cleanup, which is exactly the
condition `frob ticket reconcile` (T-0456/T-0476) needs to surface an
orphaned land as an anomaly instead of it going unnoticed forever.

Journal files are local to `root` (unlike T-0473's cross-worktree lease
side-channel under the shared git common dir) -- an in-flight `land` only
ever mutates the ONE worktree/root pair it was invoked against, so there is
nothing cross-worktree to reconcile here.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._store import atomic_write

_log = get_logger(__name__)

# frob:doc docs/modules/tickets.md#intent-journal-t-0456
JOURNAL_DIRNAME = "journal"


# frob:ticket T-0601
class _JournalError(ErrorSet):
    """Fallible outcomes of the intent-journal side-channel (T-0456)."""

    WriteFailed = "writing the journal record failed"


# frob:ticket T-0601
class _LandIntent(BaseModel):
    """One in-flight `frob ticket land` operation (T-0456): which ticket,
    and when the operation started -- read back by `frob ticket reconcile`
    to detect a land that never reached its own cleanup (crash/interrupt)."""

    model_config = {}

    ticket_id: str
    worktree: str
    started_at: str


# frob:ticket T-0601
def _journal_dir(root: Path) -> Path:
    """`<root>/.frob/journal`, where in-flight land intent records live (T-0456)."""
    return root / ".frob" / JOURNAL_DIRNAME


# frob:ticket T-0601
def _intent_path(root: Path, ticket_id: str) -> Path:
    """The per-ticket intent-journal file path under `root`."""
    return _journal_dir(root) / f"{ticket_id}.json"


# frob:tests tests/test_ticket_journal.py::TestWriteIntent.test_write_then_read_round_trips  # noqa: E501
# frob:tests tests/test_ticket_journal.py::TestWriteIntent.test_write_failure_returns_err  # noqa: E501
# frob:ticket T-0601
def _write_intent(
    root: Path, ticket_id: str, worktree: Path
) -> Result[None, _JournalError]:
    """Record that a `land` of `ticket_id` (from `worktree`) is starting
    (T-0456) -- called BEFORE `frob.tickets._land.land` mutates anything.
    Best-effort in the same spirit as T-0473's `record_lease`: a write
    failure is logged and returned as `Err`, but callers may choose to
    proceed anyway rather than block an otherwise-working `land` on a
    journal-directory permission problem -- the journal is a recovery aid,
    not the source of truth for whether the land itself succeeded."""
    intent = _LandIntent(
        ticket_id=ticket_id,
        worktree=str(worktree.resolve()),
        started_at=datetime.now(UTC).isoformat(),
    )
    written = atomic_write(
        _intent_path(root, ticket_id), intent.model_dump_json(indent=2) + "\n"
    )
    if written.is_err:
        _log.warning(
            "tickets: could not write land intent for %s: %s",
            ticket_id,
            written.danger_err,
        )
        return Err(_JournalError.WriteFailed)
    _log.info("tickets: land intent recorded for %s", ticket_id)
    return Ok(None)


# frob:tests tests/test_ticket_journal.py::TestClearIntent.test_clear_removes_the_file  # noqa: E501
# frob:tests tests/test_ticket_journal.py::TestClearIntent.test_clear_missing_file_is_a_no_op  # noqa: E501
# frob:ticket T-0601
def _clear_intent(root: Path, ticket_id: str) -> None:
    """Remove `ticket_id`'s land-intent record, if any (T-0456) -- called
    when `land` returns for ANY reason (success or a clean, handled `Err`),
    from a `finally` block so a raised exception still clears it. A missing
    file (never written, or already cleared) is silently fine: clearing is
    always safe to call unconditionally at the end of `land`."""
    path = _intent_path(root, ticket_id)
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning("tickets: could not clear land intent for %s: %s", ticket_id, exc)


# frob:tests tests/test_ticket_journal.py::TestReadAllIntents.test_reads_every_recorded_intent  # noqa: E501
# frob:tests tests/test_ticket_journal.py::TestReadAllIntents.test_no_journal_dir_returns_empty  # noqa: E501
# frob:tests tests/test_ticket_journal.py::TestReadAllIntents.test_malformed_record_is_skipped_not_fatal  # noqa: E501
# frob:ticket T-0601
def _read_all_intents(root: Path) -> tuple[_LandIntent, ...]:
    """Every currently-recorded land-intent record under `root` (T-0456),
    ticket-id-ordered. A record still present means the `land` that wrote
    it never reached its own `clear_intent` call -- either it is still
    genuinely running (rare but possible: reconcile is a point-in-time
    snapshot, not a lock), or the process that started it died before
    finishing. `frob ticket reconcile` is the caller that turns "still
    present" into a reported anomaly. Degrades to `()` if the journal
    directory does not exist yet (nothing has ever landed); a malformed
    single record is logged and skipped rather than failing the whole
    read, matching `read_all_leases`' (T-0473) same defensive shape."""
    directory = _journal_dir(root)
    if not directory.is_dir():
        return ()
    records: list[_LandIntent] = []
    for path in sorted(directory.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            records.append(_LandIntent.model_validate(raw))
        except (OSError, ValueError) as exc:
            _log.warning("tickets: could not parse journal file %s: %s", path, exc)
            continue
    return tuple(records)


__all__ = [
    "JOURNAL_DIRNAME",
]
