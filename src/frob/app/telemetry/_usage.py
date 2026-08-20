"""Corpus-wide usage aggregation (T-1360's `frob doctor usage`
deliverable), split out of the former monolithic `telemetry.py` by
T-2694 (T-1656 LARGE001 successor): read-only over the event stream
`frob.app.telemetry` (event recording, this package's `__init__.py`)
writes, distinct from `_footguns.py`'s bounded-lookback per-invocation
detection -- this module always scans the WHOLE corpus. Re-exported
from `frob.app.telemetry` unchanged (see that module's own docstring)
so no pre-existing caller needs editing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from frob.logging import get_logger

from . import _telemetry_path
from ._footguns import _FAST_EXIT_MS, _REPEATED_FAILURE_STREAK

_log = get_logger(__name__)


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_usage_report_aggregates_time_and_failures  # noqa: E501
class SubcommandTimeSink(BaseModel):
    """One subcommand's aggregate cost across the whole corpus (T-1360's
    `frob doctor usage` deliverable) -- ranked by `total_duration_ms`
    descending in `UsageReport.top_time_sinks`."""

    model_config = {}

    subcommand: str
    calls: int
    total_duration_ms: float
    failures: int


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_usage_report_empty_corpus_is_all_zero
class UsageReport(BaseModel):
    """`frob doctor usage`'s report (T-1360's fourth delivery requirement):
    top time sinks and footgun totals mined from the local telemetry
    corpus -- the same numbers T-1360's own Description mined by hand
    (2.55h wasted on redundant re-runs, 756 fast-exit-1 runs, 11% overall
    failure rate) are now a command, not an ad-hoc script."""

    model_config = {}

    total_calls: int
    total_duration_ms: float
    failures: int
    failure_rate: float
    top_time_sinks: list[SubcommandTimeSink]
    redundant_rerun_count: int
    redundant_rerun_wasted_ms: float
    fast_exit1_count: int
    repeated_failure_streaks: int


# frob:ticket T-1360
def _all_cli_events(root: Path) -> list[dict[str, Any]]:
    """Every `kind=\"cli\"` record in `root`'s telemetry stream, oldest
    first -- `usage_report`'s corpus-wide scan needs the whole history, not
    `_read_recent_cli_events`'s bounded lookback window."""
    path = _telemetry_path(root)
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _log.debug("telemetry: read failed (ignored): %s", exc)
        return []
    events: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("kind") == "cli":
            events.append(record)
    return events


def _top_time_sinks(
    events: list[dict[str, Any]], *, top_n: int
) -> list[SubcommandTimeSink]:
    """Per-subcommand call count/total duration/failure count from `events`,
    the `top_n` costliest by total duration, descending -- `usage_report`'s
    time-sink ranking."""
    by_subcommand: dict[str, list[float | int]] = {}
    for e in events:
        sub = str(e.get("subcommand", ""))
        bucket = by_subcommand.setdefault(sub, [0, 0.0, 0])
        bucket[0] = int(bucket[0]) + 1
        bucket[1] = float(bucket[1]) + float(e.get("duration_ms", 0.0))
        if e.get("exit") != 0:
            bucket[2] = int(bucket[2]) + 1
    return sorted(
        (
            SubcommandTimeSink(
                subcommand=sub,
                calls=int(calls),
                total_duration_ms=float(dur),
                failures=int(fails),
            )
            for sub, (calls, dur, fails) in by_subcommand.items()
        ),
        key=lambda s: s.total_duration_ms,
        reverse=True,
    )[:top_n]


def _redundant_rerun_totals(events: list[dict[str, Any]]) -> tuple[int, float]:
    """(count, wasted_ms) for `events` whose `(subcommand, args_head,
    tree_hash, home_config_hash, external_path_hash)` repeats an EARLIER
    event exactly (T-2191 added `home_config_hash`, T-2204 added
    `external_path_hash`, both matching `_tip_redundant_rerun`'s own key
    -- see its docstring for why) -- each repeat after the first is
    provably redundant (neither the repo tree, `~/.claude`, nor any
    external PATH argument the command line named had changed). An older
    event recorded before T-2191/T-2204 has no `home_config_hash`/
    `external_path_hash` field at all; `.get(..., "")` reads that as the
    empty string on both sides consistently, so two such legacy events
    can still match each other (degrading gracefully to the older,
    narrower comparison for old data), but a legacy event never
    spuriously matches a post-fix one (whose digest fields are never the
    empty string)."""
    seen: dict[tuple[str, str, str, str, str], bool] = {}
    redundant_count = 0
    redundant_wasted_ms = 0.0
    for e in events:
        key = (
            str(e.get("subcommand", "")),
            str(e.get("args_head", "")),
            str(e.get("tree_hash", "")),
            str(e.get("home_config_hash", "")),
            str(e.get("external_path_hash", "")),
        )
        if key in seen:
            redundant_count += 1
            redundant_wasted_ms += float(e.get("duration_ms", 0.0))
        else:
            seen[key] = True
    return redundant_count, redundant_wasted_ms


def _repeated_failure_streak_count(events: list[dict[str, Any]]) -> int:
    """How many times a run of `_REPEATED_FAILURE_STREAK`-or-more
    consecutive identical `(subcommand, args_head)` failures occurs across
    `events`, with no intervening success resetting the streak."""
    streak_key: tuple[str, str] | None = None
    streak_len = 0
    repeated_failure_streaks = 0
    for e in events:
        key2 = (str(e.get("subcommand", "")), str(e.get("args_head", "")))
        if e.get("exit") != 0 and key2 == streak_key:
            streak_len += 1
            if streak_len == _REPEATED_FAILURE_STREAK:
                repeated_failure_streaks += 1
        elif e.get("exit") != 0:
            streak_key = key2
            streak_len = 1
        else:
            streak_key = None
            streak_len = 0
    return repeated_failure_streaks


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:waive AFFECT001 reason="T-1465 is a pure ARCH001 line-count split (extracted \
# _top_time_sinks/_redundant_rerun_totals/ _repeated_failure_streak_count helpers, \
# preserving behavior verbatim, 26 tests in tests/test_telemetry.py still green); the \
# documented public contract is unchanged, so \
# docs/guides/agentic-time-profiling.md#public-api needs no update"
# frob:tests tests/test_telemetry.py::test_usage_report_aggregates_time_and_failures  # noqa: E501
# frob:tests tests/test_telemetry.py::test_usage_report_counts_redundant_reruns
def usage_report(root: Path, *, top_n: int = 10) -> UsageReport:
    """Aggregate `root`'s whole telemetry corpus into a `UsageReport`
    (T-1360): per-subcommand time sinks, provably-redundant re-run cost
    (identical `(subcommand, args_head, tree_hash)` seen twice), fast-exit
    failures, and stuck-repeat streaks. Read-only, corpus-wide, and cheap
    relative to the run it summarizes -- a single linear pass over the
    file. Empty/missing corpus yields an all-zero report, never an error."""
    events = _all_cli_events(root)
    total_calls = len(events)
    total_duration_ms = sum(float(e.get("duration_ms", 0.0)) for e in events)
    failures = sum(1 for e in events if e.get("exit") != 0)
    failure_rate = (failures / total_calls) if total_calls else 0.0

    top_time_sinks = _top_time_sinks(events, top_n=top_n)
    redundant_count, redundant_wasted_ms = _redundant_rerun_totals(events)
    fast_exit1_count = sum(
        1
        for e in events
        if e.get("exit") != 0 and float(e.get("duration_ms", 0.0)) < _FAST_EXIT_MS
    )
    repeated_failure_streaks = _repeated_failure_streak_count(events)

    return UsageReport(
        total_calls=total_calls,
        total_duration_ms=total_duration_ms,
        failures=failures,
        failure_rate=failure_rate,
        top_time_sinks=top_time_sinks,
        redundant_rerun_count=redundant_count,
        redundant_rerun_wasted_ms=redundant_wasted_ms,
        fast_exit1_count=fast_exit1_count,
        repeated_failure_streaks=repeated_failure_streaks,
    )


