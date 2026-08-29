"""`frob stats --agentic`'s dispatch-cost half (T-1724, split out of
`frob.stats._agentic` by T-3059): joins the `kind="dispatch"` boundary
events `.claude/hooks/dispatch-telemetry.py` records against the
`kind="tool"`/`kind="ticket"` events `_agentic.py` already reads, and
derives per-dispatch/per-worktree cost -- tokens per landed ticket, the
cold-start floor, and marginal cost per resume. Report-only, same posture
as `_agentic.agentic_report`: never fails, never guesses a `0` where a
value is unmeasured (T-1703's sweep-reads-zero class, applied to cost).

`frob.stats.__init__` re-exports this module's public names, so callers
keep importing everything from `frob.stats` regardless of which submodule
actually owns a given symbol."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from frob.stats._agentic_shared import _completed_tool_events, _load_events, _parse_iso


# frob:doc docs/modules/stats.md#public-api
# frob:ticket T-3059
# frob:tests tests/test_stats_agentic.py::TestDispatchCostReport.test_tool_events_join_by_window_and_sum_tokens kind="unit"  # noqa: E501
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
# frob:ticket T-3059
# frob:tests tests/test_stats_agentic.py::TestDispatchCostReport.test_marginal_run_deltas_ordered_and_computed_per_worktree kind="unit"  # noqa: E501
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
# frob:ticket T-3059
# frob:tests tests/test_stats_agentic.py::TestDispatchCostReport.test_empty_stream_yields_empty_report kind="unit"  # noqa: E501
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


# frob:ticket T-3059
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


# frob:ticket T-3059
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


# frob:ticket T-3059
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


# frob:ticket T-3059
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


# frob:ticket T-3059
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


# frob:ticket T-3059
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


# frob:ticket T-3059
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


# frob:ticket T-3059
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


# frob:ticket T-3059
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
# frob:ticket T-3059
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
