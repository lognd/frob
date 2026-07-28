"""Unit tests for strata refinement v0 (docs/strata/surface.md#refinement)."""

from __future__ import annotations

import datetime as dt

from frob.strata import (
    StrataError,
    Verdict,
    elaborate,
    evaluate_claims,
    parse_module,
)


def _elaborate(text: str):
    module = parse_module(text).danger_ok
    return elaborate(module)


class TestRefineHappyPath:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_flattens_abstract_node_and_rewires_outer_flow(self):
        text = """
        module m
        node evil : foreign
        node api : trusted abstract
        flow f1 : evil -> api
        refine api into {
            node inner : trusted
            flow fi : inner -> inner
            binds api = inner
        }
        """
        model = _elaborate(text).danger_ok

        node_ids = {n.id for n in model.nodes}
        assert "api" not in node_ids
        assert "inner" in node_ids

        inner = next(n for n in model.nodes if n.id == "inner")
        assert "abstract" not in inner.attrs

        outer_flow = next(f for f in model.flows if f.id == "f1")
        assert outer_flow.src == "evil"
        assert outer_flow.dst == "inner"

        inner_flow = next(f for f in model.flows if f.id == "fi")
        assert inner_flow.src == "inner"
        assert inner_flow.dst == "inner"

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_claim_endpoint_rewritten_and_still_evaluable(self):
        text = """
        module m
        node evil : foreign
        node api : trusted abstract
        flow f1 : evil -> api
        assert c1 noflow foreign -> api
        refine api into {
            node inner : trusted
            binds api = inner
        }
        """
        model = _elaborate(text).danger_ok
        claim = model.claims[0]
        assert claim.body.dst == "inner"
        # still evaluable: the rewritten claim body names a real node id.
        results = evaluate_claims(model, today=dt.date(2026, 7, 17)).danger_ok
        assert len(results) == 1

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_noflow_claim_proved_at_abstract_level_stays_proved_after_refinement(self):
        """The compositional-proof property: refinement must not re-refute
        a claim that already held against the abstraction (docs/strata/
        surface.md#refinement)."""
        abstract_text = """
        module m
        node evil : foreign
        node boundary_node : authenticated
        node api : trusted abstract
        flow f1 : evil -> boundary_node
        boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified"
        flow f2 : boundary_node -> api
        assert c1 noflow foreign -> api
        """
        abstract_model = _elaborate(abstract_text).danger_ok
        abstract_results = evaluate_claims(
            abstract_model, today=dt.date(2026, 7, 17)
        ).danger_ok
        assert abstract_results[0].verdict is Verdict.PROVED

        refined_text = """
        module m
        node evil : foreign
        node boundary_node : authenticated
        node api : trusted abstract
        flow f1 : evil -> boundary_node
        boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified"
        flow f2 : boundary_node -> api
        assert c1 noflow foreign -> api
        refine api into {
            node inner : trusted
            binds api = inner
        }
        """
        refined_model = _elaborate(refined_text).danger_ok
        refined_results = evaluate_claims(
            refined_model, today=dt.date(2026, 7, 17)
        ).danger_ok
        assert refined_results[0].verdict is Verdict.PROVED


class TestRefineViolations:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_refine_of_non_abstract_node_fails(self):
        text = """
        module m
        node api : trusted
        refine api into {
            node inner : trusted
            binds api = inner
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.RefinementViolation

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_refine_of_unknown_target_fails(self):
        text = """
        module m
        node other : trusted
        refine api into {
            node inner : trusted
            binds api = inner
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.RefinementViolation

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_inner_flow_touching_outer_id_fails_new_external_surface(self):
        text = """
        module m
        node outsider : trusted
        node api : trusted abstract
        refine api into {
            node inner : trusted
            flow fi : inner -> outsider
            binds api = inner
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.RefinementViolation

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_foreign_inner_node_under_trusted_abstract_fails_trust_laundering(self):
        text = """
        module m
        node api : trusted abstract
        refine api into {
            node inner : foreign
            binds api = inner
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.RefinementViolation

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_bind_to_not_an_inner_node_fails(self):
        text = """
        module m
        node api : trusted abstract
        refine api into {
            node inner : trusted
            binds api = not_inner
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.RefinementViolation


class TestUnrefinedFrontier:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_unrefined_abstract_node_keeps_marker(self):
        text = """
        module m
        node api : trusted abstract
        """
        model = _elaborate(text).danger_ok
        node = next(n for n in model.nodes if n.id == "api")
        assert "abstract" in node.attrs
