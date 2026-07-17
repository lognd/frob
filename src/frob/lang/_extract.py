"""Per-language tree-sitter walkers (docs/lang.md has the full extraction table).

Five grammars, five node vocabularies -- python's docstring-as-first-
statement has no analogue in rust's `///`-comment-above-item convention, and
C's file-scope-`static` publicness rule has no analogue in TypeScript's
`export` keyword. Those differences are real and are kept as small per-
language tables/functions. What is NOT allowed to differ five times is the
mechanism (leaf-token collection, doc-comment stripping, span/qualname
bookkeeping) -- that lives once in ``_common.py`` and every walker below
calls into it instead of restating it.

Each `_walk_<language>` function performs a single recursive descent that
both extracts symbols (functions/methods/classes/consts/types) and defers
comment extraction to `_extract_comments`, which is language-parameterized
only by its comment-node-type set (comments look identical to every
grammar: a leaf node whose type names it as one).
"""

from __future__ import annotations

from tree_sitter import Node, Tree

from frob.lang._common import (
    ByteRange,
    child_text,
    collapse_ws,
    leading_doc_comment,
    leaf_tokens,
    span_of,
    strip_comment_delims,
)
from frob.lang._models import RawComment, RawSymbol, SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)


def _body_skip(body: Node | None) -> tuple[ByteRange, ...]:
    """A skip-range tuple excluding `body`'s byte span, or empty if absent."""
    if body is None:
        return ()
    return ((body.start_byte, body.end_byte),)


COMMENT_TYPES: dict[str, frozenset[str]] = {
    "python": frozenset({"comment"}),
    "typescript": frozenset({"comment"}),
    "tsx": frozenset({"comment"}),
    "rust": frozenset({"line_comment", "block_comment"}),
    "c": frozenset({"comment"}),
    "cpp": frozenset({"comment"}),
}


# frob:doc docs/lang.md#extraction-api
def extract(
    tree: Tree, source: bytes, language: str
) -> tuple[tuple[RawSymbol, ...], tuple[RawComment, ...]]:
    """Extract symbols then comments (order matters: comments bind to symbol spans)."""
    walker = _WALKERS[language]
    symbols = walker(tree.root_node)
    comments = _extract_comments(tree.root_node, COMMENT_TYPES[language], symbols)
    _log.debug(
        "extracted %d symbols, %d comments for language=%s",
        len(symbols),
        len(comments),
        language,
    )
    return symbols, comments


def _extract_comments(
    root: Node,
    comment_types: frozenset[str],
    symbols: tuple[RawSymbol, ...],
) -> tuple[RawComment, ...]:
    """Walk the whole tree for comment-typed leaves, then bind enclosing/following."""
    raw_nodes: list[Node] = []

    def walk(n: Node) -> None:
        if n.type in comment_types:
            raw_nodes.append(n)
            return
        for child in n.children:
            walk(child)

    walk(root)

    out: list[RawComment] = []
    for node in raw_nodes:
        span = span_of(node)
        text = strip_comment_delims(child_text(node))
        enclosing = _find_enclosing(span, symbols)
        following = _find_following(span, symbols)
        out.append(
            RawComment(text=text, span=span, enclosing=enclosing, following=following)
        )
    return tuple(out)


def _find_enclosing(
    span: tuple[int, int], symbols: tuple[RawSymbol, ...]
) -> str | None:
    """Deepest (narrowest-span) symbol whose span fully contains `span`."""
    best: RawSymbol | None = None
    for sym in symbols:
        if sym.span[0] <= span[0] and sym.span[1] >= span[1]:
            width = sym.span[1] - sym.span[0]
            if best is None or width < (best.span[1] - best.span[0]):
                best = sym
    return best.qualname if best is not None else None


def _find_following(
    span: tuple[int, int], symbols: tuple[RawSymbol, ...]
) -> str | None:
    """Symbol starting within 2 lines after the comment's end line, earliest first."""
    end = span[1]
    best: RawSymbol | None = None
    for sym in symbols:
        if end < sym.span[0] <= end + 2:
            if best is None or sym.span[0] < best.span[0]:
                best = sym
    return best.qualname if best is not None else None


# --------------------------------------------------------------------- python


def _walk_python(root: Node) -> tuple[RawSymbol, ...]:
    comment_types = COMMENT_TYPES["python"]
    symbols: list[RawSymbol] = []

    def python_docstring(body: Node) -> tuple[str, ByteRange | None]:
        if body.named_child_count == 0:
            return "", None
        first = body.named_children[0]
        if first.type == "expression_statement":
            if first.named_child_count == 0 or first.named_children[0].type != "string":
                return "", None
            string_node = first.named_children[0]
            doc_range = (first.start_byte, first.end_byte)
        elif first.type == "string":
            string_node = first
            doc_range = (first.start_byte, first.end_byte)
        else:
            return "", None
        content = "".join(
            child_text(c) for c in string_node.children if c.type == "string_content"
        )
        return collapse_ws(content), doc_range

    def visit(container: Node, stack: tuple[str, ...]) -> None:
        for child in container.children:
            node = child
            decorated_wrapper: Node | None = None
            if node.type == "decorated_definition":
                decorated_wrapper = node
                def_types = ("function_definition", "class_definition")
                inner = next(
                    (c for c in node.children if c.type in def_types),
                    None,
                )
                if inner is None:
                    continue
                node = inner
            if node.type == "function_definition":
                sig_node = decorated_wrapper or node
                name = child_text(node.child_by_field_name("name"))
                body = node.child_by_field_name("body")
                if body is None:
                    continue
                doc, doc_range = python_docstring(body)
                sig_tokens = leaf_tokens(sig_node, comment_types, _body_skip(body))
                body_skip = (doc_range,) if doc_range else ()
                body_tokens = leaf_tokens(body, comment_types, body_skip)
                kind = SymbolKind.METHOD if stack else SymbolKind.FUNCTION
                qualname = ".".join((*stack, name))
                symbols.append(
                    RawSymbol(
                        qualname=qualname,
                        kind=kind,
                        public=not name.startswith("_"),
                        span=span_of(sig_node),
                        sig_tokens=sig_tokens,
                        body_tokens=body_tokens,
                        doc_text=doc,
                    )
                )
            elif node.type == "class_definition":
                sig_node = decorated_wrapper or node
                name = child_text(node.child_by_field_name("name"))
                body = node.child_by_field_name("body")
                if body is None:
                    continue
                doc, doc_range = python_docstring(body)
                sig_tokens = leaf_tokens(sig_node, comment_types, _body_skip(body))
                nested_types = (
                    "function_definition",
                    "class_definition",
                    "decorated_definition",
                )
                nested_ranges = tuple(
                    (c.start_byte, c.end_byte)
                    for c in body.children
                    if c.type in nested_types
                )
                body_skip = nested_ranges + ((doc_range,) if doc_range else ())
                body_tokens = leaf_tokens(body, comment_types, body_skip)
                qualname = ".".join((*stack, name))
                symbols.append(
                    RawSymbol(
                        qualname=qualname,
                        kind=SymbolKind.CLASS,
                        public=not name.startswith("_"),
                        span=span_of(sig_node),
                        sig_tokens=sig_tokens,
                        body_tokens=body_tokens,
                        doc_text=doc,
                    )
                )
                visit(body, (*stack, name))
            elif node.type == "expression_statement" and not stack:
                assign = node.named_children[0] if node.named_child_count else None
                if assign is None or assign.type != "assignment":
                    continue
                left = assign.child_by_field_name("left")
                if left is None or left.type != "identifier":
                    continue
                name = child_text(left)
                if not (name and (name.isupper() or "_" in name) and name[0].isalpha()):
                    continue
                if not name.replace("_", "").isupper():
                    continue
                sig_tokens = leaf_tokens(node, comment_types)
                symbols.append(
                    RawSymbol(
                        qualname=name,
                        kind=SymbolKind.CONST,
                        public=not name.startswith("_"),
                        span=span_of(node),
                        sig_tokens=sig_tokens,
                        body_tokens=(),
                        doc_text="",
                    )
                )

    visit(root, ())
    return tuple(symbols)


# ----------------------------------------------------------------- typescript


def _ts_unwrap(node: Node) -> tuple[Node, bool]:
    """Peel `export [default]` off a declaration; return (inner, exported)."""
    if node.type == "export_statement":
        exported = True
        inner = None
        for c in node.children:
            if c.type not in ("export", "default"):
                inner = c
        return (inner or node, exported)
    return (node, False)


def _walk_typescript(root: Node) -> tuple[RawSymbol, ...]:
    comment_types = COMMENT_TYPES["typescript"]
    symbols: list[RawSymbol] = []

    def visit(container: Node, stack: tuple[str, ...]) -> None:
        for raw_child in container.children:
            node, exported = _ts_unwrap(raw_child)
            doc = leading_doc_comment(raw_child, comment_types)

            if node.type == "function_declaration":
                name = child_text(node.child_by_field_name("name"))
                body = node.child_by_field_name("body")
                if body is None:
                    continue
                sig_tokens = leaf_tokens(node, comment_types, _body_skip(body))
                body_tokens = leaf_tokens(body, comment_types)
                symbols.append(
                    RawSymbol(
                        qualname=".".join((*stack, name)),
                        kind=SymbolKind.METHOD if stack else SymbolKind.FUNCTION,
                        public=exported or bool(stack),
                        span=span_of(raw_child),
                        sig_tokens=sig_tokens,
                        body_tokens=body_tokens,
                        doc_text=doc,
                    )
                )
            elif node.type == "class_declaration":
                name = child_text(node.child_by_field_name("name"))
                body = node.child_by_field_name("body")
                if body is None:
                    continue
                sig_tokens = leaf_tokens(node, comment_types, _body_skip(body))
                symbols.append(
                    RawSymbol(
                        qualname=".".join((*stack, name)),
                        kind=SymbolKind.CLASS,
                        public=exported,
                        span=span_of(raw_child),
                        sig_tokens=sig_tokens,
                        body_tokens=(),
                        doc_text=doc,
                    )
                )
                visit(body, (*stack, name))
            elif node.type == "method_definition" and stack:
                name = child_text(node.child_by_field_name("name"))
                body = node.child_by_field_name("body")
                if body is None:
                    continue
                access = next(
                    (
                        child_text(c)
                        for c in node.children
                        if c.type == "accessibility_modifier"
                    ),
                    "public",
                )
                sig_tokens = leaf_tokens(node, comment_types, _body_skip(body))
                body_tokens = leaf_tokens(body, comment_types)
                symbols.append(
                    RawSymbol(
                        qualname=".".join((*stack, name)),
                        kind=SymbolKind.METHOD,
                        public=access == "public",
                        span=span_of(raw_child),
                        sig_tokens=sig_tokens,
                        body_tokens=body_tokens,
                        doc_text=doc,
                    )
                )
            elif node.type == "lexical_declaration" and not stack:
                declarator = next(
                    (c for c in node.named_children if c.type == "variable_declarator"),
                    None,
                )
                if declarator is None:
                    continue
                name_node = declarator.child_by_field_name("name")
                name = child_text(name_node)
                if not name:
                    continue
                sig_tokens = leaf_tokens(node, comment_types)
                symbols.append(
                    RawSymbol(
                        qualname=name,
                        kind=SymbolKind.CONST,
                        public=exported,
                        span=span_of(raw_child),
                        sig_tokens=sig_tokens,
                        body_tokens=(),
                        doc_text=doc,
                    )
                )
            elif (
                node.type
                in (
                    "interface_declaration",
                    "type_alias_declaration",
                    "enum_declaration",
                )
                and not stack
            ):
                name_node = node.child_by_field_name("name")
                name = child_text(name_node)
                if not name:
                    continue
                sig_tokens = leaf_tokens(node, comment_types)
                symbols.append(
                    RawSymbol(
                        qualname=name,
                        kind=SymbolKind.TYPE,
                        public=exported,
                        span=span_of(raw_child),
                        sig_tokens=sig_tokens,
                        body_tokens=(),
                        doc_text=doc,
                    )
                )

    visit(root, ())
    return tuple(symbols)


# ----------------------------------------------------------------------- rust


# PyO3 export attributes: an item carrying one of these is the crate's
# actual Python-facing public surface even without a `pub` keyword, so it
# must count as public for coverage/doc obligations. (`#[pymethods]` marks
# an impl block whose contained methods are all exported -- propagated by
# `_rust_public` via the enclosing container.)
_PYO3_EXPORT_ATTRS = ("pyfunction", "pymodule", "pyclass", "pymethods")


def _rust_has_pub(node: Node) -> bool:
    return any(c.type == "visibility_modifier" for c in node.children)


def _rust_pyo3_export(node: Node) -> bool:
    """True if a PyO3 export attribute precedes `node` (its own item)."""
    sib = node.prev_sibling
    while sib is not None and sib.type in (
        "attribute_item",
        "line_comment",
        "block_comment",
    ):
        if sib.type == "attribute_item" and any(
            marker in child_text(sib) for marker in _PYO3_EXPORT_ATTRS
        ):
            return True
        sib = sib.prev_sibling
    return False


def _rust_public(node: Node, in_pyo3_impl: bool = False) -> bool:
    """Rust publicness: an explicit `pub`, a direct PyO3 export attribute,
    or membership in a `#[pymethods]` impl (all its methods are exported)."""
    return in_pyo3_impl or _rust_has_pub(node) or _rust_pyo3_export(node)


def _walk_rust(root: Node) -> tuple[RawSymbol, ...]:
    comment_types = COMMENT_TYPES["rust"]
    symbols: list[RawSymbol] = []

    def visit(
        container: Node,
        stack: tuple[str, ...],
        in_impl: bool,
        in_pyo3_impl: bool = False,
    ) -> None:
        for node in container.children:
            doc = leading_doc_comment(node, comment_types)

            if node.type == "function_item":
                name = child_text(node.child_by_field_name("name"))
                body = node.child_by_field_name("body")
                skip = ((body.start_byte, body.end_byte),) if body else ()
                sig_tokens = leaf_tokens(node, comment_types, skip)
                body_tokens = leaf_tokens(body, comment_types) if body else ()
                symbols.append(
                    RawSymbol(
                        qualname=".".join((*stack, name)),
                        kind=SymbolKind.METHOD if in_impl else SymbolKind.FUNCTION,
                        public=_rust_public(node, in_pyo3_impl),
                        span=span_of(node),
                        sig_tokens=sig_tokens,
                        body_tokens=body_tokens,
                        doc_text=doc,
                    )
                )
            elif node.type in ("struct_item", "trait_item"):
                name_node = node.child_by_field_name("name")
                name = child_text(name_node)
                sig_tokens = leaf_tokens(node, comment_types)
                symbols.append(
                    RawSymbol(
                        qualname=".".join((*stack, name)),
                        kind=SymbolKind.CLASS,
                        public=_rust_public(node),
                        span=span_of(node),
                        sig_tokens=sig_tokens,
                        body_tokens=(),
                        doc_text=doc,
                    )
                )
                if node.type == "trait_item":
                    body = node.child_by_field_name("body")
                    if body is not None:
                        visit(body, (*stack, name), in_impl=True)
            elif node.type in ("enum_item", "type_item"):
                name_node = node.child_by_field_name("name")
                name = child_text(name_node)
                sig_tokens = leaf_tokens(node, comment_types)
                symbols.append(
                    RawSymbol(
                        qualname=".".join((*stack, name)),
                        kind=SymbolKind.TYPE,
                        public=_rust_public(node),
                        span=span_of(node),
                        sig_tokens=sig_tokens,
                        body_tokens=(),
                        doc_text=doc,
                    )
                )
            elif node.type in ("const_item", "static_item"):
                name_node = node.child_by_field_name("name")
                name = child_text(name_node)
                sig_tokens = leaf_tokens(node, comment_types)
                symbols.append(
                    RawSymbol(
                        qualname=".".join((*stack, name)),
                        kind=SymbolKind.CONST,
                        public=_rust_public(node),
                        span=span_of(node),
                        sig_tokens=sig_tokens,
                        body_tokens=(),
                        doc_text=doc,
                    )
                )
            elif node.type == "impl_item":
                type_node = node.child_by_field_name("type")
                name = child_text(type_node)
                body = node.child_by_field_name("body")
                if body is not None:
                    visit(
                        body,
                        (*stack, name),
                        in_impl=True,
                        in_pyo3_impl=_rust_pyo3_export(node),
                    )
            elif node.type == "mod_item":
                name = child_text(node.child_by_field_name("name"))
                body = node.child_by_field_name("body")
                if body is not None:
                    visit(body, (*stack, name), in_impl)

    visit(root, (), False)
    return tuple(symbols)


# --------------------------------------------------------------------- c/cpp


def _find_declarator_name(node: Node) -> str:
    """Descend through pointer/function declarators to the innermost identifier.

    An out-of-line method definition's declarator (`Widget::draw`) is a
    `qualified_identifier`, not a bare `identifier` -- its own text (with
    the `::` scope kept intact) is the name, not the trailing segment,
    otherwise `Widget::draw` and an unrelated top-level `draw` would
    collapse to the same qualname.
    """
    cur = node
    while cur is not None:
        if cur.type == "qualified_identifier":
            return child_text(cur)
        if cur.type in ("identifier", "field_identifier", "type_identifier"):
            return child_text(cur)
        inner = cur.child_by_field_name("declarator")
        if inner is None:
            for c in cur.children:
                if c.type in ("identifier", "field_identifier"):
                    return child_text(c)
            return ""
        cur = inner
    return ""


def _has_static(node: Node) -> bool:
    return any(
        c.type == "storage_class_specifier" and child_text(c) == "static"
        for c in node.children
    )


def _walk_c_family(root: Node, comment_types: frozenset[str]) -> tuple[RawSymbol, ...]:
    symbols: list[RawSymbol] = []

    def visit(container: Node, stack: tuple[str, ...], access: str) -> None:
        cur_access = access
        for node in container.children:
            if node.type == "access_specifier":
                cur_access = child_text(node)
                continue
            doc = leading_doc_comment(node, comment_types)

            if node.type == "function_definition":
                declarator = node.child_by_field_name("declarator")
                name = _find_declarator_name(declarator) if declarator else ""
                body = node.child_by_field_name("body")
                skip = ((body.start_byte, body.end_byte),) if body else ()
                sig_tokens = leaf_tokens(node, comment_types, skip)
                body_tokens = leaf_tokens(body, comment_types) if body else ()
                symbols.append(
                    RawSymbol(
                        qualname=".".join((*stack, name)),
                        kind=SymbolKind.METHOD if stack else SymbolKind.FUNCTION,
                        public=(cur_access != "private")
                        if stack
                        else not _has_static(node),
                        span=span_of(node),
                        sig_tokens=sig_tokens,
                        body_tokens=body_tokens,
                        doc_text=doc,
                    )
                )
            elif (
                node.type in ("class_specifier", "struct_specifier")
                and node.child_by_field_name("body") is not None
            ):
                name = child_text(node.child_by_field_name("name"))
                if not name:
                    continue
                body = node.child_by_field_name("body")
                sig_tokens = leaf_tokens(node, comment_types, _body_skip(body))
                symbols.append(
                    RawSymbol(
                        qualname=".".join((*stack, name)),
                        kind=SymbolKind.CLASS,
                        public=not _has_static(node),
                        span=span_of(node),
                        sig_tokens=sig_tokens,
                        body_tokens=(),
                        doc_text=doc,
                    )
                )
                default_access = (
                    "private" if node.type == "class_specifier" else "public"
                )
                if body is not None:
                    visit(body, (*stack, name), default_access)
            elif (
                node.type == "enum_specifier"
                and node.child_by_field_name("name") is not None
            ):
                name = child_text(node.child_by_field_name("name"))
                sig_tokens = leaf_tokens(node, comment_types)
                symbols.append(
                    RawSymbol(
                        qualname=".".join((*stack, name)),
                        kind=SymbolKind.TYPE,
                        public=True,
                        span=span_of(node),
                        sig_tokens=sig_tokens,
                        body_tokens=(),
                        doc_text=doc,
                    )
                )
            elif node.type in ("type_definition", "alias_declaration") and not stack:
                name_node = node.child_by_field_name(
                    "name"
                ) or node.child_by_field_name("type")
                name = (
                    _find_declarator_name(node)
                    if name_node is None
                    else child_text(name_node)
                )
                if not name:
                    for c in node.children:
                        if c.type == "type_identifier":
                            name = child_text(c)
                    if not name:
                        continue
                sig_tokens = leaf_tokens(node, comment_types)
                symbols.append(
                    RawSymbol(
                        qualname=name,
                        kind=SymbolKind.TYPE,
                        public=True,
                        span=span_of(node),
                        sig_tokens=sig_tokens,
                        body_tokens=(),
                        doc_text=doc,
                    )
                )
            elif node.type == "declaration" and not stack:
                has_const = any(
                    c.type == "type_qualifier" and child_text(c) == "const"
                    for c in node.children
                )
                if not has_const:
                    continue
                init = next(
                    (c for c in node.children if c.type == "init_declarator"), None
                )
                if init is None:
                    continue
                name_node = init.child_by_field_name("declarator")
                name = _find_declarator_name(name_node) if name_node else ""
                if not name:
                    continue
                sig_tokens = leaf_tokens(node, comment_types)
                symbols.append(
                    RawSymbol(
                        qualname=name,
                        kind=SymbolKind.CONST,
                        public=not _has_static(node),
                        span=span_of(node),
                        sig_tokens=sig_tokens,
                        body_tokens=(),
                        doc_text=doc,
                    )
                )
            elif node.type == "namespace_definition":
                name = child_text(node.child_by_field_name("name"))
                body = node.child_by_field_name("body")
                if body is not None:
                    visit(body, (*stack, name) if name else stack, "public")

    visit(root, (), "public")
    return tuple(symbols)


def _walk_c(root: Node) -> tuple[RawSymbol, ...]:
    return _walk_c_family(root, COMMENT_TYPES["c"])


def _walk_cpp(root: Node) -> tuple[RawSymbol, ...]:
    return _walk_c_family(root, COMMENT_TYPES["cpp"])


def _walk_tsx(root: Node) -> tuple[RawSymbol, ...]:
    return _walk_typescript(root)


_WALKERS = {
    "python": _walk_python,
    "typescript": _walk_typescript,
    "tsx": _walk_tsx,
    "rust": _walk_rust,
    "c": _walk_c,
    "cpp": _walk_cpp,
}


# ------------------------------------------------------------------ imports
#
# frob.cycle needs raw import/include specifiers (unresolved -- "os.path",
# "local.h") to build its dependency graph; this is a second, narrower walk
# per language, kept here next to the symbol walkers so cycle detection
# never has to touch tree-sitter nodes directly (docs/lang.md).


def _imports_python(root: Node) -> tuple[str, ...]:
    results: list[str] = []

    def visit(n: Node) -> None:
        if n.type == "import_statement":
            for child in n.named_children:
                results.append(child_text(child))
        elif n.type == "import_from_statement":
            mod = n.child_by_field_name("module_name")
            if mod is not None:
                results.append(child_text(mod))
        for child in n.children:
            visit(child)

    visit(root)
    return tuple(results)


def _imports_c_family(root: Node) -> tuple[str, ...]:
    """Every `#include`, quoted (local) or angled (system) alike.

    Local-vs-system is not this walker's call -- `resolve_local_import`
    naturally drops system includes (they never resolve to a file under the
    scan root), and callers that just want to *display* every include (the
    outline command) need both.
    """
    results: list[str] = []

    def visit(n: Node) -> None:
        if n.type == "preproc_include":
            path_node = n.named_children[0] if n.named_children else None
            if path_node is not None:
                results.append(child_text(path_node).strip('"<>'))
        for child in n.children:
            visit(child)

    visit(root)
    return tuple(results)


_IMPORT_WALKERS = {
    "python": _imports_python,
    "c": _imports_c_family,
    "cpp": _imports_c_family,
}


# frob:doc docs/lang.md#extraction-api
def extract_imports(tree: Tree, language: str) -> tuple[str, ...]:
    """Raw import/include specifiers for `language` (empty tuple if unsupported)."""
    walker = _IMPORT_WALKERS.get(language)
    if walker is None:
        return ()
    return walker(tree.root_node)


# --------------------------------------------------------------- identifiers
#
# frob.xref needs every identifier-token occurrence (name, line) to find
# usages, not just declarations -- a different shape than RawSymbol, so it
# gets its own narrow walk rather than forcing xref to reach into tree-sitter.

_IDENTIFIER_TYPES: dict[str, frozenset[str]] = {
    "python": frozenset({"identifier"}),
    "c": frozenset({"identifier", "type_identifier"}),
    "cpp": frozenset({"identifier", "type_identifier"}),
}


# frob:doc docs/lang.md#extraction-api
def iter_identifiers(tree: Tree, language: str) -> tuple[tuple[str, int], ...]:
    """(name, 1-based line) for every identifier-like leaf (empty if unsupported)."""
    types = _IDENTIFIER_TYPES.get(language)
    if types is None:
        return ()
    out: list[tuple[str, int]] = []

    def visit(n: Node) -> None:
        if n.type in types:
            txt = child_text(n)
            if txt:
                out.append((txt, span_of(n)[0]))
            return
        for child in n.children:
            visit(child)

    visit(tree.root_node)
    return tuple(out)
