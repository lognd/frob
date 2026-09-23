"""Per-route `<head>` metadata extraction (docs/modules/webapp-seo.md).

# frob:ticket T-5364

Every SEO/WEBPERF rule in the T-5140 web-app epic needs the same three
facts about a route's `<head>`: its title, its meta/link tags, and any
JSON-LD structured-data blocks. Re-querying the DOM with a fresh
tree-sitter walk for each rule would multiply parse cost by the number of
rules in the family, so this module is the ONE walk: `extract_page_metadata`
turns one `.html`/`.jsx` file into a single frozen `PageMetadata`, and
`build_duplicate_title_index` folds a route table's worth of those into
the cross-route duplicate-title index every downstream rule reuses instead
of re-scanning the table itself.

This module never re-detects a web framework (`frob.webapp._detect.
detect_frameworks` is the one entry point for that, T-5302) and never
stands up its own tree-sitter `Parser`/`get_parser` call -- it walks the
`Node` tree `frob.lang.raw_tree` already produced through frob.lang's
single parse dispatch (T-5300 wired `.html`/`.jsx` into that dispatch).

SCOPE (owner directive, ticket body): only `<head>` contents. HTML's
`<head>` element and a JSX `<Head>`/`<head>` wrapper element (the Next.js/
React convention) are the two shapes recognized; `.vue` Single File
Components have no `<head>` block at the grammar's top level (`_walk_vue.
py`'s SFC-shell-only docstring) and are out of scope here.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from tree_sitter import Node
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.lang import LangError, raw_tree
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/webapp-seo.md#seoerror
class SeoError(ErrorSet):
    """Failure values `extract_page_metadata` can return -- never a bare exception.

    frob:ticket T-5364
    """

    UnsupportedLanguage = "File extension is not .html or .jsx (T-5364 scope)"
    ParseFailed = "frob.lang could not produce a usable tree for this file"
    NoHeadElement = "No <head>/<Head> element found in the document"


# The two node-type vocabularies this module understands: HTML's own
# element/attribute grammar, and JSX's element/attribute grammar (used for
# React/Next.js `<Head>` wrapper components). Each entry names the node
# types that play a given role in that grammar so `_find_head`/
# `_collect_head_children` can walk either shape with the same logic.
_HTML_ELEMENT_TYPES = frozenset({"element", "script_element"})
_JSX_ELEMENT_TYPES = frozenset({"jsx_element", "jsx_self_closing_element"})


# frob:doc docs/modules/webapp-seo.md#metatag
class MetaTag(BaseModel):
    """One `<meta>` tag's `name`/`property`/`content` attributes (any may be absent).

    frob:ticket T-5364
    """

    model_config = {"frozen": True}

    name: str | None = None
    property: str | None = None
    content: str | None = None


# frob:doc docs/modules/webapp-seo.md#linktag
class LinkTag(BaseModel):
    """One `<link>` tag's `rel`/`href` attributes (either may be absent).

    frob:ticket T-5364
    """

    model_config = {"frozen": True}

    rel: str | None = None
    href: str | None = None


# frob:doc docs/modules/webapp-seo.md#extract_page_metadata
class PageMetadata(BaseModel):
    """One route's normalized `<head>` contents: title, meta/link tags, JSON-LD.

    `source_path` is kept alongside `route` so `build_duplicate_title_index`
    can report which file backs a duplicate route, not just the route
    label a caller supplied.

    frob:ticket T-5364
    """

    model_config = {"frozen": True}

    route: str
    source_path: str
    title: str | None = None
    meta: tuple[MetaTag, ...] = ()
    links: tuple[LinkTag, ...] = ()
    json_ld: tuple[str, ...] = ()


def _node_text(node: Node | None) -> str:
    """Decode `node`'s own text, or "" if the node (or its text) is absent.

    tree-sitter types `Node.text` as `bytes | None`; every attribute/text
    lookup in this module goes through this one null-safe decode instead
    of repeating the `is None` guard at each call site.

    frob:ticket T-5364
    """
    if node is None or node.text is None:
        return ""
    return node.text.decode("utf-8", errors="ignore")


def _html_tag_name(node: Node) -> str:
    """The HTML `element`/`script_element` node's own tag name, lowercased."""
    start_tag = next(
        (c for c in node.children if c.type in ("start_tag", "self_closing_tag")), None
    )
    if start_tag is None:
        return ""
    name_node = next((c for c in start_tag.children if c.type == "tag_name"), None)
    if name_node is None:
        return ""
    return _node_text(name_node).lower()


def _html_attrs(node: Node) -> dict[str, str]:
    """The HTML element's own attribute name/value map (module docstring shape)."""
    start_tag = next(
        (c for c in node.children if c.type in ("start_tag", "self_closing_tag")), None
    )
    if start_tag is None:
        return {}
    out: dict[str, str] = {}
    for attr in start_tag.children:
        if attr.type != "attribute":
            continue
        attr_name = next((c for c in attr.children if c.type == "attribute_name"), None)
        if attr_name is None:
            continue
        value_node = next(
            (c for c in attr.children if c.type == "quoted_attribute_value"), None
        )
        value = ""
        if value_node is not None:
            value = _node_text(value_node).strip("\"'")
        out[_node_text(attr_name)] = value
    return out


def _html_text(node: Node) -> str:
    """The direct `text`/`raw_text` child's text (an HTML `<title>`/`<script>` body)."""
    text_node = next((c for c in node.children if c.type in ("text", "raw_text")), None)
    if text_node is None:
        return ""
    return _node_text(text_node).strip()


def _jsx_tag_name(node: Node) -> str:
    """The JSX `jsx_element`/`jsx_self_closing_element` node's own tag name."""
    opening = node
    if node.type == "jsx_element":
        opening = next(
            (c for c in node.children if c.type == "jsx_opening_element"), node
        )
    name_node = next((c for c in opening.children if c.type == "identifier"), None)
    if name_node is None:
        return ""
    return _node_text(name_node)


def _jsx_attrs(node: Node) -> dict[str, str]:
    """The JSX element's own `prop="value"` attribute map (string literals only)."""
    opening = node
    if node.type == "jsx_element":
        opening = next(
            (c for c in node.children if c.type == "jsx_opening_element"), node
        )
    out: dict[str, str] = {}
    for attr in opening.children:
        if attr.type != "jsx_attribute":
            continue
        name_node = next(
            (c for c in attr.children if c.type == "property_identifier"), None
        )
        value_node = next((c for c in attr.children if c.type == "string"), None)
        if name_node is None or value_node is None:
            continue
        text = _node_text(value_node).strip("\"'")
        out[_node_text(name_node)] = text
    return out


def _jsx_children(node: Node) -> tuple[Node, ...]:
    """The JSX element's child nodes (empty for a self-closing element)."""
    if node.type != "jsx_element":
        return ()
    return tuple(node.children)


def _jsx_text(node: Node) -> str:
    """The JSX element's own `jsx_text`/string-literal body (a `<title>` body)."""
    for child in _jsx_children(node):
        if child.type == "jsx_text":
            return _node_text(child).strip()
        if child.type == "jsx_expression":
            string_node = next((c for c in child.children if c.type == "string"), None)
            if string_node is not None:
                return _node_text(string_node).strip("\"'")
    return ""


def _find_head(
    root: Node, element_types: frozenset[str], head_names: frozenset[str]
) -> Node | None:
    """Depth-first search for the first element whose tag name is in `head_names`.

    frob:ticket T-5364
    """
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type in element_types:
            tag = (
                _html_tag_name(node)
                if node.type in _HTML_ELEMENT_TYPES
                else _jsx_tag_name(node)
            )
            if tag.lower() in head_names:
                return node
        stack.extend(reversed(node.children))
    return None


def _iter_html_head_children(head: Node) -> tuple[Node, ...]:
    """Every `element`/`script_element` directly under the HTML `<head>` node."""
    return tuple(c for c in head.children if c.type in _HTML_ELEMENT_TYPES)


def _iter_jsx_head_children(head: Node) -> tuple[Node, ...]:
    """Every `jsx_element`/`jsx_self_closing_element` directly under the JSX head."""
    return tuple(c for c in _jsx_children(head) if c.type in _JSX_ELEMENT_TYPES)


def _extract_html_metadata(
    root: Node,
) -> Result[
    tuple[str | None, tuple[MetaTag, ...], tuple[LinkTag, ...], tuple[str, ...]],
    SeoError,
]:
    """Walk an HTML tree's `<head>` into `(title, meta, links, json_ld)`.

    frob:ticket T-5364
    """
    head = _find_head(root, _HTML_ELEMENT_TYPES, frozenset({"head"}))
    if head is None:
        return Err(SeoError.NoHeadElement)
    title: str | None = None
    meta: list[MetaTag] = []
    links: list[LinkTag] = []
    json_ld: list[str] = []
    for child in _iter_html_head_children(head):
        tag = _html_tag_name(child)
        attrs = _html_attrs(child)
        if tag == "title":
            title = _html_text(child) or None
        elif tag == "meta":
            meta.append(
                MetaTag(
                    name=attrs.get("name"),
                    property=attrs.get("property"),
                    content=attrs.get("content"),
                )
            )
        elif tag == "link":
            links.append(LinkTag(rel=attrs.get("rel"), href=attrs.get("href")))
        elif tag == "script" and attrs.get("type") == "application/ld+json":
            body = _html_text(child)
            if body:
                json_ld.append(body)
    return Ok((title, tuple(meta), tuple(links), tuple(json_ld)))


def _extract_jsx_metadata(
    root: Node,
) -> Result[
    tuple[str | None, tuple[MetaTag, ...], tuple[LinkTag, ...], tuple[str, ...]],
    SeoError,
]:
    """Walk a JSX tree's `<Head>`/`<head>` wrapper into `(title, meta, links, json_ld)`.

    frob:ticket T-5364
    """
    head = _find_head(root, _JSX_ELEMENT_TYPES, frozenset({"head", "Head"}))
    if head is None:
        return Err(SeoError.NoHeadElement)
    title: str | None = None
    meta: list[MetaTag] = []
    links: list[LinkTag] = []
    json_ld: list[str] = []
    for child in _iter_jsx_head_children(head):
        tag = _jsx_tag_name(child)
        attrs = _jsx_attrs(child)
        if tag == "title":
            title = _jsx_text(child) or None
        elif tag == "meta":
            meta.append(
                MetaTag(
                    name=attrs.get("name"),
                    property=attrs.get("property"),
                    content=attrs.get("content"),
                )
            )
        elif tag == "link":
            links.append(LinkTag(rel=attrs.get("rel"), href=attrs.get("href")))
        elif tag == "script" and attrs.get("type") == "application/ld+json":
            body = _jsx_text(child)
            if body:
                json_ld.append(body)
    return Ok((title, tuple(meta), tuple(links), tuple(json_ld)))


_LANG_EXTRACTORS = {
    "html": _extract_html_metadata,
    "javascript": _extract_jsx_metadata,
}


# frob:doc docs/modules/webapp-seo.md#extract_page_metadata
def extract_page_metadata(
    path: Path, *, route: str | None = None
) -> Result[PageMetadata, SeoError]:
    """One route's `<head>` contents, normalized into a `PageMetadata`.

    `route` defaults to `path`'s own string form -- callers building a
    route table (an out-of-scope future leaf, ticket body) pass the
    logical route path instead. Delegates parsing entirely to `frob.lang.
    raw_tree` (T-5300's `.html`/`.jsx` grammar wiring); this function does
    no filesystem I/O and stands up no tree-sitter `Parser` of its own.

    frob:ticket T-5364
    """
    if path.suffix not in (".html", ".jsx"):
        _log.debug("extract_page_metadata: unsupported extension %s", path)
        return Err(SeoError.UnsupportedLanguage)
    parsed = raw_tree(path)
    if parsed.is_err:
        lang_err = parsed.danger_err
        _log.debug("extract_page_metadata: raw_tree failed for %s: %s", path, lang_err)
        if lang_err is LangError.UnsupportedLanguage:
            return Err(SeoError.UnsupportedLanguage)
        return Err(SeoError.ParseFailed)
    tree, _source, language_label = parsed.danger_ok
    extractor = _LANG_EXTRACTORS.get(language_label)
    if extractor is None:
        _log.debug(
            "extract_page_metadata: no extractor for language %s", language_label
        )
        return Err(SeoError.UnsupportedLanguage)
    result = extractor(tree.root_node)
    if result.is_err:
        return Err(result.danger_err)
    title, meta, links, json_ld = result.danger_ok
    resolved_route = route if route is not None else str(path)
    _log.debug(
        "extract_page_metadata: route=%s title=%r meta=%d links=%d json_ld=%d",
        resolved_route,
        title,
        len(meta),
        len(links),
        len(json_ld),
    )
    return Ok(
        PageMetadata(
            route=resolved_route,
            source_path=str(path),
            title=title,
            meta=meta,
            links=links,
            json_ld=json_ld,
        )
    )


# frob:doc docs/modules/webapp-seo.md#build_duplicate_title_index
def build_duplicate_title_index(
    pages: tuple[PageMetadata, ...],
) -> dict[str, tuple[str, ...]]:
    """The route-table-wide duplicate-title index: title text -> routes sharing it.

    Only titles shared by two or more routes appear in the returned map
    (a unique title carries no lint signal) -- every SEO rule that flags
    duplicate `<title>` tags across a route table reuses this one index
    instead of re-scanning `pages` itself.

    frob:ticket T-5364
    """
    by_title: dict[str, list[str]] = {}
    for page in pages:
        if page.title is None:
            continue
        by_title.setdefault(page.title, []).append(page.route)
    duplicates = {
        title: tuple(routes) for title, routes in by_title.items() if len(routes) > 1
    }
    _log.debug(
        "build_duplicate_title_index: %d duplicate title(s) of %d page(s)",
        len(duplicates),
        len(pages),
    )
    return duplicates


__all__ = [
    "LinkTag",
    "MetaTag",
    "PageMetadata",
    "SeoError",
    "build_duplicate_title_index",
    "extract_page_metadata",
]
