"""Fact base and closure engine for the strata kernel (docs/strata/kernel.md).

`build_facts` validates a `KernelModel` into an indexed `FactBase`; the
closure methods are the tier-1 fixpoint the claim evaluator consumes.
Everything here is complete over the model: reachability, worst-case age
accumulation, and rate demand are computed over every declared path, so a
PROVED verdict downstream really is a forall (charter law 4).

Validation and indexing stay in Python (the open interface); the hot
propagation kernels (reachable/worst_age/demand) run in the independent
`strata_core` Rust extension, which is REQUIRED -- no pure-Python
fallback (charter D3 as amended; build with `make core`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

try:
    import strata_core
except ImportError as exc:  # pragma: no cover - environment bug, not a code path
    raise ImportError(
        "strata_core native extension is required (charter D3: no pure-Python "
        "fallback); build it with `make core`"
    ) from exc
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._models import Boundary, Flow, KernelModel, Lattice, Node

_log = get_logger(__name__)

#: Flow attr marking at-least-once delivery; its dst must carry _IDEMPOTENT.
_AT_LEAST_ONCE = "delivery=at_least_once"
#: Node attr that discharges the at-least-once obligation.
_IDEMPOTENT = "idempotent"


def _lattice_is_acyclic(lattice: Lattice) -> bool:
    """DFS cycle check over the covering pairs; a cyclic order is no order."""
    adjacency: dict[str, list[str]] = {}
    for lower, higher in lattice.order:
        adjacency.setdefault(lower, []).append(higher)
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(level: str) -> bool:
        if level in done:
            return True
        if level in visiting:
            return False
        visiting.add(level)
        for nxt in adjacency.get(level, ()):
            if not visit(nxt):
                return False
        visiting.discard(level)
        done.add(level)
        return True

    return all(visit(level) for level in lattice.elements())


# frob:doc docs/strata/kernel.md#fact-base
@dataclass(frozen=True)
class FactBase:
    """The validated, indexed form of one `KernelModel`; derived, never edited."""

    model: KernelModel
    nodes: dict[str, Node]
    flows: dict[str, Flow]
    outgoing: dict[str, tuple[str, ...]]  # node id -> flow ids leaving it
    boundaries_on: dict[str, tuple[Boundary, ...]]  # flow id -> its boundaries
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    def nodes_at(self, trust_level: str) -> tuple[str, ...]:
        """Every node id declared exactly at `trust_level`, sorted for determinism."""
        # frob:doc docs/strata/kernel.md#fact-base
        return tuple(
            sorted(n.id for n in self.nodes.values() if n.trust == trust_level)
        )

    def reachable(
        self, src: str, *, through_barriers: bool = False
    ) -> dict[str, tuple[str, ...]]:
        """BFS influence closure from `src`: reached node id -> witness path.

        A path alternates node and flow ids (`src, flow, node, flow, ...`).
        With `through_barriers=False` a flow carrying any boundary is a
        declared trust/label change point and stops taint (the endorsement
        semantics of docs/strata/kernel.md); with True the closure ignores
        boundaries, which is what positive `reach` claims want.
        """
        # frob:doc docs/strata/kernel.md#fact-base
        edges = [
            (f.id, f.src, f.dst, bool(self.boundaries_on.get(f.id)))
            for f in self.flows.values()
        ]
        raw = strata_core.reachable(edges, src, through_barriers)
        paths = {node: tuple(path) for node, path in raw.items()}
        _log.debug("closure from %s reached %d node(s)", src, len(paths) - 1)
        return paths

    def worst_age(self, target: str) -> tuple[float, tuple[str, ...]]:
        """Worst-case accumulated staleness reaching `target`, in seconds.

        Longest-path over per-hop flow ages (flows without an age add 0).
        A positive-age cycle feeding the target means staleness is
        unbounded: returns `inf` with the cycle's witness path, which the
        claim evaluator turns into a refutation, never a silent clamp.
        """
        # frob:doc docs/strata/kernel.md#fact-base
        edges = []
        for flow in self.flows.values():
            hop = 0.0
            if flow.age is not None:
                base = flow.age.base_value()
                hop = base.danger_ok if base.is_ok else 0.0
            edges.append((flow.id, flow.src, flow.dst, hop))
        age, path = strata_core.worst_age(edges, target)
        _log.debug("worst_age(%s) = %s via %s", target, age, path)
        return age, tuple(path)

    def demand(self, node_id: str) -> float:
        """Total declared inbound rate at a node in base units (per second)."""
        # frob:doc docs/strata/kernel.md#fact-base
        rates = []
        for flow in self.flows.values():
            if flow.rate is not None:
                base = flow.rate.base_value()
                if base.is_ok:
                    rates.append((flow.dst, base.danger_ok))
        return strata_core.demand(rates, node_id)


def _validate_ids(model: KernelModel) -> Result[None, StrataError]:
    """Every id unique within its kind; every reference resolves."""
    node_ids = [n.id for n in model.nodes]
    flow_ids = [f.id for f in model.flows]
    for kind, ids in (("node", node_ids), ("flow", flow_ids)):
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            _log.error("duplicate %s id(s): %s", kind, dupes)
            return Err(StrataError.DuplicateId)
    known_nodes = set(node_ids)
    known_flows = set(flow_ids)
    for flow in model.flows:
        for endpoint in (flow.src, flow.dst):
            if endpoint not in known_nodes:
                _log.error("flow %s references unknown node %r", flow.id, endpoint)
                return Err(StrataError.UnknownReference)
    for boundary in model.boundaries:
        if boundary.flow_id not in known_flows:
            _log.error(
                "boundary %s references unknown flow %r", boundary.id, boundary.flow_id
            )
            return Err(StrataError.UnknownReference)
    return Ok(None)


def _validate_levels(model: KernelModel) -> Result[None, StrataError]:
    """Node trust and clearance levels must exist in their lattices."""
    trust_levels = model.trust.elements()
    label_levels = model.labels.elements()
    for node in model.nodes:
        if node.trust not in trust_levels:
            _log.error("node %s: unknown trust level %r", node.id, node.trust)
            return Err(StrataError.UnknownLevel)
        if node.clearance not in label_levels:
            _log.error("node %s: unknown clearance %r", node.id, node.clearance)
            return Err(StrataError.UnknownLevel)
    for flow in model.flows:
        if flow.label not in label_levels:
            _log.error("flow %s: unknown label %r", flow.id, flow.label)
            return Err(StrataError.UnknownLevel)
    return Ok(None)


def _structural_diagnostics(
    model: KernelModel, nodes: dict[str, Node]
) -> tuple[str, ...]:
    """Deny-by-default well-formedness findings that are not fatal to indexing."""
    findings: list[str] = []
    for flow in model.flows:
        if _AT_LEAST_ONCE in flow.attrs:
            dst = nodes[flow.dst]
            if _IDEMPOTENT not in dst.attrs:
                findings.append(
                    f"flow {flow.id}: at-least-once delivery into {dst.id} "
                    f"which is not declared idempotent"
                )
        dst = nodes[flow.dst]
        clearance_ok = model.labels.leq(flow.label, dst.clearance)
        if clearance_ok.is_ok and not clearance_ok.danger_ok:
            findings.append(
                f"flow {flow.id}: payload label {flow.label} exceeds "
                f"clearance {dst.clearance} of {dst.id}"
            )
    for finding in findings:
        _log.warning("structural: %s", finding)
    return tuple(findings)


# frob:doc docs/strata/kernel.md#fact-base
def build_facts(model: KernelModel) -> Result[FactBase, StrataError]:
    """Validate a `KernelModel` and index it into a `FactBase`.

    Fails closed on the first structural error (duplicate ids, dangling
    references, unknown lattice levels, cyclic lattices); non-fatal
    findings land in `FactBase.diagnostics` so nothing is silently fine.
    """
    for lattice in (model.trust, model.labels):
        if not _lattice_is_acyclic(lattice):
            _log.error("lattice %s has a cycle", lattice.name)
            return Err(StrataError.MalformedLattice)
    ids_ok = _validate_ids(model)
    if ids_ok.is_err:
        return Err(ids_ok.danger_err)
    levels_ok = _validate_levels(model)
    if levels_ok.is_err:
        return Err(levels_ok.danger_err)

    nodes = {n.id: n for n in model.nodes}
    flows = {f.id: f for f in model.flows}
    outgoing: dict[str, list[str]] = {}
    for flow in model.flows:
        outgoing.setdefault(flow.src, []).append(flow.id)
    boundaries_on: dict[str, list[Boundary]] = {}
    for boundary in model.boundaries:
        boundaries_on.setdefault(boundary.flow_id, []).append(boundary)

    facts = FactBase(
        model=model,
        nodes=nodes,
        flows=flows,
        outgoing={k: tuple(sorted(v)) for k, v in outgoing.items()},
        boundaries_on={k: tuple(v) for k, v in boundaries_on.items()},
        diagnostics=_structural_diagnostics(model, nodes),
    )
    _log.info(
        "fact base built: %d node(s), %d flow(s), %d boundary(ies), %d diagnostic(s)",
        len(nodes),
        len(flows),
        len(model.boundaries),
        len(facts.diagnostics),
    )
    return Ok(facts)
