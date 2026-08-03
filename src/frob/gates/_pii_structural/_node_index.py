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
