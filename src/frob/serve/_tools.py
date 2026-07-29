"""Read-only query functions the MCP server exposes as tools (docs/modules/serve.md).

Each function loads state via frob's existing library entry points and
returns a JSON-serializable dict; none of them mutate tickets, the lock
file, or the graph cache on disk beyond the normal incremental-build cache
write that `frob graph build`/`frob check` also perform. Kept separate from
`frob.serve.server` so the tool layer is testable without an `mcp` SDK
transport (T-0010).
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pathlib import Path

from typani import Err, ErrorSet, Ok
from typani.result import Result

import frob.serve._warm as _warm
from frob.graph import affects, build_graph, edges_from, edges_to, load_graph, resolve
from frob.graph.lock import drift, load_lock
from frob.logging import get_logger
from frob.perf import list_sketches
from frob.stats._sketch import quantile, total_weight
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
    # T-1127
    ExportsFailed = "exports listing could not be built"
    StatsFailed = "delivery stats could not be collected"


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
# frob:tests tests/test_app_daemon_proxy.py::TestDifferentialParity.test_doable_tickets_json_daemon_matches_in_process kind="unit"  # noqa: E501
def frob_doable_tickets(root: Path) -> Result[list[dict], ServeError]:
    """Doable tickets, oldest-first, as JSON-able dicts.

    T-1128: each entry is `ticket.model_dump(mode="json")` -- the FULL
    ticket model, field-for-field identical to `frob ticket doable --json`'s
    own `t.model_dump(mode="json")` per row (`frob.app.ticket_runner.
    _query._doable`) -- not the earlier id/title/kind-only subset, which
    could never reach byte-for-byte parity with the CLI's `--json` output.
    """
    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("serve: frob_doable_tickets: %s", queue_result.danger_err)
        return Err(ServeError.QueueUnavailable)
    tickets = doable(queue_result.danger_ok, root)
    _log.info("serve: frob_doable_tickets: %d doable", len(tickets))
    return Ok([t.model_dump(mode="json") for t in tickets])


# frob:doc docs/modules/serve.md#tools
# frob:tests tests/test_app_daemon_proxy.py::TestDifferentialParity.test_exports_json_daemon_matches_in_process kind="unit"  # noqa: E501
def frob_exports(
    root: Path,
    pkg_dir: str,
    *,
    include_private: bool = False,
    exclude_modules: tuple[str, ...] = (),
) -> Result[dict, ServeError]:
    """`ExportsResult.model_dump(mode="json")` for `pkg_dir` -- the default
    (non-`--consumers`, non-`--write`) `frob exports <path> --json` render
    mode (`frob.app.exports_runner.run`). `pkg_dir` (not `root` -- unlike
    every other proxied RPC, this one answers for a SUBDIRECTORY of the
    daemon's own root, sent verbatim from the client so it echoes back
    identically as `ExportsResult.package_dir`) is resolved relative to
    THIS PROCESS's cwd, exactly as `exports_package`'s own `Path.is_dir()`/
    `.glob()` calls resolve any relative path (T-1127)."""
    from frob.exports import exports_package

    result = exports_package(
        Path(pkg_dir),
        include_private=include_private,
        exclude_modules=list(exclude_modules),
    )
    if result.is_err:
        _log.error("serve: frob_exports: %s", result.danger_err)
        return Err(ServeError.ExportsFailed)
    er = result.danger_ok
    _log.info("serve: frob_exports: %s: %d module(s)", pkg_dir, len(er.modules))
    return Ok(er.model_dump(mode="json"))


# frob:doc docs/modules/serve.md#tools
# frob:tests tests/test_app_daemon_proxy.py::TestDifferentialParity.test_stats_json_daemon_matches_in_process kind="unit"  # noqa: E501
def frob_stats(root: Path, *, window_days: int = 30) -> Result[dict, ServeError]:
    """`StatsReport.model_dump(mode="json")` for `root` -- the default
    (non-`--agentic`) `frob stats --json` render mode (`frob.app.
    stats_runner.run`), field-for-field identical since both sides dump
    the identical `StatsReport` pydantic model (T-1127). The `--agentic`
    mode (env-var-triggered, `FROB_STATS_AGENTIC`) reads a different
    report shape (`frob.stats.agentic_report`) entirely and is out of
    this RPC's scope -- `_try_stats_via_daemon` never calls this RPC for
    that mode."""
    from frob.stats import collect

    result = collect(root, window_days=window_days)
    if result.is_err:
        _log.error("serve: frob_stats: %s", result.danger_err)
        return Err(ServeError.StatsFailed)
    report = result.danger_ok
    _log.info("serve: frob_stats: %s: %d ticket(s)", root, report.tickets.total)
    return Ok(report.model_dump(mode="json"))


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
# frob:tests tests/test_app_daemon_proxy.py::TestDifferentialParity.test_graph_query_json_daemon_matches_in_process kind="unit"  # noqa: E501
def frob_graph_query(root: Path, symref: str) -> Result[dict, ServeError]:
    """Resolve `symref`; list outgoing/incoming edges, like `frob graph query`.

    T-1128: the payload shape is field-for-field identical to
    `frob.app.graph_runner._query_json_payload` (the CLI's own `frob graph
    query --json` output) -- `span`/`digests` and each edge's full
    `model_dump()` (not a trimmed subset), so a proxied CLI hit needs zero
    reshaping beyond `edges_from`/`edges_to` already being plain dicts.
    """
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
            "span": list(record.span),
            "digests": record.digests.model_dump(),
            "edges_from": [e.model_dump() for e in outgoing],
            "edges_to": [e.model_dump() for e in incoming],
        }
    )


def _edges_by_kind_value(edges, kind_value: str) -> list:
    """Edges whose `kind.value` equals `kind_value`."""
    return [e for e in edges if e.kind.value == kind_value]


# frob:doc docs/modules/serve.md#tools
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


# frob:doc docs/modules/graph.md#affects
# frob:doc docs/modules/serve.md#tools
# frob:tests tests/test_serve.py::TestAffects.test_direct_symbol_no_dependents kind="unit"  # noqa: E501
# frob:tests tests/test_serve.py::TestAffects.test_transitive_dependent_docs_included kind="unit"  # noqa: E501
# frob:tests tests/test_serve.py::TestAffects.test_unknown_symbol_is_err kind="unit"
def frob_affects(
    root: Path,
    symref: str,
    *,
    max_depth: int | None = None,
    max_nodes: int | None = None,
) -> Result[dict, ServeError]:
    """The T-0325 north-star query: resolve `symref`, then warm-walk the
    obligation graph (`frob.graph.affects`) for every doc anchor, test, and
    transitively-dependent symbol (`frob:uses-contract` chain) that must be
    reviewed/updated because `symref` changed -- reuses the warm snapshot
    `frob.serve._warm._warm_state` already built, no cold graph reload and no
    test run."""
    state_result = _warm._warm_state(root)
    if state_result.is_err:
        _log.error("serve: frob_affects: graph: %s", state_result.danger_err)
        return Err(ServeError.GraphUnavailable)
    snapshot = state_result.danger_ok.snapshot

    resolved = _resolve_symref(snapshot, symref, caller="frob_affects")
    if resolved.is_err:
        return Err(resolved.danger_err)
    record = resolved.danger_ok

    kwargs: dict = {}
    if max_depth is not None:
        kwargs["max_depth"] = max_depth
    if max_nodes is not None:
        kwargs["max_nodes"] = max_nodes
    result = affects(snapshot, record.symref, **kwargs)

    _log.info(
        "serve: frob_affects: %s: %d dependent(s), %d doc(s), %d test(s), truncated=%s",
        symref,
        len(result.dependents),
        len(result.docs),
        len(result.tests),
        result.truncated,
    )
    return Ok(
        {
            "ref": result.root,
            "dependents": list(result.dependents),
            "docs": list(result.docs),
            "tests": list(result.tests),
            "truncated": result.truncated,
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

    _warm._invalidate(root)
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
# frob:doc docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602  # noqa: E501
# frob:doc docs/modules/serve.md#proxied-commands
# frob:ticket T-0602
# frob:ticket T-1147
# frob:tests tests/test_serve.py::TestCheckDelta.test_delta_against_fresh_baseline_is_empty kind="unit"  # noqa: E501
# frob:tests tests/test_serve.py::TestCheckDelta.test_delta_reports_new_violation kind="unit"  # noqa: E501
# frob:tests tests/test_serve.py::TestCheckDelta.test_missing_baseline_is_full_set kind="unit"  # noqa: E501
# frob:tests tests/test_serve.py::TestCheckDelta.test_verify_true_matches_when_no_drift kind="unit"  # noqa: E501
# frob:tests tests/test_serve.py::TestCheckDelta.test_check_result_matches_only_gates_delta_cli_shape kind="unit"  # noqa: E501
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
    whether the two violation sets agree.

    T-1147: also renders `check_result`, the SAME per-gate-family
    `ToolResult` list (`frob.check._python._gates_success_result`) `frob
    check --only gates --delta --json`'s CLI path builds, wrapped in a
    `CheckResult(path, results)`-shaped dict -- byte-for-byte what that one
    narrow CLI invocation shape prints, reusing the identical rendering
    code rather than a second hand-built summary. The flatter `delta`/
    `violation_count`/`baseline_stale` keys above are UNCHANGED (kept for
    any existing narrower caller of this RPC) -- `check_result` is new,
    additive structure, not a replacement."""
    from frob.check._python import _gates_success_result
    from frob.gates import GateConfig, delta_violations, is_baseline_stale, run_gates
    from frob.process.parsers.common import ToolResult

    state_result = _warm._warm_state(root)
    if state_result.is_err:
        _log.error("serve: frob_check_delta: graph: %s", state_result.danger_err)
        return Err(ServeError.GraphUnavailable)
    baseline = state_result.danger_ok.baseline

    cfg = GateConfig(root=str(root), base=base, ticket=ticket_id, gates=frozenset())
    # T-0602: this is the "gate dispatch runs" call `docs/modules/serve.md`'s
    # "What it does NOT cover" section named as a follow-up -- `use_cache`
    # opts into `_gate_cache`'s per-gate dependency-tracked partial
    # re-evaluation for the closed cacheable-gate allowlist. `verify=True`'s
    # own cold cross-check below deliberately does NOT pass `use_cache` (it
    # must stay a genuinely cold, cache-bypassing run to be the correctness
    # oracle it claims to be).
    gate_result = run_gates(cfg, use_cache=True)
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

    # T-1147: `_gates_success_result` re-derives its own delta-filtering
    # via `load_baseline`/`is_baseline_stale` (a fresh, cold read, same as
    # the CLI's own `_apply_delta` does) rather than reusing this
    # function's own warm-cache `baseline`/`baseline_stale` above -- this
    # is what makes `check_result` byte-identical to the CLI path instead
    # of merely equivalent; the two delta computations are independent by
    # design, not a duplicated call the way they might look.
    check_results: list[ToolResult] = _gates_success_result(
        report, root=root, delta=True
    )

    payload: dict = {
        "ticket": ticket_id,
        "baseline_stale": baseline_stale,
        "violation_count": len(report.violations),
        "delta_count": len(delta),
        "delta": _violations_as_dicts(delta),
        "check_result": {
            "path": str(root),
            "results": [r.model_dump(mode="json") for r in check_results],
        },
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

    state_result = _warm._warm_state(root)
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
    return Ok(test_run.model_dump(mode="json"))


# frob:ticket T-0917
def _perf_hot_sort_key(row, by: str) -> float:  # noqa: ANN001
    """Sort key mirroring `frob perf hot --by p90|p50xcount` (T-0712's
    `frob.app.perf_runner._hot_sort_key`): `p90` ranks by the stored
    sketch's p90 read; `p50xcount` (the default) ranks by p50 times total
    observation weight."""
    p50 = quantile(row.sketch, 0.5)
    p90 = quantile(row.sketch, 0.9)
    if by == "p90":
        return p90
    return p50 * total_weight(row.sketch)


# frob:doc docs/modules/serve.md#tools
# frob:ticket T-0917
def frob_perf_hot(
    root: Path, top: int | None = None, by: str = "p50xcount"
) -> Result[list[dict], ServeError]:
    """T-0712's `frob perf hot` query surface (`frob.perf.list_sketches`,
    the persisted hot-graph sketch store), ranked by `by` (`p50xcount`
    default, or `p90`) and truncated to `top` rows -- the MCP mirror T-0712's
    acceptance text called for but that fell outside its own declared scope
    (T-0917)."""
    rows = list_sketches(root)
    rows.sort(key=lambda row: _perf_hot_sort_key(row, by), reverse=True)
    if top is not None:
        rows = rows[:top]

    _log.info("serve: frob_perf_hot: root=%s by=%s %d row(s)", root, by, len(rows))
    return Ok(
        [
            {
                "section_key": row.section_key,
                "kind": row.kind,
                "label": row.label,
                "p50": quantile(row.sketch, 0.5),
                "p90": quantile(row.sketch, 0.9),
                "sample_count": total_weight(row.sketch),
            }
            for row in rows
        ]
    )


# frob:doc docs/modules/serve.md#daemon-jobs
# frob:tests tests/test_serve_daemon.py::TestFrobDaemonStatus.test_reads_current_status kind="unit"  # noqa: E501
def frob_daemon_status(root: Path) -> Result[dict, ServeError]:
    """(T-0733) The background daemon's latest post-land verdict and
    outstanding rebase warnings for `root`, as JSON-able dicts -- a pure
    read of `frob.serve._daemon.daemon_status`, never triggers a poll
    itself; the daemon's own background thread (`_daemon._start_daemon`)
    keeps this fresh."""
    from frob.serve import _daemon

    status = _daemon.daemon_status(root)
    post_land = status.post_land.model_dump(mode="json") if status.post_land else None
    _log.info(
        "serve: frob_daemon_status: post_land=%s rebase_warnings=%d",
        "present" if post_land else "none",
        len(status.rebase_warnings),
    )
    return Ok(
        {
            "post_land": post_land,
            "rebase_warnings": [
                w.model_dump(mode="json") for w in status.rebase_warnings
            ],
            "last_poll_at": status.last_poll_at,
        }
    )


__all__ = [
    "ServeError",
    "frob_affects",
    "frob_check_delta",
    "frob_check_scope",
    "frob_daemon_status",
    "frob_doable_tickets",
    "frob_doc_for",
    "frob_exports",
    "frob_graph_query",
    "frob_perf_hot",
    "frob_run_touched_tests",
    "frob_stale_docs",
    "frob_stats",
]
