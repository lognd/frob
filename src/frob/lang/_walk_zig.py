"""Zig raw-to-`RawSymbol` walker (T-1603, epic T-1599 child).

GRAMMAR SHAPE: like `_walk_kotlin.py` (not `_walk_csharp.py`/`_walk_java.py`),
`tree-sitter-language-pack`'s "zig" grammar exposes NO named fields --
`node.child_by_field_name(...)` returns `None` for every node type here
(verified interactively before writing any walker code) -- so every lookup
below is positional/type-based (`_zig_child_of_type`, mirroring `_walk_
kotlin.py`'s `_kt_child_of_type` exactly). A second, Zig-specific quirk
neither kotlin nor any prior adapter has: `pub` is not a modifier CHILD of
the declaration it marks -- it is a bare SIBLING token immediately
preceding a top-level/container-member `Decl` node (`source_file`/a
`ContainerDecl`'s body are flat sequences of `[doc_comment?, pub?, Decl]`
runs, never a `Decl` wrapping its own visibility marker) -- so publicness
must be tracked while iterating a CONTAINER's children, not read off the
`Decl` node in isolation the way every other adapter's modifier-scan does.

PUBLICNESS (the ticket's own required decision): `pub` is Zig's explicit,
opt-in visibility marker -- ABSENT means private, the same shape rust's
`pub` keyword takes (an enumerated PUBLIC set, not kotlin's enumerated
NON-public set) and the opposite of kotlin's public-by-default rule.

COMPTIME BLOCKS (the ticket's own required decision): a top-level
`ComptimeDecl` (`comptime { ... }`) is a bare, unnamed side-effecting
block -- it has no declaration name of its own to hang a `RawSymbol` on,
so it is never walked for symbols, a disclosed limitation mirroring how
`_walk_python.py` never walks a function body's nested closures. Any
`pub const`/`pub fn` written INSIDE a comptime block (a genuinely unusual
but legal Zig construct) is therefore invisible to this walker -- the
same "not every reachable node is symbol-shaped" disclosure `_walk_
csharp.py`/`_walk_java.py` each make for their own dialect's anonymous-
scope construct.

ERROR UNIONS IN SIGNATURES (the ticket's own required decision): a
fallible function's `!ReturnType` marker lives INSIDE `FnProto`'s own
child sequence (the `!` token sits between the parameter list and the
return-type expression, both ordinary positional children) -- no special
handling is needed at all, since `sig_tokens` captures every leaf under
`FnProto` uniformly; `mayFail() !i32` and a plain `() i32` function
naturally produce DIFFERENT `sig_tokens` streams, which is the correct,
desired behavior (they really are different signatures), not something
requiring normalization.

DOC COMMENTS (the ticket's own required decision): tree-sitter-zig gives
triple-slash `///` its OWN node type, `doc_comment` -- genuinely distinct
from `line_comment` (which covers both plain `//` and file-level `//!`),
unlike every prior C-style-comment adapter where `///`/`//`/`/* */` all
collapse onto one or two shared types. `COMMENT_TYPES` (exported to
`frob.lang._extract` for general comment-leaf extraction, so `pf.comments`
still surfaces every comment regardless of kind) therefore covers BOTH
types, but `_ZIG_DOC_COMMENT_TYPES` -- the narrower set this module's OWN
`doc_text` binding calls (`_zig_leading_doc`) pass to `_leading_doc_
comment` -- covers ONLY `doc_comment`: a plain `//` or `//!` comment
immediately above a declaration is deliberately NEVER captured as that
declaration's `doc_text`, matching the ticket's own "doc comments distinct
from ordinary comments" framing exactly.
"""

from __future__ import annotations

from tree_sitter import Node

from frob.lang._common import (
    _canonical_tokens,
    _child_text,
    _leading_doc_comment,
    _leaf_tokens,
    _span_of,
)
from frob.lang._models import RawSymbol, SymbolKind

# frob:ticket T-1603
# frob:doc docs/modules/lang.md#per-language-walker-notes
# `doc_comment` (`///`) is its own node type, distinct from `line_comment`
# (`//`/`//!`) -- see module docstring's "doc comments" decision. This is
# the set `frob.lang._extract` uses for GENERAL comment-leaf extraction
# (every comment becomes a `RawComment`, regardless of doc status).
COMMENT_TYPES = frozenset({"line_comment", "doc_comment"})

# frob:ticket T-1603
# The narrower set this module's OWN `doc_text` binding uses (module
# docstring) -- a plain `//`/`//!` comment never counts as a symbol's doc
# text, only a real `///` one does.
_ZIG_DOC_COMMENT_TYPES = frozenset({"doc_comment"})

# Declaration node types this walker treats as CLASS/TYPE-shaped qualname
# containers once found inside a `VarDecl`'s value expression (module
# docstring: `struct`/`union` are CLASS-shaped, `enum` is TYPE-shaped,
# mirroring `_walk_c.py`'s own struct-vs-enum split).
_ZIG_CLASS_CONTAINER_KINDS = frozenset({"struct", "union"})
_ZIG_TYPE_CONTAINER_KINDS = frozenset({"enum"})

# The single-child expression-wrapper chain a `VarDecl`'s value hides a
# `ContainerDecl` behind (`ErrorUnionExpr` -> `SuffixExpr` -> the real
# node) -- walked positionally since neither wrapper node carries a name
# of its own worth stopping at.
_ZIG_EXPR_CHAIN_TYPES = frozenset({"ErrorUnionExpr", "SuffixExpr"})


def _zig_child_of_type(node: Node | None, type_name: str) -> Node | None:
    """The first DIRECT child of `node` with tree-sitter type `type_name`
    -- positional stand-in for a named-field lookup (module docstring;
    mirrors `_walk_kotlin.py`'s `_kt_child_of_type`)."""
    if node is None:
        return None
    for c in node.children:
        if c.type == type_name:
            return c
    return None


def _zig_leading_doc(anchor: Node) -> str:
    """`doc_text` for the declaration whose left edge is `anchor` -- pass
    the `pub` token when present, else the `Decl`/container-member node
    itself, so a `///` comment separated from its target only by `pub`
    (module docstring: `pub` is a SIBLING, not a `Decl` child) still binds
    correctly. Uses `_ZIG_DOC_COMMENT_TYPES` (module docstring's doc-vs-
    ordinary-comment decision), never the wider `COMMENT_TYPES`."""
    return _leading_doc_comment(anchor, _ZIG_DOC_COMMENT_TYPES)


def _zig_container_decl(vardecl: Node) -> Node | None:
    """The `ContainerDecl` a `VarDecl`'s value expression wraps (module
    docstring's expression-chain walk), or `None` if this `VarDecl` is an
    ordinary value/const, not a struct/union/enum type definition."""
    children = vardecl.children
    eq_index = next((i for i, c in enumerate(children) if c.type == "="), None)
    if eq_index is None or eq_index + 1 >= len(children):
        return None
    node: Node | None = children[eq_index + 1]
    while node is not None and node.type in _ZIG_EXPR_CHAIN_TYPES:
        node = node.children[0] if node.children else None
    return node if node is not None and node.type == "ContainerDecl" else None


def _zig_function_symbol(
    fnproto: Node,
    body: Node | None,
    stack: tuple[str, ...],
    *,
    in_container: bool,
    public: bool,
    doc: str,
) -> RawSymbol | None:
    """A `FnProto` `RawSymbol` (`METHOD` inside a struct/union body, else
    `FUNCTION`), or `None` if unnamed."""
    name_node = _zig_child_of_type(fnproto, "IDENTIFIER")
    if name_node is None:
        return None
    name = _child_text(name_node)
    skip = ((body.start_byte, body.end_byte),) if body else ()
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.METHOD if in_container else SymbolKind.FUNCTION,
        public=public,
        span=_span_of(fnproto),
        sig_tokens=_leaf_tokens(fnproto, COMMENT_TYPES, skip),
        body_tokens=_leaf_tokens(body, COMMENT_TYPES) if body else (),
        doc_text=doc,
        body_norm=_canonical_tokens(body, COMMENT_TYPES) if body else (),
    )


def _zig_container_symbol(
    vardecl: Node,
    container_decl: Node,
    stack: tuple[str, ...],
    *,
    public: bool,
    doc: str,
) -> tuple[RawSymbol, Node, str] | None:
    """`(symbol, body, name)` for a struct/union/enum type definition
    (module docstring), or `None` if unnamed."""
    name_node = _zig_child_of_type(vardecl, "IDENTIFIER")
    if name_node is None:
        return None
    name = _child_text(name_node)
    decl_type_node = _zig_child_of_type(container_decl, "ContainerDeclType")
    keyword = _child_text(decl_type_node) if decl_type_node else ""
    kind = SymbolKind.TYPE if keyword in _ZIG_TYPE_CONTAINER_KINDS else SymbolKind.CLASS
    symbol = RawSymbol(
        qualname=".".join((*stack, name)),
        kind=kind,
        public=public,
        span=_span_of(vardecl),
        sig_tokens=_leaf_tokens(vardecl, COMMENT_TYPES, _body_span(container_decl)),
        body_tokens=(),
        doc_text=doc,
    )
    return symbol, container_decl, name


def _body_span(container_decl: Node) -> tuple[tuple[int, int], ...]:
    """Byte-range to mask out of a container type's own `sig_tokens` --
    everything from its opening `{` onward, mirroring `_body_skip`'s
    shape for a node with no single `body` field to read positionally."""
    brace = _zig_child_of_type(container_decl, "{")
    if brace is None:
        return ()
    return ((brace.start_byte, container_decl.end_byte),)


def _zig_const_symbol(
    vardecl: Node, stack: tuple[str, ...], *, public: bool, doc: str
) -> RawSymbol | None:
    """A plain top-level/member `const`/`var` binding `RawSymbol`
    (`CONST` -- Zig has no first-class type-alias keyword distinct from
    an ordinary `const NAME = Expr;` binding, module docstring), or
    `None` if unnamed."""
    name_node = _zig_child_of_type(vardecl, "IDENTIFIER")
    if name_node is None:
        return None
    name = _child_text(name_node)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.CONST,
        public=public,
        span=_span_of(vardecl),
        sig_tokens=_leaf_tokens(vardecl, COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


def _zig_dispatch_decl(
    decl: Node,
    stack: tuple[str, ...],
    symbols: list[RawSymbol],
    *,
    in_container: bool,
    public: bool,
    doc: str,
) -> None:
    """Build and append the symbol(s) for one `Decl` node, and recurse
    into a struct/union/enum's own body."""
    fnproto = _zig_child_of_type(decl, "FnProto")
    if fnproto is not None:
        body = _zig_child_of_type(decl, "Block")
        symbol = _zig_function_symbol(
            fnproto, body, stack, in_container=in_container, public=public, doc=doc
        )
        if symbol is not None:
            symbols.append(symbol)
        return
    vardecl = _zig_child_of_type(decl, "VarDecl")
    if vardecl is None:
        return
    container_decl = _zig_container_decl(vardecl)
    if container_decl is not None:
        built = _zig_container_symbol(
            vardecl, container_decl, stack, public=public, doc=doc
        )
        if built is not None:
            symbol, body, name = built
            symbols.append(symbol)
            # frob:invariant terminates reason="body is reached by descending through vardecl's own value-expression chain, and vardecl is itself a child of the Decl passed to the caller's _zig_visit, so body is a proper descendant of the container passed to that visit call" measure="container's subtree depth strictly decreases"  # noqa: E501
            _zig_visit(body, (*stack, name), symbols, in_container=True)
        return
    symbol = _zig_const_symbol(vardecl, stack, public=public, doc=doc)
    if symbol is not None:
        symbols.append(symbol)


def _zig_visit(
    container: Node,
    stack: tuple[str, ...],
    symbols: list[RawSymbol],
    *,
    in_container: bool,
) -> None:
    """Recursive descent appending Zig symbols under `container`'s direct
    children -- threads a `pending_pub`/`doc_anchor` pair across sibling
    tokens (module docstring: `pub` and `///` are both bare SIBLINGS of
    the `Decl` they mark, not its children)."""
    pending_pub = False
    doc_anchor: Node | None = None
    for node in container.children:
        if node.type == "pub":
            pending_pub = True
            doc_anchor = node
            continue
        if node.type == "Decl":
            anchor = doc_anchor if doc_anchor is not None else node
            _zig_dispatch_decl(
                node,
                stack,
                symbols,
                in_container=in_container,
                public=pending_pub,
                doc=_zig_leading_doc(anchor),
            )
            pending_pub = False
            doc_anchor = None
            continue
        # Any other node (a comptime block, a comment, a container field,
        # punctuation) neither carries nor extends a pending pub/doc run.
        pending_pub = False
        doc_anchor = None


# frob:ticket T-1603
# frob:tests tests/test_lang.py::TestZig.test_walks_top_level_function
# frob:tests tests/test_lang.py::TestZig.test_function_without_pub_is_not_public
# frob:tests tests/test_lang.py::TestZig.test_struct_and_method
# frob:tests tests/test_lang.py::TestZig.test_enum_is_a_type_symbol
# frob:tests tests/test_lang.py::TestZig.test_top_level_const_is_a_const_symbol
# frob:tests \
# tests/test_lang.py::TestZig.test_error_union_return_type_is_captured_in_signature
# frob:tests tests/test_lang.py::TestZig.test_triple_slash_doc_comment_binds_as_doc_text
# frob:tests tests/test_lang.py::TestZig.test_plain_comment_does_not_bind_as_doc_text
# frob:tests tests/test_lang.py::TestZig.test_comptime_block_is_not_walked_for_symbols
def _walk_zig(root: Node) -> tuple[RawSymbol, ...]:
    """Every Zig symbol: top-level/struct-or-union-member functions
    (`FUNCTION`/`METHOD`), struct/union type definitions (`CLASS`), enum
    type definitions (`TYPE`), and top-level/member `const`/`var`
    bindings (`CONST`) -- see module docstring for the publicness,
    comptime-block, error-union, and doc-comment decisions this walker
    makes explicit."""
    symbols: list[RawSymbol] = []
    _zig_visit(root, (), symbols, in_container=False)
    return tuple(symbols)
