"""`frob sys audit` -- the CHECKING counterpart to `frob sys doc`'s rendering
(T-0115, docs/strata/threat.md#the-exhaustiveness-proof-the-point item F).

Evaluates the full three-part exhaustiveness conjunction (THREAT001 +
THREAT002 + THREAT003, and the COMPLIANCE001/002 mirror) for a model
against a CONFIGURED set of baseline views -- one per family (security,
quality, compliance) -- and reports every failing view as a named gap: a
machine-usable, CI-ready summary (`AuditReport.proved`, `AuditReport.gaps`)
rather than the human-facing markdown `_sysdoc.py::render_audit_matrix`
prints.

Zero new detection: this module calls only the ALREADY-SHIPPED per-check
functions `_threat.py::check_catalog_completeness` / `check_capability_
completeness` / `check_discharge_completeness` and `_compliance.py::
evaluate_compliance` -- the exact same joins `evaluate_threats` and `frob
sys doc` already run. The one seam this module adds is `_evaluate_family`,
which threads a per-family `views` table (`QUALITY_VIEWS` differs from the
security family's global `VIEWS`, so `evaluate_threats` -- which always
resolves against the module-global `VIEWS` -- cannot be reused as-is for
the quality family; `_evaluate_family` is the SAME three-call assembly
`evaluate_threats` itself performs, just parameterized on which view table
to resolve against).

T-0280: HOST001/HOST002 movement-impossibility proofs and the compromised-
user blast-radius scenario (`_host_isolation.py::evaluate_host_isolation_
waived`, `_scenarios.py::build_compromised_user_scenario`, both ALREADY
SHIPPED and sound, T-0256) are wired into `evaluate_exhaustiveness` the
SAME zero-new-detection way -- `_host_isolation_gap`/`_blast_radius_gaps`
are pure adapters, mirroring `_lint_gaps`/`_pii_gaps`. Before this, neither
function had a caller reaching them from `frob sys audit`, so a real repo
had no way to run the proof without a hand-written harness."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._compliance import REGULATION_VIEWS, ComplianceViolation, evaluate_compliance
from ._cve_fingerprint import (
    CVE_FINGERPRINTS,
    FingerprintViolation,
    check_fingerprint_catalog_drift,
)
from ._errors import StrataError
from ._host import host_manifest_for
from ._host_isolation import HostIsolationViolation, evaluate_host_isolation_waived
from ._lint import LintViolation, evaluate_lint
from ._models import KernelModel, Verdict
from ._pii import PiiViolation, evaluate_pii
from ._scenarios import (
    ScenarioResult,
    build_compromised_user_scenario,
    evaluate_scenarios,
)
from ._selfconform import (
    SYS_STALE_DESIGN,
    SYS_UNDECLARED_INTERFACE,
    SYS_UNMODELED_CODE,
)
from ._threat import (
    CWE_CATALOG,
    DEFAULT_BENIGN_CAPABILITIES,
    QUALITY_CATALOG,
    QUALITY_OUT_OF_SCOPE,
    QUALITY_VIEWS,
    VIEWS,
    BenignCapability,
    OutOfScopeEntry,
    ThreatViolation,
    WeaknessEntry,
    check_capability_completeness,
    check_catalog_completeness,
    check_discharge_completeness,
)
from ._waive import STALE_WAIVER_RULE, apply_waivers, stale_detail

_log = get_logger(__name__)

#: HOST001/HOST002 own their waiver channel exactly like SYS100-102
#: (`_selfconform.py`'s `SYS_*` constants): `evaluate_host_isolation_waived`
#: already runs each finding through `_waive.py::apply_waivers` scoped to
#: its own rule family (`_host_isolation.py` module docstring's
#: `HOST_MULTI_INSTANCE_WAIVER_FAMILIES` precedent) BEFORE this module ever
#: sees a result, so this module's OWN generic `apply_waivers` pass over
#: `gaps` must exclude both rule ids here too -- otherwise a HOST001/
#: HOST002 waiver clause, already correctly matched inside `evaluate_host_
#: isolation_waived`, would be re-evaluated against a `gaps` list that no
#: longer contains the (now-suppressed) finding, and get misreported STALE
#: a second time (T-0280).
_HOST_RULE_IDS = frozenset({"HOST001", "HOST002"})

#: Default configured views per family -- every view each family's catalog
#: ships, so a default `frob sys audit` run proves exhaustiveness against
#: EVERY baseline the repo's catalogs currently define (docs/strata/
#: threat.md#the-exhaustiveness-proof-the-point: "the exhaustiveness claim
#: is the conjunction"). A caller wanting a narrower audit passes explicit
#: view tuples.
# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
DEFAULT_SECURITY_VIEWS: tuple[str, ...] = tuple(VIEWS)
# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
DEFAULT_QUALITY_VIEWS: tuple[str, ...] = tuple(QUALITY_VIEWS)
# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
DEFAULT_COMPLIANCE_VIEWS: tuple[str, ...] = tuple(REGULATION_VIEWS)


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class FamilyGap(BaseModel):
    """One named exhaustiveness gap: which family/view failed, the
    underlying rule id (THREAT00x / COMPLIANCE00x), and the human detail --
    the machine-usable unit `frob sys audit`'s exit code and CI summary key
    off (docs/strata/threat.md: "every gap named, owned, and expiring")."""

    model_config = ConfigDict(frozen=True)

    family: str  # "security" | "quality" | "compliance"
    view: str
    rule: str
    detail: str
    # T-0174: the node/target id this gap fired against, when the
    # underlying violation names one -- the key a `waive` clause (T-0174,
    # `_waive.py`) matches against. `None` for family/view-level gaps
    # (e.g. a catalog-completeness gap) that name no single node.
    target: str | None = None
    # T-0174 REJECT round: the sub-target (capability kind for THREAT002,
    # CWE id for THREAT003) THIS instance fired for -- these two rules can
    # each fire more than once on the same node, so a `waive` clause
    # targeting either MUST name a sub-target (`_waive.py::
    # MULTI_INSTANCE_WAIVER_FAMILIES`) and matching needs this structured
    # field, never parsed back out of `detail`'s free text. `None` for
    # every single-instance-per-node family (LINT/PII/COMPLIANCE) and for
    # THREAT001 (a catalog/view-level gap, not per-node).
    sub_target: str | None = None


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class AuditReport(BaseModel):
    """The full exhaustiveness conjunction's outcome across every configured
    view: `proved` iff `gaps` is empty. `views_checked` names exactly what
    was evaluated (family-qualified, e.g. `security:owasp-top-10`), so a
    clean report is auditable -- no view silently skipped."""

    model_config = ConfigDict(frozen=True)

    views_checked: tuple[str, ...] = ()
    gaps: tuple[FamilyGap, ...] = ()
    # T-0174: gaps suppressed by a matching `waive` clause -- kept here for
    # report visibility (never a silent drop, `_waive.py` module
    # docstring), separate from `gaps` so `proved` stays exactly "zero
    # UNWAIVED gaps."
    waived: tuple[FamilyGap, ...] = ()

    # frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
    @property
    def proved(self) -> bool:
        """True iff every configured view's exhaustiveness conjunction held
        across all families -- zero named gaps anywhere."""
        return not self.gaps


def _threat_violation_sub_target(v: ThreatViolation) -> str | None:
    """THREAT002/THREAT003's multi-instance-per-node sub-target: the
    capability kind THREAT002 fired for, or the CWE id THREAT003 fired
    for (`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`'s module docstring).
    `None` for THREAT001 (a catalog/view-level gap, not per-node) and for
    any violation that names neither (should not happen for THREAT002/
    THREAT003 -- `check_capability_completeness`/`check_discharge_
    completeness` always set one)."""
    if v.rule == "THREAT002":
        return v.capability
    if v.rule == "THREAT003":
        return v.cwe or None
    return None


def _threat_gaps(
    family: str, view: str, violations: tuple[ThreatViolation, ...]
) -> tuple[FamilyGap, ...]:
    """Adapt `_threat.py::ThreatViolation`s into `FamilyGap`s for `view`,
    naming whichever id the violation actually carries (CWE, capability
    kind, or node) when `detail` is empty -- never a blank gap."""
    return tuple(
        FamilyGap(
            family=family,
            view=view,
            rule=v.rule,
            detail=v.detail or (v.cwe or v.capability or v.node or "unnamed"),
            target=v.node,
            sub_target=_threat_violation_sub_target(v),
        )
        for v in violations
    )


def _compliance_gaps(
    view: str, violations: tuple[ComplianceViolation, ...]
) -> tuple[FamilyGap, ...]:
    """Adapt `_compliance.py::ComplianceViolation`s into `FamilyGap`s for `view`."""
    return tuple(
        FamilyGap(
            family="compliance",
            view=view,
            rule=v.rule,
            detail=v.detail or (v.target or v.regulation or "unnamed"),
            target=v.target,
        )
        for v in violations
    )


def _pii_gaps(violations: tuple[PiiViolation, ...]) -> tuple[FamilyGap, ...]:
    """Adapt `_pii.py::PiiViolation`s into `FamilyGap`s. `_pii.py::
    evaluate_pii` has no baseline-view concept (PII001-004 are all
    structural joins, not a catalog-completeness check like THREAT001), so
    every gap is reported under the fixed `"model"` view (T-0154)."""
    return tuple(
        FamilyGap(
            family="pii",
            view="model",
            rule=v.rule,
            detail=v.detail or (v.target or "unnamed"),
            target=v.target,
        )
        for v in violations
    )


def _lint_gaps(violations: tuple[LintViolation, ...]) -> tuple[FamilyGap, ...]:
    """Adapt `_lint.py::LintViolation`s into `FamilyGap`s. `_lint.py::
    evaluate_lint` has no baseline-view concept (LINT001-005 are all
    structural joins, not a catalog-completeness check like THREAT001), so
    every gap is reported under the fixed `"model"` view -- the same
    fixed-view shape `_pii_gaps` uses (T-0154 precedent), T-0155."""
    return tuple(
        FamilyGap(
            family="lint",
            view="model",
            rule=v.rule,
            detail=v.detail or (v.target or "unnamed"),
            target=v.target,
        )
        for v in violations
    )


def _fingerprint_gaps(
    violations: tuple[FingerprintViolation, ...],
) -> tuple[FamilyGap, ...]:
    """Adapt `_cve_fingerprint.py::FingerprintViolation`s (CVEFP001) into
    `FamilyGap`s. Model-independent, like `_pii_gaps`: `check_fingerprint_
    catalog_drift` proves a static catalog-join property (every `CveFingerprint
    .cwe_id` resolves against the std.cwe catalog union), not a per-model
    THREAT001-style baseline-view check, so every gap is reported under the
    fixed `"catalog"` view (T-0153, docs/strata/threat.md#cve-fingerprints-
    code-level-pattern-catalog-t-0153)."""
    return tuple(
        FamilyGap(
            family="cve-fingerprint",
            view="catalog",
            rule=v.rule,
            detail=v.detail or f"{v.fingerprint_id} -> {v.cwe_id}",
        )
        for v in violations
    )


def _host_isolation_gap(v: HostIsolationViolation) -> FamilyGap:
    """Adapt one `_host_isolation.py::HostIsolationViolation` (HOST001
    lateral or HOST002 vertical) into a `FamilyGap`, reported under the
    fixed `"model"` view -- the same fixed-view shape `_lint_gaps`/
    `_pii_gaps` use (HOST001/HOST002 are structural per-model joins, not a
    catalog-completeness check like THREAT001). `target` names the
    implicated service user (not a node id) since a user may be declared
    by more than one node (`evaluate_host_isolation_waived`'s own
    `target_of` docstring) -- callers waiving a HOST finding still write
    the clause on a NODE, matched inside `evaluate_host_isolation_waived`
    before this adapter ever runs, so `target` here is for report
    readability only, not a second waiver-matching key."""
    detail = v.detail or (f"user={v.user}" + (f" peer={v.peer}" if v.peer else ""))
    return FamilyGap(
        family="host",
        view="model",
        rule=v.rule,
        detail=detail,
        target=v.user,
        sub_target=v.sub_target,
    )


def _blast_radius_gaps(
    user: str, scenario_result: ScenarioResult
) -> tuple[FamilyGap, ...]:
    """Adapt one compromised-user scenario's REFUTED claims
    (`_scenarios.py::build_compromised_user_scenario`) into `FamilyGap`s
    under the fixed `"blast-radius"` view: a refuted `blast-radius:<user>:
    <node>` claim means the compromise reached OUTSIDE that user's own
    manifest slice -- exactly the failure HOST001/HOST002's structural
    proofs exist to prevent (T-0280). PROVED/EVIDENCED/ASSUMED claims
    contribute no gap; only REFUTED does, matching every other adapter in
    this module reporting failures, not passes."""
    return tuple(
        FamilyGap(
            family="host",
            view="blast-radius",
            rule="HOST-BLAST",
            detail=result.detail
            or f"compromised user {user!r} blast radius reaches beyond its "
            f"own nodes (claim {result.claim_id})",
            target=user,
        )
        for result in scenario_result.results
        if result.verdict == Verdict.REFUTED
    )


def _evaluate_family(
    model: KernelModel,
    view: str,
    catalog: tuple[WeaknessEntry, ...],
    out_of_scope: tuple[OutOfScopeEntry, ...],
    benign: tuple[BenignCapability, ...],
    views: dict[str, frozenset[str]],
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT001 + THREAT002 + THREAT003 over `model` against `view`,
    resolved against the FAMILY-SPECIFIC `views` table -- the same three
    calls `_threat.py::evaluate_threats` makes, reparameterized so a
    non-security family (whose views live in a separate table, e.g.
    `QUALITY_VIEWS`) can be evaluated without `evaluate_threats`'s
    hardcoded fallback to the module-global `VIEWS` shadowing it (zero new
    detection -- see module docstring)."""
    catalog_violations = check_catalog_completeness(view, catalog, out_of_scope, views)
    if catalog_violations.is_err:
        return Err(catalog_violations.danger_err)
    capability_violations = check_capability_completeness(model, catalog, benign)
    if capability_violations.is_err:
        return Err(capability_violations.danger_err)
    discharge_violations = check_discharge_completeness(model, catalog)
    if discharge_violations.is_err:
        return Err(discharge_violations.danger_err)
    return Ok(
        (
            *catalog_violations.danger_ok,
            *capability_violations.danger_ok,
            *discharge_violations.danger_ok,
        )
    )


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
# frob:tests tests/unit/strata/test_audit.py::TestExhaustiveness.test_clean_proved
# frob:tests tests/unit/strata/test_audit.py::TestVulnLitmus.test_refutes_gap_per_family
# frob:tests tests/unit/strata/test_audit.py::TestHardenedLitmus.test_hardened_clean
# frob:tests tests/unit/strata/test_audit.py::TestExhaustiveness.test_pii_gap_reported
# frob:tests tests/unit/strata/test_audit.py::TestExhaustiveness.test_lint_gap_reported
# frob:tests tests/unit/strata/test_audit.py::TestHostWiring.test_shared_model_gaps
# frob:tests tests/unit/strata/test_audit.py::TestHostWiring.test_hardened_model_proved
# frob:tests tests/unit/strata/test_audit.py::TestHostWiring.test_no_runs_as_no_gaps
# frob:waive TEST005 reason="Err branches need a deep StrataError; debt T-0160"
# frob:waive PERF004 reason="sorted() builds iterable once, not a re-sort (T-0283)"
def evaluate_exhaustiveness(
    model: KernelModel,
    *,
    security_views: tuple[str, ...] = DEFAULT_SECURITY_VIEWS,
    quality_views: tuple[str, ...] = DEFAULT_QUALITY_VIEWS,
    compliance_views: tuple[str, ...] = DEFAULT_COMPLIANCE_VIEWS,
    benign: tuple[BenignCapability, ...] = DEFAULT_BENIGN_CAPABILITIES,
) -> Result[AuditReport, StrataError]:
    """`frob sys audit`'s model-side entrypoint: the full three-part
    exhaustiveness conjunction (THREAT001-003 for security AND quality,
    COMPLIANCE001-002 for compliance) over `model` against every configured
    view, composed from the ALREADY-SHIPPED per-check functions -- zero new
    detection (module docstring). `benign` defaults to
    `DEFAULT_BENIGN_CAPABILITIES` (T-0150) so tier-2 `may` kinds with no
    CWE-catalog analog do not fail THREAT002 by default; a caller wanting
    the pre-T-0150 strict behavior passes `benign=()`. Fails closed: an
    unknown view name in any family propagates as
    `Err(StrataError.UnknownReference)` rather than being silently
    skipped, matching every other exhaustiveness check in this package."""
    gaps: list[FamilyGap] = []
    checked: list[str] = []

    for view in security_views:
        report = _evaluate_family(model, view, CWE_CATALOG, (), benign, VIEWS)
        if report.is_err:
            return Err(report.danger_err)
        gaps.extend(_threat_gaps("security", view, report.danger_ok))
        checked.append(f"security:{view}")

    for view in quality_views:
        report = _evaluate_family(
            model, view, QUALITY_CATALOG, QUALITY_OUT_OF_SCOPE, benign, QUALITY_VIEWS
        )
        if report.is_err:
            return Err(report.danger_err)
        gaps.extend(_threat_gaps("quality", view, report.danger_ok))
        checked.append(f"quality:{view}")

    for view in compliance_views:
        compliance_report = evaluate_compliance(model, view)
        if compliance_report.is_err:
            return Err(compliance_report.danger_err)
        gaps.extend(_compliance_gaps(view, compliance_report.danger_ok.violations))
        checked.append(f"compliance:{view}")

    pii_report = evaluate_pii(model)
    if pii_report.is_err:
        return Err(pii_report.danger_err)
    gaps.extend(_pii_gaps(pii_report.danger_ok.violations))
    checked.append("pii:model")

    lint_report = evaluate_lint(model)
    if lint_report.is_err:
        return Err(lint_report.danger_err)
    gaps.extend(_lint_gaps(lint_report.danger_ok.violations))
    checked.append("lint:model")

    fingerprint_report = check_fingerprint_catalog_drift(CVE_FINGERPRINTS)
    if fingerprint_report.is_err:
        return Err(fingerprint_report.danger_err)
    gaps.extend(_fingerprint_gaps(fingerprint_report.danger_ok))
    checked.append("cve-fingerprint:catalog")

    # T-0280: HOST001 (lateral) + HOST002 (vertical) movement-impossibility
    # proofs, folded in exactly like every other family above -- these were
    # previously built and sound (T-0256) but had ZERO caller reaching them
    # from `frob sys audit`, so a real repo could never see the verdict.
    # `evaluate_host_isolation_waived` already applies HOST001/HOST002's OWN
    # waiver channel internally (module docstring precedent, same as
    # `check_self_conformance` owning SYS100-102's channel) -- `.kept` is
    # already post-waiver, so it is folded straight into `gaps` here rather
    # than re-run through this function's own `apply_waivers` call below
    # (`_HOST_RULE_IDS` excludes both rule ids from that call's `in_scope`
    # for exactly this reason).
    host_report = evaluate_host_isolation_waived(model)
    if host_report.is_err:
        return Err(host_report.danger_err)
    host001_applied, host002_applied = host_report.danger_ok
    for host_applied in (host001_applied, host002_applied):
        gaps.extend(_host_isolation_gap(v) for v in host_applied.kept)
    checked.append("host:model")

    # T-0280: one auto-generated compromised-user red-team scenario per
    # `runs_as` service user declared anywhere in `model` -- the SAME
    # "desugar to an auto-generated scenario, then reuse `evaluate_
    # scenarios`" shape `_crash.py::_generate_crash_scenarios` already uses
    # for `on crash` contracts, so a real repo proves (or refutes) blast-
    # radius containment with zero manual scenario authoring.
    users = sorted(
        {
            manifest.runs_as
            for node in model.nodes
            if (manifest := host_manifest_for(node)) is not None
        }
    )
    for user in users:
        scenario = build_compromised_user_scenario(
            model, user, f"compromised-user:{user}"
        )
        if scenario.is_err:
            return Err(scenario.danger_err)
        scenario_model = model.model_copy(update={"scenarios": (scenario.danger_ok,)})
        scenario_results = evaluate_scenarios(scenario_model)
        if scenario_results.is_err:
            return Err(scenario_results.danger_err)
        for scenario_result in scenario_results.danger_ok:
            gaps.extend(_blast_radius_gaps(user, scenario_result))
        checked.append(f"host:blast-radius:{user}")

    # T-0174: apply every node's `waive` clause against this run's full gap
    # set before reporting -- a matched waiver moves its gap into `waived`
    # (still visible, never dropped); a waiver that matched nothing is
    # STALE and becomes a new SYSWAIVE002 gap under the "waiver" family so
    # drift fails the exhaustiveness conjunction rather than silently
    # going stale forever (`_waive.py` module docstring).
    applied = apply_waivers(
        model,
        gaps,
        rule_of=lambda g: g.rule,
        target_of=lambda g: g.target,
        # T-0174 REJECT round: THREAT002/THREAT003 fire once per
        # capability kind/CWE per node -- `FamilyGap.sub_target` already
        # carries it (`_threat_gaps`); every other family here is
        # single-instance-per-node and leaves `sub_target` `None`.
        sub_target_of=lambda g: g.sub_target,
        # T-0174: this call sees every THREAT/LINT/PII/compliance/
        # CVE-fingerprint finding -- everything EXCEPT SYS100-102 (owned by
        # `check_self_conformance`) and HOST001/HOST002 (owned by
        # `evaluate_host_isolation_waived`, T-0280) -- each of those owns
        # its own waiver channel (apply_waivers' `in_scope` docstring).
        # Excluding those rule ids here (rather than enumerating every rule
        # this call DOES own) keeps this predicate correct as new
        # gap-producing rule families are added -- a new rule id is in
        # scope here by default, exactly like `gaps` itself already is.
        in_scope=lambda rule: (
            rule
            not in (
                SYS_UNDECLARED_INTERFACE,
                SYS_STALE_DESIGN,
                SYS_UNMODELED_CODE,
                *_HOST_RULE_IDS,
            )
        ),
    )
    final_gaps = list(applied.kept)
    for stale in applied.stale:
        final_gaps.append(
            FamilyGap(
                family="waiver",
                view="model",
                rule=STALE_WAIVER_RULE,
                detail=stale_detail(stale),
                target=stale.node,
            )
        )
    # T-0280: HOST001/HOST002's OWN waiver-application pass (inside
    # `evaluate_host_isolation_waived`) already computed its own waived/
    # stale sets -- fold them in here so the audit report's `waived` and
    # `gaps` (via the "waiver" family stale entries) stay complete, without
    # asking the generic `apply_waivers` call above to redo work its
    # `in_scope` predicate deliberately excludes.
    for host_applied in (host001_applied, host002_applied):
        for stale in host_applied.stale:
            final_gaps.append(
                FamilyGap(
                    family="waiver",
                    view="model",
                    rule=STALE_WAIVER_RULE,
                    detail=stale_detail(stale),
                    target=stale.node,
                )
            )
    # T-0174: fold the waiver's reason/ticket into the reported gap's
    # `detail` -- `report.waived` must show WHY, never just THAT (module
    # docstring's "loud in output" requirement, mirrors `frob.gates`'s
    # `WaiverRef`-annotated `Violation.waived`).
    # T-0174 REJECT round: fold `wf.waiver.rule` (the RAW declared string,
    # e.g. "THREAT003:CWE-78") into the printed detail, not just
    # `wf.finding.rule` (the bare family) -- a reader must be able to see
    # the exact sub-target a waiver named, never just that SOME waiver on
    # this rule matched (module docstring's "no blanket waivers").
    waived_gaps = tuple(
        wf.finding.model_copy(
            update={
                "detail": (
                    f"{wf.finding.detail} -- WAIVED[{wf.waiver.rule}]: "
                    f"{wf.waiver.reason!r}"
                    + (f" (ticket {wf.waiver.ticket})" if wf.waiver.ticket else "")
                )
            }
        )
        for wf in applied.waived
    )
    # T-0280: HOST001/HOST002 findings suppressed by `evaluate_host_
    # isolation_waived`'s OWN waiver pass -- adapted + detail-folded the
    # identical way `waived_gaps` above folds every other family's.
    host_waived_gaps = tuple(
        _host_isolation_gap(wf.finding).model_copy(
            update={
                "detail": (
                    f"{_host_isolation_gap(wf.finding).detail} -- "
                    f"WAIVED[{wf.waiver.rule}]: {wf.waiver.reason!r}"
                    + (f" (ticket {wf.waiver.ticket})" if wf.waiver.ticket else "")
                )
            }
        )
        for host_applied in (host001_applied, host002_applied)
        for wf in host_applied.waived
    )
    waived_gaps = waived_gaps + host_waived_gaps

    _log.info(
        "audit: evaluated views=%d -> %d gap(s), %d waived, %d stale waiver(s)",
        len(checked),
        len(final_gaps),
        len(waived_gaps),
        len(applied.stale),
    )
    return Ok(
        AuditReport(
            views_checked=tuple(checked),
            gaps=tuple(final_gaps),
            waived=waived_gaps,
        )
    )


__all__ = [
    "DEFAULT_COMPLIANCE_VIEWS",
    "DEFAULT_QUALITY_VIEWS",
    "DEFAULT_SECURITY_VIEWS",
    "AuditReport",
    "FamilyGap",
    "evaluate_exhaustiveness",
]
