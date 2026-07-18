"""Capacity arithmetic tests (docs/strata/kernel.md#capacity-semantics).

Covers propagated demand through fanout chains, positive-rate cycle
detection, zipf hottest-shard utilization (the key skew-vs-mean contrast),
and growth-horizon saturation diagnostics (T-0066).
"""

from __future__ import annotations

import datetime as dt

from hypothesis import given, settings
from hypothesis import strategies as st

from frob.strata import (
    BoundClaim,
    Capacity,
    Claim,
    Flow,
    KernelModel,
    Metric,
    Node,
    Quantity,
    Verdict,
    build_facts,
    evaluate_claims,
)


def _node(nid: str, trust: str = "trusted", **kw) -> Node:
    """A minimal trusted node for fixtures, forwarding kwargs to `Node`."""
    return Node(id=nid, trust=trust, **kw)


def _flow(fid: str, src: str, dst: str, **kw) -> Flow:
    """A minimal flow for fixtures, forwarding kwargs to `Flow`."""
    return Flow(id=fid, src=src, dst=dst, **kw)


def _one(model: KernelModel, today: dt.date = dt.date(2026, 7, 17)):
    """Evaluate a single-claim model and return its lone `ClaimResult`."""
    results = evaluate_claims(model, today=today).danger_ok
    assert len(results) == 1
    return results[0]


class TestPropagatedDemand:
    # frob:tests src/frob/strata/_facts.py::FactBase.propagated_demand kind="unit"
    def test_chain_multiplies_fanout(self) -> None:
        model = KernelModel(
            nodes=(_node("src"), _node("a"), _node("b")),
            flows=(
                _flow("f1", "src", "a", rate=Quantity(value=10, unit="/s")),
                _flow("f2", "a", "b", attrs=("fanout=2",)),
            ),
        )
        facts = build_facts(model).danger_ok
        # 10/s declared into a, fanout 2 on a->b: no rate declared on f2, so
        # it propagates a's own demand (10) times fanout 2 = 20.
        assert facts.demand("b") == 20.0

    # frob:tests src/frob/strata/_facts.py::FactBase.propagated_demand kind="unit"
    def test_declared_rate_terminates_propagation(self) -> None:
        model = KernelModel(
            nodes=(_node("src"), _node("a"), _node("b")),
            flows=(
                _flow("f1", "src", "a", rate=Quantity(value=999, unit="/s")),
                _flow(
                    "f2",
                    "a",
                    "b",
                    rate=Quantity(value=5, unit="/s"),
                    attrs=("fanout=3",),
                ),
            ),
        )
        facts = build_facts(model).danger_ok
        # f2 declares its own rate (5), so it does NOT recurse into a's
        # demand (999); the declared rate is just multiplied by fanout.
        assert facts.demand("b") == 15.0

    # frob:tests src/frob/strata/_facts.py::FactBase.propagated_demand kind="unit"
    def test_unresolvable_rate_propagates_upstream_demand(self) -> None:
        """A declared `rate` whose unit doesn't resolve (`base_value()`
        errors) is treated the same as no declared rate at all: demand
        recurses into the source's own propagated demand rather than being
        dropped from the sum (T-0066/T-0099 -- see
        docs/strata/kernel.md#capacity-semantics)."""
        model = KernelModel(
            nodes=(_node("src"), _node("a"), _node("b")),
            flows=(
                _flow("f1", "src", "a", rate=Quantity(value=10, unit="/s")),
                _flow(
                    "f2",
                    "a",
                    "b",
                    rate=Quantity(value=5, unit="bogus-unit"),
                ),
            ),
        )
        facts = build_facts(model).danger_ok
        # f2's rate fails to resolve (unknown unit), so it is treated as
        # undeclared and propagates a's demand (10) rather than dropping
        # to 0 or using the unresolvable 5.
        assert facts.demand("b") == 10.0

    # frob:tests src/frob/strata/_facts.py::FactBase.propagated_demand kind="unit"
    def test_sums_over_converging_paths(self) -> None:
        model = KernelModel(
            nodes=(_node("s1"), _node("s2"), _node("t")),
            flows=(
                _flow("f1", "s1", "t", rate=Quantity(value=4, unit="/s")),
                _flow("f2", "s2", "t", rate=Quantity(value=6, unit="/s")),
            ),
        )
        facts = build_facts(model).danger_ok
        assert facts.demand("t") == 10.0

    # frob:tests src/frob/strata/_facts.py::FactBase.propagated_demand kind="unit"
    def test_positive_rate_cycle_is_unbounded(self) -> None:
        model = KernelModel(
            nodes=(_node("src"), _node("a"), _node("b")),
            flows=(
                _flow("f0", "src", "a", rate=Quantity(value=5, unit="/s")),
                _flow("f1", "a", "b"),
                _flow("f2", "b", "a"),
            ),
        )
        facts = build_facts(model).danger_ok
        demand, witness = facts.propagated_demand("b")
        assert demand == float("inf")
        assert "a" in witness and "b" in witness

    # frob:tests src/frob/strata/_facts.py::FactBase.propagated_demand kind="unit"
    def test_unfed_cycle_contributes_zero(self) -> None:
        model = KernelModel(
            nodes=(_node("a"), _node("b")),
            flows=(_flow("f1", "a", "b"), _flow("f2", "b", "a")),
        )
        facts = build_facts(model).danger_ok
        assert facts.demand("b") == 0.0


class TestSkewUtilization:
    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_skew_refutes_where_mean_would_prove(self) -> None:
        """Same demand/capacity numbers: unskewed proves, skewed refutes.

        4 replicas, mean utilization is clearly under limit, but the
        hottest shard under a sharp zipf skew (alpha=1.5) takes far more
        than its even 25% share, pushing it over the same 80% limit.
        """
        capacity = Capacity(
            service_rate=Quantity(value=100, unit="/s"),
            replicas_min=1,
            replicas_max=4,
        )
        flows = (_flow("f1", "src", "hot", rate=Quantity(value=150, unit="/s")),)
        nodes_unskewed = (_node("src"), _node("hot", capacity=capacity))
        nodes_skewed = (
            _node("src"),
            _node("hot", capacity=capacity, attrs=("skew=1.5",)),
        )
        claim = Claim(
            id="c1",
            body=BoundClaim(
                metric=Metric.UTILIZATION,
                target="hot",
                limit=Quantity(value=80, unit="%"),
            ),
        )

        unskewed = _one(KernelModel(nodes=nodes_unskewed, flows=flows, claims=(claim,)))
        skewed = _one(KernelModel(nodes=nodes_skewed, flows=flows, claims=(claim,)))

        # mean utilization: 150 / (100*4) = 37.5% -- well under 80%, PROVED.
        assert unskewed.verdict is Verdict.PROVED
        # hottest-shard utilization is much higher under zipf skew: REFUTED,
        # and the detail names the hottest-shard share.
        assert skewed.verdict is Verdict.REFUTED
        assert "hottest-shard share" in skewed.detail

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_skew_single_replica_matches_mean(self) -> None:
        """With replicas_max=1 the hottest shard *is* the only shard: share is 1.0."""
        capacity = Capacity(service_rate=Quantity(value=100, unit="/s"))
        model = KernelModel(
            nodes=(_node("src"), _node("hot", capacity=capacity, attrs=("skew=1.5",))),
            flows=(_flow("f1", "src", "hot", rate=Quantity(value=50, unit="/s")),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.UTILIZATION,
                        target="hot",
                        limit=Quantity(value=80, unit="%"),
                    ),
                ),
            ),
        )
        result = _one(model)
        assert result.verdict is Verdict.PROVED
        assert "50.0%" in result.detail


class TestGrowthHorizon:
    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_growth_flips_proved_to_refuted_with_month_count(self) -> None:
        capacity = Capacity(service_rate=Quantity(value=100, unit="/s"))
        model = KernelModel(
            nodes=(_node("src"), _node("api", capacity=capacity)),
            flows=(
                _flow(
                    "f1",
                    "src",
                    "api",
                    rate=Quantity(value=70, unit="/s"),
                    attrs=("growth=10",),
                ),
            ),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.UTILIZATION,
                        target="api",
                        limit=Quantity(value=80, unit="%"),
                    ),
                ),
            ),
        )
        result = _one(model, today=dt.date(2026, 7, 17))
        # utilization0 = 70%, limit 80%, 10%/mo compound: crosses within a
        # few months -- well inside the 24-month deny-by-default horizon.
        assert result.verdict is Verdict.REFUTED
        assert "saturates in" in result.detail
        assert "months (2026-" in result.detail or "months (2027-" in result.detail

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_no_growth_stays_proved(self) -> None:
        capacity = Capacity(service_rate=Quantity(value=100, unit="/s"))
        model = KernelModel(
            nodes=(_node("src"), _node("api", capacity=capacity)),
            flows=(_flow("f1", "src", "api", rate=Quantity(value=70, unit="/s")),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.UTILIZATION,
                        target="api",
                        limit=Quantity(value=80, unit="%"),
                    ),
                ),
            ),
        )
        result = _one(model)
        assert result.verdict is Verdict.PROVED

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_slow_growth_beyond_horizon_stays_proved(self) -> None:
        capacity = Capacity(service_rate=Quantity(value=100, unit="/s"))
        model = KernelModel(
            nodes=(_node("src"), _node("api", capacity=capacity)),
            flows=(
                _flow(
                    "f1",
                    "src",
                    "api",
                    rate=Quantity(value=50, unit="/s"),
                    attrs=("growth=0.1",),
                ),
            ),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.UTILIZATION,
                        target="api",
                        limit=Quantity(value=80, unit="%"),
                    ),
                ),
            ),
        )
        result = _one(model)
        # 50% -> 80% at 0.1%/mo compound growth takes centuries: PROVED.
        assert result.verdict is Verdict.PROVED


# ---------------------------------------------------------------------
# Property test: propagated_demand vs. a brute-force recursive oracle
# ---------------------------------------------------------------------

_NODE_IDS = tuple(f"n{i}" for i in range(8))


@st.composite
def _fanout_dag(draw: st.DrawFn):
    """A random DAG (edges only lower->higher index) with rates and fanouts."""
    n = draw(st.integers(min_value=1, max_value=8))
    nodes = _NODE_IDS[:n]
    edges: list[tuple[str, str, str, float | None, float]] = []
    eid = 0
    for i in range(n):
        for j in range(i + 1, n):
            if draw(st.booleans()):
                has_rate = draw(st.booleans())
                rate = (
                    draw(st.floats(min_value=0.0, max_value=50.0, allow_nan=False))
                    if has_rate
                    else None
                )
                fanout = draw(st.floats(min_value=0.1, max_value=3.0, allow_nan=False))
                edges.append((f"f{eid}", nodes[i], nodes[j], rate, fanout))
                eid += 1
    return nodes, edges


def _oracle_demand(
    nodes: tuple[str, ...],
    edges: list[tuple[str, str, str, float | None, float]],
    target: str,
) -> float:
    """Brute-force recursive oracle matching the documented v0 semantics."""
    incoming: dict[str, list[tuple[str, str, float | None, float]]] = {}
    for fid, src, dst, rate, fanout in edges:
        incoming.setdefault(dst, []).append((fid, src, rate, fanout))
    memo: dict[str, float] = {}

    def rec(node: str) -> float:
        if node in memo:
            return memo[node]
        total = 0.0
        for _fid, src, rate, fanout in incoming.get(node, ()):
            if rate is not None:
                total += rate * fanout
            else:
                total += rec(src) * fanout
        memo[node] = total
        return total

    return rec(target)


@settings(max_examples=50, deadline=None)
@given(_fanout_dag())
def test_propagated_demand_matches_oracle_on_dags(graph) -> None:
    """On acyclic graphs (no cycles possible), `propagated_demand` matches
    a pure-Python recursive oracle over every fanout/rate combination."""
    import math

    import strata_core

    nodes, edges = graph
    if not nodes:
        return
    target = nodes[-1]
    got, _witness = strata_core.propagated_demand(edges, target)
    want = _oracle_demand(nodes, edges, target)
    assert math.isclose(got, want, rel_tol=1e-9, abs_tol=1e-9)
