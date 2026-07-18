"""Unit tests for `frob.strata._sysdoc` -- the `frob sys doc` audit matrix
and DOC003's model-side claims audit (T-0085, docs/strata/threat.md#the-
exhaustiveness-proof-the-point).
"""

from __future__ import annotations

from frob.strata import (
    CWE_CATALOG,
    Claim,
    KernelModel,
    Node,
    NoFlow,
    OutOfScopeEntry,
    Rung,
    StrataError,
    audit_claim,
    merge_models,
    render_audit_matrix,
)
from frob.strata._threat import _discharge_claim_id


class TestMergeModels:
    # frob:tests src/frob/strata/_sysdoc.py::merge_models kind="unit"
    def test_concat_fields(self):
        a = KernelModel(nodes=(Node(id="A", trust="trusted"),))
        b = KernelModel(nodes=(Node(id="B", trust="trusted"),))
        merged = merge_models((a, b))
        assert [n.id for n in merged.nodes] == ["A", "B"]

    # frob:tests src/frob/strata/_sysdoc.py::merge_models kind="unit"
    def test_empty_tuple(self):
        assert merge_models(()) == KernelModel()


class TestRenderAuditMatrix:
    # frob:tests src/frob/strata/_sysdoc.py::render_audit_matrix kind="unit"
    def test_unknown_view_is_an_error(self):
        result = render_audit_matrix(KernelModel(), "no-such-view")
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_sysdoc.py::render_audit_matrix kind="unit"
    def test_empty_model_names_every_catalog_entry_unevaluated_or_absent(self):
        result = render_audit_matrix(KernelModel(), "owasp-top-10")
        assert result.is_ok
        text = result.danger_ok
        assert "CWE-79" in text
        assert "## security" in text
        assert "PROVED" not in text

    # frob:tests src/frob/strata/_sysdoc.py::render_audit_matrix kind="unit"
    def test_discharged_obligation_renders_proved(self):
        node = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(node,),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="foreign", dst="Web"),
                    required_rung=Rung.L4,
                ),
            ),
        )
        result = render_audit_matrix(model, "owasp-top-10")
        assert result.is_ok
        text = result.danger_ok
        assert "PROVED (L4)" in text
        assert "| CWE-79 |" in text

    # frob:tests src/frob/strata/_sysdoc.py::render_audit_matrix kind="unit"
    def test_undischarged_obligation_renders_failing(self):
        model = KernelModel(
            nodes=(Node(id="Web", trust="trusted", may=("html_render",)),)
        )
        result = render_audit_matrix(model, "owasp-top-10")
        assert result.is_ok
        text = result.danger_ok
        assert "FAILING:" in text

    # frob:tests src/frob/strata/_sysdoc.py::render_audit_matrix kind="unit"
    def test_out_of_scope_entry_gets_its_own_section(self):
        thin = tuple(e for e in CWE_CATALOG if e.id != "CWE-79")
        result = render_audit_matrix(
            KernelModel(),
            "owasp-top-10",
            catalog=thin,
            out_of_scope=(OutOfScopeEntry(id="CWE-79", reason="no html_render yet"),),
        )
        assert result.is_ok
        text = result.danger_ok
        assert "## out-of-scope" in text
        assert "no html_render yet" in text
        assert "## catalog gaps" not in text

    # frob:tests src/frob/strata/_sysdoc.py::render_audit_matrix kind="unit"
    def test_deterministic_rendering(self):
        model = KernelModel(
            nodes=(Node(id="Web", trust="trusted", may=("html_render",)),)
        )
        first = render_audit_matrix(model, "owasp-top-10")
        second = render_audit_matrix(model, "owasp-top-10")
        assert first.danger_ok == second.danger_ok


class TestAuditClaim:
    # frob:tests src/frob/strata/_sysdoc.py::audit_claim kind="unit"
    def test_unknown_view_is_an_error(self):
        result = audit_claim(KernelModel(), "no-such-view")
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_sysdoc.py::audit_claim kind="unit"
    def test_empty_model_is_proved_no_capabilities_ever_fire(self):
        result = audit_claim(KernelModel(), "owasp-top-10")
        assert result.is_ok
        assert result.danger_ok.proved is True
        assert result.danger_ok.violations == ()

    # frob:tests src/frob/strata/_sysdoc.py::audit_claim kind="unit"
    def test_undischarged_obligation_is_not_proved_and_names_it(self):
        model = KernelModel(
            nodes=(Node(id="Web", trust="trusted", may=("html_render",)),)
        )
        result = audit_claim(model, "owasp-top-10")
        assert result.is_ok
        audit = result.danger_ok
        assert audit.proved is False
        assert any(v.cwe == "CWE-79" for v in audit.violations)

    # frob:tests src/frob/strata/_sysdoc.py::audit_claim kind="unit"
    def test_discharged_obligation_is_proved(self):
        node = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(node,),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="foreign", dst="Web"),
                    required_rung=Rung.L4,
                ),
            ),
        )
        result = audit_claim(model, "owasp-top-10")
        assert result.is_ok
        assert result.danger_ok.proved is True
