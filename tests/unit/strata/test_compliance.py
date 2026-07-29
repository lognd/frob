"""Unit tests for `std.compliance`: COPPA/GDPR/HIPAA obligations +
privacy-policy-as-claims reverse audit (docs/strata/threat.md#compliance,
T-0109/T-0116).
"""

from __future__ import annotations

from pathlib import Path

from frob.registry import RegistryEntry, parse_disposition
from frob.strata import (
    Boundary,
    BoundaryDirection,
    Claim,
    Flow,
    KernelModel,
    Node,
    NoFlow,
    OutOfScopeRegulation,
    PrivacyPolicy,
    Quantity,
)
from frob.strata._compliance import (
    _CMPL_UNIT_TRIAGE_TICKET,
    CMPL_REGISTRY_UNIT_IDS,
    COMPLIANCE_CATALOG,
    REGULATION_VIEWS,
    _check_cmpl_registry_unit_backing,
    _check_cmpl_registry_unit_dispositions,
    _check_regulation_caught_by_integrity,
    check_cmpl_registry,
    check_privacy_policy,
    check_regulation_catalog_completeness,
    check_regulation_discharge,
    evaluate_compliance,
)

_SOME_CMPL_ID = next(iter(sorted(CMPL_REGISTRY_UNIT_IDS)))


def _cmpl_entry(disposition_raw: str, entry_id: str = _SOME_CMPL_ID) -> RegistryEntry:
    """A synthetic `RegistryEntry` for `entry_id` carrying `disposition_raw`,
    parsed through the SAME shared grammar (`frob.registry.parse_disposition`)
    the real registry loader uses -- never a hand-rolled `Disposition`."""
    return RegistryEntry(id=entry_id, disposition=parse_disposition(disposition_raw))


class TestRegulationCatalogCompleteness:
    # frob:tests src/frob/strata/_compliance.py::check_regulation_catalog_completeness \
    # kind="unit"
    def test_full_catalog_satisfies_all_regulations_view(self):
        result = check_regulation_catalog_completeness("all-regulations")
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_compliance.py::check_regulation_catalog_completeness \
    # kind="unit"
    def test_missing_entry_is_a_violation(self):
        thin_catalog = tuple(e for e in COMPLIANCE_CATALOG if e.id != "COPPA")
        result = check_regulation_catalog_completeness("us-coppa", catalog=thin_catalog)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "COMPLIANCE001"
        assert violations[0].regulation == "COPPA"

    # frob:tests src/frob/strata/_compliance.py::check_regulation_catalog_completeness \
    # kind="unit"
    def test_out_of_scope_entry_excuses_a_missing_catalog_entry(self):
        thin_catalog = tuple(e for e in COMPLIANCE_CATALOG if e.id != "COPPA")
        result = check_regulation_catalog_completeness(
            "us-coppa",
            catalog=thin_catalog,
            out_of_scope=(
                OutOfScopeRegulation(
                    id="COPPA",
                    reason="no under-13 flows in this deployment",
                    owner="legal@example.com",
                    review="2027-01-01",
                    caught_by="legal intake process reviews age-gating at "
                    "onboarding, outside frob's static scope",
                ),
            ),
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_compliance.py::check_regulation_catalog_completeness \
    # kind="unit"
    def test_unknown_view_fails_closed(self):
        result = check_regulation_catalog_completeness("no-such-view")
        assert result.is_err

    # frob:tests src/frob/strata/_compliance.py::check_regulation_catalog_completeness \
    # kind="unit"
    def test_views_table_is_data_driven(self):
        assert "us-coppa" in REGULATION_VIEWS
        assert REGULATION_VIEWS["all-regulations"] == frozenset(
            e.id for e in COMPLIANCE_CATALOG
        )


def _coppa_model(*, gated: bool) -> KernelModel:
    """A child-tagged collection flow into a Pii store, gated or not."""
    principal = Node(id="Child", trust="foreign")
    store = Node(id="Store", trust="trusted", clearance="Pii")
    flow = Flow(
        id="collect",
        src="Child",
        dst="Store",
        label="Pii",
        attrs=("subject:child",),
    )
    boundaries = ()
    if gated:
        boundaries = (
            Boundary(
                id="age-gate",
                flow_id="collect",
                direction=BoundaryDirection.ENDORSE,
                from_level="foreign",
                to_level="authenticated",
                predicate="verified_parental_consent",
            ),
        )
    return KernelModel(nodes=(principal, store), flows=(flow,), boundaries=boundaries)


class TestCoppa:
    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_ungated_child_collection_flow_refutes_coppa(self):
        model = _coppa_model(gated=False)
        result = check_regulation_discharge(model)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].regulation == "COPPA"
        assert violations[0].target == "collect"

    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_age_gate_boundary_discharges_coppa(self):
        model = _coppa_model(gated=True)
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_declassify_only_boundary_does_not_discharge_coppa(self):
        """An unrelated DECLASSIFY boundary on the same flow must not
        silently satisfy the age-gate obligation -- only ENDORSE does
        (the T-0113 any-boundary lesson; reviewer-reported gap)."""
        principal = Node(id="Child", trust="foreign")
        store = Node(id="Store", trust="trusted", clearance="Pii")
        flow = Flow(
            id="collect",
            src="Child",
            dst="Store",
            label="Pii",
            attrs=("subject:child",),
        )
        boundary = Boundary(
            id="declassify-only",
            flow_id="collect",
            direction=BoundaryDirection.DECLASSIFY,
            from_level="Pii",
            to_level="Internal",
            predicate="unrelated_declassification",
        )
        model = KernelModel(
            nodes=(principal, store), flows=(flow,), boundaries=(boundary,)
        )
        result = check_regulation_discharge(model)
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].regulation == "COPPA"
        assert violations[0].target == "collect"

    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_assumed_claim_with_owner_and_review_overrides(self):
        model = _coppa_model(gated=False)
        model = model.model_copy(
            update={
                "claims": (
                    Claim(
                        id="compliance:COPPA:collect",
                        body=NoFlow(src="Child", dst="Store"),
                        assumed=True,
                        owner="legal@example.com",
                        review="2027-01-01",
                    ),
                )
            }
        )
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_assumed_claim_with_no_owner_is_a_violation(self):
        model = _coppa_model(gated=False)
        model = model.model_copy(
            update={
                "claims": (
                    Claim(
                        id="compliance:COPPA:collect",
                        body=NoFlow(src="Child", dst="Store"),
                        assumed=True,
                    ),
                )
            }
        )
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert any(
            v.rule == "COMPLIANCE002" and "owner" in v.detail for v in result.danger_ok
        )


def _erasure_model(*, has_revocation: bool) -> KernelModel:
    store = Node(
        id="EuStore",
        trust="trusted",
        clearance="Pii",
        attrs=("jurisdiction:eu-resident",),
    )
    issuer = Node(id="Api", trust="trusted")
    flows = [Flow(id="collect", src="Api", dst="EuStore", label="Pii")]
    if has_revocation:
        flows.append(
            Flow(
                id="delete",
                src="Api",
                dst="EuStore",
                label="Pii",
                attrs=("revocation",),
            )
        )
    return KernelModel(nodes=(issuer, store), flows=tuple(flows))


class TestGdprErasure:
    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_eu_resident_store_with_no_deletion_path_refutes_erasure(self):
        model = _erasure_model(has_revocation=False)
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert any(v.regulation == "GDPR-ERASURE" for v in result.danger_ok)

    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_revocation_edge_discharges_erasure(self):
        model = _erasure_model(has_revocation=True)
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert not any(v.regulation == "GDPR-ERASURE" for v in result.danger_ok)


class TestGdprRetention:
    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_store_past_declared_retention_refutes(self):
        store = Node(
            id="EuStore",
            trust="trusted",
            clearance="Pii",
            attrs=("jurisdiction:eu-resident", "retention=1d"),
        )
        api = Node(id="Api", trust="trusted")
        flow = Flow(
            id="collect",
            src="Api",
            dst="EuStore",
            label="Pii",
            age=Quantity(value=10, unit="d"),
        )
        model = KernelModel(nodes=(api, store), flows=(flow,))
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert any(v.regulation == "GDPR-RETENTION" for v in result.danger_ok)

    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_store_within_retention_bound_passes(self):
        store = Node(
            id="EuStore",
            trust="trusted",
            clearance="Pii",
            attrs=("jurisdiction:eu-resident", "retention=90d"),
        )
        api = Node(id="Api", trust="trusted")
        flow = Flow(
            id="collect",
            src="Api",
            dst="EuStore",
            label="Pii",
            age=Quantity(value=1, unit="d"),
        )
        model = KernelModel(nodes=(api, store), flows=(flow,))
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert not any(v.regulation == "GDPR-RETENTION" for v in result.danger_ok)


class TestGdprLawfulBasis:
    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_no_declared_basis_refutes(self):
        store = Node(
            id="EuStore",
            trust="trusted",
            clearance="Pii",
            attrs=("jurisdiction:eu-resident",),
        )
        api = Node(id="Api", trust="trusted")
        flow = Flow(id="collect", src="Api", dst="EuStore", label="Pii")
        model = KernelModel(nodes=(api, store), flows=(flow,))
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert any(v.regulation == "GDPR-BASIS" for v in result.danger_ok)

    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_declared_basis_discharges(self):
        store = Node(
            id="EuStore",
            trust="trusted",
            clearance="Pii",
            attrs=("jurisdiction:eu-resident",),
        )
        api = Node(id="Api", trust="trusted")
        flow = Flow(
            id="collect",
            src="Api",
            dst="EuStore",
            label="Pii",
            attrs=("basis:consent",),
        )
        model = KernelModel(nodes=(api, store), flows=(flow,))
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert not any(v.regulation == "GDPR-BASIS" for v in result.danger_ok)


class TestHipaaBaa:
    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_health_flow_to_uncovered_party_refutes(self):
        api = Node(id="Api", trust="trusted")
        vendor = Node(id="Vendor", trust="authenticated")
        flow = Flow(
            id="share", src="Api", dst="Vendor", label="Pii", attrs=("subject:health",)
        )
        model = KernelModel(nodes=(api, vendor), flows=(flow,))
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert any(v.regulation == "HIPAA-BAA" for v in result.danger_ok)

    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_covered_party_attestation_discharges(self):
        api = Node(id="Api", trust="trusted")
        vendor = Node(id="Vendor", trust="authenticated", attrs=("covered-party",))
        flow = Flow(
            id="share", src="Api", dst="Vendor", label="Pii", attrs=("subject:health",)
        )
        model = KernelModel(nodes=(api, vendor), flows=(flow,))
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert not any(v.regulation == "HIPAA-BAA" for v in result.danger_ok)


class TestMinimization:
    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_collected_but_never_read_is_a_violation(self):
        api = Node(id="Api", trust="trusted")
        store = Node(id="Store", trust="trusted", clearance="Pii")
        flow = Flow(
            id="collect", src="Api", dst="Store", label="Pii", attrs=("field:ssn",)
        )
        model = KernelModel(nodes=(api, store), flows=(flow,))
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert any(v.regulation == "MINIMIZATION" for v in result.danger_ok)

    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_downstream_read_discharges(self):
        api = Node(id="Api", trust="trusted")
        store = Node(id="Store", trust="trusted", clearance="Pii")
        reader = Node(id="Reader", trust="trusted")
        flows = (
            Flow(
                id="collect", src="Api", dst="Store", label="Pii", attrs=("field:ssn",)
            ),
            Flow(id="read", src="Store", dst="Reader", label="Pii"),
        )
        model = KernelModel(nodes=(api, store, reader), flows=flows)
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert not any(v.regulation == "MINIMIZATION" for v in result.danger_ok)


class TestPrivacyNotice:
    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_public_web_node_with_no_mitigation_refutes(self):
        store = Node(
            id="Store", trust="trusted", clearance="Pii", attrs=("exposure:public-web",)
        )
        model = KernelModel(nodes=(store,), flows=())
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert any(v.regulation == "PRIVACY-NOTICE" for v in result.danger_ok)

    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_declared_privacy_policy_attr_discharges(self):
        store = Node(
            id="Store",
            trust="trusted",
            clearance="Pii",
            attrs=("exposure:public-web", "privacy-policy"),
        )
        model = KernelModel(nodes=(store,), flows=())
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert not any(v.regulation == "PRIVACY-NOTICE" for v in result.danger_ok)

    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_no_public_web_exposure_is_silent(self):
        store = Node(id="Store", trust="trusted", clearance="Pii")
        model = KernelModel(nodes=(store,), flows=())
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert not any(v.regulation == "PRIVACY-NOTICE" for v in result.danger_ok)

    # frob:tests src/frob/strata/_compliance.py::check_regulation_discharge kind="unit"
    def test_public_web_node_below_pii_clearance_is_silent(self):
        store = Node(
            id="Store",
            trust="trusted",
            clearance="Public",
            attrs=("exposure:public-web",),
        )
        model = KernelModel(nodes=(store,), flows=())
        result = check_regulation_discharge(model)
        assert result.is_ok
        assert not any(v.regulation == "PRIVACY-NOTICE" for v in result.danger_ok)


class TestPrivacyPolicy:
    # frob:tests src/frob/strata/_compliance.py::check_privacy_policy kind="unit"
    def test_field_the_policy_omits_refutes(self):
        api = Node(id="Api", trust="trusted")
        store = Node(id="Store", trust="trusted", clearance="Pii")
        flow = Flow(
            id="collect", src="Api", dst="Store", label="Pii", attrs=("field:ssn",)
        )
        model = KernelModel(nodes=(api, store), flows=(flow,))
        policy = PrivacyPolicy(id="v1", collected_fields=frozenset({"email"}))
        violations = check_privacy_policy(model, policy)
        assert len(violations) == 1
        assert violations[0].rule == "COMPLIANCE003"
        assert "ssn" in violations[0].detail

    # frob:tests src/frob/strata/_compliance.py::check_privacy_policy kind="unit"
    def test_declared_field_passes(self):
        api = Node(id="Api", trust="trusted")
        store = Node(id="Store", trust="trusted", clearance="Pii")
        flow = Flow(
            id="collect", src="Api", dst="Store", label="Pii", attrs=("field:email",)
        )
        model = KernelModel(nodes=(api, store), flows=(flow,))
        policy = PrivacyPolicy(id="v1", collected_fields=frozenset({"email"}))
        violations = check_privacy_policy(model, policy)
        assert violations == ()


class TestRegulationCaughtByIntegrity:
    """COMPLIANCE004 (T-0382): a `caught_by` naming a rule id must resolve
    against the live gate-rule-id set -- existence AND (via that set being
    exactly the rule ids a real Violation-producing gate can emit)
    efficacy, not just a registered-looking string. Non-vacuous pairing:
    the claimed control absent -> discharge REFUSED (negative case below),
    the claimed control present -> discharge succeeds (positive case)."""

    # frob:tests src/frob/strata/_compliance.py::_check_regulation_caught_by_integrity \
    # kind="unit"
    def test_honest_none_caught_by_never_fails(self):
        entry = OutOfScopeRegulation(
            id="COPPA",
            reason="not applicable",
            owner="legal@example.com",
            review="2027-01-01",
            caught_by="none -- no compensating control today",
        )
        result = _check_regulation_caught_by_integrity(out_of_scope=(entry,))
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_compliance.py::_check_regulation_caught_by_integrity \
    # kind="unit"
    def test_caught_by_naming_absent_control_is_refused(self):
        """Negative case: the claimed control (SEC999) does not exist in
        the live rule-id set -- discharge must be REFUSED, not silently
        trusted."""
        entry = OutOfScopeRegulation(
            id="COPPA",
            reason="claims coverage",
            owner="legal@example.com",
            review="2027-01-01",
            caught_by="already enforced by SEC999",
        )
        result = _check_regulation_caught_by_integrity(
            out_of_scope=(entry,), known_rule_ids=frozenset({"SEC001"})
        )
        assert result.is_ok
        violations = result.danger_ok
        assert len(violations) == 1
        assert violations[0].rule == "COMPLIANCE004"
        assert "SEC999" in violations[0].detail

    # frob:tests src/frob/strata/_compliance.py::_check_regulation_caught_by_integrity \
    # kind="unit"
    def test_caught_by_naming_present_control_discharges(self):
        """Positive case: the identical claim, but SEC001 is actually in
        the live rule-id set -- discharge succeeds."""
        entry = OutOfScopeRegulation(
            id="COPPA",
            reason="claims coverage",
            owner="legal@example.com",
            review="2027-01-01",
            caught_by="already enforced by SEC001",
        )
        result = _check_regulation_caught_by_integrity(
            out_of_scope=(entry,), known_rule_ids=frozenset({"SEC001"})
        )
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_compliance.py::_check_regulation_caught_by_integrity \
    # kind="unit"
    def test_free_text_with_no_rule_id_token_is_not_checked_further(self):
        entry = OutOfScopeRegulation(
            id="COPPA",
            reason="no under-13 flows in this deployment",
            owner="legal@example.com",
            review="2027-01-01",
            caught_by="legal intake process reviews age-gating at onboarding",
        )
        result = _check_regulation_caught_by_integrity(out_of_scope=(entry,))
        assert result.is_ok
        assert result.danger_ok == ()


#: T-0383: same placeholder vocabulary `test_threat.py`'s exhaustive audit
#: uses -- kept identical (not re-derived) so a "lazy caught_by" means the
#: same thing across both the security (`OutOfScopeEntry`/
#: `BenignCapability`) and compliance (`OutOfScopeRegulation`) families.
_CAUGHT_BY_PLACEHOLDERS = frozenset(
    {"none", "todo", "tbd", "n/a", "na", "fixme", "unknown", "?", ""}
)


class TestCaughtByAuditExhaustive:
    """T-0383: audits EVERY built-in `OutOfScopeRegulation` this repo
    ships (not a sample). Today there is exactly one
    (`COMPLIANCE_OUT_OF_SCOPE`'s CCPA entry) -- the count assertion below
    is the forcing function that re-triggers this audit the moment a
    second one is added without a substantive `caught_by`."""

    # frob:tests tests/unit/strata/test_compliance.py::TestCaughtByAuditExhaustive.test_every_shipped_entry_has_a_substantive_caught_by  # noqa: E501
    def test_every_shipped_entry_has_a_substantive_caught_by(self):
        from frob.strata._compliance import COMPLIANCE_OUT_OF_SCOPE

        assert len(COMPLIANCE_OUT_OF_SCOPE) == 1
        for entry in COMPLIANCE_OUT_OF_SCOPE:
            normalized = entry.caught_by.strip().lower()
            assert normalized not in _CAUGHT_BY_PLACEHOLDERS, (
                f"{entry.id}: caught_by is a bare placeholder, not a "
                f"substantive control reference: {entry.caught_by!r}"
            )
            if normalized.startswith("none"):
                assert len(entry.caught_by.strip()) > len("none -- "), (
                    f"{entry.id}: caught_by declares an unexplained "
                    f"'none': {entry.caught_by!r}"
                )

    # frob:tests tests/unit/strata/test_compliance.py::TestCaughtByAuditExhaustive.test_every_shipped_entry_passes_real_production_verification  # noqa: E501
    def test_every_shipped_entry_passes_real_production_verification(self):
        # Same corpus, but through COMPLIANCE004 with the REAL live
        # gate-rule-id set, proving the shipped entry passes the actual
        # production verification path, not merely a permissive default.
        from frob.gates import known_gate_rule_ids
        from frob.strata._compliance import COMPLIANCE_OUT_OF_SCOPE

        result = _check_regulation_caught_by_integrity(
            out_of_scope=COMPLIANCE_OUT_OF_SCOPE,
            known_rule_ids=known_gate_rule_ids(),
        )
        assert result.is_ok
        assert result.danger_ok == ()


class TestEvaluateCompliance:
    # frob:tests src/frob/strata/_compliance.py::evaluate_compliance kind="unit"
    def test_conjunction_of_catalog_discharge_and_policy(self):
        model = _coppa_model(gated=False)
        result = evaluate_compliance(model, view="us-coppa")
        assert result.is_ok
        rules = {v.rule for v in result.danger_ok.violations}
        assert "COMPLIANCE002" in rules

    # frob:tests src/frob/strata/_compliance.py::evaluate_compliance kind="unit"
    def test_unknown_view_fails_closed(self):
        model = KernelModel()
        result = evaluate_compliance(model, view="no-such-view")
        assert result.is_err

    # frob:tests src/frob/strata/_compliance.py::evaluate_compliance kind="unit"
    def test_caught_by_integrity_folds_into_the_conjunction(self):
        """T-0382: `evaluate_compliance` itself refuses an out-of-scope
        exclusion whose caught_by names an absent control -- COMPLIANCE004
        fires from the real entrypoint, not merely as a standalone
        function nobody calls."""
        thin_catalog = tuple(e for e in COMPLIANCE_CATALOG if e.id != "COPPA")
        out_of_scope = (
            OutOfScopeRegulation(
                id="COPPA",
                reason="claims coverage",
                owner="legal@example.com",
                review="2027-01-01",
                caught_by="already enforced by SEC999",
            ),
        )
        model = KernelModel()
        result = evaluate_compliance(
            model,
            view="us-coppa",
            catalog=thin_catalog,
            out_of_scope=out_of_scope,
            known_rule_ids=frozenset({"SEC001"}),
        )
        assert result.is_ok
        rules = {v.rule for v in result.danger_ok.violations}
        assert "COMPLIANCE004" in rules

    # frob:tests src/frob/strata/_compliance.py::evaluate_compliance kind="unit"
    def test_caught_by_integrity_passes_when_control_is_real(self):
        thin_catalog = tuple(e for e in COMPLIANCE_CATALOG if e.id != "COPPA")
        out_of_scope = (
            OutOfScopeRegulation(
                id="COPPA",
                reason="claims coverage",
                owner="legal@example.com",
                review="2027-01-01",
                caught_by="already enforced by SEC001",
            ),
        )
        model = KernelModel()
        result = evaluate_compliance(
            model,
            view="us-coppa",
            catalog=thin_catalog,
            out_of_scope=out_of_scope,
            known_rule_ids=frozenset({"SEC001"}),
        )
        assert result.is_ok
        rules = {v.rule for v in result.danger_ok.violations}
        assert "COMPLIANCE004" not in rules


class TestCmplRegistry:
    """COMPLIANCE005 (T-0607): `_check_cmpl_registry_unit_dispositions` over
    the 17 `CMPL_REGISTRY_UNIT_IDS` compliance-registry units, plus the
    real-file `check_cmpl_registry` entrypoint."""

    # frob:tests \
    # src/frob/strata/_compliance.py::_check_cmpl_registry_unit_dispositions kind="unit"
    def test_deferred_disposition_is_refused(self):
        entries = (_cmpl_entry("deferred:T-0001"),)
        violations = _check_cmpl_registry_unit_dispositions(entries)
        assert len(violations) == 1
        assert violations[0].rule == "COMPLIANCE005"
        assert violations[0].regulation == _SOME_CMPL_ID

    # frob:tests \
    # src/frob/strata/_compliance.py::_check_cmpl_registry_unit_dispositions kind="unit"
    def test_undispositioned_is_refused(self):
        entries = (_cmpl_entry("pending"),)
        violations = _check_cmpl_registry_unit_dispositions(entries)
        assert len(violations) == 1
        assert violations[0].rule == "COMPLIANCE005"

    # frob:tests \
    # src/frob/strata/_compliance.py::_check_cmpl_registry_unit_dispositions kind="unit"
    def test_handled_by_and_out_of_scope_dispositions_pass(self):
        handled = _cmpl_entry(
            "handled_by:COMPLIANCE005", entry_id=sorted(CMPL_REGISTRY_UNIT_IDS)[0]
        )
        out_of_scope = _cmpl_entry(
            "out_of_scope:reason text", entry_id=sorted(CMPL_REGISTRY_UNIT_IDS)[1]
        )
        violations = _check_cmpl_registry_unit_dispositions((handled, out_of_scope))
        assert violations == ()

    # frob:tests \
    # src/frob/strata/_compliance.py::_check_cmpl_registry_unit_dispositions kind="unit"
    def test_id_outside_the_universe_is_ignored(self):
        entries = (_cmpl_entry("deferred:T-0001", entry_id="CMPL-NOT-TRACKED"),)
        violations = _check_cmpl_registry_unit_dispositions(entries)
        assert violations == ()

    # frob:tests \
    # src/frob/strata/_compliance.py::_check_cmpl_registry_unit_dispositions kind="unit"
    def test_id_absent_from_entries_is_silently_skipped(self):
        violations = _check_cmpl_registry_unit_dispositions(())
        assert violations == ()

    # frob:tests src/frob/strata/_compliance.py::check_cmpl_registry kind="unit"
    def test_check_cmpl_registry_loads_real_file(self):
        registry_dir = (
            Path(__file__).resolve().parents[3] / "docs" / "design" / "registry"
        )
        result = check_cmpl_registry(registry_dir)
        assert result.is_ok
        violations = result.danger_ok
        # T-1244: COMPLIANCE005 (disposition-string presence) is clean, but
        # COMPLIANCE007 (real per-framework backing) surfaces the honest,
        # currently-open catalogued-not-enforced gap for every
        # _CMPL_UNIT_TRIAGE_TICKET member that still carries the vacuous
        # handled_by:COMPLIANCE005 self-reference -- this is the finding
        # this ticket exists to make loud, not a regression to suppress.
        assert not any(v.rule == "COMPLIANCE005" for v in violations)
        compliance007 = {v.regulation for v in violations if v.rule == "COMPLIANCE007"}
        assert compliance007 == set(_CMPL_UNIT_TRIAGE_TICKET)

    # frob:tests src/frob/strata/_compliance.py::check_cmpl_registry kind="unit"
    def test_check_cmpl_registry_missing_file_is_parse_failed(self, tmp_path):
        result = check_cmpl_registry(tmp_path)
        assert result.is_err


class TestCmplRegistryBacking:
    """COMPLIANCE007 (T-1244): the generate-and-verify half COMPLIANCE005
    alone cannot provide -- distinguishing a real per-framework backing
    from the vacuous handled_by:COMPLIANCE005 self-reference."""

    # frob:tests src/frob/strata/_compliance.py::_check_cmpl_registry_unit_backing \
    # kind="unit"
    def test_self_referential_handled_by_is_flagged(self):
        some_id = next(iter(sorted(_CMPL_UNIT_TRIAGE_TICKET)))
        entries = (_cmpl_entry("handled_by:COMPLIANCE005", entry_id=some_id),)
        violations = _check_cmpl_registry_unit_backing(entries)
        assert len(violations) == 1
        assert violations[0].rule == "COMPLIANCE007"
        assert violations[0].regulation == some_id
        assert _CMPL_UNIT_TRIAGE_TICKET[some_id] in violations[0].detail

    # frob:tests src/frob/strata/_compliance.py::_check_cmpl_registry_unit_backing \
    # kind="unit"
    def test_frob_catalog_entries_self_reference_is_not_flagged(self):
        entries = (
            _cmpl_entry(
                "handled_by:COMPLIANCE005", entry_id="CMPL-FROB-CATALOG-ENTRIES"
            ),
        )
        violations = _check_cmpl_registry_unit_backing(entries)
        assert violations == ()

    # frob:tests src/frob/strata/_compliance.py::_check_cmpl_registry_unit_backing \
    # kind="unit"
    def test_non_self_referential_handled_by_is_not_flagged(self):
        some_id = next(iter(sorted(_CMPL_UNIT_TRIAGE_TICKET)))
        entries = (_cmpl_entry("handled_by:PII010", entry_id=some_id),)
        violations = _check_cmpl_registry_unit_backing(entries)
        assert violations == ()
