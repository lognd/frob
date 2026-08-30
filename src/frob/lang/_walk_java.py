"""Java raw-to-`RawSymbol` walker (T-1601, epic T-1599 child).

Mirrors `_walk_csharp.py`'s field-based shape (`tree-sitter-java`, as
bundled by `tree-sitter-language-pack`, exposes real named fields --
`name`/`body`/`type`/`parameters`/`declarator` -- verified interactively
before writing any walker code): recursive descent over
`child_by_field_name` lookups, with the shared token/span/doc mechanism
living in `_common.py` as usual. Wired into central dispatch in
`frob.lang._extract`/`frob.lang.__init__` (`_WALKERS`/`COMMENT_TYPES`/
`_EXTENSION_TABLE`, edited alongside this module -- see
docs/modules/lang.md#per-language-walker-notes).

PUBLICNESS (the ticket's own required decision, made explicit rather than
left implicit): a bare Java declaration -- no `public`/`protected`/
`private` keyword at all -- is PACKAGE-PRIVATE, not public; this is the
ticket's named trap (absence of a modifier is meaningful, the opposite of
kotlin's bare-declaration-means-public rule). `_java_public` therefore
checks for the LITERAL `public` keyword among a declaration's `modifiers`
children and nothing else -- mirroring `_cs_public`'s enumerated-NON-
public shape exactly, because Java's package-private default is exactly
as "not visible to an external caller" as its explicit `protected`/
`private` keywords are. The one carve-out (mirroring C#'s own interface
member rule) is an INTERFACE member with no modifier of its own: the
language itself makes a modifier-less interface method/constant public by
definition (Java has required this since interfaces existed, long before
Java 8 added `default`/`static`/`private` interface methods, which DO
require an explicit modifier to read as non-public) -- `implicit_public`
reverses only that true no-modifier-at-all case, never an explicit
non-public modifier.

INTERFACES WITH DEFAULT METHODS: a `default` method inside an interface
carries the literal `default` keyword as one of its `modifiers` children,
same shape as `static`/`public`/etc; it is walked as an ordinary METHOD
symbol like any other interface member (implicit-public carve-out
applies identically -- `default` does not change publicness, only
`private`/`protected` would, and a `default` interface method has no
modifier-less form that means anything other than public).

INNER AND ANONYMOUS CLASSES: a `class_declaration`/`interface_
declaration`/`enum_declaration` nested directly inside another type's
body is walked as a CLASS-shaped qualname container exactly like a
top-level type (recursion, not a special case) -- the qualname stack
naturally nests (`Outer.Inner`). An ANONYMOUS class body (`new Runnable()
{ ... }`, an `object_creation_expression`'s own `class_body` field) is
never reached at all: this walker only recurses into a container's
declared body when dispatching a container of a NAMED declaration kind
(`_JAVA_CONTAINER_DECLS`), and an anonymous class body lives inside a
`block` (a method body), which this walker never descends into -- the
same disclosed limitation `_walk_csharp.py` documents for partial-class
fragments: not every reachable node is symbol-shaped, and an anonymous
class has no stable qualname to hang a symbol on in the first place.

ANNOTATIONS: `@Deprecated`/`@Override`/etc are `marker_annotation`/
`annotation` children of a declaration's `modifiers` node, sitting
alongside (not instead of) the real visibility keywords -- `_java_
has_modifier`'s scan for a literal keyword type simply never matches an
annotation node's own type (`marker_annotation`/`annotation`), so an
annotation can never be mistaken for a modifier keyword and never
suppresses a real one.

JAVADOC: `/** ... */` is `tree-sitter-java`'s `block_comment` node type,
identically to a plain `/* ... */` comment -- `_common._strip_comment_
delims` already strips the `/**`/`*/` delimiters and every continuation
line's leading `*` for any block comment, so no javadoc-specific stripping
is needed here (verified interactively: a doc comment's `**` extra star
and per-line `*` gutter both come off through the SAME code path a plain
block comment already uses).
"""

from __future__ import annotations

from tree_sitter import Node

from frob.lang._common import (
    _body_skip,
    _canonical_tokens,
    _child_text,
    _leading_doc_comment,
    _leaf_tokens,
    _span_of,
)
from frob.lang._models import RawSymbol, SymbolKind

# frob:ticket T-1601
# frob:doc docs/modules/lang.md#per-language-walker-notes
# Java's two comment node types: `//` line comments and `/* */`/`/** */`
# block comments (javadoc included) both collapse onto `block_comment` --
# mirrors kotlin's `line_comment`/`multiline_comment` pair, not C#'s
# single-type grammar (verified interactively, module docstring's own
# exploration).
COMMENT_TYPES = frozenset({"line_comment", "block_comment"})

# Declaration node types this walker treats as CLASS-shaped qualname
# containers: `class`/`interface`/`enum` all carry a `name` field and a
# `body` field whose members get their own symbols (module docstring's
# inner-class note: nesting is recursion, not a special case).
_JAVA_CONTAINER_DECLS = frozenset(
    {"class_declaration", "interface_declaration", "enum_declaration"}
)


def _java_has_modifier(node: Node, keyword: str) -> bool:
    """True if `node` carries a literal `keyword` modifier (a `modifiers`
    child whose own child's node TYPE is the literal keyword text)."""
    return any(
        c.type == "modifiers" and any(gc.type == keyword for gc in c.children)
        for c in node.children
    )


def _java_public(node: Node, *, implicit_public: bool = False) -> bool:
    """Java publicness (module docstring): the literal `public` keyword
    among `node`'s direct `modifiers` children -- the package-private
    default (no modifier at all) and every explicit non-public modifier
    (`protected`/`private`) are NOT public. `implicit_public` (module
    docstring's interface-member carve-out) reverses ONLY the true
    no-modifier-at-all case: an interface member the language itself
    makes public by definition still needs an explicit `private`/
    `protected` modifier to read as non-public -- it does not make
    `default`/`static` on an interface member non-public, only the
    true-default (no access modifier at all) case."""
    if _java_has_modifier(node, "public"):
        return True
    if not implicit_public:
        return False
    has_any_access_modifier = any(
        _java_has_modifier(node, kw) for kw in ("protected", "private")
    )
    return not has_any_access_modifier


def _java_class_symbol(
    node: Node, stack: tuple[str, ...], doc: str
) -> tuple[RawSymbol, Node, str] | None:
    """`(symbol, body, name)` for a class/interface/enum declaration, or
    `None` if unnamed or bodyless."""
    name_node = node.child_by_field_name("name")
    body = node.child_by_field_name("body")
    if name_node is None or body is None:
        return None
    name = _child_text(name_node)
    symbol = RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.CLASS,
        public=_java_public(node),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES, _body_skip(body)),
        body_tokens=(),
        doc_text=doc,
    )
    return symbol, body, name


def _java_method_symbol(
    node: Node, stack: tuple[str, ...], doc: str, *, in_interface: bool
) -> RawSymbol | None:
    """A `method_declaration`/`constructor_declaration` `RawSymbol`
    (always `METHOD` -- Java has no free-function concept outside a
    type), or `None` if unnamed."""
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    name = _child_text(name_node)
    body = node.child_by_field_name("body")
    skip = _body_skip(body)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.METHOD,
        public=_java_public(node, implicit_public=in_interface),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES, skip),
        body_tokens=_leaf_tokens(body, COMMENT_TYPES) if body else (),
        doc_text=doc,
        body_norm=_canonical_tokens(body, COMMENT_TYPES) if body else (),
    )


def _java_const_field_symbol(
    node: Node, stack: tuple[str, ...], doc: str, *, in_interface: bool
) -> list[RawSymbol]:
    """`CONST` `RawSymbol`s for a `static final` (or bare interface-field,
    implicitly `public static final` in Java) `field_declaration` -- a
    plain instance field is NOT symbol-shaped (mirrors `_walk_csharp.py`'s
    identical const-field-only rule); one `field_declaration` can declare
    MULTIPLE comma-separated `variable_declarator`s (`static final int A,
    B;`), so this returns a list rather than a single optional symbol."""
    is_const = in_interface or (
        _java_has_modifier(node, "static") and _java_has_modifier(node, "final")
    )
    if not is_const:
        return []
    out: list[RawSymbol] = []
    for declarator in node.children:
        if declarator.type != "variable_declarator":
            continue
        name_node = declarator.child_by_field_name("name")
        if name_node is None:
            continue
        name = _child_text(name_node)
        out.append(
            RawSymbol(
                qualname=".".join((*stack, name)),
                kind=SymbolKind.CONST,
                public=_java_public(node, implicit_public=in_interface),
                span=_span_of(node),
                sig_tokens=_leaf_tokens(node, COMMENT_TYPES),
                body_tokens=(),
                doc_text=doc,
            )
        )
    return out


def _java_dispatch(
    node: Node,
    stack: tuple[str, ...],
    symbols: list[RawSymbol],
    *,
    in_interface: bool,
) -> None:
    """Build and append the symbol(s) for one Java declaration node, and
    recurse into class/interface/enum bodies."""
    doc = _leading_doc_comment(node, COMMENT_TYPES)
    if node.type in _JAVA_CONTAINER_DECLS:
        built = _java_class_symbol(node, stack, doc)
        if built is not None:
            symbol, body, name = built
            symbols.append(symbol)
            # frob:invariant terminates reason="body is node's own body field child, and node is itself a child of the container passed to the caller's _java_visit, so body is a proper descendant of that container in the finite tree-sitter parse tree" measure="container's subtree depth strictly decreases"  # noqa: E501
            _java_visit(
                body,
                (*stack, name),
                symbols,
                in_interface=node.type == "interface_declaration",
            )
    elif node.type in ("method_declaration", "constructor_declaration") and stack:
        symbol = _java_method_symbol(node, stack, doc, in_interface=in_interface)
        if symbol is not None:
            symbols.append(symbol)
    elif node.type == "field_declaration" and stack:
        symbols.extend(
            _java_const_field_symbol(node, stack, doc, in_interface=in_interface)
        )


def _java_visit(
    container: Node,
    stack: tuple[str, ...],
    symbols: list[RawSymbol],
    *,
    in_interface: bool = False,
) -> None:
    """Recursive descent appending Java symbols across `container`'s
    direct children."""
    for node in container.children:
        _java_dispatch(node, stack, symbols, in_interface=in_interface)


# frob:ticket T-1601
# frob:tests tests/test_lang.py::TestJava.test_walks_class_and_method
# frob:tests tests/test_lang.py::TestJava.test_package_private_method_is_not_public
# frob:tests tests/test_lang.py::TestJava.test_static_final_field_is_a_const_symbol
# frob:tests tests/test_lang.py::TestJava.test_plain_field_is_not_extracted
# frob:tests tests/test_lang.py::TestJava.test_enum_is_a_class_symbol
# frob:tests tests/test_lang.py::TestJava.test_inner_class_is_a_transparent_qualname_container  # noqa: E501
# frob:tests \
# tests/test_lang.py::TestJava.test_interface_default_method_is_implicitly_public
# frob:tests tests/test_lang.py::TestJava.test_leading_javadoc_comment_binds_as_doc_text
def _walk_java(root: Node) -> tuple[RawSymbol, ...]:
    """Every Java symbol: classes/interfaces/enums (`CLASS`), their
    methods/constructors (`METHOD`), and their `static final` (or
    implicitly-const interface) fields (`CONST`) -- see module docstring
    for the publicness and inner/anonymous-class decisions this walker
    makes explicit."""
    symbols: list[RawSymbol] = []
    _java_visit(root, (), symbols)
    return tuple(symbols)
