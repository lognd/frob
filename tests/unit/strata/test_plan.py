"""Unit tests for frob.strata._plan (T-0084 obligation -> ticket compiler)."""

from __future__ import annotations

from pathlib import Path

from frob.graph import GraphSnapshot
from frob.strata import (
    DesignIds,
    KernelModel,
    Node,
    StrataError,
    Verdict,
    elaborate,
    parse_module,
    plan_obligations,
)
from frob.strata._plan import MARKER_PREFIX

_ABSTRACT_MODEL = """
module m
node evil : foreign
node api : trusted abstract
flow f1 : evil -> api
"""

_REFUTED_MODEL = """
module m
node evil : foreign
node api : trusted
flow f1 : evil -> api
assert c1 noflow evil -> api
"""

_CLEAN_MODEL = """
module m
node evil : foreign
node api : trusted
flow f1 : evil -> api
"""


def _model(text: str):
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


def _empty_snapshot() -> GraphSnapshot:
    return GraphSnapshot(root=".", symbols={}, edges=())


class TestPlanObligations:
    # frob:tests src/frob/strata/_plan.py::plan_obligations kind="unit"
    def test_unrefined_frontier(self):
        result = plan_obligations(_model(_ABSTRACT_MODEL)).danger_ok
        markers = {t.marker for t in result.tickets}
        assert f"{MARKER_PREFIX}api:unrefined" in markers
        assert f"{MARKER_PREFIX}api:refine" in markers
        parent = next(t for t in result.tickets if t.marker.endswith(":unrefined"))
        child = next(t for t in result.tickets if t.marker.endswith(":refine"))
        assert child.parent_marker == parent.marker
        assert child.blocked_by_markers == (parent.marker,)

    # frob:tests src/frob/strata/_plan.py::plan_obligations kind="unit"
    def test_refuted_claim(self):
        result = plan_obligations(_model(_REFUTED_MODEL)).danger_ok
        markers = {t.marker for t in result.tickets}
        assert f"{MARKER_PREFIX}c1:refuted" in markers
        ticket = next(t for t in result.tickets if t.marker.endswith("c1:refuted"))
        assert "REFUTED" in ticket.body

    # frob:tests src/frob/strata/_plan.py::plan_obligations kind="unit"
    def test_clean_model_plans_nothing(self):
        result = plan_obligations(_model(_CLEAN_MODEL)).danger_ok
        assert result.tickets == ()

    # frob:tests src/frob/strata/_plan.py::plan_obligations kind="unit"
    def test_unbound_boundary(self):
        model = _model(_CLEAN_MODEL)
        design_ids = DesignIds(boundaries=frozenset({"b1"}))
        result = plan_obligations(
            model, design_ids=design_ids, snapshot=_empty_snapshot()
        ).danger_ok
        markers = {t.marker for t in result.tickets}
        assert f"{MARKER_PREFIX}b1:unbound" in markers

    # frob:tests src/frob/strata/_plan.py::plan_obligations kind="unit"
    def test_idempotent_markers(self):
        model = _model(_ABSTRACT_MODEL)
        first = plan_obligations(model).danger_ok
        second = plan_obligations(model).danger_ok
        assert {t.marker for t in first.tickets} == {t.marker for t in second.tickets}

    # frob:tests src/frob/strata/_plan.py::plan_obligations kind="unit"
    def test_threat_frontier(self):
        # A node declaring `may=("html_render",)` with no discharging claim
        # fires CWE-79 (THREAT003, docs/strata/threat.md) -- the same fixture
        # shape as test_threat.py::TestDischargeCompleteness
        # .test_fired_obligation_with_no_claim_is_a_violation.
        model = KernelModel(
            nodes=(Node(id="Web", trust="trusted", may=("html_render",)),)
        )
        result = plan_obligations(model).danger_ok
        markers = {t.marker for t in result.tickets}
        assert f"{MARKER_PREFIX}Web:CWE-79:threat" in markers
        ticket = next(t for t in result.tickets if t.marker.endswith(":threat"))
        assert ticket.title == "Discharge CWE-79 at Web"

    # frob:tests src/frob/strata/_plan.py::plan_obligations kind="unit"
    def test_root_given_binds_code_and_still_plans(self, tmp_path: Path):
        """T-0630: passing `root` binds `model` against the real tree
        (`bind_code`) once and threads it into the THREAT003 frontier --
        a successful binding must not change the ticket set for a model
        with no fired obligations. This is the untested `if root is not
        None` branch: without it a regression that silently stopped
        honoring `root` would go uncaught."""
        (tmp_path / "web").mkdir()
        (tmp_path / "web" / "handler.py").write_text("x = 1\n", encoding="utf-8")
        model = KernelModel(
            nodes=(Node(id="Web", trust="trusted", attrs=("code=web/**",)),)
        )
        result = plan_obligations(model, root=tmp_path)
        assert result.is_ok
        assert result.danger_ok.tickets == ()

    # frob:tests src/frob/strata/_plan.py::plan_obligations kind="unit"
    def test_ambiguous_code_binding_propagates_as_error(self, tmp_path: Path):
        """A `root` whose real tree makes `bind_code` itself fail (two
        nodes' `code=` globs both matching the same file) must propagate
        `Err(AmbiguousCodeBinding)` rather than silently planning tickets
        off a partial/missing binding -- the fail-closed REJECT path the
        docstring promises."""
        (tmp_path / "web").mkdir()
        (tmp_path / "web" / "handler.py").write_text("x = 1\n", encoding="utf-8")
        model = KernelModel(
            nodes=(
                Node(id="Web", trust="trusted", attrs=("code=web/**",)),
                Node(id="WebToo", trust="trusted", attrs=("code=web/*.py",)),
            )
        )
        result = plan_obligations(model, root=tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.AmbiguousCodeBinding


class TestClaimEvaluationSanity:
    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_refuted_model_actually_refutes(self):
        from frob.strata import evaluate_claims

        results = evaluate_claims(_model(_REFUTED_MODEL)).danger_ok
        c1 = next(r for r in results if r.claim_id == "c1")
        assert c1.verdict is Verdict.REFUTED
