"""Unit tests for the strata scenario engine (docs/strata/kernel.md#scenario)."""

from __future__ import annotations

from frob.strata import (
    RemoveDecl,
    RemoveNode,
    ScaleDecl,
    ScaleRate,
    Scenario,
    ScenarioResult,
    SetTrust,
    StrataError,
    TrustDecl,
    Verdict,
    elaborate,
    evaluate_scenarios,
    parse_module,
)

_MODULE_TEXT = """
module m
node a : trusted
node b : trusted
node c : foreign
flow f1 : a -> b { rate 5 req/s; }
flow f2 : b -> c
boundary bd1 endorse f2 : foreign -> trusted when "x"
assert base_claim noflow foreign -> a

scenario node_loss {
    remove b;
    assert c1 noflow foreign -> a;
}

scenario surge {
    scale f1 by 3;
    assert c2 bound rate b <= 100 req/s;
}

scenario compromise {
    trust a := foreign;
    assert c3 noflow foreign -> a;
}
"""


class TestParseScenario:
    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_all_rewrite_kinds_and_nested_claims(self):
        module = parse_module(_MODULE_TEXT).danger_ok
        assert len(module.scenarios) == 3
        node_loss = module.scenarios[0]
        assert node_loss.id == "node_loss"
        assert node_loss.rewrites == (RemoveDecl(node_id="b"),)
        assert node_loss.claims[0].id == "c1"

        surge = module.scenarios[1]
        assert surge.rewrites == (ScaleDecl(flow_id="f1", factor=3.0),)

        compromise = module.scenarios[2]
        assert compromise.rewrites == (TrustDecl(node_id="a", level="foreign"),)

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_scenario_claims_do_not_leak_into_module_claims(self):
        module = parse_module(_MODULE_TEXT).danger_ok
        assert [c.id for c in module.claims] == ["base_claim"]


class TestElaborateScenario:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_elaborates_every_rewrite_kind(self):
        module = parse_module(_MODULE_TEXT).danger_ok
        model = elaborate(module).danger_ok
        assert len(model.scenarios) == 3
        assert model.scenarios[0].id == "node_loss"
        remove_rewrite = model.scenarios[0].rewrites[0]
        assert isinstance(remove_rewrite, RemoveNode)
        assert remove_rewrite.node_id == "b"
        scale_rewrite = model.scenarios[1].rewrites[0]
        assert isinstance(scale_rewrite, ScaleRate)
        assert scale_rewrite.factor == 3.0
        trust_rewrite = model.scenarios[2].rewrites[0]
        assert isinstance(trust_rewrite, SetTrust)
        assert trust_rewrite.level == "foreign"

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_fails_closed_on_unknown_rewrite_target(self):
        text = """
        module m
        node a : trusted
        scenario s {
            remove nonexistent;
        }
        """
        module = parse_module(text).danger_ok
        result = elaborate(module)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_fails_closed_on_unknown_trust_level(self):
        text = """
        module m
        node a : trusted
        scenario s {
            trust a := nonexistent_level;
        }
        """
        module = parse_module(text).danger_ok
        result = elaborate(module)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownLevel


class TestEvaluateScenarios:
    # frob:tests src/frob/strata/_scenarios.py::evaluate_scenarios kind="unit"
    # frob:waive PERF003 reason="a list comprehension plus a sibling all()-generator over scenarios, each independent; not a nested join"
    def test_evaluates_every_scenario_in_declaration_order(self):
        module = parse_module(_MODULE_TEXT).danger_ok
        model = elaborate(module).danger_ok
        result = evaluate_scenarios(model)
        assert result.is_ok
        scenarios = result.danger_ok
        assert [s.scenario_id for s in scenarios] == [
            "node_loss",
            "surge",
            "compromise",
        ]
        assert all(isinstance(s, ScenarioResult) for s in scenarios)

    # frob:tests src/frob/strata/_scenarios.py::evaluate_scenarios kind="unit"
    def test_remove_node_cascades_to_flows_and_boundaries(self):
        text = """
        module m
        node a : foreign
        node b : trusted
        node c : trusted
        flow f1 : a -> b
        flow f2 : b -> c
        boundary bd1 endorse f1 : foreign -> trusted when "x"

        scenario node_loss {
            remove b;
            assert unreachable reach a -> c;
        }
        """
        module = parse_module(text).danger_ok
        model = elaborate(module).danger_ok
        result = evaluate_scenarios(model)
        assert result.is_ok
        (scenario_result,) = result.danger_ok
        # b is gone, so f1/f2/bd1 cascade away; a -> c is no longer reachable.
        assert scenario_result.results[0].verdict is Verdict.REFUTED

    # frob:tests src/frob/strata/_scenarios.py::evaluate_scenarios kind="unit"
    def test_scale_rate_multiplies_declared_rate(self):
        text = """
        module m
        node a : trusted
        node b : trusted
        flow f1 : a -> b { rate 5 req/s; }

        scenario surge {
            scale f1 by 3;
            assert too_hot bound rate b <= 10 req/s;
        }
        """
        module = parse_module(text).danger_ok
        model = elaborate(module).danger_ok
        result = evaluate_scenarios(model)
        assert result.is_ok
        (scenario_result,) = result.danger_ok
        # 5 req/s * 3 = 15 req/s > 10 req/s limit.
        assert scenario_result.results[0].verdict is Verdict.REFUTED

    # frob:tests src/frob/strata/_scenarios.py::evaluate_scenarios kind="unit"
    def test_scale_rate_fails_closed_on_unrated_flow(self):
        text = """
        module m
        node a : trusted
        node b : trusted
        flow f1 : a -> b

        scenario surge {
            scale f1 by 3;
            assert too_hot bound rate b <= 10 req/s;
        }
        """
        module = parse_module(text).danger_ok
        model = elaborate(module).danger_ok
        result = evaluate_scenarios(model)
        assert result.is_err
        assert result.danger_err is StrataError.UnratedFlow

    # frob:tests src/frob/strata/_scenarios.py::evaluate_scenarios kind="unit"
    def test_set_trust_reassigns_node_trust(self):
        text = """
        module m
        node a : trusted
        node b : trusted
        flow f1 : a -> b

        scenario compromise {
            trust a := foreign;
            assert now_untrusted noflow foreign -> b;
        }
        """
        module = parse_module(text).danger_ok
        model = elaborate(module).danger_ok
        result = evaluate_scenarios(model)
        assert result.is_ok
        (scenario_result,) = result.danger_ok
        # a is now "foreign", and flows to b, so foreign -> b is refuted.
        assert scenario_result.results[0].verdict is Verdict.REFUTED

    # frob:tests src/frob/strata/_scenarios.py::evaluate_scenarios kind="unit"
    def test_never_mutates_the_input_model(self):
        text = """
        module m
        node a : trusted
        node b : trusted
        flow f1 : a -> b { rate 5 req/s; }

        scenario surge {
            scale f1 by 3;
            assert c1 bound rate b <= 100 req/s;
        }
        """
        module = parse_module(text).danger_ok
        model = elaborate(module).danger_ok
        # Full structural snapshot: a scenario rewrites a COPY, so the whole
        # input model -- not just the scaled flow -- must compare equal after.
        snapshot = model.model_copy(deep=True)
        evaluate_scenarios(model)
        assert model == snapshot

    # frob:tests src/frob/strata/_scenarios.py::evaluate_scenarios kind="unit"
    def test_empty_scenarios_returns_empty_tuple(self):
        module = parse_module("module m\nnode a : trusted").danger_ok
        model = elaborate(module).danger_ok
        result = evaluate_scenarios(model)
        assert result.is_ok
        assert result.danger_ok == ()


class TestScenarioResultModel:
    # frob:tests src/frob/strata/_scenarios.py::ScenarioResult kind="unit"
    def test_is_frozen_and_identity_of_value(self):
        r1 = ScenarioResult(scenario_id="s", results=())
        r2 = ScenarioResult(scenario_id="s", results=())
        assert r1 == r2
        assert hash(r1) == hash(r2)


class TestScenarioModel:
    # frob:tests src/frob/strata/_models.py::Scenario kind="unit"
    def test_scenario_is_frozen_and_hashable(self):
        s = Scenario(id="s", rewrites=(), claims=())
        assert hash(s) is not None
