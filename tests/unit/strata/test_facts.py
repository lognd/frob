"""Unit tests for the strata fact base and closure engine (docs/strata/kernel.md)."""

# frob:waive OPAQUE001 reason="T-1038: sys.modules replacement below fakes an import \
# target for one test's own fixture module, standard unittest.mock/sys.modules test \
# isolation -- deliberate test infrastructure, not an evasion risk"

from __future__ import annotations

import sys

import pytest

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
    def test_negative_age_fails_closed(self):
        model = KernelModel(
            nodes=(_node("a"), _node("b")),
            flows=(_flow("f1", "a", "b", age=Quantity(value=-1, unit="s")),),
        )
        assert build_facts(model).danger_err is StrataError.NegativeQuantity

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_negative_rate_fails_closed(self):
        model = KernelModel(
            nodes=(_node("a"), _node("b")),
            flows=(_flow("f1", "a", "b", rate=Quantity(value=-5, unit="req/s")),),
        )
        assert build_facts(model).danger_err is StrataError.NegativeQuantity

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_nonnegative_age_is_accepted(self):
        model = KernelModel(
            nodes=(_node("a"), _node("b")),
            flows=(_flow("f1", "a", "b", age=Quantity(value=0, unit="s")),),
        )
        assert build_facts(model).is_ok

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
    def test_krb_no_transit_attr_stops_chaining_past_that_hop(self):
        # T-0282: a flow tagged krb_no_transit is a terminal edge -- its
        # dst is reachable directly, but the closure must not chain past
        # it to extend the path any further.
        model = KernelModel(
            nodes=(_node("a"), _node("b"), _node("c")),
            flows=(
                _flow("f1", "a", "b", attrs=("krb_trust", "krb_no_transit")),
                _flow("f2", "b", "c"),
            ),
        )
        facts = build_facts(model).danger_ok
        paths = facts.reachable("a")
        assert "b" in paths
        assert "c" not in paths

    # frob:tests src/frob/strata/_facts.py::FactBase.reachable kind="unit"
    def test_utility_attr_stops_chaining_past_that_hop(self):
        # T-0226/T-0496: a flow tagged `utility` (the general-purpose
        # surface marker `flow ... { utility; }`) is a terminal edge under
        # `through_barriers=True` (the existential reach/independent/
        # readers/krb-movement closures) -- its dst is reachable directly,
        # but the closure must not chain past it there.
        model = KernelModel(
            nodes=(_node("a"), _node("b"), _node("c")),
            flows=(
                _flow("f1", "a", "b", attrs=("utility",)),
                _flow("f2", "b", "c"),
            ),
        )
        facts = build_facts(model).danger_ok
        paths = facts.reachable("a", through_barriers=True)
        assert "b" in paths
        assert "c" not in paths

    # frob:tests src/frob/strata/_facts.py::FactBase.reachable kind="unit"
    def test_utility_attr_does_not_stop_chaining_for_confidentiality_noflow(self):
        """T-0496 (docs/audits/strata.md G5): the confidentiality closure
        (`through_barriers=False`, the ONLY caller being `noflow`) must NOT
        honor `utility` as terminal -- a real downstream leak transiting an
        otherwise-innocuous `utility`-marked hub must still be caught.
        Repro straight from the ticket: `log_hub{utility}` then a real
        `leak` edge out of the hub -- `c` MUST be reached, not silently
        hidden the way the pre-fix behavior hid it."""
        model = KernelModel(
            nodes=(_node("a"), _node("b"), _node("c")),
            flows=(
                _flow("f1", "a", "b", attrs=("utility",)),
                _flow("f2", "b", "c"),
            ),
        )
        facts = build_facts(model).danger_ok
        paths = facts.reachable("a")
        assert "b" in paths
        assert "c" in paths

    # frob:tests src/frob/strata/_facts.py::FactBase.reachable kind="unit"
    def test_krb_no_transit_still_terminal_for_confidentiality_noflow(self):
        """`krb_no_transit` is NOT excluded from `_NOFLOW_NON_TRANSITIVE_
        ATTRS` (T-0496's comment: no known equivalent gap for it) -- it
        stays a terminal edge under `through_barriers=False` too, same as
        before this ticket's fix."""
        model = KernelModel(
            nodes=(_node("a"), _node("b"), _node("c")),
            flows=(
                _flow("f1", "a", "b", attrs=("krb_trust", "krb_no_transit")),
                _flow("f2", "b", "c"),
            ),
        )
        facts = build_facts(model).danger_ok
        paths = facts.reachable("a")
        assert "b" in paths
        assert "c" not in paths

    # frob:tests src/frob/strata/_facts.py::FactBase.reachable kind="unit"
    def test_utility_attr_does_not_defeat_a_real_transitive_flow(self):
        # No weakening: an UNMARKED hub edge still lets a genuine
        # transitive flow reach all the way through -- only an explicitly
        # `utility`-marked edge is a terminal hop.
        model = KernelModel(
            nodes=(_node("a"), _node("b"), _node("c")),
            flows=(_flow("f1", "a", "b"), _flow("f2", "b", "c")),
        )
        facts = build_facts(model).danger_ok
        paths = facts.reachable("a")
        assert "c" in paths

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
    # invariant spec: [INV-028](invariants/INV-028.md)
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


class TestBuildFactsNativeExtensionUnavailable:
    """T-0134: a standalone tool install has no `strata_core` extension.

    `build_facts` used to do a module-level `import strata_core` and raise
    a bare `ImportError` on missing it -- crashing `frob check`'s sys_gate
    for any repo with a `design/` dir in a standalone install. Monkeypatch
    the module-level binding to `None` (the state a bare `uv tool install
    frob` leaves it in) and confirm `build_facts` degrades to a typed
    `Err` before touching any `strata_core` call, matching the T-0133
    pattern already applied to `frob.lang._walk_strata`.
    """

    @pytest.fixture(autouse=True)
    def _no_native_parser(self, monkeypatch: pytest.MonkeyPatch) -> None:
        facts_mod = sys.modules["frob.strata._facts"]
        monkeypatch.setattr(facts_mod, "strata_core", None)

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_build_facts_returns_native_extension_unavailable(self):
        model = KernelModel(
            nodes=(_node("a"), _node("b")), flows=(_flow("f1", "a", "b"),)
        )
        result = build_facts(model)
        assert result.is_err
        assert result.danger_err is StrataError.NativeExtensionUnavailable
