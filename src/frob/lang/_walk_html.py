"""HTML symbol walker (T-5300, WEBSEC web-app-lint substrate leaf).

WEBSEC/A11Y/SEO rules in the `T-5140` web-app epic need `.html` files to
reach `frob.lang.parse_file` instead of returning
`LangError.UnsupportedLanguage` -- this module is that wiring's walker
half, mirroring `_walk_css.py`'s shape: a small, one-node-kind-at-a-time
walk over `tree-sitter-language-pack`'s bundled `html` grammar, feeding
`frob.lang._extract`'s `_WALKERS`/`COMMENT_TYPES` dispatch tables (wired in
`frob.lang.__init__`'s `_EXTENSION_TABLE` and `frob.lang._extract`, both
edited alongside this module -- see
docs/modules/lang.md#per-language-walker-notes).

WHAT IS A PUBLIC SYMBOL HERE: HTML has no visibility keyword at all --
every element in a document is visible to anything that loads the page.
Every symbol this walker emits is therefore always `public=True`, the same
decision `_walk_css.py` makes for CSS selectors.

WHAT COUNTS AS A SYMBOL: this walker does not attempt full DOM-tree
fidelity -- the lint rules that consume it (innerHTML/document.write
sinks live in the JS grammar; this walker's own consumers query raw nodes
via `frob.lang.raw_tree`/`symbol_tree`, not `frob.graph` symbol
qualnames) so a thin walk is enough to make `parse_file` succeed and
produce a non-empty tree (this ticket's positive control). Only
top-level `element` nodes (direct children of the `document` root, or of
another top-level element -- i.e. NOT deeply nested descendants) become
symbols, mapped onto `SymbolKind.CLASS` (the closest analogue HTML has to
a named, body-bearing symbol -- same convention `_walk_css.py` uses for
`rule_set`). The qualname is the tag name plus, when present, the
element's own `id` attribute (`div#app`) -- the most stable human-legible
identifier an HTML element carries.
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

# frob:ticket T-5300
# frob:doc docs/modules/lang.md#per-language-walker-notes
# HTML's one comment node type (the `<!-- ... -->` form -- HTML has no
# other comment syntax).
COMMENT_TYPES = frozenset({"comment"})

_ELEMENT_TYPES = frozenset({"element", "script_element", "style_element"})


def _start_tag(node: Node) -> Node | None:
    """The `element`'s own `start_tag` child, or None if self-closing/absent."""
    return next(
        (c for c in node.children if c.type in ("start_tag", "self_closing_tag")),
        None,
    )


def _tag_name(start_tag: Node | None) -> str:
    """The tag's own name (`div`, `script`, ...), or `<element>` if absent."""
    if start_tag is None:
        return "<element>"
    name_node = next((c for c in start_tag.children if c.type == "tag_name"), None)
    return _child_text(name_node) or "<element>"


# frob:waive DUP002 reason="tiny named-attribute scan also in \
# _walk_vue.py::_lang_attribute; different callers/semantics -- see T-5300"
def _element_id(start_tag: Node | None) -> str:
    """The element's `id="..."` attribute value, or "" if it has none."""
    if start_tag is None:
        return ""
    for attr in start_tag.children:
        if attr.type != "attribute":
            continue
        attr_name = next((c for c in attr.children if c.type == "attribute_name"), None)
        if _child_text(attr_name) != "id":
            continue
        value_node = next(
            (c for c in attr.children if c.type == "quoted_attribute_value"), None
        )
        return _child_text(value_node).strip("\"'") if value_node else ""
    return ""


def _element_symbol(node: Node) -> RawSymbol:
    """A top-level `element` `RawSymbol` (module docstring: always
    `SymbolKind.CLASS`, always public -- HTML has no visibility concept)."""
    start_tag = _start_tag(node)
    tag = _tag_name(start_tag)
    element_id = _element_id(start_tag)
    qualname = f"{tag}#{element_id}" if element_id else tag
    doc = _leading_doc_comment(node, COMMENT_TYPES)
    skip = ((start_tag.end_byte, node.end_byte),) if start_tag else ()
    return RawSymbol(
        qualname=qualname,
        kind=SymbolKind.CLASS,
        public=True,
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES, skip),
        body_tokens=_leaf_tokens(node, COMMENT_TYPES),
        doc_text=doc,
        body_norm=_canonical_tokens(node, COMMENT_TYPES),
    )


# frob:ticket T-5300
def _walk_html(root: Node) -> tuple[RawSymbol, ...]:
    """Every top-level HTML element symbol under `root` (module docstring)."""
    return tuple(
        _element_symbol(node) for node in root.children if node.type in _ELEMENT_TYPES
    )
