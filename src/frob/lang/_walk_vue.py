"""Vue SFC-shell symbol walker (T-5300, WEBSEC web-app-lint substrate leaf).

WEBSEC/A11Y/SEO rules in the `T-5140` web-app epic need `.vue` Single File
Components to reach `frob.lang.parse_file` instead of returning
`LangError.UnsupportedLanguage` -- this module is that wiring's walker
half, mirroring `_walk_html.py`'s and `_walk_css.py`'s shape: a small,
one-node-kind-at-a-time walk over `tree-sitter-language-pack`'s bundled
`vue` grammar, feeding `frob.lang._extract`'s `_WALKERS`/`COMMENT_TYPES`
dispatch tables (wired in `frob.lang.__init__`'s `_EXTENSION_TABLE` and
`frob.lang._extract`, both edited alongside this module -- see
docs/modules/lang.md#per-language-walker-notes).

SFC-SHELL ONLY (this ticket's explicit scope, docs/modules/lang.md
#per-language-walker-notes): a `.vue` file's grammar top level is exactly
three possible block kinds -- `template_element`, `script_element`, and
`style_element` -- each an opaque container whose *inner* language (HTML
for `<template>`, JS/TS for `<script>`, CSS for `<style>`) this walker does
NOT descend into or re-parse; a future ticket can compose this walker with
`_walk_html`/`_walk_javascript`/`_walk_css` per-block if a lint rule in
this epic ever needs symbol-level fidelity inside one. WEBSEC's `v-html`
sink detector (T-5141-1) queries the raw `template_element` subtree via
`frob.lang.raw_tree`, not this walker's symbol shape.

WHAT IS A PUBLIC SYMBOL HERE: same as `_walk_html.py`/`_walk_css.py` --
there is no SFC-block visibility concept, every block this walker emits is
always `public=True`.
"""

from __future__ import annotations

from tree_sitter import Node

from frob.lang._common import (
    _canonical_tokens,
    _child_text,
    _leaf_tokens,
    _span_of,
)
from frob.lang._models import RawSymbol, SymbolKind

# frob:ticket T-5300
# frob:doc docs/modules/lang.md#per-language-walker-notes
# Vue's SFC shell has no comment node type of its own at this top level --
# `<!-- -->`/`//`/`/* */` comments all live inside a block's own inner
# language (HTML/JS/CSS), which this walker does not descend into (module
# docstring's SFC-SHELL-ONLY scope).
COMMENT_TYPES: frozenset[str] = frozenset()

_BLOCK_TYPES = frozenset({"template_element", "script_element", "style_element"})

# The SFC block kind's own tag name -> a short, stable qualname prefix
# (module docstring: these three are the entire SFC shell surface).
_BLOCK_LABELS = {
    "template_element": "template",
    "script_element": "script",
    "style_element": "style",
}


def _start_tag(node: Node) -> Node | None:
    """The block's own `start_tag` child, or None if absent."""
    return next((c for c in node.children if c.type == "start_tag"), None)


def _lang_attribute(start_tag: Node | None) -> str:
    """The block's `lang="..."` attribute value (e.g. `<script lang="ts">`),
    or "" if the block declares none -- appended to the qualname so a
    `<script>` and a `<script lang="ts">` block are distinguishable."""
    if start_tag is None:
        return ""
    for attr in start_tag.children:
        if attr.type != "attribute":
            continue
        attr_name = next((c for c in attr.children if c.type == "attribute_name"), None)
        if _child_text(attr_name) != "lang":
            continue
        value_node = next(
            (c for c in attr.children if c.type == "quoted_attribute_value"), None
        )
        return _child_text(value_node).strip("\"'") if value_node else ""
    return ""


def _block_symbol(node: Node) -> RawSymbol:
    """An SFC-shell block `RawSymbol` (module docstring: always
    `SymbolKind.CLASS`, always public -- Vue's SFC shell has no visibility
    concept)."""
    start_tag = _start_tag(node)
    label = _BLOCK_LABELS.get(node.type, node.type)
    lang = _lang_attribute(start_tag)
    qualname = f"{label}[{lang}]" if lang else label
    return RawSymbol(
        qualname=qualname,
        kind=SymbolKind.CLASS,
        public=True,
        span=_span_of(node),
        sig_tokens=_leaf_tokens(start_tag, COMMENT_TYPES) if start_tag else (),
        body_tokens=_leaf_tokens(node, COMMENT_TYPES),
        doc_text="",
        body_norm=_canonical_tokens(node, COMMENT_TYPES),
    )


# frob:ticket T-5300
def _walk_vue(root: Node) -> tuple[RawSymbol, ...]:
    """Every top-level SFC-shell block symbol under `root` (module
    docstring: `<template>`/`<script>`/`<style>` only, no inner-language
    descent)."""
    return tuple(
        _block_symbol(node) for node in root.children if node.type in _BLOCK_TYPES
    )
