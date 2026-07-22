"""Read-only query functions the MCP server exposes as tools (docs/modules/serve.md).

Each function loads state via frob's existing library entry points and
returns a JSON-serializable dict; none of them mutate tickets, the lock
file, or the graph cache on disk beyond the normal incremental-build cache
write that `frob graph build`/`frob check` also perform. Kept separate from
`frob.serve.server` so the tool layer is testable without an `mcp` SDK
transport (T-0010).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/serve/_tools.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from pathlib import Path

from typani import Err, ErrorSet, Ok
from typani.result import Result

import frob.serve._warm as _warm
from frob.graph import build_graph, edges_from, edges_to, load_graph, resolve
from frob.graph.lock import drift, load_lock
from frob.logging import get_logger
from frob.tickets import doable, load_queue

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"


# frob:doc docs/modules/serve.md#mcp-sdk
class ServeError(ErrorSet):
    """Failure values every `frob.serve` tool function can return."""

    GraphUnavailable = "Obligation graph could not be built or loaded"
    QueueUnavailable = "Ticket queue could not be loaded"
    LockUnavailable = "frob.lock could not be loaded"
    UnknownSymbol = "Symbol reference does not resolve"
    GateFailed = "Gate evaluation failed"
    # T-0177
    GitFailed = "git diff could not be computed"
    RunnersUnavailable = "test runner config could not be loaded"
    RunFailed = "touched-set test run failed"


def _load_snapshot(root: Path):  # noqa: ANN202
    """Cache-first graph load, falling back to a full (re)build on staleness/miss."""
    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_ok:
        return loaded
    _log.info(
        "serve: graph cache stale/missing at %s, building: %s", root, loaded.danger_err
    )
    return build_graph(root, cache)


# frob:doc docs/modules/serve.md#tools
# frob:waive TEST005 reason="frob_doable_tickets 66.7% branch cover, debt T-0160"
def frob_doable_tickets(root: Path) -> Result[list[dict], ServeError]:
    """Doable tickets (id/title/kind), oldest-first, as JSON-able dicts."""
    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("serve: frob_doable_tickets: %s", queue_result.danger_err)
        return Err(ServeError.QueueUnavailable)
    tickets = doable(queue_result.danger_ok)
    _log.info("serve: frob_doable_tickets: %d doable", len(tickets))
    return Ok([{"id": t.id, "title": t.title, "kind": t.kind.value} for t in tickets])


def _stale_entries_as_dicts(report) -> list[dict]:  # noqa: ANN001
    """DRIFT001 stale-ack entries from `report`, as JSON-able dicts."""
    return [
        {
            "ref": s.entry.ref,
            "facet": s.entry.facet,
            "was": s.entry.digest,
            "now": s.current,
            "dependents": list(s.dependents),
        }
        for s in report.stale
    ]


def _dangling_entries_as_dicts(report) -> list[dict]:  # noqa: ANN001
    """DRIFT002 dangling-edge entries from `report`, as JSON-able dicts."""
    return [
        {
            "src": d.edge.src,
            "kind": d.edge.kind.value,
            "target": d.edge.target,
            "candidates": list(d.candidates),
        }
        for d in report.dangling
    ]


# frob:doc docs/modules/serve.md#tools
# frob:waive TEST005 reason="frob_stale_docs 69.2% branch cover, debt T-0160"
def frob_stale_docs(root: Path) -> Result[dict, ServeError]:
    """DRIFT001 stale acks and DRIFT002 dangling edges from the drift report."""
    snapshot_result = _load_snapshot(root)
    if snapshot_result.is_err:
        _log.error("serve: frob_stale_docs: graph: %s", snapshot_result.danger_err)
        return Err(ServeError.GraphUnavailable)
    snapshot = snapshot_result.danger_ok

    lock_result = load_lock(root / "frob.lock")
    if lock_result.is_err:
        _log.error("serve: frob_stale_docs: lock: %s", lock_result.danger_err)
        return Err(ServeError.LockUnavailable)
    report = drift(lock_result.danger_ok, snapshot)

    _log.info(
        "serve: frob_stale_docs: stale=%d dangling=%d",
        len(report.stale),
        len(report.dangling),
    )
    return Ok(
        {
            "stale": _stale_entries_as_dicts(report),
            "dangling": _dangling_entries_as_dicts(report),
        }
    )


# frob:doc docs/modules/serve.md#tools
# frob:waive TEST005 reason="frob_check_scope 81.8% branch cover, debt T-0160"
def frob_check_scope(root: Path, ticket_id: str) -> Result[dict, ServeError]:
    """Whether the working diff stays within `ticket_id`'s declared scope (SCOPE001)."""
    from frob.gates import GateConfig, run_gates

    cfg = GateConfig(root=str(root), ticket=ticket_id, gates=frozenset({"scope"}))
    gate_result = run_gates(cfg)
    if gate_result.is_err:
        _log.error("serve: frob_check_scope: %s: %s", ticket_id, gate_result.danger_err)
        return Err(ServeError.GateFailed)
    report = gate_result.danger_ok
    violations = [
        {"rule": v.rule, "file": v.file, "message": v.message}
        for v in report.violations
    ]
    _log.info(
        "serve: frob_check_scope: %s: %d violation(s)", ticket_id, len(violations)
    )
    return Ok(
        {"ticket": ticket_id, "in_scope": not violations, "violations": violations}
    )


def _resolve_symref(
    snapshot,
    symref: str,
    *,
    caller: str,  # noqa: ANN001
) -> Result:
    """Resolve `symref` in `snapshot`, logging under `caller`'s name on failure."""
    resolved = resolve(snapshot, symref)
    if resolved.is_err:
        _log.warning("serve: %s: %s: %s", caller, symref, resolved.danger_err)
        return Err(ServeError.UnknownSymbol)
    return resolved


# frob:doc docs/modules/serve.md#tools
# frob:waive TEST005 reason="frob_graph_query 85.7% branch cover, debt T-0160"
def frob_graph_query(root: Path, symref: str) -> Result[dict, ServeError]:
    """Resolve `symref`; list outgoing/incoming edges, like `frob graph query`."""
    snapshot_result = _load_snapshot(root)
    if snapshot_result.is_err:
        _log.error("serve: frob_graph_query: graph: %s", snapshot_result.danger_err)
        return Err(ServeError.GraphUnavailable)
    snapshot = snapshot_result.danger_ok

    resolved = _resolve_symref(snapshot, symref, caller="frob_graph_query")
    if resolved.is_err:
        return Err(resolved.danger_err)
    record = resolved.danger_ok
    outgoing = edges_from(snapshot, record.symref)
    incoming = edges_to(snapshot, record.symref)
    _log.info(
        "serve: frob_graph_query: %s: %d out, %d in",
        symref,
        len(outgoing),
        len(incoming),
    )
    return Ok(
        {
            "ref": record.symref,
            "kind": record.kind.value,
            "public": record.public,
            "edges_from": [
                {"kind": e.kind.value, "target": e.target} for e in outgoing
            ],
            "edges_to": [{"src": e.src, "kind": e.kind.value} for e in incoming],
        }
    )


def _edges_by_kind_value(edges, kind_value: str) -> list:
    """Edges whose `kind.value` equals `kind_value`."""
    return [e for e in edges if e.kind.value == kind_value]


# frob:doc docs/modules/serve.md#tools
# frob:waive TEST005 reason="frob_doc_for 85.7% branch cover, debt T-0160"
def frob_doc_for(root: Path, symref: str) -> Result[dict, ServeError]:
    """The doc anchor `symref` links to and the describes-edges pointing at it."""
    snapshot_result = _load_snapshot(root)
    if snapshot_result.is_err:
        _log.error("serve: frob_doc_for: graph: %s", snapshot_result.danger_err)
        return Err(ServeError.GraphUnavailable)
    snapshot = snapshot_result.danger_ok

    resolved = _resolve_symref(snapshot, symref, caller="frob_doc_for")
    if resolved.is_err:
        return Err(resolved.danger_err)
    record = resolved.danger_ok
    doc_edges = _edges_by_kind_value(edges_from(snapshot, record.symref), "doc")
    described_by = _edges_by_kind_value(edges_to(snapshot, record.symref), "describes")
    _log.info(
        "serve: frob_doc_for: %s: %d doc edge(s), %d describes edge(s)",
        symref,
        len(doc_edges),
        len(described_by),
    )
    return Ok(
        {
            "ref": record.symref,
            "doc": [{"target": e.target} for e in doc_edges],
            "described_by": [
                {"src": e.src, "facet": e.attrs.get("facet", "sig")}
                for e in described_by
            ],
        }
    )


def _violations_as_dicts(violations) -> list[dict]:
    """`Violation`s (T-0177's `frob_check_delta`) as JSON-able dicts."""
    return [
        {"rule": v.rule, "file": v.file, "line": v.line, "message": v.message}
        for v in violations
    ]


def _run_verify_pass(root: Path, cfg, warm_violations: tuple) -> dict:
    """T-0177's correctness guarantee: drop the warm cache, re-run
    `run_gates` fully cold, and report whether its violation set matches
    `warm_violations` fingerprint-for-fingerprint -- an obligation NOT
    re-evaluated between the two passes must not have had a changed input,
    so a real mismatch means the warm path served a stale answer."""
    from frob.gates import run_gates, violation_fingerprint

    _warm.invalidate(root)
    cold_result = run_gates(cfg)
    if cold_result.is_err:
        _log.error("serve: frob_check_delta: verify: %s", cold_result.danger_err)
        return {"verified": False, "verify_error": str(cold_result.danger_err.value)}
    cold_violations = cold_result.danger_ok.violations
    warm_fp = frozenset(violation_fingerprint(v) for v in warm_violations)
    cold_fp = frozenset(violation_fingerprint(v) for v in cold_violations)
    matched = warm_fp == cold_fp
    if not matched:
        _log.error(
            "serve: frob_check_delta: verify MISMATCH: warm=%d cold=%d symdiff=%d",
            len(warm_fp),
            len(cold_fp),
            len(warm_fp ^ cold_fp),
        )
    return {
        "verified": matched,
        "cold_violation_count": len(cold_violations),
        "verify_mismatch_count": len(warm_fp ^ cold_fp),
    }


# frob:doc docs/modules/serve.md#tools
# frob:tests tests/test_serve.py::TestCheckDelta.test_delta_against_fresh_baseline_is_empty kind="unit"  # noqa: E501
# frob:tests tests/test_serve.py::TestCheckDelta.test_delta_reports_new_violation kind="unit"  # noqa: E501
# frob:tests tests/test_serve.py::TestCheckDelta.test_missing_baseline_is_full_set kind="unit"  # noqa: E501
# frob:tests tests/test_serve.py::TestCheckDelta.test_verify_true_matches_when_no_drift kind="unit"  # noqa: E501
def frob_check_delta(
    root: Path,
    ticket_id: str | None = None,
    base: str = "main",
    *,
    verify: bool = False,
) -> Result[dict, ServeError]:
    """Violations from a full `run_gates` pass that are NEW since the
    stamped `.frob/baseline` (docs/modules/serve.md's staleness/correctness
    contract) -- reuses the warm graph/baseline cache (`frob.serve._warm`)
    instead of a cold reload per call. `verify=True` additionally re-runs
    the check fully cold (dropping the warm cache first) and reports
    whether the two violation sets agree."""
    from frob.gates import GateConfig, delta_violations, is_baseline_stale, run_gates

    state_result = _warm.warm_state(root)
    if state_result.is_err:
        _log.error("serve: frob_check_delta: graph: %s", state_result.danger_err)
        return Err(ServeError.GraphUnavailable)
    baseline = state_result.danger_ok.baseline

    cfg = GateConfig(root=str(root), base=base, ticket=ticket_id, gates=frozenset())
    gate_result = run_gates(cfg)
    if gate_result.is_err:
        _log.error("serve: frob_check_delta: %s", gate_result.danger_err)
        return Err(ServeError.GateFailed)
    report = gate_result.danger_ok

    baseline_stale = baseline is None or is_baseline_stale(root, baseline)
    delta = (
        report.violations
        if baseline_stale
        else delta_violations(report.violations, baseline)
    )

    payload: dict = {
        "ticket": ticket_id,
        "baseline_stale": baseline_stale,
        "violation_count": len(report.violations),
        "delta_count": len(delta),
        "delta": _violations_as_dicts(delta),
    }
    if verify:
        payload.update(_run_verify_pass(root, cfg, report.violations))

    _log.info(
        "serve: frob_check_delta: ticket=%s %d violation(s), %d new since baseline "
        "(stale=%s)",
        ticket_id,
        len(report.violations),
        len(delta),
        baseline_stale,
    )
    return Ok(payload)


# frob:doc docs/modules/serve.md#tools
# frob:tests tests/test_serve.py::TestRunTouchedTests.test_no_diff_selects_nothing kind="unit"  # noqa: E501
# frob:tests tests/test_serve.py::TestRunTouchedTests.test_bad_base_is_git_failed kind="unit"  # noqa: E501
def frob_run_touched_tests(root: Path, base: str = "main") -> Result[dict, ServeError]:
    """Select AND run the touched-set tests for `base` (`frob.testing.
    select_tests` + `run_selected`, the MCP-exposed counterpart of `frob
    test --base <base>`), against the warm graph snapshot `frob_check_
    delta` already paid to build."""
    from frob.gitio import working_diff
    from frob.testing import SelectConfig, load_runners, run_selected, select_tests

    state_result = _warm.warm_state(root)
    if state_result.is_err:
        _log.error("serve: frob_run_touched_tests: graph: %s", state_result.danger_err)
        return Err(ServeError.GraphUnavailable)
    snapshot = state_result.danger_ok.snapshot

    diff_result = working_diff(root, base)
    if diff_result.is_err:
        _log.error("serve: frob_run_touched_tests: diff: %s", diff_result.danger_err)
        return Err(ServeError.GitFailed)

    selection = select_tests(snapshot, diff_result.danger_ok, SelectConfig())

    runners_result = load_runners(root)
    if runners_result.is_err:
        _log.error(
            "serve: frob_run_touched_tests: runners: %s", runners_result.danger_err
        )
        return Err(ServeError.RunnersUnavailable)

    run_result = run_selected(selection, runners_result.danger_ok, root)
    if run_result.is_err:
        _log.error("serve: frob_run_touched_tests: run: %s", run_result.danger_err)
        return Err(ServeError.RunFailed)
    test_run = run_result.danger_ok

    _log.info(
        "serve: frob_run_touched_tests: base=%s ok=%s %d outcome(s)",
        base,
        test_run.ok,
        len(test_run.outcomes),
    )
    return Ok(
        {
            "base": base,
            "touched": list(selection.touched),
            "ok": test_run.ok,
            "outcomes": [
                {
                    "language": o.language,
                    "exit_code": o.exit_code,
                    "duration_s": o.duration_s,
                    "stdout_tail": o.stdout_tail,
                    "stderr_tail": o.stderr_tail,
                }
                for o in test_run.outcomes
            ],
        }
    )


__all__ = [
    "ServeError",
    "frob_check_delta",
    "frob_check_scope",
    "frob_doable_tickets",
    "frob_doc_for",
    "frob_graph_query",
    "frob_run_touched_tests",
    "frob_stale_docs",
]
