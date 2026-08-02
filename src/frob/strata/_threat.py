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

import re
import tomllib
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import FOREIGN, CodeBinding
from ._effects import (
    CapabilityViolation,
    ObservedEffect,
    _may_kind,
    check_capability_conformance,
    extract_effects,
)
from ._errors import StrataError
from ._models import KernelModel
from ._threat_catalog_benign import DEFAULT_BENIGN_CAPABILITIES
from ._threat_catalog_cwe import (
    CWE_CATALOG,
    CWE_TOP_25_CATALOG,
    CWE_TOP_25_OUT_OF_SCOPE,
    CWE_TOP_25_VIEWS,
    VIEWS,
)
from ._threat_catalog_quality import (
    ALL_CATALOG,
    QUALITY_CATALOG,
    QUALITY_OUT_OF_SCOPE,
    QUALITY_VIEWS,
)
from ._threat_discharge import _entries_by_capability_kind, check_discharge_completeness
from ._threat_models import (
    BenignCapability,
    OutOfScopeEntry,
    ThreatReport,
    ThreatViolation,
    WeaknessEntry,
)

_log = get_logger(__name__)

#: T-0511 (strata audit G12): the two catalog families a repo-declared
#: excuse's `family` must name, each mapped to the catalog tuple(s)
#: `_family_catalog_for` checks a repo excuse's `kind` against --
#: "security" spans BOTH `CWE_CATALOG` and `CWE_TOP_25_CATALOG` (a kind
#: classified in either is already known security-side), "quality" is
#: `QUALITY_CATALOG` alone, mirroring `_threat_and_quality_gaps`
#: (`_audit.py`)'s own security/quality split -- kept local rather than
#: importing `ALL_CATALOG` (which would erase exactly the per-family
#: distinction this ticket exists to restore).
_BENIGN_EXCUSE_FAMILIES: frozenset[str] = frozenset({"security", "quality"})


def _family_catalog_for(family: str) -> tuple[WeaknessEntry, ...]:
    """T-0511: the catalog tuple a repo-declared excuse's `family` claim is
    checked against -- "security" is `CWE_CATALOG + CWE_TOP_25_CATALOG`,
    "quality" is `QUALITY_CATALOG` alone; callers must first confirm
    `family in _BENIGN_EXCUSE_FAMILIES` (this raises `KeyError` on any
    other value, deliberately -- an unchecked call is a bug, not a
    user-facing malformed-config path, which `load_repo_benign_
    capabilities` validates BEFORE calling this)."""
    return {
        "security": CWE_CATALOG + CWE_TOP_25_CATALOG,
        "quality": QUALITY_CATALOG,
    }[family]


# frob:doc docs/strata/threat.md#per-repo-benign-capability-declarations
# frob:doc docs/guides/extending/benign-capabilities.md#per-repo-declarations
# frob:ticket T-0017
# frob:ticket T-0511
def load_repo_benign_capabilities(
    root: Path,
) -> Result[tuple[BenignCapability, ...], StrataError]:
    """T-0017 (graphite adoption): the per-repo `.strata`-consuming-repo
    excuse channel `DEFAULT_BENIGN_CAPABILITIES` alone could not provide --
    a consuming repo genuinely has a capability kind (`html_render`,
    `client_storage`, ...) that maps to no `CWE_CATALOG`/`QUALITY_CATALOG`
    sink in ITS model, but the only excuse mechanism was this module's own
    hardcoded Python tuple, which no downstream repo can edit. Reads
    `frob.toml`'s `[[strata.benign_capabilities]]` array of tables (the same
    array-of-tables shape `frob.policy`'s `[[policy.*]]` already uses for
    repo-declared rules) -- each entry needs `kind`, a non-blank `reason`,
    a non-blank `caught_by` (T-0381: the compensating gate/rule/mechanism
    that catches the excused capability elsewhere, or an honest "none"
    disclosure), AND (T-0511, strata audit G12) a mandatory `family`
    naming WHICH catalog family ("security" | "quality") the excuse
    applies against (deny-by-default, charter law 2: an excuse without a
    written reason is not honest -- and, as of T-0511, without a checked
    family claim is not verifiable). A repo excuse whose `kind` is
    ALREADY classified (has a `capability_kind` entry) in the family it
    names is REJECTED at load time -- that is not a genuine gap, it is
    either a no-op or, worse, an attempt to mask an already-known sink
    under the label of an "excuse"; a kind legitimately unclassified in
    one family but classified in the OTHER (e.g. `client_storage`,
    CWE_CATALOG-classified security-side but unmapped in
    `QUALITY_CATALOG`, the T-0017 case) is exactly what `family="quality"`
    is for and stays accepted. Returns `Ok(())` for a missing `frob.toml`
    or a missing `[strata]`/`benign_capabilities` table (no repo-declared
    excuses is a valid, common case, not an error) and
    `Err(StrataError.MalformedBenignConfig)` for a present-but-invalid
    table (unparseable TOML; an entry missing `kind`/`reason`/`caught_by`/
    `family`; an unrecognized `family` value; or a `family` claim the
    catalog itself contradicts) -- fails closed rather than silently
    dropping or silently trusting a malformed/illegitimate entry, the same
    posture `_load_policy`'s sibling loaders take. Callers combine the
    result with `DEFAULT_BENIGN_CAPABILITIES` (repo entries are ADDITIONAL
    excuses, never a replacement for the built-in tier-2 vocabulary
    excuses) before passing `benign=` to `evaluate_exhaustiveness`."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        _log.info("load_repo_benign_capabilities: no frob.toml at %s", toml_path)
        return Ok(())
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.error(
            "load_repo_benign_capabilities: could not parse %s: %s", toml_path, exc
        )
        return Err(StrataError.MalformedBenignConfig)

    entries = doc.get("strata", {}).get("benign_capabilities", [])
    if not isinstance(entries, list):
        _log.error(
            "load_repo_benign_capabilities: [strata.benign_capabilities] must "
            "be an array of tables, got %s",
            type(entries).__name__,
        )
        return Err(StrataError.MalformedBenignConfig)

    excuses: list[BenignCapability] = []
    for entry in entries:
        validated = _validate_benign_entry(entry, toml_path)
        if validated.is_err:
            return Err(validated.danger_err)
        excuses.append(validated.danger_ok)

    _log.info(
        "load_repo_benign_capabilities: loaded %d repo-declared excuse(s) from %s",
        len(excuses),
        toml_path,
    )
    return Ok(tuple(excuses))


# frob:ticket T-0598
def _validate_benign_entry(
    entry: Any, toml_path: Path
) -> Result[BenignCapability, StrataError]:
    """One `[[strata.benign_capabilities]]` entry, validated (required keys
    present, `family` recognized and not already classified in its own
    catalog) and built into a `BenignCapability`, or the same
    `MalformedBenignConfig` `Err` `load_repo_benign_capabilities` itself
    returns for a bad entry (its per-entry body, split out for ARCH001 --
    T-0598)."""
    try:
        kind = entry["kind"]
        reason = entry["reason"]
        caught_by = entry["caught_by"]
        family = entry["family"]
    except (KeyError, TypeError) as exc:
        _log.error(
            "load_repo_benign_capabilities: malformed entry in %s: %s",
            toml_path,
            exc,
        )
        return Err(StrataError.MalformedBenignConfig)
    if family not in _BENIGN_EXCUSE_FAMILIES:
        _log.error(
            "load_repo_benign_capabilities: entry for kind=%r in %s names "
            "family=%r, not one of %s",
            kind,
            toml_path,
            family,
            sorted(_BENIGN_EXCUSE_FAMILIES),
        )
        return Err(StrataError.MalformedBenignConfig)
    family_known = frozenset(_entries_by_capability_kind(_family_catalog_for(family)))
    if kind in family_known:
        _log.error(
            "load_repo_benign_capabilities: entry for kind=%r in %s claims "
            "family=%r, but %r is ALREADY classified in that family's "
            "catalog -- not a genuine gap, refusing the excuse",
            kind,
            toml_path,
            family,
            kind,
        )
        return Err(StrataError.MalformedBenignConfig)
    try:
        return Ok(
            BenignCapability(
                kind=kind, reason=reason, caught_by=caught_by, family=family
            )
        )
    except (TypeError, ValidationError) as exc:
        _log.error(
            "load_repo_benign_capabilities: malformed entry in %s: %s",
            toml_path,
            exc,
        )
        return Err(StrataError.MalformedBenignConfig)


# frob:enforces CHK-GATE-THREAT001
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
# frob:invariant INV-035
# invariant spec: [INV-035](invariants/INV-035.md)
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


# frob:enforces CHK-GATE-THREAT002
# frob:enforces CWE-78
# frob:enforces CWE-79
# frob:enforces CWE-89
# frob:enforces CWE-94
# frob:enforces CWE-502
# frob:enforces CWE-639
# frob:enforces CWE-918
# frob:enforces CWE-922
# T-0684: the 8 weaknesses.yaml CWE entries this function's deny-by-default
# capability-kind check actually enforces, cross-checked against CWE_CATALOG/
# CWE_TOP_25_CATALOG's real (non-None) capability_kind rows above.
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
    taxonomy: tuple[WeaknessEntry, ...] | None = None,
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT002: every capability kind a node declares via a `may` atom is
    classified -- it names a sink `taxonomy` recognizes (its
    `capability_kind`) or is explicitly excused by a `BenignCapability`;
    an unclassified kind is a violation, deny-by-default (docs/strata/
    threat.md#phasing item B). The model-level half of "every capability
    ... is classified" (threat.md#the-exhaustiveness-proof-the-point,
    item 2); the code-level half is phase C (module docstring).

    `taxonomy` defaults to `catalog` (pre-T-0171 behavior: classify only
    against the SAME catalog whose entries this call's `view` resolves
    obligations from) -- pass `ALL_CATALOG` (or any wider union) explicitly
    when checking a NARROWER per-family catalog (e.g. `QUALITY_CATALOG`)
    so a capability kind classified elsewhere in the taxonomy (security's
    `CWE_CATALOG`) is not misreported as unclassified just because this
    family's own catalog has no entry for it (T-0171: THREAT002 fired in
    quality views for capabilities the taxonomy classifies, just not in
    QUALITY_CATALOG's narrower vocabulary -- classification is a taxonomy-
    wide fact, not a per-family one; see `ALL_CATALOG`'s comment).

    "Classified" means: a `may` kind present in `_entries_by_capability_
    kind(taxonomy)` -- when `taxonomy is None` this is the SAME join
    `_fired_obligations` computes over the same `catalog` argument, so the
    pre-T-0171 default can never diverge from what actually fires (charter:
    no duplication)."""
    known = frozenset(
        _entries_by_capability_kind(taxonomy if taxonomy is not None else catalog)
    )
    excused = {entry.kind for entry in benign}

    violations: list[ThreatViolation] = []
    for node in sorted(model.nodes, key=lambda n: n.id):
        kinds = sorted({_may_kind(atom) for atom in node.may})
        for kind in kinds:
            if kind not in known and kind not in excused:
                violations.append(_capability_violation(kind, node.id))
    return Ok(tuple(violations))


#: T-0382: a `caught_by` string is honest about naming NO compensating
#: control -- "not caught anywhere yet" -- when it starts with this marker,
#: e.g. `"none -- no CWE_CATALOG entry targets ..."` (many existing
#: `DEFAULT_BENIGN_CAPABILITIES`/`*_OUT_OF_SCOPE` entries use this exact
#: convention already). `_check_caught_by_integrity` never fails an honest
#: "none" -- fabricating a control reference to dodge the check would be
#: worse than admitting the gap; converting each honest "none" into a real
#: enforced check or a genuine compensating control is T-0383's job, not
#: this one's.
# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
CAUGHT_BY_NONE_MARKER = "none"

#: A rule-id-shaped token: 2-10 uppercase letters then 3+ digits, matching
#: this repo's own gate-rule naming convention (`THREAT002`, `SEC110`,
#: `PII010`, ...) -- `frob.gates._KNOWN_GATE_RULES`'s own id shape. Kept
#: local to this module (no import from `frob.gates`, which already
#: imports `frob.strata` -- importing back would cycle); callers that know
#: the live gate-rule set (`frob.gates`) pass it in as `known_rule_ids`.
_RULE_ID_TOKEN = re.compile(r"\b([A-Z]{2,10}[0-9]{3})\b")

#: A CWE-id-shaped token, e.g. "CWE-78" -- verified against this module's
#: own `WeaknessEntry` catalogs (`ALL_CATALOG` by default), never a
#: separately hand-maintained id list (charter: no duplication).
_CWE_ID_TOKEN = re.compile(r"\b(CWE-\d+)\b")


def _caught_by_referenced_tokens(
    caught_by: str,
) -> tuple[frozenset[str], frozenset[str]]:
    """Every rule-id-shaped and CWE-id-shaped token a `caught_by` string
    mentions, as `(rule_ids, cwe_ids)` -- the set `check_caught_by_
    integrity` verifies each actually resolves to a real control."""
    return (
        frozenset(_RULE_ID_TOKEN.findall(caught_by)),
        frozenset(_CWE_ID_TOKEN.findall(caught_by)),
    )


# frob:tests tests/unit/strata/test_threat.py::TestCaughtByUnresolvedTokens.test_unknown_rule_id_is_unresolved  # noqa: E501
# frob:ticket T-0601
def _caught_by_unresolved_tokens(
    caught_by: str,
    known_rule_ids: frozenset[str] = frozenset(),
    cataloged_ids: frozenset[str] = frozenset(),
) -> frozenset[str]:
    """Sibling of `_check_caught_by_integrity`'s per-entry
    resolution step: every rule-id-/CWE-id-shaped token `caught_by`
    references that resolves to NEITHER `known_rule_ids` (the live
    gate-rule-id set) NOR `cataloged_ids` (a catalog's own id set) --
    empty means every referenced token resolved (or none was referenced
    at all). Exists so `_compliance.py`'s own caught_by family
    (`OutOfScopeRegulation.caught_by`, COMPLIANCE004) can verify its
    excuses identically to `_check_caught_by_integrity`'s THREAT006
    without duplicating the token-extraction regexes or the deny-by-
    default resolution rule (charter: no duplication) -- callers still
    own the `CAUGHT_BY_NONE_MARKER` honest-disclosure short-circuit
    themselves, this function does not special-case it."""
    rule_ids, cwe_ids = _caught_by_referenced_tokens(caught_by)
    return (rule_ids - known_rule_ids) | (cwe_ids - cataloged_ids)


# frob:enforces CHK-GATE-THREAT006
def _caught_by_violation(
    entry_id: str, caught_by: str, unresolved: frozenset[str]
) -> ThreatViolation:
    """THREAT006 violation helper: `caught_by` names a rule id or CWE id
    that resolves to no real registered control -- deny-by-default, an
    excuse referencing a fabricated control is worse than one honestly
    naming none at all (`CAUGHT_BY_NONE_MARKER`)."""
    named = ", ".join(sorted(unresolved))
    _log.warning(
        "threat: THREAT006 %s caught_by %r references unknown control(s): %s",
        entry_id,
        caught_by,
        named,
    )
    return ThreatViolation(
        rule="THREAT006",
        cwe=entry_id if entry_id.startswith("CWE-") else "",
        detail=f"{entry_id} caught_by {caught_by!r} references unknown "
        f"control(s) that do not exist: {named}",
    )


# frob:ticket T-0601
def _check_caught_by_integrity(
    out_of_scope: tuple[OutOfScopeEntry, ...] = (),
    benign: tuple[BenignCapability, ...] = (),
    known_rule_ids: frozenset[str] = frozenset(),
    catalog: tuple[WeaknessEntry, ...] = ALL_CATALOG,
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT006 (T-0382): every `OutOfScopeEntry`/`BenignCapability.
    caught_by` that names a rule-id- or CWE-id-shaped token must reference
    a control that actually exists -- a typo'd or fabricated reference is
    a violation, deny-by-default (an excused CWE/capability "caught
    nowhere" must be visible, not silently trusted, docs/strata/threat.md
    #the-exhaustiveness-proof-the-point). An honest `"none -- ..."`
    `caught_by` (`CAUGHT_BY_NONE_MARKER`) never fails this check -- it is
    already declaring the gap, not hiding it; free text with no
    recognizable rule-id/CWE-id token is not checked further (this pass
    verifies REFERENCES resolve, it does not grade prose).

    `known_rule_ids` is the live gate-rule-id set (`frob.gates.
    _KNOWN_GATE_RULES`) -- passed in by the caller rather than imported,
    since `frob.gates` already imports `frob.strata` (import direction
    would cycle otherwise). Passing the default empty set means no
    rule-id-shaped token can ever resolve, so a caller wanting real rule-id
    verification must supply it explicitly."""
    cataloged_cwes = frozenset(entry.id for entry in catalog)
    violations: list[ThreatViolation] = []
    for entry_id, caught_by in (
        *((e.id, e.caught_by) for e in out_of_scope),
        *((e.kind, e.caught_by) for e in benign),
    ):
        if caught_by.strip().lower().startswith(CAUGHT_BY_NONE_MARKER):
            continue
        unresolved = _caught_by_unresolved_tokens(
            caught_by, known_rule_ids, cataloged_cwes
        )
        if unresolved:
            violations.append(_caught_by_violation(entry_id, caught_by, unresolved))
    return Ok(tuple(violations))


# frob:enforces CHK-GATE-THREAT004
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


# frob:enforces CHK-GATE-THREAT005
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

    # strata audit G8 (T-0497): `extract_effects` only walks
    # `binding.owner`'s non-FOREIGN files today, so every `effect.file` it
    # yields is currently guaranteed present in `binding.owner` -- but that
    # guarantee lives in a DIFFERENT module (`_effects.py`) and this join
    # trusted it implicitly via a bare `binding.owner[effect.file]`
    # subscript, which would KeyError (crash, not a fail-closed Violation)
    # the instant that filtering invariant ever drifted. `.get(...,
    # FOREIGN)` makes the same case that is unreachable today explicit and
    # non-crashing, reusing the SAME `FOREIGN` sentinel `_code_binding.py`
    # already uses for "no real owner" everywhere else (charter: no
    # duplication) -- a future drift degrades to a `FOREIGN`-owner message,
    # never a hard crash.
    unclassified = tuple(
        _unclassified_sink_violation(effect, binding.owner.get(effect.file, FOREIGN))
        for effect in extract_effects(binding, root)
        if effect.kind not in known and effect.kind not in excused
    )
    return Ok(undeclared + unclassified)


def _run_all_completeness_checks(
    model: KernelModel,
    view: str,
    catalog: tuple[WeaknessEntry, ...],
    out_of_scope: tuple[OutOfScopeEntry, ...],
    benign: tuple[BenignCapability, ...],
    binding: CodeBinding | None,
    root: Path | None,
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """Run THREAT001+002 (catalog/capability), THREAT003 (discharge), and --
    when both `binding` and `root` are given -- THREAT004+005 (effect), in
    that exact order, short-circuiting on the first `Err` -- split out of
    `evaluate_threats` so its own line count reflects the entrypoint seam,
    not the four-check sequence (frob-arch long-function). T-0595: THREAT003
    now also receives `binding`/`root` so its G1-stronger-half code-binding
    join runs whenever a caller supplies a code tree, exactly like
    THREAT004+005 already do."""
    catalog_violations = check_catalog_completeness(view, catalog, out_of_scope)
    if catalog_violations.is_err:
        return Err(catalog_violations.danger_err)
    capability_violations = check_capability_completeness(model, catalog, benign)
    if capability_violations.is_err:
        return Err(capability_violations.danger_err)
    discharge_violations = check_discharge_completeness(model, catalog, binding, root)
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
    return Ok(
        (
            *catalog_violations.danger_ok,
            *capability_violations.danger_ok,
            *discharge_violations.danger_ok,
            *effect_violations,
        )
    )


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
    all_violations_result = _run_all_completeness_checks(
        model, view, catalog, out_of_scope, benign, binding, root
    )
    if all_violations_result.is_err:
        return Err(all_violations_result.danger_err)
    all_violations = all_violations_result.danger_ok
    _log_pre_discharge_obligation_count(view, catalog, out_of_scope, all_violations)
    return Ok(ThreatReport(violations=all_violations))


# T-0217: this is the RAW pre-discharge obligation count across all four
# completeness checks (catalog/capability/discharge/effect) -- callers
# such as `frob sys plan` only turn THREAT003 violations into obligation
# tickets, and `frob sys doc` renders a per-CWE PROVED/ASSUMED matrix
# from a DIFFERENT reduction of this same data. At INFO level this line
# printed right before a "0 obligation ticket(s)" / "PROVED" summary and
# read as contradictory (a nonzero count next to a zero/clean verdict)
# even though nothing was wrong -- the two numbers answer different
# questions. Demoted to DEBUG so default-verbosity output only shows the
# post-discharge verdict; `-v`/`-vv` still surface this detail.
def _log_pre_discharge_obligation_count(
    view: str,
    catalog: tuple[WeaknessEntry, ...],
    out_of_scope: tuple[OutOfScopeEntry, ...],
    all_violations: tuple[ThreatViolation, ...],
) -> None:
    """DEBUG-level log of `evaluate_threats`'s raw pre-discharge obligation
    count -- see the comment above this def for why it is DEBUG, not INFO."""
    _log.debug(
        "threat: obligations evaluated view=%r catalog=%d out_of_scope=%d -> "
        "%d pre-discharge obligation(s) (not all become tickets; see caller's "
        "own post-discharge count/verdict)",
        view,
        len(catalog),
        len(out_of_scope),
        len(all_violations),
    )


__all__ = [
    "ALL_CATALOG",
    "CWE_CATALOG",
    "CWE_TOP_25_CATALOG",
    "CWE_TOP_25_OUT_OF_SCOPE",
    "CWE_TOP_25_VIEWS",
    "DEFAULT_BENIGN_CAPABILITIES",
    "QUALITY_CATALOG",
    "QUALITY_OUT_OF_SCOPE",
    "QUALITY_VIEWS",
    "VIEWS",
    "BenignCapability",
    "OutOfScopeEntry",
    "ThreatReport",
    "ThreatViolation",
    "WeaknessEntry",
    "CAUGHT_BY_NONE_MARKER",
    "check_capability_completeness",
    "check_catalog_completeness",
    "check_discharge_completeness",
    "check_effect_completeness",
    "evaluate_threats",
    "load_repo_benign_capabilities",
]
