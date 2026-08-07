"""REL29x reliability family: SINGLE SOURCE OF TRUTH obligation -- a store
written by two or more distinct nodes with no declared owner/
reconciliation is a hazard (T-0649, child of the T-0331 systems-checks
epic, docs/strata/reliability.md). Extends `_contention.py`'s SYS203
shared-store-write DETECTION (two or more distinct non-store nodes have a
`Flow` edge landing on the same store node) with an OBLIGATION: SYS203
alone only reports the fact of multi-writer contention; REL290/REL291
additionally require the store to declare who owns write authority (or
how conflicting writes reconcile), deny-by-default, mirroring
`_circuit_breaker.py`'s REL23x node-scoped structure (module docstring
precedent, T-0699/T-0640/.../T-0648: one rule module per obligation, same
`Report`/`Violation` pydantic pair, node-scoped single-instance carve-out,
CLI wiring via `frob.app.sys_runner`).

TWO RULES, both STORE-node-scoped (a store has at most one multi-writer
finding and fires at most one REL290/REL291 each -- single-instance-per-
node, the same carve-out `_circuit_breaker.py`'s REL230/REL231 pair
already establishes, NOT registered in `MULTI_INSTANCE_WAIVER_FAMILIES`):

  - REL290 missing owner/reconciliation: a store id in the caller-
    supplied `store_ids` set (module docstring below explains why this is
    a parameter, not a `KernelModel` fact) written by >=2 distinct non-
    store nodes (SYS203's exact detection, `_contention.py::
    _shared_store_write_violations`, re-derived here rather than
    imported since REL290 needs the FULL writer set per store, not
    SYS203's per-writer-peer finding shape) with no `owner` attr and no
    `reconciliation` attr declared on the store node. Deny-by-default:
    two or more nodes writing the same store with no declared single-
    owner authority or conflict-reconciliation strategy is a hard
    consistency hazard -- concurrent writers can silently clobber each
    other with no defined resolution.
  - REL291 unproven owner: a multi-writer store DOES declare `owner` or
    `reconciliation`, but the T-0331 PROVABILITY CONSTRAINT forbids
    discharging it by bare declaration alone -- the store node must have
    at least one file bound to it (`_obligation_proof.py::
    node_has_bound_code`) containing a real single-writer/reconciliation-
    shaped token. A store with no bound code at all is UNCHECKABLE, not
    unproven -- the same ceiling REL201/REL222/REL231/REL261/REL271/
    REL281 draw.

SAME "NOT A KERNEL FACT" CEILING SYS203 ALREADY DISCLOSES: `store_ids`
(which node ids are STORES, not plain components) is not a `KernelModel`-
level fact -- a store desugars into a plain `Node` at elaborate time
(docs/strata/surface.md#key-construct-semantics) with no reconstructible
marker -- so callers that know a design file's `Module.stores` (the
parsed AST, before elaboration folds stores into nodes) must pass those
ids in explicitly; an empty `store_ids` (the default) makes REL290/REL291
emit nothing, never a guessed-at store set (`_contention.py`'s exact
precedent, module docstring).

GRAMMAR-DATA CEILING, HONESTLY: `owner`/`reconciliation` are both
presence-only bare Node attrs (no numeric magnitude, no actual owner
node-id or reconciliation-strategy name round-trips through the grammar
-- the same digit-led-literal ceiling every other REL2xx marker in this
family discloses), so REL290/REL291 prove PRESENCE of a declared single-
source-of-truth obligation and its code-level evidence, not a specific
owning node or reconciliation algorithm. No `strata-core` change needed
(this ticket's scope is `src/frob/strata/**`/`docs/strata/**`/
`tests/unit/strata/**` only, same as T-0640/T-0641/T-0648's).
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import bind_code
from ._errors import StrataError
from ._models import KernelModel
from ._obligation_proof import files_evidence_token, node_has_bound_code, owner_index
from ._waive import apply_waivers

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL290 missing owner/reconciliation: a
#: multi-writer store with no `owner` and no `reconciliation` attr.
# frob:doc docs/strata/reliability.md#rel29x-single-source-of-truth-obligation-t-0649  # noqa: E501
REL_MISSING_OWNER = "REL290"

#: `frob sys audit` rule id for REL291 unproven owner: a multi-writer
#: store declares `owner`/`reconciliation`, but its bound code has no
#: real single-writer/reconciliation-shaped token (PROVABILITY
#: CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel29x-single-source-of-truth-obligation-t-0649  # noqa: E501
REL_UNPROVEN_OWNER = "REL291"

#: Every REL29x rule id this module can emit -- this module's own, narrow
#: family for `_apply_ssot_waivers`' `in_scope` (the "never a shared
#: superset" discipline `_reliability.py`'s module docstring documents
#: the real regression for).
# frob:doc docs/strata/reliability.md#rel29x-single-source-of-truth-obligation-t-0649  # noqa: E501
SSOT_RULES: frozenset[str] = frozenset({REL_MISSING_OWNER, REL_UNPROVEN_OWNER})

#: Node attr declaring a single-owner write-authority obligation
#: discharged (presence-only, module docstring's grammar-data ceiling).
_OWNER_ATTR = "owner"

#: Node attr declaring a conflict-reconciliation-strategy obligation
#: discharged (presence-only, module docstring's grammar-data ceiling).
_RECONCILIATION_ATTR = "reconciliation"

#: Regex proving a real single-writer/reconciliation-shaped token in
#: bound source text (REL291) -- deliberately narrow (a syntactic token
#: scan, not a semantic call-argument binding), matching common single-
#: source-of-truth/reconciliation-library shapes: a `single_writer`
#: identifier, a `leader_election`/`leader_only` construct, a
#: `distributed_lock`/`DistributedLock(` construct, or a `reconcil`/`CRDT`
#: token (conflict-free replicated data type, a common reconciliation
#: strategy). Same honesty line
#: `_reliability.py::_TIMEOUT_TOKEN_RE`'s docstring already establishes:
#: not a claim the matched token guards the SAME store the model
#: describes, only that the store's bound code contains real evidence of
#: a single-source-of-truth construct.
_OWNER_TOKEN_RE = re.compile(
    r"(single_writer|leader_election|leader_only|distributed_lock|"
    r"DistributedLock\(|reconcil|\bCRDT\b)",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel29x-single-source-of-truth-obligation-t-0649  # noqa: E501
class SsotViolation(BaseModel):
    """One REL29x finding: rule id, the store node, a human-readable
    detail. `sub_target` stays `None` -- single-instance-per-store
    (module docstring: at most one REL290/REL291 finding each), the same
    bare-rule waiver carve-out REL230/REL231 use. Mirrors
    `_circuit_breaker.py::CircuitBreakerViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel29x-single-source-of-truth-obligation-t-0649  # noqa: E501
class SsotReport(BaseModel):
    """Every UNWAIVED REL29x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_circuit_breaker.py::CircuitBreakerReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[SsotViolation, ...] = ()
    waived: tuple[SsotViolation, ...] = ()


def _multi_writer_stores(
    model: KernelModel, store_ids: frozenset[str]
) -> dict[str, frozenset[str]]:
    """Every store id in `store_ids` written (mode-blind: ANY inbound
    `Flow`, `_contention.py::_shared_store_write_violations`'s exact
    detection) by >=2 distinct non-store nodes, mapped to its full writer
    set. Empty `store_ids` yields an empty result -- module docstring's
    "not a guessed-at store set" discipline."""
    if not store_ids:
        return {}
    writers: dict[str, set[str]] = {}
    for flow in model.flows:
        if flow.dst in store_ids and flow.src != flow.dst:
            writers.setdefault(flow.dst, set()).add(flow.src)
    return {
        store_id: frozenset(node_ids)
        for store_id, node_ids in writers.items()
        if len(node_ids) >= 2
    }


def _has_owner_or_reconciliation(attrs: tuple[str, ...]) -> bool:
    """Whether a store node's `attrs` carries `owner` or
    `reconciliation`."""
    return _OWNER_ATTR in attrs or _RECONCILIATION_ATTR in attrs


# frob:ticket T-0972
def _missing_owner_violations(
    model: KernelModel, store_ids: frozenset[str]
) -> list[SsotViolation]:
    """REL290: every multi-writer store with no `owner`/`reconciliation`
    attr."""
    nodes_by_id = {node.id: node for node in model.nodes}
    violations: list[SsotViolation] = []
    for store_id, writer_ids in sorted(_multi_writer_stores(model, store_ids).items()):
        store_node = nodes_by_id.get(store_id)
        if store_node is None or _has_owner_or_reconciliation(store_node.attrs):
            continue
        # frob:waive PERF004 reason="writer_ids is this loop's own per-store distinct set, not a shared re-sort"  # noqa: E501
        writers = ", ".join(sorted(writer_ids))
        _log.warning(
            "ssot: REL290 store %s written by %s with no owner/reconciliation",
            store_id,
            writers,
        )
        violations.append(
            SsotViolation(
                rule=REL_MISSING_OWNER,
                node=store_id,
                detail=(
                    f"store {store_id} is written by {writers} with no "
                    "declared owner/reconciliation obligation (no `owner` or "
                    "`reconciliation` attr)"
                ),
            )
        )
    return violations


def _unproven_owner_violations(
    model: KernelModel,
    store_ids: frozenset[str],
    owner_by_node: dict[str, list[str]],
    root: Path,
) -> list[SsotViolation]:
    """REL291: every multi-writer store declaring `owner`/`reconciliation`
    with bound code, but whose bound code carries no real single-writer/
    reconciliation-shaped token (PROVABILITY CONSTRAINT). Mirrors
    `_circuit_breaker.py::_unproven_circuit_breaker_violations` exactly,
    parameterized on `_OWNER_TOKEN_RE`."""
    nodes_by_id = {node.id: node for node in model.nodes}
    violations: list[SsotViolation] = []
    for store_id in sorted(_multi_writer_stores(model, store_ids)):
        store_node = nodes_by_id.get(store_id)
        if store_node is None or not _has_owner_or_reconciliation(store_node.attrs):
            continue
        if not node_has_bound_code(store_id, owner_by_node):
            continue
        if files_evidence_token(owner_by_node[store_id], root, _OWNER_TOKEN_RE):
            continue
        _log.warning(
            "ssot: REL291 store %s declares owner/reconciliation but bound "
            "code has no real single-source-of-truth token",
            store_id,
        )
        violations.append(
            SsotViolation(
                rule=REL_UNPROVEN_OWNER,
                node=store_id,
                detail=(
                    f"store {store_id} declares owner/reconciliation, but its "
                    "bound code has no real single-writer/reconciliation "
                    "token (proof-against-code, T-0331 PROVABILITY "
                    "CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_ssot_waivers(model: KernelModel, violations: list[SsotViolation]):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_circuit_breaker.py::_apply_circuit_breaker_waivers`'s pattern reused
    for the REL29x family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in SSOT_RULES,
    )


# frob:doc docs/strata/reliability.md#rel29x-single-source-of-truth-obligation-t-0649  # noqa: E501
# frob:ticket T-0649
# frob:enforces CHK-GATE-REL290
# frob:enforces CHK-GATE-REL291
# frob:tests tests/unit/strata/test_ssot.py::TestMissingOwner.test_multi_writer_store_without_owner_fires  # noqa: E501
def check_ssot_obligations(
    model: KernelModel, store_ids: frozenset[str], root: Path
) -> Result[SsotReport, StrataError]:
    """The REL29x SINGLE-SOURCE-OF-TRUTH-obligation entrypoint (T-0649):
    REL290 (missing owner/reconciliation) and REL291 (declared-but-
    unproven owner, proof-against-code) across every multi-writer store in
    `store_ids`, waivers already applied. `store_ids` is the caller-
    supplied set of node ids that originated from a `store` construct
    (module docstring: `KernelModel` alone cannot reconstruct which of its
    nodes were stores). `root` is the repo root `_code_binding.py::
    bind_code` binds against -- `Err` propagates `bind_code`'s
    `AmbiguousCodeBinding` unchanged (deny by default, the same
    discipline `check_circuit_breaker_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[SsotViolation] = []
    violations.extend(_missing_owner_violations(model, store_ids))
    violations.extend(_unproven_owner_violations(model, store_ids, owner_by_node, root))
    applied = _apply_ssot_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        SsotViolation(
            rule="RELWAIVE002",
            node=stale_waiver.node,
            sub_target=stale_waiver.rule,
            detail=(
                f"waive {stale_waiver.rule!r} on node {stale_waiver.node} "
                f"reason={stale_waiver.reason!r} is stale -- no matching "
                f"finding fired this run"
            ),
        )
        for stale_waiver in applied.stale
    )
    _log.info(
        "ssot: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(SsotReport(violations=tuple(applied.kept) + stale, waived=waived))


__all__ = [
    "REL_MISSING_OWNER",
    "REL_UNPROVEN_OWNER",
    "SSOT_RULES",
    "SsotReport",
    "SsotViolation",
    "check_ssot_obligations",
]
