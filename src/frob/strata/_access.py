"""T-0700: access modes + shared-resource/lease declarations for
contention proofs (docs/strata/host.md#resource-access-modes-t-0700), the
grammar half of the resource-contention mandate that upgrades
`_contention.py`'s SYS203 shared-store-write rule from MODE-BLIND (module
docstring there: "`Flow` carries no read/write direction today ... any
inbound flow to a store [is] a 'write' for contention purposes") to
mode-aware WITHOUT renaming SYS200-203 -- this module adds a NEW rule
(SYS204) alongside them rather than touching that file, per the same
"one rule module per obligation" precedent `_message_schema.py`'s module
docstring already establishes for this ticket family.

GRAMMAR (`strata-core/src/parse.rs`): a node/store may declare
`access "RESOURCE" mode MODE` (MODE one of `read`/`append`/`alpha`/
`write`/`exclusive`, `parse_access_attr`), repeatable, desugared STRAIGHT
to an `access=<resource>:<mode>` attr -- the `bin_path` T-0629 direct-
attr-push shape, so no `NodeDecl`/`StoreDecl` field was threaded through
`_ast.py`/`_elaborate.py`/`_infra.py` (out of this module's read-back-only
concern, mirroring `_host.py::_parse_host_attrs`'s "reads the attr back
regardless of which caller produced it" discipline). Separately, a
top-level `resource ID { arbitrated_by NODE | lock "NAME" }` statement
(`_ast.py::ResourceDecl`, `Module.resources`) names a shared resource and,
optionally, its single arbiter/lease -- a resource has no accessor of its
own, so unlike `access` it could not desugar into an attr and gets its own
`Module`-level field instead.

ALPHA SEMANTICS (user-specified 2026-07-22, the update/upgradeable-lock
pattern): `alpha` declares INTEREST in a future writer lock -- many writes
need a read just before, so `alpha` sits between `read` and `write`.
COMPATIBILITY MATRIX two accessors of the SAME resource must satisfy
(`mode_conflict` below) -- only ONE pairing is deliberately silent
(read+read) and one is explicitly SAFE (read+alpha, "alpha never
conflicts with readers"); everything else conflicts:

  - read + read:      OK (any number of readers)
  - read + alpha:     OK (alpha never conflicts with readers)
  - alpha + alpha:    CONFLICT (exactly one writer-intender per resource --
                       this is what prevents the two-readers-both-
                       upgrading deadlock)
  - write/append/exclusive + anything (including itself): CONFLICT
    ("write+anything CONFLICT", the ticket's exact framing -- an alpha
    holder upgrades to write only once readers drain, so a write-mode
    accessor coexisting with ANY other accessor, reader or not, is unsafe
    without an arbiter)

DOCUMENTED JUDGMENT CALL: the ticket's prose matrix only names
`read`/`alpha`/`write` explicitly; `append` and `exclusive` are folded in
here as WRITE-LIKE -- `append` still mutates the resource so
"write+anything conflicts" applies to it too, and `exclusive` is, if
anything, STRICTER than plain `write` (it must not coexist with ANY other
accessor, including another `exclusive` or a lone `read`). `mode_conflict`
implements this as a closed ALLOW-list (only read+read and read+alpha are
safe; everything else conflicts) rather than an explicit write-like
frozenset, so `append`/`exclusive` fall out of the same default without a
special case.

CONTENTION PROOF (`resource_contention_violations`, SYS204): for every
resource id referenced by at least one `access` declaration across
`model`'s nodes, gather every (node, mode) accessor pair; if any two
conflict per the matrix above AND the resource declares no arbiter (no
`arbitrated_by`/`lock` in `Module.resources`, or no `resource` block at
all for that id), fire SYS204 fail-closed -- a declared arbiter is trusted
to make the conflicting pair provably safe (T-0701 is the code-level
conformance proof that the arbiter/lease is actually RESPECTED; this
module only checks the model-level declaration, module docstring's scope
line).

DELIBERATELY NOT WIRED HERE (disclosed cut, not silently dropped): CLI
dispatch (`src/frob/app/sys_runner.py`) and the T-0174 waiver channel
(`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`) are both shared surfaces a
sibling ticket's obligation batch may be touching concurrently
(dispatch-prompt scope boundary) -- `resource_contention_violations` is a
pure, fully-tested function any caller can wire in; the CLI/waiver
integration is filed as a follow-up ticket (Done report) rather than
touched here.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's 'only' hits \
# are source-level design-rationale/scope-cut prose (docstrings describing the \
# compatibility matrix and disclosed cuts) rather than a separate cross-module \
# contract needing its own tracked invariant, the same disposition \
# _ssot.py/_contention.py's own identical waiver already uses for this module family \
# (module docstring precedent)"

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from itertools import combinations

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._ast import Module, ResourceDecl
from ._models import KernelModel, Node

_log = get_logger(__name__)

#: `access=<resource>:<mode>` attr prefix `parse_access_attr` desugars to
#: (mirrors `_pii.py::_PII_PREFIX`'s `pii=<tag>` convention).
_ACCESS_PREFIX = "access="

#: `frob sys audit` rule id for SYS204 unarbitrated mode conflict: two or
#: more accessors of the same resource whose declared modes conflict per
#: the compatibility matrix (module docstring), with no declared arbiter.
# frob:doc docs/strata/host.md#resource-access-modes-t-0700
SYS_UNARBITRATED_MODE_CONFLICT = "SYS204"


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
class AccessMode(StrEnum):
    """The closed `access ... mode MODE` vocabulary (T-0700), validated
    already at parse time (`parse_access_attr`) -- this enum exists so
    Python callers get the same closed set back, not a bare string, and so
    `mode_conflict`'s matrix has a fixed domain to switch over."""

    READ = "read"
    APPEND = "append"
    ALPHA = "alpha"
    WRITE = "write"
    EXCLUSIVE = "exclusive"


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
class NodeAccess(BaseModel):
    """One `access "RESOURCE" mode MODE` declaration read back off a
    node's attrs (`node_access_declarations`) -- the resource id and the
    declared `AccessMode`."""

    model_config = ConfigDict(frozen=True)

    resource: str
    mode: AccessMode


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
class ResourceContentionViolation(BaseModel):
    """One SYS204 finding: the resource id, the two conflicting accessor
    node ids and their declared modes, and a human-readable detail --
    mirrors `_contention.py::ResourceContentionViolation`'s shape
    deliberately (module docstring: same finding contract, sibling rule
    family, no shared import to avoid touching that file)."""

    model_config = ConfigDict(frozen=True)

    rule: str
    resource: str
    node: str
    mode: AccessMode
    peer: str
    peer_mode: AccessMode
    detail: str


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
class ResourceContentionReport(BaseModel):
    """Every SYS204 finding across a model (module docstring: waiver
    integration deliberately not wired here, see the cut disclosed
    there)."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[ResourceContentionViolation, ...] = ()


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
# frob:tests tests/unit/strata/test_access.py::TestNodeAccessDeclarations.test_reads_access_attrs  # noqa: E501
def node_access_declarations(node: Node) -> tuple[NodeAccess, ...]:
    """Every `access "RESOURCE" mode MODE` clause `node` declares (i.e.
    every `access=<resource>:<mode>` attr, `_ACCESS_PREFIX` convention) --
    mirrors `_pii.py::node_pii_tags`'s attr read-back shape exactly.

    Raises `ValueError` if an attr's mode is not a recognized
    `AccessMode` -- fail-closed rather than silently skipping a malformed
    attr, since `parse_access_attr` already validates this vocabulary at
    parse time and a mismatch here would mean the attr was hand-built by
    something other than the grammar (the same defensive posture
    `_host.py::host_manifest_for`'s platform check takes)."""
    declarations: list[NodeAccess] = []
    for attr in node.attrs:
        if not attr.startswith(_ACCESS_PREFIX):
            continue
        resource, _, mode_str = attr[len(_ACCESS_PREFIX) :].partition(":")
        try:
            mode = AccessMode(mode_str)
        except ValueError as exc:
            raise ValueError(
                f"node {node.id!r} access attr {attr!r} has unrecognized "
                f"mode {mode_str!r}"
            ) from exc
        declarations.append(NodeAccess(resource=resource, mode=mode))
    return tuple(declarations)


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
# frob:tests tests/unit/strata/test_access.py::TestModeConflict.test_read_read_is_safe
def mode_conflict(a: AccessMode, b: AccessMode) -> bool:
    """Whether two accessors of the SAME resource declaring modes `a`/`b`
    conflict per the T-0700 compatibility matrix (module docstring): the
    ONLY safe pairings are read+read and read+alpha ("alpha never
    conflicts with readers") -- every other pairing conflicts, including
    a mode against itself (alpha+alpha, write+write, exclusive+exclusive)
    and any write-like mode against anything at all. Fail-closed default:
    a future mode this matrix has not been extended to cover conflicts by
    default rather than being silently treated as safe."""
    modes = frozenset({a, b})
    if modes == frozenset({AccessMode.READ}):
        return False
    if modes == frozenset({AccessMode.READ, AccessMode.ALPHA}):
        return False
    return True


def _resource_arbiters(module: Module) -> dict[str, ResourceDecl]:
    """Every declared `resource` statement, keyed by id -- the arbiter
    lookup `resource_contention_violations` joins accessors against."""
    return {resource.id: resource for resource in module.resources}


def _resource_accessors(model: KernelModel) -> dict[str, list[tuple[str, AccessMode]]]:
    """Every (node id, mode) pair declaring `access` to each resource id,
    across every node in `model` -- the per-resource accessor lists the
    contention proof compares pairwise."""
    accessors: dict[str, list[tuple[str, AccessMode]]] = defaultdict(list)
    for node in model.nodes:
        for declaration in node_access_declarations(node):
            accessors[declaration.resource].append((node.id, declaration.mode))
    return accessors


# frob:doc docs/strata/host.md#resource-access-modes-t-0700
# frob:tests tests/unit/strata/test_access.py::TestResourceContentionViolations.test_two_writers_no_arbiter_fires  # noqa: E501
def resource_contention_violations(
    model: KernelModel, module: Module
) -> ResourceContentionReport:
    """The SYS204 contention-proof entrypoint (T-0700): every pair of
    `access` declarations on the SAME resource whose modes conflict
    (`mode_conflict`) with NO declared arbiter/lease for that resource
    (`Module.resources`) fires a fail-closed finding. A declared arbiter
    (`arbitrated_by` OR `lock`) discharges the model-level obligation --
    whether the arbiter is actually RESPECTED by the node's code is
    T-0701's separate, code-level conformance proof (module docstring
    scope line), not this function's job.

    `module` is the pre-elaboration `Module` (parsed AST) purely to reach
    `Module.resources` -- `KernelModel` has no reconstructible notion of a
    `resource` block (it has no accessor of its own to desugar into a
    node/attr), the same "caller must pass in what elaboration cannot
    reconstruct" shape `_contention.py::check_resource_contention`'s
    `store_ids` parameter already established for SYS203 (module
    docstring)."""
    arbiters = _resource_arbiters(module)
    accessors = _resource_accessors(model)
    violations: list[ResourceContentionViolation] = []
    for resource_id, pairs in accessors.items():
        arbitered = resource_id in arbiters and (
            arbiters[resource_id].arbitrated_by is not None
            or arbiters[resource_id].lock is not None
        )
        if arbitered:
            _log.debug(
                "resource %s: arbiter/lease declared, contention proof skipped",
                resource_id,
            )
            continue
        for (node_a, mode_a), (node_b, mode_b) in combinations(pairs, 2):
            if not mode_conflict(mode_a, mode_b):
                continue
            _log.debug(
                "SYS204: resource %s conflict %s(%s) vs %s(%s), no arbiter",
                resource_id,
                node_a,
                mode_a,
                node_b,
                mode_b,
            )
            violations.append(
                ResourceContentionViolation(
                    rule=SYS_UNARBITRATED_MODE_CONFLICT,
                    resource=resource_id,
                    node=node_a,
                    mode=mode_a,
                    peer=node_b,
                    peer_mode=mode_b,
                    detail=(
                        f"resource {resource_id!r}: node {node_a!r} "
                        f"({mode_a.value}) conflicts with node {node_b!r} "
                        f"({mode_b.value}), no arbitrated_by/lock declared"
                    ),
                )
            )
    return ResourceContentionReport(violations=tuple(violations))
