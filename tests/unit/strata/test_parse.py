"""Unit tests for the strata surface parser (docs/strata/surface.md#parser)."""

from __future__ import annotations

from frob.strata import Module, StrataError, parse_module


class TestParseModule:
    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_bare_module(self):
        result = parse_module("module payments")
        assert result.is_ok
        module = result.danger_ok
        assert isinstance(module, Module)
        assert module.name == "payments"
        assert module.nodes == ()

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_node_with_all_properties(self):
        text = """
        module m
        node api : trusted abstract {
            clearance Secret;
            attr idempotent;
            attr region=us;
            residence us_east;
            capacity 100 req/s replicas 1..8;
        }
        """
        module = parse_module(text).danger_ok
        node = module.nodes[0]
        assert node.id == "api"
        assert node.trust == "trusted"
        assert node.is_abstract is True
        assert node.clearance == "Secret"
        assert node.attrs == ("idempotent", "region=us")
        assert node.residence == "us_east"
        assert node.capacity is not None
        assert node.capacity.rate.value == 100
        assert node.capacity.rate.unit == "req/s"
        assert node.capacity.replicas_min == 1
        assert node.capacity.replicas_max == 8

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_flow_with_all_properties_and_units(self):
        text = """
        module m
        flow f1 : a -> b {
            label Pii;
            age 250 ms;
            rate 5 req/s;
            size 4 KiB;
            attr delivery=at_least_once;
            transport tls;
        }
        """
        module = parse_module(text).danger_ok
        flow = module.flows[0]
        assert flow.src == "a"
        assert flow.dst == "b"
        assert flow.label == "Pii"
        assert flow.age is not None and flow.age.value == 250 and flow.age.unit == "ms"
        assert (
            flow.rate is not None and flow.rate.value == 5 and flow.rate.unit == "req/s"
        )
        assert (
            flow.size is not None and flow.size.value == 4 and flow.size.unit == "KiB"
        )
        assert flow.attrs == ("delivery=at_least_once",)
        assert flow.transport == ("tls",)

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_percent_unit_and_bound_claim(self):
        text = "module m\nassert c1 bound utilization api <= 80 %"
        module = parse_module(text).danger_ok
        claim = module.claims[0]
        assert claim.kind == "bound"
        assert claim.metric == "utilization"
        assert claim.target == "api"
        assert claim.limit is not None
        assert claim.limit.value == 80
        assert claim.limit.unit == "%"

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_boundary(self):
        text = (
            "module m\n"
            'boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified"'
        )
        module = parse_module(text).danger_ok
        boundary = module.boundaries[0]
        assert boundary.kind == "endorse"
        assert boundary.flow_id == "f1"
        assert boundary.from_level == "foreign"
        assert boundary.to_level == "authenticated"
        assert boundary.predicate == "jwt_verified"

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_assert_noflow_and_reach(self):
        text = "module m\nassert c1 noflow evil -> api\nassert c2 reach audit -> log"
        module = parse_module(text).danger_ok
        assert module.claims[0].kind == "noflow"
        assert module.claims[0].src == "evil"
        assert module.claims[0].dst == "api"
        assert module.claims[1].kind == "reach"

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_assume_with_owner_and_review(self):
        text = 'module m\nassume c1 noflow evil -> api owner alice review "2026-08-01"'
        claim = parse_module(text).danger_ok.claims[0]
        assert claim.assumed is True
        assert claim.owner == "alice"
        assert claim.review == "2026-08-01"

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_module_missing_is_parse_failed(self):
        result = parse_module("node a : trusted")
        assert result.is_err
        assert result.danger_err is StrataError.ParseFailed

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_unknown_keyword_is_parse_failed(self):
        result = parse_module("module m\nbogus x")
        assert result.is_err
        assert result.danger_err is StrataError.ParseFailed

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_duplicate_module_is_parse_failed(self):
        result = parse_module("module a\nmodule b")
        assert result.is_err
        assert result.danger_err is StrataError.ParseFailed

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_round_trip_small_design(self):
        text = """
        module payments
        node api : trusted { clearance Pii; capacity 100 req/s replicas 1..8; }
        node evil : foreign
        flow f1 : evil -> api { label Pii; rate 5 req/s; transport tls; }
        boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified"
        assert c1 noflow evil -> api
        assume c2 bound age api <= 30 s owner alice review "2026-09-01"
        """
        module = parse_module(text).danger_ok
        assert module.name == "payments"
        assert len(module.nodes) == 2
        assert len(module.flows) == 1
        assert len(module.boundaries) == 1
        assert len(module.claims) == 2
