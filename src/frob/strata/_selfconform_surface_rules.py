"""SYS105/SYS108/SYS110 rule family (T-2729 layer 2, split out of
`_selfconform.py`): purpose contract, duplicate interface declaration,
and undeclared intended surface -- the "declared public surface" trio.
See `_selfconform.py`'s own module docstring for the full design
narrative; this module holds only the code."""

from __future__ import annotations

import ast
from pathlib import Path

from frob.logging import get_logger

from ._code_binding import CodeBinding
from ._models import KernelModel
from ._selfconform_ids import (
    SYS110_UNAUDITED_NODES,
    SYS_DUPLICATE_INTERFACE,
    SYS_PURPOSE_CONTRACT,
    SYS_UNDECLARED_INTENDED_SURFACE,
)
from ._selfconform_kinds import _node_attr_values
from ._selfconform_models import SelfConformViolation

_log = get_logger(__name__)


#: Node attr prefix for a SYS104 (T-0668) declared-interface entry (one
#: attr per declared public symbol name), mirroring `_code_binding.py`'s
#: `code=<glob>` attr-string convention (module docstring's SYS104
#: section).
# frob:ticket T-2729
_INTERFACE_PREFIX = "interface="

#: Node attr prefix for a SYS105 (T-0669) declared purpose profile (at
#: most one per node), same opaque-attr convention.
# frob:ticket T-2729
_PURPOSE_PREFIX = "purpose="

#: SYS105's fixed, closed allowed-effect-profile vocabulary (module
#: docstring's SYS105 section): profile name -> the set of observed effect
#: kinds (the SAME normalized vocabulary `_observed_all_kinds_by_node`
#: yields) that profile permits. `"full"` is the explicit opt-out --
#: still requires declaring a purpose (so a node cannot hide behind
#: silence), but permits every observed kind.
# frob:ticket T-2729
_PURPOSE_PROFILES: dict[str, frozenset[str] | None] = {
    "pure": frozenset(),
    "read-only": frozenset({"fs.read", "net.connect", "env.read"}),
    "logging": frozenset({"fs.write"}),
    "network": frozenset({"net.connect", "net.listen", "fetch_url"}),
    "full": None,  # None = no restriction (explicit opt-out)
}


# frob:ticket T-2729
def _module_public_symbols(path: Path) -> frozenset[str] | None:
    """The real top-level public symbol set of one `.py` file: `__all__`'s
    string-literal entries if the module declares one, else every
    non-underscore-prefixed module-level `def`/`class`/plain-assignment
    target name. `None` on a parse failure (deny-by-default: the caller
    treats an unparseable file as contributing nothing rather than
    crashing the whole SYS104 pass, same posture `_parse_ast` establishes
    in `_code_binding.py`)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, OSError, UnicodeDecodeError) as exc:
        _log.warning("selfconform: SYS104 could not parse %s: %s", path, exc)
        return None
    all_literal = _module_all_literal(tree)
    if all_literal is not None:
        return all_literal
    names: set[str] = set()
    for stmt in tree.body:
        names |= _public_names_of_statement(stmt)
    return frozenset(names)


# frob:ticket T-2729
def _module_all_literal(tree: ast.Module) -> frozenset[str] | None:
    """`__all__`'s string-literal entries if `tree` assigns it a plain
    list/tuple of string constants at module level, else `None` (no
    `__all__`, or one this static pass cannot resolve -- falls back to
    name-based public-symbol collection, never crashes)."""
    for stmt in tree.body:
        if not (
            isinstance(stmt, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "__all__" for t in stmt.targets)
        ):
            continue
        if not isinstance(stmt.value, (ast.List, ast.Tuple)):
            return None
        names: set[str] = set()
        for elt in stmt.value.elts:
            if not (isinstance(elt, ast.Constant) and isinstance(elt.value, str)):
                return None
            names.add(elt.value)
        return frozenset(names)
    return None


# frob:ticket T-2729
def _public_names_of_statement(stmt: ast.stmt) -> frozenset[str]:
    """The public (non-underscore-prefixed) top-level name(s) one module
    body statement introduces -- `def`/`class`/plain assignment targets --
    split out of `_module_public_symbols` purely to keep its loop body
    short."""
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return frozenset({stmt.name}) if not stmt.name.startswith("_") else frozenset()
    if isinstance(stmt, ast.Assign):
        return frozenset(
            t.id
            for t in stmt.targets
            if isinstance(t, ast.Name) and not t.id.startswith("_")
        )
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        name = stmt.target.id
        return frozenset({name}) if not name.startswith("_") else frozenset()
    return frozenset()


# frob:ticket T-2729
def _node_real_public_surface(
    binding: CodeBinding, root: Path, node_id: str
) -> frozenset[str]:
    """The union of `_module_public_symbols` across every `.py` file
    `binding` binds to `node_id` -- the full ground-truth exported surface
    (SYS110's own notion of "real", `_undeclared_intended_surface_
    violations`). T-3523: SYS104 used to narrow this further via the now-
    deleted `_cross_node_referenced_symbols` (T-1625) before comparing
    against a node's declared `interface=` set -- this function was
    deliberately UNCHANGED by that narrowing even then, so its own
    contract is unaffected by SYS104's T-1870 removal."""
    surface: set[str] = set()
    for rel in sorted(binding.owner):
        if binding.owner[rel] != node_id or not rel.endswith(".py"):
            continue
        found = _module_public_symbols(root / rel)
        if found is not None:
            surface |= found
    return frozenset(surface)


# T-1870: SYS104 (`_interface_conformance_violations`, T-0668) used to
# live here -- deleted along with its writer (`frob.strata.
# _sync_interface`, T-1150) per an explicit owner directive that no code
# path may auto-update declared public-symbol surface. `_node_real_
# public_surface` and `_INTERFACE_PREFIX` (both still defined in this
# module) survive because SYS110 also depends on them
# (`_undeclared_intended_surface_violations` below) -- only the SYS104
# check function and its call site are gone.
#
# T-3523: SYS104's OWN narrowing helpers -- `_imported_from_spec`,
# `_src_root_prefixes`, `_resolve_cross_package_import`, and
# `_cross_node_referenced_symbols` itself -- had exactly one caller
# each, all the way up to `_cross_node_referenced_symbols`, which SYS104
# alone consumed. A T-1870-era comment here claimed they "survive
# because SYS106 and SYS108 also depend on them"; that was never true
# for `_cross_node_referenced_symbols` (grep confirms zero callers in
# this repo, T-3523's own measurement) and is only true for `_node_
# real_public_surface` above via SYS110, not SYS106/SYS108 -- SYS106
# (`_selfconform_binding_rules.py::_binding_totality_violations`) is a
# self-contained reachability walk over `resolve_local_import` that
# never touches either helper, and SYS108
# (`_duplicate_interface_violations`) only reads `_node_attr_values`.
# Deleted the four now-provably-dead functions rather than building a
# SYS106 consumer for them -- SYS106 already does its job without them.
# frob:waive COV007 reason="T-2729: this private helper's frob:doc anchor predates \
# this ticket -- same T-0524/T-0529/T-1636 per-function architecture-doc precedent \
# every other COV007 waiver in this repo already carries, not accidental drift onto a \
# private symbol introduced by this move"
# frob:doc docs/strata/surface.md#compact-interface-attrs-t-1198
# frob:enforces CHK-GATE-SYS108
# frob:tests tests/unit/strata/test_selfconform.py::TestDuplicateInterface.test_duplicate_symbol_fires  # noqa: E501
# frob:tests tests/unit/strata/test_selfconform.py::TestDuplicateInterface.test_no_duplicates_silent  # noqa: E501
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
def _duplicate_interface_violations(model: KernelModel) -> list[SelfConformViolation]:
    """SYS108 (T-1624): a node whose `interface=` attrs (module attrs
    preserve every declared entry verbatim, `_node_attr_values`) name the
    same symbol more than once -- the exact shape two byte-identical
    `attr interface=[...]` blocks on one node elaborate into (module
    docstring's SYS108 section). Pure text/model check, needs no code
    binding at all."""
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        declared = _node_attr_values(node, _INTERFACE_PREFIX)
        seen: set[str] = set()
        dupes: set[str] = set()
        for name in declared:
            if name in seen:
                dupes.add(name)
            seen.add(name)
        # frob:waive PERF004 reason="dupes is THIS node's own distinct set (a \
        # different value every time the outer node loop advances), sorted only for \
        # deterministic WARNING log ordering -- not a repeated re-sort of identical \
        # data across iterations"
        for name in sorted(dupes):
            _log.warning(
                "selfconform: SYS108 duplicate interface symbol %s on %s",
                name,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_DUPLICATE_INTERFACE,
                    node=node.id,
                    detail=(
                        f"interface= declares {name!r} more than once "
                        "-- duplicate attr interface= block"
                    ),
                    capability=name,
                )
            )
    return found


# frob:waive COV007 reason="T-2729: this private helper's frob:doc anchor predates \
# this ticket -- same T-0524/T-0529/T-1636 per-function architecture-doc precedent \
# every other COV007 waiver in this repo already carries, not accidental drift onto a \
# private symbol introduced by this move"
# frob:ticket T-1629
# frob:doc docs/strata/surface.md#sys110-undeclared-intended-surface-t-1629
# frob:enforces CHK-GATE-SYS110
# frob:enforces SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE
# frob:tests tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface.test_real_symbol_outside_declared_set_fires  # noqa: E501
# frob:tests tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface.test_declared_superset_is_silent  # noqa: E501
# frob:tests tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface.test_node_with_no_interface_attrs_is_skipped  # noqa: E501
# frob:waive AFFECT001 reason="T-2729: LARGE001 split of _selfconform.py by SYS1xx \
# rule family -- this symbol only moved to a sibling module verbatim (same name, same \
# body/signature), no behavior change, so the affects()-closure doc it names needs no \
# update"
# frob:ticket T-2729
def _undeclared_intended_surface_violations(
    model: KernelModel, binding: CodeBinding, root: Path
) -> list[SelfConformViolation]:
    """SYS110 (T-1629): for every node that has opted into hand-declared
    `interface=` intent (`_node_attr_values` returns at least one entry),
    any symbol in its REAL public surface (`_node_real_public_surface`,
    unchanged from SYS104's era) that is NOT named in that declared set is
    a violation -- module docstring's SYS110 section for the full
    intent-vs-mirror rationale and the deliberate phased-migration skip
    for a node with zero `interface=` attrs (not yet opted in, not
    "declares an empty surface"). Also skips any node named in
    `SYS110_UNAUDITED_NODES` -- a node whose pre-T-1629 `interface=` block
    is a stale, un-audited mirror rather than hand-curated intent (that
    frozenset's own docstring)."""
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        if node.id in SYS110_UNAUDITED_NODES:
            continue
        declared = frozenset(_node_attr_values(node, _INTERFACE_PREFIX))
        if not declared:
            continue
        real = _node_real_public_surface(binding, root, node.id)
        # frob:waive PERF004 reason="real - declared is THIS node's own distinct set \
        # (a different value every time the outer node loop advances), sorted only for \
        # deterministic WARNING log ordering -- not a repeated re-sort of identical \
        # data across iterations"
        for symbol in sorted(real - declared):
            _log.warning(
                "selfconform: SYS110 undeclared public symbol %s on %s",
                symbol,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_UNDECLARED_INTENDED_SURFACE,
                    node=node.id,
                    detail=(
                        f"{symbol} is public in code but not declared in this "
                        "node's interface= (hand-declared intent, T-1629) -- "
                        "add `attr interface=" + symbol + "` if this is really "
                        "part of the contract, or make the symbol private"
                    ),
                    capability=symbol,
                )
            )
    return found


# frob:tests tests/unit/strata/test_selfconform.py::TestPurposeContract.test_effect_outside_profile_fires  # noqa: E501
# frob:tests tests/unit/strata/test_selfconform.py::TestPurposeContract.test_unrecognized_profile_fires  # noqa: E501
# frob:ticket T-2729
def _purpose_contract_violations(
    model: KernelModel, observed_by_node: dict[str, frozenset[str]]
) -> list[SelfConformViolation]:
    """SYS105 (T-0669): for every node declaring a `purpose=` attr, every
    observed effect kind must lie inside that profile's allowed set
    (`_PURPOSE_PROFILES`, module docstring's SYS105 section). An
    unrecognized profile name is itself a finding -- a typo must not read
    as a silently-permissive `"full"`."""
    found: list[SelfConformViolation] = []
    for node in model.nodes:
        declared = _node_attr_values(node, _PURPOSE_PREFIX)
        if not declared:
            continue  # SYS105 scope cut: opt-in only, see module docstring
        profile = declared[0]
        allowed = _PURPOSE_PROFILES.get(profile)
        if profile not in _PURPOSE_PROFILES:
            _log.warning(
                "selfconform: SYS105 unrecognized purpose profile %r on %s",
                profile,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_PURPOSE_CONTRACT,
                    node=node.id,
                    detail=f"purpose={profile!r} is not a recognized profile",
                )
            )
            continue
        if allowed is None:
            continue  # "full" -- explicit opt-out, no restriction
        observed = observed_by_node.get(node.id, frozenset())
        # frob:waive PERF004 reason="observed - allowed is THIS node's own distinct \
        # set (a different value every time the outer node loop advances), sorted only \
        # for deterministic WARNING log ordering -- not a repeated re-sort of \
        # identical data across iterations"
        for kind in sorted(observed - allowed):
            _log.warning(
                "selfconform: SYS105 %s effect outside purpose=%s on %s",
                kind,
                profile,
                node.id,
            )
            found.append(
                SelfConformViolation(
                    rule=SYS_PURPOSE_CONTRACT,
                    node=node.id,
                    detail=(
                        f"effect {kind!r} observed outside purpose={profile!r}'s "
                        "allowed profile"
                    ),
                    capability=kind,
                )
            )
    return found
