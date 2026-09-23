"""CSS/SCSS raw-to-`RawSymbol` walker (T-5303, WEBSEC/A11Y/SEO substrate leaf).

A11Y contrast-ratio, target-size, and outline:none checks (T-5146-3,
T-5146-4) and SEO's markup checks (T-5147-3) all need `.css`/`.scss` files
to reach `frob.lang.parse_file` instead of returning
`LangError.UnsupportedLanguage` -- this module is that wiring's walker
half, mirroring `_walk_bash.py`'s and `_walk_zig.py`'s shape: a small,
one-node-kind-at-a-time walk over `tree-sitter-language-pack`'s bundled
`css`/`scss` grammars, feeding `frob.lang._extract`'s `_WALKERS`/
`COMMENT_TYPES` dispatch tables (wired in `frob.lang.__init__`'s
`_EXTENSION_TABLE` and `frob.lang._extract`, both edited alongside this
module -- see docs/modules/lang.md#per-language-walker-notes).

WHAT IS A PUBLIC SYMBOL HERE: CSS has no visibility keyword at all --
every selector and every custom property is visible to anything that
loads the stylesheet. Every symbol this walker emits is therefore always
`public=True`; there is no analogue of python's leading-underscore or
bash's naming convention to lean on for CSS.

WHAT COUNTS AS A SYMBOL: this walker does not attempt full selector-tree
fidelity -- the lint rules that consume it (contrast, target-size,
outline, hidden-text) query raw nodes via `frob.lang.raw_tree`/
`symbol_tree`, not `frob.graph` symbol qualnames, so a thin walk is
enough to make `parse_file` succeed and produce a non-empty tree (this
ticket's positive control). Two top-level node shapes become symbols:
a top-level `rule_set` (mapped onto `SymbolKind.CLASS`, qualname is the
rule's own selector text -- the closest analogue CSS has to a named,
body-bearing symbol) and a top-level SCSS variable `declaration` whose
property name starts with `$` (mapped onto `SymbolKind.CONST`, mirroring
`_walk_bash.py`'s top-level-assignment-as-CONST convention). Plain CSS
custom properties (`--foo: red` inside `:root {}`) are NOT walked as
top-level symbols here because this grammar always nests them inside a
`rule_set` block -- they are covered by that rule_set's own symbol, not
a separate one; a future ticket can add nested-property symbols if a
lint rule in this epic ever needs to bind directly to one.

COMMENT SYNTAX: plain CSS has exactly one comment node type
(`comment`, the `/* ... */` block form -- CSS has no line-comment
syntax at all). SCSS additionally supports `// ...` line comments,
which this grammar surfaces as a distinct `js_comment` node type (yes,
that is a language-pack naming artifact, not a lang.py naming choice --
verified interactively, module docstring's exploration) alongside the
same `comment` block-comment node type plain CSS uses. `COMMENT_TYPES`
in `_extract.py` carries a `"css": {"comment"}` entry and a
`"scss": {"comment", "js_comment"}` entry to cover both.
"""

from __future__ import annotations

from tree_sitter import Node

from frob.lang._common import (
    _canonical_tokens,
    _child_text,
    _collapse_ws,
    _leading_doc_comment,
    _leaf_tokens,
    _span_of,
)
from frob.lang._models import RawSymbol, SymbolKind

# frob:ticket T-5303
# frob:doc docs/modules/lang.md#per-language-walker-notes
# CSS's one comment node type (the `/* ... */` block form -- see module
# docstring for why CSS itself has no line-comment syntax at all).
CSS_COMMENT_TYPES = frozenset({"comment"})

# frob:ticket T-5303
# SCSS adds `// ...` line comments on top of CSS's block form -- this
# grammar surfaces them as a `js_comment` node type (see module
# docstring).
SCSS_COMMENT_TYPES = frozenset({"comment", "js_comment"})

_SELECTORS_FIELD = "selectors"
_VARIABLE_PREFIX = "$"


def _css_selector_text(node: Node) -> str:
    """The rule's own selector text (`.foo, .bar` etc), whitespace-collapsed
    for a stable qualname -- `rule_set`'s first `selectors` child."""
    for c in node.children:
        if c.type == _SELECTORS_FIELD:
            return _collapse_ws(_child_text(c))
    return _collapse_ws(_child_text(node))


def _css_rule_symbol(node: Node, comment_types: frozenset[str]) -> RawSymbol:
    """A top-level `rule_set` `RawSymbol` (module docstring: always
    `SymbolKind.CLASS`, always public -- CSS has no visibility concept)."""
    body = next((c for c in node.children if c.type == "block"), None)
    doc = _leading_doc_comment(node, comment_types)
    skip = ((body.start_byte, body.end_byte),) if body else ()
    return RawSymbol(
        qualname=_css_selector_text(node) or "<rule>",
        kind=SymbolKind.CLASS,
        public=True,
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, comment_types, skip),
        body_tokens=_leaf_tokens(body, comment_types) if body else (),
        doc_text=doc,
        body_norm=_canonical_tokens(body, comment_types) if body else (),
    )


def _scss_variable_name(node: Node) -> str:
    """The declared variable's own name -- `declaration`'s `property_name`
    child, only meaningful when it starts with `$` (module docstring)."""
    for c in node.children:
        if c.type == "property_name":
            return _child_text(c)
    return ""


def _scss_variable_symbol(
    node: Node, doc: str, comment_types: frozenset[str]
) -> RawSymbol | None:
    """A top-level SCSS `$var: ...` `RawSymbol` (`SymbolKind.CONST`), or
    `None` if this `declaration` is not a `$`-prefixed variable (module
    docstring)."""
    name = _scss_variable_name(node)
    if not name.startswith(_VARIABLE_PREFIX):
        return None
    return RawSymbol(
        qualname=name,
        kind=SymbolKind.CONST,
        public=True,
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, comment_types),
        body_tokens=(),
        doc_text=doc,
    )


def _walk_css_family(
    root: Node, comment_types: frozenset[str]
) -> tuple[RawSymbol, ...]:
    """Every CSS/SCSS symbol under `root` (module docstring: top-level rule
    sets plus top-level `$`-prefixed SCSS variable declarations)."""
    symbols: list[RawSymbol] = []
    for node in root.children:
        doc = _leading_doc_comment(node, comment_types)
        if node.type == "rule_set":
            symbols.append(_css_rule_symbol(node, comment_types))
        elif node.type == "declaration":
            built = _scss_variable_symbol(node, doc, comment_types)
            if built is not None:
                symbols.append(built)
    return tuple(symbols)


# frob:ticket T-5303
# frob:doc docs/modules/lang.md#per-language-walker-notes
def walk_css(root: Node) -> tuple[RawSymbol, ...]:
    """Plain-CSS symbol walk (`CSS_COMMENT_TYPES`)."""
    return _walk_css_family(root, CSS_COMMENT_TYPES)


# frob:ticket T-5303
# frob:doc docs/modules/lang.md#per-language-walker-notes
def walk_scss(root: Node) -> tuple[RawSymbol, ...]:
    """SCSS symbol walk (`SCSS_COMMENT_TYPES`, additionally covers `//`
    line comments -- module docstring)."""
    return _walk_css_family(root, SCSS_COMMENT_TYPES)
