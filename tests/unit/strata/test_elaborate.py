"""Unit tests for the strata elaborator (docs/strata/surface.md#elaborator)."""

from __future__ import annotations

import datetime as dt

from frob.strata import (
    BoundaryDirection,
    BoundClaim,
    Metric,
    NoFlow,
    Quantifier,
    StrataError,
    Verdict,
    elaborate,
    evaluate_claims,
    parse_module,
)


class TestElaborateFullMapping:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_maps_every_construct_field_for_field(self):
        text = """
        module payments
        node api : trusted {
            clearance Secret;
            attr idempotent;
            capacity 100 req/s replicas 1..8;
        }
        node db : trusted { clearance Secret; }
        flow f1 : api -> db {
            label Pii;
            age 250 ms;
            rate 5 req/s;
            size 4 KiB;
            attr delivery=at_least_once;
            transport tls;
        }
        boundary b1 endorse f1 : foreign -> trusted when "jwt_verified"
        assert c1 noflow foreign -> db
        assert c2 bound utilization api <= 80 %
        assume c3 bound age api <= 30 s owner alice review "2026-12-01"
        """
        module = parse_module(text).danger_ok
        model = elaborate(module).danger_ok

        node = next(n for n in model.nodes if n.id == "api")
        assert node.trust == "trusted"
        assert node.clearance == "Secret"
        assert "idempotent" in node.attrs
        assert node.capacity is not None
        assert node.capacity.service_rate.value == 100
        assert node.capacity.service_rate.unit == "req/s"
        assert node.capacity.replicas_min == 1
        assert node.capacity.replicas_max == 8

        flow = model.flows[0]
        assert flow.src == "api"
        assert flow.dst == "db"
        assert flow.label == "Pii"
        assert flow.age is not None and flow.age.value == 250 and flow.age.unit == "ms"
        assert flow.rate is not None and flow.rate.value == 5
        assert (
            flow.size is not None and flow.size.value == 4 and flow.size.unit == "KiB"
        )
        assert flow.attrs == ("delivery=at_least_once",)
        assert flow.transport == ("tls",)

        boundary = model.boundaries[0]
        assert boundary.flow_id == "f1"
        assert boundary.direction is BoundaryDirection.ENDORSE
        assert boundary.from_level == "foreign"
        assert boundary.to_level == "trusted"
        assert boundary.predicate == "jwt_verified"

        noflow_claim = next(c for c in model.claims if c.id == "c1")
        assert isinstance(noflow_claim.body, NoFlow)
        assert noflow_claim.body.src == "foreign"
        assert noflow_claim.body.dst == "db"

        bound_claim = next(c for c in model.claims if c.id == "c2")
        assert isinstance(bound_claim.body, BoundClaim)
        assert bound_claim.body.metric is Metric.UTILIZATION
        assert bound_claim.body.target == "api"
        assert bound_claim.body.limit.value == 80
        assert bound_claim.body.limit.unit == "%"

        assume_claim = next(c for c in model.claims if c.id == "c3")
        assert assume_claim.assumed is True
        assert assume_claim.owner == "alice"
        assert assume_claim.review == "2026-12-01"


class TestElaborateAbstract:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_abstract_marker_preserved_in_attrs(self):
        text = """
        module m
        node api : trusted abstract { clearance Secret; }
        """
        module = parse_module(text).danger_ok
        model = elaborate(module).danger_ok
        assert "abstract" in model.nodes[0].attrs


class TestElaborateValidation:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_duplicate_node_id_fails_closed(self):
        text = """
        module m
        node api : trusted { clearance Secret; }
        node api : trusted { clearance Secret; }
        """
        module = parse_module(text).danger_ok
        result = elaborate(module)
        assert result.is_err
        assert result.danger_err is StrataError.DuplicateId

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_boundary_referencing_unknown_flow_fails_closed(self):
        text = """
        module m
        node api : trusted { clearance Secret; }
        node db : trusted { clearance Secret; }
        boundary b1 endorse ghost_flow : foreign -> trusted when "jwt_verified"
        """
        module = parse_module(text).danger_ok
        result = elaborate(module)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference


class TestElaborateEndToEnd:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_parse_elaborate_evaluate_matches_expected_verdicts(self):
        text = """
        module payments
        node evil : foreign { clearance Secret; }
        node rogue : foreign { clearance Secret; }
        node api : trusted { clearance Secret; }
        node db : trusted { clearance Secret; }
        node audit : trusted { clearance Secret; }
        flow f1 : evil -> api { label Public; }
        flow f2 : api -> db { label Public; }
        flow f3 : db -> audit { label Public; }
        flow f4 : rogue -> audit { label Public; }
        boundary b1 endorse f1 : foreign -> trusted when "jwt_verified"
        assert c1 noflow foreign -> db
        assert c2 reach db -> audit
        assert c3 noflow foreign -> audit
        """
        module = parse_module(text).danger_ok
        model = elaborate(module).danger_ok
        results = evaluate_claims(model, today=dt.date(2026, 7, 17)).danger_ok

        noflow_result = next(r for r in results if r.claim_id == "c1")
        assert noflow_result.verdict is Verdict.PROVED
        assert noflow_result.quantifier is Quantifier.FORALL

        reach_result = next(r for r in results if r.claim_id == "c2")
        assert reach_result.verdict is Verdict.PROVED
        assert reach_result.quantifier is Quantifier.EXISTS
        assert reach_result.counterexample == ("db", "f3", "audit")

        # c3 drives the refutation path: `rogue` (foreign) reaches `audit`
        # over the unendorsed flow f4, so the elaborator's fact production
        # is exercised on the failing side too, not just the happy path.
        refuted_result = next(r for r in results if r.claim_id == "c3")
        assert refuted_result.verdict is Verdict.REFUTED
        assert refuted_result.quantifier is Quantifier.FORALL
        assert refuted_result.counterexample == ("rogue", "f4", "audit")
