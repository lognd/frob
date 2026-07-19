"""In-design waiver channel for `frob sys audit` findings (T-0174,
docs/strata/waive.md): the surface analog of `frob:waive` for gate
violations, scoped to SYS100-102/THREAT002-003/LINT004-shaped findings.

External repos piloting `.strata` hit a real honest-debt gap: `frob check`
gate violations have `frob:waive` with a written reason, but `frob sys
audit` findings had no waiver channel at all -- a repo either fixed a
finding immediately or lived with permanent red, which pushes toward
gaming the model (deleting a `may` declaration, weakening a claim) instead
of recording the debt honestly. This module is that channel's evaluator.

A `waive RULE reason="..." [ticket="..."]` clause lives ON THE NODE it
excuses (`strata-core/src/parse.rs`'s `waive` node property, `_ast.py::
WaiverDecl`, `_models.py::Node.waives`) rather than as a parallel
free-floating directive file -- the same "binds to the thing it excuses"
precision `frob:waive` earned the hard way (T-0148's file-scoped ->
symbol-scoped fix, `docs/guides/agent-playbook.md`). `reason` is mandatory
IN THE GRAMMAR (a `waive` clause with no reason is a parse error, not a
malformed-but-parseable directive like `frob:waive`'s WAIVE001) -- there is
no way to construct a `Waiver` value without a written reason.

Discipline mirrors `frob:waive`'s WAIVE001/WAIVE002 gate semantics
(`src/frob/gates/__init__.py`) exactly:
  - narrowly scoped: a waiver matches ONLY its declared (node, rule,
    sub-target) triple, never a blanket "waive everything for this node"
    or "for this rule repo-wide" (module docstring's "no blanket waivers"
    requirement).
  - loud in output: a waived finding is never silently dropped -- it is
    kept, tagged `WaivedFinding`, and `sys_runner.py` prints it as WAIVED
    with the reason, counted separately from PROVED/GAP.
  - drift-locked: a waiver whose target finding does not fire in the
    CURRENT run is STALE (the WAIVE002 "ineffective waiver" analog) and is
    itself reported as a new finding (`rule="SYSWAIVE002"`) so a stale
    waiver fails the audit rather than silently doing nothing forever.

## Sub-targets: required for multi-instance-per-node rule families (T-0174 REJECT round)

A node-review round REJECTED the first version of this module for a real
soundness hole: `SYS100` (undeclared capability), `SYS101` (stale
capability), `THREAT002` (unclassified capability), and `THREAT003`
(undischarged CWE obligation) can each fire MORE THAN ONCE on the SAME
node -- once per capability kind observed/declared, once per CWE
implicated. A bare `waive "SYS100" reason "...";` on such a node would
suppress EVERY current AND FUTURE SYS100 finding on that node under one
stale reason -- exactly the T-0148 blanket-waiver bug the file-scoped ->
symbol-scoped `frob:waive` fix closed for gate violations, reopened here
at node scope.

The fix: `MULTI_INSTANCE_WAIVER_FAMILIES` names the rule families that can
fire more than once per node. A `waive` clause whose rule is one of these
MUST carry a `RULE:SUBTARGET` sub-target (e.g. `waive "SYS100:fs-write"
reason "...";`, `waive "THREAT003:CWE-78" reason "...";`) -- the exact
capability kind or CWE id the waiver excuses, no more. A bare rule (no
`:SUBTARGET`) on one of these families is an ELABORATE-TIME ERROR
(`StrataError.MalformedWaiver`), not a silent narrow-vs-broad guess: law 2
(`docs/strata/charter.md`) refuses to infer scope the author did not
write down. Single-instance-per-node families (LINT/PII/COMPLIANCE, and
SYS102 which fires once per unmodeled directory) keep the bare-rule form
-- there is exactly one possible finding per (node, rule) for them, so a
sub-target would name nothing.

This module is deliberately generic over "finding": `SelfConformViolation`
(`_selfconform.py`) and `FamilyGap` (`_audit.py`, covering THREAT/LINT/
PII/compliance/CVE-fingerprint) share no common base class but both
resolve to a (rule, node, sub-target-or-None, detail) shape via caller-
supplied extractor callables, so ONE apply/stale algorithm serves every
family -- no per-rule-family duplicate (charter: no duplication).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._models import KernelModel, Waiver

_log = get_logger(__name__)

# frob:doc docs/strata/waive.md#sub-targets
#: Rule families that can fire MORE THAN ONCE on the same node (once per
#: capability kind, once per CWE) -- a bare-rule `waive` clause here would
#: blanket-suppress every current and future finding of the rule on the
#: node (the T-0148 blanket-waiver bug, reopened at node scope). A `waive`
#: clause naming one of these MUST carry a `RULE:SUBTARGET` sub-target;
#: `_validate_waiver_decl` enforces this at elaborate time. SYS101 shares
#: SYS100's exact per-capability-kind shape (`_selfconform.py::
#: _stale_design_violations`) so it is included even though it was not one
#: of the two families a reviewing pass named explicitly -- the same bug
#: would otherwise reopen on SYS101 alone.
MULTI_INSTANCE_WAIVER_FAMILIES: frozenset[str] = frozenset(
    {"SYS100", "SYS101", "THREAT002", "THREAT003"}
)


# frob:doc docs/strata/waive.md#sub-targets
def split_waiver_rule(rule: str) -> tuple[str, str | None]:
    """Split a declared `waive` rule string into `(family, sub_target)` on
    the first `:` -- `"SYS100:fs-write"` -> `("SYS100", "fs-write")`,
    `"LINT004"` -> `("LINT004", None)`. A colon with nothing (or only
    whitespace) after it is treated as "no sub-target" (empty string ->
    `None`), so `_validate_waiver_decl` reports it as a missing sub-target
    rather than a present-but-blank one."""
    family, sep, rest = rule.partition(":")
    sub_target = rest.strip() if sep else ""
    return family.strip(), (sub_target or None)


# frob:doc docs/strata/waive.md#sub-targets
def validate_waiver_fields(rule: str, reason: str) -> Result[None, StrataError]:
    """Reject a `waive` clause's `(rule, reason)` pair at elaborate time,
    fails closed: `reason` empty/whitespace-only (a blank reason is a
    functional bypass -- suppresses the finding with nothing written down
    to justify it, never accepted), or a `MULTI_INSTANCE_WAIVER_FAMILIES`
    rule with no `RULE:SUBTARGET` sub-target (the blanket-waiver bug this
    module's docstring describes). Shared by `_ast.py::WaiverDecl` (parse-
    adjacent, pre-elaboration) and `_models.py::Waiver` (post-elaboration)
    validation call sites -- both shapes carry the same two fields."""
    if not reason.strip():
        return Err(StrataError.MalformedWaiver)
    family, sub_target = split_waiver_rule(rule)
    if family in MULTI_INSTANCE_WAIVER_FAMILIES and sub_target is None:
        return Err(StrataError.MalformedWaiver)
    return Ok(None)


# frob:doc docs/strata/waive.md#drift-lock-stale-waivers-fail
#: `frob sys audit` rule id for a stale waiver (T-0174): a `waive` clause
#: whose declared (node, rule) pair matched zero findings in the current
#: run -- the drift-lock analog of the gate system's WAIVE002 (an
#: ineffective waiver is reported, never a silent no-op).
STALE_WAIVER_RULE = "SYSWAIVE002"

#: The finding type `apply_waivers`/`WaivedFinding`/`WaiverApplication` are
#: generic over (`SelfConformViolation`, `FamilyGap`, ...) -- private
#: (single-underscore-free but lowercase-prefixed by convention) since it
#: names no independent concept a caller imports, only a type parameter.
_F = TypeVar("_F")


# frob:doc docs/strata/waive.md#reported-output-waived-never-silent
class WaiverMatch(BaseModel):
    """The `waive` clause (node id + rule + reason + optional ticket) that
    suppressed a finding, kept for report visibility -- mirrors `frob.
    gates._models.WaiverRef`'s "never a silent drop" role. `rule` is the
    RAW declared string (e.g. `"SYS100:fs-write"`) so a printed WAIVED
    line always shows the sub-target a multi-instance waiver named,
    never just the bare family (which a reader could mistake for
    "every SYS100 on this node")."""

    model_config = ConfigDict(frozen=True)

    node: str
    rule: str
    reason: str
    ticket: str | None = None


# frob:doc docs/strata/waive.md#reported-output-waived-never-silent
class WaivedFinding(BaseModel, Generic[_F]):
    """One finding suppressed by a matching `waive` clause: the original
    finding (kept, never dropped) plus the `WaiverMatch` that excused it."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    finding: _F
    waiver: WaiverMatch


# frob:doc docs/strata/waive.md#drift-lock-stale-waivers-fail
class WaiverApplication(BaseModel, Generic[_F]):
    """The result of matching `findings` against every node's `waive`
    clauses: `kept` (unwaived, still a real finding), `waived` (suppressed,
    surfaced as WAIVED not silently dropped), and `stale` (a declared
    waiver that matched nothing -- itself a new `SYSWAIVER002` finding, per
    module docstring's drift-lock requirement)."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    kept: tuple[_F, ...] = ()
    waived: tuple[WaivedFinding[_F], ...] = ()
    stale: tuple[WaiverMatch, ...] = ()


# frob:doc docs/strata/waive.md#drift-lock-stale-waivers-fail
# frob:tests src/frob/strata/_waive.py::stale_detail kind="unit"
def stale_detail(stale: WaiverMatch) -> str:
    """The human detail string every caller uses for a STALE waiver's
    generated finding -- one home for the message so `_audit.py`/
    `_selfconform.py` never phrase it two different ways (charter: no
    duplication)."""
    return (
        f"waive {stale.rule!r} on node {stale.node} reason={stale.reason!r} "
        f"is stale -- no matching {stale.rule} finding fired this run"
    )


def _declared_waivers(model: KernelModel) -> list[tuple[str, Waiver]]:
    """Every `(node_id, Waiver)` pair declared anywhere in `model`, in
    node-then-declaration order -- the full waiver universe a finding
    stream is matched against."""
    return [(node.id, waiver) for node in model.nodes for waiver in node.waives]


# Split `findings` into kept/waived against every node's `waive` clauses
# declared in `model`, then compute which declared waivers are STALE
# (matched zero findings) -- the one seam every SYS100-102/THREAT002-003/
# LINT004 caller shares (module docstring: no per-family duplicate).
# `rule_of`/`target_of`/`sub_target_of` extract the (rule, node,
# sub-target-or-None) key from whatever finding shape the caller has
# (`SelfConformViolation.node`/`.capability`, `FamilyGap.target`/
# `.sub_target`, ...) since those families share no common base class. A
# waiver matches iff its `(node, family, sub_target)` triple exactly equals
# a finding's `(target_of(finding), rule_of(finding),
# sub_target_of(finding))` -- narrow, never a substring/prefix match
# (module docstring's "no blanket waivers"). For a
# `MULTI_INSTANCE_WAIVER_FAMILIES` rule, `sub_target_of` MUST return the
# finding's actual capability kind / CWE id (never `None`) or it can never
# match any waiver on that family (which, by `_validate_waiver_decl`,
# always carries a sub-target) -- a caller returning `None` there is a
# caller bug, not a valid "no sub-target" finding.
#
# `in_scope` is MANDATORY, not a convenience default: `Node.waives` is
# model-global, but `check_self_conformance` (SYS100-102) and
# `evaluate_exhaustiveness` (THREAT/LINT/PII/compliance/CVE-fingerprint)
# each only see THEIR OWN slice of `findings` -- a LINT004 waiver run
# through `check_self_conformance`'s SYS-only `findings` would (correctly)
# match nothing and be misreported STALE, even though it is genuinely
# effective in the OTHER caller's pass. Each caller passes an `in_scope`
# predicate naming exactly the rule ids it owns so staleness is judged
# only against the waivers actually addressable in this call; a waiver
# naming a rule id neither caller owns (a typo) is judged stale by
# whichever `in_scope` is broad enough to admit it -- never silently
# invisible to both.
# frob:doc docs/strata/waive.md#implementation
# frob:tests tests/unit/strata/test_litmus_waive.py::TestWaiveLitmus.test_stale_fails
# frob:tests tests/unit/strata/test_selfconform.py::TestWaiverChannel.test_stale
def apply_waivers(
    model: KernelModel,
    findings: Sequence[_F],
    *,
    rule_of: Callable[[_F], str],
    target_of: Callable[[_F], str | None],
    sub_target_of: Callable[[_F], str | None],
    in_scope: Callable[[str], bool],
) -> WaiverApplication[_F]:
    """Split findings into kept/waived, then compute which waivers are stale."""
    declared = [
        (node_id, w)
        for node_id, w in _declared_waivers(model)
        if in_scope(split_waiver_rule(w.rule)[0])
    ]
    by_key = _index_declared_waivers(declared)
    kept, waived, matched_keys = _split_kept_and_waived(
        findings, by_key, rule_of, target_of, sub_target_of
    )
    stale = _stale_waivers(declared, matched_keys)
    return WaiverApplication(kept=tuple(kept), waived=tuple(waived), stale=tuple(stale))


def _index_declared_waivers(
    declared: list[tuple[str, Waiver]],
) -> dict[tuple[str, str, str | None], Waiver]:
    """Index `declared` by (node, family, sub_target) once.

    T-0174 perf: rather than rescanning it per finding -- `findings` and
    `declared` are each O(n), a per-finding linear scan would make matching
    O(n*m)."""
    return {(node_id, *split_waiver_rule(w.rule)): w for node_id, w in declared}


def _split_kept_and_waived(
    findings: Sequence[_F],
    by_key: dict[tuple[str, str, str | None], Waiver],
    rule_of: Callable[[_F], str],
    target_of: Callable[[_F], str | None],
    sub_target_of: Callable[[_F], str | None],
) -> tuple[list[_F], list[WaivedFinding[_F]], set[tuple[str, str, str | None]]]:
    """Every finding into kept or waived against `by_key`, plus the set of
    waiver keys that matched at least one finding."""
    kept: list[_F] = []
    waived: list[WaivedFinding[_F]] = []
    matched_keys: set[tuple[str, str, str | None]] = set()
    for finding in findings:
        rule = rule_of(finding)
        target = target_of(finding)
        sub_target = sub_target_of(finding)
        match = by_key.get((target, rule, sub_target)) if target is not None else None
        if match is None:
            kept.append(finding)
            continue
        matched_keys.add((target or "", rule, sub_target))
        waived.append(_waived_finding(finding, rule, target, sub_target, match))
    return kept, waived, matched_keys


def _waived_finding(
    finding: _F,
    rule: str,
    target: str | None,
    sub_target: str | None,
    match: Waiver,
) -> WaivedFinding[_F]:
    """One finding paired with the `Waiver` that matched it, logged."""
    _log.info(
        "waive: %s finding on %s (sub_target=%s) waived (reason=%r ticket=%s)",
        rule,
        target,
        sub_target,
        match.reason,
        match.ticket,
    )
    return WaivedFinding(
        finding=finding,
        waiver=WaiverMatch(
            node=target or "",
            rule=match.rule,
            reason=match.reason,
            ticket=match.ticket,
        ),
    )


def _stale_waivers(
    declared: list[tuple[str, Waiver]],
    matched_keys: set[tuple[str, str, str | None]],
) -> list[WaiverMatch]:
    """Every declared waiver whose key never matched a finding."""
    stale: list[WaiverMatch] = []
    for node_id, waiver in declared:
        family, sub_target = split_waiver_rule(waiver.rule)
        key = (node_id, family, sub_target)
        if key in matched_keys:
            continue
        _log.warning(
            "waive: STALE %s waiver on %s -- no matching finding fired "
            "(reason=%r ticket=%s)",
            waiver.rule,
            node_id,
            waiver.reason,
            waiver.ticket,
        )
        stale.append(
            WaiverMatch(
                node=node_id,
                rule=waiver.rule,
                reason=waiver.reason,
                ticket=waiver.ticket,
            )
        )
    return stale


__all__ = [
    "MULTI_INSTANCE_WAIVER_FAMILIES",
    "STALE_WAIVER_RULE",
    "WaivedFinding",
    "WaiverApplication",
    "WaiverMatch",
    "apply_waivers",
    "split_waiver_rule",
    "stale_detail",
    "validate_waiver_fields",
]
