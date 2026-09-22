"""C# raw-to-`RawSymbol` walker (T-1600, epic T-1599 child).

Mirrors `_walk_typescript.py`'s field-based shape (`tree-sitter-c-sharp`,
as bundled by `tree-sitter-language-pack`, exposes real named fields --
`name`/`body`/`type`/`returns`/`parameters` -- unlike kotlin's almost-
field-free grammar, verified interactively before writing any walker
code): recursive descent over `child_by_field_name` lookups, with the
shared token/span/doc mechanism living in `_common.py` as usual. Wired
into central dispatch in `frob.lang._extract`/`frob.lang.__init__`
(`_WALKERS`/`COMMENT_TYPES`/`_EXTENSION_TABLE`, edited alongside this
module -- see docs/modules/lang.md#per-language-walker-notes).

PUBLICNESS (the ticket's own required decision, made explicit rather
than left implicit): C# has four real access modifiers (`public`/
`internal`/`protected`/`private`) plus TWO silent defaults --
`internal` for a top-level type, `private` for a type member -- neither
of which is `public`. `_cs_public` therefore checks for the LITERAL
`public` keyword among a declaration's `modifier` children and nothing
else: `internal` (explicit or default) is deliberately NOT treated as
public here, even though it is visible assembly-wide, because frob's
own public/private axis models "this is API surface a caller outside
this file should be able to depend on" (doc coverage, call-graph
public-boundary stopping, etc.) -- an assembly-internal type is exactly
as invisible to an EXTERNAL caller as a private one, so folding it in
with `public` would silently under-report doc obligations the same way
counting `protected` as public would. This mirrors kotlin's rule shape
(an enumerated NON-public set) rather than rust's (an enumerated public
set), because C#'s two silent defaults are exactly as "not public" as
its explicit non-public keywords -- there is no bare-declaration case
that means public the way a bare kotlin declaration does.

PROPERTIES VS FIELDS (the ticket's own second required decision): a
`property_declaration` (`public int Count { get; set; }`) is C#'s real
API-surface member shape -- it is what a caller outside the class
actually sees and depends on, accessors included -- so it is extracted
as a `SymbolKind.CONST` `RawSymbol` (no first-class "property" kind
exists; `CONST` is the closest existing bucket for a named, non-callable
class member, the same rung kotlin's top-level `val`/`var` occupies). A
plain `field_declaration`, by contrast, is normally private implementation
state in idiomatic C# (a `public` field is a code-smell the language
itself discourages in favor of properties) -- but it is not IGNORED
outright: a field marked `const` (a real, language-enforced compile-time
constant, unlike a plain field) is extracted as `SymbolKind.CONST` too,
mirroring every other grammar's own `CONST` rule (python's `UPPER_CASE`,
rust's `const`/`static`, C/C++'s file-scope `const`). A non-const field
is NOT extracted as a symbol at all -- a disclosed, deliberate omission
(not every C# declaration is symbol-shaped; a private mutable field is
implementation detail this walker treats the same way python treats an
un-annotated local variable).

PARTIAL CLASSES: each `partial class Foo { ... }` fragment is walked
independently, producing one `RawSymbol` per fragment sharing the SAME
qualname -- no cross-file/cross-fragment merging is attempted (frob.lang
has no multi-fragment symbol-identity concept for any grammar today).
This is a disclosed limitation, not a walker bug: doc/test coverage
still applies per-fragment, which is directionally correct (each
fragment's own members still need their own doc/test edges) even though
a `frob:doc` written once "for the whole partial type" has no single
anchor point.

NULLABLE REFERENCE TYPES: `string?`/`int?` annotations live inside a
declaration's TYPE subtree, never inside its NAME (`identifier`) field
-- `child_by_field_name("name")` never touches the nullable-annotated
type text at all, so nullable annotations cannot confuse name/symbol
extraction (verified interactively before writing any walker code, per
the ticket's own named risk).
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

# frob:ticket T-1600
# frob:doc docs/modules/lang.md#per-language-walker-notes
# C#'s one comment node type -- `//`, `/* */`, and `///` XML-doc comments
# all collapse to the same `comment` node type in this grammar (verified
# interactively, module docstring's exploration).
COMMENT_TYPES = frozenset({"comment"})

# Declaration node types this walker treats as CLASS-shaped qualname
# containers: `class`/`struct`/`interface` all carry a `name` field and a
# `body` field (`declaration_list`) whose members get their own symbols.
_CONTAINER_DECLS = frozenset(
    {"class_declaration", "struct_declaration", "interface_declaration"}
)

# frob:ticket T-4514
# Unity's own reflection-based dispatch (T-4514, epic T-4513): MonoBehaviour
# lifecycle methods (Awake/Start/Update/... and the OnCollision*/OnTrigger*
# physics-callback families) have NO visible call site anywhere in user
# code -- the Unity engine invokes them by name through its own component
# message system every frame/physics-step/enable-disable transition. A
# private (or even a totally unmodified, C#-default-private) lifecycle
# method is therefore syntactically indistinguishable from genuinely dead
# code to any caller-graph-based detector, unless something marks it
# reachable independent of any in-repo call token.
_CS_UNITY_LIFECYCLE_METHODS = frozenset(
    {
        "Awake",
        "Start",
        "Update",
        "FixedUpdate",
        "LateUpdate",
        "OnEnable",
        "OnDisable",
        "OnDestroy",
        "OnCollisionEnter",
        "OnCollisionEnter2D",
        "OnCollisionExit",
        "OnCollisionExit2D",
        "OnCollisionStay",
        "OnCollisionStay2D",
        "OnTriggerEnter",
        "OnTriggerEnter2D",
        "OnTriggerExit",
        "OnTriggerExit2D",
        "OnTriggerStay",
        "OnTriggerStay2D",
    }
)

#: attribute NAMES (the `attribute`'s own `name` field, module docstring
#: sibling note) that make Unity's editor tooling invoke a static method
#: through its own reflection scan rather than a visible call site --
#: `[MenuItem]` (Editor menu dispatch) and `[InitializeOnLoad]` (loaded on
#: editor startup/domain reload, applied to either the declaring class or,
#: for the static-constructor idiom, the method itself).
_CS_UNITY_ENTRY_ATTRIBUTES = frozenset({"MenuItem", "InitializeOnLoad"})


def _cs_has_modifier(node: Node, keyword: str) -> bool:
    """True if `node` carries a literal `keyword` modifier."""
    return any(
        c.type == "modifier" and any(gc.type == keyword for gc in c.children)
        for c in node.children
    )


def _cs_public(node: Node, *, implicit_public: bool = False) -> bool:
    """C# publicness (module docstring): the literal `public` keyword
    among `node`'s direct `modifier` children -- both silent defaults
    (top-level `internal`, member `private`) and every other explicit
    modifier (`internal`/`protected`/`protected internal`/`private`/
    `private protected`) are NOT public. `implicit_public` (module
    docstring's interface-member carve-out) reverses ONLY the true silent-
    default case: an interface member the language itself makes public by
    definition with no modifier of its own still needs an explicit
    non-public modifier (C# 8+ `private`/`protected` default-interface-
    method members) to read as non-public -- it does not make `internal`/
    `protected` on an interface member public, only the true-default
    (no-modifier-at-all) case."""
    has_public = _cs_has_modifier(node, "public")
    if has_public:
        return True
    if not implicit_public:
        return False
    has_any_access_modifier = any(
        _cs_has_modifier(node, kw) for kw in ("internal", "protected", "private")
    )
    return not has_any_access_modifier


# frob:ticket T-4514
def _cs_attribute_names(node: Node) -> frozenset[str]:
    """Every attribute NAME (`[Foo(...)]` -> `"Foo"`) attached to `node`
    (T-4514) -- C#'s grammar hangs an `attribute_list` as a plain
    positional child of the declaration it decorates (no field name, the
    module's own `_cs_dispatch` exploration confirmed), each holding one
    or more `attribute` children whose own `name` field is the identifier
    tree-sitter labels. Returns the empty set for an undecorated node
    (the common case), never `None` -- callers always get a `frozenset`
    they can test membership against directly."""
    names: set[str] = set()
    for c in node.children:
        if c.type != "attribute_list":
            continue
        for attr in c.children:
            if attr.type != "attribute":
                continue
            name_node = attr.child_by_field_name("name")
            if name_node is not None:
                names.add(_child_text(name_node))
    return frozenset(names)


# frob:ticket T-4514
def _cs_is_unity_entry_point(node: Node, name: str) -> bool:
    """True if `node` (a `method_declaration`) is one of Unity's own
    reflection-dispatched entry shapes (T-4514, module-level docstring):
    a MonoBehaviour lifecycle method by NAME (`_CS_UNITY_LIFECYCLE_
    METHODS` -- Unity calls these through its component message system,
    never a visible in-repo call token, regardless of the method's own
    declared access modifier), a coroutine (its `returns` field is the
    literal identifier `IEnumerator` -- every coroutine becomes reachable
    the moment ANY `StartCoroutine(...)` call site names it, which this
    single-file walker cannot itself trace back to; marking every
    `IEnumerator`-returning method reachable is the same fail-open
    direction `_cs_public`'s own interface carve-out already takes,
    trading a small over-approximation for never flagging a live
    coroutine as dead), or carries a `[MenuItem]`/`[InitializeOnLoad]`
    attribute (`_CS_UNITY_ENTRY_ATTRIBUTES` -- the Unity Editor's own
    menu/domain-reload dispatch, likewise invoked with no visible call
    site)."""
    if name in _CS_UNITY_LIFECYCLE_METHODS:
        return True
    returns_node = node.child_by_field_name("returns")
    if returns_node is not None and _child_text(returns_node) == "IEnumerator":
        return True
    return bool(_cs_attribute_names(node) & _CS_UNITY_ENTRY_ATTRIBUTES)


def _cs_class_symbol(
    node: Node, stack: tuple[str, ...], doc: str
) -> tuple[RawSymbol, Node, str] | None:
    """`(symbol, body, name)` for a class/struct/interface declaration,
    or `None` if unnamed or bodyless."""
    name_node = node.child_by_field_name("name")
    body = node.child_by_field_name("body")
    if name_node is None or body is None:
        return None
    name = _child_text(name_node)
    # T-4514: a class-level [InitializeOnLoad] is Unity Editor's own
    # domain-reload dispatch (its static constructor runs with no visible
    # in-repo call site) -- same fail-open direction as the method-level
    # carve-out `_cs_is_unity_entry_point` applies below.
    is_unity_entry = "InitializeOnLoad" in _cs_attribute_names(node)
    symbol = RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.CLASS,
        public=_cs_public(node) or is_unity_entry,
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES, _body_skip(body)),
        body_tokens=(),
        doc_text=doc,
    )
    return symbol, body, name


def _cs_method_symbol(
    node: Node, stack: tuple[str, ...], doc: str, *, in_interface: bool
) -> RawSymbol | None:
    """A `method_declaration` `RawSymbol` (always a `METHOD` -- C# has no
    free-function concept outside a type), or `None` if unnamed."""
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    name = _child_text(name_node)
    body = node.child_by_field_name("body")
    skip = _body_skip(body)
    # T-4514: a MonoBehaviour lifecycle method, coroutine, or Editor
    # [MenuItem]/[InitializeOnLoad] target is reachable through Unity's own
    # reflection dispatch regardless of its declared access modifier --
    # `public` is this walker's ONE existing "externally reachable"
    # channel (no bespoke entry-point field exists on `RawSymbol`), so a
    # Unity entry point is marked public here the same way an implicit
    # interface member already is above.
    public = _cs_public(node, implicit_public=in_interface) or _cs_is_unity_entry_point(
        node, name
    )
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.METHOD,
        public=public,
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES, skip),
        body_tokens=_leaf_tokens(body, COMMENT_TYPES) if body else (),
        doc_text=doc,
        body_norm=_canonical_tokens(body, COMMENT_TYPES) if body else (),
    )


def _cs_property_symbol(
    node: Node, stack: tuple[str, ...], doc: str, *, in_interface: bool
) -> RawSymbol | None:
    """A `property_declaration` `RawSymbol` (module docstring: properties
    are C#'s real API-surface member shape, mapped onto `SymbolKind.
    CONST`), or `None` if unnamed."""
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    name = _child_text(name_node)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.CONST,
        public=_cs_public(node, implicit_public=in_interface),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


# frob:waive DUP001 reason="the declarator-walk-with-identifier-fallback shape here is \
# genuinely small and grammar-specific (C#'s variable_declaration -> \
# variable_declarator -> name field, with a positional identifier-child fallback for a \
# grammar edge case) -- the flagged 95%-similar matches (pii_structural's ts/rust \
# string-literal-text helpers, _walk_c.py's _const_symbol) share only the generic \
# 'find-declarator-then-extract-name' SHAPE, not the actual grammar-specific logic; \
# extracting a shared helper across three unrelated subsystems (vet/pii_structural, \
# lang/c, lang/csharp) for a five-line name-lookup would couple them for no real reuse \
# benefit"
def _cs_const_field_symbol(
    node: Node, stack: tuple[str, ...], doc: str
) -> RawSymbol | None:
    """A `const`-modified `field_declaration` `RawSymbol` (module
    docstring: a plain, non-const field is not symbol-shaped), or `None`
    if not `const` or unnamed."""
    if not _cs_has_modifier(node, "const"):
        return None
    var_decl = next(
        (c for c in node.children if c.type == "variable_declaration"), None
    )
    if var_decl is None:
        return None
    declarator = next(
        (c for c in var_decl.children if c.type == "variable_declarator"), None
    )
    if declarator is None:
        return None
    name_node = declarator.child_by_field_name("name")
    if name_node is None:
        for c in declarator.children:
            if c.type == "identifier":
                name_node = c
                break
    if name_node is None:
        return None
    name = _child_text(name_node)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.CONST,
        public=_cs_public(node),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


def _cs_enum_symbol(node: Node, stack: tuple[str, ...], doc: str) -> RawSymbol | None:
    """An `enum_declaration` `RawSymbol` (`SymbolKind.TYPE`, mirrors
    rust's `enum` -> `TYPE` mapping), or `None` if unnamed."""
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    name = _child_text(name_node)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.TYPE,
        public=_cs_public(node),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


def _cs_dispatch(
    node: Node,
    stack: tuple[str, ...],
    symbols: list[RawSymbol],
    *,
    in_interface: bool,
) -> None:
    """Build and append the symbol(s) for one C# declaration node, and
    recurse into class/struct/interface bodies and namespaces."""
    doc = _leading_doc_comment(node, COMMENT_TYPES)
    if node.type in _CONTAINER_DECLS:
        built = _cs_class_symbol(node, stack, doc)
        if built is not None:
            symbol, body, name = built
            symbols.append(symbol)
            # frob:invariant terminates reason="body is node's own body field child, and node is itself a child of the container passed to the caller's _cs_visit, so body is a proper descendant of that container in the finite tree-sitter parse tree" measure="container's subtree depth strictly decreases"  # noqa: E501
            _cs_visit(
                body,
                (*stack, name),
                symbols,
                in_interface=node.type == "interface_declaration",
            )
    elif node.type == "method_declaration" and stack:
        _append(symbols, _cs_method_symbol(node, stack, doc, in_interface=in_interface))
    elif node.type == "property_declaration" and stack:
        _append(
            symbols, _cs_property_symbol(node, stack, doc, in_interface=in_interface)
        )
    elif node.type == "field_declaration" and stack:
        _append(symbols, _cs_const_field_symbol(node, stack, doc))
    elif node.type == "enum_declaration":
        _append(symbols, _cs_enum_symbol(node, stack, doc))
    elif node.type == "namespace_declaration":
        name_node = node.child_by_field_name("name")
        body = node.child_by_field_name("body")
        name = _child_text(name_node) if name_node else ""
        if body is not None:
            # frob:invariant terminates reason="body is node's own body field child, and node is itself a child of the container passed to the caller's _cs_visit" measure="container's subtree depth strictly decreases"  # noqa: E501
            _cs_visit(
                body, (*stack, name) if name else stack, symbols, in_interface=False
            )


def _cs_visit(
    container: Node,
    stack: tuple[str, ...],
    symbols: list[RawSymbol],
    *,
    in_interface: bool = False,
) -> None:
    """Recursive descent appending C# symbols. A `file_scoped_namespace_
    declaration` (`namespace Foo.Bar;`, no braces) rebinds `stack` for
    every remaining sibling in `container` -- unlike every other
    container form here, it has no `body` field to recurse into; its
    "body" IS the rest of the compilation unit."""
    active_stack = stack
    for node in container.children:
        if node.type == "file_scoped_namespace_declaration":
            name_node = node.child_by_field_name("name")
            name = _child_text(name_node) if name_node else ""
            active_stack = (*stack, name) if name else stack
            continue
        _cs_dispatch(node, active_stack, symbols, in_interface=in_interface)


def _append(symbols: list[RawSymbol], symbol: RawSymbol | None) -> None:
    """Append `symbol` to `symbols` when it is not `None`."""
    if symbol is not None:
        symbols.append(symbol)


# frob:ticket T-1600
def _walk_csharp(root: Node) -> tuple[RawSymbol, ...]:
    """Every C# symbol: classes/structs/interfaces (`CLASS`), their
    methods (`METHOD`), their properties and `const` fields (`CONST`),
    and enums (`TYPE`) -- see module docstring for the publicness and
    property-vs-field decisions this walker makes explicit."""
    symbols: list[RawSymbol] = []
    _cs_visit(root, (), symbols)
    return tuple(symbols)
