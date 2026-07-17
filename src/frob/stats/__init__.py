"""frob.stats -- DORA-ish delivery measurement (T-0009).

Measurement only, never a gate: reports ticket-queue health and commit
cadence so a team can see delivery trends without frob passing judgment on
them (a thermometer, not a thermostat). Reads the ticket queue and git
history; adds no obligation.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.gitio import GitError, run_argv
from frob.logging import get_logger
from frob.tickets import TicketQueue, TicketState, load_queue

_log = get_logger(__name__)

_CONVENTIONAL_RE = re.compile(r"^([a-z]+)(\([^)]*\))?!?:")
_FAILURE_LINE_RE = re.compile(r"^- \d{4}-\d{2}-\d{2} attempt \d+:", re.MULTILINE)


class TicketStats(BaseModel):
    """Queue-health snapshot: state/kind counts and work-in-flight signals."""

    model_config = ConfigDict(frozen=True)

    total: int
    by_state: dict[str, int]
    by_kind: dict[str, int]
    doable: int
    blocked: int
    failure_entries: int


class CommitStats(BaseModel):
    """Commit cadence over a recent window, by conventional-commit type."""

    model_config = ConfigDict(frozen=True)

    window_days: int
    total: int
    per_week: float
    by_type: dict[str, int]


class StatsReport(BaseModel):
    """The combined delivery snapshot rendered by `frob stats`."""

    model_config = ConfigDict(frozen=True)

    tickets: TicketStats
    commits: CommitStats


def ticket_stats(queue: TicketQueue) -> TicketStats:
    """Compute queue-health counts from a loaded ticket queue (pure)."""
    tickets = list(queue.tickets.values())
    by_state: Counter[str] = Counter(t.state.value for t in tickets)
    by_kind: Counter[str] = Counter(t.kind.value for t in tickets)
    open_states = {
        s for s in TicketState if s not in (TicketState.DONE, TicketState.DROPPED)
    }
    blocked = sum(
        1
        for t in tickets
        if any(
            (b := queue.tickets.get(bid)) is None or b.state in open_states
            for bid in t.blocked_by
        )
        and t.state in open_states
    )
    doable = sum(
        1
        for t in tickets
        if t.state in (TicketState.QUEUED, TicketState.PLANNED)
        and not any(
            (b := queue.tickets.get(bid)) is None or b.state in open_states
            for bid in t.blocked_by
        )
    )
    failures = sum(len(_FAILURE_LINE_RE.findall(t.body)) for t in tickets)
    return TicketStats(
        total=len(tickets),
        by_state=dict(by_state),
        by_kind=dict(by_kind),
        doable=doable,
        blocked=blocked,
        failure_entries=failures,
    )


def commit_stats(root: Path, window_days: int = 30) -> Result[CommitStats, GitError]:
    """Count commits in the last `window_days` by conventional-commit type."""
    spawned = run_argv(
        [
            "git",
            "-C",
            str(root),
            "log",
            f"--since={window_days} days ago",
            "--format=%s",
        ],
        cwd=root,
        timeout_s=30.0,
    )
    if spawned.is_err:
        return Err(GitError.GitFailed)
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("stats: git log failed rc=%d", result.returncode)
        return Err(GitError.GitFailed)
    subjects = [line for line in result.stdout.splitlines() if line.strip()]
    by_type: Counter[str] = Counter()
    for subject in subjects:
        match = _CONVENTIONAL_RE.match(subject)
        by_type[match.group(1) if match else "other"] += 1
    per_week = round(len(subjects) / max(window_days / 7.0, 1e-9), 2)
    return Ok(
        CommitStats(
            window_days=window_days,
            total=len(subjects),
            per_week=per_week,
            by_type=dict(by_type),
        )
    )


def collect(root: Path, window_days: int = 30) -> Result[StatsReport, GitError]:
    """The full `frob stats` report: queue health + commit cadence."""
    queue_result = load_queue(root)
    tickets = (
        ticket_stats(queue_result.danger_ok)
        if queue_result.is_ok
        else TicketStats(
            total=0, by_state={}, by_kind={}, doable=0, blocked=0, failure_entries=0
        )
    )
    commits = commit_stats(root, window_days)
    if commits.is_err:
        return Err(commits.danger_err)
    return Ok(StatsReport(tickets=tickets, commits=commits.danger_ok))


__all__ = [
    "CommitStats",
    "StatsReport",
    "TicketStats",
    "collect",
    "commit_stats",
    "ticket_stats",
]
