"""HOST001 lateral-movement checks (T-2844 split of `_host_isolation.py`,
docs/strata/host.md#movement-impossibility-proofs): for every distinct
service-user pair, prove no shared writable path, no unmitigated
cross-user socket, and no shared OS group -- see `_host_isolation.py`'s
module docstring for the full HOST001/HOST002 design and the split
rationale."""

# frob:waive REF002 reason="T-2844: this is one of three sibling check modules the \
# LARGE001 split of _host_isolation.py produced; only the facade (_host_isolation.py) \
# imports this module directly by design, one anchor per module, the same shape \
# T-2729's sibling split-out modules already set -- not an accidental single-consumer \
# anchor"

from __future__ import annotations

from typani.result import Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._host import HostManifest, manifests_by_node
from ._host_isolation_shared import (
    _SUB_CROSS_USER_SOCKET,
    _SUB_SHARED_GROUP,
    _SUB_SHARED_WRITABLE_PATH,
    HostIsolationViolation,
    _groups_by_user,
    _listening_surface_by_user,
    _nodes_by_user,
    _shared_writable_paths,
)
from ._models import KernelModel

_log = get_logger(__name__)


def _declared_flow_between(
    model: KernelModel, nodes_a: list[str], nodes_b: list[str]
) -> bool:
    """Whether any `Flow` in `model` connects a node of user A to a node
    of user B (either direction) -- the "unless a declared flow exists"
    escape hatch HOST001's cross-user-socket sub-target names."""
    set_a, set_b = frozenset(nodes_a), frozenset(nodes_b)
    return any(
        (flow.src in set_a and flow.dst in set_b)
        or (flow.src in set_b and flow.dst in set_a)
        for flow in model.flows
    )


def _shared_writable_path_violations(
    user_a: str,
    nodes_a: list[str],
    user_b: str,
    nodes_b: list[str],
    manifests: dict[str, HostManifest],
) -> list[HostIsolationViolation]:
    """HOST001 shared-writable-path findings for one user pair -- every
    path both users own (linux `owns` or windows `acl`, module docstring)
    where at least one side's claim is write-capable."""
    shared_writable = _shared_writable_paths(nodes_a, nodes_b, manifests)
    return [
        HostIsolationViolation(
            rule="HOST001",
            sub_target=_SUB_SHARED_WRITABLE_PATH,
            user=user_a,
            peer=user_b,
            detail=f"users {user_a!r} and {user_b!r} both own writable path "
            f"{path!r} -- a compromise of either reaches the other's data",
        )
        for path in shared_writable
    ]


def _shared_socket_violations(
    model: KernelModel,
    user_a: str,
    nodes_a: list[str],
    user_b: str,
    nodes_b: list[str],
    manifests: dict[str, HostManifest],
) -> list[HostIsolationViolation]:
    """HOST001 cross-user-socket finding for one user pair, unless a
    declared `Flow` already bridges them (the documented escape hatch).
    `shared` is over the labeled listening surface (module docstring's
    "Listening surface" section) -- a shared linux PORT, a shared
    windows PIPE, or one of each declared on either side."""
    surface_a = _listening_surface_by_user(nodes_a, manifests)
    surface_b = _listening_surface_by_user(nodes_b, manifests)
    shared = sorted(surface_a & surface_b)
    if not shared or _declared_flow_between(model, nodes_a, nodes_b):
        return []
    return [
        HostIsolationViolation(
            rule="HOST001",
            sub_target=_SUB_CROSS_USER_SOCKET,
            user=user_a,
            peer=user_b,
            detail=f"users {user_a!r} and {user_b!r} both listen on "
            f"{shared} with no declared Flow between their nodes -- "
            "an undeclared cross-user socket path",
        )
    ]


def _shared_group_violations(
    user_a: str,
    nodes_a: list[str],
    user_b: str,
    nodes_b: list[str],
    manifests: dict[str, HostManifest],
) -> list[HostIsolationViolation]:
    """HOST001 shared-group findings for one user pair (T-0272) -- one
    finding per OS group both users' `HostManifest.group` (`_groups_by_
    user`) declare in common, DERIVED the same way `_shared_writable_
    path_violations` intersects `owns`. A pair sharing no declared group
    produces no finding -- absence of a shared group is now structurally
    provable, not an always-fire honest gap (module docstring)."""
    groups_a = _groups_by_user(nodes_a, manifests)
    groups_b = _groups_by_user(nodes_b, manifests)
    shared = sorted(groups_a & groups_b)
    return [
        HostIsolationViolation(
            rule="HOST001",
            sub_target=_SUB_SHARED_GROUP,
            user=user_a,
            peer=user_b,
            detail=f"users {user_a!r} and {user_b!r} share OS group {group!r} "
            "-- a compromise of either reaches resources granted to that group",
        )
        for group in shared
    ]


def _lateral_pair_violations(
    model: KernelModel,
    user_a: str,
    nodes_a: list[str],
    user_b: str,
    nodes_b: list[str],
    manifests: dict[str, HostManifest],
) -> list[HostIsolationViolation]:
    """Every HOST001 sub-target finding for one (user_a, user_b) pair,
    DERIVED from the two users' `HostManifest` slices -- shared writable
    path, cross-user socket unless a declared flow bridges them, and any
    shared OS group (T-0272, module docstring)."""
    violations: list[HostIsolationViolation] = []
    violations.extend(
        _shared_writable_path_violations(user_a, nodes_a, user_b, nodes_b, manifests)
    )
    violations.extend(
        _shared_socket_violations(model, user_a, nodes_a, user_b, nodes_b, manifests)
    )
    violations.extend(
        _shared_group_violations(user_a, nodes_a, user_b, nodes_b, manifests)
    )
    return violations


def _all_lateral_pair_violations(
    model: KernelModel, users: list[str], by_user: dict[str, list[str]], manifests
) -> list[HostIsolationViolation]:
    """`_lateral_pair_violations` over every distinct unordered user pair,
    in the deterministic (sorted-users, i<j) order `evaluate_lateral_
    isolation` requires for a reproducible run."""
    violations: list[HostIsolationViolation] = []
    for i, user_a in enumerate(users):
        for user_b in users[i + 1 :]:
            violations.extend(
                _lateral_pair_violations(
                    model, user_a, by_user[user_a], user_b, by_user[user_b], manifests
                )
            )
    return violations


# frob:waive AFFECT001 reason="T-2844: LARGE001 split of _host_isolation.py by \
# lateral/vertical/movement seam -- this symbol only moved to a sibling module \
# verbatim (same name, same body/signature), no behavior change, so the \
# affects()-closure doc it names needs no update"
# frob:doc docs/strata/host.md#movement-impossibility-proofs
# frob:tests \
# tests/unit/strata/test_host_isolation.py::TestLateralIsolation.test_skips_below_two_u\
# sers kind="unit"
def evaluate_lateral_isolation(
    model: KernelModel,
) -> Result[tuple[HostIsolationViolation, ...], StrataError]:
    """HOST001: for every DISTINCT service-user pair (only fires when the
    model declares 2+ `runs_as` users, docs/strata/host.md#movement-
    impossibility-proofs), prove no shared writable path, no
    unmitigated cross-user socket, and no shared group -- every finding
    DERIVED from `HostManifest` intersection (module docstring), never
    hand-written per pair. Pairs are unordered but each finding names
    `user`/`peer` in the deterministic (sorted) order the users were
    encountered so a run is reproducible."""
    nodes_by_id = {n.id: n for n in model.nodes}
    manifests = manifests_by_node(model)
    by_user = _nodes_by_user(nodes_by_id, manifests)
    users = sorted(by_user)
    if len(users) < 2:
        _log.info(
            "host_isolation: HOST001 skipped -- %d runs_as user(s) declared, need 2+",
            len(users),
        )
        return Ok(())

    violations = _all_lateral_pair_violations(model, users, by_user, manifests)
    _log.info(
        "host_isolation: HOST001 evaluated %d user pair(s) -> %d violation(s)",
        len(users) * (len(users) - 1) // 2,
        len(violations),
    )
    return Ok(tuple(violations))
