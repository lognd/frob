"""frob self-conformance: reconcile OUR OWN `src/frob/` capability surface
against the interfaces `design/frob.strata` declares (T-0150,
docs/strata/selfconform.md).

POST-REVIEW REWORK (T-0150 REJECT round): the first version of this
module invented a parallel `frob.toml` node<->path/node<->capability
mapping, on the mistaken belief that `code=`/`may` were not reachable
from `.strata` surface text. They ARE (T-0132, `strata-core/src/parse.rs`
`code STRING+` / `may STRING`, `_elaborate.py::_elaborate_node` maps them
straight onto `Node.attrs`'s `code=<glob>` convention and `Node.may`) --
`design/frob.strata`'s own header comment was simply stale and has been
corrected as part of this rework. This module is now a THIN layer: it
declares `code "..."`/`may "..."` directly on `design/frob.strata`'s
nodes (measured honestly from a real `scan_file_capabilities` sweep, same
numbers as the original version) and reuses the ALREADY-SHIPPED
`bind_code` (T-0078) + `check_capability_conformance`/THREAT004 (T-0079/
T-0113) machinery wherever it already expresses one of this ticket's three
rules. Only what that machinery genuinely cannot express gets new code
here, each with a written gap statement:

SYS100 undeclared interface -- a capability OBSERVED in a node's
`code=`-bound files but not DECLARED in that node's `may` atoms.
  - net/fs-write/exec: DELEGATED to `check_capability_conformance`
    (THREAT004) verbatim, just relabeled SYS100 -- that function already
    computes exactly this join at file:line granularity via `_effects.py`'s
    `_KIND_MAP`/`_line_effects`, zero new detection.
  - eval/env/ffi/install-hook: NEW code (`_extended_kind_violations`).
    GAP STATEMENT: `_effects.py::_KIND_MAP` is scoped (by its own
    docstring, T-0079) to net/fs-write/exec only -- "eval/env/ffi/
    install-hook are vet-specific dependency-vetting signals with no
    `may`-capability analog yet" -- so THREAT004 structurally cannot see
    these four kinds no matter what `may` declares. `scan_file_
    capabilities` (vet's own per-file scanner, already imported
    READ-ONLY by `_effects.py` for the other three kinds) is reused
    directly for these four, at file granularity, joined against
    `Node.may` via `_effects.py::_declared_kinds` (reused, not
    reimplemented).

SYS101 stale design -- a capability DECLARED in a node's `may` atoms with
zero observed sites anywhere in that node's `code=`-bound files. NEW code
for ALL kinds. GAP STATEMENT: neither `check_capability_conformance` nor
any other shipped join checks this direction -- THREAT004's `_effects.py`
module docstring is explicit that "an observed effect with no matching
`may` declaration is a violation... not a silent pass" is the ONLY
direction it discharges; a declared-but-unexercised capability is not a
concept the tier-2 machinery has ever computed. `check_effect_
completeness`'s own docstring (`_threat.py`) confirms this: THREAT004 is
"the code-level `undeclared capability in code is an error` kicker",
singular direction.

SYS102 unmodeled code -- a `src/frob/` top-level directory whose `.py`
files are ALL bound to `FOREIGN` (or entirely absent from `bind_code`'s
partition) -- i.e. no node's `code=` glob claims it at all. NEW code.
GAP STATEMENT: `bind_code` computes the FOREIGN bucket but nothing
downstream currently treats "this directory is entirely FOREIGN" as a
reportable finding; `check_import_conformance` explicitly SKIPS FOREIGN
files ("an unclassified file names no kernel node to attest the
crossing against") rather than flagging them, which is correct for ITS
rule (imports) but leaves "a whole directory has no owner" unraised
anywhere -- exactly the gap this ticket asked SYS102 to close.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.excludes import is_skipped_dir
from frob.logging import get_logger
from frob.vet._capability import scan_file_capabilities

from ._code_binding import FOREIGN, CodeBinding, bind_code
from ._effects import _KIND_MAP, _declared_kinds, check_capability_conformance
from ._errors import StrataError
from ._models import KernelModel

_log = get_logger(__name__)

# frob:doc docs/strata/selfconform.md#the-three-rules
#: `frob sys audit` rule id for SYS100 undeclared interface: a capability
#: observed in a node's `code=`-bound files but not declared in `may`.
SYS_UNDECLARED_INTERFACE = "SYS100"
# frob:doc docs/strata/selfconform.md#the-three-rules
#: `frob sys audit` rule id for SYS101 stale design: a `may` capability
#: declared for a node but never observed in its `code=`-bound files.
SYS_STALE_DESIGN = "SYS101"
# frob:doc docs/strata/selfconform.md#the-three-rules
#: `frob sys audit` rule id for SYS102 unmodeled code: a `src/frob/`
#: directory whose files are all `FOREIGN` to `bind_code`'s partition.
SYS_UNMODELED_CODE = "SYS102"

#: `src/` subtree self-conformance actually scans -- our own package root
#: (module docstring: `design/frob.strata` models exactly this one tree).
_PACKAGE_ROOT = "src/frob"

#: The four vet capability kinds THREAT004's `_effects.py::_KIND_MAP` has
#: no tier-2 analog for (module docstring's SYS100 gap statement) -- the
#: ONLY kinds this module's own file-level scan needs to cover, since
#: net/fs-write/exec are fully delegated to `check_capability_conformance`.
_EXTENDED_KINDS = frozenset({"eval", "env", "ffi", "install-hook"})


# frob:doc docs/strata/selfconform.md#the-three-rules
class SelfConformViolation(BaseModel):
    """One SYS100/SYS101/SYS102 finding: rule id, the node (or directory,
    for SYS102) it concerns, and a human-readable detail string."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str


# frob:doc docs/strata/selfconform.md#the-three-rules
class SelfConformReport(BaseModel):
    """Every self-conformance violation found, in rule-then-node order
    (module docstring)."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[SelfConformViolation, ...] = ()


def _core_undeclared_violations(
    model: KernelModel, binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """SYS100 for net/fs-write/exec, delegated verbatim to THREAT004's
    `check_capability_conformance` -- zero new detection (module
    docstring's SYS100 core case)."""
    conformance = check_capability_conformance(model, binding, root)
    found = []
    for violation in conformance.violations:
        _log.warning(
            "selfconform: SYS100 (via THREAT004) %s:%d %s effect on %s",
            violation.file,
            violation.line,
            violation.kind,
            violation.component,
        )
        found.append(
            SelfConformViolation(
                rule=SYS_UNDECLARED_INTERFACE,
                node=violation.component,
                detail=(
                    f"capability {violation.kind!r} observed at "
                    f"{violation.file}:{violation.line} but not declared"
                ),
            )
        )
    return found


def _sorted_owned_files(binding: CodeBinding) -> list[str]:
    """Every non-`FOREIGN` bound file path, in deterministic order
    (mirrors `_effects.py::_sorted_owned_files`)."""
    return sorted(rel for rel, owner in binding.owner.items() if owner != FOREIGN)


def _observed_extended_kinds_by_node(
    binding: CodeBinding, root: Path
) -> dict[str, frozenset[str]]:
    """Every node id -> the union of `_EXTENDED_KINDS` capabilities
    `scan_file_capabilities` observes across that node's `code=`-bound
    files (module docstring's SYS100 extended case)."""
    per_node: dict[str, set[str]] = {}
    for rel in _sorted_owned_files(binding):
        owner = binding.owner[rel]
        found = scan_file_capabilities(root / rel) & _EXTENDED_KINDS
        if found:
            per_node.setdefault(owner, set()).update(found)
    return {node_id: frozenset(kinds) for node_id, kinds in per_node.items()}


def _observed_all_kinds_by_node(
    binding: CodeBinding, root: Path
) -> dict[str, frozenset[str]]:
    """Every node id -> the union of ALL vet capability kinds observed
    across its bound files, net/fs-write/exec normalized through
    `_effects.py::_KIND_MAP` to the SAME kind spelling `may` declarations
    use ("fs" not "fs-write") -- SYS101's observed side, which (unlike
    SYS100) needs the full vocabulary regardless of THREAT004's scope."""
    per_node: dict[str, set[str]] = {}
    for rel in _sorted_owned_files(binding):
        owner = binding.owner[rel]
        raw = scan_file_capabilities(root / rel)
        normalized = {_KIND_MAP.get(kind, kind) for kind in raw}
        if normalized:
            per_node.setdefault(owner, set()).update(normalized)
    return {node_id: frozenset(kinds) for node_id, kinds in per_node.items()}


def _extended_kind_violations(
    model: KernelModel, binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """SYS100 for eval/env/ffi/install-hook -- the one slice
    `check_capability_conformance` structurally cannot see (module
    docstring's SYS100 gap statement)."""
    observed_by_node = _observed_extended_kinds_by_node(binding, root)
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        declared = _declared_kinds(node) & _EXTENDED_KINDS
        observed = observed_by_node.get(node.id, frozenset())
        # frob:waive PERF004 reason="distinct small per-node diff set, not repeated"
        for kind in sorted(observed - declared):
            _log.warning(
                "selfconform: SYS100 (extended) %s observed but undeclared on %s",
                kind,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_UNDECLARED_INTERFACE,
                    node=node.id,
                    detail=f"capability {kind!r} observed but not declared",
                )
            )
    return found


def _stale_design_violations(
    model: KernelModel, binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """SYS101 over every kind (net/fs/exec included) -- new code, since no
    shipped join checks this direction (module docstring's SYS101 gap
    statement)."""
    observed_by_node = _observed_all_kinds_by_node(binding, root)
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        declared = _declared_kinds(node)
        observed = observed_by_node.get(node.id, frozenset())
        # frob:waive PERF004 reason="distinct small per-node diff set, not repeated"
        for kind in sorted(declared - observed):
            _log.warning(
                "selfconform: SYS101 %s declared but never observed on %s",
                kind,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_STALE_DESIGN,
                    node=node.id,
                    detail=f"capability {kind!r} declared but never observed",
                )
            )
    return found


def _top_level_dirs(root: Path) -> list[str]:
    """Every immediate, non-skipped subdirectory name of `root / _PACKAGE_ROOT`
    (module docstring's SYS102 unit of "unmodeled code"), in sorted order."""
    package_root = root / _PACKAGE_ROOT
    if not package_root.is_dir():
        _log.warning("selfconform: %s does not exist", package_root)
        return []
    return sorted(
        entry.name
        for entry in package_root.iterdir()
        if entry.is_dir() and not is_skipped_dir(entry.name)
    )


def _unmodeled_violations(
    root: Path, binding: CodeBinding
) -> list[SelfConformViolation]:
    """SYS102: every top-level `src/frob/` directory whose files (if any)
    are ALL `FOREIGN` to `bind_code`'s partition -- no node's `code=`
    glob claims it at all (module docstring's SYS102 gap statement)."""
    prefix_owned: set[str] = set()
    # frob:waive PERF003 reason="ownership loop, separate dirs loop below, not a join"
    for rel, owner in binding.owner.items():
        if owner == FOREIGN or not rel.startswith(f"{_PACKAGE_ROOT}/"):
            continue
        top = rel[len(_PACKAGE_ROOT) + 1 :].split("/", 1)[0]
        prefix_owned.add(top)

    found: list[SelfConformViolation] = []
    for name in _top_level_dirs(root):
        if name in prefix_owned:
            continue
        _log.warning("selfconform: SYS102 unmodeled code src/frob/%s", name)
        found.append(
            SelfConformViolation(
                rule=SYS_UNMODELED_CODE,
                node=name,
                detail=f"src/frob/{name} has no node's code= glob binding it",
            )
        )
    return found


# frob:doc docs/strata/selfconform.md#the-three-rules
def check_self_conformance(
    model: KernelModel, root: Path
) -> Result[SelfConformReport, StrataError]:
    """The `frob sys audit` self-conformance entrypoint (T-0150): `bind_code`
    (T-0078, reused verbatim) partitions `src/frob/` by each node's `code=`
    glob, then SYS100/SYS101/SYS102 reconcile that partition against
    `Node.may` (module docstring: SYS100's net/fs-write/exec slice
    delegates to THREAT004 outright; the rest is new code with a written
    gap statement each). `Err` propagates `bind_code`'s
    `AmbiguousCodeBinding` unchanged -- deny by default, never a silent
    partial scan."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    binding = bound.danger_ok

    violations = _core_undeclared_violations(model, binding, root)
    violations.extend(_extended_kind_violations(model, binding, root))
    violations.extend(_stale_design_violations(model, binding, root))
    violations.extend(_unmodeled_violations(root, binding))

    _log.info("selfconform: %d violation(s) found under %s", len(violations), root)
    return Ok(SelfConformReport(violations=tuple(violations)))


__all__ = [
    "SYS_STALE_DESIGN",
    "SYS_UNDECLARED_INTERFACE",
    "SYS_UNMODELED_CODE",
    "SelfConformReport",
    "SelfConformViolation",
    "check_self_conformance",
]
