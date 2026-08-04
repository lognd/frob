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
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from dataclasses import dataclass

from typani import Err, Ok, Result

from ._ast import Module
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
    """T-1196's cross-file-aware entry point: pre-check flow/boundary
    references per file (`check_cross_file_references`), then merge every
    file's `Module` (`merge_modules`) and elaborate ONCE so a reference to
    a node/flow declared in a different loaded file resolves exactly like
    a single-file design would. Fails closed -- naming the file and id --
    on either the pre-check or the merged `elaborate()` call; never
    returns a partial model on error."""
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
]
