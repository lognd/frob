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

#: Flow attrs that mark an edge as a non-transitive hop in `reachable`'s BFS
#: when `through_barriers=True` (the existential `reach`/`independent`/
#: `readers`/krb-movement closures): the edge's dst is still directly
#: reachable, but the closure does not chain past it to extend the witness
#: path any further. `krb_no_transit` is `_krb.py::krb_trust_flows`'s
#: synthesis for a one-way domain trust with no `transitive` marker
#: (T-0282); `utility` is the general-purpose surface marker (`flow ...
#: { utility; }`, docs/strata/surface.md) for a utility/hub edge whose
#: relaying is not itself a meaningful transitive link.
_NON_TRANSITIVE_ATTRS = frozenset({"krb_no_transit", "utility"})

#: T-0496 (docs/audits/strata.md G5): the non-transitive attrs honored when
#: `through_barriers=False` -- the confidentiality `noflow` closure
#: (`_claims.py::_first_noflow_witness`, the ONLY caller that omits
#: `through_barriers`). Deliberately EXCLUDES `utility`: T-0226 added
#: `utility`-as-terminal specifically so an unrelated hub edge (e.g. a
#: logging import) would not falsely refute a legitimate `noflow` claim --
#: but this made the SAME marker a real, author-controlled way to hide a
#: genuine downstream leak from the confidentiality check (repro: `flow
#: log_hub{src=secret_store, dst=logger, utility}` then `flow leak{src=
#: logger, dst=foreign_sink}` -- `noflow(secret_store, foreign_sink)`
#: PROVED despite the two-hop leak, since `logger` was reached only via the
#: terminal `utility` edge and so was never enqueued to explore its own
#: `leak` edge). Per charter law 2 (deny-by-default): a false REFUTED that
#: forces a human to add a real `Boundary`/discharge is an acceptable cost;
#: a false PROVED that hides a real exfiltration path is not. `krb_no_
#: transit` is NOT similarly excluded here -- no caller currently reaches
#: it through this path (`_krb.py`'s synthesized flows feed the `through_
#: barriers=True` movement/reach closures, `_krb_movement.py:388`), and
#: T-0282's own fix was never claimed for confidentiality noflow the way
#: T-0226's `utility` fix was, so there is no known equivalent gap to close
#: for it.
_NOFLOW_NON_TRANSITIVE_ATTRS = frozenset({"krb_no_transit"})


def _flow_fanout(flow: Flow) -> float:
    """A flow's demand-propagation multiplier: its `fanout=<float>` attr, or 1.0."""
    # frob:doc docs/strata/kernel.md#capacity-semantics
    # frob:waive COV007 reason="docs/strata/kernel.md's Capacity semantics section names this helper individually (T-0529)"  # noqa: E501
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


# frob:doc docs/strata/kernel.md#demand-declarations-t-0702
@dataclass(frozen=True)
class AggregateDemand:
    """T-0702: the aggregate inbound demand `FactBase.aggregate_demand`
    computes reaching one node, distinguishing UNDECLARED (`declared=
    False`, `value=0.0`) -- no `users`/`rate`-declaring node's demand
    reaches this node at all -- from a genuine, computed zero or
    positive sum (`declared=True`). This is the exact "missing demand is
    distinguishable from zero demand" acceptance criterion (T-0702 ticket
    body): a node with no upstream demand declaration MUST NOT be
    silently treated the same as one whose declared demand happens to sum
    to zero."""

    declared: bool
    value: float = 0.0
    witness: tuple[str, ...] = field(default_factory=tuple)


# frob:doc docs/strata/kernel.md#fact-base
# frob:ticket T-0972
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

        A flow carrying any of `_NON_TRANSITIVE_ATTRS` (`through_barriers=
        True`) or `_NOFLOW_NON_TRANSITIVE_ATTRS` (`through_barriers=False`)
        -- `krb_no_transit` (synthesized by `_krb.py::krb_trust_flows` for
        a `trusts ...` clause with no `transitive` marker, docs/strata/
        krb.md#domain-trust-lattice) always, plus `utility` (the general-
        purpose surface marker `flow ... { utility; }`, T-0226) ONLY when
        `through_barriers=True` -- is a TERMINAL edge in the kernel's BFS
        (`strata-core/src/lib.rs::reachable`): its `dst` is reachable
        directly but the closure does not chain past it. This fixes
        T-0282's disclosed gap where a chain of non-transitive trusts
        wrongly reached as far as a transitive one. `utility` is
        deliberately NOT honored when `through_barriers=False` (T-0496,
        docs/audits/strata.md G5, `_NOFLOW_NON_TRANSITIVE_ATTRS`'s own
        comment): the ONLY `through_barriers=False` caller is the
        confidentiality `noflow` closure (`_claims.py::
        _first_noflow_witness`), and T-0226's original `utility`-as-
        terminal fix there made the marker a real, author-controlled way
        to hide a genuine downstream leak transiting an otherwise-innocuous
        hub, not just an unrelated one. Every edge NOT explicitly marked
        stays fully transitive -- a real transitive flow is still caught,
        deny-by-default (charter law 2); this is an opt-in exclusion, never
        a default weakening.
        """
        # frob:doc docs/strata/kernel.md#fact-base
        # A `FactBase` only ever exists via `build_facts`, which already
        # fails closed on `strata_core is None` (T-0134) -- so by
        # construction it is present here.
        assert strata_core is not None
        non_transitive = (
            _NON_TRANSITIVE_ATTRS if through_barriers else _NOFLOW_NON_TRANSITIVE_ATTRS
        )
        edges = [
            (
                f.id,
                f.src,
                f.dst,
                bool(self.boundaries_on.get(f.id)),
                not (non_transitive & set(f.attrs)),
            )
            for f in self.flows.values()
        ]
        raw = strata_core.reachable(edges, src, through_barriers)
        paths = {node: tuple(path) for node, path in raw.items()}
        _log.debug("closure from %s reached %d node(s)", src, len(paths) - 1)
        return paths

    # frob:invariant INV-028
    # invariant spec: [INV-028](invariants/INV-028.md)
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

    # frob:doc docs/strata/kernel.md#demand-declarations-t-0702
    # frob:ticket T-0972
    # frob:tests tests/unit/strata/test_demand.py::TestAggregateDemand.test_two_entry_nodes_sum_at_fan_in  # noqa: E501
    def aggregate_demand(self, node_id: str) -> AggregateDemand:
        """Aggregate inbound demand at `node_id`, seeded by every node's
        declared `users`/`rate` entry demand and SUMMED at fan-in exactly
        like `propagated_demand` (T-0702): a `users`/`rate`-declaring node
        is treated as if fed by a synthetic external source flow whose
        declared rate equals `users + rate.base_value()` (both, if both
        are declared -- they compose additively, not exclusively), reusing
        `strata_core.propagated_demand`'s existing fanout-aware summation
        engine unchanged (no `strata-core/src/lib.rs` change needed or
        made -- out of this ticket's declared scope, module docstring).

        Returns `AggregateDemand(declared=False)` when NO declaring node's
        demand reaches `node_id` at all (including `node_id` itself
        declaring nothing) -- the exact "missing demand is distinguishable
        from zero demand" acceptance criterion, computed via a plain
        reverse-BFS ancestor check over the same edge set fed to
        `propagated_demand`, not by comparing the computed value to 0.0
        (a real declared demand of exactly 0 would otherwise be
        indistinguishable from "nothing declared" -- see `AggregateDemand`
        docstring)."""
        # frob:doc docs/strata/kernel.md#demand-declarations-t-0702
        assert strata_core is not None
        edges: list[tuple[str, str, str, float | None, float]] = []
        for flow in self.flows.values():
            rate: float | None = None
            if flow.rate is not None:
                base = flow.rate.base_value()
                if base.is_ok:
                    rate = base.danger_ok
            edges.append((flow.id, flow.src, flow.dst, rate, _flow_fanout(flow)))
        declaring_ids: set[str] = set()
        for node in self.nodes.values():
            seed = 0.0
            declares = False
            if node.rate is not None:
                base = node.rate.base_value()
                if base.is_ok:
                    seed += base.danger_ok
                    declares = True
            if node.users is not None:
                seed += node.users
                declares = True
            if declares:
                declaring_ids.add(node.id)
                edges.append(
                    (
                        f"__demand_seed__{node.id}",
                        f"__demand_source__{node.id}",
                        node.id,
                        seed,
                        1.0,
                    )
                )
        if not declaring_ids:
            _log.debug("aggregate_demand(%s): no node declares users/rate", node_id)
            return AggregateDemand(declared=False)
        incoming: dict[str, list[str]] = {}
        for _flow_id, src, dst, _rate, _fanout in edges:
            incoming.setdefault(dst, []).append(src)
        reached_declarer = node_id in declaring_ids
        seen = {node_id}
        frontier = [node_id]
        # frob:waive PERF003 reason="BFS closure over the flow graph, one pass over incoming edges, not a cross join"  # noqa: E501
        while frontier and not reached_declarer:
            cur = frontier.pop()
            for src in incoming.get(cur, ()):
                if src in declaring_ids:
                    reached_declarer = True
                    break
                if src not in seen:
                    seen.add(src)
                    frontier.append(src)
        if not reached_declarer:
            _log.debug(
                "aggregate_demand(%s): no declaring node's demand reaches it", node_id
            )
            return AggregateDemand(declared=False)
        value, witness = strata_core.propagated_demand(edges, node_id)
        if value == float("inf"):
            _log.warning(
                "aggregate_demand(%s) unbounded: positive-rate cycle %s",
                node_id,
                witness,
            )
        else:
            _log.debug("aggregate_demand(%s) = %s", node_id, value)
        return AggregateDemand(declared=True, value=value, witness=tuple(witness))


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
