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

from ._host import HostManifest, host_manifest_for
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


def _node_manifests(model: KernelModel) -> dict[str, HostManifest]:
    """Every node's `HostManifest`, keyed by node id, skipping nodes with
    no std.host construct at all (`host_manifest_for` returns `None` for
    those) -- the shared per-node lookup every SYS2xx rule reads from."""
    manifests: dict[str, HostManifest] = {}
    for node in model.nodes:
        manifest = host_manifest_for(node)
        if manifest is not None:
            manifests[node.id] = manifest
    return manifests


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


def _overlapping_path_violations(
    manifests: dict[str, HostManifest],
) -> list[ResourceContentionViolation]:
    """SYS201: every pairwise-overlapping `(node, path)` claim across
    DISTINCT nodes, reported once per participating node (module
    docstring's `ResourceContentionViolation` shape) with `write_capable`
    set when either side's claim expresses a write-capable grant."""
    violations: list[ResourceContentionViolation] = []
    for (node_a, path_a, write_a), (node_b, path_b, write_b) in combinations(
        _path_claims(manifests), 2
    ):
        if node_a == node_b or not _paths_overlap(path_a, path_b):
            continue
        write_capable = write_a or write_b
        _log.warning(
            "contention: SYS201 path %r on %s overlaps %s's %r (write_capable=%s)",
            path_a,
            node_a,
            node_b,
            path_b,
            write_capable,
        )
        violations.append(
            ResourceContentionViolation(
                rule=SYS_OVERLAPPING_PATH,
                node=node_a,
                sub_target=path_a,
                detail=(
                    f"path {path_a!r} overlaps {node_b}'s {path_b!r}"
                    + (" (write-capable)" if write_capable else "")
                ),
                write_capable=write_capable,
            )
        )
        violations.append(
            ResourceContentionViolation(
                rule=SYS_OVERLAPPING_PATH,
                node=node_b,
                sub_target=path_b,
                detail=(
                    f"path {path_b!r} overlaps {node_a}'s {path_a!r}"
                    + (" (write-capable)" if write_capable else "")
                ),
                write_capable=write_capable,
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


# frob:ticket T-0972
def _shared_store_write_violations(
    model: KernelModel, store_ids: frozenset[str]
) -> list[ResourceContentionViolation]:
    """SYS203: every store id in `store_ids` written (module docstring:
    ANY inbound `Flow`, mode-blind) by >=2 distinct non-store nodes fires
    once per writer, naming its co-writers. `store_ids` empty (the
    default) means "no store facts available to this caller" -- emits
    nothing, never a guessed-at store set (module docstring)."""
    if not store_ids:
        return []
    writers: dict[str, set[str]] = defaultdict(set)
    for flow in model.flows:
        if flow.dst in store_ids and flow.src != flow.dst:
            writers[flow.dst].add(flow.src)
    violations: list[ResourceContentionViolation] = []
    for store_id, node_id_set in sorted(writers.items()):
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
# frob:tests tests/unit/strata/test_contention.py::TestDuplicatePort.test_two_nodes_same_port_fires  # noqa: E501
def check_resource_contention(
    model: KernelModel, store_ids: frozenset[str] = frozenset()
) -> ResourceContentionReport:
    """The SYS2xx resource-contention entrypoint (T-0699): every
    duplicate-port (SYS200), overlapping-path (SYS201), shared-pipe
    (SYS202), and shared-store-write (SYS203) finding across `model`,
    waivers already applied (module docstring). `store_ids` is the caller-
    supplied set of node ids that originated from a `store` construct
    (`Module.stores`, pre-elaboration) -- `KernelModel` alone cannot
    reconstruct which of its nodes were stores (module docstring), so
    SYS203 is silent without it."""
    manifests = _node_manifests(model)
    violations: list[ResourceContentionViolation] = []
    violations.extend(_duplicate_port_violations(manifests))
    violations.extend(_overlapping_path_violations(manifests))
    violations.extend(_shared_pipe_violations(manifests))
    violations.extend(_shared_store_write_violations(model, store_ids))
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
