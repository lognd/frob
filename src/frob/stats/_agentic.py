"""`frob stats --agentic`: non-gated aggregation over `.frob/telemetry.jsonl`
(T-0178). Report-only, like the rest of `frob.stats` -- no rule ids, nothing
here fails a gate. Reads whatever the CLI-timing hook (`frob.app.telemetry`)
and the Claude Code PostToolUse hook script (`scripts/frob-telemetry-hook`)
have appended to the shared stream and turns it into a breakdown a human can
use to decide what to speed up next.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/stats/_agentic.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/stats.md#public-api
TELEMETRY_REL = Path(".frob") / "telemetry.jsonl"
"""Path (relative to a repo root) the agentic report reads events from --
same relative path `frob.app.telemetry.TELEMETRY_REL` writes to."""

# frob:ticket T-0178
_CATEGORY_BY_PREFIX: tuple[tuple[str, str], ...] = (
    ("check", "frob-check"),
    ("test", "test-suite"),
    ("release", "native-build"),
    ("sys", "native-build"),
    ("gitlog", "vcs"),
    ("ticket land", "vcs"),
)


def _categorize(subcommand: str, args_head: str) -> str:
    """Bucket a CLI event into `frob-check` / `test-suite` / `native-build`
    / `vcs` / `other` by subcommand (and, for `ticket land`, its args head)
    -- the fixed category list T-0178 deliverable 5 asks the report to
    break command time down by."""
    combined = f"{subcommand} {args_head}".strip()
    for prefix, category in _CATEGORY_BY_PREFIX:
        if combined.startswith(prefix):
            return category
    return "other"


# frob:doc docs/modules/stats.md#public-api
class CategoryTime(BaseModel):
    """Total and count of CLI events observed in one time-category bucket."""

    model_config = ConfigDict(frozen=True)

    category: str
    total_ms: float
    count: int


# frob:doc docs/modules/stats.md#public-api
class TimeSink(BaseModel):
    """One slow CLI invocation, named for the "top wall-clock sinks" list."""

    model_config = ConfigDict(frozen=True)

    subcommand: str
    args_head: str
    duration_ms: float
    iso_ts: str


# frob:doc docs/modules/stats.md#public-api
class RetreadCandidate(BaseModel):
    """A `(subcommand, args_head, tree_hash)` triple that ran more than
    once with no tree change in between -- a cache-hit candidate quantifying
    the T-0177 daemon's potential payoff."""

    model_config = ConfigDict(frozen=True)

    subcommand: str
    args_head: str
    tree_hash: str
    run_count: int
    total_ms: float


# frob:doc docs/modules/stats.md#public-api
class TicketCycleTime(BaseModel):
    """Wall-clock between `created`/`started`/`done` telemetry events for
    one ticket id, in whatever subset of the three the stream recorded."""

    model_config = ConfigDict(frozen=True)

    ticket_id: str
    created_ts: str | None = None
    started_ts: str | None = None
    done_ts: str | None = None
    lead_time_s: float | None = None  # created -> done
    cycle_time_s: float | None = None  # started -> done


# frob:doc docs/modules/stats.md#public-api
class ToolTokens(BaseModel):
    """Cumulative estimated output tokens for one harness tool name, from
    PostToolUse hook events (T-0178 addendum a's len/4 heuristic)."""

    model_config = ConfigDict(frozen=True)

    tool: str
    total_tokens: int
    call_count: int


# frob:doc docs/modules/stats.md#public-api
class AgenticReport(BaseModel):
    """The full `frob stats --agentic` snapshot: time and token breakdowns
    over the local, non-gated telemetry stream."""

    model_config = ConfigDict(frozen=True)

    event_count: int
    category_time: tuple[CategoryTime, ...]
    top_time_sinks: tuple[TimeSink, ...]
    retread_candidates: tuple[RetreadCandidate, ...]
    ticket_cycle_times: tuple[TicketCycleTime, ...]
    tool_tokens: tuple[ToolTokens, ...]


def _load_events(root: Path) -> list[dict[str, Any]]:
    """Every valid JSON line in `root`'s telemetry stream; malformed lines
    are skipped with a debug log, never raised -- a hand-edited or
    partially-written telemetry file must not break `frob stats`."""
    path = root / TELEMETRY_REL
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            _log.debug("stats: telemetry line %d unparseable, skipped", lineno)
    return events


def _category_time(cli_events: list[dict[str, Any]]) -> tuple[CategoryTime, ...]:
    """Total duration and count per `_categorize` bucket, descending by time."""
    totals: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    for ev in cli_events:
        category = _categorize(ev.get("subcommand", ""), ev.get("args_head", ""))
        totals[category] += float(ev.get("duration_ms", 0.0))
        counts[category] += 1
    return tuple(
        CategoryTime(category=cat, total_ms=round(totals[cat], 3), count=counts[cat])
        for cat in sorted(totals, key=lambda c: -totals[c])
    )


def _top_time_sinks(
    cli_events: list[dict[str, Any]], limit: int
) -> tuple[TimeSink, ...]:
    """The `limit` slowest individual CLI invocations, descending."""
    ordered = sorted(cli_events, key=lambda e: -float(e.get("duration_ms", 0.0)))
    return tuple(
        TimeSink(
            subcommand=ev.get("subcommand", ""),
            args_head=ev.get("args_head", ""),
            duration_ms=float(ev.get("duration_ms", 0.0)),
            iso_ts=ev.get("iso_ts", ""),
        )
        for ev in ordered[:limit]
    )


# frob:ticket T-0874
def _retread_candidates(
    cli_events: list[dict[str, Any]],
) -> tuple[RetreadCandidate, ...]:
    """Group by `(subcommand, args_head, tree_hash)`; any group with more
    than one run is a retread candidate -- the same command re-run against
    an unchanged tree, exactly what a result cache would have skipped."""
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for ev in cli_events:
        key = (
            ev.get("subcommand", ""),
            ev.get("args_head", ""),
            ev.get("tree_hash", "unknown"),
        )
        groups[key].append(ev)
    candidates = [
        RetreadCandidate(
            subcommand=key[0],
            args_head=key[1],
            tree_hash=key[2],
            run_count=len(evs),
            total_ms=round(sum(float(e.get("duration_ms", 0.0)) for e in evs), 3),
        )
        for key, evs in groups.items()
        if len(evs) > 1 and key[2] != "unknown"
    ]
    candidates.sort(key=lambda c: -c.total_ms)
    return tuple(candidates)


def _parse_iso(ts: str) -> float | None:
    """Seconds-since-epoch for an `iso_now()`-shaped timestamp, or None."""
    from datetime import datetime

    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _group_ticket_marks(
    ticket_events: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    """First-seen ISO timestamp per `(ticket_id, event)` pair, grouped by
    ticket id -- the raw material `_ticket_cycle_times` turns into spans."""
    by_ticket: dict[str, dict[str, str]] = defaultdict(dict)
    for ev in ticket_events:
        ticket_id = ev.get("ticket_id")
        event = ev.get("event")
        ts = ev.get("iso_ts")
        if ticket_id and event and ts:
            by_ticket[ticket_id].setdefault(event, ts)
    return by_ticket


def _cycle_time_for(ticket_id: str, marks: dict[str, str]) -> TicketCycleTime:
    """One ticket's `TicketCycleTime` from its `created`/`started`/`done`
    marks, whichever subset is present."""
    created_ts = marks.get("created")
    started_ts = marks.get("started")
    done_ts = marks.get("done")
    created_s = _parse_iso(created_ts) if created_ts else None
    started_s = _parse_iso(started_ts) if started_ts else None
    done_s = _parse_iso(done_ts) if done_ts else None
    lead_time_s = round(done_s - created_s, 3) if created_s and done_s else None
    cycle_time_s = round(done_s - started_s, 3) if started_s and done_s else None
    return TicketCycleTime(
        ticket_id=ticket_id,
        created_ts=created_ts,
        started_ts=started_ts,
        done_ts=done_ts,
        lead_time_s=lead_time_s,
        cycle_time_s=cycle_time_s,
    )


def _ticket_cycle_times(
    ticket_events: list[dict[str, Any]],
) -> tuple[TicketCycleTime, ...]:
    """One `TicketCycleTime` per ticket id seen in the stream, from whatever
    subset of `created`/`started`/`done` events it recorded."""
    by_ticket = _group_ticket_marks(ticket_events)
    return tuple(
        _cycle_time_for(ticket_id, marks)
        for ticket_id, marks in sorted(by_ticket.items())
    )


def _tool_tokens(tool_events: list[dict[str, Any]]) -> tuple[ToolTokens, ...]:
    """Cumulative estimated output tokens per harness tool name, descending."""
    totals: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    for ev in tool_events:
        tool = ev.get("tool", "unknown")
        totals[tool] += int(ev.get("output_tokens_est", 0))
        counts[tool] += 1
    return tuple(
        ToolTokens(tool=tool, total_tokens=totals[tool], call_count=counts[tool])
        for tool in sorted(totals, key=lambda t: -totals[t])
    )


# frob:doc docs/modules/stats.md#public-api
def agentic_report(root: Path, *, top_n: int = 10) -> AgenticReport:
    """Aggregate `root`'s telemetry stream into an `AgenticReport`.

    Never fails: an absent or empty stream produces an all-zero report, not
    an error, since telemetry is diagnostics-only and must never block
    `frob stats` from running (T-0178 -- explicitly not a gate family).
    """
    events = _load_events(root)
    cli_events = [e for e in events if e.get("kind") == "cli"]
    ticket_events = [e for e in events if e.get("kind") == "ticket"]
    tool_events = [e for e in events if e.get("kind") == "tool"]

    return AgenticReport(
        event_count=len(events),
        category_time=_category_time(cli_events),
        top_time_sinks=_top_time_sinks(cli_events, top_n),
        retread_candidates=_retread_candidates(cli_events),
        ticket_cycle_times=_ticket_cycle_times(ticket_events),
        tool_tokens=_tool_tokens(tool_events),
    )


__all__ = [
    "AgenticReport",
    "CategoryTime",
    "RetreadCandidate",
    "TicketCycleTime",
    "TimeSink",
    "ToolTokens",
    "agentic_report",
]
