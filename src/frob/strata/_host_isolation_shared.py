"""HOST001/HOST002 shared model and utilities (T-2844 split of
`_host_isolation.py`, docs/strata/host.md#movement-impossibility-proofs):
`HostIsolationViolation`/`_PathClaim` plus every identity/ACL/mode-parsing
join more than one of the three independent checks
(`_host_isolation_lateral.py`'s HOST001, `_host_isolation_vertical.py`'s
HOST002, `_host_isolation_movement.py`'s `host_movement_flows`) reads.

Kept as its own leaf module, with NO import of any `_host_isolation_*`
sibling, so each check module can import shared state without inverting
the split's import direction back into a cycle -- the identical
`_selfconform_models.py` precedent (T-2729) for the same reason, stated
there verbatim: "that would invert the split's import direction back
into a cycle." `_host_isolation.py` (the facade) imports from here too,
for its own waiver plumbing and to re-export `HostIsolationViolation`/
`HOST_MULTI_INSTANCE_WAIVER_FAMILIES`/`_join_acl_entries` so every
existing external import (`frob.strata.__init__`, `_audit.py`, tests)
keeps working unchanged."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._host import HostAcl, HostManifest, HostOwns
from ._models import Node

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

#: T-0825: coarse bit-coverage ranking over `_ACL_WRITE_RIGHTS`, real NTFS
#: RIGHTS bit-sets nest (`write` bits subset-of `modify` bits subset-of
#: `fullcontrol` bits, which ALSO carries WRITE_DAC/WRITE_OWNER -- bits no
#: `write`/`modify` RIGHTS value grants at all). Used only by `_join_acl_
#: entries`'s WRITE_DAC-indirection corner below; every other
#: `_ACL_WRITE_RIGHTS` membership check in this module stays a flat set
#: test, unaffected by this ranking.
_RIGHTS_RANK: dict[str, int] = {"write": 0, "modify": 1, "fullcontrol": 2}

#: T-0825: the ONE `_ACL_WRITE_RIGHTS` level that grants WRITE_DAC/
#: WRITE_OWNER in real NTFS -- `write`/`modify` grant neither. A deny at
#: any level BELOW this one does not touch those bits at all, so it
#: cannot cancel a `fullcontrol` allow's WRITE_DAC grant no matter how
#: "broad" the deny otherwise looks in this coarse vocabulary.
_DAC_GRANTING_RIGHTS = "fullcontrol"

#: `"port:<n>"` / `"pipe:<name>"` label prefixes `_listening_surface_by_
#: user` uses to keep a linux PORT number and a same-named windows PIPE
#: from colliding in the merged listening-surface set (module docstring).
_PORT_LABEL_PREFIX = "port:"
_PIPE_LABEL_PREFIX = "pipe:"


# frob:waive AFFECT001 reason="T-2844: LARGE001 split of _host_isolation.py by \
# lateral/vertical/movement seam -- this symbol only moved to a sibling module \
# verbatim (same name, same body/signature), no behavior change, so the \
# affects()-closure doc it names needs no update"
# frob:doc docs/strata/host.md#movement-impossibility-proofs
# frob:tests \
# tests/unit/strata/test_host_isolation.py::TestLateralIsolation.test_skips_below_two_u\
# sers kind="unit"
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


# frob:waive DUP001 reason="T-2844: pre-existing verbatim body (unchanged by this \
# ticket, only relocated by the LARGE001 split) -- \
# _contention.py::_acl_rule_write_capable already existed independently before this \
# split and this pair was never flagged before because the ticket-scoped DUP gate only \
# surfaces pairs where a touched line is on one side; this duplicate is a real, \
# already-accepted pattern (two modules each doing their own narrow ACL-rule parse), \
# not new duplication introduced here"
def _acl_ace_of(rule: str) -> tuple[str, bool, str | None]:
    """Decompose a validated windows `acl` RULE into its (PRINCIPAL,
    is_deny, rights) triple -- the one parse `_join_acl_entries`
    (T-0792 multi-ACE deny-overrides-allow join, module docstring's
    "Owned paths" section) builds on, so the RULE grammar is only ever
    split in one place (charter: no duplication). `HostAcl.rule` is
    already validated `PRINCIPAL:RIGHTS[:deny][:no_inherit]` shape
    (`_host.py::HostAcl._validate_rule`), so a plain split is safe
    here. `rights` is the lowercased RIGHTS token when it is one of
    `_ACL_WRITE_RIGHTS` (T-0825: callers need the LEVEL, not just
    membership, to reason about the WRITE_DAC-indirection corner), `None`
    otherwise (a non-write-capable RIGHTS value, e.g. `Read`)."""
    principal, _, rest = rule.partition(":")
    flags = rest.split(":")
    rights = flags[0].strip().lower() if flags else ""
    is_deny = "deny" in flags[1:]
    return principal, is_deny, rights if rights in _ACL_WRITE_RIGHTS else None


def _net_acl_levels_by_principal(
    entries: list[HostAcl],
) -> tuple[dict[str, str], dict[str, str]]:
    """Split off `_join_acl_entries`'s first pass (ARCH001 line-count
    split, T-0825): the broadest allow level and broadest deny level each
    principal declares among `entries`' write-capable ACEs, keyed by
    principal -- the raw input `_join_acl_entries`'s WRITE_DAC-indirection
    reasoning nets out."""
    net_allow: dict[str, str] = {}
    net_deny: dict[str, str] = {}
    for entry in entries:
        principal, is_deny, rights = _acl_ace_of(entry.rule)
        if rights is None:
            continue
        target = net_deny if is_deny else net_allow
        current = target.get(principal)
        if current is None or _RIGHTS_RANK[rights] > _RIGHTS_RANK[current]:
            target[principal] = rights
    return net_allow, net_deny


def _join_acl_entries(entries: list[HostAcl]) -> bool:
    """T-0792: real NTFS deny-overrides-allow join across EVERY ACE
    declared for one path, replacing the last-declaration-wins collapse
    that silently discarded all but the final entry (`_owned_paths_by_
    user`'s prior overwrite-by-path-key loop, module docstring's T-0606
    "Owned paths" section -- the reviewer finding this ticket closes).

    NTFS evaluates access per accessing PRINCIPAL: an explicit `:deny` ACE
    always wins over an explicit allow ACE for the SAME principal, no
    matter which was declared first (`_acl_ace_of`'s is_deny flag nets out
    within a principal's own ACEs before anything else is asked). A deny
    for one principal never reaches across to cancel a DIFFERENT
    principal's allow -- so the path is write-capable overall if ANY
    principal's net verdict is "allow", the join's final OR-reduction.
    This is the fix's soundness direction: the prior collapse could pick
    whichever ACE happened to land last in iteration order and silently
    lose an entirely different principal's real write grant, under-
    reporting a movement violation the model should have caught.

    T-0825 WRITE_DAC-indirection corner (T-0792 reviewer finding, the one
    corner this join used to understate): NTFS RIGHTS bit-sets nest
    (`write` subset `modify` subset `fullcontrol`), and ONLY `fullcontrol`
    carries WRITE_DAC/WRITE_OWNER -- bits `write`/`modify` never grant at
    any level. A same-principal narrow deny (e.g. `Modify`) does cancel a
    broad `FullControl` allow's plain content-write bit (every
    `_ACL_WRITE_RIGHTS` level, including `modify`, covers that bit, so any
    deny among them removes it) -- but it does NOT touch the WRITE_DAC/
    WRITE_OWNER bits, which only an explicit `fullcontrol`-level deny
    reaches. Left standing, WRITE_DAC lets the "denied" principal rewrite
    the path's own DACL and grant themselves full access back -- so the
    join still counts them as write-capable overall (via that indirection)
    UNLESS the deny is itself `fullcontrol`-level (a real full deny that
    reaches WRITE_DAC too). A narrower allow (`write`/`modify`) never
    grants WRITE_DAC in the first place, so this indirection path never
    applies to it -- any deny at all still fully cancels it, unchanged
    from before this fix."""
    net_allow, net_deny = _net_acl_levels_by_principal(entries)
    for principal, allow_level in net_allow.items():
        deny_level = net_deny.get(principal)
        if deny_level is None:
            return True  # unopposed allow
        if allow_level == _DAC_GRANTING_RIGHTS and deny_level != _DAC_GRANTING_RIGHTS:
            # T-0825: the deny is narrower than fullcontrol, so it never
            # reaches WRITE_DAC/WRITE_OWNER -- the principal can rewrite
            # the DACL and regain full write, still counted write-capable.
            _log.debug(
                "T-0825 WRITE_DAC indirection: principal=%s allow=fullcontrol "
                "deny=%s does not reach WRITE_DAC/WRITE_OWNER -- still "
                "write-capable via DACL rewrite",
                principal,
                deny_level,
            )
            return True
        # deny_level covers everything allow_level grants (both nest
        # within write/modify/fullcontrol's shared "plain content-write"
        # bit, and here deny reaches whatever DAC bits allow grants too)
        # -- fully cancelled for this principal.
    return False


def _rule_of(v: HostIsolationViolation) -> str:
    """`apply_waivers` extractor: the bare rule family (`_waive.py`'s
    generic waiver matcher keys on `(node, family, sub_target)`, never
    the pre-joined `RULE:SUBTARGET` string)."""
    return v.rule


def _sub_target_of(v: HostIsolationViolation) -> str | None:
    """`apply_waivers` extractor: HOST001/HOST002 are always sub-targeted
    (module docstring), so this is never `None` for a real finding."""
    return v.sub_target


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
    section) -- keyed by path. `owns` stays last-declaration-wins (a POSIX
    path has exactly one MODE, matching `_owns_by_user`'s own overwrite
    convention). `acl` is DIFFERENT: NTFS is multi-ACE by design, so every
    ACE declared for a path (across all of this user's nodes) is
    accumulated and joined via `_join_acl_entries`'s real deny-overrides-
    allow semantics (T-0792) instead of the path's dict entry being
    overwritten ACE by ACE -- the T-0606 reviewer finding this ticket
    closes: a last-wins overwrite could silently drop an earlier ACE's
    real write grant to a different principal, under-reporting a movement
    violation. Cross-vocabulary precedence: a path is never claimed by
    both `owns` and `acl` in a well-formed manifest, but if it were, the
    `acl` loop runs SECOND and its `_join_acl_entries` result applies
    after (overwrites) whatever `owns` wrote for that same path key."""
    claims: dict[str, _PathClaim] = {}
    acl_entries_by_path: dict[str, list[HostAcl]] = {}
    for node_id in user_nodes:
        manifest = manifests[node_id]
        for entry in manifest.owns:
            claims[entry.path] = _PathClaim(
                path=entry.path,
                write_capable=_mode_owner_writable(entry.mode),
                descriptor=entry.mode,
            )
        for acl_entry in manifest.acl:
            acl_entries_by_path.setdefault(acl_entry.path, []).append(acl_entry)
    for path, entries in acl_entries_by_path.items():
        claims[path] = _PathClaim(
            path=path,
            write_capable=_join_acl_entries(entries),
            descriptor="; ".join(entry.rule for entry in entries),
        )
    return claims


def _shared_writable_paths(
    nodes_a: list[str], nodes_b: list[str], manifests: dict[str, HostManifest]
) -> list[str]:
    """Every path BOTH users own (linux `owns` or windows `acl`) where at
    least one side's claim is write-capable, sorted for a deterministic
    finding order (T-2844: extracted so `_host_isolation_lateral.py`'s
    HOST001 shared-writable-path finding and `_host_isolation_movement.
    py`'s synthetic-Flow materialization -- the SAME sharing relation,
    read for two different purposes -- share ONE join instead of two
    copies drifting apart)."""
    owns_a = _owned_paths_by_user(nodes_a, manifests)
    owns_b = _owned_paths_by_user(nodes_b, manifests)
    # frob:waive PERF004 reason="differs per pair, fresh work not a re-sort"
    return sorted(
        path
        for path in (set(owns_a) & set(owns_b))
        if owns_a[path].write_capable or owns_b[path].write_capable
    )


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
    across a pair, same shape as `_listening_surface_by_user`."""
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


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to _mode_digits, a module-local \
# str-normalizing helper the resolver cannot see through; the one real raise path \
# (int() on a malformed digit) is caught below"
# frob:waive EXHAUST002 reason="T-1062: same resolver artifact as EXHAUST001 above"
def _mode_owner_writable(mode: str) -> bool:
    """Whether the OWNER permission digit of a POSIX octal `mode` string
    grants write (bit `0o2`) -- the derivation `_lateral_pair_violations`
    uses instead of new grammar (module docstring)."""
    digits = _mode_digits(mode)
    if digits is None:
        return False
    try:
        owner_digit = int(digits[0])
    except (IndexError, TypeError, ValueError):
        return False
    return bool(owner_digit & 0o2)


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to str.strip/len, plain str \
# methods the resolver cannot statically bound; the one real raise path (int() on a \
# malformed digit) is caught below"
# frob:waive EXHAUST002 reason="T-1062: same resolver artifact as EXHAUST001 above"
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
    except (TypeError, ValueError):
        return False
    return bool(special_digit & 0o4)
