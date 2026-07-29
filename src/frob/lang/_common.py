"""Shared, language-agnostic tree-sitter helpers (the walker skeleton).

Every grammar tree-sitter hands back is formatting-insensitive at the leaf
level: whitespace is never itself a node. That single property is what lets
``_leaf_tokens`` double as the entire "normalized token" story for the sig/
body digest contract in docs/modules/graph.md -- no per-language pretty-printer is
needed, only a byte-range exclusion list (a symbol's own body, a docstring
statement) and a comment-type-name set. Keeping that trick here, instead of
re-deriving it in each of the five per-language walkers in ``_extract.py``,
is what keeps this package free of the five-way duplication the task spec
explicitly forbids.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/lang/_common.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"
# frob:waive ARCH102 reason="T-0871 demoted child_text/iter_cpp_functions to \
# _child_text/_iter_cpp_functions (frob-exports: genuinely private, used only within \
# frob.lang's own walkers, never a cross-package import) -- the reduced public surface \
# crossed the clustering heuristic's report threshold as a side effect of the \
# demotion, not a new design problem; remaining exports \
# (child_by_field/export_tree/flatten_tree) are the same shared tree-sitter primitives \
# this module's docstring already scopes it to"

from __future__ import annotations

from tree_sitter import Node

from frob.lang._models import RawSymbol, TreeNode

ByteRange = tuple[int, int]

# Cap on exported-tree size (node count): R4's Zhang-Shasha kernel is
# O(n*m*min(depth,leaves)) -- fine for a clone-candidate function body, not
# fine for a 50k-node file. `export_tree` truncates deeper descent past
# this many nodes rather than let one huge body blow up a comparison; the
# caller (frob.dup._pipeline) treats a truncated tree as still-comparable
# (truncation is symmetric per input, not silently dropped).
_MAX_EXPORT_NODES = 4000


# frob:doc docs/modules/lang.md#primitives
# frob:waive COV007 reason="docs/modules/lang.md's Primitives section is a deliberate, \
# per-function architecture doc of this module's internal tree-sitter helpers (T-0524) \
# -- each private primitive gets its own named bullet there by design, not a \
# caller-side public-API summary"
def _collapse_ws(text: str) -> str:
    """Whitespace-collapse doc text so reflow never changes ``doc_text``."""
    return " ".join(text.split())


def _body_skip(body: Node | None) -> tuple[ByteRange, ...]:
    """A skip-range tuple excluding `body`'s byte span, or empty if absent."""
    if body is None:
        return ()
    return ((body.start_byte, body.end_byte),)


def _in_skip_range(node: Node, skip_ranges: tuple[ByteRange, ...]) -> bool:
    """True if `node`'s byte span is fully covered by one skip range."""
    for start, end in skip_ranges:
        if node.start_byte >= start and node.end_byte <= end:
            return True
    return False


# frob:doc docs/modules/lang.md#primitives
# frob:waive COV007 reason="docs/modules/lang.md's Primitives section is a deliberate, \
# per-function architecture doc of this module's internal tree-sitter helpers (T-0524) \
# -- each private primitive gets its own named bullet there by design, not a \
# caller-side public-API summary"
def _leaf_tokens(
    node: Node,
    comment_types: frozenset[str],
    skip_ranges: tuple[ByteRange, ...] = (),
) -> tuple[str, ...]:
    """Collect leaf-node text under `node`, skipping comments and exclusions.

    Leaves are tree-sitter tokens with no children -- whitespace is never
    represented as a node, so this sequence is stable across reformatting
    and only changes when a real token (identifier, keyword, literal,
    punctuation) is added, removed, or renamed.
    """
    tokens: list[str] = []

    def walk(n: Node) -> None:
        if _in_skip_range(n, skip_ranges):
            return
        if n.child_count == 0:
            if n.type in comment_types:
                return
            text = n.text
            if text is not None:
                tokens.append(text.decode("utf-8", errors="replace"))
            return
        for child in n.children:
            walk(child)

    walk(node)
    return tuple(tokens)


# T-0334: the tag every identifier-shaped leaf (a name, whether a
# declaration or a reference) collapses to in `_canonical_tokens` --
# structural bucketing needs "some name was used here", not which name.
_IDENT_TAG = "IDENT"

# T-0334: the tag every literal-shaped leaf (number, string, bool, null)
# collapses to -- same rationale as `_IDENT_TAG`.
_LIT_TAG = "LIT"

# Leaf node types tree-sitter emits for a bare name reference/declaration,
# across all five grammars this package walks. Anonymous per-grammar names
# for "this is an identifier" differ (`identifier` everywhere, but also
# `type_identifier`/`field_identifier`/`property_identifier` depending on
# grammar and position) -- collecting them here means `_canonical_tokens`
# does not need per-language branching to find them.
_IDENT_LEAF_TYPES = frozenset(
    {
        "identifier",
        "type_identifier",
        "field_identifier",
        "property_identifier",
        "shorthand_property_identifier",
        "shorthand_property_identifier_pattern",
        "namespace_identifier",
        "primitive_type",
    }
)

# Leaf node types for a literal value, across all five grammars. Deliberately
# collapses `1`, `1.0`, `"x"`, `true`, `None`/`null`/`nullptr` alike -- the
# goal is a structural "a literal sat here" signal for cross-grammar
# bucketing, not a faithful literal-kind distinction (that distinction is
# already fully preserved in `body_tokens`, which `body_norm` supplements
# rather than replaces).
_LITERAL_LEAF_TYPES = frozenset(
    {
        "integer",
        "float",
        "number",
        "string",
        "string_content",
        "char_literal",
        "number_literal",
        "string_literal",
        "raw_string_literal",
        "true",
        "false",
        "none",
        "null",
        "nullptr",
        "undefined",
    }
)

# T-0334: keyword/punctuation leaf node types, across python/typescript/
# rust/c/cpp, mapped onto a shared vocabulary tag. Tree-sitter's anonymous
# (unnamed) leaf nodes carry their own literal spelling as `node.type`
# (python's `for` keyword node has `type == "for"`), so this table's keys
# are literal keyword/punctuation spellings pooled across all five grammars
# -- a spelling absent from one grammar simply never matches when walking
# that grammar's tree. Entries intentionally group semantically-equivalent
# constructs across grammars (python `def/class` colon-block vs
# typescript/rust/c/cpp brace-block both map their block delimiter to
# `BLOCK_OPEN`/`BLOCK_CLOSE`-adjacent tags where possible, `for ... in`
# (python) and `for ... of` (typescript) both land on `FOR_KW`/`ITER_KW`)
# -- that grouping is the entire point: it is what lets `frob.dup`'s R1-R3
# bucket the same logic written in two languages into the same bucket
# instead of two disjoint ones (see `RawSymbol.body_norm`'s docstring).
_CANONICAL_VOCAB: dict[str, str] = {
    # function/method declaration
    "def": "FUNC_KW",
    "function": "FUNC_KW",
    "fn": "FUNC_KW",
    "lambda": "FUNC_KW",
    "async": "FUNC_KW",
    # type/class declaration
    "class": "TYPE_KW",
    "struct": "TYPE_KW",
    "trait": "TYPE_KW",
    "interface": "TYPE_KW",
    "enum": "TYPE_KW",
    "impl": "TYPE_KW",
    "typedef": "TYPE_KW",
    "union": "TYPE_KW",
    "type": "TYPE_KW",
    # loops
    "for": "FOR_KW",
    "while": "WHILE_KW",
    "loop": "WHILE_KW",
    "do": "WHILE_KW",
    "in": "ITER_KW",
    "of": "ITER_KW",
    # conditionals
    "if": "IF_KW",
    "else": "ELSE_KW",
    "elif": "ELSE_KW",
    "switch": "SWITCH_KW",
    "match": "SWITCH_KW",
    "case": "CASE_KW",
    "default": "CASE_KW",
    # control transfer
    "return": "RETURN_KW",
    "break": "BREAK_KW",
    "continue": "CONTINUE_KW",
    "yield": "YIELD_KW",
    "pass": "NOOP_KW",
    # exceptions
    "try": "TRY_KW",
    "except": "CATCH_KW",
    "catch": "CATCH_KW",
    "finally": "FINALLY_KW",
    "raise": "THROW_KW",
    "throw": "THROW_KW",
    # local declaration
    "let": "DECL_KW",
    "const": "DECL_KW",
    "var": "DECL_KW",
    "static": "DECL_KW",
    "mut": "DECL_KW",
    "new": "NEW_KW",
    # imports
    "import": "IMPORT_KW",
    "from": "IMPORT_KW",
    "use": "IMPORT_KW",
    "include": "IMPORT_KW",
    "#include": "IMPORT_KW",
    # bracketing / block structure
    "{": "BLOCK_OPEN",
    "}": "BLOCK_CLOSE",
    "(": "PAREN_OPEN",
    ")": "PAREN_CLOSE",
    "[": "BRACKET_OPEN",
    "]": "BRACKET_CLOSE",
    ":": "COLON",
    ";": "STMT_END",
    ",": "COMMA",
    ".": "DOT",
    "->": "ARROW",
    "=>": "ARROW",
    "::": "SCOPE",
    # assignment
    "=": "ASSIGN_OP",
    "+=": "ASSIGN_OP",
    "-=": "ASSIGN_OP",
    "*=": "ASSIGN_OP",
    "/=": "ASSIGN_OP",
    # comparison
    "==": "CMP_OP",
    "!=": "CMP_OP",
    ">": "CMP_OP",
    "<": "CMP_OP",
    ">=": "CMP_OP",
    "<=": "CMP_OP",
    # arithmetic
    "+": "ARITH_OP",
    "-": "ARITH_OP",
    "*": "ARITH_OP",
    "/": "ARITH_OP",
    "%": "ARITH_OP",
    # boolean
    "&&": "BOOL_OP",
    "||": "BOOL_OP",
    "and": "BOOL_OP",
    "or": "BOOL_OP",
    "not": "BOOL_OP",
    "!": "BOOL_OP",
}


def _canonical_tokens(
    node: Node,
    comment_types: frozenset[str],
    skip_ranges: tuple[ByteRange, ...] = (),
) -> tuple[str, ...]:
    """`_leaf_tokens`-shaped walk of `node`, but each leaf is mapped onto a
    shared cross-grammar vocabulary tag (`RawSymbol.body_norm`, T-0334)
    instead of kept as literal text.

    Identifier- and literal-shaped leaves collapse to `_IDENT_TAG`/
    `_LIT_TAG`; keyword/punctuation leaves map through `_CANONICAL_VOCAB`;
    anything neither table recognizes falls back to `OTHER:<node.type>` so
    an unmapped grammar construct degrades to a harmless bucket-miss (still
    distinct per node type, never silently merged into an unrelated tag)
    rather than being dropped or crashing.
    """
    tokens: list[str] = []

    def walk(n: Node) -> None:
        if _in_skip_range(n, skip_ranges):
            return
        if n.child_count == 0:
            if n.type in comment_types:
                return
            if n.type in _IDENT_LEAF_TYPES:
                tokens.append(_IDENT_TAG)
            elif n.type in _LITERAL_LEAF_TYPES:
                tokens.append(_LIT_TAG)
            else:
                tokens.append(_CANONICAL_VOCAB.get(n.type, f"OTHER:{n.type}"))
            return
        for child in n.children:
            walk(child)

    walk(node)
    return tuple(tokens)


# frob:doc docs/modules/lang.md#primitives
# frob:waive COV007 reason="docs/modules/lang.md's Primitives section is a deliberate, \
# per-function architecture doc of this module's internal tree-sitter helpers (T-0524) \
# -- each private primitive gets its own named bullet there by design, not a \
# caller-side public-API summary"
def _strip_comment_delims(raw: str) -> str:
    """Strip `//`, `///`, `/* */`, `/** */`, and leading `*` from one comment."""
    text = raw.strip()
    if text.startswith("/**"):
        text = text[3:]
        if text.endswith("*/"):
            text = text[:-2]
    elif text.startswith("/*"):
        text = text[2:]
        if text.endswith("*/"):
            text = text[:-2]
    elif text.startswith("///"):
        text = text[3:]
    elif text.startswith("//"):
        text = text[2:]
    elif text.startswith("#"):
        text = text[1:]
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("*"):
            stripped = stripped[1:]
        lines.append(stripped)
    return " ".join(lines)


# frob:doc docs/modules/lang.md#primitives
# frob:waive COV007 reason="docs/modules/lang.md's Primitives section is a deliberate, \
# per-function architecture doc of this module's internal tree-sitter helpers (T-0524) \
# -- each private primitive gets its own named bullet there by design, not a \
# caller-side public-API summary"
def _leading_doc_comment(
    node: Node,
    comment_types: frozenset[str],
) -> str:
    """Gather the contiguous comment block directly above `node` as doc text.

    Contiguous means each comment sibling ends on the line immediately
    before the next token starts -- a blank line breaks the chain, matching
    the "immediately above" rule in the token contract.
    """
    parent = node.parent
    if parent is None:
        return ""
    siblings = parent.children
    idx = siblings.index(node)
    collected: list[str] = []
    expected_end_row = node.start_point[0]
    i = idx - 1
    while i >= 0:
        sib = siblings[i]
        if sib.type not in comment_types:
            break
        if sib.end_point[0] + 1 < expected_end_row:
            break
        collected.append(_strip_comment_delims(_child_text(sib)))
        expected_end_row = sib.start_point[0]
        i -= 1
    collected.reverse()
    return _collapse_ws(" ".join(collected))


# frob:doc docs/modules/lang.md#primitives
# frob:waive COV007 reason="docs/modules/lang.md's Primitives section is a deliberate, \
# per-function architecture doc of this module's internal tree-sitter helpers (T-0524) \
# -- each private primitive gets its own named bullet there by design, not a \
# caller-side public-API summary"
def _span_of(node: Node) -> tuple[int, int]:
    """1-based inclusive (start_line, end_line) span for `node`.

    Some tokens (e.g. a rust `///` line comment whose text includes the
    trailing newline) report an `end_point` at column 0 of the following
    line -- that is a lexer artifact, not real content on that line, so it
    is folded back onto the line the content actually occupies.
    """
    end_row = node.end_point[0]
    if node.end_point[1] == 0 and end_row > node.start_point[0]:
        end_row -= 1
    return (node.start_point[0] + 1, end_row + 1)


# frob:doc docs/modules/lang.md#primitives
def child_by_field(node: Node, field: str) -> Node | None:
    """`node.child_by_field_name(field)` -- a one-line convenience so every
    per-language walker (`frob.arch`, `frob.dup._legacy`) shares the same
    field-lookup call instead of each keeping its own copy."""
    return node.child_by_field_name(field)


# frob:doc docs/modules/lang.md#primitives
def _child_text(node: Node | None) -> str:
    """Decode a node's own text, or '' if the node is absent -- a programmer
    convenience for optional field lookups (missing name is a grammar bug,
    not a runtime error worth a Result)."""
    if node is None or node.text is None:
        return ""
    return node.text.decode("utf-8", errors="replace")


# frob:doc docs/modules/lang.md#primitives
def export_tree(node: Node, comment_types: frozenset[str]) -> TreeNode:
    """A `TreeNode` snapshot of `node`'s subtree, comments stripped.

    Leaf nodes label themselves with their decoded text (so `x` and `y`
    are distinguishable leaves, matching the rename-cost story in
    `frob-core`'s `_apted_similarity`); internal nodes label themselves
    with their grammar type (`if_statement`, `binary_operator`, ...), which
    is what makes the tree comparable across alpha-renamed-but-
    structurally-identical bodies. Truncates past `_MAX_EXPORT_NODES` total
    nodes (see the module-level cap's docstring) by stopping descent, not
    by silently dropping the whole subtree.

    Each `TreeNode.field` (T-0495) is looked up via the PARENT's
    `field_name_for_child` against the child's original (unfiltered)
    index, so a stripped comment sibling never shifts a later child's
    field-name lookup.
    """
    budget = [_MAX_EXPORT_NODES]

    def build(n: Node, field: str | None) -> TreeNode:
        span = (n.start_byte, n.end_byte)
        if budget[0] <= 0:
            return TreeNode(label=n.type, span=span, field=field)
        budget[0] -= 1
        kids = [
            (c, n.field_name_for_child(i))
            for i, c in enumerate(n.children)
            if c.type not in comment_types
        ]
        if not kids:
            return _leaf_tree_node(n, field)
        return TreeNode(
            label=n.type,
            span=span,
            field=field,
            children=tuple(build(c, f) for c, f in kids),
        )

    return build(node, None)


def _leaf_tree_node(n: Node, field: str | None = None) -> TreeNode:
    """A `TreeNode` for a childless node: its decoded text, else its grammar type."""
    span = (n.start_byte, n.end_byte)
    if n.child_count == 0:
        text = n.text
        label = text.decode("utf-8", errors="replace") if text else n.type
        return TreeNode(label=label, span=span, field=field)
    return TreeNode(label=n.type, span=span, field=field)


# frob:doc docs/modules/lang.md#primitives
# frob:waive COV007 reason="docs/modules/lang.md's Primitives section is a deliberate, \
# per-function architecture doc of this module's internal tree-sitter helpers (T-0524) \
# -- each private primitive gets its own named bullet there by design, not a \
# caller-side public-API summary"
def _find_enclosing_symbol(
    span: tuple[int, int], symbols: tuple[RawSymbol, ...]
) -> str | None:
    """Deepest (narrowest-span) symbol whose span fully contains `span`.

    Span-comparison logic, not tree-sitter-node logic -- both the
    tree-sitter comment walk (`frob.lang._extract`) and the text-based
    strata walk (`frob.lang._walk_strata`) bind a comment to its enclosing
    symbol by comparing `RawSymbol.span` tuples, so this lives here once
    instead of twice.
    """
    best: RawSymbol | None = None
    for sym in symbols:
        if sym.span[0] <= span[0] and sym.span[1] >= span[1]:
            width = sym.span[1] - sym.span[0]
            if best is None or width < (best.span[1] - best.span[0]):
                best = sym
    return best.qualname if best is not None else None


# Lines a symbol's start may sit past a directive block's end line and
# still count as "following" (T-0402 audit finding G4, docs/audits/graph.md).
# A single blank line between the block and the `def` is the common case
# this window must always cover; widened from 2 to 3 so a SECOND blank
# line (or one blank line plus a decorator whose node start is offset by
# one) does not silently drop the def out of the window and rebind the
# directive onto a bare enclosing/module fallback instead (dsl.py's
# consumer trusts whatever this returns -- see G4 for the full
# blast-radius). Still a fixed heuristic, not a real "same paragraph"
# check: `frob.graph.dsl` is the right place to additionally flag (as a
# `MalformedDirective`) a directive that resolves to no following/enclosing
# symbol at all for a verb that semantically requires one; that consumer
# lives outside this package's scope.
_FOLLOWING_SYMBOL_WINDOW = 3


# frob:doc docs/modules/lang.md#primitives
# frob:ticket T-0434
# frob:waive COV007 reason="docs/modules/lang.md's Primitives section is a deliberate, \
# per-function architecture doc of this module's internal tree-sitter helpers (T-0524) \
# -- each private primitive gets its own named bullet there by design, not a \
# caller-side public-API summary"
def _find_following_symbol(
    span: tuple[int, int], symbols: tuple[RawSymbol, ...]
) -> str | None:
    """Symbol starting within `_FOLLOWING_SYMBOL_WINDOW` lines after `span`'s end.

    Earliest match wins.

    Shared by the tree-sitter and strata comment walks -- see
    `_find_enclosing_symbol`. `span[1]` need not be the comment's own end
    line: `frob.lang._extract._extract_comments` passes a stacked-comment
    *block*'s end line instead (T-0100 -- `_block_ends`/`_is_trailing_comment`
    there), so a directive several lines above a `def` still resolves as
    long as every intervening line is either another comment in the same
    contiguous block or up to `_FOLLOWING_SYMBOL_WINDOW` blank lines. This
    function only ever compares the span tuple it is given; the
    block-vs-own-line distinction is entirely the caller's concern.
    """
    end = span[1]
    best: RawSymbol | None = None
    for sym in symbols:
        if end < sym.span[0] <= end + _FOLLOWING_SYMBOL_WINDOW:
            if best is None or sym.span[0] < best.span[0]:
                best = sym
    return best.qualname if best is not None else None


# frob:doc docs/modules/lang.md#primitives
def flatten_tree(node: TreeNode) -> tuple[list[str], list[int]]:
    """`(labels, parents)` flat arrays for `frob_core._apted_similarity`.

    Preorder walk; `parents[i]` is the index of node `i`'s parent, `-1` for
    the root -- the exact shape `frob-core`'s Zhang-Shasha kernel expects
    (it derives its own postorder internally, so any traversal order that
    keeps parent indices consistent works).
    """
    labels: list[str] = []
    parents: list[int] = []

    def walk(n: TreeNode, parent_idx: int) -> None:
        my_idx = len(labels)
        labels.append(n.label)
        parents.append(parent_idx)
        for child in n.children:
            walk(child, my_idx)

    walk(node, -1)
    return labels, parents


def _cpp_declarator_name(node: Node) -> str:
    """Innermost name of a C/C++ declarator, unwrapping `function_declarator`."""
    if node.type == "function_declarator":
        name_node = node.child_by_field_name("declarator")
        return _child_text(name_node) if name_node else _child_text(node)
    return _child_text(node)


def _cpp_free_function(node: Node) -> tuple[Node, str] | None:
    """`(node, name)` if `node` is a C/C++ function/declaration, else None."""
    if node.type not in ("function_definition", "declaration"):
        return None
    decl = node.child_by_field_name("declarator")
    if decl is None:
        return None
    return (node, _cpp_declarator_name(decl))


def _cpp_class_methods(node: Node) -> list[tuple[Node, str]]:
    """`(node, ClassName::method)` for every method in a class/struct `node`."""
    name_node = node.child_by_field_name("name")
    class_name = _child_text(name_node) if name_node else _child_text(node)
    body = node.child_by_field_name("body")
    if body is None:
        return []
    out: list[tuple[Node, str]] = []
    for m in body.named_children:
        fn = _cpp_free_function(m)
        if fn is not None:
            out.append((fn[0], f"{class_name}::{fn[1]}"))
    return out


# frob:doc docs/modules/lang.md#primitives
def _iter_cpp_functions(root: Node) -> tuple[tuple[Node, str], ...]:
    """(node, qualified_name) for every C/C++ function under `root`.

    Shared by `frob.arch` (long-function/god-class checks) and `frob.dup`
    (the legacy Type-1/2 scanner) so a C/C++ function-declaration walk lives
    in exactly one place. `ClassName::method` qualnames for one level of
    class/struct nesting; free functions are unqualified.
    """
    out: list[tuple[Node, str]] = []
    for n in root.named_children:
        if n.type in ("class_specifier", "struct_specifier"):
            out.extend(_cpp_class_methods(n))
            continue
        fn = _cpp_free_function(n)
        if fn is not None:
            out.append(fn)
    return tuple(out)
