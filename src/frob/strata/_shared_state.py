"""REL36x reliability family: NO-SHARED-MUTABLE-STATE-ACROSS-SERVICE-
BOUNDARIES obligation (T-0656, child of the T-0331 systems-checks epic,
docs/strata/reliability.md), mirroring `_spof.py`'s REL25x structure
(module docstring precedent: ONE RULE, not a missing/unproven pair --
like REL250, shared mutable state is a STRUCTURAL fact readable straight
off the kernel model, not an operator-declared obligation needing
separate proof-against-code).

RELATIONSHIP TO REL29x (SSOT), HONESTLY DISTINGUISHED: `_ssot.py`'s
REL290/REL291 already flag a store written by >=2 distinct nodes with no
declared `owner`/`reconciliation` -- but REL29x's obligation is
DISCHARGEABLE by declaring who owns write authority; two services are
still allowed to share the SAME mutable store as long as a
reconciliation strategy is named. REL36x is a STRICTER, INDEPENDENT
architectural principle: services should not share mutable state
DIRECTLY at all (communicate via APIs/messages instead), regardless of
whether the sharing is reconciled -- so REL360 is NOT discharged by
`owner`/`reconciliation` (those answer "how do conflicts resolve", not
"should this state be shared at all"), only by a dedicated
`shared_state_ok` exemption naming the sharing itself as a reviewed,
accepted exception. REL36x's population is also BROADER than REL29x's:
SSOT only counts WRITERS (a node is a "writer" only via an outbound
`Flow` landing on the store); REL36x counts every ACCESSOR (a node
touching the shared node via a `Flow` in EITHER direction -- a read-only
consumer of a store two independent services write into is still
coupled to that store's shape and lifecycle, the same hazard class even
though it never itself writes).

  - REL360 shared mutable state across service boundaries: some MUTABLE
    node (module docstring: a node that is the `dst` of at least one
    `Flow` at all -- something writes into it, so it holds state that can
    change) is ACCESSED (touched as either `src` or `dst` of a `Flow`) by
    `Flow`s connecting it to >=2 distinct OTHER nodes (every `Flow`
    already crosses a real process/service boundary by construction,
    REL2xx's own module docstring -- so >=2 distinct accessing nodes IS
    >=2 distinct services), and the shared node does not carry the
    `shared_state_ok` exemption attr. Deny-by-default with a reasoned
    waive channel (T-0174), same discipline every REL2xx/REL3xx
    obligation in this cluster uses.

GRAMMAR-DATA CEILING, HONESTLY: `shared_state_ok` is a presence-only bare
Node attr -- the same digit-led-literal ceiling every other REL2xx/REL3xx
marker in this family discloses. No `strata-core` change needed (this
ticket's scope is `src/frob/strata/**`/`docs/strata/**`/
`tests/unit/strata/**` only, same as T-0640/.../T-0655's).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's 'only' hits \
# are source-level design-rationale/scope-cut prose mirroring _spof.py's own identical \
# waiver for the identical reason (module docstring precedent, T-0656), not a separate \
# cross-module contract"

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._models import KernelModel
from ._waive import apply_waivers

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL360 shared mutable state across
#: service boundaries: a mutable node accessed (read or write) by >=2
#: distinct other nodes, no `shared_state_ok` exemption.
# frob:doc docs/strata/reliability.md#rel36x-no-shared-mutable-state-across-service-boundaries-obligation-t-0656  # noqa: E501
REL_SHARED_MUTABLE_STATE = "REL360"

#: Every REL36x rule id this module can emit -- this module's own,
#: narrow family for `_apply_shared_state_waivers`' `in_scope` (the
#: "never a shared superset" discipline `_reliability.py`'s module
#: docstring documents the real regression for). A one-element frozenset
#: today (REL36x is a single rule, module docstring), kept as a set (not
#: a bare constant comparison) so a future REL36x sibling rule slots into
#: `_apply_shared_state_waivers` without a call-site change.
# frob:doc docs/strata/reliability.md#rel36x-no-shared-mutable-state-across-service-boundaries-obligation-t-0656  # noqa: E501
SHARED_STATE_RULES: frozenset[str] = frozenset({REL_SHARED_MUTABLE_STATE})

#: Node attr exempting a shared mutable node from REL360 -- an explicit
#: modeler assertion that the direct sharing is a reviewed, accepted
#: exception (module docstring: distinct from, and not satisfied by,
#: REL29x's `owner`/`reconciliation`).
_SHARED_STATE_OK_ATTR = "shared_state_ok"


# frob:doc docs/strata/reliability.md#rel36x-no-shared-mutable-state-across-service-boundaries-obligation-t-0656  # noqa: E501
class SharedStateViolation(BaseModel):
    """One REL360 finding: rule id, the node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-node (a node either
    is or is not shared mutable state this run; module docstring), the
    same bare-rule waiver carve-out REL250 uses. Mirrors
    `_spof.py::SpofViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel36x-no-shared-mutable-state-across-service-boundaries-obligation-t-0656  # noqa: E501
class SharedStateReport(BaseModel):
    """Every UNWAIVED REL36x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_spof.py::SpofReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[SharedStateViolation, ...] = ()
    waived: tuple[SharedStateViolation, ...] = ()


def _mutable_node_ids(model: KernelModel) -> set[str]:
    """Every node id that is the `dst` of at least one `Flow` at all --
    something writes into it, so it holds state that can change (module
    docstring's "mutable" definition)."""
    return {flow.dst for flow in model.flows}


def _accessors(model: KernelModel) -> dict[str, set[str]]:
    """node id -> every OTHER node id touching it via a `Flow` in EITHER
    direction (module docstring: broader than `_ssot.py`'s writer-only
    count -- a read-only consumer still counts as an accessor)."""
    accessors: dict[str, set[str]] = {}
    for flow in model.flows:
        if flow.src == flow.dst:
            continue
        accessors.setdefault(flow.dst, set()).add(flow.src)
        accessors.setdefault(flow.src, set()).add(flow.dst)
    return accessors


def _is_shared_state_ok(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the `shared_state_ok` exemption."""
    return _SHARED_STATE_OK_ATTR in attrs


# frob:ticket T-0972
def _shared_state_violations(model: KernelModel) -> list[SharedStateViolation]:
    """REL360: every mutable node accessed (read or write) by >=2 distinct
    other nodes, with no `shared_state_ok` exemption."""
    nodes_by_id = {node.id: node for node in model.nodes}
    mutable_ids = _mutable_node_ids(model)
    accessors = _accessors(model)
    violations: list[SharedStateViolation] = []
    for node_id in sorted(accessors):
        if node_id not in mutable_ids:
            continue
        accessing = accessors[node_id]
        if len(accessing) < 2:
            continue
        node = nodes_by_id.get(node_id)
        if node is None or _is_shared_state_ok(node.attrs):
            continue
        # frob:waive PERF004 reason="accessing is this loop's own per-node distinct set, not a shared re-sort"  # noqa: E501
        services = ", ".join(sorted(accessing))
        _log.warning(
            "shared_state: REL360 node %s is mutable state shared across "
            "services %s with no `shared_state_ok` exemption",
            node_id,
            services,
        )
        violations.append(
            SharedStateViolation(
                rule=REL_SHARED_MUTABLE_STATE,
                node=node_id,
                detail=(
                    f"node {node_id} is mutable state (written into by at "
                    "least one flow) accessed directly by services "
                    f"{services}, with no `shared_state_ok` exemption -- "
                    "services should not share mutable state directly"
                ),
            )
        )
    return violations


def _apply_shared_state_waivers(
    model: KernelModel, violations: list[SharedStateViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_spof.py::_apply_spof_waivers`'s pattern reused for the REL36x
    family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in SHARED_STATE_RULES,
    )


# frob:doc docs/strata/reliability.md#rel36x-no-shared-mutable-state-across-service-boundaries-obligation-t-0656  # noqa: E501
# frob:ticket T-0656
# frob:tests tests/unit/strata/test_shared_state.py::TestSharedState.test_mutable_node_shared_by_two_services_fires  # noqa: E501
def check_shared_state(model: KernelModel) -> SharedStateReport:
    """The REL36x NO-SHARED-MUTABLE-STATE-ACROSS-SERVICE-BOUNDARIES
    entrypoint (T-0656): REL360 across every mutable node in `model`
    accessed by >=2 distinct services, waivers already applied. Like
    `_spof.py::check_spof`, this takes no `root`/`bind_code` call and
    returns a bare `SharedStateReport`, not a `Result` -- REL360 is a
    pure structural read of the kernel model (module docstring), so it
    cannot `Err` the way a proof-against-code entrypoint can."""
    violations = _shared_state_violations(model)
    applied = _apply_shared_state_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        SharedStateViolation(
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
        "shared_state: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return SharedStateReport(violations=tuple(applied.kept) + stale, waived=waived)


__all__ = [
    "REL_SHARED_MUTABLE_STATE",
    "SHARED_STATE_RULES",
    "SharedStateReport",
    "SharedStateViolation",
    "check_shared_state",
]
