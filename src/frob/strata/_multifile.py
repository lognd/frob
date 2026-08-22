"""Cross-file reference resolution for a multi-file `.strata` design (T-1196).

`_design_load.py` (T-0080) already rglobs and parses every `.strata` file
under `design/`, but historically elaborated each file's `Module` on its
own (`elaborate()` runs `require_analyzable`/duplicate/unknown-reference
checks against ONE file's declarations) and only merged the resulting
`KernelModel`s' facts AFTER elaboration (`frob.strata._sysdoc.merge_models`,
concatenation of already-elaborated fields). That ordering means a `flow`
in file B referencing a `node` declared only in file A could never resolve:
elaborate(B) sees no such node and fails closed, even though the id exists
in the loaded design as a whole.

Architecture decision (T-1196, coordinated with T-1198): merge the PARSED
`Module`s together before elaboration, then elaborate the combined result
ONCE. This was chosen over an explicit import/include surface-grammar
construct because it needs zero grammar changes (a `Module` is already
just a flat bag of declaration tuples, `_ast.py::Module`), reuses
`elaborate()`'s existing duplicate-id/unknown-reference validation
unmodified, and generalizes directly to T-1198's generated-fragment
design (a generated `.strata` file is just one more `Module` in the same
merge). The tradeoff, accepted here: a cross-declaration validation error
(duplicate id, unknown reference) coming out of the merged `elaborate()`
call names the id but not, on its own, which loaded file introduced it --
`check_cross_file_references` below closes exactly that gap for the two
reference shapes elaborate would otherwise reject blind (flow src/dst,
boundary flow_id), by checking them per-file BEFORE the merge, while ids
are still file-tagged.
"""
# frob:ticket T-1196

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from typani import Err, Ok, Result

from ._ast import ExtendNodeDecl, MayGrantDecl, Module, NodeDecl
from ._elaborate import _known_node_ids, elaborate
from ._errors import StrataError
from ._models import KernelModel

#: One `.strata` file's relative path paired with its parsed `Module`, the
#: unit `check_cross_file_references`/`merge_modules` operate over -- kept
#: as a plain tuple (not a dataclass) since both are one-shot pure
#: functions with no state of their own.
FileModule = tuple[str, Module]


# frob:doc docs/strata/surface.md#multi-file-design-load-cross-file-references-t-1196
@dataclass(frozen=True)
class CrossFileError:
    """One cross-file reference fault: `path` is the file whose declaration
    used the missing id, `message` names the id and the referencing
    construct -- T-1196 acceptance 1 requires failing closed with a
    per-file error naming the missing id, never a silent partial model."""

    path: str
    message: str
    #: The underlying `StrataError` kind, so a caller (`_design_load.py`)
    #: can preserve the SAME error taxonomy a single-file `elaborate()`
    #: call would have raised, rather than collapsing every cross-file
    #: fault to one generic code.
    error: StrataError = StrataError.UnknownReference


def _declared_node_ids(files: tuple[FileModule, ...]) -> frozenset[str]:
    """Every node-SHAPED id declared by ANY loaded file -- std.trust nodes
    plus every std.infra construct (store/cache/queue/cdn/balancer/secret),
    reusing `_elaborate._known_node_ids`'s per-file definition so this
    cross-file join never drifts from what a single-file `elaborate()`
    already treats as a valid flow endpoint (`_elaborate.py::
    _known_node_ids` docstring) -- the join `check_cross_file_references`
    checks a `flow`'s `src`/`dst` against."""
    ids: set[str] = set()
    for _, module in files:
        ids |= _known_node_ids(module)
    return frozenset(ids)


def _declared_flow_ids(files: tuple[FileModule, ...]) -> frozenset[str]:
    """Every `flow` id declared by ANY loaded file -- the join
    `check_cross_file_references` checks a `boundary`'s `flow_id` against."""
    return frozenset(flow.id for _, module in files for flow in module.flows)


# frob:doc docs/strata/surface.md#multi-file-design-load-cross-file-references-t-1196
# frob:tests \
# tests/unit/strata/test_multifile.py::TestCheckCrossFileReferences.test_no_errors_when\
# _all_resolve
# frob:tests \
# tests/unit/strata/test_multifile.py::TestCheckCrossFileReferences.test_missing_node_n\
# amed_per_file
# frob:tests \
# tests/unit/strata/test_multifile.py::TestCheckCrossFileReferences.test_boundary_unkno\
# wn_flow_named
def check_cross_file_references(
    files: tuple[FileModule, ...],
) -> tuple[CrossFileError, ...]:
    """Find every `flow`/`boundary` reference naming an id declared in NO
    loaded file, per file, before the merge in `merge_modules` erases which
    file each declaration came from (T-1196 acceptance 1). Runs BEFORE
    elaboration so a missing id is reported with clear file provenance
    even though the merged `Module` elaborate() would validate next no
    longer carries per-file boundaries."""
    node_ids = _declared_node_ids(files)
    flow_ids = _declared_flow_ids(files)
    errors: list[CrossFileError] = []
    for path, module in files:
        for flow in module.flows:
            if flow.src not in node_ids:
                errors.append(
                    CrossFileError(
                        path=path,
                        message=(
                            f"flow {flow.id!r} references unknown node "
                            f"{flow.src!r} (src)"
                        ),
                    )
                )
            if flow.dst not in node_ids:
                errors.append(
                    CrossFileError(
                        path=path,
                        message=(
                            f"flow {flow.id!r} references unknown node "
                            f"{flow.dst!r} (dst)"
                        ),
                    )
                )
        for boundary in module.boundaries:
            if boundary.flow_id not in flow_ids:
                errors.append(
                    CrossFileError(
                        path=path,
                        message=(
                            f"boundary {boundary.id!r} references unknown "
                            f"flow {boundary.flow_id!r}"
                        ),
                    )
                )
    return tuple(errors)


# frob:doc docs/strata/surface.md#fragments-t-2502
# frob:ticket T-2530
# frob:tests \
# tests/unit/strata/test_fragments.py::TestSealedGrantSet.test_widen_on_declared_atom_s\
# till_works
# frob:tests \
# tests/unit/strata/test_fragments.py::TestSealedGrantSet.test_widen_on_undeclared_atom\
# _refuses_closed
# frob:tests \
# tests/unit/strata/test_fragments.py::TestSealedGrantSet.test_fresh_insert_raises_at_r\
# untime
# frob:tests \
# tests/unit/strata/test_fragments.py::TestSealedGrantSet.test_fresh_insert_fails_stati\
# c_type_check
class SealedGrantSet:
    """Per-node capability-grant mapping (atom -> `MayGrantDecl`) whose
    ONLY public mutator is `widen` -- unioning MORE `via` globs onto an
    atom the root ALREADY granted. Inserting a fresh atom is not an
    expressible operation on this type: there is no method, public or
    otherwise, that assigns a NEW key into the underlying mapping, and
    `grants` exposes a `Mapping` (never a `dict`) backed by a real
    `MappingProxyType` -- so `sealed.grants[atom] = grant` is BOTH a
    static type error (`Mapping` has no `__setitem__` in its interface;
    a type checker rejects the assignment before the code ever runs) AND
    a runtime `TypeError` (`mappingproxy` object does not support item
    assignment) for code that ignores the type checker entirely.

    T-2530: this replaces a plain `dict[str, MayGrantDecl]` the merge
    functions used to pass around and mutate directly -- correct only
    because every call site happened to only ever union into an existing
    key (`_widen_node_grants`'s old body), a property the type system
    never enforced. A future `else: node_grants[atom] = grant` edit to
    that dict-based code would have silently turned a fragment into a
    place to grant a capability the root refused; the same edit against
    THIS type does not compile (`grants` is read-only) and there is no
    other attribute to reach for -- moving the guarantee from the test
    suite (T-2502's own tests, still green, now testing a stronger
    contract) into the type system, per this ticket's own charter.

    Construction is likewise restricted: the only way to get one is
    `from_root_node`, called exactly once per node by
    `_seed_grants_by_root_node` against a ROOT `Module`'s own `nodes`
    (never a fragment's) -- a fragment's `extend` statements are folded
    in through `widen` alone, they never construct their own
    `SealedGrantSet`."""

    __slots__ = ("_grants",)

    def __init__(self, grants: dict[str, MayGrantDecl]) -> None:
        """Private in spirit (leading underscore) as well as in practice
        (the constructor argument is a plain `dict`, never exposed again
        after this call) -- `from_root_node` is the one sanctioned
        caller; nothing about this signature stops a determined bypass
        (Python has no true access control), which is the honest limit
        of what this type can guarantee -- see the class docstring's
        `Mapping`/`MappingProxyType` combination for the part that DOES
        hold even against code that tries to bypass convention."""
        self._grants: dict[str, MayGrantDecl] = grants

    # frob:doc docs/strata/surface.md#fragments-t-2502
    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestSealedGrantSet.test_widen_on_declared_at\
    # om_still_works
    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestSealedGrantSet.test_widen_on_undeclared_\
    # atom_refuses_closed
    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestSealedGrantSet.test_fresh_insert_raises_\
    # at_runtime
    @classmethod
    def from_root_node(cls, node: NodeDecl) -> "SealedGrantSet":
        """The ONLY construction path -- one entry per grant the ROOT
        node itself already declared. `_seed_grants_by_root_node` is the
        one caller, and it only ever iterates a resolved ROOT `Module`'s
        `nodes` (T-2502's `resolve_fragments` never passes a fragment's
        `Module` here)."""
        return cls({grant.atom: grant for grant in node.may_grants})

    # frob:doc docs/strata/surface.md#fragments-t-2502
    @property
    def grants(self) -> Mapping[str, MayGrantDecl]:
        """Read-only view of the current atom->grant mapping -- typed and
        backed exactly as the class docstring describes; use `widen` to
        change anything, there is no other way from outside this class."""
        return MappingProxyType(self._grants)

    # frob:doc docs/strata/surface.md#fragments-t-2502
    def widen(self, atom: str, via: tuple[str, ...]) -> bool:
        """Union `via` into the EXISTING grant for `atom`, in place;
        returns `False` and changes nothing if `atom` was never granted
        by the root. This is the sealed type's entire public mutation
        surface -- there is no sibling method that can assign a fresh
        key, by construction of this class, not by convention."""
        existing = self._grants.get(atom)
        if existing is None:
            return False
        widened_via = existing.via + tuple(
            glob for glob in via if glob not in existing.via
        )
        self._grants[atom] = existing.model_copy(update={"via": widened_via})
        return True


def _widen_node_grants(
    path: str, extend: ExtendNodeDecl, node_grants: SealedGrantSet
) -> list[CrossFileError]:
    """Fold ONE `extend node`'s `may_grants` into `node_grants` via
    `SealedGrantSet.widen` -- an atom the root never granted this node is
    refused (the ticket's hard weakening constraint; `widen` itself
    reports this by returning `False`, this function is what turns that
    into a `CrossFileError`), a matching atom's `via` tuple is widened by
    set union (root entries first, no duplicates). Split out of
    `resolve_fragments` purely to keep that function's own body a
    manageable length; no behavior of its own beyond this one fold."""
    errors: list[CrossFileError] = []
    for grant in extend.may_grants:
        if not node_grants.widen(grant.atom, grant.via):
            errors.append(
                CrossFileError(
                    path=path,
                    message=(
                        f"extend node {extend.id!r} may {grant.atom!r} -- the root "
                        f"never granted this capability to this node; a fragment "
                        f"cannot grant a capability the root refused"
                    ),
                )
            )
    return errors


def _group_targeted_roots(
    files: tuple[FileModule, ...], targeted_names: frozenset[str]
) -> dict[str, list[tuple[str, Module]]]:
    """Every root file (`part_of is None`) whose `name` is in
    `targeted_names`, grouped by that name -- the candidate set
    `_resolve_unique_roots` checks for zero/ambiguous matches. A root
    whose name no fragment targets is never even looked at (T-1196's
    pre-existing multi-module merge stays untouched)."""
    grouped: dict[str, list[tuple[str, Module]]] = {name: [] for name in targeted_names}
    for path, module in files:
        if module.part_of is None and module.name in grouped:
            grouped[module.name].append((path, module))
    return grouped


def _group_fragments_by_name(
    fragments: list[tuple[str, Module, str]],
) -> dict[str, list[str]]:
    """Every fragment's path, grouped by the root name it targets -- an
    index built once so `_resolve_unique_roots` never re-scans the whole
    fragment list per candidate name (PERF003: an O(names * fragments)
    nested scan collapses to one O(fragments) pass here)."""
    by_name: dict[str, list[str]] = {}
    for path, _module, name in fragments:
        by_name.setdefault(name, []).append(path)
    return by_name


def _resolve_unique_roots(
    roots_by_name: dict[str, list[tuple[str, Module]]],
    fragment_paths_by_name: dict[str, list[str]],
) -> Result[dict[str, tuple[str, Module]], tuple[CrossFileError, ...]]:
    """For each targeted name: zero declaring root files is "a fragment
    names a nonexistent root" (named against every fragment that targeted
    it), more than one is "ambiguous which root" (named against every
    declaring file) -- both hard errors. Exactly one candidate resolves
    that name to its `(path, Module)`."""
    errors: list[CrossFileError] = []
    unique_root_by_name: dict[str, tuple[str, Module]] = {}
    for name, candidates in roots_by_name.items():
        if not candidates:
            for path in fragment_paths_by_name.get(name, ()):
                errors.append(
                    CrossFileError(
                        path=path,
                        message=(
                            f"'part of {name!r}' names a nonexistent root -- no "
                            f"loaded file declares 'module {name}'"
                        ),
                    )
                )
        elif len(candidates) > 1:
            for path, _ in candidates:
                errors.append(
                    CrossFileError(
                        path=path,
                        message=(
                            f"multiple files declare 'module {name}' "
                            f"({', '.join(p for p, _ in candidates)}) -- exactly one "
                            f"file may declare it; a second root makes the closure "
                            f"boundary ambiguous for the fragment(s) extending it"
                        ),
                    )
                )
        else:
            unique_root_by_name[name] = candidates[0]
    if errors:
        return Err(tuple(errors))
    return Ok(unique_root_by_name)


def _seed_grants_by_root_node(
    unique_root_by_name: dict[str, tuple[str, Module]],
) -> dict[str, dict[str, SealedGrantSet]]:
    """One `SealedGrantSet`, per (root name, node id), seeded from each
    resolved root's own grants via `SealedGrantSet.from_root_node` --
    the ONLY place a `SealedGrantSet` is constructed; every fragment's
    `extend` folds into an already-built one via `_widen_node_grants`,
    never builds its own."""
    return {
        name: {node.id: SealedGrantSet.from_root_node(node) for node in root.nodes}
        for name, (_, root) in unique_root_by_name.items()
    }


def _apply_fragment_extends(
    fragments: list[tuple[str, Module, str]],
    unique_root_by_name: dict[str, tuple[str, Module]],
    grants_by_root_node: dict[str, dict[str, SealedGrantSet]],
) -> tuple[CrossFileError, ...]:
    """Fold every fragment's `extend node` statements into
    `grants_by_root_node` (mutated in place via `_widen_node_grants`); an
    `extend node ID` naming an id the target root never declared is a
    hard error, distinct from `_widen_node_grants`'s own unknown-atom
    case."""
    errors: list[CrossFileError] = []
    for path, fragment, fragment_name in fragments:
        node_grants_by_id = grants_by_root_node[fragment_name]
        for extend in fragment.extends:
            node_grants = node_grants_by_id.get(extend.id)
            if node_grants is None:
                root_path, root_module = unique_root_by_name[fragment_name]
                errors.append(
                    CrossFileError(
                        path=path,
                        message=(
                            f"extend node {extend.id!r} references a node the root "
                            f"({root_module.name!r}, {root_path}) never declared"
                        ),
                    )
                )
                continue
            errors.extend(_widen_node_grants(path, extend, node_grants))
    return tuple(errors)


def _rebuild_resolved_files(
    files: tuple[FileModule, ...],
    unique_root_by_name: dict[str, tuple[str, Module]],
    grants_by_root_node: dict[str, dict[str, SealedGrantSet]],
) -> tuple[FileModule, ...]:
    """Replace each resolved root's `Module` with a copy carrying its
    widened `may_grants`; every other file (fragments, and any root
    T-1196 left untouched) passes through unchanged."""
    resolved_roots: dict[str, Module] = {}
    for name, (_, root_module) in unique_root_by_name.items():
        node_grants_for_root = grants_by_root_node[name]
        new_nodes = tuple(
            node.model_copy(
                update={
                    "may_grants": tuple(node_grants_for_root[node.id].grants.values())
                }
            )
            for node in root_module.nodes
        )
        resolved_roots[name] = root_module.model_copy(update={"nodes": new_nodes})

    resolved_root_paths = {path for path, _ in unique_root_by_name.values()}
    resolved: list[FileModule] = []
    for path, module in files:
        if path in resolved_root_paths and module.part_of is None:
            resolved.append((path, resolved_roots[module.name]))
        else:
            resolved.append((path, module))
    return tuple(resolved)


# frob:doc docs/strata/surface.md#fragments-t-2502
# frob:tests \
# tests/unit/strata/test_fragments.py::TestResolveFragments.test_widens_existing_grant
# frob:tests \
# tests/unit/strata/test_fragments.py::TestResolveFragments.test_no_root_is_error
# frob:tests \
# tests/unit/strata/test_fragments.py::TestResolveFragments.test_two_roots_is_error
# frob:tests \
# tests/unit/strata/test_fragments.py::TestResolveFragments.test_unknown_root_name_is_e\
# rror
# frob:tests \
# tests/unit/strata/test_fragments.py::TestResolveFragments.test_unknown_node_is_error
# frob:tests \
# tests/unit/strata/test_fragments.py::TestResolveFragments.test_unknown_atom_is_error
# frob:tests \
# tests/unit/strata/test_fragments.py::TestResolveFragments.test_unrelated_multi_module\
# _merge_is_unaffected
def resolve_fragments(
    files: tuple[FileModule, ...],
) -> Result[tuple[FileModule, ...], tuple[CrossFileError, ...]]:
    """Fold every fragment file's `extend node { ... }` grants into the
    root node declaration it names, enforcing the T-2502 closure contract
    before `merge_modules`/`elaborate` ever run.

    T-1196 already lets an unrelated group of files each declare their
    own `module NAME` (any names) and merges them flatly -- that
    pre-existing, tested, backward-compatible shape is left completely
    untouched here: this function does nothing at all (`Ok(files)`
    immediately) whenever NO loaded file declares `part of` (T-2502's
    "does not mandate modularity" clause: the root may stay whole, or
    split into several co-equal root files the old way, for anyone who
    does not use fragments). The T-2502 closure rule below applies ONLY
    to a module NAME that at least one loaded fragment actually targets:

    - for each such NAME, exactly one loaded file may declare
      `module NAME` -- zero is "a fragment names a nonexistent root",
      more than one is "which one does the fragment extend" ambiguity;
      both are hard errors naming every file involved;
    - every `extend node ID` must target a node id that root itself
      declared (not a fragment-introduced id, not another fragment's
      extension) -- an unknown target is a hard error, distinct from the
      nonexistent-root case;
    - every extended `may "ATOM"` must match an atom the root ALREADY
      granted that exact node -- an atom the root never granted is a
      hard error ("a fragment cannot grant a capability the root
      refused", the ticket's hard constraint), distinct from the
      unknown-node case. A matching atom's `via` tuple is widened by
      set-union (order-preserving, root entries first) with every
      fragment's additional globs; `exclusive`/`of` are carried through
      from the root's own grant untouched -- a fragment has no
      vocabulary to set either (T-2502 grammar), so there is nothing
      here that could ever narrow or relax them either.

    This is the semantic half of extend-only enforcement; the grammar
    (`strata-core/src/parse`) is the syntactic half -- a fragment cannot
    even SPELL `clearance`/`capacity`/a via-less grant, so the only
    weakening vector left to check here is "does this atom already exist
    on this node at all", which this function refuses closed on.
    """
    # T-2502: `part_of` is narrowed to `str` here (once, via the `is not
    # None` filter) and carried as an explicit third tuple element for the
    # rest of this function -- `Module.part_of`'s declared type is
    # `str | None` for every OTHER caller, so re-reading `fragment.
    # part_of` further down would force every use site to re-narrow it.
    fragments: list[tuple[str, Module, str]] = [
        (path, module, module.part_of)
        for path, module in files
        if module.part_of is not None
    ]
    if not fragments:
        return Ok(files)

    # Only names an actual fragment targets are subject to the T-2502
    # one-root rule -- an unrelated root file with a different name (the
    # pre-existing T-1196 multi-module merge) is never touched or checked.
    targeted_names = frozenset(name for _, _, name in fragments)
    roots_by_name = _group_targeted_roots(files, targeted_names)
    fragment_paths_by_name = _group_fragments_by_name(fragments)

    resolved_roots_result = _resolve_unique_roots(roots_by_name, fragment_paths_by_name)
    if resolved_roots_result.is_err:
        return Err(resolved_roots_result.danger_err)
    unique_root_by_name = resolved_roots_result.danger_ok

    grants_by_root_node = _seed_grants_by_root_node(unique_root_by_name)
    errors = _apply_fragment_extends(
        fragments, unique_root_by_name, grants_by_root_node
    )
    if errors:
        return Err(errors)

    return Ok(_rebuild_resolved_files(files, unique_root_by_name, grants_by_root_node))


# frob:doc docs/strata/surface.md#multi-file-design-load-cross-file-references-t-1196
# frob:tests \
# tests/unit/strata/test_multifile.py::TestMergeModules.test_concatenates_declarations
def merge_modules(files: tuple[FileModule, ...], name: str = "design") -> Module:
    """Concatenate every loaded file's parsed declarations into one `Module`
    so `elaborate()` resolves a reference to any of them identically to a
    single monolithic file (T-1196 acceptance 0). Field order matches
    `Module`'s own declaration order (`_ast.py::Module`) so a future field
    added there is easy to spot as missing here."""
    modules = tuple(module for _, module in files)
    return Module(
        name=name,
        nodes=tuple(d for m in modules for d in m.nodes),
        flows=tuple(d for m in modules for d in m.flows),
        boundaries=tuple(d for m in modules for d in m.boundaries),
        claims=tuple(d for m in modules for d in m.claims),
        refines=tuple(d for m in modules for d in m.refines),
        stores=tuple(d for m in modules for d in m.stores),
        caches=tuple(d for m in modules for d in m.caches),
        queues=tuple(d for m in modules for d in m.queues),
        cdns=tuple(d for m in modules for d in m.cdns),
        balancers=tuple(d for m in modules for d in m.balancers),
        policies=tuple(d for m in modules for d in m.policies),
        operations=tuple(d for m in modules for d in m.operations),
        scenarios=tuple(d for m in modules for d in m.scenarios),
        secrets=tuple(d for m in modules for d in m.secrets),
        resources=tuple(d for m in modules for d in m.resources),
    )


# frob:doc docs/strata/surface.md#multi-file-design-load-cross-file-references-t-1196
# frob:tests \
# tests/unit/strata/test_multifile.py::TestElaborateMerged.test_resolves_cross_file_flow
# frob:tests \
# tests/unit/strata/test_multifile.py::TestElaborateMerged.test_fails_closed_on_missing\
# _id
def elaborate_merged(
    files: tuple[FileModule, ...], name: str = "design"
) -> Result[KernelModel, tuple[CrossFileError, ...]]:
    """T-1196's cross-file-aware entry point, extended by T-2502 to resolve
    `part of`/`extend` fragments FIRST: fold every fragment's grants into
    the one root file's own nodes (`resolve_fragments`, fails closed on a
    missing/duplicate root, an unknown root name, or a grant the root
    never made), then pre-check flow/boundary references per file
    (`check_cross_file_references`), then merge every file's `Module`
    (`merge_modules`) and elaborate ONCE so a reference to a node/flow
    declared in a different loaded file resolves exactly like a
    single-file design would. Fails closed -- naming the file and id --
    at any stage; never returns a partial model on error."""
    resolved = resolve_fragments(files)
    if resolved.is_err:
        return Err(resolved.danger_err)
    files = resolved.danger_ok
    cross_errors = check_cross_file_references(files)
    if cross_errors:
        return Err(cross_errors)
    merged = merge_modules(files, name=name)
    result = elaborate(merged)
    if result.is_err:
        # A single-file load attributes the fault to that one real file
        # (preserves the pre-T-1196 per-file error path for the common
        # one-file-under-design/ case); a genuine multi-file merge cannot
        # attribute a post-merge fault to one specific file (the whole
        # point of merging is that the fault may span more than one), so
        # it is named against the merged unit instead.
        path = files[0][0] if len(files) == 1 else f"<merged:{name}>"
        return Err(
            (
                CrossFileError(
                    path=path,
                    message=str(result.danger_err),
                    error=result.danger_err,
                ),
            )
        )
    return Ok(result.danger_ok)


__all__ = [
    "CrossFileError",
    "FileModule",
    "check_cross_file_references",
    "merge_modules",
    "elaborate_merged",
    "resolve_fragments",
]
