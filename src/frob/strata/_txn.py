"""REL30x reliability family: TRANSACTIONAL-BOUNDARY obligation -- an op
(non-store node) writing to two or more distinct stores with no declared
transactional boundary (or saga/compensation strategy) is a consistency
hazard (T-0650, child of the T-0331 systems-checks epic, docs/strata/
reliability.md). REUSES the store-writer graph `_ssot.py`'s REL29x family
built for T-0649 (module docstring precedent) but inverts the direction:
REL29x asks "is this STORE written by >=2 nodes?"; REL30x asks "does this
OP write to >=2 STORES?" -- same `Flow`-edge scan, same `store_ids`
caller-supplied set, opposite grouping key (`_multi_store_writers` groups
by `flow.src`, not `flow.dst`).

TWO RULES, both OP-node-scoped (an op has at most one multi-store-write
finding and fires at most one REL300/REL301 each -- single-instance-per-
node, the same carve-out `_ssot.py`'s REL290/REL291 pair already
establishes, NOT registered in `MULTI_INSTANCE_WAIVER_FAMILIES`):

  - REL300 missing transactional boundary: an op node writing (mode-
    blind: ANY outbound `Flow` landing on a distinct store id, `_ssot.py::
    _multi_writer_stores`'s exact detection mirrored in the opposite
    direction) to >=2 distinct stores in the caller-supplied `store_ids`
    set, with no `transaction` attr and no `saga` attr declared on the op
    node. Deny-by-default: an op spanning two or more stores with no
    declared transactional boundary or saga/compensation strategy is a
    hard consistency hazard -- a partial failure between the writes can
    leave the stores permanently inconsistent with no defined recovery.
  - REL301 unproven transactional boundary: a multi-store-write op DOES
    declare `transaction` or `saga`, but the T-0331 PROVABILITY
    CONSTRAINT forbids discharging it by bare declaration alone -- the op
    node must have at least one file bound to it (`_obligation_proof.py::
    node_has_bound_code`) containing a real transaction/saga-shaped
    token. An op with no bound code at all is UNCHECKABLE, not unproven --
    the same ceiling REL201/REL222/REL231/REL261/REL271/REL281/REL291
    draw.

SAME "NOT A KERNEL FACT" CEILING REL29x ALREADY DISCLOSES: `store_ids`
(which node ids are STORES, not plain components) is not a `KernelModel`-
level fact -- a store desugars into a plain `Node` at elaborate time
(docs/strata/surface.md#key-construct-semantics) with no reconstructible
marker -- so callers that know a design file's `Module.stores` (the
parsed AST, before elaboration folds stores into nodes) must pass those
ids in explicitly; an empty `store_ids` (the default) makes REL300/REL301
emit nothing, never a guessed-at store set (`_ssot.py`'s exact
precedent).

GRAMMAR-DATA CEILING, HONESTLY: `transaction`/`saga` are both presence-
only bare Node attrs (no numeric magnitude, no actual coordinator name or
compensation strategy round-trips through the grammar -- the same digit-
led-literal ceiling every other REL2xx/REL29x marker in this family
discloses), so REL300/REL301 prove PRESENCE of a declared transactional-
boundary obligation and its code-level evidence, not a specific
coordinator or compensation algorithm. No `strata-core` change needed
(this ticket's scope is `src/frob/strata/**`/`docs/strata/**`/
`tests/unit/strata/**` only, same as T-0640/T-0641/.../T-0649's).

OUT OF SCOPE, DELIBERATELY: the cross-SERVICE distributed-transaction
saga/compensation obligation (a transaction spanning multiple SERVICES,
not just multiple stores written by one op) is a separate, later ticket
(tickets.md's "strata: distributed-transaction-across-services requires
saga/compensation") that builds on this module's multi-write detection --
REL300/REL301 stay scoped to the single-op-writing-multiple-stores case
this ticket's acceptance criterion names.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's 'only' hits \
# are source-level design-rationale/scope-cut prose mirroring _ssot.py's own identical \
# waiver for the identical reason (module docstring precedent, T-0650), not a separate \
# cross-module contract"

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

#: `frob sys audit` rule id for REL300 missing transactional boundary: an
#: op writing to >=2 stores with no `transaction` and no `saga` attr.
# frob:doc docs/strata/reliability.md#rel30x-transactional-boundary-obligation-t-0650  # noqa: E501
REL_MISSING_TXN_BOUNDARY = "REL300"

#: `frob sys audit` rule id for REL301 unproven transactional boundary: an
#: op declares `transaction`/`saga`, but its bound code has no real
#: transaction/saga-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel30x-transactional-boundary-obligation-t-0650  # noqa: E501
REL_UNPROVEN_TXN_BOUNDARY = "REL301"

#: Every REL30x rule id this module can emit -- this module's own, narrow
#: family for `_apply_txn_waivers`' `in_scope` (the "never a shared
#: superset" discipline `_reliability.py`'s module docstring documents
#: the real regression for).
# frob:doc docs/strata/reliability.md#rel30x-transactional-boundary-obligation-t-0650  # noqa: E501
TXN_RULES: frozenset[str] = frozenset(
    {REL_MISSING_TXN_BOUNDARY, REL_UNPROVEN_TXN_BOUNDARY}
)

#: Node attr declaring a transactional-boundary obligation discharged
#: (presence-only, module docstring's grammar-data ceiling).
_TRANSACTION_ATTR = "transaction"

#: Node attr declaring a saga/compensation-strategy obligation discharged
#: (presence-only, module docstring's grammar-data ceiling).
_SAGA_ATTR = "saga"

#: Regex proving a real transaction/saga-shaped token in bound source
#: text (REL301) -- deliberately narrow (a syntactic token scan, not a
#: semantic call-argument binding), matching common transactional-
#: boundary/saga/compensation-library shapes: a `transaction`/
#: `atomic_transaction` identifier, a `two_phase_commit`/`2pc` construct,
#: a `saga`/`Saga(` construct, or a `compensat` token (compensating
#: transaction, the standard saga-recovery term). Same honesty line
#: `_ssot.py::_OWNER_TOKEN_RE`'s docstring already establishes: not a
#: claim the matched token guards the SAME op the model describes, only
#: that the op's bound code contains real evidence of a transactional-
#: boundary construct.
_TXN_TOKEN_RE = re.compile(
    r"(transaction|two_phase_commit|\b2pc\b|\bsaga\b|Saga\(|compensat)",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel30x-transactional-boundary-obligation-t-0650  # noqa: E501
class TxnBoundaryViolation(BaseModel):
    """One REL30x finding: rule id, the op node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-op (module docstring:
    at most one REL300/REL301 finding each), the same bare-rule waiver
    carve-out REL290/REL291 use. Mirrors `_ssot.py::SsotViolation`'s
    shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel30x-transactional-boundary-obligation-t-0650  # noqa: E501
class TxnBoundaryReport(BaseModel):
    """Every UNWAIVED REL30x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors `_ssot.py::
    SsotReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[TxnBoundaryViolation, ...] = ()
    waived: tuple[TxnBoundaryViolation, ...] = ()


def _multi_store_writers(
    model: KernelModel, store_ids: frozenset[str]
) -> dict[str, frozenset[str]]:
    """Every non-store op id writing (mode-blind: ANY outbound `Flow`
    landing on a distinct store id in `store_ids`, `_ssot.py::
    _multi_writer_stores`'s exact detection mirrored in the opposite
    direction) to >=2 distinct stores, mapped to its full written-store
    set. Empty `store_ids` yields an empty result -- module docstring's
    "not a guessed-at store set" discipline."""
    if not store_ids:
        return {}
    written: dict[str, set[str]] = {}
    for flow in model.flows:
        if flow.dst in store_ids and flow.src != flow.dst:
            written.setdefault(flow.src, set()).add(flow.dst)
    return {
        op_id: frozenset(store_id_set)
        for op_id, store_id_set in written.items()
        if len(store_id_set) >= 2
    }


def _has_txn_boundary(attrs: tuple[str, ...]) -> bool:
    """Whether an op node's `attrs` carries `transaction` or `saga`."""
    return _TRANSACTION_ATTR in attrs or _SAGA_ATTR in attrs


# frob:ticket T-0972
def _missing_txn_boundary_violations(
    model: KernelModel, store_ids: frozenset[str]
) -> list[TxnBoundaryViolation]:
    """REL300: every multi-store-write op with no `transaction`/`saga`
    attr."""
    nodes_by_id = {node.id: node for node in model.nodes}
    violations: list[TxnBoundaryViolation] = []
    for op_id, written_ids in sorted(_multi_store_writers(model, store_ids).items()):
        op_node = nodes_by_id.get(op_id)
        if op_node is None or _has_txn_boundary(op_node.attrs):
            continue
        stores = ", ".join(sorted(written_ids))
        _log.warning(
            "txn: REL300 op %s writes stores %s with no transactional boundary",
            op_id,
            stores,
        )
        violations.append(
            TxnBoundaryViolation(
                rule=REL_MISSING_TXN_BOUNDARY,
                node=op_id,
                detail=(
                    f"op {op_id} writes stores {stores} with no declared "
                    "transactional-boundary obligation (no `transaction` or "
                    "`saga` attr)"
                ),
            )
        )
    return violations


def _unproven_txn_boundary_violations(
    model: KernelModel,
    store_ids: frozenset[str],
    owner_by_node: dict[str, list[str]],
    root: Path,
) -> list[TxnBoundaryViolation]:
    """REL301: every multi-store-write op declaring `transaction`/`saga`
    with bound code, but whose bound code carries no real transaction/
    saga-shaped token (PROVABILITY CONSTRAINT). Mirrors `_ssot.py::
    _unproven_owner_violations` exactly, parameterized on `_TXN_TOKEN_RE`.
    """
    nodes_by_id = {node.id: node for node in model.nodes}
    violations: list[TxnBoundaryViolation] = []
    for op_id in sorted(_multi_store_writers(model, store_ids)):
        op_node = nodes_by_id.get(op_id)
        if op_node is None or not _has_txn_boundary(op_node.attrs):
            continue
        if not node_has_bound_code(op_id, owner_by_node):
            continue
        if files_evidence_token(owner_by_node[op_id], root, _TXN_TOKEN_RE):
            continue
        _log.warning(
            "txn: REL301 op %s declares transaction/saga but bound code has "
            "no real transactional-boundary token",
            op_id,
        )
        violations.append(
            TxnBoundaryViolation(
                rule=REL_UNPROVEN_TXN_BOUNDARY,
                node=op_id,
                detail=(
                    f"op {op_id} declares transaction/saga, but its bound "
                    "code has no real transaction/saga-shaped token "
                    "(proof-against-code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_txn_waivers(model: KernelModel, violations: list[TxnBoundaryViolation]):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_ssot.py::_apply_ssot_waivers`'s pattern reused for the REL30x
    family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in TXN_RULES,
    )


# frob:doc docs/strata/reliability.md#rel30x-transactional-boundary-obligation-t-0650  # noqa: E501
# frob:ticket T-0650
# frob:enforces CHK-GATE-REL300
# frob:enforces CHK-GATE-REL301
# frob:tests tests/unit/strata/test_txn.py::TestMissingTxnBoundary.test_multi_store_write_op_without_boundary_fires  # noqa: E501
def check_txn_boundary_obligations(
    model: KernelModel, store_ids: frozenset[str], root: Path
) -> Result[TxnBoundaryReport, StrataError]:
    """The REL30x TRANSACTIONAL-BOUNDARY-obligation entrypoint (T-0650):
    REL300 (missing transactional boundary) and REL301 (declared-but-
    unproven boundary, proof-against-code) across every op writing to >=2
    stores in `store_ids`, waivers already applied. `store_ids` is the
    caller-supplied set of node ids that originated from a `store`
    construct (module docstring: `KernelModel` alone cannot reconstruct
    which of its nodes were stores). `root` is the repo root
    `_code_binding.py::bind_code` binds against -- `Err` propagates
    `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by default, the
    same discipline `check_ssot_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[TxnBoundaryViolation] = []
    violations.extend(_missing_txn_boundary_violations(model, store_ids))
    violations.extend(
        _unproven_txn_boundary_violations(model, store_ids, owner_by_node, root)
    )
    applied = _apply_txn_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        TxnBoundaryViolation(
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
        "txn: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(TxnBoundaryReport(violations=tuple(applied.kept) + stale, waived=waived))


__all__ = [
    "REL_MISSING_TXN_BOUNDARY",
    "REL_UNPROVEN_TXN_BOUNDARY",
    "TXN_RULES",
    "TxnBoundaryReport",
    "TxnBoundaryViolation",
    "check_txn_boundary_obligations",
]
