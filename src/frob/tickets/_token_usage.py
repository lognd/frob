"""frob.tickets._token_usage -- automatic per-ticket agent token
accounting mined from harness transcript JSONL (T-5137).

Owner directive 2026-09-20: token usage is set AUTOMATICALLY, never costs
a model call, never costs significant wall time, handles interrupted
sessions, and lives in ONE abstraction. This module is that abstraction:
`collect_ticket_usage` sums `input`/`output`/`cache_creation`/`cache_read`
tokens across every harness session that worked `ticket_id`'s lease
window, and `record_ticket_usage` persists the result onto `Ticket.usage`.
Both are called from `frob.tickets._leases.release_lease` -- the ONE
chokepoint `frob.tickets.transition` already runs through on every
terminal exit from `IN_PROGRESS` (close, land's own finalize-through-
close, requeue, drop), so this fires whichever of `close`/`land` reaches
`DONE` first, idempotently (a second call only reads bytes past the
cached cursor).

SESSION IDENTITY, ZERO COST. `.claude/hooks/dispatch-telemetry.py`'s
`SessionStart` hook already appends one `kind="dispatch"` `event="start"`
JSON line per session to `root/.frob/telemetry.jsonl` (`dispatch_id`,
`worktree`, and now, T-5137, `transcript_path` when Claude Code's own
payload carries one) -- reused here rather than a second sessions-only
file (NO DUPLICATION). Nothing in `frob ticket start`/`work` needs to
change: the lease already has the worktree path and start time
(`frob.tickets._leases.lease_record_for_ticket`).

ONE ABSTRACTION, NO DUPLICATION. `HarnessAdapter` is the seam a second
coding-agent harness would implement; `ClaudeCodeAdapter` is the only one
that exists today. Every Claude-Code-specific file shape (the telemetry
JSONL, the transcript JSONL) is confined behind it.

COST BOUNDS. No model calls anywhere. Reading `.frob/telemetry.jsonl` is
one bounded stat+read. Each transcript is read AT MOST from its cached
byte offset onward (`.frob/token-usage-cache.json`), capped at
`_COLLECTION_BUDGET_SECONDS` wall-clock per `collect_ticket_usage` call,
beyond which the pass stops and reports `complete=False` for what it
could not finish -- a 100 MB transcript already collected once costs one
stat comparison, not a re-read.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import Ticket, TicketUsage
from frob.tickets._store import write_ticket

_log = get_logger(__name__)

#: wall-clock cap for one `collect_ticket_usage` call's transcript
#: streaming (T-5137 design section 6) -- past this, the pass stops and
#: reports `complete=False` rather than blocking a `close`/`land`.
_COLLECTION_BUDGET_SECONDS = 2.0

#: cursor cache filename under `root/.frob/` (T-5137 design section 2):
#: `{transcript_path: {"byte_offset", "input", "output",
#: "cache_creation", "cache_read"}}`, so re-collection only reads bytes
#: past what was already summed.
_CACHE_FILENAME = "token-usage-cache.json"


# frob:ticket T-5137
# frob:doc \
# docs/modules/tickets-lifecycle.md#automatic-per-ticket-token-accounting-t-5137  # noqa: E501
# tests/unit/test_token_usage.py::TestRecordTicketUsage.test_unknown_ticket_is_err
class UsageError(ErrorSet):
    """Fallible outcomes of `collect_ticket_usage`/`record_ticket_usage`
    (T-5137)."""

    NoTicket = "no ticket with that id"
    WriteFailed = "writing the collected usage onto the ticket failed"


@dataclass(frozen=True)
class _SessionRecord:
    """One `kind="dispatch"` `event="start"` telemetry line relevant to a
    collection window (T-5137): session id, transcript path (`None` if
    the hook ran before T-5137 or the harness never reported one), and
    the session's own start timestamp."""

    session_id: str
    transcript_path: str | None
    iso_ts: str


# frob:ticket T-5137
# frob:doc \
# docs/modules/tickets-lifecycle.md#automatic-per-ticket-token-accounting-t-5137  # noqa: E501
# tests/unit/test_token_usage.py::TestCollectTicketUsage.test_sums_assistant_usage_fields  # noqa: E501
class HarnessAdapter(Protocol):
    """T-5137 design section 5's ONE-abstraction seam: how a specific
    coding-agent harness's own session log is discovered and read. Only
    `ClaudeCodeAdapter` exists today; a second harness implements this
    Protocol instead of `collect_ticket_usage` growing a harness-specific
    branch."""

    def discover_sessions(
        self,
        root: Path,
        worktree: str,
        window_start: datetime,
        window_end: datetime,
    ) -> list[_SessionRecord]:
        """Every session whose recorded `worktree` is `worktree` and
        whose own start timestamp falls inside `[window_start,
        window_end]`."""
        ...

    def extract_usage(
        self, transcript_path: Path, cursor: dict | None
    ) -> tuple[dict[str, int], dict[str, int] | None, bool]:
        """Sum `input`/`output`/`cache_creation`/`cache_read` token
        counts from `transcript_path`, resuming from `cursor` (a prior
        `{"byte_offset", ...partial sums}`) when given. Returns
        `(totals, new_cursor, complete)` -- `new_cursor` is `None` when
        the transcript could not be read at all (rotated/deleted/
        unreadable, T-5137 design section 4)."""
        ...


def _iso(dt: datetime) -> str:
    """`dt` (assumed UTC-aware) rendered as an ISO-8601 string -- the one
    formatting call site every `TicketUsage` timestamp field goes
    through, so all four (`window_start`/`window_end`/`collected_at`)
    are byte-for-byte the same shape."""
    return dt.astimezone(UTC).isoformat()


def _parse_iso(value: str) -> datetime | None:
    """`value` parsed as an ISO-8601 timestamp, or `None` if it is not
    one -- a peer-writable telemetry line (T-0780's own precedent for
    lease files) must never crash collection, only be skipped."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


# frob:ticket T-5137
def _totals_and_offset_from_cursor(cursor: dict | None) -> tuple[dict[str, int], int]:
    """Split a raw cursor dict (loaded straight from the JSON cache, so
    its value types are unverified) into `extract_usage`'s starting
    `totals` and `byte_offset` -- a missing/malformed cursor degrades to
    an all-zero start rather than raising (T-5137 design section 2: a
    corrupt cache entry costs a re-read, never a crash)."""
    totals = {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}
    if cursor:
        for key in totals:
            value = cursor.get(key)
            if isinstance(value, int):
                totals[key] = value
    byte_offset = cursor.get("byte_offset", 0) if cursor else 0
    if not isinstance(byte_offset, int):
        byte_offset = 0
    return totals, byte_offset


def _stream_transcript_usage(
    transcript_path: Path, totals: dict[str, int], byte_offset: int
) -> tuple[dict[str, int], dict[str, int] | None, bool]:
    """`ClaudeCodeAdapter.extract_usage`'s actual streaming-read loop,
    split out under ARCH001: read `transcript_path` from `byte_offset`
    onward, capped at `_COLLECTION_BUDGET_SECONDS` wall-clock, summing
    each `type="assistant"` line's `message.usage.*` into `totals`
    (already seeded from the cursor). A transcript that vanishes
    mid-read returns `(totals, None, False)`, logged, never raised."""
    deadline = time.monotonic() + _COLLECTION_BUDGET_SECONDS
    complete = True
    try:
        with transcript_path.open("rb") as fh:
            fh.seek(byte_offset)
            for raw_line in fh:
                if time.monotonic() > deadline:
                    complete = False
                    break
                byte_offset += len(raw_line)
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict):
                    continue
                if entry.get("type") != "assistant":
                    continue
                message = entry.get("message")
                if not isinstance(message, dict):
                    continue
                usage = message.get("usage")
                if not isinstance(usage, dict):
                    continue
                totals["input"] += int(usage.get("input_tokens", 0) or 0)
                totals["output"] += int(usage.get("output_tokens", 0) or 0)
                totals["cache_creation"] += int(
                    usage.get("cache_creation_input_tokens", 0) or 0
                )
                totals["cache_read"] += int(
                    usage.get("cache_read_input_tokens", 0) or 0
                )
    except OSError as exc:
        _log.info(
            "token_usage: transcript %s vanished mid-read (%s)", transcript_path, exc
        )
        return totals, None, False

    new_cursor = {"byte_offset": byte_offset, **totals}
    return totals, new_cursor, complete


# frob:ticket T-5137
# frob:doc \
# docs/modules/tickets-lifecycle.md#automatic-per-ticket-token-accounting-t-5137  # noqa: E501
# tests/unit/test_token_usage.py::TestClaudeCodeAdapterDiscoverSessions.test_filters_by_worktree_and_window  # noqa: E501
# tests/unit/test_token_usage.py::TestClaudeCodeAdapterExtractUsage.test_sums_assistant_usage_fields  # noqa: E501
class ClaudeCodeAdapter:
    """The `HarnessAdapter` for Claude Code (T-5137): session discovery
    reads `root/.frob/telemetry.jsonl`'s `kind="dispatch"` lines (written
    by `.claude/hooks/dispatch-telemetry.py`); usage extraction streams a
    transcript JSONL summing `message.usage.*` over `type="assistant"`
    entries."""

    def discover_sessions(
        self,
        root: Path,
        worktree: str,
        window_start: datetime,
        window_end: datetime,
    ) -> list[_SessionRecord]:
        """Read `.frob/telemetry.jsonl` once, keep every `event="start"`
        line whose `worktree` matches and whose `iso_ts` falls inside the
        window. A missing/unreadable telemetry file is a session-count of
        zero, not an error (T-5137 design section 4: a ticket worked by a
        human, or before this hook existed, has none)."""
        path = root / ".frob" / "telemetry.jsonl"
        if not path.exists():
            return []
        sessions: list[_SessionRecord] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            _log.warning("token_usage: could not read %s: %s", path, exc)
            return []
        for line in lines:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict):
                continue
            if record.get("kind") != "dispatch" or record.get("event") != "start":
                continue
            if record.get("worktree") != worktree:
                continue
            iso_ts = record.get("iso_ts")
            if not isinstance(iso_ts, str):
                continue
            started = _parse_iso(iso_ts)
            if started is None or not (window_start <= started <= window_end):
                continue
            session_id = record.get("dispatch_id")
            if not isinstance(session_id, str):
                continue
            transcript_path = record.get("transcript_path")
            sessions.append(
                _SessionRecord(
                    session_id=session_id,
                    transcript_path=(
                        transcript_path if isinstance(transcript_path, str) else None
                    ),
                    iso_ts=iso_ts,
                )
            )
        return sessions

    def extract_usage(
        self, transcript_path: Path, cursor: dict | None
    ) -> tuple[dict[str, int], dict[str, int] | None, bool]:
        """Stream `transcript_path` from `cursor["byte_offset"]` (or the
        start), summing `message.usage.{input_tokens, output_tokens,
        cache_creation_input_tokens, cache_read_input_tokens}` over
        `type="assistant"` lines -- capped at `_COLLECTION_BUDGET_
        SECONDS` wall-clock, past which the partial sum is returned with
        `complete=False`. A rotated/deleted/unreadable transcript returns
        `({}, None, False)` -- logged, never raised (T-5137 design
        section 4)."""
        totals, byte_offset = _totals_and_offset_from_cursor(cursor)

        try:
            size = transcript_path.stat().st_size
        except OSError as exc:
            _log.info(
                "token_usage: transcript %s unreadable (%s), usage stays None",
                transcript_path,
                exc,
            )
            return totals, None, False
        if size <= byte_offset:
            # Nothing new since the last collection pass -- the cache
            # already reflects this transcript in full.
            return totals, {"byte_offset": byte_offset, **totals}, True

        return _stream_transcript_usage(transcript_path, totals, byte_offset)


def _cache_path(root: Path) -> Path:
    """`root/.frob/token-usage-cache.json`'s path (T-5137) -- not
    guaranteed to exist."""
    return root / ".frob" / _CACHE_FILENAME


def _load_cache(root: Path) -> dict:
    """The token-usage cursor cache, or `{}` if missing/unreadable --
    peer-writable state, same defensive posture as lease files."""
    path = _cache_path(root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_cache(root: Path, cache: dict) -> None:
    """Best-effort atomic-enough write of the cursor cache -- a failure
    here only costs a future re-read of already-seen bytes, never
    correctness, so it is logged and swallowed rather than propagated."""
    path = _cache_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, sort_keys=True), encoding="utf-8")
    except OSError as exc:
        _log.warning("token_usage: failed to write cursor cache: %s", exc)


# frob:ticket T-5137
# frob:doc \
# docs/modules/tickets-lifecycle.md#automatic-per-ticket-token-accounting-t-5137  # noqa: E501
# tests/unit/test_token_usage.py::TestCollectTicketUsage.test_sums_assistant_usage_fields  # noqa: E501
# tests/unit/test_token_usage.py::TestCollectTicketUsage.test_no_lease_returns_none
def _sum_sessions(
    root: Path, ticket_id: str, harness: HarnessAdapter, sessions: list[_SessionRecord]
) -> tuple[dict[str, int], list[str], list[str], bool]:
    """`collect_ticket_usage`'s per-session summation loop, split out
    under ARCH001: reads/updates the cursor cache and sums every
    session's `extract_usage` totals, returning `(totals, session_ids,
    transcripts_seen, complete)`. A session with no `transcript_path`
    contributes nothing and forces `complete=False` (T-5137 design
    section 4)."""
    cache = _load_cache(root)
    totals = {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}
    session_ids: list[str] = []
    transcripts_seen: list[str] = []
    complete = True

    for session in sessions:
        session_ids.append(session.session_id)
        if session.transcript_path is None:
            _log.info(
                "token_usage: %s session %s has no transcript_path (pre-T-5137 "
                "hook or unsupported harness) -- contributes nothing, complete=False",
                ticket_id,
                session.session_id,
            )
            complete = False
            continue
        transcript_path = Path(session.transcript_path)
        transcripts_seen.append(session.transcript_path)
        cursor = cache.get(session.transcript_path)
        per_transcript, new_cursor, transcript_complete = harness.extract_usage(
            transcript_path, cursor
        )
        for key in totals:
            totals[key] += per_transcript.get(key, 0)
        if new_cursor is not None:
            cache[session.transcript_path] = new_cursor
        if not transcript_complete:
            complete = False

    _save_cache(root, cache)
    return totals, session_ids, transcripts_seen, complete


# frob:ticket T-5137
# frob:doc \
# docs/modules/tickets-lifecycle.md#automatic-per-ticket-token-accounting-t-5137  # noqa: E501
# tests/unit/test_token_usage.py::TestCollectTicketUsage.test_sums_assistant_usage_fields  # noqa: E501
# tests/unit/test_token_usage.py::TestCollectTicketUsage.test_no_lease_returns_none
def collect_ticket_usage(
    root: Path,
    ticket_id: str,
    *,
    adapter: HarnessAdapter | None = None,
    now: datetime | None = None,
) -> Result[TicketUsage | None, UsageError]:
    """Sum token usage across every harness session that worked
    `ticket_id`'s CURRENT lease window (T-5137). `Ok(None)` (not an
    error) when the ticket has no recorded lease at all -- a
    human-worked or not-yet-started ticket has nothing to collect.
    `adapter` defaults to `ClaudeCodeAdapter()`; injectable for tests."""
    from frob.tickets._leases import lease_record_for_ticket

    harness = adapter if adapter is not None else ClaudeCodeAdapter()
    lease = lease_record_for_ticket(root, ticket_id)
    if lease is None:
        _log.debug(
            "token_usage: %s has no recorded lease -- usage stays None", ticket_id
        )
        return Ok(None)

    window_start = _parse_iso(lease.recorded_at)
    if window_start is None:
        _log.warning(
            "token_usage: %s lease recorded_at %r unparseable -- usage stays None",
            ticket_id,
            lease.recorded_at,
        )
        return Ok(None)
    window_end = now if now is not None else datetime.now(UTC)

    sessions = harness.discover_sessions(root, lease.worktree, window_start, window_end)
    if not sessions:
        _log.debug(
            "token_usage: %s no sessions found in window -- usage stays None",
            ticket_id,
        )
        return Ok(None)

    totals, session_ids, transcripts_seen, complete = _sum_sessions(
        root, ticket_id, harness, sessions
    )

    usage = TicketUsage(
        input_tokens=totals["input"],
        output_tokens=totals["output"],
        cache_creation_tokens=totals["cache_creation"],
        cache_read_tokens=totals["cache_read"],
        sessions=tuple(session_ids),
        transcripts_seen=tuple(transcripts_seen),
        window_start=_iso(window_start),
        window_end=_iso(window_end),
        collected_at=_iso(datetime.now(UTC)),
        complete=complete,
    )
    _log.info(
        "token_usage: %s collected input=%d output=%d cache_creation=%d "
        "cache_read=%d sessions=%d complete=%s",
        ticket_id,
        usage.input_tokens,
        usage.output_tokens,
        usage.cache_creation_tokens,
        usage.cache_read_tokens,
        len(usage.sessions),
        usage.complete,
    )
    return Ok(usage)


# frob:ticket T-5137
# frob:doc \
# docs/modules/tickets-lifecycle.md#automatic-per-ticket-token-accounting-t-5137  # noqa: E501
# tests/unit/test_token_usage.py::TestRecordTicketUsage.test_writes_usage_onto_ticket
def record_ticket_usage(
    root: Path, ticket_id: str, usage: TicketUsage | None
) -> Result[Ticket, UsageError]:
    """Persist `usage` onto `ticket_id`'s `Ticket.usage` field (T-5137).
    Called from `close`/`land` after `collect_ticket_usage`; a `None`
    `usage` is still written (idempotent no-op when the ticket already
    has no usage) rather than skipped, so a requeued ticket that lost its
    prior session window is not left showing a stale total."""
    from frob.tickets import _load_one

    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(UsageError.NoTicket)
    ticket = loaded.danger_ok
    if ticket.usage == usage:
        return Ok(ticket)
    updated = ticket.model_copy(update={"usage": usage})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        _log.error(
            "token_usage: failed to write usage onto %s: %s",
            ticket_id,
            write_result.danger_err,
        )
        return Err(UsageError.WriteFailed)
    return Ok(updated)
