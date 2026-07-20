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

import importlib
from collections import Counter
from dataclasses import dataclass, field
from types import ModuleType

try:
    strata_core: ModuleType | None = importlib.import_module("strata_core")
except ImportError:  # pragma: no cover - environment-dependent
    # The native parser is a maturin-built extension present in dev venvs
    # but not in standalone tool installs; degrade `build_facts` to a
    # typed Err instead of crashing every `frob check` on a repo with a
    # design/ dir (T-0133's guarded-import pattern, applied here for
    # T-0134 -- charter D3's "no pure-Python fallback" still holds, it
    # just now fails closed through Result instead of an unhandled
    # ImportError).
    strata_core = None
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._models import (
    _AT_LEAST_ONCE,
    _IDEMPOTENT,
    Boundary,
    Flow,
    KernelModel,
    Lattice,
    Node,
)

_log = get_logger(__name__)

#: Flow attr prefix for the demand-propagation multiplier (surface `fanout NUM`).
_FANOUT_PREFIX = "fanout="

#: Flow attrs that mark an edge as a non-transitive hop in `reachable`'s BFS:
#: the edge's dst is still directly reachable, but the closure does not
#: chain past it to extend the witness path any further. `krb_no_transit`
#: is `_krb.py::krb_trust_flows`'s synthesis for a one-way domain trust
#: with no `transitive` marker (T-0282); `utility` is the general-purpose
#: surface marker (`flow ... { utility; }`, docs/strata/surface.md) for a
#: utility/hub edge whose relaying is not itself a meaningful transitive
#: link -- this is how a real `noflow` claim survives an unrelated hub
#: edge (e.g. a logging import) without weakening the closure for any
#: edge that is NOT explicitly marked (T-0226).
_NON_TRANSITIVE_ATTRS = frozenset({"krb_no_transit", "utility"})


def _flow_fanout(flow: Flow) -> float:
    """A flow's demand-propagation multiplier: its `fanout=<float>` attr, or 1.0."""
    # frob:doc docs/strata/kernel.md#capacity-semantics
    for attr in flow.attrs:
        if attr.startswith(_FANOUT_PREFIX):
            try:
                return float(attr[len(_FANOUT_PREFIX) :])
            except ValueError:
                _log.warning("flow %s: malformed fanout attr %r", flow.id, attr)
                return 1.0
    return 1.0


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

        A flow carrying any of `_NON_TRANSITIVE_ATTRS` -- `krb_no_transit`
        (synthesized by `_krb.py::krb_trust_flows` for a `trusts ... `
        clause with no `transitive` marker, docs/strata/krb.md#domain-
        trust-lattice) or `utility` (the general-purpose surface marker
        `flow ... { utility; }`, T-0226) -- is a TERMINAL edge in the
        kernel's BFS (`strata-core/src/lib.rs::reachable`): its `dst` is
        reachable directly but the closure does not chain past it. This
        fixes T-0282's disclosed gap where a chain of non-transitive
        trusts wrongly reached as far as a transitive one, and T-0226's
        gap where an unrelated utility/hub edge (e.g. a logging import)
        falsely defeated a legitimate `noflow` claim by letting flow
        transit through it. Every edge NOT explicitly marked stays fully
        transitive -- a real transitive flow is still caught, deny-by-
        default (charter law 2); this is an opt-in exclusion, never a
        default weakening.
        """
        # frob:doc docs/strata/kernel.md#fact-base
        # A `FactBase` only ever exists via `build_facts`, which already
        # fails closed on `strata_core is None` (T-0134) -- so by
        # construction it is present here.
        assert strata_core is not None
        edges = [
            (
                f.id,
                f.src,
                f.dst,
                bool(self.boundaries_on.get(f.id)),
                not (_NON_TRANSITIVE_ATTRS & set(f.attrs)),
            )
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
        # See `reachable`'s comment: `build_facts` already fails closed on
        # a missing `strata_core` (T-0134), so it is present by construction.
        assert strata_core is not None
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

    # frob:doc docs/strata/kernel.md#fact-base
    def demand(self, node_id: str) -> float:
        """Total propagated inbound demand at a node in base units (per second).

        Thin wrapper over `propagated_demand` that drops the witness path;
        RATE/UTILIZATION bound claims (`_claims.py`) only need the number,
        and an `inf` value already refutes any finite limit on its own.
        """
        return self.propagated_demand(node_id)[0]

    def propagated_demand(self, node_id: str) -> tuple[float, tuple[str, ...]]:
        """Inbound demand at a node, fanout-multiplied, summed over paths.

        Demand at a node is the sum over inbound flows of (the flow's own
        declared rate, if any, else the propagated demand at its source)
        times the flow's `fanout` attr (default 1.0) -- load ADDS across
        converging paths, unlike `worst_age`, which MAXES
        (docs/strata/kernel.md#capacity-semantics). A flow whose `rate` is
        declared but fails to resolve (`Quantity.base_value()` errors, e.g.
        an unknown unit) is treated identically to a flow with no `rate` at
        all: it PROPAGATES into its source's own demand rather than being
        dropped from the sum. This fails toward overcounting load, not
        undercounting it (deny-by-default, charter law 2) -- see T-0066/
        T-0099. A positive-rate cycle (undeclared- or unresolvable-rate
        flows in a loop, fed by some declared-rate source, reaching
        `node_id`) is unbounded: `+inf` with the cycle as witness, never a
        silent clamp.
        """
        # frob:doc docs/strata/kernel.md#capacity-semantics
        # See `reachable`'s comment: `build_facts` already fails closed on
        # a missing `strata_core` (T-0134), so it is present by construction.
        assert strata_core is not None
        edges = []
        for flow in self.flows.values():
            rate: float | None = None
            if flow.rate is not None:
                base = flow.rate.base_value()
                if base.is_ok:
                    rate = base.danger_ok
            edges.append((flow.id, flow.src, flow.dst, rate, _flow_fanout(flow)))
        value, witness = strata_core.propagated_demand(edges, node_id)
        if value == float("inf"):
            _log.warning(
                "propagated_demand(%s) unbounded: positive-rate cycle %s",
                node_id,
                witness,
            )
        else:
            _log.debug("propagated_demand(%s) = %s", node_id, value)
        return value, tuple(witness)


# frob:ticket T-0148
def _validate_ids(model: KernelModel) -> Result[None, StrataError]:
    """Every id unique within its kind; every reference resolves."""
    node_ids = [n.id for n in model.nodes]
    flow_ids = [f.id for f in model.flows]
    # frob:waive PERF004 reason="runs once, only on the fail-closed dupe-id path"
    for kind, ids in (("node", node_ids), ("flow", flow_ids)):
        if len(ids) != len(set(ids)):
            counts = Counter(ids)
            dupes = sorted(i for i, n in counts.items() if n > 1)
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


def _flow_has_negative_quantity(flow) -> bool:
    """Whether any of `flow`'s age/rate/size is a negative base value --
    the per-flow check `_validate_nonnegative_quantities` runs over every
    declared `Flow`."""
    for field_name, quantity in (
        ("age", flow.age),
        ("rate", flow.rate),
        ("size", flow.size),
    ):
        if quantity is None:
            continue
        base = quantity.base_value()
        if base.is_err:
            continue  # unknown unit is reported by other validation paths
        if base.danger_ok < 0.0:
            _log.error(
                "flow %s: %s %s%s is negative",
                flow.id,
                field_name,
                quantity.value,
                quantity.unit,
            )
            return True
    return False


def _validate_nonnegative_quantities(model: KernelModel) -> Result[None, StrataError]:
    """Flow age/rate/size must be non-negative.

    The SCC-condensation soundness argument for `worst_age`
    (docs/strata/kernel.md#age-propagation-semantics) depends on every hop
    weight being non-negative: any intra-SCC edge lies on a cycle, and a
    positive edge there makes the cycle positive (the `+inf` case) --
    that reasoning only holds when weights cannot be negative. The surface
    grammar cannot express a negative quantity, but the Python API can, so
    this is enforced here, fail closed.
    """
    for flow in model.flows:
        if _flow_has_negative_quantity(flow):
            return Err(StrataError.NegativeQuantity)
    return Ok(None)


def _flow_structural_findings(
    model: KernelModel, flow, nodes: dict[str, Node]
) -> list[str]:
    """The at-least-once/idempotency and clearance findings one `Flow`
    contributes to `_structural_diagnostics`."""
    findings: list[str] = []
    dst = nodes[flow.dst]
    if _AT_LEAST_ONCE in flow.attrs and _IDEMPOTENT not in dst.attrs:
        findings.append(
            f"flow {flow.id}: at-least-once delivery into {dst.id} "
            f"which is not declared idempotent"
        )
    clearance_ok = model.labels.leq(flow.label, dst.clearance)
    if clearance_ok.is_ok and not clearance_ok.danger_ok:
        findings.append(
            f"flow {flow.id}: payload label {flow.label} exceeds "
            f"clearance {dst.clearance} of {dst.id}"
        )
    return findings


def _structural_diagnostics(
    model: KernelModel, nodes: dict[str, Node]
) -> tuple[str, ...]:
    """Deny-by-default well-formedness findings that are not fatal to indexing."""
    findings: list[str] = []
    for flow in model.flows:
        findings.extend(_flow_structural_findings(model, flow, nodes))
    for finding in findings:
        _log.warning("structural: %s", finding)
    return tuple(findings)


# frob:doc docs/strata/kernel.md#fact-base
def build_facts(model: KernelModel) -> Result[FactBase, StrataError]:
    """Validate a `KernelModel` and index it into a `FactBase`.

    Fails closed on the first structural error (duplicate ids, dangling
    references, unknown lattice levels, cyclic lattices); non-fatal
    findings land in `FactBase.diagnostics` so nothing is silently fine.
    Fails closed just as hard, with a typed
    `StrataError.NativeExtensionUnavailable`, if the `strata_core` native
    extension is not installed (T-0134) -- every closure method below
    assumes a successfully-built `FactBase` implies `strata_core` is
    present, so this is the one gate that must catch its absence.
    """
    fail_closed = _validate_build_facts_preconditions(model)
    if fail_closed.is_err:
        return Err(fail_closed.danger_err)

    facts = _index_facts(model)
    _log.info(
        "fact base built: %d node(s), %d flow(s), %d boundary(ies), %d diagnostic(s)",
        len(facts.nodes),
        len(facts.flows),
        len(model.boundaries),
        len(facts.diagnostics),
    )
    return Ok(facts)


def _validate_build_facts_preconditions(
    model: KernelModel,
) -> Result[None, StrataError]:
    """Every fail-closed check `build_facts` must clear before indexing,
    run in order: native extension present, lattices acyclic, ids valid,
    levels valid, quantities non-negative. Order matters -- the first
    failing check's `StrataError` is the one `build_facts` returns."""
    if strata_core is None:
        _log.error("build_facts: strata_core native extension unavailable")
        return Err(StrataError.NativeExtensionUnavailable)
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
    nonneg_ok = _validate_nonnegative_quantities(model)
    if nonneg_ok.is_err:
        return Err(nonneg_ok.danger_err)
    return Ok(None)


def _index_facts(model: KernelModel) -> FactBase:
    """Build the `FactBase` indices (nodes/flows/outgoing/boundaries) once
    structural validation has already passed -- the pure indexing step
    `build_facts` delegates to after every fail-closed check clears."""
    nodes = {n.id: n for n in model.nodes}
    flows = {f.id: f for f in model.flows}
    outgoing: dict[str, list[str]] = {}
    for flow in model.flows:
        outgoing.setdefault(flow.src, []).append(flow.id)
    boundaries_on: dict[str, list[Boundary]] = {}
    for boundary in model.boundaries:
        boundaries_on.setdefault(boundary.flow_id, []).append(boundary)

    return FactBase(
        model=model,
        nodes=nodes,
        flows=flows,
        outgoing={k: tuple(sorted(v)) for k, v in outgoing.items()},
        boundaries_on={k: tuple(v) for k, v in boundaries_on.items()},
        diagnostics=_structural_diagnostics(model, nodes),
    )
