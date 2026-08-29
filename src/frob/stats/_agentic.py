"""`frob stats --agentic`: non-gated aggregation over `.frob/telemetry.jsonl`
(T-0178). Report-only, like the rest of `frob.stats` -- no rule ids, nothing
here fails a gate. Reads whatever the CLI-timing hook (`frob.app.telemetry`)
and the Claude Code PreToolUse/PostToolUse hook script
(`.claude/hooks/tool-call-telemetry.py`, T-2912) have appended to the shared
stream and turns it into a breakdown a human can use to decide what to
speed up next.
"""

# frob:ticket T-3059

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

# T-3059: dispatch-cost aggregation split into its own module (genuine
# concern boundary: joining dispatch/tool/ticket events into per-dispatch
# COST, vs this module's own per-category/per-tool TIME breakdown) --
# re-imported here (not just used internally) so `frob.stats.__init__`'s
# existing `from frob.stats._agentic import (..., DispatchCostReport, ...)`
# keeps resolving unchanged.
from frob.stats._agentic_dispatch import (  # noqa: F401 -- re-exported: frob.stats.__init__
    DispatchCostReport,
    DispatchRecord,
    MarginalRunDelta,
    dispatch_cost_report,
)

# T-3059: telemetry-line/timestamp/completed-event primitives shared with
# `_agentic_dispatch.py` live in `_agentic_shared` (a neutral module both
# import), not in either report module -- `_agentic_dispatch` importing
# them from HERE instead would make this module depend on the dispatch
# module and the dispatch module depend back on this one.
from frob.stats._agentic_shared import (
    TELEMETRY_REL,  # noqa: F401 -- re-exported: prior public surface of this module
    _completed_tool_events,
    _load_events,
    _parse_iso,
)

_log = get_logger(__name__)

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
# frob:tests tests/test_stats_agentic.py::test_tool_call_histogram_counts_completed_calls_by_shape  # noqa: E501
# frob:tests tests/test_stats_agentic.py::test_tool_call_histogram_counts_unmatched_pre_as_blocked  # noqa: E501
class ToolCallShape(BaseModel):
    """One `(tool, command_shape)` bucket from the `kind="tool"` stream
    (T-2912): how many times it completed, how many attempts never got a
    matching completion (`blocked_count` -- a `PreToolUse` denial or a call
    that never finished), how many completions re-ran at a `head_sha`
    already seen for this same shape (`rerun_same_tree_count` -- the
    general-purpose form of the existing `REDUNDANT_RERUN` footgun, which
    only ever covered `frob` CLI invocations), and cumulative estimated
    output tokens. `command_shape` is `None` for every non-`Bash` tool
    (`.claude/hooks/tool-call-telemetry.py` never shape-normalizes their
    arguments) and for a `Bash` call whose verb could not be extracted
    safely."""

    model_config = ConfigDict(frozen=True)

    tool: str
    command_shape: str | None
    call_count: int
    blocked_count: int
    rerun_same_tree_count: int
    output_tokens_total: int


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
    tool_call_histogram: tuple[ToolCallShape, ...]


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
    """Cumulative estimated output tokens per harness tool name, descending.
    `tool_events` must already be completed-only (see
    `_completed_tool_events`)."""
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


# frob:ticket T-2912
class _ToolCallTally:
    """Mutable accumulator for `_tool_call_histogram` (T-2912), split out
    so that function stays a thin orchestrator: one `Counter`/`set` bundle
    per `(tool, command_shape)` key for `call_count`, `blocked_count`,
    `rerun_same_tree_count`, and cumulative `output_tokens_est`."""

    def __init__(self) -> None:
        self.call_count: Counter[tuple[str, str | None]] = Counter()
        self.blocked_count: Counter[tuple[str, str | None]] = Counter()
        self.rerun_count: Counter[tuple[str, str | None]] = Counter()
        self.token_total: Counter[tuple[str, str | None]] = Counter()
        self.seen_heads: defaultdict[tuple[str, str | None], set[str]] = defaultdict(
            set
        )

    def _record_blocked(self, key: tuple[str, str | None]) -> None:
        """One `phase="pre"` attempt at `key` with no matching completion."""
        self.blocked_count[key] += 1

    def _record_completed(
        self, key: tuple[str, str | None], ev: dict[str, Any]
    ) -> None:
        """One completed call at `key`: tallies tokens and detects a rerun
        at a `head_sha` already seen for this same `key`."""
        self.call_count[key] += 1
        self.token_total[key] += int(ev.get("output_tokens_est", 0))
        head = ev.get("head_sha")
        if isinstance(head, str) and head and head != "unknown":
            if head in self.seen_heads[key]:
                self.rerun_count[key] += 1
            self.seen_heads[key].add(head)

    def _shapes(self) -> tuple[ToolCallShape, ...]:
        """Every accumulated key as a `ToolCallShape`, descending by
        `call_count`."""
        keys = set(self.call_count) | set(self.blocked_count)
        out = [
            ToolCallShape(
                tool=tool,
                command_shape=shape,
                call_count=self.call_count[(tool, shape)],
                blocked_count=self.blocked_count[(tool, shape)],
                rerun_same_tree_count=self.rerun_count[(tool, shape)],
                output_tokens_total=self.token_total[(tool, shape)],
            )
            for tool, shape in keys
        ]
        return tuple(sorted(out, key=lambda s: -s.call_count))


def _accumulate_dispatch_tool_events(
    tally: _ToolCallTally, evs: list[dict[str, Any]]
) -> None:
    """One dispatch's worth of `evs` (already `iso_ts`-sorted), folded into
    `tally` -- the sequential pre/post pairing rule `_tool_call_histogram`
    documents, split out purely to keep that function's own body short."""
    pending_pre: tuple[str, str | None] | None = None
    for ev in evs:
        key = (str(ev.get("tool", "unknown")), ev.get("command_shape"))
        if ev.get("phase") == "pre":
            if pending_pre is not None:
                tally._record_blocked(pending_pre)
            pending_pre = key
            continue
        pending_pre = None
        tally._record_completed(key, ev)
    if pending_pre is not None:
        tally._record_blocked(pending_pre)


def _tool_call_histogram(
    raw_tool_events: list[dict[str, Any]],
) -> tuple[ToolCallShape, ...]:
    """Per-`(tool, command_shape)` histogram (T-2912) over the RAW
    `kind="tool"` stream, both phases -- this is the one place `phase="pre"`
    events get used, to answer the three questions
    `_tool_tokens`/`dispatch_cost_report` cannot: which shapes dominate call
    COUNT, how many attempts of a shape were blocked/never completed, and
    how many completions re-ran at a `head_sha` already seen for that same
    shape.

    Pairing is sequential per `dispatch_id` (events are grouped, then
    sorted by `iso_ts`, then folded by `_accumulate_dispatch_tool_events`):
    a `phase="pre"` event is presumed matched by the very next event for
    that dispatch if it is a `phase="post"`; if instead ANOTHER
    `phase="pre"` (or the dispatch's own event stream ends) follows
    without an intervening `phase="post"`, the first `pre` is counted as
    `blocked_count` for its own `(tool, command_shape)` -- a real completed
    call always produces its `post` event immediately after its own `pre`
    in a single-threaded agent session, so an unmatched `pre` is exactly a
    denied-then-abandoned or denied-then-retried-as-a-different-shape
    attempt. A `phase`-less legacy event (pre-T-2912 stream shape) is
    treated as a completed call directly, matching `_completed_tool_events`.
    """
    by_dispatch: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for ev in raw_tool_events:
        by_dispatch[str(ev.get("dispatch_id", "unknown"))].append(ev)

    tally = _ToolCallTally()
    for evs in by_dispatch.values():
        # frob:waive PERF004 reason="each iteration sorts a DIFFERENT dispatch's own \
        # event list -- there is nothing to hoist, this is N independent sorts of N \
        # disjoint lists, not one list re-sorted N times"
        ordered = sorted(evs, key=lambda e: e.get("iso_ts") or "")
        _accumulate_dispatch_tool_events(tally, ordered)
    return tally._shapes()


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
    raw_tool_events = [e for e in events if e.get("kind") == "tool"]
    tool_events = _completed_tool_events(events)

    return AgenticReport(
        event_count=len(events),
        category_time=_category_time(cli_events),
        top_time_sinks=_top_time_sinks(cli_events, top_n),
        retread_candidates=_retread_candidates(cli_events),
        ticket_cycle_times=_ticket_cycle_times(ticket_events),
        tool_tokens=_tool_tokens(tool_events),
        tool_call_histogram=_tool_call_histogram(raw_tool_events),
    )


__all__ = [
    "AgenticReport",
    "CategoryTime",
    "DispatchCostReport",
    "DispatchRecord",
    "MarginalRunDelta",
    "RetreadCandidate",
    "TicketCycleTime",
    "TimeSink",
    "ToolCallShape",
    "ToolTokens",
    "agentic_report",
    "dispatch_cost_report",
]
