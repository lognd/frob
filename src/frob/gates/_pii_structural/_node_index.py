"""T-1209 perf: `_scan_one_python_file` used to dispatch to ~8 sub-scans
that each ran their own full `ast.walk(tree)` pass (8.84M walk resumptions,
39.6M isinstance checks measured across this repo's own tracked files, 78pct
of `pii_structural_gate`'s wall time). `_build_node_index` runs ONE
`ast.walk(tree)` pass and buckets every node type this package's sub-scans
consume into a `_NodeIndex`; each sub-scan now reads its bucket instead of
re-walking the tree.

Bucketing must not silently reorder findings: a few sub-scans used to
interleave two node types within a single `ast.walk` loop (e.g.
`_scan_python_env_access`'s `Subscript`+`Call` sweep), so the RELATIVE
document order between those two types drove violation order. `_NodeIndex.
_position_of`/`_NodeIndex._ordered` recover that exact original walk order across
two or more separately bucketed lists, so splitting the walk never changes
what order violations come out in."""

from __future__ import annotations

import ast
from collections.abc import Sequence
from dataclasses import dataclass, field

from frob.logging import get_logger

_log = get_logger(__name__)


@dataclass
class _NodeIndex:
    """Per-file AST node buckets produced by one `ast.walk(tree)` pass
    (`_build_node_index`) -- every `_pii_structural` sub-scan reads its
    bucket(s) here instead of running its own `ast.walk`."""

    class_defs: list[ast.ClassDef] = field(default_factory=list)
    calls: list[ast.Call] = field(default_factory=list)
    assigns: list[ast.Assign] = field(default_factory=list)
    ann_assigns: list[ast.AnnAssign] = field(default_factory=list)
    str_constants: list[ast.Constant] = field(default_factory=list)
    subscripts: list[ast.Subscript] = field(default_factory=list)
    names: list[ast.Name] = field(default_factory=list)
    args: list[ast.arg] = field(default_factory=list)
    function_defs: list[ast.FunctionDef | ast.AsyncFunctionDef] = field(
        default_factory=list
    )
    attributes: list[ast.Attribute] = field(default_factory=list)
    aliases: list[ast.alias] = field(default_factory=list)
    _position: dict[int, int] = field(default_factory=dict, repr=False)

    def _position_of(self, node: ast.AST) -> int:
        """`node`'s position in the single `_build_node_index` walk (keyed by
        `id(node)`) -- the sort key `_ordered` uses to recover cross-bucket
        document order; `node` must be one this same index bucketed (its
        object identity is kept alive by the bucket lists themselves)."""
        return self._position[id(node)]

    def _ordered(self, *buckets: Sequence[ast.AST]) -> list[ast.AST]:
        """`buckets` concatenated then re-sorted into this index's original
        single-walk visitation order -- lets a consumer that used to
        interleave two+ node types in one `ast.walk` loop recover that exact
        relative order from separately bucketed lists, without re-walking.
        `Sequence` (not `list`) so a differently-typed bucket (e.g.
        `list[ast.Name]`) is accepted without a variance complaint -- this
        method reads its arguments and never mutates them."""
        merged = [node for bucket in buckets for node in bucket]
        merged.sort(key=self._position_of)
        return merged


def _build_node_index(tree: ast.Module) -> _NodeIndex:
    """One `ast.walk(tree)` pass bucketing every node type this package's
    Python sub-scans consume (T-1209): `ClassDef`, `Call`, `Assign`,
    `AnnAssign`, string `Constant`, `Subscript`, `Name`, `arg`,
    `FunctionDef`/`AsyncFunctionDef`, `Attribute`, `alias`. Each node's
    single-walk position is also recorded (`_NodeIndex._position_of`) so callers
    that used to interleave two bucketed types in one loop can recover that
    exact order via `_NodeIndex._ordered`."""
    index = _NodeIndex()
    position = 0
    for node in ast.walk(tree):
        index._position[id(node)] = position
        position += 1
        if isinstance(node, ast.ClassDef):
            index.class_defs.append(node)
        elif isinstance(node, ast.Call):
            index.calls.append(node)
        elif isinstance(node, ast.Assign):
            index.assigns.append(node)
        elif isinstance(node, ast.AnnAssign):
            index.ann_assigns.append(node)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            index.str_constants.append(node)
        elif isinstance(node, ast.Subscript):
            index.subscripts.append(node)
        elif isinstance(node, ast.Name):
            index.names.append(node)
        elif isinstance(node, ast.arg):
            index.args.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            index.function_defs.append(node)
        elif isinstance(node, ast.Attribute):
            index.attributes.append(node)
        elif isinstance(node, ast.alias):
            index.aliases.append(node)
    _log.debug("_build_node_index: bucketed %d node(s) in one ast.walk pass", position)
    return index


# frob:ticket T-2696
# frob:waive AFFECT001 reason="T-2696 adds per-violation symref precision \
# (Violation.symref) to PII010/011/012's existing behavior -- WHICH sites fire and why \
# is unchanged (verified via this ticket's own live re-run against this repo's tree), \
# only the waiver-matching precision each finding carries, so \
# docs/modules/gates.md#structural-pii-secrets-detection- t-0207's mechanism \
# description needs no update, matching the identical T-1209 _index-kwarg precedent \
# immediately below in this same file family"
# frob:doc docs/modules/gates.md#structural-pii-secrets-detection-t-0207
# frob:tests \
# tests/test_pii_structural_gate.py::TestSymrefPopulation.test_enclosing_qualname_neste\
# d_method_is_dotted kind="unit"
# frob:tests \
# tests/test_pii_structural_gate.py::TestSymrefPopulation.test_enclosing_qualname_modul\
# e_level_is_none kind="unit"
def enclosing_qualname(index: _NodeIndex, line: int) -> str | None:
    """T-2696: the tightest-spanning `ClassDef`/`FunctionDef`/
    `AsyncFunctionDef`'s dotted qualname covering `line`, built from the
    SAME `_NodeIndex` bucketing pass `_build_node_index` already performs
    -- no second `ast.walk`, no re-parse, no file read. `None` for a
    module-level site (no enclosing class/function contains `line`).

    Unlike `frob.gates._opaque._enclosing_qualname` (which re-parses the
    file via `frob.lang.parse_file` to get pre-computed qualnames), this
    reconstructs nesting itself from the flat `class_defs`/`function_defs`
    buckets: every containing node (line-span covers `line`) is collected,
    then sorted OUTERMOST-first by span size (a containing class/function
    always spans at least as many lines as anything nested inside it), and
    their `.name`s dot-joined -- `Outer.method` for a method, `Outer.Inner`
    for a nested function, a bare function name for a module-level
    function, `None` for module-level data (PII010's most common site,
    a class field, is exactly the `Class.__init__`-less case this still
    handles: dataclass/pydantic fields have no enclosing FunctionDef, so
    the class's own bare name is the correct, and only, qualname)."""
    candidates = [
        node
        for node in (*index.class_defs, *index.function_defs)
        if node.lineno <= line <= (node.end_lineno or node.lineno)
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda node: (node.end_lineno or node.lineno) - node.lineno, reverse=True
    )
    return ".".join(node.name for node in candidates)
