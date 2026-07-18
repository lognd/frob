"""strata obligation catalog phase F (compliance): `std.compliance` --
COPPA/GDPR/HIPAA regulatory obligations + privacy-policy-as-claims reverse
audit (docs/strata/threat.md#compliance-regulatory-obligations-std-compliance,
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
`retention=<value><unit>`, or `covered-party` (HIPAA BAA-satisfied). This
is opaque-string vocabulary on the existing `attrs` tuples (charter law 1:
no new kernel primitive), the same convention `_claims.py`'s `skew=`/
`growth=` prefixes and `_secrets.py`'s `attrs=("revocation",)` already use.

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

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._facts import build_facts
from ._models import BoundaryDirection, KernelModel, Quantity

_log = get_logger(__name__)

#: Flow/Node attr prefixes carrying compliance tags (module docstring).
_SUBJECT_PREFIX = "subject:"
_JURISDICTION_PREFIX = "jurisdiction:"
_BASIS_PREFIX = "basis:"
_RETENTION_PREFIX = "retention="
_COVERED_PARTY = "covered-party"
_REVOCATION_ATTR = "revocation"


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-std-compliance
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


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-std-compliance
class OutOfScopeRegulation(BaseModel):
    """A baseline regulation id explicitly excluded from the catalog.

    Unlike `_threat.py::OutOfScopeEntry`, `owner` and `review` are
    mandatory: the charter's compliance closing paragraph requires every
    cited exclusion to carry legal ownership + a review date, since
    regulations change underneath a stale exclusion (docs/strata/
    threat.md#compliance, "Exhaustiveness for compliance")."""

    model_config = ConfigDict(frozen=True)

    id: str
    reason: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    review: str  # ISO date


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-std-compliance
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
)

# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-std-compliance
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


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-std-compliance
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


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-std-compliance
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


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-std-compliance
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
    # frob:waive PERF004 reason="one sort of the view's member set, not per-iteration"
    ordered_members = sorted(members)
    violations = [
        _catalog_violation(view, reg_id)
        for reg_id in ordered_members
        if reg_id not in cataloged and reg_id not in excused
    ]
    return Ok(tuple(violations))


def _has_subject_tag(attrs: tuple[str, ...], tag: str) -> bool:
    """Whether `attrs` carries `subject:<tag>` (module docstring vocabulary)."""
    return f"{_SUBJECT_PREFIX}{tag}" in attrs


def _has_jurisdiction(attrs: tuple[str, ...], jurisdiction: str) -> bool:
    """Whether `attrs` carries `jurisdiction:<jurisdiction>`."""
    return f"{_JURISDICTION_PREFIX}{jurisdiction}" in attrs


def _retention_limit(attrs: tuple[str, ...]) -> Quantity | None:
    """A node's declared `retention=<value><unit>` bound, parsed, or None."""
    for attr in attrs:
        if attr.startswith(_RETENTION_PREFIX):
            raw = attr[len(_RETENTION_PREFIX) :]
            for cut in range(len(raw), 0, -1):
                value_part, unit_part = raw[:cut], raw[cut:]
                try:
                    return Quantity(value=float(value_part), unit=unit_part)
                except ValueError:
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
        if not (
            _has_subject_tag(flow.attrs, "child")
            or _has_subject_tag(flow.attrs, "unknown-age")
        ):
            continue
        if not _pii_or_above(model, flow.label):
            continue
        if flow.dst not in node_ids:
            continue
        claim_id = f"compliance:COPPA:{flow.id}"
        overridden, malformed = _claim_override(model, claim_id)
        if malformed is not None:
            violations.append(malformed)
        if overridden:
            continue
        if flow.id not in boundary_flows:
            _log.warning(
                "compliance: COPPA fired on flow %s (%s -> %s), no age-gate boundary",
                flow.id,
                flow.src,
                flow.dst,
            )
            violations.append(
                ComplianceViolation(
                    rule="COMPLIANCE002",
                    regulation="COPPA",
                    target=flow.id,
                    detail=f"collection flow {flow.id} ({flow.src} -> {flow.dst}) "
                    "from an under-13/unknown-age subject reaches a Pii store "
                    "with no age-gate/parental-consent boundary",
                )
            )
    return tuple(violations)


def _check_erasure(model: KernelModel) -> tuple[ComplianceViolation, ...]:
    """GDPR right to erasure: an `eu-resident`-tagged Pii-or-above store has
    no flow carrying `attrs=("revocation", ...)` touching it -- the SAME
    revocation-edge convention `_secrets.py::_secret_flows` establishes
    (docs/strata/threat.md#compliance)."""
    # One pass over flows builds the revoked-node set; the node loop below
    # is then a plain membership test, not a nested scan (charter: no
    # accidental O(nodes*flows)).
    revoked_nodes: set[str] = set()
    for flow in model.flows:
        if _REVOCATION_ATTR in flow.attrs:
            revoked_nodes.add(flow.src)
            revoked_nodes.add(flow.dst)

    violations: list[ComplianceViolation] = []
    for node in sorted(model.nodes, key=lambda n: n.id):
        if not (_has_jurisdiction(node.attrs, "eu-resident") and node.clearance):
            continue
        if not _pii_or_above(model, node.clearance):
            continue
        claim_id = f"compliance:GDPR-ERASURE:{node.id}"
        overridden, malformed = _claim_override(model, claim_id)
        if malformed is not None:
            violations.append(malformed)
        if overridden:
            continue
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
        if not (_has_jurisdiction(node.attrs, "eu-resident") and node.clearance):
            continue
        if not _pii_or_above(model, node.clearance):
            continue
        limit = _retention_limit(node.attrs)
        if limit is None:
            continue  # no declared bound: nothing to check yet (structural cut)
        claim_id = f"compliance:GDPR-RETENTION:{node.id}"
        overridden, malformed = _claim_override(model, claim_id)
        if malformed is not None:
            violations.append(malformed)
        if overridden:
            continue
        dim = limit.dimension()
        if dim.is_err or dim.danger_ok != "time":
            violations.append(
                ComplianceViolation(
                    rule="COMPLIANCE002",
                    regulation="GDPR-RETENTION",
                    target=node.id,
                    detail=f"{node.id} retention bound {limit.value}{limit.unit} "
                    "is not a time unit",
                )
            )
            continue
        age, _path = base.worst_age(node.id)
        limit_base = limit.base_value().danger_ok
        if age == float("inf") or age > limit_base:
            _log.warning(
                "compliance: GDPR-RETENTION fired on store %s, worst age %s > limit %s",
                node.id,
                age,
                limit_base,
            )
            violations.append(
                ComplianceViolation(
                    rule="COMPLIANCE002",
                    regulation="GDPR-RETENTION",
                    target=node.id,
                    detail=f"{node.id} worst-case age {age}s exceeds declared "
                    f"retention {limit_base}s",
                )
            )
    return Ok(tuple(violations))


def _check_lawful_basis(model: KernelModel) -> tuple[ComplianceViolation, ...]:
    """GDPR lawful basis: a collection flow into an `eu-resident`-tagged Pii
    store with no `basis:<consent|contract|legitimate-interest>` attr
    refuses (docs/strata/threat.md#compliance)."""
    nodes_by_id = {n.id: n for n in model.nodes}
    violations: list[ComplianceViolation] = []
    for flow in sorted(model.flows, key=lambda f: f.id):
        if not _pii_or_above(model, flow.label):
            continue
        dst = nodes_by_id.get(flow.dst)
        if dst is None or not _has_jurisdiction(dst.attrs, "eu-resident"):
            continue
        claim_id = f"compliance:GDPR-BASIS:{flow.id}"
        overridden, malformed = _claim_override(model, claim_id)
        if malformed is not None:
            violations.append(malformed)
        if overridden:
            continue
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


def _check_baa(model: KernelModel) -> tuple[ComplianceViolation, ...]:
    """HIPAA: a `subject:health`-tagged flow into a node with no
    `covered-party` attr refuses -- a declassification-to-uncovered-party
    (docs/strata/threat.md#compliance)."""
    nodes_by_id = {n.id: n for n in model.nodes}
    violations: list[ComplianceViolation] = []
    for flow in sorted(model.flows, key=lambda f: f.id):
        if not _has_subject_tag(flow.attrs, "health"):
            continue
        dst = nodes_by_id.get(flow.dst)
        if dst is None:
            continue
        claim_id = f"compliance:HIPAA-BAA:{flow.id}"
        overridden, malformed = _claim_override(model, claim_id)
        if malformed is not None:
            violations.append(malformed)
        if overridden:
            continue
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
        if not _pii_or_above(model, flow.label):
            continue
        field = _flow_field(flow.attrs)
        if field is None:
            continue
        claim_id = f"compliance:MINIMIZATION:{flow.id}"
        overridden, malformed = _claim_override(model, claim_id)
        if malformed is not None:
            violations.append(malformed)
        if overridden:
            continue
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


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-std-compliance
# frob:waive TEST005 reason="check_regulation_discharge 83.3% branch cover, debt T-0160"
def check_regulation_discharge(
    model: KernelModel,
) -> Result[tuple[ComplianceViolation, ...], StrataError]:
    """COMPLIANCE002: every fired regulatory obligation (COPPA, GDPR
    erasure/retention/basis, HIPAA BAA, minimization) is structurally
    discharged or explicitly assumed with owner+review (docs/strata/
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
    )
    _log.info(
        "compliance: discharge check over %d node(s)/%d flow(s) -> %d violation(s)",
        len(model.nodes),
        len(model.flows),
        len(all_violations),
    )
    return Ok(all_violations)


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-std-compliance
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


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-std-compliance
# frob:waive TEST005 reason="check_privacy_policy 81.8% branch cover, debt T-0160"
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
        if not _pii_or_above(model, flow.label):
            continue
        field = _flow_field(flow.attrs)
        if field is None:
            continue
        if field not in policy.collected_fields:
            _log.warning(
                "compliance: COMPLIANCE003 flow %s collects field %r, "
                "policy %s omits it",
                flow.id,
                field,
                policy.id,
            )
            violations.append(
                ComplianceViolation(
                    rule="COMPLIANCE003",
                    regulation="PRIVACY-POLICY",
                    target=flow.id,
                    detail=f"flow {flow.id} collects field {field!r}, which "
                    f"privacy policy {policy.id!r} does not declare",
                )
            )
    return tuple(violations)


# frob:doc docs/strata/threat.md#compliance-regulatory-obligations-std-compliance
def evaluate_compliance(
    model: KernelModel,
    view: str,
    catalog: tuple[RegulationEntry, ...] = COMPLIANCE_CATALOG,
    out_of_scope: tuple[OutOfScopeRegulation, ...] = (),
    policy: PrivacyPolicy | None = None,
) -> Result[ComplianceReport, StrataError]:
    """The strata-level compliance-audit entrypoint: COMPLIANCE001 +
    COMPLIANCE002 (+ COMPLIANCE003 when `policy` is given) over `model`
    against the selected baseline `view` (docs/strata/threat.md#compliance).
    Kept gate-agnostic (no `src/frob/gates` import), mirroring
    `_threat.py::evaluate_threats`."""
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
    all_violations = (
        *catalog_violations.danger_ok,
        *discharge_violations.danger_ok,
        *policy_violations,
    )
    _log.info(
        "compliance: evaluated view=%r catalog=%d out_of_scope=%d -> %d violation(s)",
        view,
        len(catalog),
        len(out_of_scope),
        len(all_violations),
    )
    return Ok(ComplianceReport(violations=all_violations))


__all__ = [
    "COMPLIANCE_CATALOG",
    "REGULATION_VIEWS",
    "ComplianceReport",
    "ComplianceViolation",
    "OutOfScopeRegulation",
    "PrivacyPolicy",
    "RegulationEntry",
    "check_privacy_policy",
    "check_regulation_catalog_completeness",
    "check_regulation_discharge",
    "evaluate_compliance",
]
