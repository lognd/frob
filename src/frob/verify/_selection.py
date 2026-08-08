"""T-1689: batch test selection -- run a batch's union touched-set in ONE
pytest process, the second and independent half of the T-1686 epic's
wall-clock saving alongside T-1688's coalescing verify pass.

THE SAVING THIS CLOSES: `frob test` run N separate times (once per queued
`VerifyQueueEntry`) pays N cold pytest startups and re-runs every test two
tickets both touch once PER TICKET. Computing the UNION of every entry's
`touched_symbols` first and selecting once against that union collapses
this to one collection, one conftest evaluation, one set of session
fixtures -- on a batch of five tickets touching adjacent modules this is
usually the LARGER of the two savings in the epic (T-1688's own coalesce
only amortizes the gate pass, not the test run).

REUSE, NOT REINVENTION. This module does not re-derive symbolic
reachability -- `frob.testing._select.select_tests` and `frob.testing.
_runners.run_selected` already implement "resolve touched symbols to the
tests that reach them" and "spawn each language's selected tests in ONE
process" respectively. The one genuinely new piece here is bridging a
BATCH's union `touched_symbols` (a `frozenset[str]` of already-resolved
symrefs, `VerifyQueueEntry`'s own durable record -- no raw diff hunks
survive to batch time) into `select_tests`'s hunk-based `Diff` input:
`_synthetic_diff_for_touched_symbols` builds a `Hunk` spanning exactly
each touched symbol's own definition span, so `select_tests`'s own first
step (`_touched_symbols`, span-overlap against the snapshot) re-derives
that SAME symbol back out -- a faithful round-trip, not an approximation.

SYMBOLIC, NEVER LEXICAL. The union is a symbol-id set the whole way
through; nothing in this module compares file paths, filenames, or
source text to decide relevance -- `select_tests`'s own reachability walk
(`frob.graph`) is the only thing that ever answers "which tests does this
concern".

UNMEASURABLE IS NEVER A NARROWER RUN. If the graph cannot be loaded/built
at all, `select_batch_tests` returns `Err(BatchSelectionError.
GraphUnavailable)` -- the caller's job is to fall back to the FULL suite
and say so loudly (T-1689's own acceptance: "if the selection cannot be
computed ... fall back to the full suite and say so loudly, never to a
narrower set"), never to silently run nothing or a partial set."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.gitio import Diff, Hunk
from frob.graph import GraphSnapshot
from frob.logging import get_logger
from frob.testing._models import SelectConfig, SelectionReport, TestRunReport
from frob.verify._watermark import VerifyQueueEntry

_log = get_logger(__name__)


# frob:doc docs/modules/tickets.md#batch-test-selection-t-1689
class BatchSelectionError(ErrorSet):
    """Fallible outcomes of `select_batch_tests`/`run_batch_selected_tests`."""

    GraphUnavailable = (
        "the reference graph could not be loaded/built for batch test selection"
    )
    RunnersUnavailable = "test.runner config could not be loaded"


# frob:doc docs/modules/tickets.md#batch-test-selection-t-1689
class BatchSelection(BaseModel):
    """The union-touched-set selection for one batch of `VerifyQueueEntry`
    records -- `report` is the same `SelectionReport` shape a single-entry
    `frob test` run already produces (so `run_selected` can consume it
    unchanged); `entry_count`/`touched_symbol_count` are batch-level
    stats for the INFO log line T-1689's own acceptance requires."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    report: SelectionReport
    entry_count: int
    touched_symbol_count: int


def _union_touched_symbols(entries: Sequence[VerifyQueueEntry]) -> frozenset[str]:
    """The union of every `entries` record's `touched_symbols` -- the
    whole batch's affected-symbol set, T-1689's own starting point."""
    union: set[str] = set()
    for entry in entries:
        union.update(entry.touched_symbols)
    return frozenset(union)


# frob:doc docs/modules/tickets.md#batch-test-selection-t-1689
def _synthetic_diff_for_touched_symbols(
    snapshot: GraphSnapshot, touched_symbols: frozenset[str]
) -> Diff:
    """Bridge a batch's union `touched_symbols` (already-resolved symrefs,
    no raw hunks survive to batch time) into `frob.testing._select.
    select_tests`'s hunk-based `Diff` input, reusing its whole
    reachability walk verbatim rather than re-deriving it a second time.
    A `Hunk` spanning exactly a symbol's own definition span makes
    `select_tests`'s own first step (`_touched_symbols`, span-overlap
    against the snapshot) re-derive that SAME symbol back out -- a
    faithful round-trip. A `touched_symbols` entry no longer present in
    `snapshot` (renamed/deleted since it was recorded) is silently
    skipped here: `select_tests` cannot select tests for a symbol it
    cannot resolve, and this is the same "no candidates" outcome a normal
    diff-driven run would see for a since-deleted symbol."""
    hunks: list[Hunk] = []
    for symref in sorted(touched_symbols):
        record = snapshot.symbols.get(symref)
        if record is None:
            _log.warning(
                "batch selection: touched symbol %r no longer resolves in the "
                "current graph snapshot -- skipping it for this batch's selection",
                symref,
            )
            continue
        hunks.append(Hunk(file=record.id.path, span=record.span))
    return Diff(base="", hunks=tuple(hunks))


# frob:doc docs/modules/tickets.md#batch-test-selection-t-1689
# frob:tests tests/unit/verify/test_selection.py::TestSelectBatchTests.test_union_of_two_entries_selects_once  # noqa: E501
# frob:tests tests/unit/verify/test_selection.py::TestSelectBatchTests.test_empty_batch_selects_nothing  # noqa: E501
# frob:tests tests/unit/verify/test_selection.py::TestSelectBatchTests.test_unresolvable_symbol_is_skipped_not_fatal  # noqa: E501
def select_batch_tests(
    snapshot: GraphSnapshot,
    entries: Sequence[VerifyQueueEntry],
    *,
    cfg: SelectConfig | None = None,
) -> BatchSelection:
    """Compute the union-touched-set selection for `entries` against
    `snapshot` (pure, like `select_tests` itself -- no filesystem or
    process access). Report what was selected AND excluded via the
    returned `BatchSelection`; the caller logs it at INFO (T-1689's own
    acceptance) since this function has no I/O of its own to log through."""
    from frob.testing._select import select_tests

    touched_symbols = _union_touched_symbols(entries)
    diff = _synthetic_diff_for_touched_symbols(snapshot, touched_symbols)
    report = select_tests(snapshot, diff, cfg or SelectConfig())
    return BatchSelection(
        report=report,
        entry_count=len(entries),
        touched_symbol_count=len(touched_symbols),
    )


# frob:doc docs/modules/tickets.md#batch-test-selection-t-1689
# frob:tests tests/unit/verify/test_selection.py::TestRunBatchSelectedTests.test_graph_unavailable_is_an_error  # noqa: E501
# frob:tests tests/unit/verify/test_selection.py::TestRunBatchSelectedTests.test_selects_and_runs_once  # noqa: E501
def run_batch_selected_tests(
    root: Path, entries: Sequence[VerifyQueueEntry]
) -> Result[TestRunReport, BatchSelectionError]:
    """The end-to-end T-1689 entry point: build/load the graph, compute
    the batch's union selection (`select_batch_tests`), log what was
    selected/excluded at INFO, and run it via `frob.testing._runners.
    run_selected` -- ONE spawned process per language, never one per
    queue entry. Never falls back to a NARROWER run: an unmeasurable
    graph or unreadable runner config is `Err`, and the caller (T-1689's
    own acceptance) is the one responsible for falling back to the FULL
    suite with an explicit WARNING naming why, never to silently running
    nothing."""
    from frob.graph import build_graph, load_graph
    from frob.testing._runners import load_runners, run_selected

    cache = root / ".frob" / "cache.db"
    loaded = load_graph(cache)
    if loaded.is_err:
        _log.info(
            "batch selection: graph cache stale/missing (%s), building fresh",
            loaded.danger_err,
        )
        loaded = build_graph(root, cache)
    if loaded.is_err:
        _log.error(
            "batch selection: graph unavailable (%s) -- caller must fall back "
            "to the full suite, never a narrower run",
            loaded.danger_err,
        )
        return Err(BatchSelectionError.GraphUnavailable)
    snapshot = loaded.danger_ok

    runners_loaded = load_runners(root)
    if runners_loaded.is_err:
        _log.error(
            "batch selection: test.runner config unavailable (%s) -- caller "
            "must fall back to the full suite, never a narrower run",
            runners_loaded.danger_err,
        )
        return Err(BatchSelectionError.RunnersUnavailable)

    batch = select_batch_tests(snapshot, entries)
    selected_total = sum(len(items) for items in batch.report.selected.values())
    _log.info(
        "batch selection: %d queue entr(y/ies), %d touched symbol(s) union -> "
        "%d test(s) selected across %d language(s), %d unbound file(s), "
        "fallback=%s",
        batch.entry_count,
        batch.touched_symbol_count,
        selected_total,
        len(batch.report.selected),
        len(batch.report.unbound),
        batch.report.fallback,
    )

    run = run_selected(batch.report, runners_loaded.danger_ok, root)
    if run.is_err:
        _log.error("batch selection: run_selected failed: %s", run.danger_err)
        return Err(BatchSelectionError.RunnersUnavailable)
    return Ok(run.danger_ok)


__all__ = [
    "BatchSelection",
    "BatchSelectionError",
    "run_batch_selected_tests",
    "select_batch_tests",
]
