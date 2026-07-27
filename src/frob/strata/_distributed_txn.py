"""REL35x reliability family: DISTRIBUTED-TRANSACTION-ACROSS-SERVICES
saga/compensation obligation (T-0655, child of the T-0331 systems-checks
epic, docs/strata/reliability.md), mirroring `_txn.py`'s REL30x structure
(module docstring precedent: one rule module per obligation, same
`Report`/`Violation` pydantic pair, NOT registered in `_waive.py::
MULTI_INSTANCE_WAIVER_FAMILIES`). BUILDS ON `_txn.py`'s multi-write
detection (T-0650's own "OUT OF SCOPE, DELIBERATELY" note names this
exact ticket), EXTENDED across service boundaries rather than the
caller-supplied `store_ids` set REL30x needs.

THE "ACROSS SERVICE BOUNDARIES" EXTENSION, HONESTLY: REL2xx's own module
docstring (`docs/strata/reliability.md`'s REL2xx section, `_reliability.
py`) already discloses that "every `Flow` in this grammar already crosses
a real process/service boundary by construction" -- there is no in-
process/self-flow construct in this kernel, so every node IS its own
service boundary. REL30x needed a caller-supplied `store_ids` set only
because it asked a NARROWER question (does this op write to >=2 STORES,
specifically) that `KernelModel` cannot answer alone (module docstring:
"store" desugars away at elaborate time). REL35x asks the BROADER
question the ticket names ("a transaction spanning multiple services") --
does this op write to >=2 DISTINCT DOWNSTREAM NODES AT ALL, regardless of
whether either is a declared store -- which IS a `KernelModel` fact
(`model.flows` alone), needing no external input. This is the "extended
across service boundaries" the ticket body asks for: every node already
IS a service boundary, so the multi-write population widens from
"stores in a caller-supplied set" to "every node `model.flows` names".

TWO RULES, both OP-node-scoped (an op has at most one multi-node-write
finding and fires at most one REL350/REL351 each -- single-instance-per-
node, the same carve-out `_txn.py`'s REL300/REL301 pair already
establishes, NOT registered in `MULTI_INSTANCE_WAIVER_FAMILIES`):

  - REL350 missing saga/compensation: an op node writing (mode-blind: ANY
    outbound `Flow`, `_txn.py::_multi_store_writers`'s exact detection
    generalized to every node id, not a caller-supplied subset) to >=2
    distinct downstream nodes, with no `saga` attr declared. Unlike
    REL300 (which accepts EITHER `transaction` or `saga` -- a single-
    process multi-store write can be wrapped in a local ACID
    transaction), REL350 accepts `saga` ONLY: a `transaction` attr alone
    asserts a single coordinated commit, which is not a meaningful claim
    once the write fans out across independent service processes (no
    shared commit log to coordinate against) -- distributed writes need a
    saga/compensation strategy, deny-by-default.
  - REL351 unproven saga: a multi-node-write op DOES declare `saga`, but
    the T-0331 PROVABILITY CONSTRAINT forbids discharging it by bare
    declaration alone -- the op node must have at least one file bound to
    it (`_obligation_proof.py::node_has_bound_code`) containing a real
    saga/compensation-shaped token. An op with no bound code at all is
    UNCHECKABLE, not unproven -- the same ceiling REL201/REL222/REL231/
    REL261/REL271/REL281/REL291/REL301/REL311/REL321/REL331 draw.

GRAMMAR-DATA CEILING, HONESTLY: `saga` is a presence-only bare Node attr
(no numeric magnitude, no actual coordinator name or compensation
strategy round-trips through the grammar -- the same digit-led-literal
ceiling every other REL2xx/REL3xx marker in this family discloses), so
REL350/REL351 prove PRESENCE of a declared saga/compensation obligation
and its code-level evidence, not a specific saga coordinator or
compensation algorithm. No `strata-core` change needed (this ticket's
scope is `src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**`
only, same as T-0640/.../T-0654's).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's \
# 'only' hits are source-level design-rationale/scope-cut prose mirroring \
# _txn.py's own identical waiver for the identical reason (module \
# docstring precedent, T-0655), not a separate cross-module contract"

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

#: `frob sys audit` rule id for REL350 missing saga/compensation: an op
#: writing to >=2 distinct downstream nodes with no `saga` attr declared.
# frob:doc docs/strata/reliability.md#rel35x-distributed-transaction-across-services-obligation-t-0655  # noqa: E501
REL_MISSING_SAGA = "REL350"

#: `frob sys audit` rule id for REL351 unproven saga: an op declares
#: `saga`, but its bound code has no real saga/compensation-shaped token
#: (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel35x-distributed-transaction-across-services-obligation-t-0655  # noqa: E501
REL_UNPROVEN_SAGA = "REL351"

#: Every REL35x rule id this module can emit -- this module's own, narrow
#: family for `_apply_distributed_txn_waivers`' `in_scope` (the "never a
#: shared superset" discipline `_reliability.py`'s module docstring
#: documents the real regression for).
# frob:doc docs/strata/reliability.md#rel35x-distributed-transaction-across-services-obligation-t-0655  # noqa: E501
DISTRIBUTED_TXN_RULES: frozenset[str] = frozenset({REL_MISSING_SAGA, REL_UNPROVEN_SAGA})

#: Node attr declaring a saga/compensation-strategy obligation discharged
#: (presence-only, module docstring's grammar-data ceiling) -- the SAME
#: string as `_txn.py::_SAGA_ATTR`, deliberately not imported from there
#: (same reasoning `_spof.py`'s module docstring gives for a
#: coincidentally-shared word at an independent grammar site: REL30x's
#: `saga` discharges a SINGLE-PROCESS multi-store write, REL35x's `saga`
#: discharges a MULTI-SERVICE one -- the same English word, two
#: independently-scoped obligations that happen to share a marker).
_SAGA_ATTR = "saga"

#: Regex proving a real saga/compensation-shaped token in bound source
#: text (REL351) -- deliberately narrow (a syntactic token scan, not a
#: semantic call-argument binding), matching common saga/compensating-
#: transaction shapes: a `saga`/`Saga(` construct, a `compensat` token
#: (compensating transaction, the standard saga-recovery term), or a
#: `two_phase_commit`/`2pc` construct. A narrower version of `_txn.py::
#: _TXN_TOKEN_RE` (drops the bare `transaction` token: module docstring,
#: `transaction` alone is not a meaningful cross-service discharge here).
#: Same honesty line `_txn.py::_TXN_TOKEN_RE`'s docstring already
#: establishes: not a claim the matched token guards the SAME op the
#: model describes, only that the op's bound code contains real evidence
#: of a saga/compensation construct.
_SAGA_TOKEN_RE = re.compile(
    r"(\bsaga\b|Saga\(|compensat|two_phase_commit|\b2pc\b)",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel35x-distributed-transaction-across-services-obligation-t-0655  # noqa: E501
class DistributedTxnViolation(BaseModel):
    """One REL35x finding: rule id, the op node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-op (module
    docstring: at most one REL350/REL351 finding each), the same bare-
    rule waiver carve-out REL300/REL301 use. Mirrors
    `_txn.py::TxnBoundaryViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel35x-distributed-transaction-across-services-obligation-t-0655  # noqa: E501
class DistributedTxnReport(BaseModel):
    """Every UNWAIVED REL35x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_txn.py::TxnBoundaryReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[DistributedTxnViolation, ...] = ()
    waived: tuple[DistributedTxnViolation, ...] = ()


def _multi_service_writers(model: KernelModel) -> dict[str, frozenset[str]]:
    """Every op id writing (mode-blind: ANY outbound `Flow`, `_txn.py::
    _multi_store_writers`'s exact detection generalized from a caller-
    supplied store set to every node `model.flows` names -- module
    docstring's "every node already is a service boundary") to >=2
    distinct downstream nodes, mapped to its full written-node set."""
    written: dict[str, set[str]] = {}
    for flow in model.flows:
        if flow.src != flow.dst:
            written.setdefault(flow.src, set()).add(flow.dst)
    return {
        op_id: frozenset(node_id_set)
        for op_id, node_id_set in written.items()
        if len(node_id_set) >= 2
    }


def _has_saga(attrs: tuple[str, ...]) -> bool:
    """Whether an op node's `attrs` carries `saga`."""
    return _SAGA_ATTR in attrs


def _missing_saga_violations(model: KernelModel) -> list[DistributedTxnViolation]:
    """REL350: every multi-service-write op with no `saga` attr."""
    nodes_by_id = {node.id: node for node in model.nodes}
    violations: list[DistributedTxnViolation] = []
    for op_id, written_ids in sorted(_multi_service_writers(model).items()):
        op_node = nodes_by_id.get(op_id)
        if op_node is None or _has_saga(op_node.attrs):
            continue
        services = ", ".join(sorted(written_ids))
        _log.warning(
            "distributed_txn: REL350 op %s writes services %s with no "
            "saga/compensation strategy",
            op_id,
            services,
        )
        violations.append(
            DistributedTxnViolation(
                rule=REL_MISSING_SAGA,
                node=op_id,
                detail=(
                    f"op {op_id} writes across services {services} with no "
                    "declared saga/compensation strategy (no `saga` attr)"
                ),
            )
        )
    return violations


def _unproven_saga_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[DistributedTxnViolation]:
    """REL351: every multi-service-write op declaring `saga` with bound
    code, but whose bound code carries no real saga/compensation-shaped
    token (PROVABILITY CONSTRAINT). Mirrors `_txn.py::
    _unproven_txn_boundary_violations` exactly, parameterized on
    `_SAGA_TOKEN_RE`."""
    nodes_by_id = {node.id: node for node in model.nodes}
    violations: list[DistributedTxnViolation] = []
    for op_id in sorted(_multi_service_writers(model)):
        op_node = nodes_by_id.get(op_id)
        if op_node is None or not _has_saga(op_node.attrs):
            continue
        if not node_has_bound_code(op_id, owner_by_node):
            continue
        if files_evidence_token(owner_by_node[op_id], root, _SAGA_TOKEN_RE):
            continue
        _log.warning(
            "distributed_txn: REL351 op %s declares saga but bound code has "
            "no real saga/compensation token",
            op_id,
        )
        violations.append(
            DistributedTxnViolation(
                rule=REL_UNPROVEN_SAGA,
                node=op_id,
                detail=(
                    f"op {op_id} declares saga, but its bound code has no "
                    "real saga/compensation token (proof-against-code, "
                    "T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_distributed_txn_waivers(
    model: KernelModel, violations: list[DistributedTxnViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_txn.py::_apply_txn_waivers`'s pattern reused for the REL35x
    family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in DISTRIBUTED_TXN_RULES,
    )


# frob:doc docs/strata/reliability.md#rel35x-distributed-transaction-across-services-obligation-t-0655  # noqa: E501
# frob:ticket T-0655
# frob:ticket T-0958
# frob:enforces SDC-4-DISTRIBUTED-TRANSACTIONS
# frob:enforces SDC-4-OUTBOX-SAGA-PATTERNS
# frob:tests tests/unit/strata/test_distributed_txn.py::TestMissingSaga.test_multi_service_write_op_without_saga_fires  # noqa: E501
def check_distributed_txn_obligations(
    model: KernelModel, root: Path
) -> Result[DistributedTxnReport, StrataError]:
    """The REL35x DISTRIBUTED-TRANSACTION-ACROSS-SERVICES entrypoint
    (T-0655): REL350 (missing saga/compensation) and REL351 (declared-
    but-unproven saga, proof-against-code) across every op writing to
    >=2 distinct downstream nodes in `model`, waivers already applied.
    Unlike `_txn.py::check_txn_boundary_obligations`, this takes no
    caller-supplied `store_ids` -- module docstring: every node already
    IS a service boundary, so the population is every node `model.flows`
    names, not a caller-narrowed subset. `root` is the repo root
    `_code_binding.py::bind_code` binds against -- `Err` propagates
    `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by default, the
    same discipline `check_txn_boundary_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[DistributedTxnViolation] = []
    violations.extend(_missing_saga_violations(model))
    violations.extend(_unproven_saga_violations(model, owner_by_node, root))
    applied = _apply_distributed_txn_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        DistributedTxnViolation(
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
        "distributed_txn: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(
        DistributedTxnReport(violations=tuple(applied.kept) + stale, waived=waived)
    )


__all__ = [
    "DISTRIBUTED_TXN_RULES",
    "REL_MISSING_SAGA",
    "REL_UNPROVEN_SAGA",
    "DistributedTxnReport",
    "DistributedTxnViolation",
    "check_distributed_txn_obligations",
]
