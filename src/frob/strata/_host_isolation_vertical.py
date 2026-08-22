"""HOST002 vertical-movement checks (T-2844 split of `_host_isolation.py`,
docs/strata/host.md#movement-impossibility-proofs): per declared service
user, prove no setuid path owned, no sudoers grant, no root-run unit
whose owned paths this user can write to, and no write access to a path
a higher-trust node also owns -- see `_host_isolation.py`'s module
docstring for the full HOST001/HOST002 design and the split rationale."""

# frob:waive REF002 reason="T-2844: this is one of three sibling check modules the \
# LARGE001 split of _host_isolation.py produced; only the facade (_host_isolation.py) \
# imports this module directly by design, one anchor per module, the same shape \
# T-2729's sibling split-out modules already set -- not an accidental single-consumer \
# anchor"

from __future__ import annotations

from typani.result import Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._host import HostManifest, HostOwns, manifests_by_node
from ._host_isolation_shared import (
    _SUB_HIGHER_TRUST_WRITE,
    _SUB_ROOT_UNIT_WRITABLE,
    _SUB_SETUID,
    _SUB_SUDOERS,
    HostIsolationViolation,
    _mode_has_setuid,
    _nodes_by_user,
    _owned_paths_by_user,
    _owns_by_user,
    _PathClaim,
    _sudoers_by_user,
)
from ._models import KernelModel, Node

_log = get_logger(__name__)


def _root_run_nodes(
    nodes_by_id: dict[str, Node], manifests: dict[str, HostManifest]
) -> list[str]:
    """Node ids that run as the platform's privileged default identity: a
    declared `unit` with no `runs_as` (systemd's own default `User=root`)
    OR a declared `service` with no `service_account` (SCM's own default
    LocalSystem) -- the surface has no way to declare "root"/"LocalSystem"
    explicitly on either platform, so absence of a dedicated identity on
    a unit/service IS the privileged-run case (module docstring's
    "Root-run identity" section)."""
    return sorted(
        node_id
        for node_id, manifest in manifests.items()
        if (manifest.is_unit and manifest.runs_as is None)
        or (manifest.is_service and manifest.service_account is None)
    )


def _setuid_violations(
    user: str, owns: dict[str, HostOwns]
) -> list[HostIsolationViolation]:
    """HOST002 setuid-path findings for one user's owned paths."""
    return [
        HostIsolationViolation(
            rule="HOST002",
            sub_target=_SUB_SETUID,
            user=user,
            detail=f"user {user!r} owns setuid path {path!r} (mode "
            f"{owns[path].mode!r}) -- privilege escalation on compromise",
        )
        for path in sorted(owns)
        if _mode_has_setuid(owns[path].mode)
    ]


def _sudoers_violations(
    user: str, user_nodes: list[str], manifests: dict[str, HostManifest]
) -> list[HostIsolationViolation]:
    """HOST002 sudoers findings for one service user (T-0272) -- one
    finding per declared `HostManifest.sudoers` grant (`_sudoers_by_
    user`), DERIVED the same way `_setuid_violations` reads `owns`. A
    user with no declared sudoers grant produces no finding -- absence
    of a grant is now structurally provable, not an always-fire honest
    gap (module docstring)."""
    return [
        HostIsolationViolation(
            rule="HOST002",
            sub_target=_SUB_SUDOERS,
            user=user,
            detail=f"user {user!r} holds sudoers grant {rule!r} -- "
            "privilege escalation on compromise",
        )
        for rule in _sudoers_by_user(user_nodes, manifests)
    ]


def _root_unit_writable_violations(
    user: str,
    owns: dict[str, _PathClaim],
    root_nodes: list[str],
    manifests: dict[str, HostManifest],
) -> list[HostIsolationViolation]:
    """HOST002 findings where `user` writably owns a path a root-run
    unit/service also owns (linux `owns` or windows `acl`, module
    docstring) -- a plant-then-root-executes vector."""
    violations: list[HostIsolationViolation] = []
    for root_id in root_nodes:
        root_paths = _owned_paths_by_user([root_id], manifests)
        for path, root_claim in root_paths.items():
            user_entry = owns.get(path)
            if user_entry is not None and user_entry.write_capable:
                violations.append(
                    HostIsolationViolation(
                        rule="HOST002",
                        sub_target=_SUB_ROOT_UNIT_WRITABLE,
                        user=user,
                        detail=f"root-run unit/service {root_id!r} owns path "
                        f"{path!r} ({root_claim.descriptor!r}), which user "
                        f"{user!r} also owns writably ({user_entry.descriptor!r}) "
                        "-- a user compromise can plant content a root-run "
                        "unit/service later executes/reads",
                    )
                )
    return violations


def _higher_trust_write_violations(
    model: KernelModel,
    trust_by_node: dict[str, str],
    user: str,
    user_nodes: list[str],
    owns: dict[str, _PathClaim],
    manifests: dict[str, HostManifest],
) -> list[HostIsolationViolation]:
    """HOST002 findings where `user` writably owns a path also owned by a
    strictly-higher-trust node (linux `owns` or windows `acl`, module
    docstring) -- a corrupt-input-for-a-more-trusted-reader vector."""
    violations: list[HostIsolationViolation] = []
    user_trust = trust_by_node.get(user_nodes[0])
    for node_id, node_trust in sorted(trust_by_node.items()):
        if node_id in user_nodes or user_trust is None:
            continue
        higher = model.trust.leq(user_trust, node_trust)
        if higher.is_err or not higher.danger_ok or node_trust == user_trust:
            continue
        peer_manifest = manifests.get(node_id)
        if peer_manifest is None:
            continue
        peer_paths = _owned_paths_by_user([node_id], manifests)
        # frob:waive PERF004 reason="differs per (user, peer node) pair -- fresh work \
        # each iteration, not a re-sort of the same set"
        for path in sorted(set(owns) & set(peer_paths)):
            if owns[path].write_capable:
                violations.append(
                    HostIsolationViolation(
                        rule="HOST002",
                        sub_target=_SUB_HIGHER_TRUST_WRITE,
                        user=user,
                        detail=f"user {user!r} writably owns path {path!r} "
                        f"({owns[path].descriptor!r}) also owned by higher-trust "
                        f"node {node_id!r} ({node_trust}) -- a user compromise "
                        "can corrupt input a more-trusted node reads",
                    )
                )
    return violations


def _vertical_user_violations(
    model: KernelModel,
    trust_by_node: dict[str, str],
    user: str,
    user_nodes: list[str],
    manifests: dict[str, HostManifest],
    root_nodes: list[str],
) -> list[HostIsolationViolation]:
    """Every HOST002 sub-target finding for one service user, DERIVED from
    that user's `HostManifest` slice plus the model's root-run units and
    trust lattice (module docstring). `setuid` reads the linux-only raw
    `owns` (`_owns_by_user`, no windows analog); every other sub-target
    reads the platform-merged `_owned_paths_by_user` (module docstring's
    "Windows wiring" section)."""
    linux_owns = _owns_by_user(user_nodes, manifests)
    owns = _owned_paths_by_user(user_nodes, manifests)
    violations: list[HostIsolationViolation] = []
    violations.extend(_setuid_violations(user, linux_owns))
    violations.extend(_sudoers_violations(user, user_nodes, manifests))
    violations.extend(_root_unit_writable_violations(user, owns, root_nodes, manifests))
    violations.extend(
        _higher_trust_write_violations(
            model, trust_by_node, user, user_nodes, owns, manifests
        )
    )
    return violations


# frob:waive AFFECT001 reason="T-2844: LARGE001 split of _host_isolation.py by \
# lateral/vertical/movement seam -- this symbol only moved to a sibling module \
# verbatim (same name, same body/signature), no behavior change, so the \
# affects()-closure doc it names needs no update"
# frob:doc docs/strata/host.md#movement-impossibility-proofs
# frob:doc docs/strata/host.md#windows-wiring-t-0606
# frob:doc \
# docs/strata/host.md#multi-ace-deny-overrides-allow-join-and-the-write_dac-indirection\
# -corner-t-0792t-0825
# frob:invariant INV-033
# frob:tests \
# tests/unit/strata/test_host_isolation.py::TestVerticalIsolation.test_skips_with_no_us\
# ers kind="unit"
def evaluate_vertical_isolation(
    model: KernelModel,
) -> Result[tuple[HostIsolationViolation, ...], StrataError]:
    """HOST002: PER declared service user, prove no setuid path owned, no
    sudoers grant, no root-run unit whose owned paths this user can write
    to, and no write access to a path a higher-trust node also owns --
    every finding DERIVED from `HostManifest` plus the model's existing
    trust lattice (module docstring), never hand-written per user."""
    nodes_by_id = {n.id: n for n in model.nodes}
    manifests = manifests_by_node(model)
    by_user = _nodes_by_user(nodes_by_id, manifests)
    if not by_user:
        _log.info("host_isolation: HOST002 skipped -- no runs_as users declared")
        return Ok(())

    trust_by_node = {node_id: nodes_by_id[node_id].trust for node_id in manifests}
    root_nodes = _root_run_nodes(nodes_by_id, manifests)

    violations: list[HostIsolationViolation] = []
    for user in sorted(by_user):
        violations.extend(
            _vertical_user_violations(
                model, trust_by_node, user, by_user[user], manifests, root_nodes
            )
        )
    _log.info(
        "host_isolation: HOST002 evaluated %d user(s) -> %d violation(s)",
        len(by_user),
        len(violations),
    )
    return Ok(tuple(violations))
