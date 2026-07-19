"""HOST001/HOST002: movement-impossibility proofs over `std.host`
manifests (T-0256, docs/strata/host.md#movement-impossibility-proofs).

T-0254 child 2, the SECURITY CORE of the deploy epic: the red-team
scenario ("assume one service user's process is compromised -- what can
it reach?") as a first-class, DEMANDED obligation the moment a model
declares 2+ `runs_as` service users, not an optional afterthought.

HOST001 (lateral movement) fires per DISTINCT service-user PAIR: prove
no shared writable filesystem path, no shared listening port reachable
across users without a declared `Flow` between their nodes, and (an
honest gap, see below) no shared OS group. HOST002 (vertical movement)
fires PER service user: no setuid path owned, no sudoers grant, no
root-run unit whose owned paths are writable by a lower-trust user, and
no write access to a path a higher-trust node also owns.

Every sub-target is DERIVED from `HostManifest` intersection
(`_host.py::host_manifest_for`) -- there is no hand-written per-pair or
per-user table to fall out of sync with the model, mirroring
`_threat.py::_entries_by_capability_kind`'s "one join, every caller
reuses it" discipline.

## The honest gap: two sub-targets `HostManifest` cannot see

`std.host` (T-0255) carries NO OS-group and NO sudoers-grant vocabulary
-- `strata-core/src/parse.rs`'s grammar is out of THIS ticket's declared
scope (`src/frob/strata/**` only, not `strata-core/**`), so neither can
be added here. Per T-0174's waive discipline (module docstring,
`_waive.py`), a sub-target this checker cannot structurally prove is
NEVER silently assumed safe (charter law 2, deny-by-default): `shared
group` and `sudoers` UNCONDITIONALLY fire for every pair/user a HOST001/
HOST002 obligation applies to, with a detail naming the missing grammar,
until an operator either files the grammar ticket (`frob:todo T-draft-7b5b5541`
below) or writes an explicit `waive "HOST001:shared-group" reason="..."`
/ `waive "HOST002:sudoers" reason="..."` clause. This is the SAME shape
`_threat.py::DEFAULT_BENIGN_CAPABILITIES` uses for a capability kind the
catalog has no sink for -- an honest, always-visible gap, not a false
"PROVED".

`setuid` (HOST002) IS derivable without new grammar: `owns "PATH"
"MODE"` already carries a full POSIX octal mode string
(`_host.py::HostOwns.mode`), and a 4-digit mode's leading digit encodes
the setuid/setgid/sticky bits (`_mode_owner_writable`/`_mode_has_setuid`
below) -- no grammar change needed, just reading a field that was
already there.

## Compromised-service-owner threat catalog rows

`COMPROMISED_OWNER_CATALOG` (below) adds the CWE-522/CWE-269/CWE-284
weakness rows this scenario class implicates, joining a SEPARATE
`compromised-owner-baseline` view (`COMPROMISED_OWNER_VIEWS`) rather
than widening `_threat.py::VIEWS`/`CWE_CATALOG` -- the SAME
separate-view precedent `QUALITY_VIEWS`/`CWE_TOP_25_VIEWS` already set
(`_threat.py` module docstring phase E / T-0143): a caller checking the
default OWASP baseline never silently starts being held to a HOST-only
obligation set it did not ask for.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._host import HostManifest, HostOwns, host_manifest_for
from ._models import Flow, KernelModel, Node, Rung
from ._threat import OutOfScopeEntry, WeaknessEntry
from ._waive import (
    WaiverApplication,
    apply_waivers,
)

_log = get_logger(__name__)

#: HOST001/HOST002 are multi-instance-per-node (one HOST001 finding per
#: service-user PAIR sub-target, one HOST002 finding per user sub-target)
#: -- the SAME blanket-waiver hazard `_waive.py::MULTI_INSTANCE_WAIVER_
#: FAMILIES` closes for SYS100/SYS101/THREAT002/THREAT003. A caller
#: wiring HOST001/HOST002 into a waiver-aware audit path MUST union this
#: set into whatever `MULTI_INSTANCE_WAIVER_FAMILIES` it validates
#: against (module docstring's ticket-mandated sub-target requirement) --
#: kept here, not appended to `_waive.py`'s frozen module constant, so a
#: bare-rule `waive "HOST001"` clause is rejected the identical way a
#: bare `waive "SYS100"` is (`_waive.py::validate_waiver_fields`).
# frob:doc docs/strata/host.md#waiver-discipline
HOST_MULTI_INSTANCE_WAIVER_FAMILIES: frozenset[str] = frozenset({"HOST001", "HOST002"})

#: HOST002 sub-target for the sudoers-grant check: `std.host` has no
#: sudoers vocabulary (module docstring "honest gap"), so this ALWAYS
#: fires until waived or the grammar lands.
_SUB_SUDOERS = "sudoers"

#: HOST001 sub-target for the shared-OS-group check: `std.host` has no
#: group vocabulary (module docstring "honest gap"), so this ALWAYS
#: fires for every qualifying pair until waived or the grammar lands.
_SUB_SHARED_GROUP = "shared-group"

_SUB_SETUID = "setuid"
_SUB_SHARED_WRITABLE_PATH = "shared-writable-path"
_SUB_CROSS_USER_SOCKET = "cross-user-socket"
_SUB_ROOT_UNIT_WRITABLE = "root-unit-writable-by-user"
_SUB_HIGHER_TRUST_WRITE = "write-to-higher-trust-path"


# frob:doc docs/strata/host.md#movement-impossibility-proofs
class HostIsolationViolation(BaseModel):
    """One HOST001 (lateral) or HOST002 (vertical) finding: the rule id,
    the sub-target (module docstring -- always present, HOST001/HOST002
    are multi-instance-per-node), the service user(s) implicated, and a
    human detail. `peer` is the second user for a HOST001 pairwise
    finding, `None` for a HOST002 per-user finding."""

    model_config = ConfigDict(frozen=True)

    rule: str  # "HOST001" | "HOST002"
    sub_target: str
    user: str
    peer: str | None = None
    detail: str = ""


def _rule_of(v: HostIsolationViolation) -> str:
    """`apply_waivers` extractor: the bare rule family (`_waive.py`'s
    generic waiver matcher keys on `(node, family, sub_target)`, never
    the pre-joined `RULE:SUBTARGET` string)."""
    return v.rule


def _sub_target_of(v: HostIsolationViolation) -> str | None:
    """`apply_waivers` extractor: HOST001/HOST002 are always sub-targeted
    (module docstring), so this is never `None` for a real finding."""
    return v.sub_target


def _manifests_by_node(model: KernelModel) -> dict[str, HostManifest]:
    """Every node with a declared `std.host` manifest, keyed by node id --
    the one join HOST001/HOST002 both build their user index from
    (charter: no duplication)."""
    manifests: dict[str, HostManifest] = {}
    for node in model.nodes:
        manifest = host_manifest_for(node)
        if manifest is not None:
            manifests[node.id] = manifest
    return manifests


def _nodes_by_user(
    nodes_by_id: dict[str, Node], manifests: dict[str, HostManifest]
) -> dict[str, list[str]]:
    """`runs_as` user -> the node ids declaring that user, in declaration
    order -- a service user may own more than one node's manifest (e.g. a
    unit plus a store it privately owns)."""
    by_user: dict[str, list[str]] = {}
    for node_id in nodes_by_id:
        manifest = manifests.get(node_id)
        if manifest is None or manifest.runs_as is None:
            continue
        by_user.setdefault(manifest.runs_as, []).append(node_id)
    return by_user


def _owns_by_user(
    user_nodes: list[str], manifests: dict[str, HostManifest]
) -> dict[str, HostOwns]:
    """Every `owns` path a user's node(s) declare, keyed by path (last
    declaration wins, matching `Node.attrs`'s own overwrite convention)."""
    owns: dict[str, HostOwns] = {}
    for node_id in user_nodes:
        for entry in manifests[node_id].owns:
            owns[entry.path] = entry
    return owns


def _listens_by_user(
    user_nodes: list[str], manifests: dict[str, HostManifest]
) -> set[int]:
    """Every port a user's node(s) declare `listens` on."""
    ports: set[int] = set()
    for node_id in user_nodes:
        ports.update(manifests[node_id].listens)
    return ports


def _mode_digits(mode: str) -> str | None:
    """Normalize a `HostOwns.mode` string to its owner/group/other digits
    (drop a leading `0`-padded special-bits digit when present -- a
    3-digit mode has none). Returns `None` for a mode too short/malformed
    to interpret rather than guessing (deny-by-default, charter law 2)."""
    digits = mode.strip()
    if len(digits) == 4:
        return digits[1:]
    if len(digits) == 3:
        return digits
    return None


def _mode_owner_writable(mode: str) -> bool:
    """Whether the OWNER permission digit of a POSIX octal `mode` string
    grants write (bit `0o2`) -- the derivation `_lateral_pair_violations`
    uses instead of new grammar (module docstring)."""
    digits = _mode_digits(mode)
    if digits is None:
        return False
    try:
        owner_digit = int(digits[0])
    except ValueError:
        return False
    return bool(owner_digit & 0o2)


def _mode_has_setuid(mode: str) -> bool:
    """Whether a 4-digit POSIX octal `mode` string's special-bits digit
    sets the setuid bit (`0o4`) -- `owns "PATH" "4755"` is the ONLY
    surface shape that can express this (module docstring: no new
    grammar needed, the field already carries it)."""
    stripped = mode.strip()
    if len(stripped) != 4:
        return False
    try:
        special_digit = int(stripped[0])
    except ValueError:
        return False
    return bool(special_digit & 0o4)


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
    path both users own where at least one owner mode is writable."""
    owns_a = _owns_by_user(nodes_a, manifests)
    owns_b = _owns_by_user(nodes_b, manifests)
    # frob:waive PERF004 reason="differs per pair, fresh work not a re-sort"
    shared_writable = sorted(
        path
        for path in (set(owns_a) & set(owns_b))
        if _mode_owner_writable(owns_a[path].mode)
        or _mode_owner_writable(owns_b[path].mode)
    )
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
    declared `Flow` already bridges them (the documented escape hatch)."""
    ports_a = _listens_by_user(nodes_a, manifests)
    ports_b = _listens_by_user(nodes_b, manifests)
    shared_ports = sorted(ports_a & ports_b)
    if not shared_ports or _declared_flow_between(model, nodes_a, nodes_b):
        return []
    return [
        HostIsolationViolation(
            rule="HOST001",
            sub_target=_SUB_CROSS_USER_SOCKET,
            user=user_a,
            peer=user_b,
            detail=f"users {user_a!r} and {user_b!r} both listen on port(s) "
            f"{shared_ports} with no declared Flow between their nodes -- "
            "an undeclared cross-user socket path",
        )
    ]


def _shared_group_violation(user_a: str, user_b: str) -> HostIsolationViolation:
    """HOST001 shared-group honest-gap finding -- always fires, since
    std.host carries no OS-group vocabulary to disprove it (frob:todo
    T-draft-7b5b5541)."""
    return HostIsolationViolation(
        rule="HOST001",
        sub_target=_SUB_SHARED_GROUP,
        user=user_a,
        peer=user_b,
        detail="std.host carries no OS-group vocabulary "
        "(frob:todo T-draft-7b5b5541) -- "
        f"whether {user_a!r} and {user_b!r} share a group cannot be "
        "structurally proved false; waive with a reason or await the "
        "group grammar",
    )


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
    path, cross-user socket unless a declared flow bridges them, and the
    always-fires shared-group honest gap (module docstring)."""
    violations: list[HostIsolationViolation] = []
    violations.extend(
        _shared_writable_path_violations(user_a, nodes_a, user_b, nodes_b, manifests)
    )
    violations.extend(
        _shared_socket_violations(
            model, user_a, nodes_a, user_b, nodes_b, manifests
        )
    )
    violations.append(_shared_group_violation(user_a, user_b))
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


# frob:doc docs/strata/host.md#movement-impossibility-proofs
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
    manifests = _manifests_by_node(model)
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
    between the two users' node lists (see `_movement_flows_for_pair`)."""
    owns_a = _owns_by_user(nodes_a, manifests)
    owns_b = _owns_by_user(nodes_b, manifests)
    shared_writable = sorted(
        path
        for path in (set(owns_a) & set(owns_b))
        if _mode_owner_writable(owns_a[path].mode)
        or _mode_owner_writable(owns_b[path].mode)
    )
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
    port (see `_movement_flows_for_pair`)."""
    ports_a = _listens_by_user(nodes_a, manifests)
    ports_b = _listens_by_user(nodes_b, manifests)
    if not (ports_a & ports_b):
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
    manifests = _manifests_by_node(model)
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


def _root_run_nodes(
    nodes_by_id: dict[str, Node], manifests: dict[str, HostManifest]
) -> list[str]:
    """Node ids that run as root: a declared `unit` with no `runs_as`
    (the surface has no way to declare "root" explicitly -- absence of a
    dedicated service user on a unit IS the root-run case, matching
    systemd's own default `User=root`)."""
    return sorted(
        node_id
        for node_id, manifest in manifests.items()
        if manifest.is_unit and manifest.runs_as is None
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


def _sudoers_violation(user: str) -> HostIsolationViolation:
    """HOST002 sudoers honest-gap finding -- always fires, since std.host
    carries no sudoers vocabulary to disprove it (frob:todo T-draft-7b5b5541)."""
    return HostIsolationViolation(
        rule="HOST002",
        sub_target=_SUB_SUDOERS,
        user=user,
        detail="std.host carries no sudoers vocabulary "
        "(frob:todo T-draft-7b5b5541) -- "
        f"whether {user!r} holds a sudoers grant cannot be structurally "
        "proved false; waive with a reason or await the grammar",
    )


def _root_unit_writable_violations(
    user: str, owns: dict[str, HostOwns], root_nodes: list[str], manifests
) -> list[HostIsolationViolation]:
    """HOST002 findings where `user` writably owns a path a root-run unit
    also owns (a plant-then-root-executes vector)."""
    violations: list[HostIsolationViolation] = []
    for root_id in root_nodes:
        for entry in manifests[root_id].owns:
            user_entry = owns.get(entry.path)
            if user_entry is not None and _mode_owner_writable(user_entry.mode):
                violations.append(
                    HostIsolationViolation(
                        rule="HOST002",
                        sub_target=_SUB_ROOT_UNIT_WRITABLE,
                        user=user,
                        detail=f"root-run unit {root_id!r} owns path {entry.path!r}, "
                        f"which user {user!r} also owns writably (mode "
                        f"{user_entry.mode!r}) -- a user compromise can plant "
                        "content a root-run unit later executes/reads",
                    )
                )
    return violations


def _higher_trust_write_violations(
    model: KernelModel,
    trust_by_node: dict[str, str],
    user: str,
    user_nodes: list[str],
    owns: dict[str, HostOwns],
    manifests: dict[str, HostManifest],
) -> list[HostIsolationViolation]:
    """HOST002 findings where `user` writably owns a path also owned by a
    strictly-higher-trust node (a corrupt-input-for-a-more-trusted-reader
    vector)."""
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
        for path in sorted(set(owns) & {o.path for o in peer_manifest.owns}):
            if _mode_owner_writable(owns[path].mode):
                violations.append(
                    HostIsolationViolation(
                        rule="HOST002",
                        sub_target=_SUB_HIGHER_TRUST_WRITE,
                        user=user,
                        detail=f"user {user!r} writably owns path {path!r} "
                        f"({owns[path].mode!r}) also owned by higher-trust node "
                        f"{node_id!r} ({node_trust}) -- a user compromise can "
                        "corrupt input a more-trusted node reads",
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
    trust lattice (module docstring)."""
    owns = _owns_by_user(user_nodes, manifests)
    violations: list[HostIsolationViolation] = []
    violations.extend(_setuid_violations(user, owns))
    violations.append(_sudoers_violation(user))
    violations.extend(
        _root_unit_writable_violations(user, owns, root_nodes, manifests)
    )
    violations.extend(
        _higher_trust_write_violations(
            model, trust_by_node, user, user_nodes, owns, manifests
        )
    )
    return violations


# frob:doc docs/strata/host.md#movement-impossibility-proofs
def evaluate_vertical_isolation(
    model: KernelModel,
) -> Result[tuple[HostIsolationViolation, ...], StrataError]:
    """HOST002: PER declared service user, prove no setuid path owned, no
    sudoers grant, no root-run unit whose owned paths this user can write
    to, and no write access to a path a higher-trust node also owns --
    every finding DERIVED from `HostManifest` plus the model's existing
    trust lattice (module docstring), never hand-written per user."""
    nodes_by_id = {n.id: n for n in model.nodes}
    manifests = _manifests_by_node(model)
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


def _host_isolation_target_of(
    by_user: dict[str, list[str]], v: HostIsolationViolation
) -> str | None:
    """A HOST001/HOST002 finding waives against the node(s) declaring
    the implicated user -- the FIRST node id `_nodes_by_user` recorded
    for that `runs_as` (a `waive` clause on ANY of a user's nodes
    excuses that user's findings, matching `owns`'s "a user may
    declare more than one node" shape).

    A HOST001 PAIR finding is attributed to `v.user` only (the
    alphabetically-earlier user of the pair, per `evaluate_lateral_
    isolation`'s sorted iteration) -- ONE `waive` clause on that
    user's node discharges the pair finding; a matching `waive`
    clause also placed on the peer (`v.peer`) user's node correctly
    reports STALE (`_waive.py`'s drift-lock), since no HOST001
    finding is ever generated attributed to the peer for the same
    pair. This is intentional, not a gap: a pair has exactly one
    canonical owner for waiver purposes, chosen deterministically, so
    a caller never has two different valid places to write the same
    waiver (which would itself be a "which one is authoritative"
    ambiguity, charter: no duplication)."""
    candidates = by_user.get(v.user, ())
    return candidates[0] if candidates else None


# Each call's `in_scope` names ONLY the rule family it is checking --
# not the union `HOST_MULTI_INSTANCE_WAIVER_FAMILIES` -- exactly the
# `_waive.py::apply_waivers` "each caller passes an `in_scope`
# predicate naming exactly the rule ids it owns" contract
# (`_audit.py`/`_selfconform.py`'s SYS-only vs THREAT/LINT-only split
# is the same precedent): a `HOST002:sudoers` waiver considered by
# THIS call's HOST001 pass would otherwise be reported STALE here too
# (it fires nothing HOST001-shaped), double-counting one waiver as
# two different findings across the two returned `WaiverApplication`s.
def _apply_host_waivers(
    model: KernelModel,
    lateral_violations: tuple[HostIsolationViolation, ...],
    vertical_violations: tuple[HostIsolationViolation, ...],
    by_user: dict[str, list[str]],
) -> tuple[
    WaiverApplication[HostIsolationViolation], WaiverApplication[HostIsolationViolation]
]:
    """Run HOST001 and HOST002 findings each through `apply_waivers`,
    scoped to their own rule family only (see `evaluate_host_isolation_
    waived` for why `in_scope` must not use the union of both families)."""

    def target_of(v: HostIsolationViolation) -> str | None:
        return _host_isolation_target_of(by_user, v)

    host001 = apply_waivers(
        model,
        lateral_violations,
        rule_of=_rule_of,
        target_of=target_of,
        sub_target_of=_sub_target_of,
        in_scope=lambda family: family == "HOST001",
    )
    host002 = apply_waivers(
        model,
        vertical_violations,
        rule_of=_rule_of,
        target_of=target_of,
        sub_target_of=_sub_target_of,
        in_scope=lambda family: family == "HOST002",
    )
    return host001, host002


# frob:doc docs/strata/host.md#movement-impossibility-proofs
def evaluate_host_isolation_waived(
    model: KernelModel,
) -> Result[
    tuple[
        WaiverApplication[HostIsolationViolation],
        WaiverApplication[HostIsolationViolation],
    ],
    StrataError,
]:
    """HOST001 + HOST002, each run through the SAME `_waive.py::
    apply_waivers` T-0174 waiver channel every other multi-instance-per-
    node rule family uses -- returns `(host001_application,
    host002_application)`. A `waive "HOST001:shared-group" reason="..."`
    (or `HOST002:sudoers`) clause on the node that OWNS the user (any
    node declaring that `runs_as`) suppresses that user's/pair's finding
    for that sub-target only, per `RULE:SUBTARGET` discipline (module
    docstring's `HOST_MULTI_INSTANCE_WAIVER_FAMILIES`)."""
    lateral = evaluate_lateral_isolation(model)
    if lateral.is_err:
        return Err(lateral.danger_err)
    vertical = evaluate_vertical_isolation(model)
    if vertical.is_err:
        return Err(vertical.danger_err)

    by_user = _nodes_by_user(
        {n.id: n for n in model.nodes}, _manifests_by_node(model)
    )
    host001, host002 = _apply_host_waivers(
        model, lateral.danger_ok, vertical.danger_ok, by_user
    )
    return Ok((host001, host002))


# frob:doc docs/guides/extending/threat-catalog.md#threat-catalog
# The compromised-service-owner class (module docstring): CWE-522
# (insufficiently protected credentials -- a compromised owner's writable
# paths may hold secrets), CWE-269 (improper privilege management -- the
# HOST002 vertical class), CWE-284 (improper access control -- the
# HOST001 lateral class). Kept in its OWN catalog/view, never appended to
# `_threat.py::CWE_CATALOG`/`VIEWS` -- the same separate-view precedent
# `QUALITY_CATALOG`/`CWE_TOP_25_CATALOG` set (module docstring).
COMPROMISED_OWNER_CATALOG: tuple[WeaknessEntry, ...] = (
    WeaknessEntry(
        id="CWE-284",
        title="Improper Access Control",
        cite="https://cwe.mitre.org/data/definitions/284.html",
        family="security",
        capability_kind=None,  # fired by HOST001, not a `may` capability join
        mitigation="host_isolation",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-269",
        title="Improper Privilege Management",
        cite="https://cwe.mitre.org/data/definitions/269.html",
        family="security",
        capability_kind=None,  # fired by HOST002, not a `may` capability join
        mitigation="host_isolation",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-522",
        title="Insufficiently Protected Credentials",
        cite="https://cwe.mitre.org/data/definitions/522.html",
        family="security",
        capability_kind=None,  # a compromised owner's writable-path blast radius
        # may include resting credentials; no `may` capability names this --
        # HOST001's shared-writable-path finding is the structural signal.
        mitigation="host_isolation",
        rung=Rung.L4,
    ),
)

#: No `OutOfScopeEntry` rows: the compromised-owner class names exactly
#: three ids, all cataloged above -- an empty tuple is the honest
#: "nothing excluded" answer for THREAT001-shaped completeness checks
#: run against this view (mirrors `CWE_CATALOG`'s own empty `out_of_scope`
#: default).
# frob:doc docs/strata/host.md#compromised-service-owner-threat-catalog
COMPROMISED_OWNER_OUT_OF_SCOPE: tuple[OutOfScopeEntry, ...] = ()

#: Baseline view for the compromised-service-owner class (module
#: docstring's separate-view precedent) -- a caller checking this class
#: passes `view="compromised-owner-baseline"` plus `COMPROMISED_OWNER_
#: CATALOG` to `_threat.py::check_catalog_completeness`'s `views`
#: override, exactly `CWE_TOP_25_VIEWS`'s convention.
# frob:doc docs/strata/host.md#compromised-service-owner-threat-catalog
COMPROMISED_OWNER_VIEWS: dict[str, frozenset[str]] = {
    "compromised-owner-baseline": frozenset(
        entry.id for entry in COMPROMISED_OWNER_CATALOG
    ),
}


__all__ = [
    "COMPROMISED_OWNER_CATALOG",
    "COMPROMISED_OWNER_OUT_OF_SCOPE",
    "COMPROMISED_OWNER_VIEWS",
    "HOST_MULTI_INSTANCE_WAIVER_FAMILIES",
    "HostIsolationViolation",
    "evaluate_host_isolation_waived",
    "evaluate_lateral_isolation",
    "evaluate_vertical_isolation",
]
