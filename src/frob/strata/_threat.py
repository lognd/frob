"""strata obligation catalog phase A: `std.cwe` + weakness/capability grammar
+ THREAT001/THREAT003 (docs/strata/threat.md, T-0109/T-0111).

Phase A is design-level only (docs/strata/threat.md#phasing): a CWE
weakness is cataloged as structured data (never hand-transcribed --
`WeaknessEntry.cite` names the authoritative source url), a capability
kind on a `Node.may` atom auto-instantiates the weakness obligations the
charter's capability table maps it to, and two of the three exhaustiveness
conjuncts are checked:

- THREAT001 (catalog completeness): every CWE id a selected baseline VIEW
  names has a catalog entry or an explicit `out_of_scope` entry.
- THREAT003 (discharge completeness): every FIRED weakness obligation (a
  node declares the `may` capability kind that drags it in) has a
  corresponding `Claim` in the model, evaluated at or above the catalog's
  required rung, never REFUTED, and -- if assumed -- owned with a review
  date.

THREAT002 (sink taxonomy / capability completeness, phase B) and the code-
binding discharge join (phase C, T-0079) are out of scope here; this
module's `may`-kind join reuses exactly the same `_may_kind` convention
`_effects.py` already established so the two stay joinable later without
rework.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._claims import evaluate_claims
from ._effects import _may_kind
from ._errors import StrataError
from ._models import Claim, ClaimResult, KernelModel, Rung, Verdict

_log = get_logger(__name__)

#: Evidence ladder order, low to high (docs/strata/evidence.md); reused to
#: compare a declared claim's required_rung against a catalog entry's.
_RUNG_ORDER: tuple[Rung, ...] = (Rung.L1, Rung.L2, Rung.L3, Rung.L4, Rung.L5)


# frob:doc docs/strata/threat.md#the-catalog-stdcwe
class WeaknessEntry(BaseModel):
    """One `std.cwe` catalog entry: a conditional obligation predicated on
    a capability being present in the model (docs/strata/threat.md#the-
    core-reframe). `capability_kind` is the `may` atom KIND (matching
    `_effects.py::_may_kind`'s convention) whose declaration auto-
    instantiates this obligation (docs/strata/threat.md#capabilities-drag-
    in-obligations); `None` when phase A has no capability-driven
    precondition detector for this id yet (CSRF, hardcoded credentials --
    still cataloged for THREAT001, never fired by THREAT003 in phase A).
    """

    model_config = ConfigDict(frozen=True)

    id: str  # e.g. "CWE-79"
    title: str
    cite: str  # authoritative source url, never hand-transcribed
    family: str = "security"
    capability_kind: str | None = None
    mitigation: str = ""  # required mitigation/boundary predicate name
    rung: Rung = Rung.L4


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class OutOfScopeEntry(BaseModel):
    """A baseline CWE id explicitly excluded from the catalog, with a
    reason -- satisfies THREAT001 without a `WeaknessEntry` (docs/strata/
    threat.md#the-exhaustiveness-proof-the-point, item 1)."""

    model_config = ConfigDict(frozen=True)

    id: str
    reason: str


# frob:doc docs/strata/threat.md#the-catalog-stdcwe
# The OWASP Top-10 subset shipped as phase-A data (docs/strata/threat.md
# #phasing "the OWASP Top-10 subset as data"). Every precondition/mitigation
# pair below is transcribed from the charter's "core reframe" table, which
# itself cites MITRE CWE ids -- the pins/digest-verified ingestion pipeline
# the charter's closing section describes is a build-step follow-up (out of
# scope here; noted as a cut, not silently dropped).
CWE_CATALOG: tuple[WeaknessEntry, ...] = (
    WeaknessEntry(
        id="CWE-79",
        title="Improper Neutralization of Input During Web Page Generation",
        cite="https://cwe.mitre.org/data/definitions/79.html",
        capability_kind="html_render",
        mitigation="output_encoding",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-89",
        title="Improper Neutralization of Special Elements used in an SQL Command",
        cite="https://cwe.mitre.org/data/definitions/89.html",
        capability_kind="sql",
        mitigation="parameterization",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-78",
        title="Improper Neutralization of Special Elements used in an OS Command",
        cite="https://cwe.mitre.org/data/definitions/78.html",
        capability_kind="exec",
        mitigation="argument_confinement",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-22",
        title="Improper Limitation of a Pathname to a Restricted Directory",
        cite="https://cwe.mitre.org/data/definitions/22.html",
        capability_kind=None,  # flow-to-filesystem-path-sink precondition, not a
        # capability kind the charter's auto-instantiate table lists (phase B/C
        # sink taxonomy territory, docs/strata/threat.md#capabilities-drag-in
        # -obligations)
        mitigation="path_confinement",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-918",
        title="Server-Side Request Forgery (SSRF)",
        cite="https://cwe.mitre.org/data/definitions/918.html",
        capability_kind="fetch_url",
        mitigation="allowlist_mediation",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-502",
        title="Deserialization of Untrusted Data",
        cite="https://cwe.mitre.org/data/definitions/502.html",
        capability_kind="deserialize",
        mitigation="schema_validation",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-922",
        title="Insecure Storage of Sensitive Information",
        cite="https://cwe.mitre.org/data/definitions/922.html",
        capability_kind="client_storage",
        mitigation="clearance_boundary",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-352",
        title="Cross-Site Request Forgery (CSRF)",
        cite="https://cwe.mitre.org/data/definitions/352.html",
        capability_kind=None,  # state-changing-endpoint precondition, not a
        # capability kind; phase B/C sink taxonomy territory
        mitigation="anti_csrf_token",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-798",
        title="Use of Hard-coded Credentials",
        cite="https://cwe.mitre.org/data/definitions/798.html",
        capability_kind=None,  # secret-resting-at-low-clearance precondition,
        # already the lattice's own clearance-violation refusal; no capability
        # kind fires it
        mitigation="clearance_boundary",
        rung=Rung.L4,
    ),
)

#: Baseline VIEWS: the id set a selected view holds the catalog to. Phase A
#: ships one view, the OWASP Top-10 subset actually cataloged above;
#: `cwe-top-25`/`owasp-asvs`/`cwe-1000` are later-phase ingestion targets
#: (phasing section, item A), not stubbed here so THREAT001 never lies
#: about a view it cannot check.
# frob:doc docs/strata/threat.md#the-catalog-stdcwe
VIEWS: dict[str, frozenset[str]] = {
    "owasp-top-10": frozenset(entry.id for entry in CWE_CATALOG),
}

#: capability KIND (the `_effects.py::_may_kind` convention) -> the CWE ids
#: its declaration auto-instantiates (docs/strata/threat.md#capabilities-
#: drag-in-obligations).
_CAPABILITY_OBLIGATIONS: dict[str, tuple[str, ...]] = {}
for _entry in CWE_CATALOG:
    if _entry.capability_kind is not None:
        _CAPABILITY_OBLIGATIONS.setdefault(_entry.capability_kind, ())
        _CAPABILITY_OBLIGATIONS[_entry.capability_kind] += (_entry.id,)
del _entry


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class ThreatViolation(BaseModel):
    """One THREAT001/THREAT003 finding: a rule id, the CWE id, an optional
    firing node, and a human detail -- never a silent gap."""

    model_config = ConfigDict(frozen=True)

    rule: str  # "THREAT001" | "THREAT003"
    cwe: str
    node: str | None = None
    detail: str = ""


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class ThreatReport(BaseModel):
    """Every THREAT001/THREAT003 violation, in rule-then-cwe-then-node order."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[ThreatViolation, ...] = ()


def _catalog_violation(view: str, cwe_id: str) -> ThreatViolation:
    """THREAT001 violation helper: deny-by-default unaddressed baseline CWE."""
    _log.warning("threat: THREAT001 %s has no catalog or out-of-scope entry", cwe_id)
    return ThreatViolation(
        rule="THREAT001",
        cwe=cwe_id,
        detail=f"baseline view {view!r} names {cwe_id} with no catalog "
        "or out-of-scope entry",
    )


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
def check_catalog_completeness(
    view: str,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
    out_of_scope: tuple[OutOfScopeEntry, ...] = (),
    views: dict[str, frozenset[str]] | None = None,
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT001: every CWE id the selected `view` names has a `WeaknessEntry`
    or an `OutOfScopeEntry`; an unaddressed baseline CWE is a violation
    (docs/strata/threat.md#the-exhaustiveness-proof-the-point, item 1).

    Fails closed (`StrataError.UnknownReference`) on a `view` name the
    catalog does not ship -- a typo'd view must never silently pass as
    "nothing to check".
    """
    view_table = views if views is not None else VIEWS
    members = view_table.get(view)
    if members is None:
        _log.error("threat: unknown baseline view %r", view)
        return Err(StrataError.UnknownReference)

    cataloged = {entry.id for entry in catalog}
    excused = {entry.id for entry in out_of_scope}
    # frob:waive PERF004 reason="one sort of the view's member set, not per-iteration"
    ordered_members = sorted(members)
    violations = [
        _catalog_violation(view, cwe_id)
        for cwe_id in ordered_members
        if cwe_id not in cataloged and cwe_id not in excused
    ]
    return Ok(tuple(violations))


def _fired_obligations(
    model: KernelModel, catalog: tuple[WeaknessEntry, ...]
) -> list[tuple[str, WeaknessEntry]]:
    """Every (node_id, WeaknessEntry) pair whose obligation fires: the node
    declares a `may` atom of the entry's `capability_kind`."""
    by_kind: dict[str, list[WeaknessEntry]] = {}
    for entry in catalog:
        if entry.capability_kind is not None:
            by_kind.setdefault(entry.capability_kind, []).append(entry)

    fired: list[tuple[str, WeaknessEntry]] = []
    for node in model.nodes:
        kinds = {_may_kind(atom) for atom in node.may}
        for kind in kinds:
            for entry in by_kind.get(kind, ()):
                fired.append((node.id, entry))
    return fired


def _rung_at_least(have: Rung, need: Rung) -> bool:
    """Whether `have` sits at or above `need` on the evidence ladder."""
    return _RUNG_ORDER.index(have) >= _RUNG_ORDER.index(need)


def _discharge_claim_id(cwe_id: str, node_id: str) -> str:
    """The naming convention a discharging `Claim.id` must follow: `weakness:
    <cwe-id>:<node-id>` (docs/strata/threat.md#the-core-reframe) -- one
    canonical home for the format so THREAT003 and any future authoring
    surface never disagree (charter: no duplication)."""
    return f"weakness:{cwe_id}:{node_id}"


def _discharge_violation(
    entry: WeaknessEntry, node_id: str, detail: str
) -> ThreatViolation:
    """THREAT003 violation helper: deny-by-default undischarged obligation."""
    _log.warning(
        "threat: THREAT003 %s on %s undischarged: %s", entry.id, node_id, detail
    )
    return ThreatViolation(rule="THREAT003", cwe=entry.id, node=node_id, detail=detail)


def _check_one_discharge(
    entry: WeaknessEntry,
    node_id: str,
    claims_by_id: dict[str, Claim],
    results_by_id: dict[str, ClaimResult],
) -> ThreatViolation | None:
    """One fired obligation's discharge check: present, not REFUTED, at or
    above the catalog's required rung, and -- if assumed -- owned with a
    review date (docs/strata/threat.md#the-exhaustiveness-proof-the-point,
    item 3)."""
    claim_id = _discharge_claim_id(entry.id, node_id)
    claim = claims_by_id.get(claim_id)
    if claim is None:
        return _discharge_violation(
            entry, node_id, f"no claim {claim_id!r} discharges this obligation"
        )
    if not _rung_at_least(claim.required_rung, entry.rung):
        return _discharge_violation(
            entry,
            node_id,
            f"claim {claim_id!r} required_rung {claim.required_rung.value} "
            f"below catalog rung {entry.rung.value}",
        )
    if claim.assumed and (claim.owner is None or claim.review is None):
        return _discharge_violation(
            entry,
            node_id,
            f"claim {claim_id!r} is assumed with no owner/review date",
        )
    result = results_by_id.get(claim_id)
    if result is not None and result.verdict is Verdict.REFUTED:
        return _discharge_violation(
            entry, node_id, f"claim {claim_id!r} is REFUTED: {result.detail}"
        )
    return None


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
def check_discharge_completeness(
    model: KernelModel,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT003: every FIRED weakness obligation (a node declares the `may`
    capability kind that drags it in) is discharged by a `Claim` named
    `weakness:<cwe-id>:<node-id>` (docs/strata/threat.md#the-core-reframe),
    evaluated at or above the catalog's required rung and never REFUTED; a
    dangling or under-evidenced obligation is a violation (docs/strata/
    threat.md#the-exhaustiveness-proof-the-point, item 3).

    Runs `evaluate_claims` to resolve verdicts for claims that are present;
    a missing claim never reaches evaluation -- that is itself the
    violation, deny-by-default (charter law 2).
    """
    fired = _fired_obligations(model, catalog)
    if not fired:
        _log.info("threat: THREAT003 no fired obligations (no matching capabilities)")
        return Ok(())

    claims_by_id = {claim.id: claim for claim in model.claims}
    results = evaluate_claims(model)
    if results.is_err:
        return Err(results.danger_err)
    results_by_id = {r.claim_id: r for r in results.danger_ok}

    violations: list[ThreatViolation] = []
    for node_id, entry in sorted(fired, key=lambda pair: (pair[1].id, pair[0])):
        violation = _check_one_discharge(entry, node_id, claims_by_id, results_by_id)
        if violation is not None:
            violations.append(violation)
    return Ok(tuple(violations))


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
def evaluate_threats(
    model: KernelModel,
    view: str,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
    out_of_scope: tuple[OutOfScopeEntry, ...] = (),
) -> Result[ThreatReport, StrataError]:
    """The strata-level threat-audit entrypoint: THREAT001 + THREAT003 over
    `model` against the selected baseline `view` (docs/strata/threat.md
    #the-exhaustiveness-proof-the-point). Gate wiring (`frob check`
    surfacing this as a diagnostic) is a follow-up once T-0080's sys_gate
    lands -- this function is the seam that follow-up calls into, kept
    deliberately gate-agnostic (no `src/frob/gates` import here).
    """
    catalog_violations = check_catalog_completeness(view, catalog, out_of_scope)
    if catalog_violations.is_err:
        return Err(catalog_violations.danger_err)
    discharge_violations = check_discharge_completeness(model, catalog)
    if discharge_violations.is_err:
        return Err(discharge_violations.danger_err)
    all_violations = (*catalog_violations.danger_ok, *discharge_violations.danger_ok)
    _log.info(
        "threat: evaluated view=%r catalog=%d out_of_scope=%d -> %d violation(s)",
        view,
        len(catalog),
        len(out_of_scope),
        len(all_violations),
    )
    return Ok(ThreatReport(violations=all_violations))


__all__ = [
    "CWE_CATALOG",
    "VIEWS",
    "OutOfScopeEntry",
    "ThreatReport",
    "ThreatViolation",
    "WeaknessEntry",
    "check_catalog_completeness",
    "check_discharge_completeness",
    "evaluate_threats",
]
