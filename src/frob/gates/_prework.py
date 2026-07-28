"""Pre-work sweep storage (docs/modules/gates.md's PRE001 / `record_prework`).

**Deviation from docs/modules/gates.md**: the doc's prose suggested storing the
sweep digest "in the ticket body" via `frob.tickets`' record-style body
appender, but `frob.tickets` exposes only `record_failure` (a fixed
"## Failure log" section) -- no generic body-section appender, and
`frob.tickets` is explicitly out of scope for this phase (docs/rework.md's
cycle-avoidance: `frob.gates` may *read* tickets, but must not grow
`frob.tickets`'s public surface). The sweep is instead stored as JSON at
`.frob/prework/<ticket_id>.json`, one file per ticket, mirroring the
`.frob/coverage-stamp` posture used by TEST006. `prework_gate` reads it
back with `load_prework`.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_prework.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from typani import Err, Ok
from typani.result import Result
from typani.unit import Unit

from frob.gates._models import GateError, PreworkSweep
from frob.logging import get_logger

if TYPE_CHECKING:
    from frob.tickets import Ticket

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"

# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0584
# Default wall-clock budget for the per-scope-pattern xref half of
# `sweep_ticket`, comfortably under the ~90s per-stage foreground cap
# `docs/guides/agent-playbook.md` section 3b documents for this repo's own
# gate stages. This is what turns a slow-mount full sweep from "block until
# done or the caller's foreground timeout kills it" into "make as much
# progress as the budget allows, persist it, and let the next call resume".
DEFAULT_SWEEP_BUDGET_SECONDS = 60.0


def _prework_path(root: Path, ticket_id: str) -> Path:
    """The `.frob/prework/<ticket_id>.json` path for `ticket_id`."""
    return root / ".frob" / "prework" / f"{ticket_id}.json"


# frob:doc docs/modules/gates.md#public-api
def record_prework(
    root: Path, ticket_id: str, sweep: PreworkSweep
) -> Result[Unit, GateError]:
    """Persist `sweep` for `ticket_id`; called by `frob ticket start`."""
    path = _prework_path(root, ticket_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(sweep.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        _log.error("record_prework: could not write %s: %s", path, exc)
        return Err(GateError.WriteFailed)
    _log.info(
        "record_prework: %s sweep recorded (dup=%d, xref=%d) at %s",
        ticket_id,
        sweep.dup_findings,
        len(sweep.xref_hits),
        path,
    )
    return Ok(Unit())


# frob:ticket T-0240
def _scope_pattern_scan_path(root: Path, pattern: str) -> Path:
    """The directory (or file) a scope glob's literal, non-wildcard prefix
    resolves to under `root` (e.g. `"src/frob/tickets/**"` -> `root /
    "src/frob/tickets"`), used to bound both the xref real-symbol lookup and
    the exclude/skip-dir check to that subtree instead of the whole repo.
    """
    base = pattern.split("*", 1)[0].rstrip("/") or "."
    return root / base if base != "." else root


# frob:ticket T-0240
def _is_scan_path_pruned(
    root: Path, scan_path: Path, exclude_globs: tuple[str, ...]
) -> bool:
    """True if `scan_path` itself is a built-in skip dir or matches `[graph]
    exclude` -- so a poorly-scoped ticket glob (e.g. covering a vendored or
    generated tree) still cannot pull the sweep into walking it.
    """
    from frob.excludes import is_excluded, is_skipped_dir

    if scan_path == root:
        return False
    if is_skipped_dir(scan_path.name):
        return True
    if not exclude_globs:
        return False
    try:
        rel = scan_path.relative_to(root).as_posix()
    except ValueError:
        return False
    return is_excluded(rel, exclude_globs) or is_excluded(f"{rel}/.", exclude_globs)


# frob:ticket T-0240
def _real_symbol_for_scope_pattern(scan_path_rel: str, snapshot) -> str | None:
    """A real, graph-known public symbol name rooted under `scan_path_rel`,
    or `None` if the scope glob's subtree defines none.

    Replaces the old `Path(pattern).stem` guess (which produced nonsense
    xref terms like `"**"`, `"__init__"`, or `"README"` straight from glob
    syntax and filenames that were never symbols) with a lookup against the
    already-built obligation graph, so xref only ever searches for names
    that actually exist.
    """
    from frob.tickets import scope_matches

    candidates = sorted(
        record.id.qualname
        for record in snapshot.symbols.values()
        if record.public and scope_matches(record.id.path, [scan_path_rel])
    )
    return candidates[0] if candidates else None


# frob:ticket T-0361
def _xref_hit_for_scope_pattern(
    root: Path,
    ticket_id: str,
    pattern: str,
    exclude_globs: tuple[str, ...],
    snapshot,
) -> str | None:
    """The single xref hit `sweep_ticket` records for one scope glob `pattern`,
    or `None` if the pattern's scan path does not exist, is excluded/a
    skip-dir, resolves to no real symbol, or the bounded xref call finds
    nothing; split out of `sweep_ticket`'s loop body (T-0361)."""
    from frob.xref import xref

    scan_path = _scope_pattern_scan_path(root, pattern)
    if not scan_path.exists():
        return None
    if _is_scan_path_pruned(root, scan_path, exclude_globs):
        _log.debug(
            "sweep_ticket: %s skipping excluded/skip-dir scan path %s",
            ticket_id,
            scan_path,
        )
        return None
    symbol = None
    if snapshot is not None:
        try:
            scan_path_rel = scan_path.relative_to(root).as_posix()
        except ValueError:
            scan_path_rel = "."
        symbol = _real_symbol_for_scope_pattern(
            f"{scan_path_rel}/**" if scan_path_rel != "." else "**", snapshot
        )
    if symbol is None:
        return None
    xref_result = xref(symbol, scan_path)
    return xref_result.danger_ok.symbol if xref_result.is_ok else None


# frob:ticket T-0976
def _resume_or_start_sweep(
    root: Path, ticket: Ticket, all_patterns: list[str], digest: str
) -> tuple[list[str], list[str]]:
    """`(xref_hits, patterns_to_scan)` for `sweep_ticket`: resumes from a
    prior partial sweep's leftovers (T-0584) when one exists and its
    digest still matches `digest`, else starts fresh over every pattern in
    `all_patterns` with no prior hits."""
    previous = load_prework(root, ticket.id)
    if previous is not None and previous.partial and previous.digest == digest:
        patterns_to_scan = [p for p in previous.pending_patterns if p in all_patterns]
        _log.info(
            "sweep_ticket: %s resuming partial sweep (%d pattern(s) pending)",
            ticket.id,
            len(patterns_to_scan),
        )
        return list(previous.xref_hits), patterns_to_scan
    return [], all_patterns


# frob:ticket T-0976
def _bounded_xref_scan(
    root: Path,
    ticket_id: str,
    patterns_to_scan: list[str],
    exclude_globs,
    snapshot,
    xref_hits: list[str],
    started: float,
    budget_seconds: float | None,
) -> list[str]:
    """Run `_xref_hit_for_scope_pattern` over `patterns_to_scan`, appending
    hits onto `xref_hits` IN PLACE, until either every pattern is scanned
    or `budget_seconds` elapses since `started` (T-0584) -- returns the
    patterns left unscanned (empty if the budget was never hit)."""
    for i, pattern in enumerate(patterns_to_scan):
        if budget_seconds is not None and time.monotonic() - started > budget_seconds:
            pending_patterns = list(patterns_to_scan[i:])
            _log.warning(
                "sweep_ticket: %s exceeded %.1fs budget with %d pattern(s) "
                "remaining -- recording a partial sweep, resume with "
                "`frob ticket sweep %s`",
                ticket_id,
                budget_seconds,
                len(pending_patterns),
                ticket_id,
            )
            return pending_patterns
        hit = _xref_hit_for_scope_pattern(
            root, ticket_id, pattern, exclude_globs, snapshot
        )
        if hit is not None:
            xref_hits.append(hit)
    return []


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0236
# frob:ticket T-0240
# frob:tests tests/test_ticket_land.py::TestPreworkSweepRefresh.test_land_refreshes_stale_sweep_after_unrelated_main_change kind="unit"  # noqa: E501
# frob:tests tests/test_gates.py::TestPreworkSweepBounds.test_sweep_ticket_honors_graph_excludes  # noqa: E501
# frob:tests tests/test_gates.py::TestPreworkSweepBounds.test_sweep_ticket_skips_builtin_skip_dirs  # noqa: E501
# frob:tests tests/test_gates.py::TestPreworkSweepBounds.test_sweep_ticket_xref_hits_are_real_symbols  # noqa: E501
# frob:tests tests/test_gates.py::TestPreworkSweepBounds.test_sweep_ticket_partial_on_budget_exceeded  # noqa: E501
# frob:tests tests/test_gates.py::TestPreworkSweepBounds.test_sweep_ticket_resumes_pending_patterns  # noqa: E501
def sweep_ticket(
    root: Path,
    ticket: Ticket,
    budget_seconds: float | None = DEFAULT_SWEEP_BUDGET_SECONDS,
) -> Result[PreworkSweep, GateError]:
    """Recompute (dup findings, xref hits, scope digest) and persist `ticket`'s
    pre-work sweep against `root`'s CURRENT tree state, then record it via
    `record_prework`.

    T-0584: bounded and resumable. The per-scope-pattern xref loop is timed
    against `budget_seconds` (a wall-clock deadline measured from this
    call's start, `None` meaning unbounded -- used by tests and by any
    caller that deliberately wants a full synchronous sweep regardless of
    cost). If a previously-recorded sweep for this ticket is `partial` and
    its digest still matches the ticket's CURRENT scope digest, this resumes
    from its `pending_patterns` instead of rescanning patterns it already
    swept -- so a slow mount pays down the remaining work across however
    many bounded calls it takes, rather than a single caller ever being on
    the hook for the whole scan in one shot. Once the deadline is hit with
    patterns still remaining, this returns (and persists) a `partial=True`
    sweep instead of blocking -- `prework_gate` treats a partial sweep whose
    digest matches as provisionally clean, so PRE001 does not require the
    very sweep that timed out before it can be satisfied again.

    This is the single sweep-computation used by both `frob ticket
    start`/`sweep` (app/ticket_runner.py's `_run_sweep`, which this mirrors
    so the two call sites cannot desync -- see T-0236's Done report for the
    follow-up ticket filed to collapse that duplication) and `frob ticket
    land`'s post-merge, pre-close refresh: landing a ticket can pull in
    unrelated main commits that touch the ticket's scope globs, which moves
    the scope digest and would otherwise leave a stale-looking sweep behind
    if `land` fails after the merge and the ticket stays in-progress for a
    retry (T-0236 -- PRE001 stale-sweep churn in the multi-agent loop).

    T-0240: the xref half used to call `xref(symbol, root)` -- ALWAYS the
    full repo root regardless of the per-pattern `scan_path` it computed --
    so every scope pattern re-walked the entire tree including any
    `.venv`/`node_modules`/nested-worktree trees under it (measured at
    >13min on a real pilot scope vs 5.2s once bounded). It now bounds each
    xref call to that pattern's own `scan_path`, skips scan paths that are
    themselves built-in skip dirs or `[graph] exclude` matches (reusing
    `frob.excludes`, the one place that logic lives -- see its module
    docstring), and derives the xref search term from a real, graph-known
    public symbol in that subtree rather than a glob-syntax stem guess.
    """
    from frob.dup import find_duplicates
    from frob.excludes import load_exclude_globs
    from frob.gates import scope_digest
    from frob.graph import build_graph, load_graph

    started = time.monotonic()

    dup_result = find_duplicates(root)
    dup_findings = dup_result.total_clones

    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_err:
        loaded = build_graph(root, cache)
    snapshot = loaded.ok

    all_patterns = list(ticket.scope or (".",))
    digest = scope_digest(ticket.scope, snapshot) if snapshot is not None else ""

    xref_hits, patterns_to_scan = _resume_or_start_sweep(
        root, ticket, all_patterns, digest
    )
    exclude_globs = load_exclude_globs(root)
    pending_patterns = _bounded_xref_scan(
        root,
        ticket.id,
        patterns_to_scan,
        exclude_globs,
        snapshot,
        xref_hits,
        started,
        budget_seconds,
    )
    partial = bool(pending_patterns)

    sweep = PreworkSweep(
        date=date.today(),
        dup_findings=dup_findings,
        xref_hits=tuple(xref_hits),
        digest=digest,
        partial=partial,
        pending_patterns=tuple(pending_patterns),
    )
    recorded = record_prework(root, ticket.id, sweep)
    if recorded.is_err:
        return Err(recorded.danger_err)
    _log.info(
        "sweep_ticket: %s refreshed (dup=%d, xref=%d, partial=%s)",
        ticket.id,
        dup_findings,
        len(xref_hits),
        partial,
    )
    return Ok(sweep)


# frob:doc docs/modules/gates.md#public-api
def load_prework(root: Path, ticket_id: str) -> PreworkSweep | None:
    """The recorded sweep for `ticket_id`, or `None` if never recorded/unreadable."""
    path = _prework_path(root, ticket_id)
    if not path.exists():
        _log.debug("load_prework: no sweep recorded for %s", ticket_id)
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return PreworkSweep.model_validate(raw)
    except (OSError, ValueError) as exc:
        _log.warning("load_prework: %s unreadable: %s", path, exc)
        return None


__all__ = [
    "DEFAULT_SWEEP_BUDGET_SECONDS",
    "load_prework",
    "record_prework",
    "sweep_ticket",
]
