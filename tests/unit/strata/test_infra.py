"""Unit tests for std.infra elaboration (docs/strata/surface.md#std-infra)."""

from __future__ import annotations

from frob.strata import (
    BoundaryDirection,
    Quantifier,
    StrataError,
    Verdict,
    elaborate,
    elaborate_infra,
    evaluate_claims,
    parse_module,
)


def _elaborate(text: str):
    module = parse_module(text).danger_ok
    return elaborate(module)


class TestStoreDesugar:
    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_store_becomes_node_with_markers(self):
        text = """
        module m
        store db : trusted {
            clearance Pii;
            engine postgres;
            immutable;
            append_only;
        }
        """
        model = _elaborate(text).danger_ok
        node = next(n for n in model.nodes if n.id == "db")
        assert node.trust == "trusted"
        assert node.clearance == "Pii"
        assert "engine=postgres" in node.attrs
        assert "immutable" in node.attrs
        assert "append_only" in node.attrs

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_store_rpo_becomes_seconds_attr(self):
        text = """
        module m
        store db : trusted {
            rpo 5 min;
        }
        """
        model = _elaborate(text).danger_ok
        node = next(n for n in model.nodes if n.id == "db")
        assert "rpo=300.0" in node.attrs

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_store_rpo_wrong_dimension_fails_closed(self):
        text = """
        module m
        store db : trusted {
            rpo 5 MiB;
        }
        """
        result = _elaborate(text)
        assert result.danger_err is StrataError.UnitMismatch


class TestCacheDesugar:
    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    # frob:waive PERF003 reason="three sibling next()-generator lookups over model.nodes/model.flows, each with its own == filter; not a nested join"
    def test_cache_node_and_fill_flow(self):
        text = """
        module m
        node api : trusted
        store db : trusted { clearance Pii; }
        flow w1 : api -> db { label Pii; }
        cache c of db {
            keyed_by user_id;
            staleness 30 s;
            hit 90 %;
            policy lru;
            invalidate_on w1;
        }
        """
        model = _elaborate(text).danger_ok
        node = next(n for n in model.nodes if n.id == "c")
        assert node.trust == "trusted"
        assert node.clearance == "Pii"
        assert "hit=90.0" in node.attrs
        assert "policy=lru" in node.attrs
        assert "keyed_by=user_id" in node.attrs

        fill = next(f for f in model.flows if f.id == "c__fill")
        assert fill.src == "db"
        assert fill.dst == "c"
        assert fill.age is not None
        assert fill.age.value == 30.0
        assert fill.age.unit == "s"

        inval = next(f for f in model.flows if f.id == "c__inval_w1")
        assert inval.src == "db"
        assert inval.dst == "c"
        assert inval.age is not None
        assert inval.age.value == 0.0

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_ttl_and_staleness_must_agree(self):
        text = """
        module m
        store db : trusted
        cache c of db { ttl 30 s; staleness 60 s; invalidate_on w1; }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.MissingBound

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_ttl_and_staleness_agreeing_is_ok(self):
        text = """
        module m
        store db : trusted
        cache c of db { ttl 30 s; staleness 30 s; }
        """
        model = _elaborate(text).danger_ok
        fill = next(f for f in model.flows if f.id == "c__fill")
        assert fill.age.value == 30.0

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_cache_with_no_bound_is_err(self):
        text = """
        module m
        store db : trusted
        cache c of db { policy lru; }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.MissingBound

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_cache_without_invalidation_is_err(self):
        text = """
        module m
        node api : trusted
        store db : trusted
        flow w1 : api -> db
        cache c of db { staleness 30 s; }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.MissingInvalidation

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_cache_no_inbound_writes_needs_no_invalidation(self):
        text = """
        module m
        store db : trusted
        cache c of db { staleness 30 s; }
        """
        model = _elaborate(text).danger_ok
        assert any(n.id == "c" for n in model.nodes)

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_invalidate_on_wrong_dst_is_err(self):
        text = """
        module m
        node api : trusted
        node other : trusted
        store db : trusted
        flow w1 : api -> other
        cache c of db { staleness 30 s; invalidate_on w1; }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.MissingInvalidation


class TestQueueDesugar:
    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_queue_node_attrs(self):
        text = """
        module m
        queue q { delivery at_least_once; ordering fifo; }
        """
        model = _elaborate(text).danger_ok
        node = next(n for n in model.nodes if n.id == "q")
        assert "delivery=at_least_once" in node.attrs
        assert "ordering=fifo" in node.attrs

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_queue_no_trust_clause_defaults_to_trusted(self):
        text = """
        module m
        queue q { delivery at_least_once; }
        """
        model = _elaborate(text).danger_ok
        node = next(n for n in model.nodes if n.id == "q")
        assert node.trust == "trusted"

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_queue_explicit_trust_clause_wins_over_default(self):
        # T-0093: queue may declare TRUST explicitly instead of the
        # "trusted" default (docs/strata/surface.md#std-infra).
        text = """
        module m
        queue q : authenticated { delivery at_least_once; }
        """
        model = _elaborate(text).danger_ok
        node = next(n for n in model.nodes if n.id == "q")
        assert node.trust == "authenticated"

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    # frob:waive PERF003 reason="a next()-generator lookup over model.flows plus a sibling any()-generator over facts.diagnostics; not a nested join"
    def test_queue_delivery_propagates_to_outbound_flows_and_fires_diagnostic(self):
        text = """
        module m
        queue q { delivery at_least_once; }
        node consumer : trusted
        flow f1 : q -> consumer
        """
        module = parse_module(text).danger_ok
        model = elaborate(module).danger_ok
        flow = next(f for f in model.flows if f.id == "f1")
        assert "delivery=at_least_once" in flow.attrs

        from frob.strata._facts import build_facts

        facts = build_facts(model).danger_ok
        assert any(
            "at-least-once delivery" in d and "consumer" in d for d in facts.diagnostics
        )


class TestCdnDesugar:
    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    # frob:waive PERF003 reason="two sibling next()-generator lookups over model.nodes/model.flows, each with its own == filter; not a nested join"
    def test_cdn_node_and_fill_flow(self):
        text = """
        module m
        store origin : trusted { clearance Internal; }
        cdn c of origin {
            provider fastly : authenticated;
            staleness 5 min;
            hit 95 %;
        }
        """
        model = _elaborate(text).danger_ok
        node = next(n for n in model.nodes if n.id == "c")
        assert node.trust == "authenticated"
        assert node.clearance == "Internal"
        assert "provider=fastly" in node.attrs
        assert "hit=95.0" in node.attrs
        fill = next(f for f in model.flows if f.id == "c__fill")
        assert fill.src == "origin"
        assert fill.dst == "c"
        assert fill.age.value == 5.0
        assert fill.age.unit == "min"

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_cdn_unlimited_on_mutable_is_err(self):
        text = """
        module m
        store origin : trusted
        cdn c of origin { provider fastly : authenticated; staleness unlimited; }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.MutableUnbounded

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_cdn_unlimited_on_immutable_is_ok(self):
        text = """
        module m
        store origin : trusted { immutable; }
        cdn c of origin { provider fastly : authenticated; staleness unlimited; }
        """
        model = _elaborate(text).danger_ok
        fill = next(f for f in model.flows if f.id == "c__fill")
        assert fill.age is None

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_cdn_missing_provider_is_err(self):
        text = """
        module m
        store origin : trusted
        cdn c of origin { staleness 5 min; }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.MissingBound

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_cdn_tls_terminates_adds_declassify_boundary(self):
        text = """
        module m
        store origin : trusted { clearance Pii; }
        cdn c of origin {
            provider fastly : authenticated;
            staleness 5 min;
            tls_terminates_at_provider;
        }
        """
        model = _elaborate(text).danger_ok
        boundary = next(b for b in model.boundaries if b.id == "c__declassify")
        assert boundary.direction is BoundaryDirection.DECLASSIFY
        assert boundary.flow_id == "c__fill"
        assert boundary.from_level == "Pii"
        assert boundary.to_level == "Public"
        assert boundary.predicate == "tls_terminates_at_provider"


class TestBalancerDesugar:
    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_balancer_node_attrs(self):
        text = """
        module m
        balancer b { policy round_robin; sticky; }
        """
        model = _elaborate(text).danger_ok
        node = next(n for n in model.nodes if n.id == "b")
        assert "policy=round_robin" in node.attrs
        assert "sticky" in node.attrs
        assert node.trust == "trusted"

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_balancer_explicit_trust_clause_wins_over_default(self):
        # T-0093: balancer may declare TRUST explicitly instead of the
        # "trusted" default (docs/strata/surface.md#std-infra).
        text = """
        module m
        balancer b : authenticated { policy round_robin; }
        """
        model = _elaborate(text).danger_ok
        node = next(n for n in model.nodes if n.id == "b")
        assert node.trust == "authenticated"

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_sticky_balancer_stateless_downstream_is_diagnostic(self):
        text = """
        module m
        balancer b { sticky; }
        node worker : trusted { attr state=none; }
        flow f1 : b -> worker
        """
        module = parse_module(text).danger_ok
        base_model = elaborate(module)
        assert base_model.is_ok

        # Re-run elaborate_infra directly against the std.trust base facts
        # to inspect the diagnostic InfraExpansion carries (the elaborator
        # only logs it -- KernelModel, a kernel type, gains no new field).
        from frob.strata._elaborate import (
            _elaborate_boundary,
            _elaborate_flow,
            _elaborate_node,
        )

        nodes = tuple(_elaborate_node(n) for n in module.nodes)
        flows = tuple(_elaborate_flow(f) for f in module.flows)
        boundaries = tuple(_elaborate_boundary(b) for b in module.boundaries)
        expansion = elaborate_infra(module, nodes, flows, boundaries).danger_ok
        assert any(
            "sticky" in d and "worker" in d and "state=none" in d
            for d in expansion.diagnostics
        )


class TestEndToEnd:
    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_cache_staleness_refutes_age_bound_claim(self):
        text = """
        module m
        node api : trusted
        store db : trusted
        flow w1 : api -> db
        cache c of db { staleness 60 s; invalidate_on w1; }
        assert age_ok bound age c <= 10 s
        """
        module = parse_module(text).danger_ok
        model = elaborate(module).danger_ok
        results = evaluate_claims(model).danger_ok
        result = next(r for r in results if r.claim_id == "age_ok")
        assert result.verdict is Verdict.REFUTED
        assert result.quantifier is Quantifier.FORALL
        assert "60" in result.detail


class TestStoreCapacity:
    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_store_capacity_maps_through_to_the_kernel_node(self):
        from frob.strata import elaborate, parse_module

        src = """module m
store db : trusted { engine postgres; capacity 100 req/s replicas 2 .. 4 }
"""
        module = parse_module(src).danger_ok
        model = elaborate(module).danger_ok
        node = {n.id: n for n in model.nodes}["db"]
        assert node.capacity is not None
        assert node.capacity.service_rate.value == 100
        assert node.capacity.replicas_max == 4
