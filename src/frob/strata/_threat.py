"""strata obligation catalog phases A-C: `std.cwe` + weakness/capability
grammar + THREAT001-THREAT005 (docs/strata/threat.md,
T-0109/T-0111/T-0112/T-0113).

Phase A (T-0111, design-level only, docs/strata/threat.md#phasing): a CWE
weakness is cataloged as structured data (`WeaknessEntry.cite` names the
authoritative source url, never hand-transcribed); a capability kind on a
`Node.may` atom auto-instantiates the weakness obligations the charter's
capability table maps it to. THREAT001 (catalog completeness): every CWE
id a selected baseline VIEW names has a catalog entry or an explicit
`out_of_scope` entry. THREAT003 (discharge completeness): every FIRED
obligation (a node declares the `may` kind that drags it in) has a
corresponding `Claim`, evaluated at or above the catalog's required rung,
never REFUTED, and -- if assumed -- owned with a review date.

Phase B (T-0112, docs/strata/threat.md#phasing item B) adds THREAT002
(precondition/capability completeness), still model-level: every
capability kind a node declares via `may` is CLASSIFIED -- it names a
sink the catalog recognizes (`_entries_by_capability_kind`, the same join
`_fired_obligations` uses) or is explicitly excused by a `BenignCapability` entry,
mirroring THREAT001's `OutOfScopeEntry`. Unclassified is a violation,
deny-by-default (charter law 2) -- the "never forget" mechanism (threat.md
#the-exhaustiveness-proof-the-point, item 2).

Phase C (T-0113, docs/strata/threat.md#phasing item C) closes the
code-level half phase B deferred, in two independent pieces:

1. Code-level capability classification/declaration (THREAT004/THREAT005):
   `check_effect_completeness` joins `_effects.py::extract_effects`'s
   observed net/fs/exec sinks into the SAME taxonomy join
   (`_entries_by_capability_kind`) THREAT002 and `_fired_obligations`
   already use. An observed sink whose owning node declares no matching
   `may` capability is THREAT004 (reusing `check_capability_conformance`'s
   join, not re-detecting it); an observed sink whose kind the catalog
   does not recognize (and no `BenignCapability` excuses it) is THREAT005
   -- the code-level mirror of THREAT002's model-level "every capability
   ... is classified" (threat.md#the-exhaustiveness-proof-the-point, item
   2). Still v0's kind-only join (`_effects.py`'s own documented scope
   cut: no destination-scoped capability grammar yet).

2. Mitigation chokepoint verification (still THREAT003, tightened twice):
   a Claim named `weakness:<cwe-id>:<node-id>` used to be accepted as a
   discharge purely by existing at the right rung -- it could be ANY
   claim body, "declared somewhere" (threat.md#phasing item C) rather
   than a proof the mitigation actually interposes on every path from a
   foreign source to the firing node.

   Round 1 required the body to be a `NoFlow(src=<foreign>, dst=<node_id>)`
   claim -- the shape `_eval_noflow` (`_claims.py`) already proves over the
   closure engine's boundary-aware `reachable` (a flow carrying ANY
   `Boundary` stops the influence walk, docs/strata/kernel.md). Review
   round 2 caught the gap this leaves: `reachable`'s barrier test does not
   look at a boundary's `direction`/`predicate` at all, so a PROVED
   `NoFlow` says only "SOME boundary sits on every path" -- a `declassify`
   boundary with an unrelated `predicate` (e.g. `"legal_review_signed_off"`
   discharging a CWE-79 `output_encoding` obligation) proves the SAME
   `NoFlow` a genuine `endorse output_encoding` boundary would. "Declared
   somewhere" had shrunk from "any claim" to "any boundary of any kind",
   still not the catalog's actual `needs mitigation <name>` requirement.

   `_mitigation_is_chokepoint` closes this: it isolates the boundaries
   that carry the catalog's EXACT required mitigation
   (`direction=ENDORSE` and `predicate == entry.mitigation`,
   `_matching_boundary_ids`) and re-evaluates the SAME `NoFlow` claim on a
   model copy with every OTHER boundary removed (`_restricted_to_
   boundaries`) -- still the SAME `evaluate_claims`/`_eval_noflow`/
   `reachable` call, no new closure primitive. If the claim still
   PROVES/EVIDENCES over that restricted model, the correctly-kinded
   boundaries alone are sufficient to cut every path the closure walks:
   a genuine chokepoint, not a boundary of convenience. Quantifier
   documented on `_mitigation_is_chokepoint` itself (not "every path is
   independently proved cut by a matching boundary" -- see its docstring
   for the precise cut this makes and does not make).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._claims import evaluate_claims
from ._code_binding import CodeBinding
from ._effects import (
    CapabilityViolation,
    ObservedEffect,
    _may_kind,
    check_capability_conformance,
    extract_effects,
)
from ._errors import StrataError
from ._models import (
    BoundaryDirection,
    Claim,
    ClaimResult,
    KernelModel,
    Node,
    NoFlow,
    Rung,
    Verdict,
)

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


# frob:doc docs/strata/threat.md#phasing
class BenignCapability(BaseModel):
    """A `may` capability KIND explicitly excused from THREAT002's sink
    taxonomy, with a reason -- mirrors `OutOfScopeEntry` for THREAT001
    (docs/strata/threat.md#phasing item B); an unmapped kind must be
    named here or THREAT002 fails closed on it."""

    model_config = ConfigDict(frozen=True)

    kind: str
    reason: str = Field(min_length=1)


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


def _entries_by_capability_kind(
    catalog: tuple[WeaknessEntry, ...],
) -> dict[str, tuple[WeaknessEntry, ...]]:
    """capability KIND (the `_effects.py::_may_kind` convention) -> the
    `catalog` entries its declaration auto-instantiates (docs/strata/
    threat.md#capabilities-drag-in-obligations). The ONE home this join is
    computed in: `_fired_obligations` (instantiation) and
    `check_capability_completeness` (THREAT002's sink taxonomy) both call
    this over the SAME `catalog` argument they were given, so a caller who
    passes a non-default catalog can never see the two checks diverge
    (charter: no duplication) -- there is no module-level cache keyed to
    `CWE_CATALOG` to go stale against a different catalog."""
    by_kind: dict[str, list[WeaknessEntry]] = {}
    for entry in catalog:
        if entry.capability_kind is not None:
            by_kind.setdefault(entry.capability_kind, []).append(entry)
    return {kind: tuple(entries) for kind, entries in by_kind.items()}


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class ThreatViolation(BaseModel):
    """One THREAT001/THREAT002/THREAT003 finding: a rule id, an optional
    CWE id, an optional capability kind, an optional firing node, and a
    human detail -- never a silent gap. THREAT002 sets `capability` and
    leaves `cwe` empty (no CWE is implicated -- the capability itself is
    unclassified); THREAT001/THREAT003 leave `capability` `None`."""

    model_config = ConfigDict(frozen=True)

    rule: str  # "THREAT001" | "THREAT002" | "THREAT003"
    cwe: str = ""
    capability: str | None = None
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


def _capability_violation(kind: str, node_id: str) -> ThreatViolation:
    """THREAT002 violation helper: deny-by-default unclassified capability
    kind (docs/strata/threat.md#phasing item B)."""
    _log.warning(
        "threat: THREAT002 capability %r on %s matches no sink taxonomy "
        "entry and no BenignCapability excuse",
        kind,
        node_id,
    )
    return ThreatViolation(
        rule="THREAT002",
        capability=kind,
        node=node_id,
        detail=f"capability kind {kind!r} matches no std.cwe sink taxonomy "
        "entry and no BenignCapability excuse",
    )


# frob:doc docs/strata/threat.md#phasing
def check_capability_completeness(
    model: KernelModel,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
    benign: tuple[BenignCapability, ...] = (),
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT002: every capability kind a node declares via a `may` atom is
    classified -- it names a sink the `catalog` recognizes (its
    `capability_kind`) or is explicitly excused by a `BenignCapability`;
    an unclassified kind is a violation, deny-by-default (docs/strata/
    threat.md#phasing item B). The model-level half of "every capability
    ... is classified" (threat.md#the-exhaustiveness-proof-the-point,
    item 2); the code-level half is phase C (module docstring).

    "Classified" means: a `may` kind present in `_entries_by_capability_
    kind(catalog)` -- the SAME join `_fired_obligations` computes over the
    same `catalog` argument, so this can never diverge from what actually
    fires (charter: no duplication)."""
    known = frozenset(_entries_by_capability_kind(catalog))
    excused = {entry.kind for entry in benign}

    violations: list[ThreatViolation] = []
    for node in sorted(model.nodes, key=lambda n: n.id):
        kinds = sorted({_may_kind(atom) for atom in node.may})
        for kind in kinds:
            if kind not in known and kind not in excused:
                violations.append(_capability_violation(kind, node.id))
    return Ok(tuple(violations))


def _fired_obligations(
    model: KernelModel, catalog: tuple[WeaknessEntry, ...]
) -> list[tuple[str, WeaknessEntry]]:
    """Every (node_id, WeaknessEntry) pair whose obligation fires: the node
    declares a `may` atom of the entry's `capability_kind`."""
    by_kind = _entries_by_capability_kind(catalog)

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


# frob:doc docs/strata/threat.md#phasing
_FOREIGN_TRUST = "foreign"


# frob:doc docs/strata/threat.md#phasing
def _discharges_as_chokepoint(
    nodes_by_id: dict[str, Node], node_id: str, claim: Claim
) -> bool:
    """Whether `claim` PROVES a mitigation boundary sits on every path from a
    foreign source to `node_id`, not merely "declared somewhere" (docs/
    strata/threat.md#phasing item C, T-0113).

    Requires `claim.body` to be a `NoFlow(src=<foreign>, dst=node_id)` --
    exactly the shape `_eval_noflow` (`_claims.py`) already proves over the
    closure engine's boundary-aware `reachable`: a REFUTED verdict there
    means some path survives with no boundary in the way, and
    `_check_one_discharge` already rejects a REFUTED claim, so requiring
    THIS shape is what turns "a claim exists" into "the mitigation is a
    proven chokepoint" -- no new detection, no new closure call, the SAME
    `NoFlow` evaluation every other flow-cutting claim in the kernel
    already relies on. `src` may name the `"foreign"` trust level directly
    (expands to every foreign-trust node, `_claims.py::_expand`) or a
    single node whose own declared `trust` is `"foreign"`.
    """
    if not isinstance(claim.body, NoFlow):
        return False
    if claim.body.dst != node_id:
        return False
    src = claim.body.src
    if src == _FOREIGN_TRUST:
        return True
    src_node = nodes_by_id.get(src)
    return src_node is not None and src_node.trust == _FOREIGN_TRUST


def _matching_boundary_ids(model: KernelModel, entry: WeaknessEntry) -> frozenset[str]:
    """Boundary ids that carry the EXACT mitigation `entry` requires: an
    `ENDORSE`-direction boundary (a chokepoint raises integrity, it never
    lowers confidentiality -- `declassify` is the opposite operation and
    can never be a weakness mitigation, docs/strata/kernel.md#data-models)
    whose `predicate` equals `entry.mitigation` (the catalog's `needs
    mitigation <name>` clause, docs/strata/threat.md#the-catalog-stdcwe).

    A boundary of the wrong direction, or an `endorse` boundary with an
    unrelated predicate (e.g. `"legal_review_signed_off"` sitting in for a
    CWE-79 `output_encoding` requirement), is excluded -- review round 2's
    gap: `_eval_noflow`'s `reachable` treats ANY boundary as a barrier
    regardless of kind, so without this filter a claim could be "proved"
    by a boundary that mitigates nothing relevant to this weakness.
    """
    return frozenset(
        boundary.id
        for boundary in model.boundaries
        if boundary.direction is BoundaryDirection.ENDORSE
        and boundary.predicate == entry.mitigation
    )


def _restricted_to_boundaries(
    model: KernelModel, keep_ids: frozenset[str], claim: Claim
) -> KernelModel:
    """`model` with every boundary NOT in `keep_ids` removed and `claims`
    narrowed to just `claim` -- the input to `_mitigation_is_chokepoint`'s
    re-evaluation (docs/strata/threat.md#phasing item C). Narrowing
    `claims` to one is an optimization only (`evaluate_claims` would
    otherwise re-evaluate every other claim in the model against the
    restricted boundary set for no reason this check needs)."""
    kept = tuple(b for b in model.boundaries if b.id in keep_ids)
    return model.model_copy(update={"boundaries": kept, "claims": (claim,)})


# frob:doc docs/strata/threat.md#phasing
def _claim_holds(model: KernelModel, claim: Claim) -> bool:
    """Whether `claim` evaluates PROVED/EVIDENCED (`evaluate_claims`) over
    `model` -- the one place `_mitigation_is_chokepoint` calls into the
    closure engine, reused for both the vacuous-path short-circuit and the
    matching-boundary re-evaluation below (charter: no duplication)."""
    result = evaluate_claims(model)
    if result.is_err:
        _log.warning(
            "threat: mitigation-chokepoint re-evaluation for %s failed: %s",
            claim.id,
            result.danger_err,
        )
        return False
    for claim_result in result.danger_ok:
        if claim_result.claim_id == claim.id:
            return claim_result.verdict in (Verdict.PROVED, Verdict.EVIDENCED)
    return False


def _mitigation_is_chokepoint(
    model: KernelModel, entry: WeaknessEntry, claim: Claim
) -> bool:
    """Whether the boundaries carrying `entry`'s EXACT required mitigation
    (`_matching_boundary_ids`) are, by themselves, sufficient to make
    `claim`'s `NoFlow` hold -- i.e. the catalog-correct mitigation is a
    genuine chokepoint, not merely one boundary among several (of possibly
    unrelated kinds) that happen to also block a path (docs/strata/
    threat.md#phasing item C, review round 2).

    Vacuous-path short-circuit FIRST: if `claim` already holds with EVERY
    boundary removed (`_restricted_to_boundaries(model, frozenset(),
    claim)`), no path from the claim's source to its sink exists in the
    closure AT ALL -- the `NoFlow` is proved by absence of a flow, not by
    any boundary, so there is nothing for a mitigation to be a chokepoint
    ON. Requiring a matching boundary in this case would reject models
    that were already correctly PROVED before phase C's tightening
    (`_check_one_discharge`'s pre-T-0113 fixtures declare no flows/
    boundaries at all) -- a real regression, not the reviewer-flagged gap.

    Otherwise, re-evaluates the SAME claim (`_claim_holds`, so the SAME
    `_eval_noflow`/`reachable` closure walk `_discharges_as_chokepoint`'s
    round-1 shape check already leans on) over a model copy with every
    OTHER boundary removed (`_restricted_to_boundaries`) -- no new closure
    primitive, no new `strata_core` call.

    Quantifier: this is "the matching boundaries alone cut the closure the
    SAME `NoFlow` walk already computes" -- sound (a PROVED result here
    means the matching boundaries really do interpose on every path
    `reachable` traverses, since removing MORE boundaries can only ADD
    reachability, never remove it) but not maximal: a path blocked ONLY by
    a non-matching boundary (with no matching boundary anywhere on it) is
    invisible to per-path attribution, since `FactBase.reachable` reports
    reachability, not which specific boundary blocked which specific path
    (docs/strata/kernel.md#fact-base). If EVERY path happens to carry a
    matching boundary, this proves True exactly; if only SOME paths do
    while others are saved solely by a non-matching boundary, this proves
    False (the restricted-model NoFlow is REFUTED, since removing the
    non-matching boundary that had been covering that path reopens it) --
    which is the conservative, deny-by-default direction (charter law 2).
    No unsound acceptance is possible; the disclosed gap is precision, not
    soundness: a model needing a per-path (rather than per-model)
    mitigation-kind proof is out of v0's scope, noted here and in
    threat.md rather than silently assumed away.
    """
    if _claim_holds(_restricted_to_boundaries(model, frozenset(), claim), claim):
        return True
    matching = _matching_boundary_ids(model, entry)
    if not matching:
        return False
    return _claim_holds(_restricted_to_boundaries(model, matching, claim), claim)


def _check_one_discharge(
    entry: WeaknessEntry,
    node_id: str,
    claims_by_id: dict[str, Claim],
    results_by_id: dict[str, ClaimResult],
    nodes_by_id: dict[str, Node],
    model: KernelModel,
) -> ThreatViolation | None:
    """One fired obligation's discharge check: present, shaped as a proven
    mitigation chokepoint of the CORRECT kind, not REFUTED, at or above the
    catalog's required rung, and -- if assumed -- owned with a review date
    (docs/strata/threat.md#the-exhaustiveness-proof-the-point, item 3;
    chokepoint shape + mitigation-kind check added phase C, docs/strata/
    threat.md#phasing item C).

    The mitigation-kind check (`_mitigation_is_chokepoint`) is skipped for
    an `assumed` claim, exactly like the REFUTED check above it: an assumed
    claim is a human-owned TCB entry never run through the closure at all
    (`_claims.py::evaluate_claims` short-circuits assumed claims to the
    `ASSUMED` verdict before touching `_eval_noflow`), so there is no
    closure-derived proof to inspect for boundary kind -- the owner/review
    gate a few lines up is the only accountability an assume gets, same as
    every other claim form in this module.
    """
    claim_id = _discharge_claim_id(entry.id, node_id)
    claim = claims_by_id.get(claim_id)
    if claim is None:
        return _discharge_violation(
            entry, node_id, f"no claim {claim_id!r} discharges this obligation"
        )
    if not _discharges_as_chokepoint(nodes_by_id, node_id, claim):
        return _discharge_violation(
            entry,
            node_id,
            f"claim {claim_id!r} does not prove a mitigation chokepoint -- "
            f"body must be NoFlow(src=<foreign source>, dst={node_id!r})",
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
    if not claim.assumed and not _mitigation_is_chokepoint(model, entry, claim):
        return _discharge_violation(
            entry,
            node_id,
            f"claim {claim_id!r} proves a chokepoint but not of the required "
            f"mitigation kind -- no ENDORSE boundary with predicate "
            f"{entry.mitigation!r} is sufficient alone to block every path",
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
    nodes_by_id = {node.id: node for node in model.nodes}
    results = evaluate_claims(model)
    if results.is_err:
        return Err(results.danger_err)
    results_by_id = {r.claim_id: r for r in results.danger_ok}

    violations: list[ThreatViolation] = []
    for node_id, entry in sorted(fired, key=lambda pair: (pair[1].id, pair[0])):
        violation = _check_one_discharge(
            entry, node_id, claims_by_id, results_by_id, nodes_by_id, model
        )
        if violation is not None:
            violations.append(violation)
    return Ok(tuple(violations))


def _undeclared_sink_violation(violation: CapabilityViolation) -> ThreatViolation:
    """THREAT004 violation helper: an observed sink whose owning node declares
    no `may` capability of the matching kind -- the code-level "undeclared
    capability in code is an error" kicker (docs/strata/threat.md
    #capabilities-drag-in-obligations)."""
    _log.warning(
        "threat: THREAT004 %s:%d %s effect (%s) on %s has no declared may "
        "capability of that kind",
        violation.file,
        violation.line,
        violation.kind,
        violation.needle,
        violation.component,
    )
    return ThreatViolation(
        rule="THREAT004",
        capability=violation.kind,
        node=violation.component,
        detail=f"observed {violation.kind} effect at {violation.file}:"
        f"{violation.line} ({violation.needle!r}) has no declared may "
        "capability of that kind",
    )


def _unclassified_sink_violation(effect: ObservedEffect, owner: str) -> ThreatViolation:
    """THREAT005 violation helper: an extracted sink whose kind the catalog
    does not recognize and no `BenignCapability` excuses -- the code-level
    mirror of THREAT002 (docs/strata/threat.md#phasing item C)."""
    _log.warning(
        "threat: THREAT005 %s:%d %s effect (%s) on %s matches no std.cwe sink "
        "taxonomy entry and no BenignCapability excuse",
        effect.file,
        effect.line,
        effect.kind,
        effect.needle,
        owner,
    )
    return ThreatViolation(
        rule="THREAT005",
        capability=effect.kind,
        node=owner,
        detail=f"observed {effect.kind} effect at {effect.file}:{effect.line} "
        f"({effect.needle!r}) matches no std.cwe sink taxonomy entry and no "
        "BenignCapability excuse",
    )


# frob:doc docs/strata/threat.md#phasing
def check_effect_completeness(
    model: KernelModel,
    binding: CodeBinding,
    root: Path,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
    benign: tuple[BenignCapability, ...] = (),
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT004 + THREAT005: the code-level half of "every capability ...
    is classified" phase B deferred (docs/strata/threat.md#phasing item C,
    T-0113) -- joins `_effects.py`'s extracted net/fs/exec sinks into the
    SAME taxonomy join THREAT002 uses (`_entries_by_capability_kind`), over
    the SAME `catalog`/`benign` arguments, so code-level and model-level
    classification can never diverge (charter: no duplication).

    THREAT004 reuses `check_capability_conformance`'s undeclared-capability
    join directly (no re-detection): an observed sink on a node with no
    matching `may` declaration. THREAT005 is the sink-classification half:
    an observed sink whose `kind` names no `capability_kind` the `catalog`
    recognizes, unless a `BenignCapability` excuses it.
    """
    known = frozenset(_entries_by_capability_kind(catalog))
    excused = {entry.kind for entry in benign}

    conformance = check_capability_conformance(model, binding, root)
    undeclared = tuple(_undeclared_sink_violation(v) for v in conformance.violations)

    unclassified = tuple(
        _unclassified_sink_violation(effect, binding.owner[effect.file])
        for effect in extract_effects(binding, root)
        if effect.kind not in known and effect.kind not in excused
    )
    return Ok(undeclared + unclassified)


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
def evaluate_threats(
    model: KernelModel,
    view: str,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
    out_of_scope: tuple[OutOfScopeEntry, ...] = (),
    benign: tuple[BenignCapability, ...] = (),
    binding: CodeBinding | None = None,
    root: Path | None = None,
) -> Result[ThreatReport, StrataError]:
    """The strata-level threat-audit entrypoint: THREAT001 + THREAT002 +
    THREAT003 over `model` against the selected baseline `view` (docs/
    strata/threat.md#the-exhaustiveness-proof-the-point); THREAT004 +
    THREAT005 (the code-level join, T-0113) run too when both `binding`
    and `root` are given -- omitted by default since design-level-only
    callers have no code tree to bind (charter law 2: an absent join is
    never silently assumed clean, it is simply not run; a caller wanting
    the full phase C proof must pass both). Gate wiring (`frob check`
    surfacing this as a diagnostic) is a follow-up once T-0080's sys_gate
    lands -- this function is the seam that follow-up calls into, kept
    deliberately gate-agnostic (no `src/frob/gates` import here).
    """
    catalog_violations = check_catalog_completeness(view, catalog, out_of_scope)
    if catalog_violations.is_err:
        return Err(catalog_violations.danger_err)
    capability_violations = check_capability_completeness(model, catalog, benign)
    if capability_violations.is_err:
        return Err(capability_violations.danger_err)
    discharge_violations = check_discharge_completeness(model, catalog)
    if discharge_violations.is_err:
        return Err(discharge_violations.danger_err)
    effect_violations: tuple[ThreatViolation, ...] = ()
    if binding is not None and root is not None:
        effects_result = check_effect_completeness(
            model, binding, root, catalog, benign
        )
        if effects_result.is_err:
            return Err(effects_result.danger_err)
        effect_violations = effects_result.danger_ok
    all_violations = (
        *catalog_violations.danger_ok,
        *capability_violations.danger_ok,
        *discharge_violations.danger_ok,
        *effect_violations,
    )
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
    "BenignCapability",
    "OutOfScopeEntry",
    "ThreatReport",
    "ThreatViolation",
    "WeaknessEntry",
    "check_capability_completeness",
    "check_catalog_completeness",
    "check_discharge_completeness",
    "check_effect_completeness",
    "evaluate_threats",
]
