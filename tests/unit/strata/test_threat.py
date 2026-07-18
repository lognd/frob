"""Unit tests for the `std.cwe` catalog + THREAT001-THREAT005
(docs/strata/threat.md, T-0109/T-0111/T-0112/T-0113).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from frob.strata import (
    BenignCapability,
    Boundary,
    BoundaryDirection,
    Claim,
    Flow,
    KernelModel,
    Node,
    NoFlow,
    OutOfScopeEntry,
    Reach,
    Rung,
    WeaknessEntry,
    bind_code,
    check_capability_completeness,
    check_catalog_completeness,
    check_discharge_completeness,
    check_effect_completeness,
    evaluate_threats,
)
from frob.strata._effects import _may_kind
from frob.strata._threat import CWE_CATALOG, VIEWS, _discharge_claim_id


def _write(root: Path, rel: str, source: str) -> None:
    """Test helper: write `source` to `root/rel`, creating parent dirs."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


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


class TestDischargeChokepointShape:
    """Phase C (T-0113, docs/strata/threat.md#phasing item C): a discharging
    claim must PROVE a mitigation chokepoint (a NoFlow(src=foreign, dst=node)
    claim), not merely exist at the right rung -- "declared somewhere" is no
    longer enough."""

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_reach_claim_does_not_discharge_as_a_chokepoint(self):
        node = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(node,),
            claims=(
                Claim(
                    id=claim_id,
                    body=Reach(src="Web", dst="Web"),
                    required_rung=Rung.L4,
                ),
            ),
        )
        result = check_discharge_completeness(model)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "THREAT003"
        assert "does not prove a mitigation chokepoint" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_noflow_claim_with_wrong_dst_does_not_discharge(self):
        node = Node(id="Web", trust="trusted", may=("html_render",))
        other = Node(id="Other", trust="trusted")
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(node, other),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="foreign", dst="Other"),
                    required_rung=Rung.L4,
                ),
            ),
        )
        result = check_discharge_completeness(model)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert "does not prove a mitigation chokepoint" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_noflow_from_a_specific_foreign_trust_node_discharges(self):
        node = Node(id="Web", trust="trusted", may=("html_render",))
        evil = Node(id="Evil", trust="foreign")
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(node, evil),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="Evil", dst="Web"),
                    required_rung=Rung.L4,
                ),
            ),
        )
        result = check_discharge_completeness(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_noflow_from_a_non_foreign_node_does_not_discharge(self):
        node = Node(id="Web", trust="trusted", may=("html_render",))
        internal = Node(id="Internal", trust="trusted")
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(node, internal),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="Internal", dst="Web"),
                    required_rung=Rung.L4,
                ),
            ),
        )
        result = check_discharge_completeness(model)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert "does not prove a mitigation chokepoint" in violations[0].detail


class TestMitigationKindChokepoint:
    """Review round 2 (docs/strata/threat.md#phasing item C): a discharging
    `NoFlow` claim proving "SOME boundary blocks every path" is not enough
    -- the boundary(ies) doing the blocking must carry the CATALOG's exact
    required mitigation (`direction=ENDORSE`, `predicate ==
    WeaknessEntry.mitigation`), not merely any boundary of any kind."""

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_declassify_boundary_does_not_discharge(self):
        evil = Node(id="Evil", trust="foreign")
        web = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(evil, web),
            flows=(Flow(id="f1", src="Evil", dst="Web"),),
            boundaries=(
                Boundary(
                    id="b1",
                    flow_id="f1",
                    direction=BoundaryDirection.DECLASSIFY,
                    from_level="foreign",
                    to_level="trusted",
                    predicate="legal_review_signed_off",
                ),
            ),
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
        assert "not of the required mitigation kind" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_endorse_boundary_with_wrong_predicate_does_not_discharge(self):
        evil = Node(id="Evil", trust="foreign")
        web = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(evil, web),
            flows=(Flow(id="f1", src="Evil", dst="Web"),),
            boundaries=(
                Boundary(
                    id="b1",
                    flow_id="f1",
                    direction=BoundaryDirection.ENDORSE,
                    from_level="foreign",
                    to_level="trusted",
                    predicate="legal_review_signed_off",
                ),
            ),
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
        assert "not of the required mitigation kind" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_endorse_boundary_with_matching_predicate_discharges(self):
        evil = Node(id="Evil", trust="foreign")
        web = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(evil, web),
            flows=(Flow(id="f1", src="Evil", dst="Web"),),
            boundaries=(
                Boundary(
                    id="b1",
                    flow_id="f1",
                    direction=BoundaryDirection.ENDORSE,
                    from_level="foreign",
                    to_level="trusted",
                    predicate="output_encoding",
                ),
            ),
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
    def test_mixed_paths_matching_on_one_wrong_kind_on_other_does_not_discharge(self):
        # Two independent Evil->Web routes. The ORIGINAL (unrestricted)
        # NoFlow proves: both f1 and f2 carry SOME boundary, so
        # `reachable(through_barriers=False)` sees no unblocked path. But
        # only f1's boundary is the catalog-correct mitigation kind -- with
        # every non-matching boundary removed, f2 reopens a path, so the
        # documented quantifier (matching boundaries alone must cut the
        # closure) correctly refutes discharge.
        evil = Node(id="Evil", trust="foreign")
        web = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(evil, web),
            flows=(
                Flow(id="f1", src="Evil", dst="Web"),
                Flow(id="f2", src="Evil", dst="Web"),
            ),
            boundaries=(
                Boundary(
                    id="b1",
                    flow_id="f1",
                    direction=BoundaryDirection.ENDORSE,
                    from_level="foreign",
                    to_level="trusted",
                    predicate="output_encoding",
                ),
                Boundary(
                    id="b2",
                    flow_id="f2",
                    direction=BoundaryDirection.DECLASSIFY,
                    from_level="foreign",
                    to_level="trusted",
                    predicate="legal_review_signed_off",
                ),
            ),
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
        assert "not of the required mitigation kind" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_assumed_claim_bypasses_the_mitigation_kind_check(self):
        # An assumed claim never reaches the closure at all
        # (`evaluate_claims` short-circuits it to ASSUMED), so there is no
        # boundary-kind proof to inspect -- the owner/review gate is its
        # only accountability, same as every other claim form.
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


class TestBenignCapability:
    # frob:tests src/frob/strata/_threat.py::BenignCapability kind="unit"
    def test_empty_reason_is_rejected(self):
        with pytest.raises(ValidationError):
            BenignCapability(kind="metrics", reason="")


class TestCapabilityCompleteness:
    # frob:tests src/frob/strata/_threat.py::check_capability_completeness kind="unit"
    def test_known_capability_kind_is_classified(self):
        node = Node(id="Web", trust="trusted", may=("html_render", "sql"))
        result = check_capability_completeness(KernelModel(nodes=(node,)))
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_capability_completeness kind="unit"
    def test_unknown_capability_kind_is_a_violation(self):
        node = Node(id="Web", trust="trusted", may=("mystery_power",))
        result = check_capability_completeness(KernelModel(nodes=(node,)))
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "THREAT002"
        assert violations[0].capability == "mystery_power"
        assert violations[0].node == "Web"
        assert violations[0].cwe == ""

    # frob:tests src/frob/strata/_threat.py::check_capability_completeness kind="unit"
    def test_benign_capability_excuses_an_unknown_kind(self):
        node = Node(id="Web", trust="trusted", may=("metrics",))
        result = check_capability_completeness(
            KernelModel(nodes=(node,)),
            benign=(BenignCapability(kind="metrics", reason="no CWE weakness"),),
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_capability_completeness kind="unit"
    def test_kind_scoped_may_atom_is_still_classified(self):
        node = Node(id="Web", trust="trusted", may=("sql:orders_db",))
        result = check_capability_completeness(KernelModel(nodes=(node,)))
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_capability_completeness kind="unit"
    def test_no_capabilities_no_violations(self):
        model = KernelModel(nodes=(Node(id="Api", trust="trusted"),))
        result = check_capability_completeness(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_capability_completeness kind="unit"
    def test_multiple_unknown_kinds_each_violate(self):
        node = Node(id="Web", trust="trusted", may=("foo", "bar"))
        result = check_capability_completeness(KernelModel(nodes=(node,)))
        assert result.is_ok
        kinds = {v.capability for v in result.danger_ok}
        assert kinds == {"foo", "bar"}

    # frob:tests src/frob/strata/_threat.py::check_capability_completeness kind="unit"
    def test_non_default_catalog_moves_the_taxonomy_with_it(self):
        # A catalog with an extra bespoke entry must make its capability_kind
        # a known sink for THREAT002 too -- the join is derived from the
        # `catalog` argument, never a module-level default-catalog cache
        # (structural single-source with `_fired_obligations`).
        extra = WeaknessEntry(
            id="CWE-000",
            title="bespoke",
            cite="https://example.invalid/CWE-000",
            capability_kind="widget_render",
            mitigation="widget_encoding",
        )
        catalog = (*CWE_CATALOG, extra)
        node = Node(id="Web", trust="trusted", may=("widget_render",))
        result = check_capability_completeness(
            KernelModel(nodes=(node,)), catalog=catalog
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_capability_completeness kind="unit"
    def test_thin_catalog_shrinks_the_taxonomy_with_it(self):
        # Dropping CWE-79 from the catalog must make html_render unclassified
        # for THREAT002 too -- same non-divergence guarantee in reverse.
        thin_catalog = tuple(e for e in CWE_CATALOG if e.id != "CWE-79")
        node = Node(id="Web", trust="trusted", may=("html_render",))
        result = check_capability_completeness(
            KernelModel(nodes=(node,)), catalog=thin_catalog
        )
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].capability == "html_render"


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
    def test_unclassified_capability_reports_threat002(self):
        node = Node(id="Web", trust="trusted", may=("mystery_power",))
        model = KernelModel(nodes=(node,))
        report = evaluate_threats(model, "owasp-top-10")
        assert report.is_ok
        rules = {v.rule for v in report.danger_ok.violations}
        assert "THREAT002" in rules

    # frob:tests src/frob/strata/_threat.py::evaluate_threats kind="unit"
    def test_benign_capability_param_excuses_threat002(self):
        node = Node(id="Web", trust="trusted", may=("metrics",))
        model = KernelModel(nodes=(node,))
        report = evaluate_threats(
            model,
            "owasp-top-10",
            benign=(BenignCapability(kind="metrics", reason="no CWE weakness"),),
        )
        assert report.is_ok
        assert report.danger_ok.violations == ()

    # frob:tests src/frob/strata/_threat.py::evaluate_threats kind="unit"
    def test_unknown_view_fails_closed(self):
        model = KernelModel(nodes=())
        report = evaluate_threats(model, "no-such-view")
        assert report.is_err

    # frob:tests src/frob/strata/_threat.py::evaluate_threats kind="unit"
    def test_binding_and_root_wire_in_threat004_and_threat005(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "subprocess.run(['x'])\n")
        node = Node(id="Api", trust="trusted", attrs=("code=api/**",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok
        report = evaluate_threats(model, "owasp-top-10", binding=binding, root=tmp_path)
        assert report.is_ok
        rules = {v.rule for v in report.danger_ok.violations}
        assert "THREAT004" in rules

    # frob:tests src/frob/strata/_threat.py::evaluate_threats kind="unit"
    def test_no_binding_or_root_skips_effect_completeness(self):
        model = KernelModel(nodes=(Node(id="Api", trust="trusted"),))
        report = evaluate_threats(model, "owasp-top-10")
        assert report.is_ok
        assert report.danger_ok.violations == ()


class TestCheckEffectCompleteness:
    """Phase C (T-0113, docs/strata/threat.md#phasing item C): the code-level
    join of `_effects.py::extract_effects` against the `std.cwe` sink
    taxonomy -- THREAT004 (undeclared capability in code) and THREAT005
    (extracted sink the catalog does not recognize, unless benign)."""

    # frob:tests src/frob/strata/_threat.py::check_effect_completeness kind="unit"
    def test_undeclared_sink_is_threat004(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "subprocess.run(['x'])\n")
        node = Node(id="Api", trust="trusted", attrs=("code=api/**",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok
        result = check_effect_completeness(model, binding, tmp_path)
        assert result.is_ok
        rules = {v.rule for v in result.danger_ok}
        assert "THREAT004" in rules
        undeclared = [v for v in result.danger_ok if v.rule == "THREAT004"]
        assert undeclared[0].node == "Api"
        assert undeclared[0].capability == "exec"

    # frob:tests src/frob/strata/_threat.py::check_effect_completeness kind="unit"
    def test_declared_capability_silences_threat004(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "subprocess.run(['x'])\n")
        node = Node(id="Api", trust="trusted", attrs=("code=api/**",), may=("exec",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok
        result = check_effect_completeness(model, binding, tmp_path)
        assert result.is_ok
        assert all(v.rule != "THREAT004" for v in result.danger_ok)

    # frob:tests src/frob/strata/_threat.py::check_effect_completeness kind="unit"
    def test_unclassified_sink_kind_is_threat005(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "requests.get('https://x')\n")
        node = Node(id="Api", trust="trusted", attrs=("code=api/**",), may=("net",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok
        result = check_effect_completeness(model, binding, tmp_path)
        assert result.is_ok
        # "net" silences THREAT004 (declared) but the catalog has no
        # capability_kind == "net" entry, so THREAT005 still fires.
        rules = {v.rule for v in result.danger_ok}
        assert rules == {"THREAT005"}
        assert result.danger_ok[0].capability == "net"

    # frob:tests src/frob/strata/_threat.py::check_effect_completeness kind="unit"
    def test_benign_capability_excuses_threat005(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "requests.get('https://x')\n")
        node = Node(id="Api", trust="trusted", attrs=("code=api/**",), may=("net",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok
        result = check_effect_completeness(
            model,
            binding,
            tmp_path,
            benign=(BenignCapability(kind="net", reason="no CWE weakness for net"),),
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_effect_completeness kind="unit"
    def test_classified_sink_with_declared_capability_is_clean(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "subprocess.run(['x'])\n")
        node = Node(id="Api", trust="trusted", attrs=("code=api/**",), may=("exec",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok
        result = check_effect_completeness(model, binding, tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_effect_completeness kind="unit"
    def test_foreign_code_is_not_joined(self, tmp_path: Path):
        _write(tmp_path, "scripts/one_off.py", "subprocess.run(['x'])\n")
        model = KernelModel(nodes=(Node(id="Api", trust="trusted"),))
        binding = bind_code(model, tmp_path).danger_ok
        result = check_effect_completeness(model, binding, tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_effect_completeness kind="unit"
    def test_non_default_catalog_moves_the_sink_taxonomy_with_it(self, tmp_path: Path):
        _write(tmp_path, "api/handler.py", "requests.get('https://x')\n")
        extra = WeaknessEntry(
            id="CWE-000",
            title="bespoke net weakness",
            cite="https://example.invalid/CWE-000",
            capability_kind="net",
            mitigation="allowlist_mediation",
        )
        catalog = (*CWE_CATALOG, extra)
        node = Node(id="Api", trust="trusted", attrs=("code=api/**",), may=("net",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok
        result = check_effect_completeness(model, binding, tmp_path, catalog=catalog)
        assert result.is_ok
        assert result.danger_ok == ()
