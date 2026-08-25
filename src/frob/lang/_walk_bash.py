"""Bash/Shell raw-to-`RawSymbol` walker (T-1604, epic T-1599 child).

Mirrors `_walk_kotlin.py`'s shape one node-kind at a time: a small,
positional (no named-field lookups needed here -- `tree-sitter-bash`'s
`function_definition`/`variable_assignment` nodes expose plain
positional children) walker over `tree-sitter-language-pack`'s bundled
`bash` grammar, feeding `frob.lang._extract`'s `_WALKERS`/`COMMENT_TYPES`
dispatch tables (wired in `frob.lang.__init__`'s `_EXTENSION_TABLE` and
`frob.lang._extract`, both edited alongside this module -- see
docs/modules/lang.md#per-language-walker-notes).

WHAT IS A PUBLIC SYMBOL HERE (the ticket's own required decision, made
explicit rather than left implicit): bash has no visibility keyword at
all -- every function and variable is name-visible to anything that
sources the file. The one convention shell authors and shellcheck itself
already lean on is the leading-underscore name -- `_helper` reads as
"private by convention" the same way python's leading underscore does.
`_bash_public` adopts exactly that rule: a symbol is public unless its
own name starts with `_`. This is a naming convention, not a language
enforcement mechanism (bash cannot stop a caller from invoking `_helper`
directly) -- documented here rather than silently assumed, per the
ticket's own instruction to decide and document what publicness means
for this language before writing any walker code.

WHAT COUNTS AS A SYMBOL: bash has no class/type declarations at all (no
`SymbolKind.CLASS`/`SymbolKind.TYPE` member is ever emitted here) and
much real behavior lives in bare top-level statements this walker does
NOT turn into symbols (a loop, an `if`, a bare command) -- per the
ticket's own framing, "much meaningful code is top-level statements
rather than named symbols" is a genuine, disclosed limitation of what a
symbol-shaped obligation graph can cover for this language, not a walker
bug. Two node shapes DO become symbols: `function_definition` (both the
`name() { ... }` and `function name { ... }` forms share this one node
type in this grammar) and a top-level `variable_assignment` -- bare
(`FOO=bar`) or wrapped in a `declaration_command` (`export`/`readonly`/
`declare`/`local` -- e.g. `export FOO=bar`, `readonly BAZ=1`) -- mapped
onto `SymbolKind.CONST`, mirroring `_walk_kotlin.py`'s top-level
`val`/`var` -> `SymbolKind.CONST` mapping. A `variable_assignment`
nested inside a function body is deliberately NOT walked as a top-level
symbol (mirrors kotlin's `not in_class` guard on `property_declaration`)
-- it is local state, not a name a caller outside the function can see.

COMMENT SYNTAX: bash has exactly one comment form, `# ...` to end of
physical line -- no block-comment analogue at all (the ticket's own
"hash-only line comments, no block comments" framing). This makes a
`frob:` directive continuation (a `# frob:tests` line ending in a
trailing backslash, folded onto the next `# ...` line) the ONLY way a
directive can span more than one physical
line here, which is exactly what `frob.lang._extract`'s block-comment
chaining (`_block_ends`) already handles language-agnostically once this
module's `COMMENT_TYPES` names bash's one comment node type -- no
special-cased continuation logic needed in this file.
"""

from __future__ import annotations

from tree_sitter import Node, Tree
from tree_sitter_language_pack import get_parser

from frob.lang._common import (
    _canonical_tokens,
    _child_text,
    _leading_doc_comment,
    _leaf_tokens,
    _span_of,
)
from frob.lang._models import RawSymbol, SymbolKind

# tree-sitter-bash's grammar name inside tree-sitter-language-pack.
_GRAMMAR_NAME = "bash"

# frob:ticket T-1604
# frob:doc docs/modules/lang.md#per-language-walker-notes
# Bash's one comment node type -- `# ...` to end of physical line, no
# block-comment form exists in the grammar (module docstring).
COMMENT_TYPES = frozenset({"comment"})

# Wrapper node types a top-level `variable_assignment` may be nested
# directly under (`export FOO=bar`, `readonly BAZ=1`, `declare -r X=1`,
# `local Y=2`) -- all share the single `declaration_command` node type in
# this grammar (verified interactively, module docstring's exploration).
_DECLARATION_WRAPPER = "declaration_command"


# frob:ticket T-1604
# frob:waive WIRE001 follow_up="T-2900" reason="deliberately test-only, same \
# posture as kotlin's parse_kotlin (T-0613) before T-0723's dispatch wiring landed -- \
# frob.lang.__init__'s _parse dispatch loads every tree-sitter grammar through its own \
# generic get_parser(grammar_name) chokepoint, so this helper has no production call \
# site to wire; kept only so this module's own tests can exercise the parse step in \
# isolation from the full _walk_bash walk"
def _parse_bash(source: bytes) -> Tree:
    """Parse bash source bytes into a tree-sitter `Tree` via the language
    pack's bundled bash grammar (no separate `tree-sitter-bash` pin
    needed, same as kotlin -- `tree_sitter_language_pack.get_parser`
    resolves the bundled grammar directly). Private (unlike kotlin's
    `parse_kotlin`/`raw_kotlin_tree` pair, which T-0613 exposed publicly
    ahead of T-0723's own dispatch wiring): `frob.lang.__init__`'s `_parse`
    dispatch loads every tree-sitter grammar through its own generic
    `get_parser(grammar_name)` chokepoint, so this helper has no real
    production caller of its own to wire -- kept only for this module's
    own tests to exercise the parse step in isolation from the full
    `_walk_bash` walk."""
    parser = get_parser(_GRAMMAR_NAME)
    return parser.parse(source)


def _bash_public(name: str) -> bool:
    """Bash publicness (module docstring): public unless the name itself
    starts with `_` -- the one visibility convention shell authors and
    shellcheck already lean on; bash has no visibility keyword at all."""
    return not name.startswith("_")


def _bash_function_name(node: Node) -> str:
    """The function's own name: the first `word` child, present in both
    the `name() { ... }` and `function name { ... }` grammar forms."""
    for c in node.children:
        if c.type == "word":
            return _child_text(c)
    return ""


def _bash_function_symbol(node: Node) -> RawSymbol:
    """A `function_definition` `RawSymbol` -- always a top-level
    `SymbolKind.FUNCTION` (bash has no method/class nesting concept)."""
    name = _bash_function_name(node)
    body = next((c for c in node.children if c.type == "compound_statement"), None)
    doc = _leading_doc_comment(node, COMMENT_TYPES)
    skip = ((body.start_byte, body.end_byte),) if body else ()
    return RawSymbol(
        qualname=name,
        kind=SymbolKind.FUNCTION,
        public=_bash_public(name),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES, skip),
        body_tokens=_leaf_tokens(body, COMMENT_TYPES) if body else (),
        doc_text=doc,
        body_norm=_canonical_tokens(body, COMMENT_TYPES) if body else (),
    )


def _bash_assignment_name(node: Node) -> str:
    """The assigned variable's own name -- `variable_assignment`'s first
    `variable_name` child."""
    for c in node.children:
        if c.type == "variable_name":
            return _child_text(c)
    return ""


def _bash_const_symbol(node: Node, doc: str) -> RawSymbol | None:
    """A top-level `variable_assignment` `RawSymbol` (`SymbolKind.CONST`,
    mirrors kotlin's top-level `val`/`var` mapping), or `None` if no name
    could be recovered."""
    name = _bash_assignment_name(node)
    if not name:
        return None
    return RawSymbol(
        qualname=name,
        kind=SymbolKind.CONST,
        public=_bash_public(name),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


# frob:ticket T-1604
# frob:tests tests/test_lang.py::TestBash.test_walks_top_level_function
# frob:tests tests/test_lang.py::TestBash.test_private_symbol_is_not_public
# frob:tests tests/test_lang.py::TestBash.test_top_level_variable_assignment
# frob:tests tests/test_lang.py::TestBash.test_nested_assignment_is_not_a_symbol
# frob:tests tests/test_lang.py::TestBash.test_leading_comment_binds_as_doc_text
def _walk_bash(root: Node) -> tuple[RawSymbol, ...]:
    """Every bash symbol: top-level function definitions and top-level
    variable assignments (bare or `export`/`readonly`/`declare`/`local`-
    wrapped). Nested assignments (inside a function body) are
    deliberately excluded -- see module docstring."""
    symbols: list[RawSymbol] = []
    for node in root.children:
        doc = _leading_doc_comment(node, COMMENT_TYPES)
        if node.type == "function_definition":
            symbols.append(_bash_function_symbol(node))
        elif node.type == "variable_assignment":
            built = _bash_const_symbol(node, doc)
            if built is not None:
                symbols.append(built)
        elif node.type == _DECLARATION_WRAPPER:
            inner = next(
                (c for c in node.children if c.type == "variable_assignment"), None
            )
            if inner is not None:
                built = _bash_const_symbol(inner, doc)
                if built is not None:
                    symbols.append(built)
    return tuple(symbols)
