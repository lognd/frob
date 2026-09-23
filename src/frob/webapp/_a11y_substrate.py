"""A11Y tree-query substrate over html/jsx/vue trees (docs/modules/webapp-a11y.md).

# frob:ticket T-5313

Every A11Y rule in the `T-5140` web-app epic (missing `alt` on `<img>`,
missing `aria-label` on an `<input>`, skipped heading levels, a `<html>`
with no `lang`) needs the SAME three tree-sitter query shapes repeated
over three different grammars (html, vue's SFC `<template>` shell, and
jsx embedded in javascript/typescript) -- this module is that one shared
query library, so no individual A11Y rule module hand-rolls its own
node-walking/attribute-scan against tree-sitter's raw `Node` API.

WHY THIS MODULE TAKES A PARSED `Node`, NOT A `Path`: `[arch.layering]`
(`frob.toml`) makes `webapp` a leaf layer with no allowed imports of its
own (same table T-5302 left this module's sibling `_detect.py` in) --
this module therefore never imports `frob.lang` itself. Every A11Y rule
module (which lives under `frob.gates`, already allowed to import both
`lang` and `webapp`) calls `frob.lang.raw_tree`/`parse_file` itself and
hands this module the resulting `tree_sitter.Node` root plus the parsed
`ParsedFile.language` label; this module only ever walks the `Node` tree
it is given. `frob.lang`'s own `_walk_html.py`/`_walk_vue.py` walkers are
NOT reused directly either, for the same layering reason plus a semantic
one: those walkers build `RawSymbol`s for `frob.graph`'s symbol index (one
row per top-level element), while every query here needs to see elements
at ANY nesting depth (a heading three `<div>`s deep, an `<img>` inside a
JSX fragment) -- a different traversal shape from a symbol walk.

THREE GRAMMAR FAMILIES, ONE NODE VOCABULARY EACH: html (`.html`) and vue's
SFC `<template>` block (`.vue`) share IDENTICAL node type names for
elements/attributes (`element`, `start_tag`/`self_closing_tag`,
`attribute`, `attribute_name`, `quoted_attribute_value`) -- vue's own
tree-sitter grammar reuses html's node shapes for its template block, not
a nested sub-parse -- so `_HTML_FAMILY_LANGUAGES` below routes both
through the same walk. JSX (embedded in the `javascript`/`typescript`
`ParsedFile.language` labels `.jsx`/`.tsx` files carry, per
`frob.lang.language_for_extension`) uses a structurally different but
parallel vocabulary (`jsx_element`/`jsx_self_closing_element`,
`jsx_opening_element`, `jsx_attribute`) and gets its own walk branch.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger

if TYPE_CHECKING:
    from tree_sitter import Node

_log = get_logger(__name__)


# frob:doc docs/modules/webapp-a11y.md#errors
class A11ySubstrateError(ErrorSet):
    """Failure values this module's query helpers can return.

    frob:ticket T-5313
    """

    UnsupportedLanguage = (
        "language is not one of the html/vue/javascript/typescript families "
        "this substrate walks"
    )


# `ParsedFile.language` labels routed through the html-shaped node
# vocabulary (module docstring: vue's `<template>` block reuses html's own
# node types verbatim, no nested sub-parse).
_HTML_FAMILY_LANGUAGES = frozenset({"html", "vue"})

# `ParsedFile.language` labels routed through the jsx-shaped node
# vocabulary -- `.jsx` parses as "javascript", `.tsx` as "typescript"
# (frob.lang.__init__'s `_EXTENSION_TABLE`), and both embed jsx nodes
# identically.
_JSX_FAMILY_LANGUAGES = frozenset({"javascript", "typescript"})

_SUPPORTED_LANGUAGES = _HTML_FAMILY_LANGUAGES | _JSX_FAMILY_LANGUAGES

_HTML_ELEMENT_TYPES = frozenset({"element"})
_JSX_ELEMENT_TYPES = frozenset({"jsx_element", "jsx_self_closing_element"})

# Heading tag names in ascending level order -- index + 1 is the heading level.
_HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")


# frob:doc docs/modules/webapp-a11y.md#elementmatch
class ElementMatch(BaseModel):
    """One matched element: its tag name, its own attributes, and its
    1-based inclusive-line span in the source.

    frob:ticket T-5313
    """

    tag: str
    attributes: dict[str, str]
    span: tuple[int, int]


# frob:doc docs/modules/webapp-a11y.md#headingmatch
class HeadingMatch(BaseModel):
    """One matched heading: its level (1-6, from `h1`..`h6`), its own
    text content, and its 1-based inclusive-line span.

    frob:ticket T-5313
    """

    level: int
    text: str
    span: tuple[int, int]


def _span_of(node: Node) -> tuple[int, int]:
    """`node`'s 1-based inclusive-line span."""
    return (node.start_point[0] + 1, node.end_point[0] + 1)


def _child_text(node: Node | None, source: bytes) -> str:
    """`node`'s own source text, or "" if `node` is absent."""
    if node is None:
        return ""
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")


def _html_family_tag_and_attrs(node: Node, source: bytes) -> tuple[str, dict[str, str]]:
    """The tag name and attribute map of an html-family `element` node
    (module docstring: shared by `.html` and `.vue` `<template>` blocks)."""
    open_tag = next(
        (c for c in node.children if c.type in ("start_tag", "self_closing_tag")),
        None,
    )
    if open_tag is None:
        return "<element>", {}
    name_node = next((c for c in open_tag.children if c.type == "tag_name"), None)
    tag = _child_text(name_node, source) or "<element>"
    attrs: dict[str, str] = {}
    for attr in open_tag.children:
        if attr.type != "attribute":
            continue
        name_node = next((c for c in attr.children if c.type == "attribute_name"), None)
        name = _child_text(name_node, source)
        if not name:
            continue
        value_node = next(
            (c for c in attr.children if c.type == "quoted_attribute_value"), None
        )
        if value_node is not None:
            inner = next(
                (c for c in value_node.children if c.type == "attribute_value"), None
            )
            attrs[name] = _child_text(inner, source)
        else:
            attrs[name] = ""
    return tag, attrs


def _jsx_family_tag_and_attrs(node: Node, source: bytes) -> tuple[str, dict[str, str]]:
    """The tag name and attribute map of a `jsx_element`/
    `jsx_self_closing_element` node."""
    opening = (
        node
        if node.type == "jsx_self_closing_element"
        else next((c for c in node.children if c.type == "jsx_opening_element"), None)
    )
    if opening is None:
        return "<element>", {}
    name_node = next((c for c in opening.children if c.type == "identifier"), None)
    tag = _child_text(name_node, source) or "<element>"
    attrs: dict[str, str] = {}
    for attr in opening.children:
        if attr.type != "jsx_attribute":
            continue
        name_node = next(
            (c for c in attr.children if c.type == "property_identifier"), None
        )
        name = _child_text(name_node, source)
        if not name:
            continue
        string_node = next((c for c in attr.children if c.type == "string"), None)
        if string_node is not None:
            fragment = next(
                (c for c in string_node.children if c.type == "string_fragment"), None
            )
            attrs[name] = _child_text(fragment, source)
        else:
            attrs[name] = ""
    return tag, attrs


def _iter_elements(
    root: Node, language: str, source: bytes
) -> Iterator[tuple[str, dict[str, str], Node]]:
    """Every element in `root`'s subtree, at any nesting depth, as
    `(tag, attributes, node)` -- the shared walk `elements_with_attribute`/
    `elements_missing_attribute`/`heading_sequence` all build on."""
    element_types = (
        _HTML_ELEMENT_TYPES
        if language in _HTML_FAMILY_LANGUAGES
        else _JSX_ELEMENT_TYPES
    )
    extractor = (
        _html_family_tag_and_attrs
        if language in _HTML_FAMILY_LANGUAGES
        else _jsx_family_tag_and_attrs
    )
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type in element_types:
            tag, attrs = extractor(node, source)
            yield tag, attrs, node
        # Push children in reverse so document order is preserved when
        # popped (a stack-based walk avoids Python recursion depth limits
        # on deeply-nested markup).
        stack.extend(reversed(node.children))


def _text_of(node: Node, language: str, source: bytes) -> str:
    """The flattened text content of a heading `node` (its `text`/
    `jsx_text` leaf children, whitespace-collapsed)."""
    leaf_type = "text" if language in _HTML_FAMILY_LANGUAGES else "jsx_text"
    parts = [
        _child_text(child, source) for child in node.children if child.type == leaf_type
    ]
    return " ".join(" ".join(parts).split())


# frob:doc docs/modules/webapp-a11y.md#elements_with_attribute
def elements_with_attribute(
    root: Node, language: str, source: bytes, tag_names: frozenset[str], attribute: str
) -> Result[tuple[ElementMatch, ...], A11ySubstrateError]:
    """Every element under `root` whose tag is in `tag_names` AND that
    carries `attribute` (the `img[alt]`/`input[aria-label]` query shape).

    Returns `A11ySubstrateError.UnsupportedLanguage` for a `language` this
    substrate does not walk.

    frob:ticket T-5313
    """
    if language not in _SUPPORTED_LANGUAGES:
        _log.debug("elements_with_attribute: unsupported language=%s", language)
        return Err(A11ySubstrateError.UnsupportedLanguage)
    matches = tuple(
        ElementMatch(tag=tag, attributes=attrs, span=_span_of(node))
        for tag, attrs, node in _iter_elements(root, language, source)
        if tag in tag_names and attribute in attrs
    )
    _log.debug(
        "elements_with_attribute: %d match(es) for tags=%s attribute=%s",
        len(matches),
        sorted(tag_names),
        attribute,
    )
    return Ok(matches)


# frob:doc docs/modules/webapp-a11y.md#elements_missing_attribute
def elements_missing_attribute(
    root: Node, language: str, source: bytes, tag_names: frozenset[str], attribute: str
) -> Result[tuple[ElementMatch, ...], A11ySubstrateError]:
    """Every element under `root` whose tag is in `tag_names` and that
    does NOT carry `attribute` -- the inverse of `elements_with_attribute`,
    the shape every "missing alt/aria-label" A11Y violation rule queries.

    frob:ticket T-5313
    """
    if language not in _SUPPORTED_LANGUAGES:
        _log.debug("elements_missing_attribute: unsupported language=%s", language)
        return Err(A11ySubstrateError.UnsupportedLanguage)
    matches = tuple(
        ElementMatch(tag=tag, attributes=attrs, span=_span_of(node))
        for tag, attrs, node in _iter_elements(root, language, source)
        if tag in tag_names and attribute not in attrs
    )
    _log.debug(
        "elements_missing_attribute: %d match(es) for tags=%s attribute=%s",
        len(matches),
        sorted(tag_names),
        attribute,
    )
    return Ok(matches)


# frob:doc docs/modules/webapp-a11y.md#heading_sequence
def heading_sequence(
    root: Node, language: str, source: bytes
) -> Result[tuple[HeadingMatch, ...], A11ySubstrateError]:
    """Every `h1`..`h6` heading under `root`, in document order, as
    `(level, text, span)` -- the walk an A11Y "skipped heading level"
    rule (`h1` straight to `h3`, no `h2`) queries.

    frob:ticket T-5313
    """
    if language not in _SUPPORTED_LANGUAGES:
        _log.debug("heading_sequence: unsupported language=%s", language)
        return Err(A11ySubstrateError.UnsupportedLanguage)
    headings: list[HeadingMatch] = []
    for tag, _attrs, node in _iter_elements(root, language, source):
        if tag not in _HEADING_TAGS:
            continue
        level = _HEADING_TAGS.index(tag) + 1
        headings.append(
            HeadingMatch(
                level=level,
                text=_text_of(node, language, source),
                span=_span_of(node),
            )
        )
    _log.debug("heading_sequence: %d heading(s) found", len(headings))
    return Ok(tuple(headings))


# frob:doc docs/modules/webapp-a11y.md#html_lang
def html_lang(
    root: Node, language: str, source: bytes
) -> Result[str | None, A11ySubstrateError]:
    """The top-level `<html lang="...">` attribute value, or `None` if no
    `<html>` element is present or it carries no `lang` attribute -- the
    query an A11Y "document has no language" rule uses.

    Only meaningful for the html-family languages (a jsx tree has no
    `<html>` root); returns `Ok(None)` rather than an error for a jsx
    language, since "no `<html>` element in this subtree" is itself a
    legitimate answer, not a substrate failure.

    frob:ticket T-5313
    """
    if language not in _SUPPORTED_LANGUAGES:
        _log.debug("html_lang: unsupported language=%s", language)
        return Err(A11ySubstrateError.UnsupportedLanguage)
    if language not in _HTML_FAMILY_LANGUAGES:
        return Ok(None)
    for tag, attrs, _node in _iter_elements(root, language, source):
        if tag == "html":
            lang = attrs.get("lang")
            _log.debug("html_lang: <html lang=%r>", lang)
            return Ok(lang)
    _log.debug("html_lang: no <html> element found")
    return Ok(None)
