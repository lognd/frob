"""REL34x reliability family: SYNC CALL-CHAIN DEPTH bound (T-0654, child
of the T-0331 systems-checks epic, docs/strata/reliability.md), mirroring
`_spof.py`'s REL25x structure (module docstring precedent: ONE RULE, not
a missing/unproven pair -- like REL250, an over-deep synchronous call
chain is a STRUCTURAL fact readable straight off the kernel model, not an
operator-declared obligation needing separate proof-against-code).

A synchronous call chain (a path of flows the caller BLOCKS on, one
awaiting the next) that grows too deep is a cascading-latency/failure
risk: each hop adds its own latency to the critical path, and a failure
at the bottom of a deep chain propagates a hang/error back through every
synchronous caller above it (the exact "no-hang" concern `_crash.py`'s
module docstring already names for a single hop, generalized here to a
whole chain). A flow marked `async` (`_crash.py::_ASYNC_ATTR`, reused
here -- the SAME "this hop does not block its caller" meaning, at the
SAME grammar site, so imported directly rather than re-declared: unlike
`_spof.py`'s deliberate non-import of a coincidentally-reused word, this
IS the same fact) breaks the chain: a caller firing an async hop is not
blocked on it, so the chain measured here does not continue past it.

  - REL340 sync call-chain depth exceeded: some node is reachable from
    another only by following `_SYNC_CHAIN_MAX_DEPTH` (a fixed, non-
    declarable default -- GRAMMAR-DATA CEILING below) or more consecutive
    synchronous (non-`async`) flow hops, and does not carry the
    `deep_chain_ok` exemption attr (an explicit modeler assertion that
    the depth is a reviewed, accepted risk -- e.g. the chain fans out to
    genuinely independent slow paths that do not compound in practice).
    Deny-by-default with a reasoned waive channel (T-0174), same
    discipline every REL2xx/REL3xx obligation in this cluster uses.

REACHABILITY CHOICE, HONESTLY: this module does NOT reuse `_facts.py::
FactBase.reachable` (T-0282's terminal/non-transitive-edge machinery,
which the ticket body points at) directly -- `reachable`'s non-transitive
attr sets (`_NON_TRANSITIVE_ATTRS`/`_NOFLOW_NON_TRANSITIVE_ATTRS`) are
fixed, `_facts.py`-owned constants that encode TRUST-BOUNDARY/KRB/utility
terminal semantics shared by every other closure consumer (PII,
compliance, breach, krb-movement); folding `async` into that shared set
would change taint-closure semantics for every one of those unrelated
callers, a cross-cutting change well outside this ticket's own rule-
module scope (charter law 1's spirit: don't smuggle a new obligation's
needs into a shared primitive other obligations depend on). SYNC-CHAIN
DEPTH needs the SAME underlying idea T-0282 introduced -- a marked edge
attribute makes a hop a terminal/non-continuing edge in an otherwise-
transitive walk -- applied to a narrower, independent graph (only
sync-vs-async, nothing else terminal), so this module computes its own
longest-path-ending-at-node walk directly over `model.flows` (a
memoized DFS with `_lattice_is_acyclic`-style cycle detection, mirroring
`_facts.py::FactBase.worst_age`'s own "a cycle means unbounded" `inf`
discipline for the SAME reason: a cycle of synchronous calls is not a
finite chain, it is a hang).

GRAMMAR-DATA CEILING, HONESTLY: `deep_chain_ok` is a presence-only bare
Node attr (no numeric magnitude -- the same digit-led-literal ceiling
every other REL2xx/REL3xx marker in this family discloses, `strata-core/
src/parse.rs`'s generic `attr KEY=IDENT` clause cannot hold a digit-led
bound), so a model CANNOT declare its own depth bound -- `_SYNC_CHAIN_MAX_
DEPTH` is a fixed Python-side default, not a per-model override (the
ticket body's "declared/default depth bound" language: this ships the
DEFAULT half only; a per-model declared override would need a NEW
kernel-level numeric field, out of this ticket's `src/frob/strata/**` rule-
module scope). No `strata-core` change needed (this ticket's scope is
`src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**` only, same
as T-0640/.../T-0653's).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's \
# 'only' hits are source-level design-rationale/scope-cut prose mirroring \
# _spof.py's own identical waiver for the identical reason (module \
# docstring precedent, T-0654), not a separate cross-module contract"

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._crash import _ASYNC_ATTR
from ._models import KernelModel
from ._waive import apply_waivers

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL340 sync call-chain depth exceeded: a
#: node reachable only via `_SYNC_CHAIN_MAX_DEPTH`+ consecutive
#: synchronous flow hops, no `deep_chain_ok` exemption.
# frob:doc docs/strata/reliability.md#rel34x-sync-call-chain-depth-bound-t-0654  # noqa: E501
REL_SYNC_CHAIN_TOO_DEEP = "REL340"

#: Every REL34x rule id this module can emit -- this module's own, narrow
#: family for `_apply_sync_depth_waivers`' `in_scope` (the "never a
#: shared superset" discipline `_reliability.py`'s module docstring
#: documents the real regression for). A one-element frozenset today
#: (REL34x is a single rule, module docstring), kept as a set (not a bare
#: constant comparison) so a future REL34x sibling rule slots into
#: `_apply_sync_depth_waivers` without a call-site change.
# frob:doc docs/strata/reliability.md#rel34x-sync-call-chain-depth-bound-t-0654  # noqa: E501
SYNC_DEPTH_RULES: frozenset[str] = frozenset({REL_SYNC_CHAIN_TOO_DEEP})

#: Default max consecutive synchronous flow hops before REL340 fires
#: (module docstring's GRAMMAR-DATA CEILING: not model-declarable today).
# frob:doc docs/strata/reliability.md#rel34x-sync-call-chain-depth-bound-t-0654  # noqa: E501
SYNC_CHAIN_MAX_DEPTH = 4

#: Node attr exempting a node from REL340 -- an explicit modeler
#: assertion that the measured depth is a reviewed, accepted risk.
_DEEP_CHAIN_OK_ATTR = "deep_chain_ok"


# frob:doc docs/strata/reliability.md#rel34x-sync-call-chain-depth-bound-t-0654  # noqa: E501
class SyncDepthViolation(BaseModel):
    """One REL340 finding: rule id, the node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-node (a node either
    is or is not too deep this run; module docstring), the same bare-rule
    waiver carve-out REL250 uses. Mirrors `_spof.py::SpofViolation`'s
    shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel34x-sync-call-chain-depth-bound-t-0654  # noqa: E501
class SyncDepthReport(BaseModel):
    """Every UNWAIVED REL34x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_spof.py::SpofReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[SyncDepthViolation, ...] = ()
    waived: tuple[SyncDepthViolation, ...] = ()


def _sync_predecessors(model: KernelModel) -> dict[str, list[str]]:
    """dst node id -> every src node id reaching it via a synchronous
    (non-`async`) flow -- the reverse adjacency `_sync_chain_depths`
    walks (a node's own depth is 1 + the deepest of its predecessors')."""
    predecessors: dict[str, list[str]] = {}
    for flow in model.flows:
        if _ASYNC_ATTR in flow.attrs:
            continue
        predecessors.setdefault(flow.dst, []).append(flow.src)
    return predecessors


def _sync_chain_depths(model: KernelModel) -> dict[str, float]:
    """Every node id reachable via at least one synchronous flow, mapped
    to the LONGEST synchronous call-chain depth (in hops) ending at it.
    A node with no synchronous inbound flow has depth 0 (it is not
    itself reached by any chain). A node fed by a synchronous cycle gets
    `math.inf` (module docstring: an unbounded chain, mirroring
    `_facts.py::FactBase.worst_age`'s identical cycle-to-inf discipline)."""
    predecessors = _sync_predecessors(model)
    memo: dict[str, float] = {}
    visiting: set[str] = set()

    def depth(node_id: str) -> float:
        if node_id in memo:
            return memo[node_id]
        if node_id in visiting:
            return math.inf
        visiting.add(node_id)
        preds = predecessors.get(node_id, ())
        result = 0.0 if not preds else 1.0 + max(depth(p) for p in preds)
        visiting.discard(node_id)
        memo[node_id] = result
        return result

    for node_id in predecessors:
        depth(node_id)
    return memo


def _is_deep_chain_ok(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the `deep_chain_ok` exemption."""
    return _DEEP_CHAIN_OK_ATTR in attrs


def _sync_depth_violations(model: KernelModel) -> list[SyncDepthViolation]:
    """REL340: every node whose deepest synchronous inbound call chain is
    `SYNC_CHAIN_MAX_DEPTH` hops or more (including an unbounded, cyclic
    chain), and which does not carry `deep_chain_ok`."""
    nodes_by_id = {node.id: node for node in model.nodes}
    violations: list[SyncDepthViolation] = []
    depths = _sync_chain_depths(model)
    for node_id in sorted(depths):
        depth = depths[node_id]
        if depth < SYNC_CHAIN_MAX_DEPTH:
            continue
        node = nodes_by_id.get(node_id)
        if node is None or _is_deep_chain_ok(node.attrs):
            continue
        depth_text = "unbounded (cyclic)" if math.isinf(depth) else str(int(depth))
        _log.warning(
            "sync_depth: REL340 node %s reached by a %s-hop synchronous "
            "call chain (bound %d)",
            node_id,
            depth_text,
            SYNC_CHAIN_MAX_DEPTH,
        )
        violations.append(
            SyncDepthViolation(
                rule=REL_SYNC_CHAIN_TOO_DEEP,
                node=node_id,
                detail=(
                    f"node {node_id} is reached by a {depth_text}-hop "
                    "synchronous call chain, at or past the default bound "
                    f"of {SYNC_CHAIN_MAX_DEPTH} (no `deep_chain_ok` "
                    "exemption) -- cascading latency/failure risk"
                ),
            )
        )
    return violations


def _apply_sync_depth_waivers(model: KernelModel, violations: list[SyncDepthViolation]):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_spof.py::_apply_spof_waivers`'s pattern reused for the REL34x
    family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in SYNC_DEPTH_RULES,
    )


# frob:doc docs/strata/reliability.md#rel34x-sync-call-chain-depth-bound-t-0654  # noqa: E501
# frob:ticket T-0654
# frob:tests tests/unit/strata/test_sync_depth.py::TestSyncDepth.test_chain_at_bound_fires  # noqa: E501
def check_sync_chain_depth(model: KernelModel) -> SyncDepthReport:
    """The REL34x SYNC-CALL-CHAIN-DEPTH-bound entrypoint (T-0654): REL340
    across every node in `model` reached by a too-deep synchronous call
    chain, waivers already applied. Like `_spof.py::check_spof`, this
    takes no `root`/`bind_code` call and returns a bare `SyncDepthReport`,
    not a `Result` -- REL340 is a pure structural read of the kernel
    model (module docstring), so it cannot `Err` the way a proof-
    against-code entrypoint can."""
    violations = _sync_depth_violations(model)
    applied = _apply_sync_depth_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        SyncDepthViolation(
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
        "sync_depth: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return SyncDepthReport(violations=tuple(applied.kept) + stale, waived=waived)


__all__ = [
    "SYNC_CHAIN_MAX_DEPTH",
    "SYNC_DEPTH_RULES",
    "REL_SYNC_CHAIN_TOO_DEEP",
    "SyncDepthReport",
    "SyncDepthViolation",
    "check_sync_chain_depth",
]
