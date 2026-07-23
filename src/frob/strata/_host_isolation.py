"""HOST001/HOST002: movement-impossibility proofs over `std.host`
manifests (T-0256, docs/strata/host.md#movement-impossibility-proofs).

T-0254 child 2, the SECURITY CORE of the deploy epic: the red-team
scenario ("assume one service user's process is compromised -- what can
it reach?") as a first-class, DEMANDED obligation the moment a model
declares 2+ `runs_as` service users, not an optional afterthought.

HOST001 (lateral movement) fires per DISTINCT service-user PAIR: prove
no shared writable filesystem path, no shared listening port reachable
across users without a declared `Flow` between their nodes, and (T-0272)
no shared OS group. HOST002 (vertical movement)
fires PER service user: no setuid path owned, no sudoers grant, no
root-run unit whose owned paths are writable by a lower-trust user, and
no write access to a path a higher-trust node also owns.

Every sub-target is DERIVED from `HostManifest` intersection
(`_host.py::host_manifest_for`) -- there is no hand-written per-pair or
per-user table to fall out of sync with the model, mirroring
`_threat.py::_entries_by_capability_kind`'s "one join, every caller
reuses it" discipline.

## The (former) honest gap: two sub-targets now derived from HostManifest

`std.host` (T-0255) originally carried NO OS-group and NO sudoers-grant
vocabulary, so `shared group` and `sudoers` UNCONDITIONALLY fired for
every pair/user a HOST001/HOST002 obligation applied to (deny-by-default,
charter law 2), with a detail naming the missing grammar, until an
operator wrote an explicit `waive "HOST001:shared-group" reason="..."` /
`waive "HOST002:sudoers" reason="..."` clause. T-0272 added `group
"NAME"`+ and `sudoers "RULE"`+ to `std.host` (`strata-core/src/parse.rs`,
`_host.py::HostManifest.group`/`.sudoers`), so both sub-targets now
derive REAL findings from `HostManifest` intersection, the same
DERIVED-not-hand-written discipline every other sub-target in this
module follows: HOST001's shared-group fires when two service users'
`group` tuples intersect; HOST002's sudoers fires when a user's
`sudoers` tuple is non-empty. A user who declares no `group`/`sudoers`
at all now correctly proves nothing to report, exactly like `owns`/
`listens`'s absence -- this is the module's fired-until-declared
discipline (charter law 2) applied consistently, not a relaxation of it.

`setuid` (HOST002) IS derivable without new grammar: `owns "PATH"
"MODE"` already carries a full POSIX octal mode string
(`_host.py::HostOwns.mode`), and a 4-digit mode's leading digit encodes
the setuid/setgid/sticky bits (`_mode_owner_writable`/`_mode_has_setuid`
below) -- no grammar change needed, just reading a field that was
already there.

## Windows wiring (T-0606)

T-0261 shipped the Windows `std.host` surface (`service_account`/`acl`/
`pipe`, `docs/strata/host.md#windows-surface-grammar`) but explicitly
deferred wiring it into HOST001/HOST002 to a follow-up ticket (its Done
report and `docs/strata/host.md#scope-boundary-what-is-not-built-here`) --
until T-0606, a windows-only node declaring solely `service_account`/
`acl`/`pipe` produced NO HOST001/HOST002 findings at all, not because it
was proven isolated but because nothing read its windows-shaped facts.
T-0606 closes that gap by generalizing every identity/path/listening-
surface join this module performs to read EITHER platform's fields,
never branching the rule logic itself on `HostManifest.platform`:

- **Service-user identity** (`_identity_of`): a manifest's `runs_as`
  (linux) or `service_account` (windows) -- whichever is set -- is the
  ONE key `_nodes_by_user` groups nodes by. A manifest declaring neither
  contributes no identity, exactly like the pre-T-0606 `runs_as is None`
  skip.
- **Owned paths** (`_PathClaim`, `_owned_paths_by_user`): linux `owns`
  (`HostOwns`, POSIX MODE) and windows `acl` (`HostAcl`, NTFS DACL RULE)
  are merged into one `path -> _PathClaim(write_capable, descriptor)`
  index per user -- `write_capable` reads `_mode_owner_writable` for an
  `owns` entry or `_acl_grants_write` (this module's RULE-shaped analog,
  "not `:deny`'d and RIGHTS in `{Write,Modify,FullControl}`") for an
  `acl` entry. Every HOST001/HOST002 sub-target that intersects owned
  paths (shared-writable-path, root-unit-writable-by-user,
  write-to-higher-trust-path) reads this merged index instead of
  `HostManifest.owns` directly, so a linux/windows pair (or a
  windows/windows pair) proves the identical shape of finding a
  linux/linux pair does. `setuid` stays linux-only by construction, not
  by a platform branch: `_mode_has_setuid` only ever matches a 4-digit
  POSIX MODE string, so an `acl` RULE descriptor (which never parses as
  four decimal digits) structurally cannot trip it -- there is no NTFS
  ACL bit that maps onto POSIX setuid, so no windows finding is invented
  in its place (deny-by-default names the honest absence of an
  equivalent, it does not fabricate one).
- **Listening surface** (`_listening_surface_by_user`): linux `listens`
  (TCP/UDP PORT) and windows `pipe` (named pipe) are merged into one
  labeled string set per user (`"port:9000"` / `"pipe:api-ipc"`) so
  HOST001's cross-user-socket sub-target fires on a shared PORT, a
  shared PIPE, or one of each declared on either side -- the labels keep
  a port number and a same-named pipe from colliding. `host_movement_
  flows` mirrors the same union so `build_compromised_user_scenario`'s
  blast-radius claims stay non-vacuous over a windows pipe exactly like
  they already were over a linux port (module docstring above,
  T-0256's REJECT-round fix).
- **Root-run identity** (`_root_run_nodes`): a linux `unit` with no
  `runs_as` (systemd's own default `User=root`) OR a windows `service`
  with no `service_account` (SCM's own default LocalSystem) is treated
  as the root-equivalent identity HOST002's root-unit-writable-by-user
  sub-target guards against -- the identical "no way to declare root
  explicitly, absence of a dedicated identity on a unit/service IS the
  privileged case" reasoning, generalized to both platforms.

`group`/`sudoers` (T-0272) needed NO change here: neither field was ever
platform-gated in `HostManifest` -- a windows node declaring `group`/
`sudoers` already derived real HOST001/HOST002 findings before T-0606;
only the identity/path/listening-surface joins were linux-only.

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
#: bare `waive "SYS100"` is (`_waive.py::_validate_waiver_fields`).
# frob:doc docs/strata/host.md#waiver-discipline
HOST_MULTI_INSTANCE_WAIVER_FAMILIES: frozenset[str] = frozenset({"HOST001", "HOST002"})

#: HOST002 sub-target for the sudoers-grant check: fires when a service
#: user's `HostManifest.sudoers` (T-0272) is non-empty (module docstring).
_SUB_SUDOERS = "sudoers"

#: HOST001 sub-target for the shared-OS-group check: fires when two
#: service users' `HostManifest.group` (T-0272) tuples intersect (module
#: docstring).
_SUB_SHARED_GROUP = "shared-group"

_SUB_SETUID = "setuid"
_SUB_SHARED_WRITABLE_PATH = "shared-writable-path"
_SUB_CROSS_USER_SOCKET = "cross-user-socket"
_SUB_ROOT_UNIT_WRITABLE = "root-unit-writable-by-user"
_SUB_HIGHER_TRUST_WRITE = "write-to-higher-trust-path"

#: Windows `acl` RIGHTS values (lowercased) that grant write-capable
#: access, the windows analog of `_mode_owner_writable`'s POSIX write bit
#: (module docstring's "Windows wiring" section) -- mirrors `_contention.
#: py::_ACL_WRITE_RIGHTS`'s vocabulary; kept local (not imported) since
#: this module's write-capability check is deliberately OWNER/PRINCIPAL-
#: scoped like `_mode_owner_writable`, a narrower question than
#: `_contention.py`'s "is ANY digit/rule write-capable" contention join.
_ACL_WRITE_RIGHTS = {"write", "modify", "fullcontrol"}

#: `"port:<n>"` / `"pipe:<name>"` label prefixes `_listening_surface_by_
#: user` uses to keep a linux PORT number and a same-named windows PIPE
#: from colliding in the merged listening-surface set (module docstring).
_PORT_LABEL_PREFIX = "port:"
_PIPE_LABEL_PREFIX = "pipe:"


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


# frob:doc docs/strata/host.md#windows-wiring-t-0606
class _PathClaim(BaseModel):
    """One owned filesystem/registry path, unified across linux `owns`
    (`HostOwns`, POSIX MODE) and windows `acl` (`HostAcl`, NTFS DACL
    RULE) -- module docstring's "Owned paths" section. `descriptor` keeps
    the original mode/rule string for finding detail messages;
    `write_capable` is the platform-specific write-grant question
    already reduced to one bool so every path-intersecting sub-target
    reads it uniformly."""

    model_config = ConfigDict(frozen=True)

    path: str
    write_capable: bool
    descriptor: str


def _identity_of(manifest: HostManifest) -> str | None:
    """The one service-user identity a `HostManifest` declares: `runs_as`
    (linux) or `service_account` (windows), whichever is set -- the join
    key `_nodes_by_user` groups nodes by (module docstring's "Service-user
    identity" section). `None` when neither is declared."""
    return (
        manifest.runs_as if manifest.runs_as is not None else manifest.service_account
    )


def _acl_grants_write(rule: str) -> bool:
    """Whether a windows `acl` RULE grants write-capable access -- the
    windows analog of `_mode_owner_writable` (module docstring): RIGHTS
    is one of `_ACL_WRITE_RIGHTS` and the rule carries no `:deny` flag.
    `HostAcl.rule` is already validated `PRINCIPAL:RIGHTS[:deny]
    [:no_inherit]` shape (`_host.py::HostAcl._validate_rule`), so a plain
    split is safe here."""
    _principal, _, rest = rule.partition(":")
    flags = rest.split(":")
    rights = flags[0].strip().lower() if flags else ""
    is_deny = "deny" in flags[1:]
    return (not is_deny) and rights in _ACL_WRITE_RIGHTS


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
    """Service-user identity (`_identity_of`: `runs_as` or `service_
    account`, module docstring's "Windows wiring" section) -> the node ids
    declaring that identity, in declaration order -- a service user may
    own more than one node's manifest (e.g. a unit/service plus a store
    it privately owns)."""
    by_user: dict[str, list[str]] = {}
    for node_id in nodes_by_id:
        manifest = manifests.get(node_id)
        if manifest is None:
            continue
        identity = _identity_of(manifest)
        if identity is None:
            continue
        by_user.setdefault(identity, []).append(node_id)
    return by_user


def _owns_by_user(
    user_nodes: list[str], manifests: dict[str, HostManifest]
) -> dict[str, HostOwns]:
    """Every `owns` path a user's node(s) declare, keyed by path (last
    declaration wins, matching `Node.attrs`'s own overwrite convention).
    LINUX-ONLY (`HostOwns`) -- `_setuid_violations` needs the raw
    `HostOwns` shape (`_mode_has_setuid` has no windows analog, module
    docstring); every OTHER sub-target reads the platform-merged
    `_owned_paths_by_user` instead."""
    owns: dict[str, HostOwns] = {}
    for node_id in user_nodes:
        for entry in manifests[node_id].owns:
            owns[entry.path] = entry
    return owns


def _owned_paths_by_user(
    user_nodes: list[str], manifests: dict[str, HostManifest]
) -> dict[str, _PathClaim]:
    """Every path a user's node(s) declare ownership of, merged across
    linux `owns` and windows `acl` (module docstring's "Owned paths"
    section) -- keyed by path, last declaration wins across BOTH
    vocabularies in node/field-declaration order, matching `_owns_by_
    user`'s own overwrite convention."""
    claims: dict[str, _PathClaim] = {}
    for node_id in user_nodes:
        manifest = manifests[node_id]
        for entry in manifest.owns:
            claims[entry.path] = _PathClaim(
                path=entry.path,
                write_capable=_mode_owner_writable(entry.mode),
                descriptor=entry.mode,
            )
        for acl_entry in manifest.acl:
            claims[acl_entry.path] = _PathClaim(
                path=acl_entry.path,
                write_capable=_acl_grants_write(acl_entry.rule),
                descriptor=acl_entry.rule,
            )
    return claims


def _listens_by_user(
    user_nodes: list[str], manifests: dict[str, HostManifest]
) -> set[int]:
    """Every port a user's node(s) declare `listens` on."""
    ports: set[int] = set()
    for node_id in user_nodes:
        ports.update(manifests[node_id].listens)
    return ports


def _listening_surface_by_user(
    user_nodes: list[str], manifests: dict[str, HostManifest]
) -> set[str]:
    """Every labeled listening-surface atom a user's node(s) declare,
    merged across linux `listens` PORTs and windows `pipe`s (module
    docstring's "Listening surface" section) -- `"port:9000"` /
    `"pipe:api-ipc"` labels keep a port number and a same-named pipe from
    colliding when unioned into one set."""
    surface: set[str] = set()
    for node_id in user_nodes:
        manifest = manifests[node_id]
        surface.update(f"{_PORT_LABEL_PREFIX}{port}" for port in manifest.listens)
        surface.update(f"{_PIPE_LABEL_PREFIX}{pipe}" for pipe in manifest.pipes)
    return surface


def _groups_by_user(
    user_nodes: list[str], manifests: dict[str, HostManifest]
) -> set[str]:
    """Every OS group a user's node(s) declare `group` membership in
    (T-0272) -- the union HOST001's shared-group sub-target intersects
    across a pair, same shape as `_listens_by_user`."""
    groups: set[str] = set()
    for node_id in user_nodes:
        groups.update(manifests[node_id].group)
    return groups


def _sudoers_by_user(
    user_nodes: list[str], manifests: dict[str, HostManifest]
) -> tuple[str, ...]:
    """Every sudoers grant a user's node(s) declare (T-0272), in
    declaration order across the user's nodes -- HOST002's sudoers
    sub-target fires per grant, same "one finding per declared fact"
    shape `_setuid_violations` uses for `owns`."""
    sudoers: list[str] = []
    for node_id in user_nodes:
        sudoers.extend(manifests[node_id].sudoers)
    return tuple(sudoers)


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
    path both users own (linux `owns` or windows `acl`, module docstring)
    where at least one side's claim is write-capable."""
    owns_a = _owned_paths_by_user(nodes_a, manifests)
    owns_b = _owned_paths_by_user(nodes_b, manifests)
    # frob:waive PERF004 reason="differs per pair, fresh work not a re-sort"
    shared_writable = sorted(
        path
        for path in (set(owns_a) & set(owns_b))
        if owns_a[path].write_capable or owns_b[path].write_capable
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
    (linux `owns` or windows `acl`, module docstring) between the two
    users' node lists (see `_movement_flows_for_pair`)."""
    owns_a = _owned_paths_by_user(nodes_a, manifests)
    owns_b = _owned_paths_by_user(nodes_b, manifests)
    shared_writable = sorted(
        path
        for path in (set(owns_a) & set(owns_b))
        if owns_a[path].write_capable or owns_b[path].write_capable
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


# frob:doc docs/strata/host.md#movement-impossibility-proofs
# frob:invariant INV-033
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

    by_user = _nodes_by_user({n.id: n for n in model.nodes}, _manifests_by_node(model))
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
