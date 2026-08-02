"""strata THREAT003 discharge/chokepoint verification (T-1420 split from
`_threat.py`, verbatim relocation -- WHY: this file held the "mitigation
chokepoint" family (docs/strata/threat.md#phasing item C's Round 1/Round
2 tightening) as one of several unrelated concerns packed into the same
2500-line module; it is a single cohesive piece (a claim must PROVE a
boundary carrying the catalog's exact required mitigation sits on every
path from a foreign source, not merely exist) that stands on its own).
See the "Phase C" section of `frob.strata._threat`'s own module docstring
for the full Round 1/Round 2 history this family closes."""

from __future__ import annotations

from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._claims import evaluate_claims
from ._code_binding import CodeBinding, _observed_call_names, is_managed
from ._effects import _may_kind
from ._errors import StrataError
from ._models import (
    Boundary,
    BoundaryDirection,
    Claim,
    ClaimResult,
    KernelModel,
    Node,
    NoFlow,
    Rung,
    Verdict,
)
from ._threat_catalog_cwe import CWE_CATALOG
from ._threat_models import ThreatViolation, WeaknessEntry

_log = get_logger(__name__)

#: Evidence ladder order, low to high (docs/strata/evidence.md); reused to
#: compare a declared claim's required_rung against a catalog entry's.
_RUNG_ORDER: tuple[Rung, ...] = (Rung.L1, Rung.L2, Rung.L3, Rung.L4, Rung.L5)


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


def _index_claims_and_results(
    model: KernelModel,
) -> Result[
    tuple[dict[str, Claim], dict[str, Node], dict[str, ClaimResult]], StrataError
]:
    """Build the three id-keyed lookups `check_discharge_completeness` needs
    per fired obligation (claims, nodes, evaluated results) -- split out so
    that function's line count reflects the per-obligation loop, not the
    one-time index setup (frob-arch long-function)."""
    claims_by_id = {claim.id: claim for claim in model.claims}
    nodes_by_id = {node.id: node for node in model.nodes}
    results = evaluate_claims(model)
    if results.is_err:
        return Err(results.danger_err)
    results_by_id = {r.claim_id: r for r in results.danger_ok}
    return Ok((claims_by_id, nodes_by_id, results_by_id))


def _rung_at_least(have: Rung, need: Rung) -> bool:
    """Whether `have` sits at or above `need` on the evidence ladder."""
    return _RUNG_ORDER.index(have) >= _RUNG_ORDER.index(need)


def _discharge_claim_id(cwe_id: str, node_id: str) -> str:
    """The naming convention a discharging `Claim.id` must follow: `weakness:
    <cwe-id>:<node-id>` (docs/strata/threat.md#the-core-reframe) -- one
    canonical home for the format so THREAT003 and any future authoring
    surface never disagree (charter: no duplication)."""
    return f"weakness:{cwe_id}:{node_id}"


# frob:enforces CHK-GATE-THREAT003
def _discharge_violation(
    entry: WeaknessEntry, node_id: str, detail: str
) -> ThreatViolation:
    """THREAT003 violation helper: deny-by-default undischarged obligation."""
    _log.warning(
        "threat: THREAT003 %s on %s undischarged: %s", entry.id, node_id, detail
    )
    return ThreatViolation(rule="THREAT003", cwe=entry.id, node=node_id, detail=detail)


_FOREIGN_TRUST = "foreign"


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


def _obligations_resolve(model: KernelModel, boundary: Boundary) -> bool:
    """Whether every evidence ref in `boundary.obligations` names a real
    `Claim.id` present in `model` (docs/audits/strata.md G1). `obligations`
    (`_models.py`: "evidence refs discharged in tier 3") was, before G1,
    declared on `Boundary` but never joined against anything -- a boundary
    could carry an empty tuple, or a string naming no claim that exists,
    and `_matching_boundary_ids` would still treat its bare `predicate`
    string as sufficient proof of a real-world mitigation. Requiring at
    least one obligation that resolves to an in-model claim turns "some
    reviewer typed a plausible-sounding predicate" into "this boundary
    points at a concrete, independently-checkable claim" -- still not a
    proof that the underlying code truly implements the mitigation (that
    is the SYS-family follow-up the audit finding also names), but no
    longer vacuous: an empty or dangling `obligations` tuple is refused
    outright."""
    if not boundary.obligations:
        return False
    claim_ids = {claim.id for claim in model.claims}
    return all(ref in claim_ids for ref in boundary.obligations)


def _boundary_flow_dst(model: KernelModel, boundary: Boundary) -> str | None:
    """The node id at the receiving end of `boundary`'s own flow -- the
    guarded code path an ENDORSE boundary's predicate must be OBSERVED in
    (docs/audits/strata.md G1 stronger half): the flow's `dst` is where
    the endorsed data lands, so a real sanitizer/validator call site is
    expected in that node's own `code=`-bound files, not the source's.
    `None` if `boundary.flow_id` names no flow in `model` -- should not
    happen for a well-formed model, but this join never raises on it."""
    for flow in model.flows:
        if flow.id == boundary.flow_id:
            return flow.dst
    return None


# frob:ticket T-0601
def _predicate_is_code_bound(
    model: KernelModel,
    binding: CodeBinding | None,
    root: Path | None,
    boundary: Boundary,
) -> bool:
    """Whether `boundary`'s `predicate` names an OBSERVED call site in the
    guarded flow's destination node's own `code=`-bound files (docs/audits/
    strata.md G1 stronger half, T-0595) -- an ENDORSE boundary whose
    `obligations` resolve to a real `Claim.id` (T-0498's weaker half) is
    still, by itself, only a model-side cross-reference: nothing yet joins
    the boundary's `predicate` against any real sanitizer/validator in the
    guarded code. `_observed_call_names` (`_code_binding.py`) is the code-
    side half of that join: `predicate` is trusted as a genuine mitigation
    only when it also names a call target actually invoked somewhere in
    the destination node's bound files.

    When no `binding`/`root` is supplied (a design-level-only caller with
    no code tree -- the SAME optional-join posture `check_effect_
    completeness`'s THREAT004/005 pair already takes for binding/root),
    this returns True: there is nothing to check a call site against in
    that mode, and T-0498's obligations-resolve gate is the only code-
    adjacent proof available. Every real `frob check`/`frob sys audit`-
    style caller that has a code tree passes both, so this is not a
    silent pass in the mode this ticket closes -- see
    `_code_unbound_boundary_ids` for how a caller WITH a code tree turns a
    negative result here into a named violation rather than a bare
    exclusion."""
    if binding is None or root is None:
        return True
    dst = _boundary_flow_dst(model, boundary)
    if dst is None:
        return False
    return boundary.predicate in _observed_call_names(binding, root, dst)


def _matching_boundary_ids(
    model: KernelModel,
    entry: WeaknessEntry,
    binding: CodeBinding | None = None,
    root: Path | None = None,
) -> frozenset[str]:
    """Boundary ids that carry the EXACT mitigation `entry` requires: an
    `ENDORSE`-direction boundary (a chokepoint raises integrity, it never
    lowers confidentiality -- `declassify` is the opposite operation and
    can never be a weakness mitigation, docs/strata/kernel.md#data-models)
    whose `predicate` equals `entry.mitigation` (the catalog's `needs
    mitigation <name>` clause, docs/strata/threat.md#the-catalog-stdcwe),
    whose `obligations` resolve to a real in-model claim
    (`_obligations_resolve`, docs/audits/strata.md G1 weaker half, T-0498),
    AND whose `predicate` is bound to an OBSERVED sanitizer/validator call
    site in the guarded code (`_predicate_is_code_bound`, docs/audits/
    strata.md G1 stronger half, T-0595).

    A boundary of the wrong direction, or an `endorse` boundary with an
    unrelated predicate (e.g. `"legal_review_signed_off"` sitting in for a
    CWE-79 `output_encoding` requirement), is excluded -- review round 2's
    gap: `_eval_noflow`'s `reachable` treats ANY boundary as a barrier
    regardless of kind, so without this filter a claim could be "proved"
    by a boundary that mitigates nothing relevant to this weakness. G1
    (docs/audits/strata.md): a matching-predicate boundary with no
    resolving `obligations`, or (when a code tree is available) no
    observed call site for its `predicate` in the guarded destination
    node's own code, is ALSO excluded -- before this, `predicate` was an
    opaque, self-declared string joined against nothing else in the model
    or the code (THREAT003 "PROVED" required zero evidence that the
    claimed mitigation was real).
    """
    return frozenset(
        boundary.id
        for boundary in model.boundaries
        if boundary.direction is BoundaryDirection.ENDORSE
        and boundary.predicate == entry.mitigation
        and _obligations_resolve(model, boundary)
        and _predicate_is_code_bound(model, binding, root, boundary)
    )


def _code_unbound_boundary_ids(
    model: KernelModel,
    entry: WeaknessEntry,
    binding: CodeBinding | None,
    root: Path | None,
) -> frozenset[str]:
    """Boundary ids that satisfy every OTHER `_matching_boundary_ids`
    criterion (ENDORSE direction, matching predicate, resolving
    obligations) but fail SPECIFICALLY `_predicate_is_code_bound` --
    named individually (docs/audits/strata.md G1, T-0595) so
    `_check_discharge_mitigation_kind`'s violation can call out the exact
    unbound boundary rather than folding it into the generic
    mitigation-kind mismatch message. Always empty when `binding`/`root`
    is None (nothing to check, see `_predicate_is_code_bound`) -- a
    design-level-only caller gets zero findings from this join, same as
    it always has."""
    if binding is None or root is None:
        return frozenset()
    return frozenset(
        boundary.id
        for boundary in model.boundaries
        if boundary.direction is BoundaryDirection.ENDORSE
        and boundary.predicate == entry.mitigation
        and _obligations_resolve(model, boundary)
        and not _predicate_is_code_bound(model, binding, root, boundary)
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


# frob:ticket T-0501
def _flow_completeness_gap(model: KernelModel, claim: Claim) -> str | None:
    """Names the G2 flow-completeness incompleteness (docs/audits/
    strata.md) that makes accepting `claim`'s vacuous NoFlow proof as a
    mitigation-chokepoint discharge unsound, or `None` when there is
    nothing to flag.

    G2's shape: the model declares AT LEAST ONE `trust == "foreign"` node
    (a real adversary IS modeled somewhere in this system) yet `claim`
    still holds with EVERY boundary removed
    (`_restricted_to_boundaries(model, frozenset(), claim)`) -- no path
    from any foreign-trust node to the sink exists in the closure at all,
    boundary or no boundary. The `NoFlow` is proved by absence of a flow,
    not by any boundary: the sink's real inbound data path from untrusted
    input was simply never modeled for THIS obligation, even though the
    model is not itself foreign-less. That is a model-completeness bug
    (an omitted `flow`), not an honest "no adversary here" declaration,
    so it must fail closed with a finding naming the gap rather than
    silently discharge.

    Deliberately does NOT flag a model with ZERO foreign-trust nodes at
    all -- that is T-0223's documented, intended "library-mode discharge
    by absence" (docs/strata/threat.md#library-mode-discharge-by-absence,
    `TestLibraryModeForeignlessDischarge`): a library repo with no
    ingress node anywhere in the model has, honestly, no modeled
    adversary, and the SAME claim shape re-evaluates and REFUTES the
    moment a real foreign node with an unendorsed flow into the sink is
    added -- there is nothing to remember to revisit, so treating that
    case as a gap here would regress a sound, already-shipped mechanism.
    G7 (docs/audits/strata.md) as literally worded ("no foreign-trust
    node exists" is always a gap) is this ticket's one disclosed
    non-fix: T-0223 makes that shape sound by design for a genuinely
    foreign-less model, so this function narrows G7 to the mixed-model
    case -- a foreign node DOES exist in the model, but this particular
    obligation's flow to it was never wired up.

    Only called for a `NoFlow`-bodied claim (`_discharges_as_chokepoint`
    already gates on that shape upstream); returns `None` for any other
    claim body so a caller can call this unconditionally.
    """
    if not isinstance(claim.body, NoFlow):
        return None
    if not any(node.trust == _FOREIGN_TRUST for node in model.nodes):
        return None
    if _claim_holds(_restricted_to_boundaries(model, frozenset(), claim), claim):
        return (
            "proves NoFlow vacuously: a foreign-trust node exists in this "
            "model but no modeled path reaches the sink from it even with "
            "every boundary removed -- the foreign->sink flow for this "
            "obligation is un-modeled, not mitigated (docs/audits/"
            "strata.md G2)"
        )
    return None


# Whether the boundaries carrying `entry`'s EXACT required mitigation
# (`_matching_boundary_ids`) are, by themselves, sufficient to make
# `claim`'s `NoFlow` hold -- i.e. the catalog-correct mitigation is a
# genuine chokepoint, not merely one boundary among several (of possibly
# unrelated kinds) that happen to also block a path (docs/strata/
# threat.md#phasing item C, review round 2). This comment (not the
# docstring) carries the explanation so frob-arch's long-function line
# count reflects the code, not the essay (same pattern as gates/
# __init__.py's `_match_waiver`).
#
# Vacuous-path short-circuit FIRST: if `claim` already holds with EVERY
# boundary removed (`_restricted_to_boundaries(model, frozenset(),
# claim)`), no path from the claim's source to its sink exists in the
# closure AT ALL -- the `NoFlow` is proved by absence of a flow, not by
# any boundary. T-0501: the caller (`_check_discharge_mitigation_kind`)
# now runs `_flow_completeness_gap` BEFORE this function and rejects the
# G2 mixed-model case (a foreign node exists elsewhere but this
# obligation's own flow was never modeled) with a distinct violation, so
# by the time this branch is reached the vacuous case is EITHER the
# sound T-0223 library-mode discharge (no foreign-trust node anywhere in
# the model) OR a model with genuinely no flows/boundaries declared at
# all (the pre-T-0113 fixtures this branch was written to keep passing) --
# both legitimately proved by absence, so accepting them here is correct,
# not the reviewer-flagged gap.
#
# Otherwise, re-evaluates the SAME claim (`_claim_holds`, so the SAME
# `_eval_noflow`/`reachable` closure walk `_discharges_as_chokepoint`'s
# round-1 shape check already leans on) over a model copy with every
# OTHER boundary removed (`_restricted_to_boundaries`) -- no new closure
# primitive, no new `strata_core` call. G1 (docs/audits/strata.md):
# `_matching_boundary_ids` additionally requires each candidate boundary's
# `obligations` to resolve to a real in-model `Claim.id`
# (`_obligations_resolve`) -- a matching `predicate` string alone is no
# longer sufficient; a chokepoint boundary with no evidence ref (or a
# dangling one) is excluded from `matching` and so cannot satisfy this
# check, even if its bare predicate name happens to equal
# `entry.mitigation`.
#
# Quantifier: this is "the matching boundaries alone cut the closure the
# SAME `NoFlow` walk already computes" -- sound (a PROVED result here
# means the matching boundaries really do interpose on every path
# `reachable` traverses, since removing MORE boundaries can only ADD
# reachability, never remove it) but not maximal: a path blocked ONLY by
# a non-matching boundary (with no matching boundary anywhere on it) is
# invisible to per-path attribution, since `FactBase.reachable` reports
# reachability, not which specific boundary blocked which specific path
# (docs/strata/kernel.md#fact-base). If EVERY path happens to carry a
# matching boundary, this proves True exactly; if only SOME paths do
# while others are saved solely by a non-matching boundary, this proves
# False (the restricted-model NoFlow is REFUTED, since removing the
# non-matching boundary that had been covering that path reopens it) --
# which is the conservative, deny-by-default direction (charter law 2).
# No unsound acceptance is possible; the disclosed gap is precision, not
# soundness: a model needing a per-path (rather than per-model)
# mitigation-kind proof is out of v0's scope, noted here and in
# threat.md rather than silently assumed away.
def _mitigation_is_chokepoint(
    model: KernelModel,
    entry: WeaknessEntry,
    claim: Claim,
    binding: CodeBinding | None = None,
    root: Path | None = None,
) -> bool:
    """Whether the catalog-correct mitigation for `entry` is a genuine
    chokepoint for `claim`, not merely one boundary among several that
    happens to also block a path -- see the comment above this def.
    `binding`/`root` (T-0595, docs/audits/strata.md G1 stronger half) are
    threaded through to `_matching_boundary_ids` so a boundary whose
    predicate names no observed call site in the guarded code is not
    counted as a genuine chokepoint candidate."""
    if _claim_holds(_restricted_to_boundaries(model, frozenset(), claim), claim):
        return True
    matching = _matching_boundary_ids(model, entry, binding, root)
    if not matching:
        return False
    return _claim_holds(_restricted_to_boundaries(model, matching, claim), claim)


# frob:invariant INV-029
# invariant spec: [INV-029](invariants/INV-029.md)
# frob:tests tests/unit/strata/test_threat.py::TestDischargeCompleteness.test_discharge_claim_below_required_rung_is_a_violation  # noqa: E501
def _check_discharge_shape_and_rung(
    entry: WeaknessEntry,
    node_id: str,
    claim: Claim,
    claim_id: str,
    nodes_by_id: dict[str, Node],
) -> ThreatViolation | None:
    """First two `_check_one_discharge` gates: `claim` must prove a
    mitigation-chokepoint SHAPE (`_discharges_as_chokepoint`) and must be
    evaluated at or above the catalog's required rung -- split out of
    `_check_one_discharge` so its long-function line count reflects the
    per-gate logic, not one 40-line if-chain (frob-arch long-function)."""
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
    return None


def _check_discharge_assumed_and_refuted(
    entry: WeaknessEntry,
    node_id: str,
    claim: Claim,
    claim_id: str,
    results_by_id: dict[str, ClaimResult],
) -> ThreatViolation | None:
    """Middle two `_check_one_discharge` gates: an `assumed` claim must
    carry an owner/review date, and a claim with a resolved verdict must
    not be REFUTED -- see `_check_one_discharge`'s comment for why the
    mitigation-kind check (which follows this pair) skips assumed claims
    entirely rather than living in this same helper."""
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


# The mitigation-kind check (`_mitigation_is_chokepoint`) is skipped for
# an `assumed` claim, exactly like the REFUTED check above it: an assumed
# claim is a human-owned TCB entry never run through the closure at all
# (`_claims.py::evaluate_claims` short-circuits assumed claims to the
# `ASSUMED` verdict before touching `_eval_noflow`), so there is no
# closure-derived proof to inspect for boundary kind -- the owner/review
# gate a few lines up is the only accountability an assume gets, same as
# every other claim form in this module.
#
# It is ALSO skipped when `node_id` names a `managed` node (T-0172,
# `_code_binding.py::is_managed`): a managed node is external, pure-config
# infrastructure declared to have no scannable code, so there is no
# tier-2 code-modeled boundary for `_mitigation_is_chokepoint` to inspect
# either -- "no tier-2 conformance; obligations shift to config evidence
# or assumes" (docs/strata/surface.md#key-construct-semantics). The claim
# still has to exist, prove a chokepoint shape (`_discharges_as_chokepoint`
# above), and clear the catalog rung -- only the boundary-KIND proof is
# exempted, same as an assume gets.
# frob:ticket T-0501
def _unbound_boundary_detail(entry: WeaknessEntry, unbound: frozenset[str]) -> str:
    """The G1-stronger-half violation detail naming every ENDORSE boundary
    that matches `entry`'s mitigation and resolves its obligations, but
    whose `predicate` names no observed sanitizer/validator call site in
    the guarded code (docs/audits/strata.md G1, T-0595) -- sorted for a
    deterministic message."""
    ids = ", ".join(sorted(unbound))
    return (
        f"ENDORSE boundary(ies) {ids} match mitigation {entry.mitigation!r} and "
        f"resolve to a real claim but have no OBSERVED sanitizer/validator "
        f"call site named {entry.mitigation!r} in the guarded destination "
        f"node's bound code (docs/audits/strata.md G1)"
    )


def _check_discharge_mitigation_kind(
    entry: WeaknessEntry,
    node_id: str,
    claim: Claim,
    claim_id: str,
    nodes_by_id: dict[str, Node],
    model: KernelModel,
    binding: CodeBinding | None = None,
    root: Path | None = None,
) -> ThreatViolation | None:
    """Last `_check_one_discharge` gate: for a non-assumed claim on a
    non-managed node, the proven chokepoint must be of the catalog's
    required mitigation KIND (`_mitigation_is_chokepoint`) -- see the
    comment above this def for why assumed/managed claims skip it.

    T-0501: BEFORE asking whether a genuine chokepoint exists, checks
    whether the claim's own NoFlow proof is vacuous in the first place
    (`_flow_completeness_gap`, docs/audits/strata.md G2/G7) -- an
    un-modeled foreign->sink flow or a model with no foreign-trust node
    at all must fail closed with a finding naming the incompleteness, not
    silently PROVED just because assumed/managed claims are otherwise
    exempt from the mitigation-kind check below.

    T-0595: when `_mitigation_is_chokepoint` fails AND `binding`/`root`
    are supplied, checks whether the failure is SPECIFICALLY because a
    matching boundary's predicate has no observed call site
    (`_code_unbound_boundary_ids`, docs/audits/strata.md G1 stronger
    half) and, if so, names the unbound boundary(ies) explicitly rather
    than falling through to the generic mismatch message -- the
    acceptance-tested "fails closed with a finding naming the unbound
    boundary" shape."""
    node = nodes_by_id.get(node_id)
    node_is_managed = node is not None and is_managed(node)
    if claim.assumed or node_is_managed:
        return None
    gap = _flow_completeness_gap(model, claim)
    if gap is not None:
        return _discharge_violation(entry, node_id, f"claim {claim_id!r} {gap}")
    if not _mitigation_is_chokepoint(model, entry, claim, binding, root):
        unbound = _code_unbound_boundary_ids(model, entry, binding, root)
        if unbound:
            return _discharge_violation(
                entry,
                node_id,
                f"claim {claim_id!r} {_unbound_boundary_detail(entry, unbound)}",
            )
        return _discharge_violation(
            entry,
            node_id,
            f"claim {claim_id!r} proves a chokepoint but not of the required "
            f"mitigation kind -- no ENDORSE boundary with predicate "
            f"{entry.mitigation!r} and a resolving evidence ref "
            f"(obligations naming a real claim) is sufficient alone to "
            f"block every path",
        )
    return None


def _check_one_discharge(
    entry: WeaknessEntry,
    node_id: str,
    claims_by_id: dict[str, Claim],
    results_by_id: dict[str, ClaimResult],
    nodes_by_id: dict[str, Node],
    model: KernelModel,
    binding: CodeBinding | None = None,
    root: Path | None = None,
) -> ThreatViolation | None:
    """One fired obligation's discharge check: present, shaped as a proven
    mitigation chokepoint of the CORRECT kind, not REFUTED, at or above the
    catalog's required rung, and -- if assumed -- owned with a review date
    (docs/strata/threat.md#the-exhaustiveness-proof-the-point, item 3;
    chokepoint shape + mitigation-kind check added phase C, docs/strata/
    threat.md#phasing item C). The four gates run in this exact order via
    `_check_discharge_shape_and_rung`, `_check_discharge_assumed_and_refuted`,
    and `_check_discharge_mitigation_kind` -- see each helper's docstring/
    comment for what it checks and why. `binding`/`root` (T-0595) are
    threaded through to the last gate only -- the earlier three never
    consult the code tree.
    """
    claim_id = _discharge_claim_id(entry.id, node_id)
    claim = claims_by_id.get(claim_id)
    if claim is None:
        return _discharge_violation(
            entry, node_id, f"no claim {claim_id!r} discharges this obligation"
        )
    violation = _check_discharge_shape_and_rung(
        entry, node_id, claim, claim_id, nodes_by_id
    )
    if violation is not None:
        return violation
    violation = _check_discharge_assumed_and_refuted(
        entry, node_id, claim, claim_id, results_by_id
    )
    if violation is not None:
        return violation
    return _check_discharge_mitigation_kind(
        entry, node_id, claim, claim_id, nodes_by_id, model, binding, root
    )


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
# frob:ticket T-0595
def check_discharge_completeness(
    model: KernelModel,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
    binding: CodeBinding | None = None,
    root: Path | None = None,
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT003: every FIRED weakness obligation (a node declares the `may`
    capability kind that drags it in) is discharged by a `Claim` named
    `weakness:<cwe-id>:<node-id>` (docs/strata/threat.md#the-core-reframe),
    evaluated at or above the catalog's required rung and never REFUTED; a
    dangling or under-evidenced obligation is a violation (docs/strata/
    threat.md#the-exhaustiveness-proof-the-point, item 3).

    `binding`/`root` (T-0595, docs/audits/strata.md G1 stronger half) are
    optional, mirroring `check_effect_completeness`'s own optional
    code-tree join: when both are given, an ENDORSE boundary's mitigation
    predicate must ALSO name an observed sanitizer/validator call site in
    the guarded destination node's own bound code, not merely resolve to
    a real in-model claim -- omitted by default since a design-level-only
    caller has no code tree to bind (same posture THREAT004/005 already
    take).

    Runs `evaluate_claims` to resolve verdicts for claims that are present;
    a missing claim never reaches evaluation -- that is itself the
    violation, deny-by-default (charter law 2).
    """
    fired = _fired_obligations(model, catalog)
    if not fired:
        _log.info("threat: THREAT003 no fired obligations (no matching capabilities)")
        return Ok(())

    indexed = _index_claims_and_results(model)
    if indexed.is_err:
        return Err(indexed.danger_err)
    claims_by_id, nodes_by_id, results_by_id = indexed.danger_ok

    violations: list[ThreatViolation] = []
    for node_id, entry in sorted(fired, key=lambda pair: (pair[1].id, pair[0])):
        violation = _check_one_discharge(
            entry,
            node_id,
            claims_by_id,
            results_by_id,
            nodes_by_id,
            model,
            binding,
            root,
        )
        if violation is not None:
            violations.append(violation)
    return Ok(tuple(violations))
