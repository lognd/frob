"""Synthetic host-movement `Flow` materialization (T-2844 split of
`_host_isolation.py`, docs/strata/host.md#movement-impossibility-proofs):
`host_movement_flows` turns the SAME HostManifest-derived sharing
relations HOST001 detects (shared writable path, shared reachable
socket) into real `Flow` facts so a scenario's `NoFlow` closure sees
them -- see `_host_isolation.py`'s module docstring for the full design
and the split rationale."""

# frob:waive REF002 reason="T-2844: this is one of three sibling check modules the \
# LARGE001 split of _host_isolation.py produced; only the facade (_host_isolation.py) \
# imports this module directly by design, one anchor per module, the same shape \
# T-2729's sibling split-out modules already set -- not an accidental single-consumer \
# anchor"

from __future__ import annotations

from frob.logging import get_logger

from ._host import HostManifest, manifests_by_node
from ._host_isolation_shared import (
    _SUB_CROSS_USER_SOCKET,
    _SUB_SHARED_WRITABLE_PATH,
    _listening_surface_by_user,
    _nodes_by_user,
    _shared_writable_paths,
)
from ._models import Flow, KernelModel

_log = get_logger(__name__)


def _writable_path_flow_pair(
    node_a: str, node_b: str, path: str, seq: int
) -> tuple[list[Flow], int]:
    """The one bidirectional `Flow` pair for a single shared writable
    path (see `_writable_path_movement_flows`)."""
    flows: list[Flow] = []
    seq += 1
    flows.append(
        Flow(
            id=f"host-movement:{seq}:{path}:{node_a}->{node_b}",
            src=node_a,
            dst=node_b,
            attrs=(f"host_movement={_SUB_SHARED_WRITABLE_PATH}",),
        )
    )
    seq += 1
    flows.append(
        Flow(
            id=f"host-movement:{seq}:{path}:{node_b}->{node_a}",
            src=node_b,
            dst=node_a,
            attrs=(f"host_movement={_SUB_SHARED_WRITABLE_PATH}",),
        )
    )
    return flows, seq


def _writable_path_movement_flows(
    node_a: str,
    nodes_a: list[str],
    node_b: str,
    nodes_b: list[str],
    manifests: dict[str, HostManifest],
    seq: int,
) -> tuple[list[Flow], int]:
    """Bidirectional synthetic `Flow`s for every shared writable path
    (linux `owns` or windows `acl`, module docstring) between the two
    users' node lists (see `_movement_flows_for_pair`)."""
    shared_writable = _shared_writable_paths(nodes_a, nodes_b, manifests)
    flows: list[Flow] = []
    for path in shared_writable:
        pair_flows, seq = _writable_path_flow_pair(node_a, node_b, path, seq)
        flows.extend(pair_flows)
    return flows, seq


def _shared_port_movement_flows(
    node_a: str,
    nodes_a: list[str],
    node_b: str,
    nodes_b: list[str],
    manifests: dict[str, HostManifest],
    seq: int,
) -> tuple[list[Flow], int]:
    """Bidirectional synthetic `Flow`s if the two users share a listening
    surface -- a PORT, a windows PIPE, or both (see `_movement_flows_
    for_pair`, module docstring's "Listening surface" section)."""
    surface_a = _listening_surface_by_user(nodes_a, manifests)
    surface_b = _listening_surface_by_user(nodes_b, manifests)
    if not (surface_a & surface_b):
        return [], seq
    flows: list[Flow] = []
    seq += 1
    flows.append(
        Flow(
            id=f"host-movement:{seq}:port:{node_a}->{node_b}",
            src=node_a,
            dst=node_b,
            attrs=(f"host_movement={_SUB_CROSS_USER_SOCKET}",),
        )
    )
    seq += 1
    flows.append(
        Flow(
            id=f"host-movement:{seq}:port:{node_b}->{node_a}",
            src=node_b,
            dst=node_a,
            attrs=(f"host_movement={_SUB_CROSS_USER_SOCKET}",),
        )
    )
    return flows, seq


def _movement_flows_for_pair(
    user_a: str,
    nodes_a: list[str],
    user_b: str,
    nodes_b: list[str],
    manifests: dict[str, HostManifest],
    seq: int,
) -> tuple[list[Flow], int]:
    """Every synthetic host-movement `Flow` for one (user_a, user_b) pair:
    bidirectional edges over a shared writable path and over a shared
    listening port -- the SAME sharing relations `_lateral_pair_
    violations` detects for HOST001, materialized as real `Flow` facts
    here instead of a `HostIsolationViolation` (module docstring's
    `host_movement_flows`). Bidirectional: ownership alone does not tell
    which side WRITES and which side READS the shared resource, so both
    directions are added -- deny-by-default, never assuming a direction
    that happens to make a claim look safer (charter law 2)."""
    node_a, node_b = nodes_a[0], nodes_b[0]
    flows: list[Flow] = []
    path_flows, seq = _writable_path_movement_flows(
        node_a, nodes_a, node_b, nodes_b, manifests, seq
    )
    flows.extend(path_flows)
    port_flows, seq = _shared_port_movement_flows(
        node_a, nodes_a, node_b, nodes_b, manifests, seq
    )
    flows.extend(port_flows)
    return flows, seq


# frob:waive AFFECT001 reason="T-2844: LARGE001 split of _host_isolation.py by \
# lateral/vertical/movement seam -- this symbol only moved to a sibling module \
# verbatim (same name, same body/signature), no behavior change, so the \
# affects()-closure doc it names needs no update"
# frob:doc docs/strata/host.md#movement-impossibility-proofs
# frob:tests tests/unit/strata/test_host_isolation.py::test_movement_flows kind="unit"
def host_movement_flows(model: KernelModel) -> tuple[Flow, ...]:
    """Materialize HOST001's HostManifest-derived sharing relations
    (shared writable path, shared reachable socket) as real `Flow` facts
    -- the fix for the reviewer-found T-0256 REJECT-round vacuity gap:
    `_facts.py::FactBase.reachable` walks ONLY declared `Flow` edges, so
    a `NoFlow` claim over the bare declared-app-flow graph is blind to
    filesystem/OS movement vectors HOST001 itself already detects. A
    caller building a scenario whose closure must account for these
    vectors (`build_compromised_user_scenario`, `_scenarios.py`) wraps
    each returned `Flow` in an `AddFlow` rewrite so the scenario's
    rewritten model's closure sees them -- the base `KernelModel`'s own
    declared flows are left untouched (this is a scenario-scoped
    counterfactual fact, not a permanent model mutation).

    Computed over EVERY distinct service-user pair in `model`
    (independent of which user a caller later marks compromised) so a
    multi-hop movement path through a THIRD user's shared resource is
    still visible to the closure -- sound (more edges only tighten a
    `NoFlow` proof, never loosen it), not scoped to any one pair."""
    nodes_by_id = {n.id: n for n in model.nodes}
    manifests = manifests_by_node(model)
    by_user = _nodes_by_user(nodes_by_id, manifests)
    users = sorted(by_user)
    flows = _all_movement_flows(users, by_user, manifests)
    _log.info(
        "host_isolation: derived %d host-movement flow(s) over %d user pair(s)",
        len(flows),
        len(users) * (len(users) - 1) // 2,
    )
    return tuple(flows)


def _all_movement_flows(
    users: list[str], by_user: dict[str, list[str]], manifests: dict[str, HostManifest]
) -> list[Flow]:
    """`_movement_flows_for_pair` over every distinct unordered user pair,
    threading the sequence counter across pairs (see `host_movement_flows`)."""
    flows: list[Flow] = []
    seq = 0
    for i, user_a in enumerate(users):
        for user_b in users[i + 1 :]:
            pair_flows, seq = _movement_flows_for_pair(
                user_a, by_user[user_a], user_b, by_user[user_b], manifests, seq
            )
            flows.extend(pair_flows)
    return flows
