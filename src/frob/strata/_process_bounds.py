"""REL39x reliability family: KERNEL-INTERFACE-CLASSIFICATION +
PROCESS-RESOURCE-BOUND obligations (T-0960, filed while reconciling
T-0958's `system-design.yaml` deferred rows: SDC-13-EVERY-KERNEL-
USERSPACE-INTERFACE-SYSCALL-PROCFS-SYSFS-ENTRY-IOCTL-IS-CLASSIFIED-INT and
SDC-13-EVERY-DEPLOYED-PROCESS-DECLARES-ITS-RESOURCE-BOUNDS-CGROUP-LIMITS-
CPU-MEMORY-IO-AND). Mirrors `_backpressure.py`'s REL26x structure exactly
(module docstring precedent, T-0646/T-0919/...: one rule module per
obligation-pair-family, same `Report`/`Violation` pydantic pair,
registration/exemption from `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
CLI wiring left as its own follow-up ticket -- the same posture
`_backpressure.py`/`_interactive_cost.py` are already in, not yet threaded
into `frob.app.sys_runner._run_audit`).

TWO OBLIGATION PAIRS, each NODE-scoped (a node has at most one marker
attr per pair and fires at most one missing/unproven finding each --
single-instance-per-node, the same carve-out `_backpressure.py`'s
REL260/REL261 and `_interactive_cost.py`'s REL310/REL311 pairs establish,
NEITHER pair registered in `MULTI_INSTANCE_WAIVER_FAMILIES`):

  - REL390 missing interface classification / REL391 unproven interface
    classification: a node marked `kernel_interface` (this node touches a
    syscall, procfs/sysfs entry, or ioctl -- a kernel/userspace boundary)
    needs a declared `interface_classified` attr (trusted/untrusted,
    read/write, ...); REL391 then requires real code-level evidence of a
    classification-shaped construct (an access-mode check, a seccomp/
    capability filter, an explicit trust-boundary comment token) in that
    node's bound code, per the T-0331 PROVABILITY CONSTRAINT. Deny-by-
    default: an unclassified kernel/userspace interface has no declared
    trust boundary at all, so a syscall/procfs/ioctl surface can silently
    widen (a new field read, a new ioctl added) with nothing statically
    flagging that it was never triaged.
  - REL392 missing process resource bounds / REL393 unproven process
    resource bounds: a node marked `deployed_process` (this node models a
    process actually deployed to a host -- a long-running service, a
    worker) needs a declared `cgroup_bounds` attr (its cpu/memory/io
    limits are set); REL393 then requires real code-level evidence of a
    cgroup/resource-limit-shaped construct in that node's bound code.
    Deny-by-default: a deployed process with no declared resource bound
    can consume unbounded host cpu/memory/io, the same "no ceiling
    declared, no ceiling enforced" risk REL26x's queue population and
    REL31x's interactive-flow population already cover for their own
    resource dimensions -- this pair is the process/cgroup dimension.

GRAMMAR-DATA CEILING, HONESTLY: `kernel_interface`/`interface_classified`/
`deployed_process`/`cgroup_bounds` are all bare Node attrs (no numeric
magnitude -- the same digit-led-literal ceiling `strata-core/src/parse.rs`'s
generic `attr KEY=VALUE` clause imposes on every other REL2xx/REL3xx
marker), so REL390-REL393 prove PRESENCE of a declared obligation and its
code-level evidence, not a specific classification value or a specific
numeric cgroup limit. This module is a static declaration-and-proof check
over strata's own host/deploy vocabulary, NOT runtime kernel introspection
-- it cannot observe an actual running process's actual cgroup file or an
actual syscall's actual classification, only whether the DECLARATION and
its bound-code evidence exist (the same honesty line REL201/REL222/
REL231/REL261/REL301/REL311 already establish for their own dimensions).
No `strata-core` change needed (this ticket's scope is
`src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**` only, same as
T-0646/T-0919's).
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import bind_code
from ._errors import StrataError
from ._models import KernelModel
from ._obligation_proof import files_evidence_token, node_has_bound_code, owner_index
from ._waive import apply_waivers, stale_relwaive_violations

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL390 missing interface classification: a
#: `kernel_interface` node with no `interface_classified` attr declared.
# frob:doc docs/strata/reliability.md#rel39x-kernel-interface--process-bounds-t-0960
REL_MISSING_INTERFACE_CLASSIFICATION = "REL390"

#: `frob sys audit` rule id for REL391 unproven interface classification: a
#: node declares `interface_classified`, but its bound code has no real
#: classification-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel39x-kernel-interface--process-bounds-t-0960
REL_UNPROVEN_INTERFACE_CLASSIFICATION = "REL391"

#: `frob sys audit` rule id for REL392 missing process resource bounds: a
#: `deployed_process` node with no `cgroup_bounds` attr declared.
# frob:doc docs/strata/reliability.md#rel39x-kernel-interface--process-bounds-t-0960
REL_MISSING_PROCESS_BOUNDS = "REL392"

#: `frob sys audit` rule id for REL393 unproven process resource bounds: a
#: node declares `cgroup_bounds`, but its bound code has no real
#: cgroup/resource-limit-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel39x-kernel-interface--process-bounds-t-0960
REL_UNPROVEN_PROCESS_BOUNDS = "REL393"

#: Every REL39x rule id this module can emit -- this module's own, narrow
#: family for `_apply_process_bounds_waivers`' `in_scope` (the "never a
#: shared superset" discipline `_reliability.py`'s module docstring
#: documents the real regression for).
# frob:doc docs/strata/reliability.md#rel39x-kernel-interface--process-bounds-t-0960
PROCESS_BOUNDS_RULES: frozenset[str] = frozenset(
    {
        REL_MISSING_INTERFACE_CLASSIFICATION,
        REL_UNPROVEN_INTERFACE_CLASSIFICATION,
        REL_MISSING_PROCESS_BOUNDS,
        REL_UNPROVEN_PROCESS_BOUNDS,
    }
)

#: Node attr marking a kernel/userspace-interface-touching node (syscall,
#: procfs/sysfs entry, ioctl) -- the REL390/REL391 population.
_KERNEL_INTERFACE_ATTR = "kernel_interface"

#: Node attr discharging the REL390 classification obligation
#: (presence-only, module docstring's grammar-data ceiling).
_INTERFACE_CLASSIFIED_ATTR = "interface_classified"

#: Node attr marking a process actually deployed to a host -- the
#: REL392/REL393 population.
_DEPLOYED_PROCESS_ATTR = "deployed_process"

#: Node attr discharging the REL392 resource-bound obligation
#: (presence-only, module docstring's grammar-data ceiling).
_CGROUP_BOUNDS_ATTR = "cgroup_bounds"

#: Regex proving a real interface-classification-shaped token in bound
#: source text (REL391) -- deliberately narrow (a syntactic token scan,
#: not a semantic call-argument binding), matching common classification
#: shapes: trust/access-mode markers (`trusted`, `untrusted`, `read_only`,
#: `readonly`, `read_write`), a kernel filter/allowlist construct
#: (`seccomp`, `capability`, `syscall_filter`, `allowlist`, `denylist`),
#: or a literal `ioctl`/`procfs`/`sysfs`/`syscall` identifier paired with
#: a classification word. Same honesty line `_backpressure.py::
#: _BOUNDED_INTAKE_TOKEN_RE`'s docstring already establishes: not a claim
#: the matched token classifies the SAME interface the node models, only
#: that the node's bound code contains real evidence of a classification
#: construct.
_INTERFACE_CLASSIFICATION_TOKEN_RE = re.compile(
    r"(trusted|untrusted|read_only|readonly|read_write|seccomp|"
    r"capability|syscall_filter|allowlist|denylist|classif)",
    re.IGNORECASE,
)

#: Regex proving a real cgroup/resource-limit-shaped token in bound
#: source text (REL393) -- deliberately narrow, matching common
#: process-resource-bound shapes: a cgroup controller file/limit
#: (`cgroup`, `cpu.max`, `memory.max`, `memory.limit`, `io.max`), a
#: process-level rlimit call (`setrlimit`, `rlimit`, `RLIMIT_`), or a
#: literal `cgroup_bounds`/`resource_limit` identifier. Same honesty line
#: as `_INTERFACE_CLASSIFICATION_TOKEN_RE` above: not a claim the matched
#: token bounds the SAME process the node models, only that the node's
#: bound code contains real evidence of a resource-bounding construct.
_PROCESS_BOUNDS_TOKEN_RE = re.compile(
    r"(cgroup|cpu\.max|memory\.max|memory\.limit|io\.max|setrlimit|"
    r"rlimit|RLIMIT_|resource_limit)",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel39x-kernel-interface--process-bounds-t-0960
class ProcessBoundsViolation(BaseModel):
    """One REL39x finding: rule id, the node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-node (module
    docstring: at most one finding per rule per node), the same bare-rule
    waiver carve-out REL260/REL261 and REL310/REL311 use. Mirrors
    `_backpressure.py::BackpressureViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel39x-kernel-interface--process-bounds-t-0960
class ProcessBoundsReport(BaseModel):
    """Every UNWAIVED REL39x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_backpressure.py::BackpressureReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[ProcessBoundsViolation, ...] = ()
    waived: tuple[ProcessBoundsViolation, ...] = ()


def _is_kernel_interface(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the `kernel_interface` marker --
    the REL390/REL391 population."""
    return _KERNEL_INTERFACE_ATTR in attrs


def _is_interface_classified(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `interface_classified`
    marker."""
    return _INTERFACE_CLASSIFIED_ATTR in attrs


def _is_deployed_process(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the `deployed_process` marker --
    the REL392/REL393 population."""
    return _DEPLOYED_PROCESS_ATTR in attrs


def _has_cgroup_bounds(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `cgroup_bounds`
    marker."""
    return _CGROUP_BOUNDS_ATTR in attrs


def _missing_interface_classification_violations(
    model: KernelModel,
) -> list[ProcessBoundsViolation]:
    """REL390: every `kernel_interface` node with no `interface_classified`
    attr."""
    violations: list[ProcessBoundsViolation] = []
    for node in model.nodes:
        if not _is_kernel_interface(node.attrs) or _is_interface_classified(node.attrs):
            continue
        _log.warning(
            "process_bounds: REL390 node %s touches a kernel/userspace "
            "interface with no classification declared",
            node.id,
        )
        violations.append(
            ProcessBoundsViolation(
                rule=REL_MISSING_INTERFACE_CLASSIFICATION,
                node=node.id,
                detail=(
                    f"node {node.id} touches a kernel/userspace interface "
                    "(syscall/procfs/sysfs/ioctl) with no declared "
                    "classification (no `interface_classified` attr) -- an "
                    "unclassified kernel/userspace interface has no "
                    "declared trust boundary"
                ),
            )
        )
    return violations


def _unproven_interface_classification_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[ProcessBoundsViolation]:
    """REL391: every `kernel_interface` node declaring
    `interface_classified` with bound code, but whose bound code carries no
    real classification-shaped token (PROVABILITY CONSTRAINT). Mirrors
    `_backpressure.py::_unproven_bounded_intake_violations` exactly,
    parameterized on `_INTERFACE_CLASSIFICATION_TOKEN_RE`."""
    violations: list[ProcessBoundsViolation] = []
    for node in model.nodes:
        if not _is_kernel_interface(node.attrs) or not _is_interface_classified(
            node.attrs
        ):
            continue
        if not node_has_bound_code(node.id, owner_by_node):
            continue
        if files_evidence_token(
            owner_by_node[node.id], root, _INTERFACE_CLASSIFICATION_TOKEN_RE
        ):
            continue
        _log.warning(
            "process_bounds: REL391 node %s declares interface_classified "
            "but bound code has no real classification token",
            node.id,
        )
        violations.append(
            ProcessBoundsViolation(
                rule=REL_UNPROVEN_INTERFACE_CLASSIFICATION,
                node=node.id,
                detail=(
                    f"node {node.id} declares interface_classified, but its "
                    "bound code has no real classification token "
                    "(proof-against-code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _missing_process_bounds_violations(
    model: KernelModel,
) -> list[ProcessBoundsViolation]:
    """REL392: every `deployed_process` node with no `cgroup_bounds`
    attr."""
    violations: list[ProcessBoundsViolation] = []
    for node in model.nodes:
        if not _is_deployed_process(node.attrs) or _has_cgroup_bounds(node.attrs):
            continue
        _log.warning(
            "process_bounds: REL392 node %s is a deployed process with no "
            "resource bounds declared",
            node.id,
        )
        violations.append(
            ProcessBoundsViolation(
                rule=REL_MISSING_PROCESS_BOUNDS,
                node=node.id,
                detail=(
                    f"node {node.id} is a deployed process with no "
                    "resource-bound obligation (no `cgroup_bounds` attr) -- "
                    "an unbounded deployed process can consume unbounded "
                    "host cpu/memory/io"
                ),
            )
        )
    return violations


def _unproven_process_bounds_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[ProcessBoundsViolation]:
    """REL393: every `deployed_process` node declaring `cgroup_bounds` with
    bound code, but whose bound code carries no real cgroup/resource-limit
    -shaped token (PROVABILITY CONSTRAINT). Mirrors `_backpressure.py::
    _unproven_bounded_intake_violations` exactly, parameterized on
    `_PROCESS_BOUNDS_TOKEN_RE`."""
    violations: list[ProcessBoundsViolation] = []
    for node in model.nodes:
        if not _is_deployed_process(node.attrs) or not _has_cgroup_bounds(node.attrs):
            continue
        if not node_has_bound_code(node.id, owner_by_node):
            continue
        if files_evidence_token(owner_by_node[node.id], root, _PROCESS_BOUNDS_TOKEN_RE):
            continue
        _log.warning(
            "process_bounds: REL393 node %s declares cgroup_bounds but "
            "bound code has no real resource-bound token",
            node.id,
        )
        violations.append(
            ProcessBoundsViolation(
                rule=REL_UNPROVEN_PROCESS_BOUNDS,
                node=node.id,
                detail=(
                    f"node {node.id} declares cgroup_bounds, but its bound "
                    "code has no real resource-bound token (proof-against-code, "
                    "T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_process_bounds_waivers(
    model: KernelModel, violations: list[ProcessBoundsViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_backpressure.py::_apply_backpressure_waivers`'s pattern reused for
    the REL39x family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in PROCESS_BOUNDS_RULES,
    )


# frob:doc docs/strata/reliability.md#rel39x-kernel-interface--process-bounds-t-0960
# frob:ticket T-0960
# frob:enforces SDC-13-EVERY-KERNEL-USERSPACE-INTERFACE-SYSCALL-PROCFS-SYSFS-ENTRY-IOCTL-IS-CLASSIFIED-INT  # noqa: E501
# frob:enforces SDC-13-EVERY-DEPLOYED-PROCESS-DECLARES-ITS-RESOURCE-BOUNDS-CGROUP-LIMITS-CPU-MEMORY-IO-AND  # noqa: E501
# frob:enforces CHK-GATE-REL390
# frob:enforces CHK-GATE-REL391
# frob:enforces CHK-GATE-REL392
# frob:enforces CHK-GATE-REL393
# frob:tests tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification.test_kernel_interface_node_without_classification_fires  # noqa: E501
def check_process_bounds_obligations(
    model: KernelModel, root: Path
) -> Result[ProcessBoundsReport, StrataError]:
    """The REL39x KERNEL-INTERFACE-CLASSIFICATION + PROCESS-RESOURCE-BOUND
    obligations entrypoint (T-0960): REL390/REL391 (kernel/userspace
    interface classification, missing then unproven) and REL392/REL393
    (deployed-process cgroup resource bounds, missing then unproven)
    across every relevant node in `model`, waivers already applied. `root`
    is the repo root `_code_binding.py::bind_code` binds against -- `Err`
    propagates `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by
    default, the same discipline `check_backpressure_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[ProcessBoundsViolation] = []
    violations.extend(_missing_interface_classification_violations(model))
    violations.extend(
        _unproven_interface_classification_violations(model, owner_by_node, root)
    )
    violations.extend(_missing_process_bounds_violations(model))
    violations.extend(_unproven_process_bounds_violations(model, owner_by_node, root))
    applied = _apply_process_bounds_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = stale_relwaive_violations(applied.stale, ProcessBoundsViolation)
    _log.info(
        "process_bounds: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(
        ProcessBoundsReport(violations=tuple(applied.kept) + stale, waived=waived)
    )


__all__ = [
    "PROCESS_BOUNDS_RULES",
    "REL_MISSING_INTERFACE_CLASSIFICATION",
    "REL_MISSING_PROCESS_BOUNDS",
    "REL_UNPROVEN_INTERFACE_CLASSIFICATION",
    "REL_UNPROVEN_PROCESS_BOUNDS",
    "ProcessBoundsReport",
    "ProcessBoundsViolation",
    "check_process_bounds_obligations",
]
