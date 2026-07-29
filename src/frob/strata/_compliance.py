"""strata obligation catalog phase F (compliance): `std.compliance` --
COPPA/GDPR/HIPAA regulatory obligations + privacy-policy-as-claims reverse
audit (docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance,
T-0109/T-0116).

A fifth catalog family alongside security/performance/reliability/
compatibility (docs/strata/threat.md#beyond-security-the-anti-pattern-
families): same obligation/discharge/exhaustiveness structure as
`_threat.py`'s `std.cwe`, but the precondition vocabulary is data-subject
tags and jurisdiction scope rather than a `may` capability kind, and several
mitigations are structural (a boundary, a revocation edge, a declared
attribute) rather than code.

**Data-subject tags** (docs/strata/threat.md#compliance): a collection
`Flow`'s `attrs` carry `subject:child`, `subject:unknown-age`,
`subject:health`, `subject:biometric`, `subject:financial`, or
`basis:<consent|contract|legitimate-interest>`; a Pii-holding `Node`'s
`attrs` carry `jurisdiction:eu-resident` / `jurisdiction:ca-resident`,
`retention=<value><unit>`, `covered-party` (HIPAA BAA-satisfied),
`exposure:public-web` (the node is reachable from the open web -- GDPR
art.13/CCPA Sec.1798.100 notice-at-collection precondition), or
`privacy-policy` (the node's data practices are covered by a published
notice -- PRIVACY-NOTICE's mitigation). This is opaque-string vocabulary
on the existing `attrs` tuples (charter law 1: no new kernel primitive),
the same convention `_claims.py`'s `skew=`/`growth=` prefixes and
`_secrets.py`'s `attrs=("revocation",)` already use.

Each regulation's discharge REUSES existing kernel machinery rather than
inventing a parallel one (docs/strata/threat.md#compliance, "THE SAME
rule"): COPPA is a `NoFlow` closure query (any `Boundary` on the collection
flow blocks the influence path exactly like every other unendorsed-flow
refusal, `_facts.py::FactBase.reachable(through_barriers=False)`); GDPR
erasure is a revocation-edge presence check, the identical convention
`_secrets.py::_secret_flows`'s `attrs=("revocation",)` edge already
establishes; data retention is the age-collapse (`_facts.py::worst_age`,
T-0065) against a declared bound, the same machinery `_claims.py::
_eval_bound`'s AGE metric uses. Lawful basis, HIPAA BAA, and minimization
have no existing detector to reuse -- they are new, small structural
predicates over `attrs` and outgoing-flow presence.

An obligation is auto-instantiated (no author-written claim required,
mirroring `_secrets.py::elaborate_secret`'s auto-generated `SetEquality`)
UNLESS the model already declares a `Claim` named `compliance:<reg-id>:
<target-id>` -- an author may override the structural check with an
explicit `assume`, which (per the charter's closing compliance paragraph)
MUST carry `owner` + `review`, since "regulations change, so the staleness
bound matters more here than anywhere."
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.registry import DispositionKind, RegistryEntry, load_registry_dir

from ._errors import StrataError
from ._facts import FactBase, build_facts
from ._models import BoundaryDirection, Flow, KernelModel, Node, Quantity

#: `_threat.py`'s `CAUGHT_BY_NONE_MARKER`/`_caught_by_unresolved_tokens`
#: (T-0382) are reused (not duplicated) below, but only via a LOCAL import
#: inside `_check_regulation_caught_by_integrity` -- a module-level import
#: here would cycle: `frob.strata.__init__` -> `_atomic` -> `_elaborate` ->
#: `_infra` -> `_pii` -> `_compliance` (this module) -> `_threat` ->
#: `_effects` -> `frob.vet` -> `frob.gates` -> `frob.gates._pii_structural`
#: -> `frob.strata._pii` (still mid-import, `PII_CATEGORIES` not yet
#: defined). `_threat.py` itself is fully initialized by the time any
#: caller actually invokes this function, so the local import is safe.

_log = get_logger(__name__)

#: Flow/Node attr prefixes carrying compliance tags (module docstring).
_SUBJECT_PREFIX = "subject:"
_JURISDICTION_PREFIX = "jurisdiction:"
_BASIS_PREFIX = "basis:"
_RETENTION_PREFIX = "retention="
_COVERED_PARTY = "covered-party"
_REVOCATION_ATTR = "revocation"
_EXPOSURE_PREFIX = "exposure:"
_PRIVACY_POLICY_ATTR = "privacy-policy"


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
# frob:doc docs/guides/extending/compliance-registry.md#compliance-registry
class RegulationEntry(BaseModel):
    """One `std.compliance` catalog entry: a conditional regulatory duty,
    scoped to the jurisdictions it binds (docs/strata/threat.md#compliance,
    "Jurisdiction scope"). `family` is always `"compliance"`, mirroring
    `WeaknessEntry.family` so a caller that groups catalog entries by
    family (per-family exhaustiveness, threat.md#beyond-security) treats
    this catalog identically to `std.cwe`."""

    model_config = ConfigDict(frozen=True)

    id: str  # e.g. "COPPA", "GDPR-ERASURE"
    title: str
    cite: str  # authoritative statute/regulation url, never hand-transcribed
    family: str = "compliance"
    jurisdictions: tuple[str, ...] = ()  # empty = binds everywhere
    mitigation: str = ""


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
class OutOfScopeRegulation(BaseModel):
    """A baseline regulation id explicitly excluded from the catalog.

    Unlike `_threat.py::OutOfScopeEntry`, `owner` and `review` are
    mandatory: the charter's compliance closing paragraph requires every
    cited exclusion to carry legal ownership + a review date, since
    regulations change underneath a stale exclusion (docs/strata/
    threat.md#compliance, "Exhaustiveness for compliance"). `caught_by`
    (T-0381) is likewise mandatory: an exclusion without a named
    compensating control (the gate/rule/mechanism -- or legal process --
    that catches the excused regulation elsewhere) is an unaccounted-for
    gap, not an honest exclusion."""

    model_config = ConfigDict(frozen=True)

    id: str
    reason: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    review: str  # ISO date
    caught_by: str = Field(min_length=1)


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
# The charter's compliance obligations table, transcribed with authoritative
# citations (COPPA/GDPR/HIPAA); the pinned/digest-verified ingestion the
# CWE-catalog docstring defers is the same follow-up here (out of scope,
# noted as a cut not silently dropped).
COMPLIANCE_CATALOG: tuple[RegulationEntry, ...] = (
    RegulationEntry(
        id="COPPA",
        title="No data collection from underage users without verifiable "
        "parental consent",
        cite="https://www.ftc.gov/legal-library/browse/rules/"
        "childrens-online-privacy-protection-rule-coppa",
        jurisdictions=("us",),
        mitigation="age_gate_boundary",
    ),
    RegulationEntry(
        id="GDPR-ERASURE",
        title="Right to erasure (right to be forgotten)",
        cite="https://gdpr-info.eu/art-17-gdpr/",
        jurisdictions=("eu",),
        mitigation="revocation_edge",
    ),
    RegulationEntry(
        id="GDPR-RETENTION",
        title="Storage limitation -- data kept no longer than necessary",
        cite="https://gdpr-info.eu/art-5-gdpr/",
        jurisdictions=("eu",),
        mitigation="age_bound",
    ),
    RegulationEntry(
        id="GDPR-BASIS",
        title="Lawful basis required for processing personal data",
        cite="https://gdpr-info.eu/art-6-gdpr/",
        jurisdictions=("eu",),
        mitigation="declared_basis",
    ),
    RegulationEntry(
        id="HIPAA-BAA",
        title="PHI disclosed to a non-covered party requires a Business "
        "Associate Agreement",
        cite="https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/"
        "business-associates/index.html",
        jurisdictions=("us",),
        mitigation="baa_attestation",
    ),
    RegulationEntry(
        id="MINIMIZATION",
        title="Data minimization -- collect no field never put to use",
        cite="https://gdpr-info.eu/art-5-gdpr/",
        jurisdictions=(),  # a general good-practice duty, not jurisdiction-scoped
        mitigation="drop_or_justify",
    ),
    RegulationEntry(
        id="PRIVACY-NOTICE",
        title="Notice at collection -- a public-facing collection point "
        "handling personal data must have a published privacy notice "
        "(GDPR art.13 notice obligation; see also CCPA Cal. Civ. Code "
        "Sec.1798.100 notice-at-collection)",
        cite="https://gdpr-info.eu/art-13-gdpr/",
        jurisdictions=(),  # public-web exposure is not jurisdiction-scoped
        mitigation="privacy_policy_attestation",
    ),
)

# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
#: Baseline VIEWS: the regulation id set a selected view holds the catalog
#: to (mirrors `_threat.py::VIEWS`). `all-regulations` is the union;
#: per-jurisdiction views let a caller prove exhaustiveness against just
#: the statutes its deployment actually touches (docs/strata/threat.md
#: #compliance, "Exhaustiveness for compliance is per-regulation against a
#: cited statute baseline").
REGULATION_VIEWS: dict[str, frozenset[str]] = {
    "all-regulations": frozenset(entry.id for entry in COMPLIANCE_CATALOG),
    "us-coppa": frozenset({"COPPA"}),
    "eu-gdpr": frozenset({"GDPR-ERASURE", "GDPR-RETENTION", "GDPR-BASIS"}),
    "us-hipaa": frozenset({"HIPAA-BAA"}),
}


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
# frob:ticket T-0503
#: T-0503: the production `OutOfScopeRegulation` catalog -- mirrors
#: `_threat.py::CWE_TOP_25_OUT_OF_SCOPE`/`QUALITY_OUT_OF_SCOPE` for the
#: compliance family (module docstring's "same obligation/discharge/
#: exhaustiveness structure as `_threat.py`"). Before this, no module-level
#: `OutOfScopeRegulation` tuple existed anywhere, so `evaluate_compliance`'s
#: production callsite (`_audit.py::_compliance_pii_lint_fingerprint_gaps`)
#: always threaded an empty `out_of_scope=()`, making COMPLIANCE004 (`caught_
#: by` integrity) vacuous in production regardless of `known_rule_ids`
#: threading (T-0499's own Done report flagged this as a distinct,
#: not-folded-in gap). Each entry names a regulation the baseline catalog
#: does not model plus the real compensating control that catches it
#: elsewhere -- a fabricated or typo'd `caught_by` here is exactly the case
#: COMPLIANCE004 exists to refuse.
COMPLIANCE_OUT_OF_SCOPE: tuple[OutOfScopeRegulation, ...] = (
    # T-1246 re-review (2026-07-29): T-1242 landed exposure:public-web and
    # T-1314 landed PRIVACY-NOTICE (mitigation privacy_policy_attestation)
    # into COMPLIANCE_CATALOG. PRIVACY-NOTICE's notice-at-collection duty
    # now PARTIALLY discharges CMPL-CCPA-CORE-RIGHTS's right-to-know
    # component (both are the same "a public collection point must
    # disclose what it collects" obligation -- PRIVACY-NOTICE's own
    # RegulationEntry cite already names CCPA Cal. Civ. Code Sec.1798.100
    # notice-at-collection as a see-also). Right-to-delete has NO
    # matching coverage: GDPR-ERASURE only fires on a `revocation` edge in
    # a GDPR jurisdiction, and CCPA carries no separate CA-specific
    # consumer-deletion-request primitive. This out_of_scope entry is
    # therefore NOT retired -- it is narrowed and reaffirmed: still
    # correct for right-to-delete, no longer the whole story for
    # right-to-know now that PRIVACY-NOTICE exists. Review date extended;
    # a future ticket may split CCPA-CORE-RIGHTS's disposition into a
    # real handled_by (right-to-know, via PRIVACY-NOTICE) plus a narrower
    # out_of_scope (right-to-delete only) once the registry-row-level
    # split machinery exists to express partial coverage per row.
    OutOfScopeRegulation(
        id="CCPA",
        reason="the kernel carries GDPR's subject/jurisdiction/retention "
        "vocabulary (subject:*, jurisdiction:*, retention=) but has no "
        "separate California-specific consumer-request primitive "
        "(right-to-delete request tracking) distinct from GDPR-ERASURE/"
        "GDPR-RETENTION already in COMPLIANCE_CATALOG -- adding one would "
        "duplicate rather than extend the existing model. Right-to-know/"
        "notice-at-collection is NO LONGER wholly out of scope: T-1314's "
        "PRIVACY-NOTICE RegulationEntry (privacy_policy_attestation) "
        "discharges the same notice obligation CCPA's right-to-know rests "
        "on for any exposure:public-web collection point -- this entry now "
        "covers only the right-to-delete gap, re-reviewed under T-1246",
        owner="logan",
        review="2027-07-29",
        caught_by="right-to-delete: the structural PII field detector "
        "(PII010) flags any PII-shaped field regardless of jurisdiction, "
        "compensating for the missing CA-specific request-tracking model "
        "at the code level. right-to-know/notice: PRIVACY-NOTICE "
        "(COMPLIANCE_CATALOG, T-1314) now directly enforces this via "
        "SELFAUDIT001/evaluate_compliance, not merely PII010's fallback",
    ),
)


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
class ComplianceViolation(BaseModel):
    """One COMPLIANCE001-003 finding: a rule id, the firing regulation id,
    the firing target (flow or node id), and a human detail. Mirrors
    `_threat.py::ThreatViolation`'s shape so a caller merging both reports
    (`frob sys audit`, threat.md#the-exhaustiveness-proof-the-point) treats
    every family identically."""

    model_config = ConfigDict(frozen=True)

    rule: str  # COMPLIANCE001 catalog | COMPLIANCE002 discharge | COMPLIANCE003 policy
    regulation: str = ""
    target: str | None = None
    detail: str = ""


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
class ComplianceReport(BaseModel):
    """Every COMPLIANCE001-003 violation, in rule-then-regulation-then-target order."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[ComplianceViolation, ...] = ()


def _catalog_violation(view: str, reg_id: str) -> ComplianceViolation:
    """COMPLIANCE001 violation helper: deny-by-default unaddressed regulation."""
    _log.warning(
        "compliance: COMPLIANCE001 %s has no catalog or out-of-scope entry", reg_id
    )
    return ComplianceViolation(
        rule="COMPLIANCE001",
        regulation=reg_id,
        detail=f"baseline view {view!r} names {reg_id} with no catalog "
        "or out-of-scope entry",
    )


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
# frob:enforces CHK-GATE-COMPLIANCE001
# frob:enforces CHK-GATE-COMPLIANCE004
def check_regulation_catalog_completeness(
    view: str,
    catalog: tuple[RegulationEntry, ...] = COMPLIANCE_CATALOG,
    out_of_scope: tuple[OutOfScopeRegulation, ...] = (),
    views: dict[str, frozenset[str]] | None = None,
) -> Result[tuple[ComplianceViolation, ...], StrataError]:
    """COMPLIANCE001: every regulation id the selected `view` names has a
    `RegulationEntry` or an `OutOfScopeRegulation` (which itself requires
    `owner`+`review`, enforced by the model). Fails closed on an unknown
    `view` name (mirrors `_threat.py::check_catalog_completeness`)."""
    view_table = views if views is not None else REGULATION_VIEWS
    members = view_table.get(view)
    if members is None:
        _log.error("compliance: unknown baseline view %r", view)
        return Err(StrataError.UnknownReference)

    cataloged = {entry.id for entry in catalog}
    excused = {entry.id for entry in out_of_scope}
    ordered_members = sorted(members)
    violations = [
        _catalog_violation(view, reg_id)
        for reg_id in ordered_members
        if reg_id not in cataloged and reg_id not in excused
    ]
    return Ok(tuple(violations))


def _regulation_caught_by_violation(
    reg_id: str, caught_by: str, unresolved: frozenset[str]
) -> ComplianceViolation:
    """COMPLIANCE004 violation helper: an `OutOfScopeRegulation.caught_by`
    names a rule id that resolves to no real registered control -- mirrors
    `_threat.py::_caught_by_violation` (THREAT006) for the compliance
    family; deny-by-default, a fabricated reference is worse than an
    honest `CAUGHT_BY_NONE_MARKER` disclosure."""
    named = ", ".join(sorted(unresolved))
    _log.warning(
        "compliance: COMPLIANCE004 %s caught_by %r references unknown control(s): %s",
        reg_id,
        caught_by,
        named,
    )
    return ComplianceViolation(
        rule="COMPLIANCE004",
        regulation=reg_id,
        detail=f"{reg_id} caught_by {caught_by!r} references unknown "
        f"control(s) that do not exist: {named}",
    )


# frob:tests tests/unit/strata/test_compliance.py::TestRegulationCaughtByIntegrity.test_caught_by_naming_absent_control_is_refused  # noqa: E501
# frob:tests tests/unit/strata/test_compliance.py::TestRegulationCaughtByIntegrity.test_caught_by_naming_present_control_discharges  # noqa: E501
# frob:ticket T-0601
def _check_regulation_caught_by_integrity(
    out_of_scope: tuple[OutOfScopeRegulation, ...] = (),
    known_rule_ids: frozenset[str] = frozenset(),
) -> Result[tuple[ComplianceViolation, ...], StrataError]:
    """COMPLIANCE004 (T-0382): every `OutOfScopeRegulation.caught_by` that
    names a rule-id-shaped token must reference a control that actually
    exists in `known_rule_ids` (the live gate-rule-id set) -- a typo'd or
    fabricated reference is a violation, existence AND (via `known_rule_
    ids` being the set of rule ids a real Violation-producing gate can
    emit) efficacy, not just a registered-looking string. An honest
    `"none -- ..."` `caught_by` (`CAUGHT_BY_NONE_MARKER`) never fails this
    check -- it is already declaring the gap. Mirrors `_threat.py::
    _check_caught_by_integrity` (THREAT006) exactly, reusing its token-
    resolution helper (`_caught_by_unresolved_tokens`) rather than
    duplicating the regex/logic (imported locally -- module docstring
    above explains why a top-level import cycles). `known_rule_ids`
    defaults to empty (fail closed: no rule-id-shaped reference can
    resolve) since this package cannot import `frob.gates` itself, same
    rationale as THREAT006's own docstring."""
    from ._threat import CAUGHT_BY_NONE_MARKER, _caught_by_unresolved_tokens

    violations: list[ComplianceViolation] = []
    for entry in out_of_scope:
        if entry.caught_by.strip().lower().startswith(CAUGHT_BY_NONE_MARKER):
            continue
        unresolved = _caught_by_unresolved_tokens(entry.caught_by, known_rule_ids)
        if unresolved:
            violations.append(
                _regulation_caught_by_violation(entry.id, entry.caught_by, unresolved)
            )
    return Ok(tuple(violations))


def _has_subject_tag(attrs: tuple[str, ...], tag: str) -> bool:
    """Whether `attrs` carries `subject:<tag>` (module docstring vocabulary)."""
    return f"{_SUBJECT_PREFIX}{tag}" in attrs


def _has_jurisdiction(attrs: tuple[str, ...], jurisdiction: str) -> bool:
    """Whether `attrs` carries `jurisdiction:<jurisdiction>`."""
    return f"{_JURISDICTION_PREFIX}{jurisdiction}" in attrs


def _has_exposure(attrs: tuple[str, ...], exposure: str) -> bool:
    """Whether `attrs` carries `exposure:<exposure>` (module docstring)."""
    return f"{_EXPOSURE_PREFIX}{exposure}" in attrs


def _retention_limit(attrs: tuple[str, ...]) -> Quantity | None:
    """A node's declared `retention=<value><unit>` bound, parsed, or None."""
    for attr in attrs:
        if attr.startswith(_RETENTION_PREFIX):
            raw = attr[len(_RETENTION_PREFIX) :]
            for cut in range(len(raw), 0, -1):
                value_part, unit_part = raw[:cut], raw[cut:]
                try:
                    return Quantity(value=float(value_part), unit=unit_part)
                except Exception:
                    continue
            _log.warning("compliance: malformed retention attr %r", attr)
            return None
    return None


def _pii_or_above(model: KernelModel, label: str) -> bool:
    """Whether `label` sits at or above `Pii` in the model's label lattice."""
    result = model.labels.leq("Pii", label)
    return bool(result.is_ok and result.danger_ok)


def _claim_override(
    model: KernelModel, claim_id: str
) -> tuple[bool, ComplianceViolation | None]:
    """Whether an author-written `Claim` overrides the auto-instantiated
    structural check for `claim_id` (module docstring: assume must carry
    owner + review). Returns `(overridden, violation_if_malformed)`."""
    claim = next((c for c in model.claims if c.id == claim_id), None)
    if claim is None:
        return False, None
    if not claim.assumed:
        return False, None  # an asserted claim does not bypass the structural check
    if claim.owner is None or claim.review is None:
        return True, ComplianceViolation(
            rule="COMPLIANCE002",
            target=claim_id,
            detail=f"claim {claim_id!r} is assumed with no owner/review date -- "
            "regulations change, staleness bound is mandatory here",
        )
    return True, None


def _coppa_boundary_violation(flow: Flow) -> ComplianceViolation:
    """The COMPLIANCE002 violation for a COPPA flow with no age-gate boundary."""
    _log.warning(
        "compliance: COPPA fired on flow %s (%s -> %s), no age-gate boundary",
        flow.id,
        flow.src,
        flow.dst,
    )
    return ComplianceViolation(
        rule="COMPLIANCE002",
        regulation="COPPA",
        target=flow.id,
        detail=f"collection flow {flow.id} ({flow.src} -> {flow.dst}) "
        "from an under-13/unknown-age subject reaches a Pii store "
        "with no age-gate/parental-consent boundary",
    )


def _coppa_flow_violations(
    model: KernelModel,
    flow: Flow,
    boundary_flows: set[str],
    node_ids: set[str],
) -> tuple[ComplianceViolation, ...]:
    """COPPA per-flow check body: 0-2 violations for one flow (malformed
    override, then missing age-gate boundary), in that order."""
    if not (
        _has_subject_tag(flow.attrs, "child")
        or _has_subject_tag(flow.attrs, "unknown-age")
    ):
        return ()
    if not _pii_or_above(model, flow.label):
        return ()
    if flow.dst not in node_ids:
        return ()
    claim_id = f"compliance:COPPA:{flow.id}"
    overridden, malformed = _claim_override(model, claim_id)
    violations: list[ComplianceViolation] = []
    if malformed is not None:
        violations.append(malformed)
    if overridden:
        return tuple(violations)
    if flow.id not in boundary_flows:
        violations.append(_coppa_boundary_violation(flow))
    return tuple(violations)


def _check_coppa(model: KernelModel) -> tuple[ComplianceViolation, ...]:
    """COPPA: a collection flow tagged `subject:child`/`subject:unknown-age`
    into a Pii-or-above store with no ENDORSE `Boundary` on that flow is
    `noflow(child -> PiiStore)` REFUTED -- pure closure, reusing the
    existing boundary-blocks-reachability rule (docs/strata/threat.md
    #compliance), but scoped to `BoundaryDirection.ENDORSE` specifically:
    the charter (threat.md:182) names "an age-gate ENDORSEMENT boundary"
    as the mitigation, and `FactBase.reachable(through_barriers=False)`
    treats ANY boundary (endorse or declassify) as blocking, so a bare
    presence check would let an unrelated DECLASSIFY on the same flow
    silently discharge COPPA -- the T-0113 any-boundary lesson. Whether
    the `predicate` text must additionally name consent/age-gate
    specifically (vs. direction alone being sufficient) is left as a
    phase-B/C tightening -- the charter's capability/sink-taxonomy
    precedent (`_threat.py` module docstring) already defers predicate-
    text semantics past phase A, so direction is the phase-A bar here
    too, consistent with the rest of this catalog."""
    boundary_flows = {
        b.flow_id for b in model.boundaries if b.direction is BoundaryDirection.ENDORSE
    }
    node_ids = {n.id for n in model.nodes}
    violations: list[ComplianceViolation] = []
    for flow in sorted(model.flows, key=lambda f: f.id):
        violations.extend(_coppa_flow_violations(model, flow, boundary_flows, node_ids))
    return tuple(violations)


def _revoked_nodes(model: KernelModel) -> set[str]:
    """Node ids touched by a flow carrying the revocation attr (one pass
    over flows, so the caller's node loop stays a plain membership test --
    charter: no accidental O(nodes*flows))."""
    revoked_nodes: set[str] = set()
    for flow in model.flows:
        if _REVOCATION_ATTR in flow.attrs:
            revoked_nodes.add(flow.src)
            revoked_nodes.add(flow.dst)
    return revoked_nodes


def _erasure_node_violations(
    model: KernelModel, node: Node, revoked_nodes: set[str]
) -> tuple[ComplianceViolation, ...]:
    """GDPR-ERASURE per-node check body: 0-2 violations for one node."""
    if not (_has_jurisdiction(node.attrs, "eu-resident") and node.clearance):
        return ()
    if not _pii_or_above(model, node.clearance):
        return ()
    claim_id = f"compliance:GDPR-ERASURE:{node.id}"
    overridden, malformed = _claim_override(model, claim_id)
    violations: list[ComplianceViolation] = []
    if malformed is not None:
        violations.append(malformed)
    if overridden:
        return tuple(violations)
    if node.id not in revoked_nodes:
        _log.warning(
            "compliance: GDPR-ERASURE fired on store %s, no revocation edge",
            node.id,
        )
        violations.append(
            ComplianceViolation(
                rule="COMPLIANCE002",
                regulation="GDPR-ERASURE",
                target=node.id,
                detail=f"eu-resident Pii store {node.id} has no declared "
                "deletion/revocation path",
            )
        )
    return tuple(violations)


def _check_erasure(model: KernelModel) -> tuple[ComplianceViolation, ...]:
    """GDPR right to erasure: an `eu-resident`-tagged Pii-or-above store has
    no flow carrying `attrs=("revocation", ...)` touching it -- the SAME
    revocation-edge convention `_secrets.py::_secret_flows` establishes
    (docs/strata/threat.md#compliance)."""
    revoked_nodes = _revoked_nodes(model)
    violations: list[ComplianceViolation] = []
    for node in sorted(model.nodes, key=lambda n: n.id):
        violations.extend(_erasure_node_violations(model, node, revoked_nodes))
    return tuple(violations)


def _retention_dim_violation(node: Node, limit: Quantity) -> ComplianceViolation:
    """The COMPLIANCE002 violation for a non-time retention bound unit."""
    return ComplianceViolation(
        rule="COMPLIANCE002",
        regulation="GDPR-RETENTION",
        target=node.id,
        detail=f"{node.id} retention bound {limit.value}{limit.unit} "
        "is not a time unit",
    )


def _retention_age_violation(
    node: Node, base: FactBase, limit: Quantity
) -> ComplianceViolation | None:
    """The COMPLIANCE002 violation when `node`'s worst-case age exceeds `limit`."""
    age, _path = base.worst_age(node.id)
    limit_base = limit.base_value().danger_ok
    if age == float("inf") or age > limit_base:
        _log.warning(
            "compliance: GDPR-RETENTION fired on store %s, worst age %s > limit %s",
            node.id,
            age,
            limit_base,
        )
        return ComplianceViolation(
            rule="COMPLIANCE002",
            regulation="GDPR-RETENTION",
            target=node.id,
            detail=f"{node.id} worst-case age {age}s exceeds declared "
            f"retention {limit_base}s",
        )
    return None


def _retention_node_violations(
    model: KernelModel, node: Node, base: FactBase
) -> tuple[ComplianceViolation, ...]:
    """GDPR-RETENTION per-node check body: 0-2 violations for one node."""
    if not (_has_jurisdiction(node.attrs, "eu-resident") and node.clearance):
        return ()
    if not _pii_or_above(model, node.clearance):
        return ()
    limit = _retention_limit(node.attrs)
    if limit is None:
        return ()  # no declared bound: nothing to check yet (structural cut)
    claim_id = f"compliance:GDPR-RETENTION:{node.id}"
    overridden, malformed = _claim_override(model, claim_id)
    violations: list[ComplianceViolation] = []
    if malformed is not None:
        violations.append(malformed)
    if overridden:
        return tuple(violations)
    dim = limit.dimension()
    if dim.is_err or dim.danger_ok != "time":
        violations.append(_retention_dim_violation(node, limit))
        return tuple(violations)
    age_violation = _retention_age_violation(node, base, limit)
    if age_violation is not None:
        violations.append(age_violation)
    return tuple(violations)


def _check_retention(
    model: KernelModel,
) -> Result[tuple[ComplianceViolation, ...], StrataError]:
    """Data-retention limit: an `eu-resident`-tagged Pii-or-above store
    declaring `retention=<bound>` must have `worst_age <= bound` -- the
    age collapse again (`_facts.py::worst_age`, T-0065)."""
    facts = build_facts(model)
    if facts.is_err:
        return Err(facts.danger_err)
    base = facts.danger_ok

    violations: list[ComplianceViolation] = []
    for node in sorted(model.nodes, key=lambda n: n.id):
        violations.extend(_retention_node_violations(model, node, base))
    return Ok(tuple(violations))


def _lawful_basis_flow_violations(
    model: KernelModel, flow: Flow, nodes_by_id: dict[str, Node]
) -> tuple[ComplianceViolation, ...]:
    """GDPR-BASIS per-flow check body: 0-2 violations for one flow."""
    if not _pii_or_above(model, flow.label):
        return ()
    dst = nodes_by_id.get(flow.dst)
    if dst is None or not _has_jurisdiction(dst.attrs, "eu-resident"):
        return ()
    claim_id = f"compliance:GDPR-BASIS:{flow.id}"
    overridden, malformed = _claim_override(model, claim_id)
    violations: list[ComplianceViolation] = []
    if malformed is not None:
        violations.append(malformed)
    if overridden:
        return tuple(violations)
    has_basis = any(attr.startswith(_BASIS_PREFIX) for attr in flow.attrs)
    if not has_basis:
        _log.warning(
            "compliance: GDPR-BASIS fired on flow %s, no declared basis", flow.id
        )
        violations.append(
            ComplianceViolation(
                rule="COMPLIANCE002",
                regulation="GDPR-BASIS",
                target=flow.id,
                detail=f"flow {flow.id} collects eu-resident Pii into {dst.id} "
                "with no declared lawful basis",
            )
        )
    return tuple(violations)


def _check_lawful_basis(model: KernelModel) -> tuple[ComplianceViolation, ...]:
    """GDPR lawful basis: a collection flow into an `eu-resident`-tagged Pii
    store with no `basis:<consent|contract|legitimate-interest>` attr
    refuses (docs/strata/threat.md#compliance)."""
    nodes_by_id = {n.id: n for n in model.nodes}
    violations: list[ComplianceViolation] = []
    for flow in sorted(model.flows, key=lambda f: f.id):
        violations.extend(_lawful_basis_flow_violations(model, flow, nodes_by_id))
    return tuple(violations)


def _baa_flow_violations(
    model: KernelModel, flow: Flow, nodes_by_id: dict[str, Node]
) -> tuple[ComplianceViolation, ...]:
    """HIPAA-BAA per-flow check body: 0-2 violations for one flow."""
    if not _has_subject_tag(flow.attrs, "health"):
        return ()
    dst = nodes_by_id.get(flow.dst)
    if dst is None:
        return ()
    claim_id = f"compliance:HIPAA-BAA:{flow.id}"
    overridden, malformed = _claim_override(model, claim_id)
    violations: list[ComplianceViolation] = []
    if malformed is not None:
        violations.append(malformed)
    if overridden:
        return tuple(violations)
    if _COVERED_PARTY not in dst.attrs:
        _log.warning(
            "compliance: HIPAA-BAA fired on flow %s -> %s, no BAA attestation",
            flow.id,
            dst.id,
        )
        violations.append(
            ComplianceViolation(
                rule="COMPLIANCE002",
                regulation="HIPAA-BAA",
                target=flow.id,
                detail=f"health-tagged flow {flow.id} reaches {dst.id}, which "
                "declares no covered-party/BAA attestation",
            )
        )
    return tuple(violations)


def _check_baa(model: KernelModel) -> tuple[ComplianceViolation, ...]:
    """HIPAA: a `subject:health`-tagged flow into a node with no
    `covered-party` attr refuses -- a declassification-to-uncovered-party
    (docs/strata/threat.md#compliance)."""
    nodes_by_id = {n.id: n for n in model.nodes}
    violations: list[ComplianceViolation] = []
    for flow in sorted(model.flows, key=lambda f: f.id):
        violations.extend(_baa_flow_violations(model, flow, nodes_by_id))
    return tuple(violations)


def _privacy_notice_node_violations(
    model: KernelModel, node: Node
) -> tuple[ComplianceViolation, ...]:
    """PRIVACY-NOTICE per-node check body: 0-2 violations for one node."""
    if not _has_exposure(node.attrs, "public-web"):
        return ()
    if not node.clearance or not _pii_or_above(model, node.clearance):
        return ()
    claim_id = f"compliance:PRIVACY-NOTICE:{node.id}"
    overridden, malformed = _claim_override(model, claim_id)
    violations: list[ComplianceViolation] = []
    if malformed is not None:
        violations.append(malformed)
    if overridden:
        return tuple(violations)
    if _PRIVACY_POLICY_ATTR not in node.attrs:
        _log.warning(
            "compliance: PRIVACY-NOTICE fired on node %s, no privacy-policy attr",
            node.id,
        )
        violations.append(
            ComplianceViolation(
                rule="COMPLIANCE002",
                regulation="PRIVACY-NOTICE",
                target=node.id,
                detail=f"public-web-exposed Pii-or-above node {node.id} "
                "declares no privacy-policy/notice mitigation",
            )
        )
    return tuple(violations)


def _check_privacy_notice(model: KernelModel) -> tuple[ComplianceViolation, ...]:
    """Notice at collection: a `exposure:public-web`-tagged Pii-or-above
    node with no declared `privacy-policy` attr refuses -- GDPR art.13's
    notice obligation (docs/strata/threat.md#compliance). Node-level (not
    flow-level, unlike HIPAA-BAA) because the precondition is the node's
    OWN public reachability, not a specific inbound collection flow's
    subject tag."""
    violations: list[ComplianceViolation] = []
    for node in sorted(model.nodes, key=lambda n: n.id):
        violations.extend(_privacy_notice_node_violations(model, node))
    return tuple(violations)


def _minimization_flow_violations(
    model: KernelModel, flow: Flow, outbound: set[str]
) -> tuple[ComplianceViolation, ...]:
    """MINIMIZATION per-flow check body: 0-2 violations for one flow."""
    if not _pii_or_above(model, flow.label):
        return ()
    field = _flow_field(flow.attrs)
    if field is None:
        return ()
    claim_id = f"compliance:MINIMIZATION:{flow.id}"
    overridden, malformed = _claim_override(model, claim_id)
    violations: list[ComplianceViolation] = []
    if malformed is not None:
        violations.append(malformed)
    if overridden:
        return tuple(violations)
    if flow.dst not in outbound:
        _log.warning(
            "compliance: MINIMIZATION fired on flow %s, field %r never read",
            flow.id,
            field,
        )
        violations.append(
            ComplianceViolation(
                rule="COMPLIANCE002",
                regulation="MINIMIZATION",
                target=flow.id,
                detail=f"flow {flow.id} collects field {field!r} into "
                f"{flow.dst}, which has no downstream read flow -- drop "
                "the field or justify with an assume",
            )
        )
    return tuple(violations)


def _check_minimization(model: KernelModel) -> tuple[ComplianceViolation, ...]:
    """Data minimization: a collection flow naming a `field:<name>` (an
    explicit, opt-in declaration of WHAT was collected, module docstring)
    whose destination has zero outbound flows is a field collected but
    never read (docs/strata/threat.md#compliance). Keyed on the declared
    field, not merely "any Pii-clearance node" -- clearance defaults to
    `Secret` on every node (`_models.py::Node.clearance`), so a node-level
    precondition would fire on every terminal sink regardless of intent."""
    outbound = {flow.src for flow in model.flows}
    violations: list[ComplianceViolation] = []
    for flow in sorted(model.flows, key=lambda f: f.id):
        violations.extend(_minimization_flow_violations(model, flow, outbound))
    return tuple(violations)


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
# frob:enforces CHK-GATE-COMPLIANCE002
def check_regulation_discharge(
    model: KernelModel,
) -> Result[tuple[ComplianceViolation, ...], StrataError]:
    """COMPLIANCE002: every fired regulatory obligation (COPPA, GDPR
    erasure/retention/basis, HIPAA BAA, minimization, PRIVACY-NOTICE) is
    structurally discharged or explicitly assumed with owner+review (docs/strata/
    threat.md#compliance). Auto-instantiated per-obligation, mirroring
    `_secrets.py::elaborate_secret`'s auto-generated claim -- no
    author-written `Claim` is required unless overriding the structural
    finding."""
    retention = _check_retention(model)
    if retention.is_err:
        return Err(retention.danger_err)
    all_violations = (
        *_check_coppa(model),
        *_check_erasure(model),
        *retention.danger_ok,
        *_check_lawful_basis(model),
        *_check_baa(model),
        *_check_minimization(model),
        *_check_privacy_notice(model),
    )
    _log.info(
        "compliance: discharge check over %d node(s)/%d flow(s) -> %d violation(s)",
        len(model.nodes),
        len(model.flows),
        len(all_violations),
    )
    return Ok(all_violations)


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
class PrivacyPolicy(BaseModel):
    """A privacy policy modeled as DECLARED data practices (docs/strata/
    threat.md#compliance, "Privacy policy as claims"): the fields it
    admits collecting. `check_privacy_policy` proves the design does not
    EXCEED this declaration -- the verifiable core of the reverse audit;
    binding this model to the actual prose document is DOC002's territory
    (T-0115), not reimplemented here."""

    model_config = ConfigDict(frozen=True)

    id: str
    collected_fields: frozenset[str] = frozenset()


def _flow_field(flow_attrs: tuple[str, ...]) -> str | None:
    """A collection flow's declared payload field name (`field:<name>` attr)."""
    for attr in flow_attrs:
        if attr.startswith("field:"):
            return attr[len("field:") :]
    return None


def _privacy_policy_flow_violation(
    model: KernelModel, flow: Flow, policy: PrivacyPolicy
) -> ComplianceViolation | None:
    """COMPLIANCE003 per-flow check body: at most one violation for one flow."""
    if not _pii_or_above(model, flow.label):
        return None
    field = _flow_field(flow.attrs)
    if field is None:
        return None
    if field not in policy.collected_fields:
        _log.warning(
            "compliance: COMPLIANCE003 flow %s collects field %r, policy %s omits it",
            flow.id,
            field,
            policy.id,
        )
        return ComplianceViolation(
            rule="COMPLIANCE003",
            regulation="PRIVACY-POLICY",
            target=flow.id,
            detail=f"flow {flow.id} collects field {field!r}, which "
            f"privacy policy {policy.id!r} does not declare",
        )
    return None


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
# frob:enforces CHK-GATE-COMPLIANCE003
def check_privacy_policy(
    model: KernelModel, policy: PrivacyPolicy
) -> tuple[ComplianceViolation, ...]:
    """COMPLIANCE003: every modeled collection flow's `field:<name>` attr
    must appear in `policy.collected_fields` -- a flow collecting a field
    the policy does not list REFUTES (docs/strata/threat.md#compliance,
    "A flow collecting a field the policy does not list ... REFUTE"). A
    flow carrying no `field:` attr is out of this check's reach (nothing
    to compare) and is not flagged -- deliberately not silently widened
    beyond what the model actually declares."""
    violations: list[ComplianceViolation] = []
    for flow in sorted(model.flows, key=lambda f: f.id):
        violation = _privacy_policy_flow_violation(model, flow, policy)
        if violation is not None:
            violations.append(violation)
    return tuple(violations)


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
# frob:ticket T-0601
def evaluate_compliance(
    model: KernelModel,
    view: str,
    catalog: tuple[RegulationEntry, ...] = COMPLIANCE_CATALOG,
    out_of_scope: tuple[OutOfScopeRegulation, ...] = (),
    policy: PrivacyPolicy | None = None,
    known_rule_ids: frozenset[str] = frozenset(),
) -> Result[ComplianceReport, StrataError]:
    """The strata-level compliance-audit entrypoint: COMPLIANCE001 +
    COMPLIANCE002 (+ COMPLIANCE003 when `policy` is given, + COMPLIANCE004
    when `out_of_scope` carries any rule-id-shaped `caught_by`) over
    `model` against the selected baseline `view` (docs/strata/threat.md
    #compliance). Kept gate-agnostic (no `src/frob/gates` import),
    mirroring `_threat.py::evaluate_threats`. `known_rule_ids` (T-0382) is
    the live gate-rule-id set COMPLIANCE004's caught_by verification
    checks against -- defaults to empty (no rule-id reference can
    resolve, fail closed), same rationale as `_threat.py::
    evaluate_exhaustiveness`'s own `known_rule_ids` parameter."""
    catalog_violations = check_regulation_catalog_completeness(
        view, catalog, out_of_scope
    )
    if catalog_violations.is_err:
        return Err(catalog_violations.danger_err)
    discharge_violations = check_regulation_discharge(model)
    if discharge_violations.is_err:
        return Err(discharge_violations.danger_err)
    policy_violations = (
        check_privacy_policy(model, policy) if policy is not None else ()
    )
    caught_by_violations = _check_regulation_caught_by_integrity(
        out_of_scope, known_rule_ids
    )
    if caught_by_violations.is_err:
        return Err(caught_by_violations.danger_err)
    all_violations = (
        *catalog_violations.danger_ok,
        *discharge_violations.danger_ok,
        *policy_violations,
        *caught_by_violations.danger_ok,
    )
    _log.info(
        "compliance: evaluated view=%r catalog=%d out_of_scope=%d -> %d violation(s)",
        view,
        len(catalog),
        len(out_of_scope),
        len(all_violations),
    )
    return Ok(ComplianceReport(violations=all_violations))


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#registry-exhaustiveness-drift-lock-t-0343  # noqa: E501
# frob:ticket T-0607
#: The 17 `docs/design/registry/compliance.yaml` `CMPL-*` entries T-0388's
#: reconciliation pass tagged `checkability: mixed|config|static` and
#: re-pointed at this ticket (`deferred:T-0607`) rather than the 10
#: `process`/`advisory`-tagged entries, which already carry their own
#: `out_of_scope` disposition and need no further work here. Kept as one
#: named constant (not re-derived from the yaml at import time) so
#: `_check_cmpl_registry_unit_dispositions` has a fixed universe to check
#: even if a future edit to the registry file adds/removes entries under
#: these frameworks -- a drift there is REG005/REG007's job, not this
#: check's.
CMPL_REGISTRY_UNIT_IDS: frozenset[str] = frozenset(
    {
        "CMPL-SOC2-CATEGORIES",
        "CMPL-SOC2-CC-FAMILIES",
        "CMPL-PCIDSS-REQUIREMENTS",
        "CMPL-HIPAA-TECHNICAL-STANDARDS",
        "CMPL-GDPR-ARTICLES",
        "CMPL-NIST80053-FAMILIES",
        "CMPL-NIST80263-VOLUMES",
        "CMPL-SSDF-PRACTICE-GROUPS",
        "CMPL-ISO27002-THEMES",
        "CMPL-ISO27002-CONTROLS",
        "CMPL-CIS-CONTROLS",
        "CMPL-CIS-SAFEGUARDS",
        "CMPL-ASVS-CHAPTERS",
        "CMPL-ASVS-REQUIREMENTS",
        "CMPL-FEDRAMP-IMPACT-TIERS",
        "CMPL-SLSA-BUILD-LEVELS",
        "CMPL-FROB-CATALOG-ENTRIES",
    }
)

# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#compliance005compliance007-compliance-registry-vs-model-checking-t-1244  # noqa: E501
#: T-1244 (gate-vacuity closure): `_check_cmpl_registry_unit_dispositions`
#: (COMPLIANCE005) only proves a `CMPL_REGISTRY_UNIT_IDS` member carries
#: SOME `handled_by`/`out_of_scope` string -- for 16 of the 17 units that
#: string is the SELF-referential `handled_by:COMPLIANCE005`, which is
#: circular: "this framework is handled by the check that verifies a
#: disposition string exists" proves nothing about whether any real
#: `RegulationEntry`/mitigation/attestation backs THAT framework's actual
#: obligations. `CMPL-FROB-CATALOG-ENTRIES` is the one legitimate
#: exception -- it is a meta-row COUNTING `COMPLIANCE_CATALOG`'s own real
#: entries, so its self-reference is not vacuous (T-1250 confirms this
#: explicitly rather than let it ride the same generic shape as the other
#: 16). Maps each vacuously-self-referential unit to the per-framework
#: triage ticket (T-1245-T-1249) that owns its real (a)/(b)/(c)/(d)
#: classification -- named here, not re-derived, so `_cmpl_unit_backing_
#: violation`'s message always points at live, open follow-up work.
_CMPL_UNIT_TRIAGE_TICKET: dict[str, str] = {
    "CMPL-SOC2-CATEGORIES": "T-1245",
    "CMPL-SOC2-CC-FAMILIES": "T-1245",
    "CMPL-PCIDSS-REQUIREMENTS": "T-1245",
    "CMPL-HIPAA-TECHNICAL-STANDARDS": "T-1245",
    "CMPL-GDPR-ARTICLES": "T-1246",
    "CMPL-NIST80053-FAMILIES": "T-1247",
    "CMPL-NIST80263-VOLUMES": "T-1247",
    "CMPL-SSDF-PRACTICE-GROUPS": "T-1247",
    "CMPL-ISO27002-THEMES": "T-1248",
    "CMPL-ISO27002-CONTROLS": "T-1248",
    "CMPL-CIS-CONTROLS": "T-1248",
    "CMPL-CIS-SAFEGUARDS": "T-1248",
    "CMPL-ASVS-CHAPTERS": "T-1249",
    "CMPL-ASVS-REQUIREMENTS": "T-1249",
    "CMPL-FEDRAMP-IMPACT-TIERS": "T-1249",
    "CMPL-SLSA-BUILD-LEVELS": "T-1249",
}


def _cmpl_disposition_violation(entry: RegistryEntry) -> ComplianceViolation:
    """COMPLIANCE005 violation helper: one `CMPL_REGISTRY_UNIT_IDS` member
    stuck `deferred:*`/undispositioned -- exactly the catalogued-not-
    enforced regression T-0607 exists to close (a `deferred:T-0388` that
    named T-0388, the reconciliation ticket ITSELF, and would have
    silently re-orphaned the moment T-0388 closed)."""
    _log.warning(
        "compliance: COMPLIANCE005 %s disposition kind %s is neither "
        "handled_by nor out_of_scope",
        entry.id,
        entry.disposition.kind.value,
    )
    return ComplianceViolation(
        rule="COMPLIANCE005",
        regulation=entry.id,
        detail=f"{entry.id} disposition {entry.disposition.raw!r} is "
        f"{entry.disposition.kind.value}, not handled_by/out_of_scope -- "
        "a checkable-control compliance-registry unit left deferred or "
        "undispositioned re-orphans itself the moment any named ticket "
        "closes (the exact T-0388/T-0607 self-reference incident this "
        "check exists to refuse a repeat of)",
    )


# frob:ticket T-0607
# frob:tests tests/unit/strata/test_compliance.py::TestCmplRegistry.test_deferred_disposition_is_refused  # noqa: E501
# frob:tests tests/unit/strata/test_compliance.py::TestCmplRegistry.test_handled_by_and_out_of_scope_dispositions_pass  # noqa: E501
# frob:ticket T-0601
def _check_cmpl_registry_unit_dispositions(
    entries: tuple[RegistryEntry, ...],
) -> tuple[ComplianceViolation, ...]:
    """COMPLIANCE005: every `CMPL_REGISTRY_UNIT_IDS` member present in
    `entries` (typically `docs/design/registry/compliance.yaml`'s loaded
    `entries:` list) must carry a `handled_by:<rule>`/`out_of_scope:
    <reason>` disposition, never `deferred:*` or an undispositioned/
    unparseable string. `frob.gates._registry_exhaustiveness`
    (REG001-REG004) already verifies the disposition grammar is well-
    formed against LIVE state (a named rule/ticket actually exists right
    now); this check adds a narrower, PERMANENT guarantee specific to
    this ticket's 17 units: none of them may ever sit in the `deferred`/
    undispositioned state again, regardless of whether a would-be
    `deferred:` target is currently valid -- the T-0388 incident this
    ticket closes was a `deferred:T-0388` that WAS valid right up until
    the moment the named ticket closed, only then becoming a REG003
    violation. An id in `CMPL_REGISTRY_UNIT_IDS` absent from `entries`
    entirely is silently skipped here (nothing to classify) -- a
    silently-dropped registry entry is REG005/REG007's job to catch, not
    this check's."""
    known = {entry.id: entry for entry in entries}
    violations: list[ComplianceViolation] = []
    checked = 0
    for entry_id in sorted(CMPL_REGISTRY_UNIT_IDS):
        entry = known.get(entry_id)
        if entry is None:
            continue
        checked += 1
        if entry.disposition.kind not in (
            DispositionKind.HANDLED_BY,
            DispositionKind.OUT_OF_SCOPE,
        ):
            violations.append(_cmpl_disposition_violation(entry))
    _log.info(
        "compliance: COMPLIANCE005 checked %d/%d CMPL registry unit(s) -> "
        "%d violation(s)",
        checked,
        len(CMPL_REGISTRY_UNIT_IDS),
        len(violations),
    )
    return tuple(violations)


def _cmpl_unit_backing_violation(entry_id: str, ticket_id: str) -> ComplianceViolation:
    """COMPLIANCE007 violation helper: `entry_id`'s `handled_by:COMPLIANCE005`
    disposition is the vacuous self-reference (module-level `_CMPL_UNIT_
    TRIAGE_TICKET` docstring) -- names the open triage ticket that owns
    re-dispositioning it against a real `RegulationEntry`/attestation."""
    _log.warning(
        "compliance: COMPLIANCE007 %s handled_by:COMPLIANCE005 is a vacuous "
        "self-reference -- no RegulationEntry/attestation backs it yet, "
        "see %s",
        entry_id,
        ticket_id,
    )
    return ComplianceViolation(
        rule="COMPLIANCE007",
        regulation=entry_id,
        detail=f"{entry_id}'s handled_by:COMPLIANCE005 disposition only "
        "proves a disposition string exists, not that a real "
        "RegulationEntry/mitigation/attestation backs this framework's "
        f"obligations (catalogued-not-enforced) -- re-disposition tracked "
        f"in {ticket_id}",
    )


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#compliance005compliance007-compliance-registry-vs-model-checking-t-1244  # noqa: E501
# frob:ticket T-1244
# frob:tests tests/unit/strata/test_compliance.py::TestCmplRegistryBacking.test_self_referential_handled_by_is_flagged  # noqa: E501
# frob:tests tests/unit/strata/test_compliance.py::TestCmplRegistryBacking.test_frob_catalog_entries_self_reference_is_not_flagged  # noqa: E501
# frob:tests tests/unit/strata/test_compliance.py::TestCmplRegistryBacking.test_non_self_referential_handled_by_is_not_flagged  # noqa: E501
def _check_cmpl_registry_unit_backing(
    entries: tuple[RegistryEntry, ...],
) -> tuple[ComplianceViolation, ...]:
    """COMPLIANCE007 (T-1244): every `_CMPL_UNIT_TRIAGE_TICKET` member
    present in `entries` whose disposition is the vacuous, self-
    referential `handled_by:COMPLIANCE005` is flagged -- the generate-
    and-verify half COMPLIANCE005 alone cannot provide (it only checks the
    disposition STRING is non-deferred, never that the named control is
    THIS framework's real enforcement). Deliberately WARN-tier (assigned
    by the gate wrapper, `frob.gates._decisions_compliance`), not ERROR:
    re-dispositioning each of these 16 rows against a real (a)/(b)/(c)/(d)
    classification is the sibling triage tickets' job (T-1245-T-1249), a
    decision above this ticket's pay grade -- this check's job is only to
    make the gap loud and durable, never to silently resolve it. A unit
    absent from `entries` is silently skipped (same convention as
    `_check_cmpl_registry_unit_dispositions`); a non-`handled_by:
    COMPLIANCE005` disposition (e.g. already re-triaged to a real rule, or
    `out_of_scope`) is silent here too -- COMPLIANCE007 only fires on the
    specific vacuous shape, not on every disposition kind."""
    known = {entry.id: entry for entry in entries}
    violations: list[ComplianceViolation] = []
    for entry_id, ticket_id in sorted(_CMPL_UNIT_TRIAGE_TICKET.items()):
        entry = known.get(entry_id)
        if entry is None:
            continue
        if (
            entry.disposition.kind is DispositionKind.HANDLED_BY
            and entry.disposition.target == "COMPLIANCE005"
        ):
            violations.append(_cmpl_unit_backing_violation(entry_id, ticket_id))
    _log.info(
        "compliance: COMPLIANCE007 checked %d candidate unit(s) -> %d violation(s)",
        len(_CMPL_UNIT_TRIAGE_TICKET),
        len(violations),
    )
    return tuple(violations)


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#registry-exhaustiveness-drift-lock-t-0343  # noqa: E501
# frob:ticket T-0607
# frob:tests tests/unit/strata/test_compliance.py::TestCmplRegistry.test_check_cmpl_registry_loads_real_file  # noqa: E501
# frob:tests tests/unit/strata/test_compliance.py::TestCmplRegistry.test_check_cmpl_registry_missing_file_is_parse_failed  # noqa: E501
# frob:ticket T-0601
def check_cmpl_registry(
    registry_dir: Path,
) -> Result[tuple[ComplianceViolation, ...], StrataError]:
    """COMPLIANCE005/COMPLIANCE007 entrypoint: loads `compliance.yaml` from
    `registry_dir` via `frob.registry.load_registry_dir` (the ONE shared
    registry loader, T-0407 -- never re-parsed inline here) and runs
    `_check_cmpl_registry_unit_dispositions` (COMPLIANCE005: does a
    disposition string exist) then `_check_cmpl_registry_unit_backing`
    (COMPLIANCE007, T-1244: is that disposition a vacuous self-reference)
    over its `entries:` list. `Err(StrataError.ParseFailed)` on a missing/
    unreadable/malformed-YAML manifest, mirroring every other kernel-
    facing Result boundary in this module -- an unloadable registry never
    silently reports "0 violations"."""
    loaded = load_registry_dir(registry_dir, ("compliance.yaml",))
    result = loaded.get("compliance.yaml")
    if result is None or result.is_err:
        _log.error(
            "compliance: COMPLIANCE005 compliance.yaml not loadable under %s (%s)",
            registry_dir,
            result.danger_err if result is not None else "file absent",
        )
        return Err(StrataError.ParseFailed)
    entries = result.danger_ok.entry_lists.get("entries", ())
    return Ok(
        _check_cmpl_registry_unit_dispositions(entries)
        + _check_cmpl_registry_unit_backing(entries)
    )


__all__ = [
    "CMPL_REGISTRY_UNIT_IDS",
    "COMPLIANCE_CATALOG",
    "COMPLIANCE_OUT_OF_SCOPE",
    "REGULATION_VIEWS",
    "ComplianceReport",
    "ComplianceViolation",
    "OutOfScopeRegulation",
    "PrivacyPolicy",
    "RegulationEntry",
    "check_cmpl_registry",
    "check_privacy_policy",
    "check_regulation_catalog_completeness",
    "check_regulation_discharge",
    "evaluate_compliance",
]
