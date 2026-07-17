"""Unit tests for the strata fact base and closure engine (docs/strata/kernel.md)."""

from __future__ import annotations

from frob.strata import (
    Boundary,
    BoundaryDirection,
    Flow,
    KernelModel,
    Lattice,
    Node,
    Quantity,
    StrataError,
    build_facts,
)


def _node(nid: str, trust: str = "trusted", **kw) -> Node:
    return Node(id=nid, trust=trust, **kw)


def _flow(fid: str, src: str, dst: str, **kw) -> Flow:
    return Flow(id=fid, src=src, dst=dst, **kw)


def _endorse(bid: str, flow_id: str) -> Boundary:
    return Boundary(
        id=bid,
        flow_id=flow_id,
        direction=BoundaryDirection.ENDORSE,
        from_level="foreign",
        to_level="authenticated",
    )


class TestBuildFacts:
    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_builds_and_indexes_a_valid_model(self):
        model = KernelModel(
            nodes=(_node("a"), _node("b")),
            flows=(_flow("f1", "a", "b"),),
        )
        facts = build_facts(model).danger_ok
        assert facts.outgoing["a"] == ("f1",)
        assert facts.flows["f1"].dst == "b"
        assert facts.diagnostics == ()

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_duplicate_ids_fail_closed(self):
        model = KernelModel(nodes=(_node("a"), _node("a")))
        assert build_facts(model).danger_err is StrataError.DuplicateId

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_dangling_flow_endpoint_fails_closed(self):
        model = KernelModel(nodes=(_node("a"),), flows=(_flow("f1", "a", "ghost"),))
        assert build_facts(model).danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_dangling_boundary_flow_fails_closed(self):
        model = KernelModel(
            nodes=(_node("a"), _node("b")),
            flows=(_flow("f1", "a", "b"),),
            boundaries=(_endorse("b1", "ghost"),),
        )
        assert build_facts(model).danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_unknown_trust_level_fails_closed(self):
        model = KernelModel(nodes=(_node("a", trust="root"),))
        assert build_facts(model).danger_err is StrataError.UnknownLevel

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_cyclic_lattice_fails_closed(self):
        cyclic = Lattice(name="bad", order=(("x", "y"), ("y", "x")))
        model = KernelModel(trust=cyclic, nodes=(_node("a", trust="x"),))
        assert build_facts(model).danger_err is StrataError.MalformedLattice

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_at_least_once_into_non_idempotent_node_is_diagnosed(self):
        model = KernelModel(
            nodes=(_node("q"), _node("worker")),
            flows=(_flow("f1", "q", "worker", attrs=("delivery=at_least_once",)),),
        )
        facts = build_facts(model).danger_ok
        assert any("not declared idempotent" in d for d in facts.diagnostics)
        fixed = KernelModel(
            nodes=(_node("q"), _node("worker", attrs=("idempotent",))),
            flows=(_flow("f1", "q", "worker", attrs=("delivery=at_least_once",)),),
        )
        assert build_facts(fixed).danger_ok.diagnostics == ()

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_label_above_clearance_is_diagnosed(self):
        model = KernelModel(
            nodes=(_node("a"), _node("b", clearance="Public")),
            flows=(_flow("f1", "a", "b", label="Secret"),),
        )
        facts = build_facts(model).danger_ok
        assert any("exceeds clearance" in d for d in facts.diagnostics)


class TestClosure:
    # frob:tests src/frob/strata/_facts.py::FactBase.nodes_at kind="unit"
    def test_nodes_at_filters_by_exact_trust_level(self):
        model = KernelModel(
            nodes=(_node("evil", trust="foreign"), _node("api"), _node("db")),
        )
        facts = build_facts(model).danger_ok
        assert facts.nodes_at("foreign") == ("evil",)
        assert facts.nodes_at("trusted") == ("api", "db")

    # frob:tests src/frob/strata/_facts.py::FactBase.reachable kind="unit"
    def test_reachable_returns_witness_paths(self):
        model = KernelModel(
            nodes=(_node("a"), _node("b"), _node("c")),
            flows=(_flow("f1", "a", "b"), _flow("f2", "b", "c")),
        )
        facts = build_facts(model).danger_ok
        paths = facts.reachable("a")
        assert paths["c"] == ("a", "f1", "b", "f2", "c")

    # frob:tests src/frob/strata/_facts.py::FactBase.reachable kind="unit"
    def test_boundaries_stop_taint_unless_asked_otherwise(self):
        model = KernelModel(
            nodes=(_node("evil", trust="foreign"), _node("api")),
            flows=(_flow("f1", "evil", "api"),),
            boundaries=(_endorse("b1", "f1"),),
        )
        facts = build_facts(model).danger_ok
        assert "api" not in facts.reachable("evil")
        assert "api" in facts.reachable("evil", through_barriers=True)

    # frob:tests src/frob/strata/_facts.py::FactBase.worst_age kind="unit"
    def test_worst_age_accumulates_along_the_stalest_path(self):
        model = KernelModel(
            nodes=(_node("truth"), _node("replica"), _node("view")),
            flows=(
                _flow("f1", "truth", "replica", age=Quantity(value=5, unit="min")),
                _flow("f2", "replica", "view", age=Quantity(value=30, unit="s")),
                _flow("f3", "truth", "view"),  # fresh direct path is not the worst
            ),
        )
        facts = build_facts(model).danger_ok
        age, path = facts.worst_age("view")
        assert age == 330.0
        assert path == ("truth", "f1", "replica", "f2", "view")

    # frob:tests src/frob/strata/_facts.py::FactBase.worst_age kind="unit"
    def test_worst_age_reports_unbounded_on_a_positive_cycle(self):
        model = KernelModel(
            nodes=(_node("a"), _node("b")),
            flows=(
                _flow("f1", "a", "b", age=Quantity(value=1, unit="s")),
                _flow("f2", "b", "a", age=Quantity(value=1, unit="s")),
            ),
        )
        facts = build_facts(model).danger_ok
        age, _path = facts.worst_age("a")
        assert age == float("inf")

    # frob:tests src/frob/strata/_facts.py::FactBase.demand kind="unit"
    def test_demand_sums_inbound_rates_in_base_units(self):
        model = KernelModel(
            nodes=(_node("a"), _node("b"), _node("api")),
            flows=(
                _flow("f1", "a", "api", rate=Quantity(value=100, unit="req/s")),
                _flow("f2", "b", "api", rate=Quantity(value=120, unit="req/min")),
            ),
        )
        facts = build_facts(model).danger_ok
        assert facts.demand("api") == 102.0
