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
from frob.strata._errors import StrataError
from frob.strata._threat import (
    ALL_CATALOG,
    CWE_CATALOG,
    CWE_TOP_25_CATALOG,
    CWE_TOP_25_OUT_OF_SCOPE,
    CWE_TOP_25_VIEWS,
    QUALITY_CATALOG,
    QUALITY_OUT_OF_SCOPE,
    QUALITY_VIEWS,
    VIEWS,
    _caught_by_unresolved_tokens,
    _check_caught_by_integrity,
    _discharge_claim_id,
    load_repo_benign_capabilities,
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
            out_of_scope=(
                OutOfScopeEntry(
                    id="CWE-79", reason="no html_render yet", caught_by="test fixture"
                ),
            ),
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


class TestCwe611Xxe:
    """T-0189 (T-0153 review follow-up): CWE-611 (XXE) added to
    `CWE_CATALOG` so the XML external-entity fingerprint can join it
    (docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-
    t-0153)."""

    # frob:tests src/frob/strata/_threat.py::CWE_CATALOG kind="unit"
    def test_cwe_611_entry_exists_in_the_catalog(self):
        entry = next((e for e in CWE_CATALOG if e.id == "CWE-611"), None)
        assert entry is not None
        assert entry.cite == "https://cwe.mitre.org/data/definitions/611.html"
        assert entry.capability_kind is None
        assert entry.mitigation == "external_entity_disabled"

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    def test_cwe_611_is_reachable_via_the_owasp_top_10_view(self):
        # CWE-611 is not an OWASP Top-10 baseline id itself, but the view
        # is derived directly from CWE_CATALOG's ids (VIEWS module
        # docstring) so adding it here still keeps THREAT001 clean.
        result = check_catalog_completeness("owasp-top-10")
        assert result.is_ok
        assert result.danger_ok == ()
        assert "CWE-611" in VIEWS["owasp-top-10"]

    # frob:tests src/frob/strata/_threat.py::check_capability_completeness kind="unit"
    def test_cwe_611_never_fires_capability_kind_is_none(self):
        # Mirrors the CWE-22/352/798 "three catalog ids can never fire"
        # design finding (docs/strata/threat.md) -- capability_kind=None
        # means no `may` atom kind ever drags this obligation in via
        # `_fired_obligations`/`_entries_by_capability_kind`.
        entry = next(e for e in CWE_CATALOG if e.id == "CWE-611")
        assert entry.capability_kind is None


class TestQualityFamilies:
    """Phase E (T-0114, docs/strata/threat.md#phasing item E): the
    performance/reliability/compat anti-pattern families reuse THREAT001's
    machinery unmodified over `QUALITY_CATALOG`/`QUALITY_OUT_OF_SCOPE` and
    a family-scoped view -- these tests prove the SAME `check_catalog_
    completeness` entrypoint is exhaustive per family, and that the quality
    catalog never leaks into the `owasp-top-10` view it is kept separate
    from."""

    # frob:tests src/frob/strata/_threat.py::check_catalog_completeness kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_threat.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
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
    # frob:waive DUP001 reason="parallel test methods within test_threat.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
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
    # frob:waive DUP001 reason="parallel test methods within test_threat.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
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

    # frob:tests src/frob/strata/_threat.py::QUALITY_CATALOG kind="unit"
    def test_cwe_295_is_cataloged_with_no_capability_kind_or_view(self):
        # T-0188: TLS verify=False's WeaknessEntry -- honest views
        # placement means it belongs to neither owasp-top-10 nor
        # cwe-top-25 (docs/strata/threat.md#cve-fingerprints-code-level-
        # pattern-catalog-t-0153) and is fired only via the std.cve
        # fingerprint layer, never a `may`-capability auto-instantiation.
        entry = next(e for e in QUALITY_CATALOG if e.id == "CWE-295")
        assert entry.title == "Improper Certificate Validation"
        assert entry.family == "security"
        assert entry.capability_kind is None
        assert entry.id not in VIEWS["owasp-top-10"]
        assert entry.id not in {e.id for e in CWE_CATALOG}
        assert entry.id not in CWE_TOP_25_VIEWS["cwe-top-25"]
        assert all(entry.id not in members for members in QUALITY_VIEWS.values())

    # frob:tests src/frob/strata/_threat.py::CWE_CATALOG kind="unit"
    def test_no_kind_field_asserted_out_of_scope_entries_have_reasons(self):
        assert len(QUALITY_OUT_OF_SCOPE) == 5
        for entry in QUALITY_OUT_OF_SCOPE:
            assert entry.reason

    # frob:ticket T-0510
    # frob:tests src/frob/strata/_threat.py::QUALITY_CATALOG kind="unit"
    @pytest.mark.parametrize(
        "cwe_id",
        ["CWE-916", "CWE-1321", "CWE-1333", "CWE-601", "CWE-1336"],
    )
    def test_t0510_entries_are_cataloged_with_no_capability_kind_or_view(
        self, cwe_id: str
    ):
        # T-0510: the five previously-disclosed-gap CWEs (weak-hash,
        # prototype pollution, ReDoS, open redirect, SSTI) follow CWE-295's
        # exact precedent immediately above -- catalog-only entries,
        # discharged solely by the `std.cve` fingerprint layer, no `may`
        # capability join and no default-view membership.
        entry = next(e for e in QUALITY_CATALOG if e.id == cwe_id)
        assert entry.family == "security"
        assert entry.capability_kind is None
        assert entry.id not in VIEWS["owasp-top-10"]
        assert entry.id not in {e.id for e in CWE_CATALOG}
        assert entry.id not in CWE_TOP_25_VIEWS["cwe-top-25"]
        assert all(entry.id not in members for members in QUALITY_VIEWS.values())


# frob:ticket T-0143
# frob:ticket T-0345
class TestCweTop25:
    """T-0143 (docs/strata/threat.md#the-catalog-stdcwe), bumped to the
    2025 release by T-0345: the `cwe-top-25` view spans two catalog tuples
    (`CWE_CATALOG`'s 7 overlapping ids + `CWE_TOP_25_CATALOG`'s 2
    genuinely new obligations: CWE-94/639) plus 16 honest
    `OutOfScopeEntry` rows -- these tests prove THREAT001 exhaustiveness
    over the combined catalog and spot-check the new entries' data."""

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
    # frob:ticket T-0345
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
    # frob:ticket T-0345
    def test_buffer_overflow_trio_name_the_same_missing_bounds_model(self):
        # T-0345: CWE-120/121/122 are 2025-list-new; each names the SAME
        # buffer/bounds gap CWE-787/125 already disclose, never a generic
        # "not supported".
        by_id = {e.id: e for e in CWE_TOP_25_OUT_OF_SCOPE}
        for cwe_id in ("CWE-120", "CWE-121", "CWE-122"):
            assert "buffer" in by_id[cwe_id].reason
            assert len(by_id[cwe_id].reason) > 20

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_OUT_OF_SCOPE kind="unit"
    # frob:ticket T-0345
    def test_cwe_284_discloses_generic_parent_of_862_863(self):
        entry = next(e for e in CWE_TOP_25_OUT_OF_SCOPE if e.id == "CWE-284")
        assert "CWE-862" in entry.reason or "CWE-863" in entry.reason

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_OUT_OF_SCOPE kind="unit"
    # frob:ticket T-0345
    def test_cwe_770_names_the_missing_resource_budget_concept(self):
        entry = next(e for e in CWE_TOP_25_OUT_OF_SCOPE if e.id == "CWE-770")
        assert "resource" in entry.reason or "rate-limit" in entry.reason

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_OUT_OF_SCOPE kind="unit"
    # frob:ticket T-0345
    def test_cwe_200_matches_the_weaknesses_registrys_own_disposition(self):
        # T-0345: 2025-list-new; docs/design/registry/weaknesses.yaml's
        # independent CWE-1000 disposition sweep already classified this
        # id `out-of-scope:authn-authz-boundary-predicate` -- this catalog
        # follows that judgment rather than re-deciding it (never a
        # `capability_kind=None` WeaknessEntry, which would contradict it).
        entry = next(e for e in CWE_TOP_25_OUT_OF_SCOPE if e.id == "CWE-200")
        assert "authz" in entry.reason or "authn" in entry.reason
        assert entry.id not in {e.id for e in CWE_TOP_25_CATALOG}

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_OUT_OF_SCOPE kind="unit"
    # frob:ticket T-0143
    def test_cwe_77_discloses_duplicate_coverage_of_cwe_78(self):
        entry = next(e for e in CWE_TOP_25_OUT_OF_SCOPE if e.id == "CWE-77")
        assert "CWE-78" in entry.reason

    # frob:tests src/frob/strata/_threat.py::CWE_TOP_25_CATALOG kind="unit"
    # frob:ticket T-0345
    def test_cwe_639_reuses_the_sql_capability_join(self):
        # T-0345: 2025-list-new; reuses QUALITY_CATALOG's existing CWE-639
        # entry's sql join rather than duplicating it (disclosed reuse, the
        # SAME convention CWE-94 follows for exec).
        entry = next(e for e in CWE_TOP_25_CATALOG if e.id == "CWE-639")
        quality_entry = next(e for e in QUALITY_CATALOG if e.id == "CWE-639")
        assert entry.capability_kind == quality_entry.capability_kind == "sql"
        assert entry.mitigation == "tenant_scoping"

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
    # frob:waive DUP001 reason="parallel test methods within test_threat.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
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


# frob:ticket T-0501
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
    # frob:waive DUP001 reason="parallel test methods within test_threat.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
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
    # frob:ticket T-0501
    def test_noflow_from_a_specific_foreign_trust_node_discharges(self):
        """`_discharges_as_chokepoint` accepts a `NoFlow` naming a
        specific foreign-trust node directly (not just the `"foreign"`
        trust level) as the correct SHAPE. T-0501: the flow from `Evil`
        to `Web` and its matching mitigation boundary must both be
        modeled for the OVERALL discharge to pass now -- before this
        ticket, this test passed with NEITHER a flow NOR a boundary
        declared at all, i.e. it was itself an undetected G2 vacuous
        discharge (confirmed: dropping the `flows`/`boundaries` below
        reproduces the pre-fix `THREAT003 ... proves NoFlow vacuously`
        finding this ticket now raises)."""
        node = Node(id="Web", trust="trusted", may=("html_render",))
        evil = Node(id="Evil", trust="foreign")
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(node, evil),
            flows=(Flow(id="f1", src="Evil", dst="Web"),),
            boundaries=(
                Boundary(
                    id="b1",
                    flow_id="f1",
                    direction=BoundaryDirection.ENDORSE,
                    from_level="foreign",
                    to_level="trusted",
                    predicate="output_encoding",
                    obligations=(claim_id,),
                ),
            ),
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
    # frob:waive DUP001 reason="parallel test methods within test_threat.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
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
                    obligations=(claim_id,),
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
    def test_endorse_boundary_with_no_evidence_ref_does_not_discharge_g1(self):
        """docs/audits/strata.md G1: before the fix, an `ENDORSE` boundary
        whose bare `predicate` string happened to equal the catalog's
        required mitigation name discharged THREAT003 with ZERO evidence
        that the mitigation was real -- `obligations=()` and no code/claim
        binding at all. This is the counterexample the audit finding
        names, confirmed to discharge vacuously before this ticket's fix
        (`_matching_boundary_ids` now also requires `obligations` to
        resolve to a real claim); it must be REFUSED after the fix."""
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
                    # No `obligations` -- the vacuous G1 case.
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
    def test_endorse_boundary_with_dangling_obligation_does_not_discharge_g1(self):
        """G1's other half: `obligations` naming a claim id that does NOT
        exist in the model must not be trusted either -- an evidence ref
        has to resolve to something real, not merely be present."""
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
                    obligations=("claim-does-not-exist",),
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
    # frob:waive DUP001 reason="parallel test methods within test_threat.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
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


# frob:ticket T-0595
class TestCodeBoundMitigationPredicate:
    """docs/audits/strata.md G1 stronger half (T-0595): an ENDORSE boundary
    whose predicate resolves to a real claim (T-0498's weaker half) is
    STILL, on its own, an unverified model-side string -- it must also
    name an OBSERVED sanitizer/validator call site in the guarded flow's
    destination node's own `code=`-bound files. Every case here passes a
    real `binding`/`root` (a `tmp_path` file tree via `bind_code`); the
    no-binding cases already covered by `TestMitigationKindChokepoint`
    (binding=None) must keep discharging exactly as before -- this class
    only exercises the NEW code-tree-supplied path."""

    # frob:ticket T-0595
    def _model(self, claim_id: str) -> KernelModel:
        """The shared Evil->Web/ENDORSE-boundary/CWE-79 fixture every case
        in this class reuses, varying only the code tree written under
        `tmp_path` (arrange-act scaffold shared with
        `TestMitigationKindChokepoint`, same claim shape)."""
        evil = Node(id="Evil", trust="foreign")
        web = Node(
            id="Web", trust="trusted", may=("html_render",), attrs=("code=api/**",)
        )
        return KernelModel(
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
                    obligations=(claim_id,),
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

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0595
    def test_no_observed_call_site_fails_closed_naming_the_boundary(
        self, tmp_path: Path
    ):
        """The ticket's acceptance repro: `output_encoding` is never
        CALLED anywhere in Web's bound code (only mentioned as a
        docstring word, so a naive substring scan would be fooled but a
        real AST call-site join is not) -- discharge must fail closed and
        the violation must name the unbound boundary id."""
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = self._model(claim_id)
        _write(
            tmp_path,
            "api/handler.py",
            '"""Uses output_encoding somewhere in a comment, never calls it."""\n'
            "def render(x):\n"
            "    return x\n",
        )
        binding = bind_code(model, tmp_path).danger_ok
        result = check_discharge_completeness(model, binding=binding, root=tmp_path)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "THREAT003"
        assert "b1" in violations[0].detail
        assert "no OBSERVED sanitizer" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0595
    def test_observed_call_site_discharges(self, tmp_path: Path):
        """The positive case: `output_encoding(...)` really is CALLED in
        Web's own bound code -- discharge succeeds."""
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = self._model(claim_id)
        _write(
            tmp_path,
            "api/handler.py",
            "def render(x):\n    return output_encoding(x)\n",
        )
        binding = bind_code(model, tmp_path).danger_ok
        result = check_discharge_completeness(model, binding=binding, root=tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0595
    def test_call_site_via_attribute_access_also_discharges(self, tmp_path: Path):
        """A method/module-qualified call (`html.output_encoding(x)`) is
        also an observed call site -- `_call_target_name` resolves
        `Attribute.attr`, not just a bare `Name`."""
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = self._model(claim_id)
        _write(
            tmp_path,
            "api/handler.py",
            "import html\ndef render(x):\n    return html.output_encoding(x)\n",
        )
        binding = bind_code(model, tmp_path).danger_ok
        result = check_discharge_completeness(model, binding=binding, root=tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0595
    def test_call_site_in_a_different_nodes_code_does_not_count(self, tmp_path: Path):
        """`output_encoding` called only in a file owned by a DIFFERENT
        node (not Web, the flow's destination) must not count -- the
        join is scoped to the guarded destination node's own bound code,
        not the whole repo."""
        evil = Node(id="Evil", trust="foreign", attrs=("code=other/**",))
        web = Node(
            id="Web", trust="trusted", may=("html_render",), attrs=("code=api/**",)
        )
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
                    obligations=(claim_id,),
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
        _write(
            tmp_path, "other/attacker.py", "def f(x):\n    return output_encoding(x)\n"
        )
        _write(tmp_path, "api/handler.py", "def render(x):\n    return x\n")
        binding = bind_code(model, tmp_path).danger_ok
        result = check_discharge_completeness(model, binding=binding, root=tmp_path)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert "b1" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0595
    def test_absent_binding_keeps_the_old_weaker_half_behavior(self, tmp_path: Path):
        """Backward compatibility: a caller with no code tree at all
        (`binding`/`root` both None/omitted, e.g. every pre-T-0595 caller)
        must keep discharging on T-0498's weaker half alone -- this is
        `TestMitigationKindChokepoint.
        test_endorse_boundary_with_matching_predicate_discharges`'s exact
        model, confirmed unaffected by this ticket's change."""
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = self._model(claim_id)
        result = check_discharge_completeness(model)
        assert result.is_ok
        assert result.danger_ok == ()


# frob:ticket T-0501
class TestFlowCompletenessGap:
    """T-0501 (docs/audits/strata.md G2): a `NoFlow(src="foreign", ...)`
    claim used to discharge THREAT003 vacuously the moment the closure
    found no path to the sink -- regardless of WHY there was no path.
    This left an incomplete/attacker-authored `.strata` that declares a
    real adversary elsewhere in the model, but simply never wires a flow
    into the node firing the obligation, "PROVED" with zero mitigation
    modeled. These fixtures confirm that shape now fails closed with a
    distinct finding naming the incompleteness, while the genuinely
    foreign-less T-0223 library-mode discharge (no `trust foreign` node
    ANYWHERE in the model, `TestLibraryModeForeignlessDischarge` above)
    and a model with no flows/boundaries declared at all keep discharging
    exactly as before -- neither of those is the flagged gap."""

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0501
    def test_foreign_node_present_but_no_flow_to_sink_fails_closed(self):
        """Confirmed vacuous discharge BEFORE this ticket's fix: `Evil` is
        a real foreign-trust node in the model (an adversary IS modeled),
        `Web` fires CWE-79 via `html_render`, but no `Flow` connects them
        at all -- `Web`'s inbound path from untrusted input was simply
        never modeled. The un-restricted closure already has no path
        (nothing links Evil to Web), so `NoFlow` proved vacuously and
        THREAT003 discharged with NO mitigation modeled -- the exact G2
        repro from docs/audits/strata.md."""
        evil = Node(id="Evil", trust="foreign")
        web = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(evil, web),
            # No `flows` at all -- Web's real inbound data path is
            # un-modeled, not merely un-mitigated.
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
        assert "vacuously" in violations[0].detail
        assert "un-modeled" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0501
    def test_foreign_node_present_and_connected_elsewhere_still_fails_closed(self):
        """The foreign node need not be totally disconnected from the
        model -- it only has to be disconnected from THIS sink. `Evil`
        reaches an unrelated node `Other`, never `Web`; `Web` still fires
        CWE-79 with no adversary wired to it at all."""
        evil = Node(id="Evil", trust="foreign")
        other = Node(id="Other", trust="trusted")
        web = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(evil, other, web),
            flows=(Flow(id="f1", src="Evil", dst="Other"),),
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
        assert "vacuously" in violations[0].detail
        assert "un-modeled" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0501
    def test_no_foreign_node_anywhere_still_discharges_by_absence(self):
        """Regression guard for T-0223: a model with ZERO `trust foreign`
        nodes anywhere is the documented library-mode case, not the G2
        gap -- it must keep discharging by absence exactly as before this
        ticket (see also `TestLibraryModeForeignlessDischarge`, which
        proves the same thing through the real parser)."""
        web = Node(id="Web", trust="trusted", may=("html_render",))
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = KernelModel(
            nodes=(web,),
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


def _load_litmus_model(filename: str) -> KernelModel:
    """Parse+elaborate one `.strata` fixture under `litmus/` end to end
    (test_managed.py's `_load_model` precedent -- real `strata_core`
    parser, never a hand-built `KernelModel`, for the library-mode-
    discharge litmus pair below)."""
    from frob.strata import elaborate, parse_module

    text = (Path(__file__).resolve().parent / "litmus" / filename).read_text(
        encoding="utf-8"
    )
    module = parse_module(text)
    assert module.is_ok, module.danger_err
    elaborated = elaborate(module.danger_ok)
    assert elaborated.is_ok, elaborated.danger_err
    return elaborated.danger_ok


class TestLibraryModeForeignlessDischarge:
    """T-0223 (docs/strata/threat.md#library-mode-discharge-by-absence): a
    foreign-less library model can discharge a CWE-78 `exec` obligation by
    naming the `foreign` TRUST LEVEL directly in a `NoFlow(src="foreign",
    dst=<node>)` claim -- with no foreign-trust node in the model,
    `_claims.py::_expand` resolves `"foreign"` to the empty node set, so
    the claim's witness search is vacuously empty and the `NoFlow` is
    PROVED by absence, not by a modeled chokepoint. The SAME claim shape
    still fires (REFUTED) the moment a real foreign source reaches the
    sink with no boundary -- no weakening for a model with a genuine
    injection path (library_exec_foreign_reaches_still_fires.strata)."""

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0223
    def test_foreign_less_library_model_discharges_cwe_78_by_absence(self):
        model = _load_litmus_model("library_exec_no_foreign_discharges.strata")
        result = check_discharge_completeness(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0223
    def test_real_foreign_source_reaching_the_sink_still_fires(self):
        model = _load_litmus_model("library_exec_foreign_reaches_still_fires.strata")
        result = check_discharge_completeness(model)
        assert result.is_ok
        violations = {(v.cwe, v.node): v for v in result.danger_ok}
        assert ("CWE-78", "runner") in violations
        assert violations[("CWE-78", "runner")].rule == "THREAT003"
        assert "REFUTED" in violations[("CWE-78", "runner")].detail


class TestBenignCapability:
    # frob:tests src/frob/strata/_threat.py::BenignCapability kind="unit"
    def test_empty_reason_is_rejected(self):
        with pytest.raises(ValidationError):
            BenignCapability(kind="metrics", reason="", caught_by="test fixture")

    # frob:tests src/frob/strata/_threat.py::BenignCapability kind="unit"
    def test_empty_caught_by_is_rejected(self):
        with pytest.raises(ValidationError):
            BenignCapability(kind="metrics", reason="no CWE weakness", caught_by="")

    # frob:tests src/frob/strata/_threat.py::BenignCapability kind="unit"
    def test_missing_caught_by_is_rejected(self):
        with pytest.raises(ValidationError):
            # intentionally omit required caught_by to verify runtime rejection
            BenignCapability(kind="metrics", reason="no CWE weakness")  # ty: ignore[missing-argument]


class TestLoadRepoBenignCapabilities:
    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    def test_missing_frob_toml_is_ok_empty(self, tmp_path: Path):
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    def test_missing_strata_table_is_ok_empty(self, tmp_path: Path):
        _write(tmp_path, "frob.toml", '[graph]\nexclude = ["build/**"]\n')
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    def test_declared_entry_is_loaded(self, tmp_path: Path):
        # html_render has no QUALITY_CATALOG sink entry (only CWE_CATALOG's
        # CWE-79) -- a legitimate quality-family excuse, same shape as the
        # T-0017 client_storage case below.
        _write(
            tmp_path,
            "frob.toml",
            "[[strata.benign_capabilities]]\n"
            'kind = "html_render"\n'
            'reason = "browser node renders trusted static assets only"\n'
            'caught_by = "content-security-policy review, out of frob scope"\n'
            'family = "quality"\n',
        )
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_ok
        excuses = result.danger_ok
        assert len(excuses) == 1
        assert excuses[0] == BenignCapability(
            kind="html_render",
            reason="browser node renders trusted static assets only",
            caught_by="content-security-policy review, out of frob scope",
            family="quality",
        )

    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_threat.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_missing_reason_is_malformed(self, tmp_path: Path):
        _write(
            tmp_path,
            "frob.toml",
            '[[strata.benign_capabilities]]\nkind = "html_render"\n'
            'caught_by = "test fixture"\nfamily = "quality"\n',
        )
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.MalformedBenignConfig

    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_threat.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_blank_reason_is_malformed(self, tmp_path: Path):
        _write(
            tmp_path,
            "frob.toml",
            '[[strata.benign_capabilities]]\nkind = "html_render"\nreason = ""\n'
            'caught_by = "test fixture"\nfamily = "quality"\n',
        )
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.MalformedBenignConfig

    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    # frob:waive DUP001 reason="parallel test methods within test_threat.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case coverage; \
    # extracting would obscure per-case intent"
    def test_missing_caught_by_is_malformed(self, tmp_path: Path):
        _write(
            tmp_path,
            "frob.toml",
            '[[strata.benign_capabilities]]\nkind = "html_render"\n'
            'reason = "browser node renders trusted static assets only"\n'
            'family = "quality"\n',
        )
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.MalformedBenignConfig

    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    def test_unparseable_toml_is_malformed(self, tmp_path: Path):
        _write(tmp_path, "frob.toml", "not valid toml [[[")
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.MalformedBenignConfig

    # frob:ticket T-0511
    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    def test_missing_family_is_malformed(self, tmp_path: Path):
        # T-0511 (strata audit G12): family is now mandatory -- an excuse
        # with no declared family cannot be verified against a specific
        # catalog and is refused, not silently treated as "applies
        # everywhere" (the exact unscoped-blanket-excuse shape G12 flags).
        _write(
            tmp_path,
            "frob.toml",
            '[[strata.benign_capabilities]]\nkind = "html_render"\n'
            'reason = "browser node renders trusted static assets only"\n'
            'caught_by = "test fixture"\n',
        )
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.MalformedBenignConfig

    # frob:ticket T-0511
    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    def test_unrecognized_family_value_is_malformed(self, tmp_path: Path):
        _write(
            tmp_path,
            "frob.toml",
            '[[strata.benign_capabilities]]\nkind = "html_render"\n'
            'reason = "browser node renders trusted static assets only"\n'
            'caught_by = "test fixture"\nfamily = "reliability"\n',
        )
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.MalformedBenignConfig

    # frob:ticket T-0511
    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    def test_excuse_already_classified_in_named_security_family_is_rejected(
        self, tmp_path: Path
    ):
        # Counterexample #2 (T-0511): "sql" IS classified in CWE_CATALOG
        # (CWE-89) -- an excuse claiming family="security" for it is not a
        # genuine gap; it must be rejected, not silently accepted as a
        # harmless no-op.
        _write(
            tmp_path,
            "frob.toml",
            '[[strata.benign_capabilities]]\nkind = "sql"\n'
            'reason = "bogus -- sql IS already classified security-side"\n'
            'caught_by = "test fixture"\nfamily = "security"\n',
        )
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.MalformedBenignConfig

    # frob:ticket T-0511
    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    def test_excuse_already_classified_in_named_quality_family_is_rejected(
        self, tmp_path: Path
    ):
        # Counterexample #2, quality-family variant: "sql" is ALSO
        # classified in QUALITY_CATALOG itself (CWE-639 reuses the same
        # sql join) -- family="quality" must be rejected too, not just
        # family="security".
        _write(
            tmp_path,
            "frob.toml",
            '[[strata.benign_capabilities]]\nkind = "sql"\n'
            'reason = "bogus -- sql IS already classified quality-side too"\n'
            'caught_by = "test fixture"\nfamily = "quality"\n',
        )
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.MalformedBenignConfig

    # frob:ticket T-0511
    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    def test_client_storage_excused_for_quality_only_stays_accepted(
        self, tmp_path: Path
    ):
        # Regression guard (T-0511): the exact T-0017 legitimate case must
        # still work after the family-scoping fix -- client_storage IS
        # classified under CWE_CATALOG (CWE-922/312, security) but has NO
        # QUALITY_CATALOG entry, so family="quality" is a real, accepted
        # excuse.
        _write(
            tmp_path,
            "frob.toml",
            '[[strata.benign_capabilities]]\nkind = "client_storage"\n'
            'reason = "no QUALITY_CATALOG sink for this repo\'s usage"\n'
            'caught_by = "already CWE-922/312 classified in the security '
            'family"\nfamily = "quality"\n',
        )
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_ok
        excuses = result.danger_ok
        assert len(excuses) == 1
        assert excuses[0].family == "quality"

    # frob:ticket T-0511
    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    def test_client_storage_excused_for_security_family_is_rejected(
        self, tmp_path: Path
    ):
        # The other half of counterexample #2: the SAME kind
        # (client_storage) that is legitimately excusable for "quality" is
        # illegitimate for "security" -- it IS classified there
        # (CWE-922/312), so claiming family="security" must be rejected.
        _write(
            tmp_path,
            "frob.toml",
            '[[strata.benign_capabilities]]\nkind = "client_storage"\n'
            'reason = "bogus -- client_storage IS classified security-side"\n'
            'caught_by = "test fixture"\nfamily = "security"\n',
        )
        result = load_repo_benign_capabilities(tmp_path)
        assert result.is_err
        assert result.danger_err == StrataError.MalformedBenignConfig

    # frob:tests src/frob/strata/_threat.py::load_repo_benign_capabilities kind="unit"
    def test_repo_declared_excuse_resolves_threat002(self, tmp_path: Path):
        # End-to-end reproduction of the graphite T-0017 gap: `client_
        # storage` IS classified under CWE_CATALOG (CWE-922/312) but has NO
        # QUALITY_CATALOG sink entry -- THREAT002 under a quality view
        # would flag it with no way to excuse it except patching frob's own
        # DEFAULT_BENIGN_CAPABILITIES. A repo-declared entry resolves it
        # without touching frob's source, same merge shape
        # sys_runner._evaluate_audit wires (DEFAULT_BENIGN_CAPABILITIES +
        # load_repo_benign_capabilities).
        _write(
            tmp_path,
            "frob.toml",
            "[[strata.benign_capabilities]]\n"
            'kind = "client_storage"\n'
            'reason = "no QUALITY_CATALOG sink for this repo\'s usage"\n'
            'caught_by = "already CWE-922/312 classified in the security family"\n'
            'family = "quality"\n',
        )
        loaded = load_repo_benign_capabilities(tmp_path)
        assert loaded.is_ok
        node = Node(id="Browser", trust="trusted", may=("client_storage",))
        result = check_capability_completeness(
            KernelModel(nodes=(node,)),
            catalog=QUALITY_CATALOG,
            benign=loaded.danger_ok,
        )
        assert result.is_ok
        assert result.danger_ok == ()


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
            benign=(
                BenignCapability(
                    kind="metrics", reason="no CWE weakness", caught_by="test fixture"
                ),
            ),
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

    # frob:tests src/frob/strata/_threat.py::check_capability_completeness kind="unit"
    def test_taxonomy_param_classifies_beyond_the_narrower_catalog(self):
        """T-0171: `exec` has NO `QUALITY_CATALOG` entry (only `CWE_CATALOG`'s
        CWE-78) -- checking against `catalog=QUALITY_CATALOG` alone (the
        pre-T-0171 shape) misclassifies it; passing `taxonomy=ALL_CATALOG`
        (the union across families) recognizes it as classified, matching
        `ALL_CATALOG`'s "one taxonomy, split per-family only for view-
        membership bookkeeping" contract."""
        node = Node(id="Worker", trust="trusted", may=("exec",))
        narrow = check_capability_completeness(
            KernelModel(nodes=(node,)), catalog=QUALITY_CATALOG
        )
        assert narrow.is_ok
        assert len(narrow.danger_ok) == 1
        assert narrow.danger_ok[0].capability == "exec"

        widened = check_capability_completeness(
            KernelModel(nodes=(node,)), catalog=QUALITY_CATALOG, taxonomy=ALL_CATALOG
        )
        assert widened.is_ok
        assert widened.danger_ok == ()


class TestEvalFiresCwe94:
    """T-0401 (docs/audits/strata.md G3): `eval` used to be globally
    `BenignCapability`-excused with the (false) reason "no CWE_CATALOG
    entry targets dynamic code evaluation" -- CWE-94 IS that entry, just
    never joined to the `eval` kind. Non-vacuous pair: BEFORE the fix an
    `eval` node fired no obligation at all (the vulnerable case, proven
    here via the empty `benign` default no longer excusing it); the
    hardened case is a real `weakness:CWE-94:<node>` discharge."""

    # frob:tests src/frob/strata/_threat.py::check_capability_completeness kind="unit"
    def test_eval_capability_is_classified_not_benign_excused(self):
        """Vulnerable-shape repro: a node declaring `may "eval"` with NO
        BenignCapability excuse must be CLASSIFIED (known to the taxonomy),
        proving `eval` now maps to a real catalog entry instead of silently
        passing THREAT002 the way the old global excuse made it."""
        node = Node(id="Worker", trust="trusted", may=("eval",))
        result = check_capability_completeness(
            KernelModel(nodes=(node,)), catalog=ALL_CATALOG, taxonomy=ALL_CATALOG
        )
        assert result.is_ok
        assert result.danger_ok == ()  # classified (CWE-94), not unclassified

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_eval_capability_fires_a_real_cwe94_obligation(self):
        """The obligation actually FIRES (THREAT003) with no discharge --
        this is the counterexample: an `eval`-declaring node with no
        mitigating claim must be refused (undischarged CWE-94), proving the
        capability is no longer a global no-op."""
        node = Node(id="Sandbox", trust="trusted", may=("eval",))
        model = KernelModel(nodes=(node,))
        result = check_discharge_completeness(model, catalog=CWE_TOP_25_CATALOG)
        assert result.is_ok
        violations = result.danger_ok
        assert any(v.rule == "THREAT003" and v.cwe == "CWE-94" for v in violations)

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    def test_eval_capability_discharges_with_a_real_mitigation_claim(self):
        """Hardened case: the identical node, but with a proven `NoFlow`
        mitigation claim named `weakness:CWE-94:<node>` -- discharges
        clean, mirroring `test_cwe_94_fires_and_discharges_on_exec_
        capability` above but for the `eval` join."""
        node = Node(id="Sandbox", trust="trusted", may=("eval",))
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
        result = check_discharge_completeness(model, catalog=CWE_TOP_25_CATALOG)
        assert result.is_ok
        assert not any(v.cwe == "CWE-94" for v in result.danger_ok)


class TestCaughtByUnresolvedTokens:
    """T-0382: `_caught_by_unresolved_tokens` -- the public per-entry
    resolution helper `_check_caught_by_integrity` (THREAT006) and
    `_compliance.py`'s `_check_regulation_caught_by_integrity`
    (COMPLIANCE004) both share, rather than duplicating the token
    regex/resolution rule."""

    # frob:tests src/frob/strata/_threat.py::_caught_by_unresolved_tokens kind="unit"
    def test_unknown_rule_id_is_unresolved(self):
        unresolved = _caught_by_unresolved_tokens(
            "already enforced by SEC999", known_rule_ids=frozenset({"SEC001"})
        )
        assert unresolved == frozenset({"SEC999"})

    # frob:tests src/frob/strata/_threat.py::_caught_by_unresolved_tokens kind="unit"
    def test_known_rule_id_resolves(self):
        unresolved = _caught_by_unresolved_tokens(
            "already enforced by SEC001", known_rule_ids=frozenset({"SEC001"})
        )
        assert unresolved == frozenset()

    # frob:tests src/frob/strata/_threat.py::_caught_by_unresolved_tokens kind="unit"
    def test_no_referenced_tokens_is_unresolved_empty(self):
        unresolved = _caught_by_unresolved_tokens("legal review, out of scope")
        assert unresolved == frozenset()


class TestCaughtByIntegrity:
    """T-0382: `_check_caught_by_integrity` (THREAT006) -- a `caught_by`
    naming a fabricated rule id or CWE id fails closed; an honest "none"
    or a real reference never does."""

    # frob:tests src/frob/strata/_threat.py::_check_caught_by_integrity kind="unit"
    def test_honest_none_caught_by_never_fails(self):
        entry = OutOfScopeEntry(
            id="CWE-999", reason="not applicable", caught_by="none -- no control"
        )
        result = _check_caught_by_integrity(out_of_scope=(entry,))
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::_check_caught_by_integrity kind="unit"
    def test_free_text_with_no_recognizable_token_passes(self):
        entry = OutOfScopeEntry(
            id="CWE-999",
            reason="handled elsewhere",
            caught_by="content-security-policy review, out of frob scope",
        )
        result = _check_caught_by_integrity(out_of_scope=(entry,))
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::_check_caught_by_integrity kind="unit"
    def test_real_cwe_reference_resolves(self):
        entry = OutOfScopeEntry(
            id="CWE-999",
            reason="already classified elsewhere",
            caught_by="already classified as CWE-78 in CWE_CATALOG",
        )
        result = _check_caught_by_integrity(out_of_scope=(entry,), catalog=CWE_CATALOG)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::_check_caught_by_integrity kind="unit"
    def test_fabricated_cwe_reference_fails_closed(self):
        entry = OutOfScopeEntry(
            id="CWE-999",
            reason="claims coverage elsewhere",
            caught_by="already classified as CWE-000000 in CWE_CATALOG",
        )
        result = _check_caught_by_integrity(out_of_scope=(entry,), catalog=CWE_CATALOG)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "THREAT006"
        assert "CWE-000000" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::_check_caught_by_integrity kind="unit"
    def test_real_rule_id_reference_resolves_when_known(self):
        entry = BenignCapability(
            kind="metrics",
            reason="already gated",
            caught_by="already enforced by SEC001",
        )
        result = _check_caught_by_integrity(
            benign=(entry,), known_rule_ids=frozenset({"SEC001"})
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat.py::_check_caught_by_integrity kind="unit"
    def test_fabricated_rule_id_reference_fails_closed(self):
        entry = BenignCapability(
            kind="metrics",
            reason="claims coverage elsewhere",
            caught_by="already enforced by SEC999",
        )
        result = _check_caught_by_integrity(
            benign=(entry,), known_rule_ids=frozenset({"SEC001"})
        )
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "THREAT006"
        assert "SEC999" in violations[0].detail

    # frob:tests src/frob/strata/_threat.py::_check_caught_by_integrity kind="unit"
    def test_rule_id_reference_unresolved_by_default_empty_known_set(self):
        # `known_rule_ids` defaults to empty (this package cannot import
        # `frob.gates`'s live registry) -- a caller that never passes it
        # gets deny-by-default on ANY rule-id-shaped reference.
        entry = BenignCapability(
            kind="metrics", reason="claims coverage", caught_by="caught by SEC001"
        )
        result = _check_caught_by_integrity(benign=(entry,))
        assert result.is_ok
        assert len(result.danger_ok) == 1
        assert result.danger_ok[0].rule == "THREAT006"

    # frob:tests src/frob/strata/_threat.py::_check_caught_by_integrity kind="unit"
    def test_clean_default_catalogs_have_no_gaps(self):
        # The built-in CWE_TOP_25_OUT_OF_SCOPE/QUALITY_OUT_OF_SCOPE/
        # DEFAULT_BENIGN_CAPABILITIES entries this module ships must
        # already pass with zero rule-id verification (no fabricated CWE
        # references among the shipped catalogs).
        from frob.strata._threat import DEFAULT_BENIGN_CAPABILITIES

        result = _check_caught_by_integrity(
            out_of_scope=CWE_TOP_25_OUT_OF_SCOPE + QUALITY_OUT_OF_SCOPE,
            benign=DEFAULT_BENIGN_CAPABILITIES,
            catalog=ALL_CATALOG,
        )
        assert result.is_ok
        assert result.danger_ok == ()


#: T-0383: every entry `caught_by` string a "placeholder/fabricated" audit
#: must reject outright -- a bare marker with no compensating-control
#: explanation at all. Real entries either name a control ("CWE-78 in
#: CWE_CATALOG", "PII010", "frob vet's dependency-supply-chain scan") or
#: an honest `"none -- <specific reason>"` (`CAUGHT_BY_NONE_MARKER` plus
#: substance); this set is what a lazy/fabricated entry would look like
#: instead, so this audit test can tell the two apart mechanically rather
#: than by re-reading prose.
_CAUGHT_BY_PLACEHOLDERS = frozenset(
    {"none", "todo", "tbd", "n/a", "na", "fixme", "unknown", "?", ""}
)


class TestCaughtByAuditExhaustive:
    """T-0383: audits EVERY built-in `OutOfScopeEntry`/`BenignCapability`
    this repo ships (not a sample) -- proves each `caught_by` is either a
    real, resolving compensating-control reference or a substantive,
    reasoned `"none -- ..."` disclosure, never a bare/fabricated
    placeholder, and locks the audited count so a future entry added
    without populating `caught_by` (or with a lazy placeholder) fails this
    test rather than going unnoticed."""

    # frob:tests tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive.test_every_shipped_entry_has_a_substantive_caught_by  # noqa: E501
    def test_every_shipped_entry_has_a_substantive_caught_by(self):
        from frob.strata._host_isolation import COMPROMISED_OWNER_OUT_OF_SCOPE
        from frob.strata._krb_movement import KRB_MOVEMENT_OUT_OF_SCOPE
        from frob.strata._threat import DEFAULT_BENIGN_CAPABILITIES

        all_out_of_scope = (
            CWE_TOP_25_OUT_OF_SCOPE
            + QUALITY_OUT_OF_SCOPE
            + KRB_MOVEMENT_OUT_OF_SCOPE
            + COMPROMISED_OWNER_OUT_OF_SCOPE
        )
        # Exhaustiveness lock: the audited universe is EXACTLY these two
        # families' entries -- 21 OutOfScopeEntry (16 CWE_TOP_25 + 5
        # QUALITY; the two krb/host-isolation tuples are empty by design)
        # + 9 BenignCapability. A future add to any of these tuples that
        # forgets `caught_by` still satisfies pydantic's `min_length=1`
        # (whitespace aside) but would change this count -- bumping it is
        # the forcing function that re-triggers this audit's placeholder
        # scan below.
        assert len(all_out_of_scope) == 21
        assert len(DEFAULT_BENIGN_CAPABILITIES) == 9

        for entry_id, caught_by in (
            *((e.id, e.caught_by) for e in all_out_of_scope),
            *((e.kind, e.caught_by) for e in DEFAULT_BENIGN_CAPABILITIES),
        ):
            normalized = caught_by.strip().lower()
            assert normalized not in _CAUGHT_BY_PLACEHOLDERS, (
                f"{entry_id}: caught_by is a bare placeholder, not a "
                f"substantive control reference or reasoned disclosure: "
                f"{caught_by!r}"
            )
            if normalized.startswith("none"):
                # An honest gap must still explain WHY nothing catches it
                # (docs/strata/threat.md#the-exhaustiveness-proof-the-
                # point) -- "none" alone (caught above) or "none -- " with
                # nothing following it is exactly the lazy case this
                # audit exists to catch.
                assert len(caught_by.strip()) > len("none -- "), (
                    f"{entry_id}: caught_by declares an unexplained "
                    f"'none': {caught_by!r}"
                )

    # frob:tests tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive.test_every_shipped_entry_passes_real_production_verification  # noqa: E501
    def test_every_shipped_entry_passes_real_production_verification(self):
        # Same corpus, but run through THREAT006 with the REAL live
        # gate-rule-id set (`frob.gates.known_gate_rule_ids()`), not the
        # default-empty set `test_clean_default_catalogs_have_no_gaps`
        # uses -- proves the audited entries pass the actual production
        # verification path, not merely a permissive test double.
        from frob.gates import known_gate_rule_ids
        from frob.strata._host_isolation import COMPROMISED_OWNER_OUT_OF_SCOPE
        from frob.strata._krb_movement import KRB_MOVEMENT_OUT_OF_SCOPE
        from frob.strata._threat import DEFAULT_BENIGN_CAPABILITIES

        result = _check_caught_by_integrity(
            out_of_scope=(
                CWE_TOP_25_OUT_OF_SCOPE
                + QUALITY_OUT_OF_SCOPE
                + KRB_MOVEMENT_OUT_OF_SCOPE
                + COMPROMISED_OWNER_OUT_OF_SCOPE
            ),
            benign=DEFAULT_BENIGN_CAPABILITIES,
            known_rule_ids=known_gate_rule_ids(),
            catalog=ALL_CATALOG,
        )
        assert result.is_ok
        assert result.danger_ok == ()


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
            benign=(
                BenignCapability(
                    kind="metrics", reason="no CWE weakness", caught_by="test fixture"
                ),
            ),
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
            benign=(
                BenignCapability(
                    kind="net",
                    reason="no CWE weakness for net",
                    caught_by="test fixture",
                ),
            ),
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
    def test_effect_on_a_file_absent_from_owner_does_not_crash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """strata audit G8 (T-0497) counterexample: `extract_effects`
        filters to non-FOREIGN owned files today, so `effect.file` is
        always a `binding.owner` key in practice -- but
        `check_effect_completeness` used to trust that via a bare
        `binding.owner[effect.file]` subscript. Force the untrusted case
        directly (an effect naming a file `extract_effects` never actually
        would) and prove the join degrades to a FOREIGN-owner Violation
        instead of raising KeyError."""
        from frob.strata import _threat as threat_module
        from frob.strata._effects import ObservedEffect

        node = Node(id="Api", trust="trusted", attrs=("code=api/**",))
        model = KernelModel(nodes=(node,))
        binding = bind_code(model, tmp_path).danger_ok
        monkeypatch.setattr(
            threat_module,
            "extract_effects",
            lambda _binding, _root: (
                ObservedEffect(
                    file="not/a/bound/file.py", line=1, kind="net", needle="x"
                ),
            ),
        )
        result = check_effect_completeness(model, binding, tmp_path)
        assert result.is_ok
        assert result.danger_ok[0].node == "__foreign__"

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
