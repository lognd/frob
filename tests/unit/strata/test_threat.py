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
from frob.strata._threat import (
    CWE_CATALOG,
    CWE_TOP_25_CATALOG,
    CWE_TOP_25_OUT_OF_SCOPE,
    CWE_TOP_25_VIEWS,
    QUALITY_CATALOG,
    QUALITY_OUT_OF_SCOPE,
    QUALITY_VIEWS,
    VIEWS,
    _discharge_claim_id,
)


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


class TestQualityFamilies:
    """Phase E (T-0114, docs/strata/threat.md#phasing item E): the
    performance/reliability/compat anti-pattern families reuse THREAT001's
    machinery unmodified over `QUALITY_CATALOG`/`QUALITY_OUT_OF_SCOPE` and
    a family-scoped view -- these tests prove the SAME `check_catalog_
    completeness` entrypoint is exhaustive per family, and that the quality
    catalog never leaks into the `owasp-top-10` view it is kept separate
    from."""

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    def test_web_performance_baseline_is_satisfied(self):
        result = check_catalog_completeness(
            "web-performance-baseline",
            catalog=QUALITY_CATALOG,
            out_of_scope=QUALITY_OUT_OF_SCOPE,
            views=QUALITY_VIEWS,
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    def test_reliability_baseline_is_satisfied(self):
        result = check_catalog_completeness(
            "reliability-baseline",
            catalog=QUALITY_CATALOG,
            out_of_scope=QUALITY_OUT_OF_SCOPE,
            views=QUALITY_VIEWS,
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    def test_web_quality_security_baseline_is_satisfied(self):
        result = check_catalog_completeness(
            "web-quality-security-baseline",
            catalog=QUALITY_CATALOG,
            out_of_scope=QUALITY_OUT_OF_SCOPE,
            views=QUALITY_VIEWS,
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    def test_missing_out_of_scope_entry_is_a_violation(self):
        thin_out_of_scope = tuple(
            e for e in QUALITY_OUT_OF_SCOPE if e.id != "PERF-COMPRESS-001"
        )
        result = check_catalog_completeness(
            "web-performance-baseline",
            catalog=QUALITY_CATALOG,
            out_of_scope=thin_out_of_scope,
            views=QUALITY_VIEWS,
        )
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "THREAT001"
        assert violations[0].cwe == "PERF-COMPRESS-001"

    # frob:tests src/frob/strata/_threat.py::CWE_CATALOG kind="unit"
    def test_quality_catalog_never_leaks_into_owasp_top_10_view(self):
        quality_ids = {e.id for e in QUALITY_CATALOG}
        assert quality_ids.isdisjoint(VIEWS["owasp-top-10"])
        assert quality_ids.isdisjoint({e.id for e in CWE_CATALOG})

    # frob:tests src/frob/strata/_threat.py::CWE_CATALOG kind="unit"
    def test_dynamic_orm_scope_reuses_the_sql_capability_join(self):
        entry = next(e for e in QUALITY_CATALOG if e.id == "CWE-639")
        cwe_89 = next(e for e in CWE_CATALOG if e.id == "CWE-89")
        assert entry.capability_kind == cwe_89.capability_kind == "sql"
        assert entry.mitigation != cwe_89.mitigation

    # frob:tests src/frob/strata/_threat.py::CWE_CATALOG kind="unit"
    def test_no_kind_field_asserted_out_of_scope_entries_have_reasons(self):
        assert len(QUALITY_OUT_OF_SCOPE) == 5
        for entry in QUALITY_OUT_OF_SCOPE:
            assert entry.reason


# frob:ticket T-0143
class TestCweTop25:
    """T-0143 (docs/strata/threat.md#the-catalog-stdcwe): the `cwe-top-25`
    view spans two catalog tuples (`CWE_CATALOG`'s 8 overlapping ids +
    `CWE_TOP_25_CATALOG`'s 1 genuinely new obligation) plus 16 honest
    `OutOfScopeEntry` rows -- these tests prove THREAT001 exhaustiveness
    over the combined catalog and spot-check three new entries' data."""

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    # frob:ticket T-0143
    def test_cwe_top_25_view_is_satisfied(self):
        result = check_catalog_completeness(
            "cwe-top-25",
            catalog=CWE_CATALOG + CWE_TOP_25_CATALOG,
            out_of_scope=CWE_TOP_25_OUT_OF_SCOPE,
            views=CWE_TOP_25_VIEWS,
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    # frob:ticket T-0143
    def test_cwe_top_25_view_has_25_members(self):
        assert len(CWE_TOP_25_VIEWS["cwe-top-25"]) == 25

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_OUT_OF_SCOPE kind="unit"
    # frob:ticket T-0143
    def test_cwe_top_25_view_not_merged_into_default_views(self):
        # T-0143: kept separate so `_audit.py::DEFAULT_SECURITY_VIEWS`
        # (tuple(VIEWS)) never auto-scans it against the bare CWE_CATALOG
        # default -- the same rationale QUALITY_VIEWS follows.
        assert "cwe-top-25" not in VIEWS
        assert "cwe-top-25" in CWE_TOP_25_VIEWS

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_OUT_OF_SCOPE kind="unit"
    # frob:ticket T-0143
    def test_missing_out_of_scope_entry_is_a_violation(self):
        thin = tuple(e for e in CWE_TOP_25_OUT_OF_SCOPE if e.id != "CWE-787")
        result = check_catalog_completeness(
            "cwe-top-25",
            catalog=CWE_CATALOG + CWE_TOP_25_CATALOG,
            out_of_scope=thin,
            views=CWE_TOP_25_VIEWS,
        )
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "THREAT001"
        assert violations[0].cwe == "CWE-787"

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_CATALOG kind="unit"
    # frob:ticket T-0143
    def test_cwe_top_25_catalog_never_leaks_into_owasp_top_10_view(self):
        top25_only_ids = {e.id for e in CWE_TOP_25_CATALOG}
        assert top25_only_ids.isdisjoint(VIEWS["owasp-top-10"])

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_OUT_OF_SCOPE kind="unit"
    # frob:ticket T-0143
    def test_out_of_scope_entries_have_specific_nonempty_reasons(self):
        assert len(CWE_TOP_25_OUT_OF_SCOPE) == 16
        for entry in CWE_TOP_25_OUT_OF_SCOPE:
            assert entry.reason
            assert len(entry.reason) > 20  # a specific reason, not a stub

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_CATALOG kind="unit"
    # frob:ticket T-0143
    def test_cwe_94_reuses_the_exec_capability_join(self):
        entry = next(e for e in CWE_TOP_25_CATALOG if e.id == "CWE-94")
        cwe_78 = next(e for e in CWE_CATALOG if e.id == "CWE-78")
        assert entry.title == (
            "Improper Control of Generation of Code ('Code Injection')"
        )
        assert entry.cite == "https://cwe.mitre.org/data/definitions/94.html"
        assert entry.capability_kind == cwe_78.capability_kind == "exec"
        # a distinct mitigation from CWE-78's -- not a title restatement
        assert entry.mitigation == "code_execution_sandboxing"
        assert entry.mitigation != cwe_78.mitigation

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_OUT_OF_SCOPE kind="unit"
    # frob:ticket T-0143
    def test_memory_safety_entries_name_the_missing_kernel_concept(self):
        by_id = {e.id: e for e in CWE_TOP_25_OUT_OF_SCOPE}
        assert (
            "buffer" in by_id["CWE-787"].reason or "bounds" in by_id["CWE-787"].reason
        )
        assert (
            "allocator" in by_id["CWE-416"].reason
            or "lifetime" in by_id["CWE-416"].reason
        )

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_OUT_OF_SCOPE kind="unit"
    # frob:ticket T-0143
    def test_cwe_77_discloses_duplicate_coverage_of_cwe_78(self):
        entry = next(e for e in CWE_TOP_25_OUT_OF_SCOPE if e.id == "CWE-77")
        assert "CWE-78" in entry.reason

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0143
    def test_cwe_94_fires_and_discharges_on_exec_capability(self):
        node = Node(id="Sandbox", trust="trusted", may=("exec",))
        claim_id = _discharge_claim_id("CWE-94", "Sandbox")
        model = KernelModel(
            nodes=(node,),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="foreign", dst="Sandbox"),
                    required_rung=Rung.L4,
                ),
            ),
        )
        result = check_discharge_completeness(
            model, catalog=CWE_CATALOG + CWE_TOP_25_CATALOG
        )
        assert result.is_ok
        cwes = {v.cwe for v in result.danger_ok}
        # CWE-78 also fires on the same "exec" capability and has no claim
        # here -- CWE-94 must be absent from the violations (discharged),
        # proving its OWN fired-obligation join works independently.
        assert "CWE-94" not in cwes
        assert "CWE-78" in cwes

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0143
    def test_cwe_94_fires_and_is_undischarged_with_no_claim(self):
        node = Node(id="Sandbox", trust="trusted", may=("exec",))
        result = check_discharge_completeness(
            model=KernelModel(nodes=(node,)), catalog=CWE_CATALOG + CWE_TOP_25_CATALOG
        )
        assert result.is_ok
        violations = {v.cwe: v for v in result.danger_ok}
        assert "CWE-94" in violations
        assert violations["CWE-94"].node == "Sandbox"
        assert violations["CWE-94"].rule == "THREAT003"


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

    # frob:tests src/frob/strata/_threat.py::evaluate_threats kind="unit"
    def test_pre_discharge_count_log_is_honest_and_debug_level(self, caplog):
        # T-0217: the pre-discharge count logged here is NOT a live-violation
        # count -- callers (e.g. `frob sys plan`'s obligation-ticket compiler)
        # only turn a subset (THREAT003) into obligations, so a raw
        # "-> N violation(s)" line printed right before a "0 obligation
        # ticket(s)" / PROVED summary read as contradictory even when
        # nothing was wrong. The log must (a) not use the misleading
        # "violation(s)" wording and (b) log at DEBUG, not INFO, so a
        # caller narrowing stdout to INFO/WARNING (as `frob check`'s `-v`
        # dial does, T-0202) does not surface it by default.
        node = Node(id="Web", trust="trusted", may=("html_render",))
        thin_catalog = tuple(e for e in CWE_CATALOG if e.id != "CWE-89")
        model = KernelModel(nodes=(node,))
        with caplog.at_level("DEBUG", logger="frob.strata._threat"):
            report = evaluate_threats(model, "owasp-top-10", catalog=thin_catalog)
        assert report.is_ok
        assert report.danger_ok.violations != ()
        threat_records = [
            r for r in caplog.records if r.message.startswith("threat: obligations")
        ]
        assert len(threat_records) == 1
        record = threat_records[0]
        assert record.levelname == "DEBUG"
        assert "violation(s)" not in record.message
        assert "pre-discharge obligation(s)" in record.message


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
