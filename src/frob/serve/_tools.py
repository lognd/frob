"""Read-only query functions the MCP server exposes as tools (docs/modules/serve.md).

Each function loads state via frob's existing library entry points and
returns a JSON-serializable dict; none of them mutate tickets, the lock
file, or the graph cache on disk beyond the normal incremental-build cache
write that `frob graph build`/`frob check` also perform. Kept separate from
`frob.serve.server` so the tool layer is testable without an `mcp` SDK
transport (T-0010).
"""

from __future__ import annotations

from pathlib import Path

from typani import Err, ErrorSet, Ok
from typani.result import Result

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


__all__ = [
    "ServeError",
    "frob_check_scope",
    "frob_doable_tickets",
    "frob_doc_for",
    "frob_graph_query",
    "frob_stale_docs",
]
