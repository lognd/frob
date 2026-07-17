"""Legacy Type-1/Type-2 duplicate scan (pre-smart-dup, docs/dup.md).

Kept verbatim behind `find_duplicates` for `frob check`'s dup stage and the
`frob dup` CLI (`frob.app.dup_runner`), neither of which has been
re-platformed onto the rung pipeline yet. New code should prefer
`frob.dup.find_clones` (docs/dup.md's smart pipeline); this module is the
compatibility shim that keeps the existing entry point working.

Parses through `frob.lang.raw_tree` (one grammar-loading mechanism, per
docs/lang.md) rather than a bespoke per-module tree-sitter parser stack --
`_child`/`_node_text` below are trivial `child_by_field_name`/decode
one-liners kept local since they are not parsing infrastructure worth a
shared home.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from tree_sitter import Node
from typani import ErrorSet

from frob.logging import get_logger

_log = get_logger(__name__)

_PY_EXTS = {".py"}
_CPP_EXTS = {".cpp", ".cc", ".cxx", ".h", ".hpp"}


def _child(node: Node, field: str) -> Node | None:
    """`node.child_by_field_name(field)` -- see the module docstring."""
    return node.child_by_field_name(field)


def _node_text(node: Node | None) -> str:
    """Decode `node`'s own text, or '' if absent (missing name = grammar bug)."""
    if node is None or node.text is None:
        return ""
    return node.text.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


# frob:doc docs/dup.md#legacy-scanner
class DupError(ErrorSet):
    ParseFailed = "failed to parse file"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


# frob:doc docs/dup.md#legacy-scanner
class CodeFragment(BaseModel):
    file: str
    start_line: int
    end_line: int
    symbol: str


# frob:doc docs/dup.md#legacy-scanner
class CloneGroup(BaseModel):
    clone_type: Literal["exact", "renamed"]
    size_lines: int
    fragments: list[CodeFragment]


# frob:doc docs/dup.md#legacy-scanner
class DupResult(BaseModel):
    root: str
    groups: list[CloneGroup]

    # frob:doc docs/dup.md#legacy-scanner
    @property
    def total_clones(self) -> int:
        return sum(len(g.fragments) for g in self.groups)

    # frob:doc docs/dup.md#legacy-scanner
    def as_text(self) -> str:
        if not self.groups:
            return "no duplicates found"
        n_groups = len(self.groups)
        n_frags = self.total_clones
        lines: list[str] = [
            f"{n_groups} duplicate group{'s' if n_groups != 1 else ''}, "
            f"{n_frags} fragment{'s' if n_frags != 1 else ''}",
            "",
        ]
        for i, g in enumerate(self.groups, 1):
            lines.append(
                f"Group {i} ({g.clone_type},"
                f" {g.size_lines} line{'s' if g.size_lines != 1 else ''}):"
            )
            # Align file:line ranges
            max_loc = max(
                len(f"{frag.file}:{frag.start_line}-{frag.end_line}")
                for frag in g.fragments
            )
            for frag in g.fragments:
                loc = f"{frag.file}:{frag.start_line}-{frag.end_line}"
                padding = " " * (max_loc - len(loc) + 2)
                lines.append(f"  {loc}{padding}{frag.symbol}")
        return "\n".join(lines)

    # frob:doc docs/dup.md#legacy-scanner
    def as_json(self) -> str:
        return json.dumps(self.model_dump(), indent=2)


# ---------------------------------------------------------------------------
# Fingerprinting helpers
# ---------------------------------------------------------------------------


def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def _collect_locals_py(func_node: Node) -> set[str]:
    """Collect identifiers that are local to a Python function."""
    locals_: set[str] = set()

    # Parameters
    params = _child(func_node, "parameters")
    if params:
        _collect_param_names_py(params, locals_)

    # Body assignments / for / with
    body = _child(func_node, "body")
    if body:
        _collect_assigned_names_py(body, locals_)

    return locals_


def _collect_param_names_py(node: Node, out: set[str]) -> None:
    for child in node.named_children:
        t = child.type
        if t == "identifier":
            out.add(_node_text(child))
        elif t in ("default_parameter", "typed_parameter", "typed_default_parameter"):
            name_node = child.child_by_field_name("name")
            if name_node:
                out.add(_node_text(name_node))
            else:
                # first identifier child
                for c in child.named_children:
                    if c.type == "identifier":
                        out.add(_node_text(c))
                        break
        elif t in ("list_splat_pattern", "dictionary_splat_pattern"):
            for c in child.named_children:
                if c.type == "identifier":
                    out.add(_node_text(c))
                    break
        elif t == "keyword_separator":
            pass


def _collect_assigned_names_py(node: Node, out: set[str]) -> None:
    """Walk the body and harvest assignment/for/with binding names."""
    for child in node.children:
        t = child.type
        if t == "expression_statement":
            # Assignments appear as expression_statement > assignment in tree-sitter
            for inner in child.children:
                if inner.type == "assignment":
                    lhs = inner.child_by_field_name("left")
                    if lhs:
                        _harvest_pattern(lhs, out)
                elif inner.type == "augmented_assignment":
                    lhs = inner.child_by_field_name("left")
                    if lhs and lhs.type == "identifier":
                        out.add(_node_text(lhs))
        elif t == "assignment":
            lhs = child.child_by_field_name("left")
            if lhs:
                _harvest_pattern(lhs, out)
        elif t == "augmented_assignment":
            lhs = child.child_by_field_name("left")
            if lhs and lhs.type == "identifier":
                out.add(_node_text(lhs))
        elif t in ("for_statement", "async_for_statement"):
            left = child.child_by_field_name("left")
            if left:
                _harvest_pattern(left, out)
            body = child.child_by_field_name("body")
            if body:
                _collect_assigned_names_py(body, out)
        elif t == "with_statement":
            for item in child.named_children:
                if item.type == "with_item":
                    alias = item.child_by_field_name("alias")
                    if alias:
                        _harvest_pattern(alias, out)
            body = child.child_by_field_name("body")
            if body:
                _collect_assigned_names_py(body, out)
        elif t in (
            "if_statement",
            "while_statement",
            "try_statement",
            "block",
            "suite",
        ):
            _collect_assigned_names_py(child, out)
        elif t in (
            "function_definition",
            "async_function_definition",
            "class_definition",
        ):
            # nested -- names in nested scopes are not ours
            pass


def _harvest_pattern(node: Node, out: set[str]) -> None:
    if node.type == "identifier":
        out.add(_node_text(node))
    else:
        for child in node.named_children:
            _harvest_pattern(child, out)


def _serialize_py_body(body: Node, locals_: set[str]) -> str:
    """Serialize a Python body node to a normalized token string."""
    mapping: dict[str, str] = {}
    tokens: list[str] = []

    def visit(n: Node) -> None:
        if n.type == "comment":
            return
        if not n.children:
            # leaf
            t = n.type
            raw = _node_text(n)
            if t == "identifier" and raw in locals_:
                if raw not in mapping:
                    mapping[raw] = f"_v{len(mapping)}"
                tokens.append(mapping[raw])
            elif t in (
                "string",
                "string_content",
                "interpolation",
                "concatenated_string",
            ):
                tokens.append("_S_")
            elif t in ("integer", "float"):
                tokens.append("_N_")
            else:
                tokens.append(raw)
        else:
            # internal node -- handle string/number containers specially
            if n.type in ("string", "concatenated_string"):
                tokens.append("_S_")
                return
            for child in n.children:
                visit(child)

    visit(body)
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# C++ fingerprinting helpers
# ---------------------------------------------------------------------------


def _collect_locals_cpp(func_node: Node) -> set[str]:
    locals_: set[str] = set()

    # Parameters
    params = _child(func_node, "parameters")
    if params:
        for child in params.named_children:
            _harvest_cpp_param(child, locals_)

    # Body declarations / for
    body = _child(func_node, "body")
    if body:
        _collect_assigned_names_cpp(body, locals_)

    return locals_


def _harvest_cpp_param(node: Node, out: set[str]) -> None:

    if node.type in ("parameter_declaration", "optional_parameter_declaration"):
        decl = node.child_by_field_name("declarator")
        if decl:
            _harvest_cpp_declarator_name(decl, out)
    elif node.type == "variadic_parameter_declaration":
        decl = node.child_by_field_name("declarator")
        if decl:
            _harvest_cpp_declarator_name(decl, out)


def _harvest_cpp_declarator_name(node: Node, out: set[str]) -> None:
    if node.type == "identifier":
        out.add(_node_text(node))
    elif node.type in (
        "pointer_declarator",
        "reference_declarator",
        "abstract_pointer_declarator",
    ):
        inner = node.child_by_field_name("declarator")
        if inner:
            _harvest_cpp_declarator_name(inner, out)
    else:
        for c in node.named_children:
            _harvest_cpp_declarator_name(c, out)


def _collect_assigned_names_cpp(node: Node, out: set[str]) -> None:
    for child in node.named_children:
        t = child.type
        if t == "declaration":
            decl = child.child_by_field_name("declarator")
            if decl:
                _harvest_cpp_declarator_name(decl, out)
        elif t in ("for_statement", "for_range_loop"):
            init = child.child_by_field_name("initializer")
            if init:
                _collect_assigned_names_cpp(init, out)
            body = child.child_by_field_name("body")
            if body:
                _collect_assigned_names_cpp(body, out)
        elif t in (
            "if_statement",
            "while_statement",
            "do_statement",
            "compound_statement",
            "try_statement",
        ):
            _collect_assigned_names_cpp(child, out)


def _serialize_cpp_body(body: Node, locals_: set[str]) -> str:
    mapping: dict[str, str] = {}
    tokens: list[str] = []

    def visit(n: Node) -> None:
        if n.type == "comment":
            return
        if not n.children:
            t = n.type
            raw = _node_text(n)
            if t == "identifier" and raw in locals_:
                if raw not in mapping:
                    mapping[raw] = f"_v{len(mapping)}"
                tokens.append(mapping[raw])
            elif t in (
                "string_literal",
                "raw_string_literal",
                "char_literal",
                "user_defined_string_literal",
            ):
                tokens.append("_S_")
            elif t in ("number_literal",):
                tokens.append("_N_")
            else:
                tokens.append(raw)
        else:
            if n.type in ("string_literal", "raw_string_literal", "char_literal"):
                tokens.append("_S_")
                return
            for child in n.children:
                visit(child)

    visit(body)
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# Python file scanning
# ---------------------------------------------------------------------------


def _enclosing_class_py(func_node: Node) -> str | None:
    """Return the enclosing class name for a function node, or None."""
    parent = func_node.parent
    while parent is not None:
        if parent.type == "block":
            grandparent = parent.parent
            if grandparent is not None and grandparent.type == "class_definition":
                name_node = _child(grandparent, "name")
                if name_node:
                    return _node_text(name_node)
        parent = parent.parent
    return None


def _iter_functions_py(root_node: Node):
    """Yield (func_node, symbol) for all function/async_function nodes."""
    def visit(n: Node):
        if n.type in ("function_definition", "async_function_definition"):
            name_node = _child(n, "name")
            func_name = _node_text(name_node) if name_node else "<unknown>"
            class_name = _enclosing_class_py(n)
            symbol = f"{class_name}.{func_name}" if class_name else func_name
            yield_item = (n, symbol)
            yield yield_item
            # recurse into nested functions
            body = _child(n, "body")
            if body:
                for child in body.children:
                    yield from _recurse(child)
        else:
            for child in n.children:
                yield from _recurse(child)

    def _recurse(n: Node):  # type: ignore[return]
        if n.type in ("function_definition", "async_function_definition"):
            yield from visit(n)
        else:
            for child in n.children:
                yield from _recurse(child)

    yield from visit(root_node)


def _scan_py_file(
    path: Path,
    root: Path,
    min_lines: int,
    exact_map: dict[str, list[CodeFragment]],
    renamed_map: dict[str, list[CodeFragment]],
) -> None:
    from frob.lang import raw_tree

    parsed = raw_tree(path)
    if parsed.is_err:
        _log.warning("parse failed for %s: %s", path, parsed.err)
        return
    tree, src, _language = parsed.danger_ok

    rel = str(path.relative_to(root))

    for func_node, symbol in _iter_functions_py(tree.root_node):
        body = _child(func_node, "body")
        if body is None:
            continue
        start_line = body.start_point[0] + 1
        end_line = body.end_point[0] + 1
        size = end_line - start_line + 1
        if size < min_lines:
            continue

        frag = CodeFragment(
            file=rel,
            start_line=start_line,
            end_line=end_line,
            symbol=symbol,
        )

        # Exact hash: normalized whitespace of original text
        body_bytes = src[body.start_byte : body.end_byte]
        exact_text = b"\n".join(line.strip() for line in body_bytes.splitlines())
        exact_hash = _sha16(exact_text.decode(errors="replace"))
        exact_map[exact_hash].append(frag)

        # Renamed hash: normalized AST tokens
        locals_ = _collect_locals_py(func_node)
        serialized = _serialize_py_body(body, locals_)
        renamed_hash = _sha16(serialized)
        renamed_map[renamed_hash].append(frag)


# ---------------------------------------------------------------------------
# C++ file scanning
# ---------------------------------------------------------------------------


def _enclosing_class_cpp(func_node: Node) -> str | None:
    parent = func_node.parent
    while parent is not None:
        if parent.type == "field_declaration_list":
            grandparent = parent.parent
            if grandparent is not None and grandparent.type in (
                "class_specifier",
                "struct_specifier",
            ):
                name_node = _child(grandparent, "name")
                if name_node:
                    return _node_text(name_node)
        parent = parent.parent
    return None


def _iter_functions_cpp(root_node: Node):
    def _func_name(n: Node) -> str:
        decl = _child(n, "declarator")
        if decl is None:
            return "<unknown>"
        # unwrap pointer/ref/function declarator
        inner = decl
        while inner.type in ("pointer_declarator", "reference_declarator"):
            inner = inner.child_by_field_name("declarator") or inner
            if inner == decl:
                break
            decl = inner
        if inner.type == "function_declarator":
            name_node = inner.child_by_field_name("declarator")
            return _node_text(name_node) if name_node else _node_text(inner)
        return _node_text(inner)

    def visit(n: Node):
        if n.type == "function_definition":
            body = _child(n, "body")
            if body is not None:
                func_name = _func_name(n)
                class_name = _enclosing_class_cpp(n)
                symbol = f"{class_name}.{func_name}" if class_name else func_name
                yield (n, symbol)
        for child in n.named_children:
            yield from visit(child)

    yield from visit(root_node)


def _scan_cpp_file(
    path: Path,
    root: Path,
    min_lines: int,
    exact_map: dict[str, list[CodeFragment]],
    renamed_map: dict[str, list[CodeFragment]],
) -> None:
    from frob.lang import raw_tree

    parsed = raw_tree(path)
    if parsed.is_err:
        _log.warning("parse failed for %s: %s", path, parsed.err)
        return
    tree, src, _language = parsed.danger_ok

    rel = str(path.relative_to(root))

    for func_node, symbol in _iter_functions_cpp(tree.root_node):
        body = _child(func_node, "body")
        if body is None:
            continue
        start_line = body.start_point[0] + 1
        end_line = body.end_point[0] + 1
        size = end_line - start_line + 1
        if size < min_lines:
            continue

        frag = CodeFragment(
            file=rel,
            start_line=start_line,
            end_line=end_line,
            symbol=symbol,
        )

        body_bytes = src[body.start_byte : body.end_byte]
        exact_text = b"\n".join(line.strip() for line in body_bytes.splitlines())
        exact_hash = _sha16(exact_text.decode(errors="replace"))
        exact_map[exact_hash].append(frag)

        locals_ = _collect_locals_cpp(func_node)
        serialized = _serialize_cpp_body(body, locals_)
        renamed_hash = _sha16(serialized)
        renamed_map[renamed_hash].append(frag)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


# frob:doc docs/dup.md#legacy-scanner
def find_duplicates(root: Path, min_lines: int = 6) -> DupResult:
    """Scan root recursively for duplicate function bodies."""
    from frob.logging.quiet import quiet_stdout_logs

    exact_map: dict[str, list[CodeFragment]] = defaultdict(list)
    renamed_map: dict[str, list[CodeFragment]] = defaultdict(list)

    # frob.lang.raw_tree logs at INFO/DEBUG per parse (unlike the retired
    # per-language wrappers this module used to call, which logged nothing)
    # -- CLI callers piping `--json` need that off stdout, same reasoning
    # as frob.logging.quiet's own docstring.
    with quiet_stdout_logs():
        for path in _walk(root):
            ext = path.suffix.lower()
            if ext in _PY_EXTS:
                _scan_py_file(path, root, min_lines, exact_map, renamed_map)
            elif ext in _CPP_EXTS:
                _scan_cpp_file(path, root, min_lines, exact_map, renamed_map)

    # Build clone groups
    # exact_map keys that have 2+ identical fragments -> Type 1 (exact)
    # renamed_map keys that have 2+ fragments but NOT all exact -> Type 2 (renamed)
    groups: list[CloneGroup] = []

    # Collect exact groups first; track which (file, start) pairs are exact clones
    exact_groups: list[CloneGroup] = []
    exact_frag_keys: set[tuple[str, int]] = set()

    for frags in exact_map.values():
        if len(frags) < 2:
            continue
        size = max(f.end_line - f.start_line + 1 for f in frags)
        exact_groups.append(
            CloneGroup(clone_type="exact", size_lines=size, fragments=frags)
        )
        for f in frags:
            exact_frag_keys.add((f.file, f.start_line))

    # Collect renamed groups: only those where not ALL fragments are already in the
    # same exact group (i.e. at least one pair differs only by renaming)
    renamed_groups: list[CloneGroup] = []
    for frags in renamed_map.values():
        if len(frags) < 2:
            continue
        # Skip if every fragment is also in an exact group and they all share one
        # exact hash -- that means it's just a re-listing of an exact clone.
        # Strategy: include group only if at least 2 fragments have different file/line
        # origins that are NOT ALL in the same exact group.
        key_set = {(f.file, f.start_line) for f in frags}
        # Check if there's a single exact group that covers all these fragments
        covered_by_exact = any(
            key_set <= {(ef.file, ef.start_line) for ef in eg.fragments}
            for eg in exact_groups
        )
        if covered_by_exact:
            continue
        size = max(f.end_line - f.start_line + 1 for f in frags)
        renamed_groups.append(
            CloneGroup(clone_type="renamed", size_lines=size, fragments=frags)
        )

    groups = sorted(
        exact_groups + renamed_groups,
        key=lambda g: g.size_lines,
        reverse=True,
    )

    return DupResult(root=str(root), groups=groups)


def _walk(root: Path):
    """Yield all files under root, honoring built-in skips and [graph] exclude."""
    # frob:ticket T-0026
    from frob.excludes import is_excluded, is_skipped_dir, load_exclude_globs

    exclude_globs = load_exclude_globs(root)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if any(is_skipped_dir(part) for part in rel.parts):
            continue
        if exclude_globs and is_excluded(rel.as_posix(), exclude_globs):
            continue
        yield path
