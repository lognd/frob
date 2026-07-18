"""Unit tests for the `std.cwe` catalog + THREAT001/THREAT003
(docs/strata/threat.md, T-0109/T-0111).
"""

from __future__ import annotations

from frob.strata import (
    Claim,
    Flow,
    KernelModel,
    Node,
    NoFlow,
    OutOfScopeEntry,
    Rung,
    check_catalog_completeness,
    check_discharge_completeness,
    evaluate_threats,
)
from frob.strata._effects import _may_kind
from frob.strata._threat import CWE_CATALOG, VIEWS, _discharge_claim_id


class TestMayKind:
    # frob:tests src/frob/strata/_effects.py::_may_kind kind="unit"
    def test_splits_on_dot_or_colon(self):
        assert _may_kind("net.out:stripe.com") == "net"
        assert _may_kind("exec:*") == "exec"
        assert _may_kind("sql") == "sql"


class TestCatalogCompleteness:
    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    def test_full_catalog_satisfies_owasp_top_10_view(self):
        result = check_catalog_completeness("owasp-top-10")
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    def test_missing_entry_is_a_violation(self):
        thin_catalog = tuple(e for e in CWE_CATALOG if e.id != "CWE-79")
        result = check_catalog_completeness("owasp-top-10", catalog=thin_catalog)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "THREAT001"
        assert violations[0].cwe == "CWE-79"

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    def test_out_of_scope_entry_excuses_a_missing_catalog_entry(self):
        thin_catalog = tuple(e for e in CWE_CATALOG if e.id != "CWE-79")
        result = check_catalog_completeness(
            "owasp-top-10",
            catalog=thin_catalog,
            out_of_scope=(OutOfScopeEntry(id="CWE-79", reason="no html_render yet"),),
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    def test_unknown_view_fails_closed(self):
        result = check_catalog_completeness("no-such-view")
        assert result.is_err

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    def test_views_table_is_data_driven(self):
        assert "owasp-top-10" in VIEWS
        assert VIEWS["owasp-top-10"] == frozenset(e.id for e in CWE_CATALOG)


class TestDischargeCompleteness:
    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_no_capability_no_fired_obligation(self):
        model = KernelModel(nodes=(Node(id="Api", trust="trusted"),))
        result = check_discharge_completeness(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_fired_obligation_with_no_claim_is_a_violation(self):
        model = KernelModel(
            nodes=(Node(id="Web", trust="trusted", may=("html_render",)),)
        )
        result = check_discharge_completeness(model)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "THREAT003"
        assert violations[0].cwe == "CWE-79"
        assert violations[0].node == "Web"

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_fired_obligation_discharged_by_proved_claim(self):
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
        result = check_discharge_completeness(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_discharge_claim_below_required_rung_is_a_violation(self):
        node = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(node,),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="foreign", dst="Web"),
                    required_rung=Rung.L2,
                ),
            ),
        )
        result = check_discharge_completeness(model)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert "below catalog rung" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_assumed_claim_without_owner_or_review_is_a_violation(self):
        node = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(node,),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="foreign", dst="Web"),
                    required_rung=Rung.L4,
                    assumed=True,
                ),
            ),
        )
        result = check_discharge_completeness(model)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert "no owner/review date" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_assumed_claim_with_owner_and_review_is_discharged(self):
        node = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(node,),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="foreign", dst="Web"),
                    required_rung=Rung.L4,
                    assumed=True,
                    owner="security-team",
                    review="2099-01-01",
                ),
            ),
        )
        result = check_discharge_completeness(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_multiple_capability_kinds_fire_multiple_obligations(self):
        node = Node(id="Web", trust="trusted", may=("html_render", "sql"))
        result = check_discharge_completeness(model=KernelModel(nodes=(node,)))
        assert result.is_ok
        cwes = {v.cwe for v in result.danger_ok}
        assert cwes == {"CWE-79", "CWE-89"}

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_discharge_claim_that_evaluates_refuted_is_a_violation(self):
        evil = Node(id="evil", trust="foreign")
        web = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(evil, web),
            flows=(Flow(id="f1", src="evil", dst="Web"),),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="foreign", dst="Web"),
                    required_rung=Rung.L4,
                ),
            ),
        )
        result = check_discharge_completeness(model)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "THREAT003"
        assert violations[0].cwe == "CWE-79"
        assert violations[0].node == "Web"
        assert "REFUTED" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_kind_scoped_may_atom_still_fires(self):
        node = Node(id="Web", trust="trusted", may=("sql:orders_db",))
        result = check_discharge_completeness(model=KernelModel(nodes=(node,)))
        assert result.is_ok
        assert {v.cwe for v in result.danger_ok} == {"CWE-89"}


class TestEvaluateThreats:
    # frob:waive PERF003 reason="two set comprehensions over small fixtures, not a join"
    # frob:tests src/frob/strata/_threat.py::evaluate_threats kind="unit"
    def test_conjoins_catalog_and_discharge_violations(self):
        node = Node(id="Web", trust="trusted", may=("html_render",))
        thin_catalog = tuple(e for e in CWE_CATALOG if e.id != "CWE-89")
        model = KernelModel(nodes=(node,))
        report = evaluate_threats(model, "owasp-top-10", catalog=thin_catalog)
        assert report.is_ok
        rules = {v.rule for v in report.danger_ok.violations}
        assert rules == {"THREAT001", "THREAT003"}

    # frob:tests src/frob/strata/_threat.py::evaluate_threats kind="unit"
    def test_clean_model_and_full_catalog_has_no_violations(self):
        model = KernelModel(nodes=(Node(id="Api", trust="trusted"),))
        report = evaluate_threats(model, "owasp-top-10")
        assert report.is_ok
        assert report.danger_ok.violations == ()

    # frob:tests src/frob/strata/_threat.py::evaluate_threats kind="unit"
    def test_unknown_view_fails_closed(self):
        model = KernelModel(nodes=())
        report = evaluate_threats(model, "no-such-view")
        assert report.is_err
