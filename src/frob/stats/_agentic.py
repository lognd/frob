"""`frob stats --agentic`: non-gated aggregation over `.frob/telemetry.jsonl`
(T-0178). Report-only, like the rest of `frob.stats` -- no rule ids, nothing
here fails a gate. Reads whatever the CLI-timing hook (`frob.app.telemetry`)
and the Claude Code PreToolUse/PostToolUse hook script
(`.claude/hooks/tool-call-telemetry.py`, T-2912) have appended to the shared
stream and turns it into a breakdown a human can use to decide what to
speed up next.
"""

# frob:ticket T-3026
# frob:debt LARGE001 reason="pre-existing debt, not introduced by the T-3006/T-2995/T-3014 batch this ticket cleans up after: verified via git history the file was already 802 lines (over the 800 threshold) BEFORE that batch landed. A real split of this report-aggregation module is a separate follow-up." ticket="T-3059"  # noqa: E501

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
        except Exception:
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
    except Exception:
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


# frob:doc docs/modules/stats.md#public-api
class DispatchRecord(BaseModel):
    """One dispatch's cost, joined against delivery (T-1724): the span
    between one `kind="dispatch"` `event="start"`/`event="end"` pair, plus
    every `kind="tool"`/`kind="ticket"` event whose `iso_ts` fell inside
    that span.

    `output_tokens_delta` is explicitly a PER-RUN figure (this dispatch's
    own tool-call tokens, not a running total across resumes) -- named
    `_delta` rather than a bare `tokens` precisely so a reader never has to
    infer which kind of counter it is by watching whether it goes up
    (2026-08-07's ordering-and-cumulative-vs-delta incident). `None` means
    "no tool events fell inside this dispatch's window" -- could not
    measure, never rendered as the number `0` (T-1703's sweep-reads-zero
    class, applied here to cost instead of coverage). `tool_call_count` is
    always a real integer (including a genuine `0`) since it is a count of
    observed events, not a derived sum -- absence of events in a bounded
    window is itself the measurement."""

    model_config = ConfigDict(frozen=True)

    dispatch_id: str
    worktree: str | None = None
    branch: str | None = None
    cold_start: bool | None = None
    start_ts: str | None = None
    end_ts: str | None = None
    wall_clock_s: float | None = None
    output_tokens_delta: int | None = None
    tool_call_count: int
    tickets_delivered: tuple[str, ...] = ()


# frob:doc docs/modules/stats.md#public-api
class MarginalRunDelta(BaseModel):
    """The token-cost delta between one dispatch and the PREVIOUS dispatch
    against the same worktree (T-1724's "marginal cost of run N vs N+1"
    deliverable) -- `run_index` is 1-based, ordered by `start_ts` within
    the worktree group (explicit ordering, never left for the reader to
    reconstruct). `marginal_tokens_delta` is `None` for the first run in a
    worktree (no previous run to compare against) or whenever either run's
    `output_tokens_delta` could not be measured -- never a guessed `0`."""

    model_config = ConfigDict(frozen=True)

    worktree: str
    run_index: int
    dispatch_id: str
    output_tokens_delta: int | None
    marginal_tokens_delta: int | None


# frob:doc docs/modules/stats.md#public-api
class DispatchCostReport(BaseModel):
    """T-1724's join of cost against delivery: `dispatches` ordered by
    `start_ts` (unparseable/missing timestamps sort last, deterministically
    by `dispatch_id`), plus the derived numbers `AgenticReport` alone could
    not produce. Every ratio/average field is `None`, never `0.0`, when its
    inputs contain no measured dispatch -- a genuinely-zero average and an
    unmeasurable one are different facts and this schema keeps them
    distinct."""

    model_config = ConfigDict(frozen=True)

    dispatches: tuple[DispatchRecord, ...]
    tokens_per_landed_ticket: float | None
    zero_delivery_dispatch_ids: tuple[str, ...]
    cold_start_floor_tokens: float | None
    marginal_run_deltas: tuple[MarginalRunDelta, ...]


def _group_dispatch_marks(
    dispatch_events: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """First-seen `start`/`end` fields per dispatch id -- the raw material
    `_dispatch_records` turns into `DispatchRecord`s. `setdefault` on every
    field (not just the timestamp) so a duplicate `start` event -- a hook
    firing twice -- cannot silently overwrite the first-recorded
    worktree/branch/cold_start with a second, possibly-stale one."""
    by_id: dict[str, dict[str, Any]] = defaultdict(dict)
    for ev in dispatch_events:
        dispatch_id = ev.get("dispatch_id")
        event = ev.get("event")
        if not dispatch_id or not event:
            continue
        bucket = by_id[dispatch_id]
        if event == "start":
            bucket.setdefault("start_ts", ev.get("iso_ts"))
            bucket.setdefault("worktree", ev.get("worktree"))
            bucket.setdefault("branch", ev.get("branch"))
            bucket.setdefault("cold_start", ev.get("cold_start"))
        elif event == "end":
            bucket.setdefault("end_ts", ev.get("iso_ts"))
    return by_id


def _events_in_window(
    events: list[dict[str, Any]], start_s: float | None, end_s: float | None
) -> list[dict[str, Any]]:
    """Every event in `events` whose `iso_ts` parses and falls within
    `[start_s, end_s]` -- `[]` (never all/none guessed) when either bound
    is unparseable, since a dispatch with no measurable span cannot
    honestly attribute any event to itself."""
    if start_s is None or end_s is None:
        return []
    matched = []
    for ev in events:
        ts = _parse_iso(ev.get("iso_ts", ""))
        if ts is not None and start_s <= ts <= end_s:
            matched.append(ev)
    return matched


def _dispatch_record(
    dispatch_id: str,
    marks: dict[str, Any],
    tool_events: list[dict[str, Any]],
    ticket_events: list[dict[str, Any]],
) -> DispatchRecord:
    """One dispatch's full `DispatchRecord`, joining `marks` (this
    dispatch's own start/end fields) against every tool/ticket event whose
    timestamp falls inside its window."""
    start_ts = marks.get("start_ts")
    end_ts = marks.get("end_ts")
    start_s = _parse_iso(start_ts) if start_ts else None
    end_s = _parse_iso(end_ts) if end_ts else None
    wall_clock_s = (
        round(end_s - start_s, 3) if start_s is not None and end_s is not None else None
    )

    matched_tools = _events_in_window(tool_events, start_s, end_s)
    tool_call_count = len(matched_tools)
    output_tokens_delta = (
        sum(int(ev.get("output_tokens_est", 0)) for ev in matched_tools)
        if tool_call_count > 0
        else None
    )

    delivered = tuple(
        sorted(
            {
                ev.get("ticket_id")
                for ev in _events_in_window(ticket_events, start_s, end_s)
                if ev.get("event") in ("done", "dropped") and ev.get("ticket_id")
            }
        )
    )

    return DispatchRecord(
        dispatch_id=dispatch_id,
        worktree=marks.get("worktree"),
        branch=marks.get("branch"),
        cold_start=marks.get("cold_start"),
        start_ts=start_ts,
        end_ts=end_ts,
        wall_clock_s=wall_clock_s,
        output_tokens_delta=output_tokens_delta,
        tool_call_count=tool_call_count,
        tickets_delivered=delivered,
    )


def _dispatch_sort_key(record: DispatchRecord) -> tuple[int, float | str]:
    """Sort key for `DispatchRecord` ordering (T-1724's "explicit ordering"
    requirement): a real, parseable `start_ts` sorts first by its epoch
    seconds; a missing/unparseable one sorts after every measured dispatch,
    deterministically by `dispatch_id` rather than landing in an
    arbitrary/input-dependent position."""
    start_s = _parse_iso(record.start_ts) if record.start_ts else None
    if start_s is not None:
        return (0, start_s)
    return (1, record.dispatch_id)


def _dispatch_records(
    dispatch_events: list[dict[str, Any]],
    tool_events: list[dict[str, Any]],
    ticket_events: list[dict[str, Any]],
) -> tuple[DispatchRecord, ...]:
    """One `DispatchRecord` per dispatch id seen in the stream, ordered by
    `_dispatch_sort_key` (start_ts, missing-last)."""
    by_id = _group_dispatch_marks(dispatch_events)
    records = [
        _dispatch_record(dispatch_id, marks, tool_events, ticket_events)
        for dispatch_id, marks in by_id.items()
    ]
    records.sort(key=lambda record: _dispatch_sort_key(record))
    return tuple(records)


def _tokens_per_landed_ticket(dispatches: tuple[DispatchRecord, ...]) -> float | None:
    """Total measured `output_tokens_delta` across every dispatch divided
    by the total count of tickets delivered -- `None` (not `0.0`) when no
    dispatch has BOTH a measured token cost and at least one delivered
    ticket, since a ratio with an empty denominator is not a zero, it is
    unanswerable."""
    total_tokens = 0
    total_tickets = 0
    for d in dispatches:
        if d.output_tokens_delta is None:
            continue
        total_tokens += d.output_tokens_delta
        total_tickets += len(d.tickets_delivered)
    if total_tickets == 0:
        return None
    return round(total_tokens / total_tickets, 1)


def _zero_delivery_dispatch_ids(
    dispatches: tuple[DispatchRecord, ...],
) -> tuple[str, ...]:
    """Dispatch ids that measurably spent tokens (`output_tokens_delta`
    is a real, positive number) but delivered zero tickets -- T-1724's
    "the signal that actually matters for retirement." A dispatch whose
    tokens could not be measured is excluded rather than assumed to have
    consumed budget -- an unmeasured cost is not evidence of waste."""
    return tuple(
        d.dispatch_id
        for d in dispatches
        if not d.tickets_delivered
        and d.output_tokens_delta is not None
        and d.output_tokens_delta > 0
    )


def _cold_start_floor_tokens(dispatches: tuple[DispatchRecord, ...]) -> float | None:
    """Mean measured token cost among dispatches that delivered zero
    tickets (T-1724's "cold-start floor: cost of a dispatch that landed
    nothing"). `None` when no zero-delivery dispatch has a measured token
    cost -- an empty floor is unmeasured, not free."""
    zero_delivery_measured = [
        d.output_tokens_delta
        for d in dispatches
        if not d.tickets_delivered and d.output_tokens_delta is not None
    ]
    if not zero_delivery_measured:
        return None
    return round(sum(zero_delivery_measured) / len(zero_delivery_measured), 1)


def _marginal_run_deltas(
    dispatches: tuple[DispatchRecord, ...],
) -> tuple[MarginalRunDelta, ...]:
    """One `MarginalRunDelta` per dispatch that names a worktree, grouped
    by worktree and ordered by `_dispatch_sort_key` within each group
    (T-1724's "marginal cost of run N vs run N+1 for the same agent" --
    `worktree` is the stable identity a resumed agent keeps across runs,
    unlike `dispatch_id`, which is fresh every time).

    `dispatches` arrives already sorted by `_dispatch_sort_key`
    (`_dispatch_records`'s own contract) -- grouping with a plain
    `defaultdict` preserves that order per worktree (dict insertion order
    is stable), so no second `sorted()` call is needed per group (PERF004:
    a sort call inside a loop)."""
    by_worktree: dict[str, list[DispatchRecord]] = defaultdict(list)
    for d in dispatches:
        if d.worktree:
            by_worktree[d.worktree].append(d)

    results: list[MarginalRunDelta] = []
    for worktree in sorted(by_worktree):
        previous_tokens: int | None = None
        for run_index, d in enumerate(by_worktree[worktree], start=1):
            marginal = (
                d.output_tokens_delta - previous_tokens
                if previous_tokens is not None and d.output_tokens_delta is not None
                else None
            )
            results.append(
                MarginalRunDelta(
                    worktree=worktree,
                    run_index=run_index,
                    dispatch_id=d.dispatch_id,
                    output_tokens_delta=d.output_tokens_delta,
                    marginal_tokens_delta=marginal,
                )
            )
            if d.output_tokens_delta is not None:
                previous_tokens = d.output_tokens_delta
    return tuple(results)


# frob:doc docs/modules/stats.md#public-api
# frob:ticket T-1724
# frob:tests tests/test_stats_agentic.py::TestDispatchCostReport.test_empty_stream_yields_empty_report  # noqa: E501
# frob:tests tests/test_stats_agentic.py::TestDispatchCostReport.test_dispatch_with_no_tool_events_has_unmeasured_not_zero_tokens  # noqa: E501
# frob:tests tests/test_stats_agentic.py::TestDispatchCostReport.test_tool_events_join_by_window_and_sum_tokens  # noqa: E501
# frob:tests tests/test_stats_agentic.py::TestDispatchCostReport.test_delivered_tickets_join_by_window  # noqa: E501
# frob:tests tests/test_stats_agentic.py::TestDispatchCostReport.test_zero_delivery_dispatch_flagged_only_when_measurably_costly  # noqa: E501
# frob:tests \
# tests/test_stats_agentic.py::TestDispatchCostReport.test_tokens_per_landed_ticket
# frob:tests tests/test_stats_agentic.py::TestDispatchCostReport.test_marginal_run_deltas_ordered_and_computed_per_worktree  # noqa: E501
# frob:tests tests/test_stats_agentic.py::TestDispatchCostReport.test_dispatches_ordered_by_start_ts_missing_last  # noqa: E501
# frob:tests tests/test_stats_agentic.py::TestDispatchCostReport.test_malformed_lines_skipped_not_raised  # noqa: E501
# frob:ticket T-1787
# frob:waive AFFECT001 reason="T-1787 adds a caller (stats_runner.py's --agentic text \
# renderer) and a one-line docstring note; the DispatchCostReport schema itself and \
# its docs/modules/stats.md#public-api anchor are unchanged"
def dispatch_cost_report(root: Path) -> DispatchCostReport:
    """T-1724: join `kind="dispatch"` boundary events against `kind="tool"`
    (cost) and `kind="ticket"` (delivery) events in the same telemetry
    stream `agentic_report` already reads, and derive the numbers the
    ticket asks for -- tokens per landed ticket, the cold-start floor,
    marginal cost per resume, and dispatches that spent budget landing
    nothing.

    Never fails, same posture as `agentic_report`: an absent/empty stream,
    or one with no `kind="dispatch"` events at all (e.g. telemetry
    disabled, or no Claude Code session recorded yet), produces an
    all-empty/all-`None` report, never an error and never a
    silently-zeroed cost. Called from `frob stats --agentic`'s plain-text
    renderer (`src/frob/app/stats_runner.py`, T-1787) in addition to the
    existing `--json` path."""
    events = _load_events(root)
    dispatch_events = [e for e in events if e.get("kind") == "dispatch"]
    tool_events = _completed_tool_events(events)
    ticket_events = [e for e in events if e.get("kind") == "ticket"]

    dispatches = _dispatch_records(dispatch_events, tool_events, ticket_events)
    return DispatchCostReport(
        dispatches=dispatches,
        tokens_per_landed_ticket=_tokens_per_landed_ticket(dispatches),
        zero_delivery_dispatch_ids=_zero_delivery_dispatch_ids(dispatches),
        cold_start_floor_tokens=_cold_start_floor_tokens(dispatches),
        marginal_run_deltas=_marginal_run_deltas(dispatches),
    )


def _completed_tool_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every `kind="tool"` event that represents a COMPLETED call -- i.e.
    every event with no `phase` field at all (the pre-T-2912 shape, which
    only ever recorded completions) plus every `phase="post"` event
    (T-2912's `.claude/hooks/tool-call-telemetry.py`). `phase="pre"`
    events are attempts, not completions, and must be excluded here so a
    blocked/retried call is not double-counted as two calls' worth of cost
    -- `_tool_call_histogram` (below) is where `phase="pre"` events earn
    their keep, for retry/blocked detection specifically."""
    return [e for e in events if e.get("kind") == "tool" and e.get("phase") != "pre"]


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
