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

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import CodeBinding, bind_code
from ._compliance import (
    COMPLIANCE_OUT_OF_SCOPE,
    REGULATION_VIEWS,
    ComplianceViolation,
    evaluate_compliance,
)
from ._contention import RESOURCE_CONTENTION_RULES
from ._cve_fingerprint import (
    CVE_FINGERPRINTS,
    FingerprintViolation,
    check_fingerprint_catalog_drift,
)
from ._errors import StrataError
from ._host import host_manifest_for
from ._host_isolation import HostIsolationViolation, evaluate_host_isolation_waived
from ._lint import LintViolation, evaluate_lint
from ._mode_conformance import SYS_MODE_NONCONFORMANCE
from ._models import KernelModel, Verdict
from ._pii import PiiViolation, evaluate_pii
from ._reliability import RELIABILITY_RULES
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
    ALL_CATALOG,
    CWE_CATALOG,
    CWE_TOP_25_CATALOG,
    CWE_TOP_25_OUT_OF_SCOPE,
    CWE_TOP_25_VIEWS,
    DEFAULT_BENIGN_CAPABILITIES,
    QUALITY_CATALOG,
    QUALITY_OUT_OF_SCOPE,
    QUALITY_VIEWS,
    VIEWS,
    BenignCapability,
    OutOfScopeEntry,
    ThreatViolation,
    WeaknessEntry,
    _check_caught_by_integrity,
    check_capability_completeness,
    check_catalog_completeness,
    check_discharge_completeness,
)
from ._waive import (
    STALE_WAIVER_RULE,
    WaivedFinding,
    WaiverApplication,
    WaiverMatch,
    _stale_detail,
    apply_waivers,
)

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


#: T-0512 (strata audit G6): every security-family baseline view the
#: catalog module ships, regardless of whether `DEFAULT_SECURITY_VIEWS`
#: actually checks it by default -- the reference `_narrower_than_
#: baseline` diffs against so a narrower-than-full-baseline default run
#: is disclosed, never silently omitted. Kept local (not re-exported)
#: since it exists purely for that one disclosure computation; a caller
#: wanting the full security-family view set imports `VIEWS`/
#: `CWE_TOP_25_VIEWS` from `_threat.py` directly, the same way
#: `DEFAULT_SECURITY_VIEWS` itself is built.
_ALL_SECURITY_VIEWS: frozenset[str] = frozenset(VIEWS) | frozenset(CWE_TOP_25_VIEWS)


def _narrower_than_baseline(security_views: tuple[str, ...]) -> tuple[str, ...]:
    """T-0512: every baseline security view `_ALL_SECURITY_VIEWS` names
    that `security_views` (whatever a caller actually configured this run
    with -- `DEFAULT_SECURITY_VIEWS` unless overridden) does NOT include,
    sorted for determinism -- empty when the run is genuinely exhaustive
    over every view this repo's catalogs currently define. This is the
    disclosure `AuditReport.narrower_than_baseline` surfaces so a PROVED
    report can never silently mean "proved against less than the full
    catalog baseline" without saying so."""
    return tuple(sorted(_ALL_SECURITY_VIEWS - frozenset(security_views)))


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class AuditReport(BaseModel):
    """The full exhaustiveness conjunction's outcome across every configured
    view: `proved` iff `gaps` is empty. `views_checked` names exactly what
    was evaluated (family-qualified, e.g. `security:owasp-top-10`), so a
    clean report is auditable -- no view silently skipped. `narrower_
    than_baseline` (T-0512, strata audit G6) names every security-family
    baseline view the catalog module ships that THIS run did not check --
    empty for a genuinely exhaustive run, non-empty (e.g. `("cwe-top-25",)`
    for the as-shipped `DEFAULT_SECURITY_VIEWS`, which names only
    `owasp-top-10`) when a caller configured (or defaulted to) a narrower
    view set: `PROVED` with a non-empty `narrower_than_baseline` means
    "every view actually run held," never "every baseline view this repo
    defines held" -- a distinction the report itself must state, not
    leave the caller to infer."""

    model_config = ConfigDict(frozen=True)

    views_checked: tuple[str, ...] = ()
    gaps: tuple[FamilyGap, ...] = ()
    # T-0174: gaps suppressed by a matching `waive` clause -- kept here for
    # report visibility (never a silent drop, `_waive.py` module
    # docstring), separate from `gaps` so `proved` stays exactly "zero
    # UNWAIVED gaps."
    waived: tuple[FamilyGap, ...] = ()
    # frob:ticket T-0512
    narrower_than_baseline: tuple[str, ...] = ()

    # frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
    @property
    def proved(self) -> bool:
        """True iff every configured view's exhaustiveness conjunction held
        across all families -- zero named gaps anywhere. NOTE (T-0512):
        `proved` answers "did every view this run actually checked hold",
        not "did every baseline view the catalogs define hold" -- check
        `narrower_than_baseline` for the latter; a `True` `proved` next to
        a non-empty `narrower_than_baseline` is an honest, disclosed
        narrower-scope PROVED, not a false completeness claim."""
        return not self.gaps


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class GroupedGap(BaseModel):
    """One dedup group of `FamilyGap`s that are verbatim-identical except
    for `view` (T-0173: `frob sys audit` was printing an IDENTICAL WARNING
    block once per configured view whenever the same underlying gap held
    under every view, burying the genuinely per-view differences under
    repeated noise). `views` names every view the group fired under, in
    first-seen order; the underlying `AuditReport.gaps`/`waived` tuples are
    left untouched so `proved` and waiver matching keep evaluating the full,
    ungrouped gap set -- this is a presentation-layer collapse only."""

    model_config = ConfigDict(frozen=True)

    family: str
    rule: str
    detail: str
    target: str | None = None
    sub_target: str | None = None
    views: tuple[str, ...] = ()


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
# frob:tests tests/unit/strata/test_audit.py::TestGroupGaps.test_group_gaps_by_view
def group_gaps_by_view(gaps: tuple[FamilyGap, ...]) -> tuple[GroupedGap, ...]:
    """Collapse `gaps` into `GroupedGap`s: entries that are verbatim-
    identical on (family, rule, detail, target, sub_target) -- differing
    only in `view` -- are merged into one group carrying every view it
    fired under (T-0173). Order-preserving on first occurrence; a gap that
    fires under only one view still yields a single-view group, so
    genuinely distinct per-view gaps are never collapsed together."""
    order: list[tuple[str, str, str, str | None, str | None]] = []
    seen: dict[tuple[str, str, str, str | None, str | None], list[str]] = {}
    for gap in gaps:
        key = (gap.family, gap.rule, gap.detail, gap.target, gap.sub_target)
        if key not in seen:
            seen[key] = []
            order.append(key)
        seen[key].append(gap.view)
    return tuple(
        GroupedGap(
            family=family,
            rule=rule,
            detail=detail,
            target=target,
            sub_target=sub_target,
            views=tuple(seen[(family, rule, detail, target, sub_target)]),
        )
        for family, rule, detail, target, sub_target in order
    )


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
    binding: CodeBinding | None = None,
    root: Path | None = None,
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT001 + THREAT002 + THREAT003 over `model` against `view`,
    resolved against the FAMILY-SPECIFIC `views` table -- the same three
    calls `_threat.py::evaluate_threats` makes, reparameterized so a
    non-security family (whose views live in a separate table, e.g.
    `QUALITY_VIEWS`) can be evaluated without `evaluate_threats`'s
    hardcoded fallback to the module-global `VIEWS` shadowing it (zero new
    detection -- see module docstring).

    T-0171: THREAT002 (capability classification) is checked against
    `ALL_CATALOG` -- the union sink taxonomy across every family -- not
    the narrower per-family `catalog`, so a capability kind classified
    security-side (`CWE_CATALOG`) but absent from a quality-only catalog's
    vocabulary (`QUALITY_CATALOG`) is not misreported as unclassified when
    auditing a quality view (`_threat.py::ALL_CATALOG`'s comment). THREAT001
    (`catalog`/`out_of_scope`/`views`) and THREAT003 (`catalog`) stay
    family-scoped -- only which family's obligations a capability FIRES is
    per-family; whether the capability is classified AT ALL is not.

    `binding`/`root` (T-0630) are threaded into THREAT003's `check_
    discharge_completeness` call exactly like `_run_all_completeness_
    checks` (`_threat.py`) already threads them for `evaluate_threats` --
    optional, defaulting to `None` (design-level-only caller, no code-bound
    join), but `evaluate_exhaustiveness` (this module's own entrypoint)
    passes a real code tree whenever its own caller supplies one, so the
    fail-closed G1 stronger half actually engages on a real `frob sys
    audit` run instead of only in unit tests that construct a `CodeBinding`
    by hand."""
    catalog_violations = check_catalog_completeness(view, catalog, out_of_scope, views)
    if catalog_violations.is_err:
        return Err(catalog_violations.danger_err)
    capability_violations = check_capability_completeness(
        model, catalog, benign, taxonomy=ALL_CATALOG
    )
    if capability_violations.is_err:
        return Err(capability_violations.danger_err)
    discharge_violations = check_discharge_completeness(model, catalog, binding, root)
    if discharge_violations.is_err:
        return Err(discharge_violations.danger_err)
    return Ok(
        (
            *catalog_violations.danger_ok,
            *capability_violations.danger_ok,
            *discharge_violations.danger_ok,
        )
    )


def _threat_and_quality_gaps(
    model: KernelModel,
    security_views: tuple[str, ...],
    quality_views: tuple[str, ...],
    benign: tuple[BenignCapability, ...],
    binding: CodeBinding | None = None,
    root: Path | None = None,
) -> Result[tuple[list[FamilyGap], list[str]], StrataError]:
    """THREAT001-003 gaps for every security then quality view, in order.

    T-0512 (strata audit G6): a security-family `view` resolves against
    ONE of two, mutually exclusive views tables/catalogs -- `owasp-top-10`
    (`VIEWS`, `CWE_CATALOG` alone) or `cwe-top-25` (`CWE_TOP_25_VIEWS`,
    the COMBINED `CWE_CATALOG + CWE_TOP_25_CATALOG` catalog, T-0143's own
    "needs the wider union" rationale) -- decided by membership in
    `CWE_TOP_25_VIEWS` (today exactly `{"cwe-top-25"}`) so a caller who
    explicitly widens `security_views` to include `cwe-top-25` (clearing
    `AuditReport.narrower_than_baseline`, `_narrower_than_baseline` below)
    resolves correctly rather than failing closed against `VIEWS`, which
    has no such key.

    `binding`/`root` (T-0630) pass straight through to every `_evaluate_
    family` call, security and quality alike -- the G1 code-bound join is
    not security-specific, a quality-family ENDORSE boundary's predicate
    needs the exact same call-site proof."""
    gaps: list[FamilyGap] = []
    checked: list[str] = []

    for view in security_views:
        if view in CWE_TOP_25_VIEWS:
            report = _evaluate_family(
                model,
                view,
                CWE_CATALOG + CWE_TOP_25_CATALOG,
                CWE_TOP_25_OUT_OF_SCOPE,
                benign,
                CWE_TOP_25_VIEWS,
                binding,
                root,
            )
        else:
            report = _evaluate_family(
                model, view, CWE_CATALOG, (), benign, VIEWS, binding, root
            )
        if report.is_err:
            return Err(report.danger_err)
        gaps.extend(_threat_gaps("security", view, report.danger_ok))
        checked.append(f"security:{view}")

    for view in quality_views:
        report = _evaluate_family(
            model,
            view,
            QUALITY_CATALOG,
            QUALITY_OUT_OF_SCOPE,
            benign,
            QUALITY_VIEWS,
            binding,
            root,
        )
        if report.is_err:
            return Err(report.danger_err)
        gaps.extend(_threat_gaps("quality", view, report.danger_ok))
        checked.append(f"quality:{view}")

    return Ok((gaps, checked))


# frob:ticket T-0601
def _caught_by_gaps(
    known_rule_ids: frozenset[str],
    benign: tuple[BenignCapability, ...],
) -> Result[tuple[list[FamilyGap], list[str]], StrataError]:
    """THREAT006 (T-0382) gaps: `caught_by` integrity across every built-in
    `OutOfScopeEntry`/`BenignCapability` this module ships, security AND
    quality families' out-of-scope tuples plus the full `benign` set
    (`DEFAULT_BENIGN_CAPABILITIES` plus whatever the repo/caller adds) --
    model-independent (a catalog-level fact, like THREAT001), so this runs
    once per audit rather than once per view."""
    result = _check_caught_by_integrity(
        out_of_scope=CWE_TOP_25_OUT_OF_SCOPE + QUALITY_OUT_OF_SCOPE,
        benign=benign,
        known_rule_ids=known_rule_ids,
        catalog=ALL_CATALOG,
    )
    if result.is_err:
        return Err(result.danger_err)
    gaps = list(_threat_gaps("security", "caught_by", result.danger_ok))
    return Ok((gaps, ["security:caught_by"]))


def _compliance_pii_lint_fingerprint_gaps(
    model: KernelModel,
    compliance_views: tuple[str, ...],
    known_rule_ids: frozenset[str] = frozenset(),
) -> Result[tuple[list[FamilyGap], list[str]], StrataError]:
    """COMPLIANCE001-002, PII, lint, and CVE-fingerprint gaps, in order.
    `known_rule_ids` (T-0499) is threaded into `evaluate_compliance` so its
    COMPLIANCE004 `caught_by` check gets the same live gate-rule-id set
    THREAT006 does, instead of silently defaulting to empty. `COMPLIANCE_
    OUT_OF_SCOPE` (T-0503) is likewise threaded in as `out_of_scope` --
    mirroring `CWE_TOP_25_OUT_OF_SCOPE + QUALITY_OUT_OF_SCOPE` at
    `_caught_by_gaps` above -- so COMPLIANCE004 has a real, non-empty
    catalog to verify in production instead of trivially passing on an
    always-empty tuple."""
    gaps: list[FamilyGap] = []
    checked: list[str] = []

    for view in compliance_views:
        compliance_report = evaluate_compliance(
            model,
            view,
            out_of_scope=COMPLIANCE_OUT_OF_SCOPE,
            known_rule_ids=known_rule_ids,
        )
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

    return Ok((gaps, checked))


def _host_isolation_and_blast_radius_gaps(
    model: KernelModel,
) -> Result[
    tuple[
        list[FamilyGap],
        list[str],
        WaiverApplication[HostIsolationViolation],
        WaiverApplication[HostIsolationViolation],
    ],
    StrataError,
]:
    """HOST001/HOST002 gaps plus one compromised-user blast-radius scenario per
    `runs_as` service user, in order (T-0280)."""
    gaps: list[FamilyGap] = []
    checked: list[str] = []

    host_report = evaluate_host_isolation_waived(model)
    if host_report.is_err:
        return Err(host_report.danger_err)
    host001_applied, host002_applied = host_report.danger_ok
    for host_applied in (host001_applied, host002_applied):
        gaps.extend(_host_isolation_gap(v) for v in host_applied.kept)
    checked.append("host:model")

    blast_result = _blast_radius_gaps_per_user(model)
    if blast_result.is_err:
        return Err(blast_result.danger_err)
    blast_gaps, blast_checked = blast_result.danger_ok
    gaps.extend(blast_gaps)
    checked.extend(blast_checked)

    return Ok((gaps, checked, host001_applied, host002_applied))


def _blast_radius_gaps_per_user(
    model: KernelModel,
) -> Result[tuple[list[FamilyGap], list[str]], StrataError]:
    """One compromised-user blast-radius scenario per `runs_as`
    service user, in order.

    Nodes that declare host constructs (`owns`/`acl`/`unit`/`listens`)
    without a `runs_as` service-account claim have no real identity to
    scan a compromised-user scenario against -- `runs_as=None` is
    filtered out of the user set rather than treated as its own
    "compromised-user:None" scenario (frob:ticket T-1164)."""
    gaps: list[FamilyGap] = []
    checked: list[str] = []
    users = sorted(
        {
            manifest.runs_as
            for node in model.nodes
            if (manifest := host_manifest_for(node)) is not None
            and manifest.runs_as is not None
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

    return Ok((gaps, checked))


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
# frob:tests tests/unit/strata/test_audit.py::TestExhaustiveness.test_clean_proved
# frob:tests tests/unit/strata/test_audit.py::TestVulnLitmus.test_refutes_gap_per_family
# frob:tests tests/unit/strata/test_audit.py::TestHardenedLitmus.test_hardened_clean
# frob:tests tests/unit/strata/test_audit.py::TestExhaustiveness.test_pii_gap_reported
# frob:tests tests/unit/strata/test_audit.py::TestExhaustiveness.test_lint_gap_reported
# frob:tests tests/unit/strata/test_audit.py::TestHostWiring.test_shared_model_gaps
# frob:tests tests/unit/strata/test_audit.py::TestHostWiring.test_hardened_model_proved
# frob:tests tests/unit/strata/test_audit.py::TestHostWiring.test_no_runs_as_no_gaps
# frob:ticket T-0601
# frob:enforces CHK-GATE-HOST-BLAST
def evaluate_exhaustiveness(
    model: KernelModel,
    *,
    security_views: tuple[str, ...] = DEFAULT_SECURITY_VIEWS,
    quality_views: tuple[str, ...] = DEFAULT_QUALITY_VIEWS,
    compliance_views: tuple[str, ...] = DEFAULT_COMPLIANCE_VIEWS,
    benign: tuple[BenignCapability, ...] = DEFAULT_BENIGN_CAPABILITIES,
    known_rule_ids: frozenset[str] = frozenset(),
    root: Path | None = None,
) -> Result[AuditReport, StrataError]:
    """`frob sys audit`'s model-side entrypoint: the full three-part
    exhaustiveness conjunction (THREAT001-003 for security AND quality,
    COMPLIANCE001-002 for compliance) over `model` against every configured
    view, composed from the ALREADY-SHIPPED per-check functions -- zero new
    detection (module docstring). `benign` defaults to
    `DEFAULT_BENIGN_CAPABILITIES` (T-0150) so tier-2 `may` kinds with no
    CWE-catalog analog do not fail THREAT002 by default; a caller wanting
    the pre-T-0150 strict behavior passes `benign=()`. `known_rule_ids`
    (T-0382) is the live gate-rule-id set THREAT006's `caught_by`
    verification checks rule-id-shaped references against
    (`frob.gates.known_gate_rule_ids()`) -- defaults to empty (no rule-id
    reference can resolve) since this package cannot import `frob.gates`
    itself (`_threat.py::_check_caught_by_integrity`'s docstring). Fails
    closed: an unknown view name in any family propagates as
    `Err(StrataError.UnknownReference)` rather than being silently
    skipped, matching every other exhaustiveness check in this package.

    `root` (T-0630, docs/audits/strata.md G1 stronger half) is the repo
    root a real `frob sys audit` run always has in hand
    (`frob.app.sys_runner._resolve_design_root`) -- when given, this binds
    `model`'s `code=` globs against `root`'s actual tree
    (`_code_binding.py::bind_code`, the SAME join `check_self_conformance`
    already performs against this exact `root`) and threads the resulting
    `CodeBinding` into every THREAT003 discharge check below, so an ENDORSE
    boundary's `predicate` must name a call site OBSERVED in the guarded
    code, not merely resolve to an in-model claim. Omitted (`None`)
    preserves the pre-T-0630 model-only posture (a design review with no
    code tree in hand) -- `bind_code`'s own `Err(StrataError.
    AmbiguousCodeBinding)` propagates fail-closed rather than degrading to
    an unbound audit silently."""
    binding: CodeBinding | None = None
    if root is not None:
        bound = bind_code(model, root)
        if bound.is_err:
            return Err(bound.danger_err)
        binding = bound.danger_ok

    all_result = _collect_all_family_gaps(
        model,
        security_views,
        quality_views,
        compliance_views,
        benign,
        known_rule_ids,
        binding,
        root,
    )
    if all_result.is_err:
        return Err(all_result.danger_err)
    gaps, checked, host001_applied, host002_applied = all_result.danger_ok

    return _apply_exhaustiveness_waivers(
        model,
        gaps,
        checked,
        host001_applied,
        host002_applied,
        _narrower_than_baseline(security_views),
    )


def _collect_all_family_gaps(
    model: KernelModel,
    security_views: tuple[str, ...],
    quality_views: tuple[str, ...],
    compliance_views: tuple[str, ...],
    benign: tuple[BenignCapability, ...],
    known_rule_ids: frozenset[str] = frozenset(),
    binding: CodeBinding | None = None,
    root: Path | None = None,
) -> Result[
    tuple[
        list[FamilyGap],
        list[str],
        WaiverApplication[HostIsolationViolation],
        WaiverApplication[HostIsolationViolation],
    ],
    StrataError,
]:
    """Every family's gaps (threat/quality, compliance/pii/lint/
    fingerprint, caught_by, host), in order. `binding`/`root` (T-0630) pass
    through to `_threat_and_quality_gaps` only -- THREAT003 is the sole G1
    code-bound join in this assembly; compliance/pii/lint/host/caught_by
    have no code-binding half to wire."""
    gaps: list[FamilyGap] = []
    checked: list[str] = []

    family_result = _threat_and_quality_gaps(
        model, security_views, quality_views, benign, binding, root
    )
    if family_result.is_err:
        return Err(family_result.danger_err)
    family_gaps, family_checked = family_result.danger_ok
    gaps.extend(family_gaps)
    checked.extend(family_checked)

    caught_by_result = _caught_by_gaps(known_rule_ids, benign)
    if caught_by_result.is_err:
        return Err(caught_by_result.danger_err)
    caught_by_gaps, caught_by_checked = caught_by_result.danger_ok
    gaps.extend(caught_by_gaps)
    checked.extend(caught_by_checked)

    other_result = _compliance_pii_lint_fingerprint_gaps(
        model, compliance_views, known_rule_ids
    )
    if other_result.is_err:
        return Err(other_result.danger_err)
    other_gaps, other_checked = other_result.danger_ok
    gaps.extend(other_gaps)
    checked.extend(other_checked)

    host_section = _host_family_gaps_section(model)
    if host_section.is_err:
        return Err(host_section.danger_err)
    host_gaps, host_checked, host001_applied, host002_applied = host_section.danger_ok
    gaps.extend(host_gaps)
    checked.extend(host_checked)

    return Ok((gaps, checked, host001_applied, host002_applied))


def _host_family_gaps_section(
    model: KernelModel,
) -> Result[
    tuple[
        list[FamilyGap],
        list[str],
        WaiverApplication[HostIsolationViolation],
        WaiverApplication[HostIsolationViolation],
    ],
    StrataError,
]:
    """HOST001/HOST002 + blast-radius gaps, folded in like every other family."""
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
    return _host_isolation_and_blast_radius_gaps(model)


def _final_gaps_with_stale(
    applied: WaiverApplication[FamilyGap],
    host001_applied: WaiverApplication[HostIsolationViolation],
    host002_applied: WaiverApplication[HostIsolationViolation],
) -> list[FamilyGap]:
    """`applied.kept` plus a "waiver" family gap for every stale
    waiver, own + host families."""
    final_gaps = list(applied.kept)
    final_gaps.extend(_stale_waiver_gaps(applied.stale))
    # T-0280: HOST001/HOST002's OWN waiver-application pass (inside
    # `evaluate_host_isolation_waived`) already computed its own waived/
    # stale sets -- fold them in here so the audit report's `waived` and
    # `gaps` (via the "waiver" family stale entries) stay complete, without
    # asking the generic `apply_waivers` call above to redo work its
    # `in_scope` predicate deliberately excludes.
    for host_applied in (host001_applied, host002_applied):
        final_gaps.extend(_stale_waiver_gaps(host_applied.stale))
    return final_gaps


def _stale_waiver_gaps(stale_waivers: tuple[WaiverMatch, ...]) -> list[FamilyGap]:
    """A "waiver" family `FamilyGap` for every stale waiver in `stale_waivers`."""
    return [
        FamilyGap(
            family="waiver",
            view="model",
            rule=STALE_WAIVER_RULE,
            detail=_stale_detail(stale),
            target=stale.node,
        )
        for stale in stale_waivers
    ]


def _waived_gaps_with_host(
    applied: WaiverApplication[FamilyGap],
    host001_applied: WaiverApplication[HostIsolationViolation],
    host002_applied: WaiverApplication[HostIsolationViolation],
) -> tuple[FamilyGap, ...]:
    """Every waived gap with the waiver's reason/ticket folded into
    `detail`, own + host families."""
    # T-0174: fold the waiver's reason/ticket into the reported gap's
    # `detail` -- `report.waived` must show WHY, never just THAT (module
    # docstring's "loud in output" requirement, mirrors `frob.gates`'s
    # `WaiverRef`-annotated `Violation.waived`).
    # T-0174 REJECT round: fold `wf.waiver.rule` (the RAW declared string,
    # e.g. "THREAT003:CWE-78") into the printed detail, not just
    # `wf.finding.rule` (the bare family) -- a reader must be able to see
    # the exact sub-target a waiver named, never just that SOME waiver on
    # this rule matched (module docstring's "no blanket waivers").
    waived_gaps = tuple(_waived_detail(wf.finding, wf) for wf in applied.waived)
    # T-0280: HOST001/HOST002 findings suppressed by `evaluate_host_
    # isolation_waived`'s OWN waiver pass -- adapted + detail-folded the
    # identical way `waived_gaps` above folds every other family's.
    host_waived_gaps = tuple(
        _waived_detail(_host_isolation_gap(wf.finding), wf)
        for host_applied in (host001_applied, host002_applied)
        for wf in host_applied.waived
    )
    return waived_gaps + host_waived_gaps


def _waived_detail(finding: FamilyGap, wf: WaivedFinding) -> FamilyGap:
    """`finding` with the waiver's reason/ticket folded into
    `detail` (module docstring)."""
    return finding.model_copy(
        update={
            "detail": (
                f"{finding.detail} -- WAIVED[{wf.waiver.rule}]: {wf.waiver.reason!r}"
                + (f" (ticket {wf.waiver.ticket})" if wf.waiver.ticket else "")
            )
        }
    )


def _apply_gap_waivers(
    model: KernelModel, gaps: list[FamilyGap]
) -> WaiverApplication[FamilyGap]:
    """Apply every node's `waive` clause against `gaps`, excluding
    rules that own their own channel."""
    # T-0174: apply every node's `waive` clause against this run's full gap
    # set before reporting -- a matched waiver moves its gap into `waived`
    # (still visible, never dropped); a waiver that matched nothing is
    # STALE and becomes a new SYSWAIVE002 gap under the "waiver" family so
    # drift fails the exhaustiveness conjunction rather than silently
    # going stale forever (`_waive.py` module docstring).
    return apply_waivers(
        model,
        gaps,
        rule_of=lambda g: g.rule,
        target_of=lambda g: g.target,
        sub_target_of=lambda g: g.sub_target,
        in_scope=_gap_rule_in_scope,
    )


# frob:ticket T-1157
# frob:tests tests/unit/strata/test_audit.py::TestExhaustiveness.test_sys205_waiver_is_not_reported_stale_by_exhaustiveness_pass  # noqa: E501
def _gap_rule_in_scope(rule: str) -> bool:
    """Excludes rule ids that own their own waiver channel
    (SYS100-102, HOST001/HOST002, SYS200-203, SYS205, REL200/REL201/
    REL210/REL211)."""
    # T-0174: this predicate sees every THREAT/LINT/PII/compliance/
    # CVE-fingerprint finding -- everything EXCEPT SYS100-102 (owned by
    # `check_self_conformance`), HOST001/HOST002 (owned by
    # `evaluate_host_isolation_waived`, T-0280), SYS200-203 (T-0724:
    # owned by `check_resource_contention`'s own `apply_waivers` call,
    # `_contention.py::_apply_contention_waivers`), SYS205 (T-1061/T-1157:
    # owned by `check_mode_conformance`'s own `apply_waivers` call,
    # `_mode_conformance.py::check_mode_conformance`), and REL200/REL201/
    # REL210/REL211 (T-0640/T-0644: owned by `check_reliability_timeouts`/
    # `check_reliability_health`'s shared `apply_waivers` call,
    # `_reliability.py::_apply_reliability_waivers`) -- each of
    # those owns its own waiver channel (apply_waivers' `in_scope`
    # docstring). Without this exclusion, a legitimate `waive "SYS20X:..."`
    # (or, per T-0640, `waive "REL20X:..."`) clause was reported STALE
    # here (this gap set never contains a matching finding) even while
    # the owning check correctly matched and applied the SAME waiver in
    # its own pass -- a real cross-family collision, not a hypothetical
    # one (T-0724 review round surfaced it for SYS20X on frob's own
    # design/frob.strata; T-0640 hit the identical collision for REL200
    # on the SAME file's cache-fill waivers; T-1157 hit the identical
    # collision for SYS205 mode-conformance waivers on the SAME file's
    # `tickets_ledger` resource). Excluding those rule ids here (rather
    # than enumerating every rule this call DOES own) keeps this
    # predicate correct as new gap-producing rule families are added --
    # a new rule id is in scope here by default, exactly like `gaps`
    # itself already is.
    return rule not in (
        SYS_UNDECLARED_INTERFACE,
        SYS_STALE_DESIGN,
        SYS_UNMODELED_CODE,
        SYS_MODE_NONCONFORMANCE,
        *_HOST_RULE_IDS,
        *RESOURCE_CONTENTION_RULES,
        *RELIABILITY_RULES,
    )


def _apply_exhaustiveness_waivers(
    model: KernelModel,
    gaps: list[FamilyGap],
    checked: list[str],
    host001_applied: WaiverApplication[HostIsolationViolation],
    host002_applied: WaiverApplication[HostIsolationViolation],
    narrower_than_baseline: tuple[str, ...] = (),
) -> Result[AuditReport, StrataError]:
    """Apply every node's `waive` clause to `gaps`, fold host
    waivers/stale, assemble the report. `narrower_than_baseline` (T-0512)
    passes straight through from `evaluate_exhaustiveness`'s caller-
    configured `security_views` -- a waiver never suppresses a NEVER-RUN
    view's absence, only a fired finding, so this disclosure is untouched
    by waiver application."""
    applied = _apply_gap_waivers(model, gaps)
    final_gaps = _final_gaps_with_stale(applied, host001_applied, host002_applied)
    waived_gaps = _waived_gaps_with_host(applied, host001_applied, host002_applied)

    _log.info(
        "audit: evaluated views=%d -> %d gap(s), %d waived, %d stale waiver(s)%s",
        len(checked),
        len(final_gaps),
        len(waived_gaps),
        len(applied.stale),
        f", narrower_than_baseline={narrower_than_baseline}"
        if narrower_than_baseline
        else "",
    )
    return Ok(
        AuditReport(
            views_checked=tuple(checked),
            gaps=tuple(final_gaps),
            waived=waived_gaps,
            narrower_than_baseline=narrower_than_baseline,
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
