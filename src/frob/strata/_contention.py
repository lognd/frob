"""SYS2xx resource-contention family: two nodes competing for the SAME
OS-layer resource (T-0699, docs/strata/host.md for the underlying
`std.host` grammar T-0261/T-0272 already elaborate).

This is the FIRST HALF of the T-0331 systems-checks epic's "Data/
consistency" and reliability catalog line "SPOF/shared-resource"
concerns, scoped deliberately narrow: NO grammar change. Every rule here
reads facts `_host.py::host_manifest_for` and `KernelModel.flows` already
expose today -- `listens` (a bound port), `owns`/`acl` (a filesystem
path claim, POSIX/Windows respectively), `pipes` (a named pipe), and
Flow edges into a `store` node. Four rule ids, SYS200-SYS203:

  - SYS200 duplicate port: two distinct nodes both declare the same
    `listens` PORT. A hard conflict -- two processes cannot bind the
    same TCP/UDP port on the same host, regardless of platform.
  - SYS201 overlapping path claim: two distinct nodes' `owns` (linux)
    or `acl` (windows) PATH atoms overlap by directory-segment prefix
    (e.g. `/var/lib/api` and `/var/lib/api/data`, or the reverse) --
    contention over the same filesystem subtree. `write_capable` is set
    when either side's mode/rule expresses a write-capable grant (a
    POSIX `owns` MODE with any write bit set, or an ACL RULE whose
    RIGHTS is `Write`/`Modify`/`FullControl` and not `:deny`'d) --
    ticket's "severity by whether either grants write-capable rights
    where expressible."
  - SYS202 shared pipe: two distinct nodes bind the same `pipe` NAME.
  - SYS203 shared store write: two or more distinct non-store nodes
    have a `Flow` edge landing on the SAME store node.

MODE-BLIND, HONESTLY (ticket's explicit framing): `Flow` carries no
read/write direction today (docs/strata/kernel.md's `Flow` model has
`src`/`dst`/`label`/... but no verb) -- so SYS203 treats ANY inbound
flow to a store as a "write" for contention purposes, which is
deliberately coarser than a real read/write distinction would be. This
is the grammar-data ceiling this ticket ships against; a flow-level
read/write mode (and the deeper SYS201 rights-aware severity a MODE
clause could carry) is T-0700/T-0701's sibling grammar-extension
ticket, not duplicated here. Likewise `store_ids` (which node ids are
STORES, not plain components) is not a `KernelModel`-level fact -- a
store desugars into a plain `Node` at elaborate time (docs/strata/
surface.md#key-construct-semantics) with no reconstructible marker --
so callers that know a design file's `Module.stores` (the parsed AST,
before elaboration folds stores into nodes) must pass those ids in
explicitly; an empty `store_ids` (the default) makes SYS203 emit
nothing, never a false-positive guess at which nodes are stores.

ARBITER-AWARE (T-1025): SYS203 used to be permanently mode-blind AND
arbiter-blind -- it had no code path that consulted `Module.resources`
(the `resource ID { arbitrated_by NODE | lock "NAME" }` declaration
T-0700's grammar added, `_access.py::resource_contention_violations`'s
SYS204 already reads this) at all, so a store with a provably-safe
declared arbiter still fired SYS203 on every one of its writers,
permanently, with no way to discharge it short of a standing waiver.
`check_resource_contention` now accepts an optional `module: Module |
None` (mirroring `resource_contention_violations`'s own signature) --
when a store id in `store_ids` is ALSO a resource id in
`module.resources` with a declared `arbitrated_by` or `lock`, SYS203
treats that store's shared-write finding as discharged (the SAME
"declared arbiter is trusted, whether it is actually RESPECTED is a
separate code-level conformance proof" posture SYS204 already
establishes, `_access.py` module docstring) and skips it entirely --
not merely waived, since the model-level fact this rule exists to catch
("a shared store has multiple writers with no declared coordination")
is no longer true once a real arbiter is declared. `module=None` (the
default) keeps every existing caller's behavior byte-for-byte unchanged
(no arbiter lookup possible without it, same fail-closed posture as an
empty `store_ids`) -- this is additive, not a signature break.

ARBITER-AWARE, SYS201 TOO (T-1149): SYS201 (overlapping path claim) had
the exact same blind spot SYS203 used to -- two nodes legitimately
sharing one arbitered resource (e.g. tickets_ledger's five writers, all
serialized through the SAME `.frob/tickets.lock` flock) would fire a
FALSE overlapping-path conflict the moment either declared an `owns`/
`acl` path claim scoping its access, with no way to discharge it short of
a standing waiver (T-1061's discovery, filed as this ticket). SYS201 now
also consults `module` (the SAME argument SYS203 already takes,
`_arbitered_access_by_node`): if the two nodes in an overlapping-path
pair both declare `access "RESOURCE" mode MODE` (`_access.py::
node_access_declarations`) to a COMMON resource id that itself declares
an arbiter, the pair is skipped entirely -- they are already known,
model-provably coordinated through that arbiter, so the raw path overlap
is no longer an undeclared conflict. `module=None` keeps every pre-T-1149
caller's behavior unchanged, same "additive, not a signature break"
guarantee.

Waiver channel: all four rules can fire more than once per node (a node
can declare several ports/paths/pipes, or write several stores), so each
is registered in `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES` and a
`waive` clause naming one MUST carry a `RULE:SUBTARGET` (the port
number, the overlapping path, the pipe name, or the store id) --
exactly the T-0174 REJECT-round discipline SYS100/SYS101 already
established, reused verbatim rather than re-derived (module docstring
of `_waive.py`).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's 'only' hits \
# are source-level design-rationale/scope-cut prose (docstrings describing \
# already-implemented internal behavior, verifiable by reading the code they annotate) \
# rather than a separate cross-module contract needing its own tracked invariant, the \
# same disposition _host.py's own INV006 waiver already uses; disposed as a \
# calibration batch, not claim-by-claim"

from __future__ import annotations

import re
from collections import defaultdict
from itertools import combinations

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._access import node_access_declarations
from ._ast import Module
from ._host import HostManifest, manifests_by_node
from ._models import KernelModel
from ._waive import apply_waivers

_log = get_logger(__name__)

#: `frob sys audit` rule id for SYS200 duplicate port: two distinct nodes
#: declare the same `listens` PORT.
# frob:doc docs/strata/host.md#resource-contention-sys2xx-t-0699
SYS_DUPLICATE_PORT = "SYS200"

#: `frob sys audit` rule id for SYS201 overlapping path claim: two
#: distinct nodes' `owns`/`acl` PATH atoms overlap by directory prefix.
# frob:doc docs/strata/host.md#resource-contention-sys2xx-t-0699
SYS_OVERLAPPING_PATH = "SYS201"

#: `frob sys audit` rule id for SYS202 shared pipe: two distinct nodes
#: bind the same `pipe` NAME.
# frob:doc docs/strata/host.md#resource-contention-sys2xx-t-0699
SYS_SHARED_PIPE = "SYS202"

#: `frob sys audit` rule id for SYS203 shared store write: two or more
#: distinct nodes have a `Flow` edge landing on the same store node
#: (mode-blind -- module docstring).
# frob:doc docs/strata/host.md#resource-contention-sys2xx-t-0699
SYS_SHARED_STORE_WRITE = "SYS203"

#: Every SYS2xx rule id this module can emit, in catalog order -- the
#: `in_scope` set `_apply_contention_waivers` hands to `apply_waivers`
#: (module docstring: waiver staleness must be judged only against the
#: rule ids this caller actually owns).
# frob:doc docs/strata/host.md#resource-contention-sys2xx-t-0699
RESOURCE_CONTENTION_RULES: frozenset[str] = frozenset(
    {SYS_DUPLICATE_PORT, SYS_OVERLAPPING_PATH, SYS_SHARED_PIPE, SYS_SHARED_STORE_WRITE}
)

#: ACL RIGHTS values (case-insensitive) that grant write access, absent a
#: `:deny` flag -- `_acl_rule_write_capable`'s vocabulary. Deliberately
#: conservative: an unrecognized RIGHTS string (e.g. a custom SDDL rights
#: mask) is treated as NOT write-capable rather than guessed at, matching
#: this module's "ship what the grammar data supports" framing.
_ACL_WRITE_RIGHTS = {"write", "modify", "fullcontrol"}

#: Splits a filesystem-ish PATH (POSIX `/` or Windows `\`) into non-empty
#: segments for prefix-overlap comparison -- `_paths_overlap`'s helper.
_PATH_SEP_RE = re.compile(r"[\\/]+")


# frob:doc docs/strata/host.md#resource-contention-sys2xx-t-0699
class ResourceContentionViolation(BaseModel):
    """One SYS200/SYS201/SYS202/SYS203 finding: rule id, the REPORTING
    node, a human-readable detail naming the peer node(s) it conflicts
    with, and the multi-instance sub-target (port number / overlapping
    path / pipe name / store id) a `waive` clause must name exactly
    (`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`). Mirrors
    `_selfconform.py::SelfConformViolation`'s shape deliberately -- same
    finding contract, different rule family. `write_capable` is only ever
    `True` for SYS201 (module docstring); every other rule leaves it
    `False`."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str
    write_capable: bool = False


# frob:doc docs/strata/host.md#resource-contention-sys2xx-t-0699
class ResourceContentionReport(BaseModel):
    """Every UNWAIVED SYS2xx finding, plus `waived` (T-0174: findings a
    matching `waive` clause suppressed, kept here for report visibility,
    never silently dropped -- `_waive.py` module docstring). Mirrors
    `_selfconform.py::SelfConformReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[ResourceContentionViolation, ...] = ()
    waived: tuple[ResourceContentionViolation, ...] = ()


# frob:ticket T-0972
def _duplicate_port_violations(
    manifests: dict[str, HostManifest],
) -> list[ResourceContentionViolation]:
    """SYS200: group every declared `listens` PORT by node, and fire one
    finding per (node, port) pair wherever >=2 distinct nodes share it --
    two processes cannot bind the same port on the same host regardless
    of platform, so this needs no write/mode distinction at all."""
    by_port: dict[int, list[str]] = defaultdict(list)
    for node_id, manifest in manifests.items():
        for port in manifest.listens:
            by_port[port].append(node_id)
    violations: list[ResourceContentionViolation] = []
    for port, node_ids in sorted(by_port.items()):
        # frob:waive PERF004 reason="node_ids is this loop's own per-port distinct set, not a shared re-sort"  # noqa: E501
        distinct = sorted(set(node_ids))
        if len(distinct) < 2:
            continue
        for node_id in distinct:
            peers = [n for n in distinct if n != node_id]
            _log.warning(
                "contention: SYS200 port %d on %s also declared by %s",
                port,
                node_id,
                peers,
            )
            violations.append(
                ResourceContentionViolation(
                    rule=SYS_DUPLICATE_PORT,
                    node=node_id,
                    sub_target=str(port),
                    detail=(f"port {port} is also declared by {', '.join(peers)}"),
                )
            )
    return violations


def _owns_mode_write_capable(mode: str) -> bool:
    """`True` iff a POSIX `owns` MODE's owner/group/other octal digit has
    the write bit (`0o2`) set anywhere -- `_HostOwns.mode` is already
    validated 3-4 octal digits by `_host.py::HostOwns._validate_mode`, so
    only the trailing 3 permission digits (owner/group/other) are
    inspected here; a leading 4th (setuid/setgid/sticky) digit carries no
    write semantics of its own."""
    permission_digits = mode[-3:]
    return any(int(digit) & 0o2 for digit in permission_digits)


def _acl_rule_write_capable(rule: str) -> bool:
    """`True` iff a Windows `acl` RULE's RIGHTS is one of
    `_ACL_WRITE_RIGHTS` and the rule is not `:deny`'d -- `HostAcl.rule` is
    already validated `PRINCIPAL:RIGHTS[:deny][:no_inherit]` shape by
    `_host.py::HostAcl._validate_rule`, so a plain split is safe here."""
    _principal, _, rest = rule.partition(":")
    flags = rest.split(":")
    rights = flags[0].strip().lower() if flags else ""
    is_deny = "deny" in flags[1:]
    return (not is_deny) and rights in _ACL_WRITE_RIGHTS


def _path_segments(path: str) -> tuple[str, ...]:
    """Split a POSIX or Windows PATH into non-empty segments, used ONLY
    for directory-prefix comparison (`_paths_overlap`) -- never
    reinterpreted as a filesystem access."""
    return tuple(segment for segment in _PATH_SEP_RE.split(path) if segment)


def _paths_overlap(path_a: str, path_b: str) -> bool:
    """`True` iff one PATH's segments are a prefix of the other's -- a
    real directory-subtree overlap (`/var/lib/api` vs `/var/lib/api/data`),
    never a bare string-prefix false-positive (`/var/lib/api` does NOT
    overlap `/var/lib/api2`, since `"api2"` is not the segment `"api"`)."""
    segments_a, segments_b = _path_segments(path_a), _path_segments(path_b)
    if not segments_a or not segments_b:
        return False
    shorter, longer = (
        (segments_a, segments_b)
        if len(segments_a) <= len(segments_b)
        else (segments_b, segments_a)
    )
    return longer[: len(shorter)] == shorter


def _path_claims(
    manifests: dict[str, HostManifest],
) -> list[tuple[str, str, bool]]:
    """Every `(node_id, path, write_capable)` claim from EITHER `owns`
    (linux) or `acl` (windows) across every manifest, sorted for
    deterministic pairwise comparison -- `_overlapping_path_violations`'s
    input. Mixing linux `owns` and windows `acl` claims in one pass is
    deliberate: the PATH STRINGS still meaningfully overlap even across a
    declared-platform mismatch (module docstring's "mode-blind, honestly"
    framing does not require single-platform purity to be useful)."""
    claims: list[tuple[str, str, bool]] = []
    for node_id, manifest in manifests.items():
        for owns in manifest.owns:
            claims.append((node_id, owns.path, _owns_mode_write_capable(owns.mode)))
        for acl in manifest.acl:
            claims.append((node_id, acl.path, _acl_rule_write_capable(acl.rule)))
    return sorted(claims)


def _share_common_arbiter(
    node_a: str,
    node_b: str,
    arbitered_access_by_node: dict[str, frozenset[str]],
) -> bool:
    """T-1149: `True` iff `node_a`/`node_b` both declare `access` to at
    least one common ARBITERED resource id -- `_overlapping_path_
    violations`'s ARBITER-AWARE discharge condition, split out purely to
    keep that function under ARCH001's line threshold."""
    return bool(
        arbitered_access_by_node.get(node_a, frozenset())
        & arbitered_access_by_node.get(node_b, frozenset())
    )


def _overlapping_path_violation_pair(
    node_a: str,
    path_a: str,
    write_a: bool,
    node_b: str,
    path_b: str,
    write_b: bool,
) -> list[ResourceContentionViolation]:
    """The two `ResourceContentionViolation`s (one per participating node)
    for one overlapping-path pair -- `_overlapping_path_violations`'s
    per-pair emission, split out purely to keep that function under
    ARCH001's line threshold."""
    write_capable = write_a or write_b
    _log.warning(
        "contention: SYS201 path %r on %s overlaps %s's %r (write_capable=%s)",
        path_a,
        node_a,
        node_b,
        path_b,
        write_capable,
    )
    return [
        ResourceContentionViolation(
            rule=SYS_OVERLAPPING_PATH,
            node=node_a,
            sub_target=path_a,
            detail=(
                f"path {path_a!r} overlaps {node_b}'s {path_b!r}"
                + (" (write-capable)" if write_capable else "")
            ),
            write_capable=write_capable,
        ),
        ResourceContentionViolation(
            rule=SYS_OVERLAPPING_PATH,
            node=node_b,
            sub_target=path_b,
            detail=(
                f"path {path_b!r} overlaps {node_a}'s {path_a!r}"
                + (" (write-capable)" if write_capable else "")
            ),
            write_capable=write_capable,
        ),
    ]


def _overlapping_path_violations(
    manifests: dict[str, HostManifest],
    arbitered_access_by_node: dict[str, frozenset[str]] | None = None,
) -> list[ResourceContentionViolation]:
    """SYS201: every pairwise-overlapping `(node, path)` claim across
    DISTINCT nodes, reported once per participating node (module
    docstring's `ResourceContentionViolation` shape) with `write_capable`
    set when either side's claim expresses a write-capable grant.

    T-1149 (ARBITER-AWARE, mirroring SYS203/T-1025's exact discharge
    condition): `arbitered_access_by_node` (default `None`, i.e. no
    discharge -- fail-closed, same posture `_shared_store_write_
    violations`'s `module=None` establishes) maps a node id to the
    ARBITERED resource ids (`_arbitered_resource_ids`) it declares
    `access` to (`_access.py::node_access_declarations`). A pair whose two
    nodes share at least one common arbitered resource id
    (`_share_common_arbiter`) is SKIPPED entirely -- the model already
    proves those two nodes coordinate their access to something both
    consider the same shared thing, so an overlapping filesystem path
    claim between them is no longer an undeclared conflict (module
    docstring's "ARBITER-AWARE" framing, same reasoning SYS203 already
    applies to store writers)."""
    arbitered_access_by_node = arbitered_access_by_node or {}
    violations: list[ResourceContentionViolation] = []
    for (node_a, path_a, write_a), (node_b, path_b, write_b) in combinations(
        _path_claims(manifests), 2
    ):
        if node_a == node_b or not _paths_overlap(path_a, path_b):
            continue
        if _share_common_arbiter(node_a, node_b, arbitered_access_by_node):
            _log.debug(
                "contention: SYS201 path %r on %s overlaps %s's %r but both "
                "share a common arbitered resource, skipped",
                path_a,
                node_a,
                node_b,
                path_b,
            )
            continue
        violations.extend(
            _overlapping_path_violation_pair(
                node_a, path_a, write_a, node_b, path_b, write_b
            )
        )
    return violations


# frob:ticket T-0972
def _shared_pipe_violations(
    manifests: dict[str, HostManifest],
) -> list[ResourceContentionViolation]:
    """SYS202: group every declared `pipe` NAME by node, fire one finding
    per (node, pipe) pair wherever >=2 distinct nodes bind it -- the
    named-pipe analog of SYS200's port check."""
    by_pipe: dict[str, list[str]] = defaultdict(list)
    for node_id, manifest in manifests.items():
        for pipe_name in manifest.pipes:
            by_pipe[pipe_name].append(node_id)
    violations: list[ResourceContentionViolation] = []
    for pipe_name, node_ids in sorted(by_pipe.items()):
        # frob:waive PERF004 reason="node_ids is this loop's own per-pipe distinct set, not a shared re-sort"  # noqa: E501
        distinct = sorted(set(node_ids))
        if len(distinct) < 2:
            continue
        for node_id in distinct:
            peers = [n for n in distinct if n != node_id]
            _log.warning(
                "contention: SYS202 pipe %r on %s also bound by %s",
                pipe_name,
                node_id,
                peers,
            )
            violations.append(
                ResourceContentionViolation(
                    rule=SYS_SHARED_PIPE,
                    node=node_id,
                    sub_target=pipe_name,
                    detail=f"pipe {pipe_name!r} is also bound by {', '.join(peers)}",
                )
            )
    return violations


def _arbitered_resource_ids(module: Module | None) -> frozenset[str]:
    """T-1025: every `Module.resources` id declaring a real arbiter
    (`arbitrated_by` or `lock`) -- the SAME discharge condition
    `_access.py::resource_contention_violations` (SYS204) already
    applies, reused here so SYS203 and SYS204 never disagree about what
    counts as "arbitered". `module=None` (no AST available to this
    caller) yields the empty set, i.e. no discharge -- fail-closed, same
    posture as an empty `store_ids`."""
    if module is None:
        return frozenset()
    return frozenset(
        resource.id
        for resource in module.resources
        if resource.arbitrated_by is not None or resource.lock is not None
    )


def _arbitered_access_by_node(
    model: KernelModel, module: Module | None
) -> dict[str, frozenset[str]]:
    """T-1149: every node id -> the set of ARBITERED resource ids
    (`_arbitered_resource_ids`) it declares `access "RESOURCE" mode MODE`
    to (`_access.py::node_access_declarations`) -- SYS201's join key for
    "these two nodes are already coordinating through a common declared
    arbiter" (module docstring's T-1149 section on
    `_overlapping_path_violations`). `module=None` yields an empty dict,
    i.e. no discharge for any node -- same fail-closed posture
    `_arbitered_resource_ids` itself establishes."""
    arbitered = _arbitered_resource_ids(module)
    if not arbitered:
        return {}
    by_node: dict[str, frozenset[str]] = {}
    for node in model.nodes:
        resources = frozenset(
            declaration.resource
            for declaration in node_access_declarations(node)
            if declaration.resource in arbitered
        )
        if resources:
            by_node[node.id] = resources
    return by_node


# frob:ticket T-0972
def _shared_store_write_violations(
    model: KernelModel,
    store_ids: frozenset[str],
    module: Module | None = None,
) -> list[ResourceContentionViolation]:
    """SYS203: every store id in `store_ids` written (module docstring:
    ANY inbound `Flow`, mode-blind) by >=2 distinct non-store nodes fires
    once per writer, naming its co-writers. `store_ids` empty (the
    default) means "no store facts available to this caller" -- emits
    nothing, never a guessed-at store set (module docstring). T-1025: a
    store id that is ALSO a `module.resources` id with a declared arbiter
    (`_arbitered_resource_ids`) is skipped entirely -- the model already
    proves that store's writes are coordinated, so there is nothing left
    for this mode-blind rule to usefully flag (module docstring's
    "ARBITER-AWARE" section)."""
    if not store_ids:
        return []
    arbitered = _arbitered_resource_ids(module)
    writers: dict[str, set[str]] = defaultdict(set)
    for flow in model.flows:
        if flow.dst in store_ids and flow.src != flow.dst:
            writers[flow.dst].add(flow.src)
    violations: list[ResourceContentionViolation] = []
    for store_id, node_id_set in sorted(writers.items()):
        if store_id in arbitered:
            _log.debug(
                "contention: SYS203 store %s has a declared arbiter, skipped",
                store_id,
            )
            continue
        # frob:waive PERF004 reason="node_id_set is this loop's own per-store distinct set, not a shared re-sort"  # noqa: E501
        distinct = sorted(node_id_set)
        if len(distinct) < 2:
            continue
        for node_id in distinct:
            peers = [n for n in distinct if n != node_id]
            _log.warning(
                "contention: SYS203 store %s written by %s, also by %s (mode-blind)",
                store_id,
                node_id,
                peers,
            )
            violations.append(
                ResourceContentionViolation(
                    rule=SYS_SHARED_STORE_WRITE,
                    node=node_id,
                    sub_target=store_id,
                    detail=(
                        f"store {store_id} is also written by {', '.join(peers)} "
                        "(mode-blind: any inbound flow counted as a write, "
                        "docs/strata/host.md)"
                    ),
                )
            )
    return violations


def _apply_contention_waivers(
    model: KernelModel, violations: list[ResourceContentionViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_selfconform.py::_apply_sys_waivers`'s pattern reused for the SYS2xx
    family: `sub_target_of` returns `ResourceContentionViolation.
    sub_target` (the port/path/pipe/store id) since every rule here is
    registered in `MULTI_INSTANCE_WAIVER_FAMILIES` and always carries one.
    `in_scope` is `RESOURCE_CONTENTION_RULES` so staleness is judged only
    against waivers this pass can actually match (`_waive.py::
    apply_waivers`'s `in_scope` docstring)."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in RESOURCE_CONTENTION_RULES,
    )


# frob:doc docs/strata/host.md#resource-contention-sys2xx-t-0699
# frob:ticket T-0699
# frob:enforces CHK-GATE-SYS200
# frob:enforces CHK-GATE-SYS201
# frob:enforces CHK-GATE-SYS202
# frob:enforces CHK-GATE-SYS203
# frob:enforces CHK-GATE-SYSWAIVE002
# frob:tests tests/unit/strata/test_contention.py::TestDuplicatePort.test_two_nodes_same_port_fires  # noqa: E501
def check_resource_contention(
    model: KernelModel,
    store_ids: frozenset[str] = frozenset(),
    module: Module | None = None,
) -> ResourceContentionReport:
    """The SYS2xx resource-contention entrypoint (T-0699): every
    duplicate-port (SYS200), overlapping-path (SYS201), shared-pipe
    (SYS202), and shared-store-write (SYS203) finding across `model`,
    waivers already applied (module docstring). `store_ids` is the caller-
    supplied set of node ids that originated from a `store` construct
    (`Module.stores`, pre-elaboration) -- `KernelModel` alone cannot
    reconstruct which of its nodes were stores (module docstring), so
    SYS203 is silent without it. `module` (T-1025, optional, additive) is
    the same pre-elaboration AST `_access.py::resource_contention_
    violations` already takes, threaded through so SYS203 can consult a
    store's declared arbiter (`_arbitered_resource_ids`) the same way
    SYS204 does -- `module=None` keeps every pre-T-1025 caller's
    behavior unchanged. T-1149: the SAME `module` argument now also makes
    SYS201 arbiter-aware (`_arbitered_access_by_node`) -- two nodes whose
    overlapping `owns`/`acl` paths would otherwise fire SYS201 are skipped
    if they share a common `access`-declared, arbitered resource id."""
    manifests = manifests_by_node(model)
    arbitered_access = _arbitered_access_by_node(model, module)
    violations: list[ResourceContentionViolation] = []
    violations.extend(_duplicate_port_violations(manifests))
    violations.extend(_overlapping_path_violations(manifests, arbitered_access))
    violations.extend(_shared_pipe_violations(manifests))
    violations.extend(_shared_store_write_violations(model, store_ids, module))
    applied = _apply_contention_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        ResourceContentionViolation(
            rule="SYSWAIVE002",
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
    return ResourceContentionReport(
        violations=tuple(applied.kept) + stale, waived=waived
    )


__all__ = [
    "RESOURCE_CONTENTION_RULES",
    "SYS_DUPLICATE_PORT",
    "SYS_OVERLAPPING_PATH",
    "SYS_SHARED_PIPE",
    "SYS_SHARED_STORE_WRITE",
    "ResourceContentionReport",
    "ResourceContentionViolation",
    "check_resource_contention",
]
