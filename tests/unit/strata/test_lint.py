"""Unit tests for `std.lint`: operational design lints -- caching,
resource bounds, rate-limiting, and kill-switch rules (T-0155,
docs/strata/threat.md#operational-design-lints-std-lint-t-0155).

The hand-built-`KernelModel` half of the proof, mirroring `test_pii.py`'s
own convention; the surface-syntax half (parse -> elaborate ->
evaluate_lint) lives in `test_litmus_lint.py`.
"""

from __future__ import annotations

from frob.strata import (
    BoundClaim,
    Capacity,
    Claim,
    Flow,
    KernelModel,
    Metric,
    Node,
    Quantity,
    RemoveNode,
    ScaleRate,
    Scenario,
)
from frob.strata._lint import (
    RISKY_CAPABILITY_KINDS,
    check_lint_cache_or_capacity,
    check_lint_fanin_capacity,
    check_lint_kill_switch,
    check_lint_rate_limit,
    check_lint_surge_capacity_bound,
    evaluate_lint,
    node_flag_ids,
)


def _rate(value: float) -> Quantity:
    return Quantity(value=value, unit="req/s")


def _node(node_id: str, trust: str, **kwargs) -> Node:
    return Node(id=node_id, trust=trust, **kwargs)


class TestFlagHelper:
    # frob:tests src/frob/strata/_lint.py::node_flag_ids kind="unit"
    def test_node_flag_ids_reads_flag_prefixed_attrs(self):
        node = _node("api", "trusted", attrs=("flag=kill_x", "other"))
        assert node_flag_ids(node) == ("kill_x",)

    # frob:tests src/frob/strata/_lint.py::node_flag_ids kind="unit"
    def test_node_flag_ids_empty_with_no_flag_attrs(self):
        node = _node("api", "trusted", attrs=("engine=postgres",))
        assert node_flag_ids(node) == ()

    def test_risky_kinds_are_exec_and_net(self):
        assert RISKY_CAPABILITY_KINDS == frozenset({"exec", "net"})


class TestLintRateLimit:
    # frob:tests src/frob/strata/_lint.py::check_lint_rate_limit kind="unit"
    def test_foreign_flow_with_rate_is_clean(self):
        model = KernelModel(
            nodes=(_node("client", "foreign"), _node("api", "trusted")),
            flows=(Flow(id="f1", src="client", dst="api", rate=_rate(5.0)),),
        )
        result = check_lint_rate_limit(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_lint.py::check_lint_rate_limit kind="unit"
    def test_foreign_flow_with_no_rate_is_lint001(self):
        model = KernelModel(
            nodes=(_node("client", "foreign"), _node("api", "trusted")),
            flows=(Flow(id="f1", src="client", dst="api"),),
        )
        result = check_lint_rate_limit(model)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "LINT001"
        assert violations[0].target == "f1"

    # frob:tests src/frob/strata/_lint.py::check_lint_rate_limit kind="unit"
    def test_trusted_flow_with_no_rate_does_not_fire(self):
        model = KernelModel(
            nodes=(_node("a", "trusted"), _node("b", "trusted")),
            flows=(Flow(id="f1", src="a", dst="b"),),
        )
        result = check_lint_rate_limit(model)
        assert result.is_ok
        assert result.danger_ok == ()


class TestLintCacheOrCapacity:
    # frob:tests src/frob/strata/_lint.py::check_lint_cache_or_capacity kind="unit"
    def test_within_service_rate_is_clean(self):
        model = KernelModel(
            nodes=(
                _node("api", "trusted"),
                _node("store", "trusted", capacity=Capacity(service_rate=_rate(10.0))),
            ),
            flows=(Flow(id="f1", src="api", dst="store", rate=_rate(5.0)),),
        )
        result = check_lint_cache_or_capacity(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_lint.py::check_lint_cache_or_capacity kind="unit"
    def test_exceeding_service_rate_with_no_cache_is_lint002(self):
        model = KernelModel(
            nodes=(
                _node("api", "trusted"),
                _node("store", "trusted", capacity=Capacity(service_rate=_rate(5.0))),
            ),
            flows=(Flow(id="f1", src="api", dst="store", rate=_rate(10.0)),),
        )
        result = check_lint_cache_or_capacity(model)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "LINT002"
        assert violations[0].target == "store"

    # frob:tests src/frob/strata/_lint.py::check_lint_cache_or_capacity kind="unit"
    def test_exceeding_service_rate_with_cache_is_clean(self):
        model = KernelModel(
            nodes=(
                _node("api", "trusted"),
                _node("store", "trusted", capacity=Capacity(service_rate=_rate(5.0))),
                _node("store_cache", "trusted"),
            ),
            flows=(
                Flow(id="f1", src="api", dst="store", rate=_rate(10.0)),
                Flow(id="f_fill", src="store", dst="store_cache", attrs=("fill",)),
            ),
        )
        result = check_lint_cache_or_capacity(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_lint.py::check_lint_cache_or_capacity kind="unit"
    def test_fill_and_invalidation_flows_excluded_from_summed_load(self):
        model = KernelModel(
            nodes=(
                _node("store", "trusted", capacity=Capacity(service_rate=_rate(1.0))),
            ),
            flows=(
                Flow(
                    id="f_fill",
                    src="src_of_truth",
                    dst="store",
                    attrs=("fill",),
                    rate=_rate(50.0),
                ),
            ),
        )
        result = check_lint_cache_or_capacity(model)
        assert result.is_ok
        assert result.danger_ok == ()


class TestLintSurgeCapacityBound:
    # frob:tests src/frob/strata/_lint.py::check_lint_surge_capacity_bound kind="unit"
    def test_scale_rewrite_with_no_bound_claim_is_lint003(self):
        flow = Flow(id="f1", src="a", dst="b", rate=_rate(5.0))
        scenario = Scenario(
            id="surge", rewrites=(ScaleRate(flow_id="f1", factor=3.0),), claims=()
        )
        model = KernelModel(
            nodes=(_node("a", "trusted"), _node("b", "trusted")),
            flows=(flow,),
            scenarios=(scenario,),
        )
        violations = check_lint_surge_capacity_bound(model)
        assert len(violations) == 1
        assert violations[0].rule == "LINT003"
        assert violations[0].target == "surge"

    # frob:tests src/frob/strata/_lint.py::check_lint_surge_capacity_bound kind="unit"
    def test_scale_rewrite_with_bound_claim_on_flow_is_clean(self):
        flow = Flow(id="f1", src="a", dst="b", rate=_rate(5.0))
        bound = Claim(
            id="c1",
            body=BoundClaim(metric=Metric.RATE, target="f1", limit=_rate(100.0)),
        )
        scenario = Scenario(
            id="surge",
            rewrites=(ScaleRate(flow_id="f1", factor=3.0),),
            claims=(bound,),
        )
        model = KernelModel(
            nodes=(_node("a", "trusted"), _node("b", "trusted")),
            flows=(flow,),
            scenarios=(scenario,),
        )
        assert check_lint_surge_capacity_bound(model) == ()

    # frob:tests src/frob/strata/_lint.py::check_lint_surge_capacity_bound kind="unit"
    def test_scale_rewrite_with_bound_claim_on_endpoint_is_clean(self):
        flow = Flow(id="f1", src="a", dst="b", rate=_rate(5.0))
        bound = Claim(
            id="c1",
            body=BoundClaim(metric=Metric.UTILIZATION, target="b", limit=_rate(1.0)),
        )
        scenario = Scenario(
            id="surge",
            rewrites=(ScaleRate(flow_id="f1", factor=3.0),),
            claims=(bound,),
        )
        model = KernelModel(
            nodes=(_node("a", "trusted"), _node("b", "trusted")),
            flows=(flow,),
            scenarios=(scenario,),
        )
        assert check_lint_surge_capacity_bound(model) == ()

    # frob:tests src/frob/strata/_lint.py::check_lint_surge_capacity_bound kind="unit"
    def test_non_scale_rewrite_never_fires(self):
        scenario = Scenario(id="loss", rewrites=(RemoveNode(node_id="a"),), claims=())
        model = KernelModel(nodes=(_node("a", "trusted"),), scenarios=(scenario,))
        assert check_lint_surge_capacity_bound(model) == ()


class TestLintKillSwitch:
    # frob:tests src/frob/strata/_lint.py::check_lint_kill_switch kind="unit"
    def test_risky_capability_with_no_flag_is_lint004(self):
        model = KernelModel(nodes=(_node("api", "trusted", may=("exec",)),))
        violations = check_lint_kill_switch(model)
        assert len(violations) == 1
        assert violations[0].rule == "LINT004"
        assert violations[0].target == "api"

    # frob:tests src/frob/strata/_lint.py::check_lint_kill_switch kind="unit"
    def test_risky_capability_with_flag_is_clean(self):
        model = KernelModel(
            nodes=(_node("api", "trusted", may=("net.out:x",), attrs=("flag=kx",)),)
        )
        assert check_lint_kill_switch(model) == ()

    # frob:tests src/frob/strata/_lint.py::check_lint_kill_switch kind="unit"
    def test_non_risky_capability_never_fires(self):
        model = KernelModel(nodes=(_node("api", "trusted", may=("fs",)),))
        assert check_lint_kill_switch(model) == ()


class TestLintFaninCapacity:
    # frob:tests src/frob/strata/_lint.py::check_lint_fanin_capacity kind="unit"
    def test_fanin_within_headroom_is_clean(self):
        model = KernelModel(
            nodes=(
                _node("a", "trusted"),
                _node("b", "trusted"),
                _node(
                    "store",
                    "trusted",
                    capacity=Capacity(service_rate=_rate(5.0), replicas_max=2),
                ),
            ),
            flows=(
                Flow(id="f1", src="a", dst="store", rate=_rate(5.0)),
                Flow(id="f2", src="b", dst="store", rate=_rate(4.0)),
            ),
        )
        result = check_lint_fanin_capacity(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_lint.py::check_lint_fanin_capacity kind="unit"
    def test_fanin_exceeding_headroom_is_lint005_even_with_cache(self):
        model = KernelModel(
            nodes=(
                _node("a", "trusted"),
                _node(
                    "store",
                    "trusted",
                    capacity=Capacity(service_rate=_rate(5.0), replicas_max=1),
                ),
                _node("store_cache", "trusted"),
            ),
            flows=(
                Flow(id="f1", src="a", dst="store", rate=_rate(20.0)),
                Flow(id="f_fill", src="store", dst="store_cache", attrs=("fill",)),
            ),
        )
        result = check_lint_fanin_capacity(model)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "LINT005"
        assert violations[0].target == "store"


class TestEvaluateLint:
    # frob:tests src/frob/strata/_lint.py::evaluate_lint kind="unit"
    def test_clean_model_has_no_violations(self):
        model = KernelModel(nodes=(_node("api", "trusted"),))
        result = evaluate_lint(model)
        assert result.is_ok
        assert result.danger_ok.violations == ()

    # frob:tests src/frob/strata/_lint.py::evaluate_lint kind="unit"
    def test_evaluate_lint_aggregates_every_rule(self):
        kid = _node("client", "foreign")
        api = _node("api", "trusted")
        store = _node(
            "store",
            "trusted",
            may=("exec",),
            capacity=Capacity(service_rate=_rate(5.0), replicas_max=1),
        )
        f_open = Flow(id="f_open", src="client", dst="api")
        f_load = Flow(id="f_load", src="api", dst="store", rate=_rate(20.0))
        scenario = Scenario(
            id="surge", rewrites=(ScaleRate(flow_id="f_load", factor=3.0),), claims=()
        )
        model = KernelModel(
            nodes=(kid, api, store), flows=(f_open, f_load), scenarios=(scenario,)
        )
        result = evaluate_lint(model)
        assert result.is_ok
        rules = {v.rule for v in result.danger_ok.violations}
        assert rules == {"LINT001", "LINT002", "LINT003", "LINT004", "LINT005"}
