"""The `frob:<verb> <target> [key="value" ...]` comment DSL (docs/graph.md).

Line-oriented, no expressions, grep-able in any of `frob.lang`'s five
grammars -- delimiters (`#`, `//`, `/* */`) are already stripped by the time
a `RawComment` reaches this module, so parsing here is language-agnostic.
A malformed directive is data (`MalformedDirective`), never a crash and
never silently dropped -- `frob.gates` reports it.
"""

from __future__ import annotations

import re

from frob.graph._models import Edge, EdgeKind, MalformedDirective
from frob.lang import ParsedFile, RawComment
from frob.logging import get_logger

_log = get_logger(__name__)

_VERB_TABLE: dict[str, EdgeKind] = {
    "doc": EdgeKind.DOC,
    "uses-contract": EdgeKind.USES_CONTRACT,
    "invariant": EdgeKind.INVARIANT,
    "ticket": EdgeKind.TICKET,
    "todo": EdgeKind.TODO,
    "waive": EdgeKind.WAIVE,
    "tests": EdgeKind.TESTS,
    "decision": EdgeKind.DECISION,
}

_LINE_RE = re.compile(r"^frob:(?P<verb>\S+)(?:\s+(?P<rest>.*))?$")
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
_TESTS_KINDS = frozenset({"unit", "integration", "e2e"})

_DESCRIBES_RE = re.compile(
    r"<!--\s*frob:describes\s+(?P<symref>\S+)(?:\s+(?P<facet>sig|body|doc))?\s*-->"
)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(heading: str) -> str:
    """GitHub-style heading slug: lowercase, non-alnum runs collapsed to `-`."""
    slug = _SLUG_RE.sub("-", heading.strip().lower()).strip("-")
    return slug or "top"


# frob:doc docs/graph.md#comment-dsl
def markdown_anchors(doc_path: str, text: str) -> tuple[Edge, ...]:
    """Extract `<!-- frob:describes ... -->` anchors bound to the nearest heading."""
    edges: list[Edge] = []
    slug = "top"
    for line in text.splitlines():
        heading = _HEADING_RE.match(line)
        if heading is not None:
            slug = _slugify(heading.group(2))
            continue
        match = _DESCRIBES_RE.search(line)
        if match is None:
            continue
        facet = match.group("facet") or "sig"
        edges.append(
            Edge(
                src=f"{doc_path}#{slug}",
                kind=EdgeKind.DESCRIBES,
                target=match.group("symref"),
                origin=doc_path,
                attrs={"facet": facet},
            )
        )
    _log.debug("%s: %d describes anchor(s)", doc_path, len(edges))
    return tuple(edges)


def _enclosing_src(comment: RawComment, path: str) -> str:
    """Binding target: enclosing symbol, else following symbol, else bare path."""
    if comment.enclosing is not None:
        return f"{path}::{comment.enclosing}"
    if comment.following is not None:
        return f"{path}::{comment.following}"
    return path


def _parse_line(
    line: str, *, path: str, lineno: int, src: str
) -> Edge | MalformedDirective:
    """Parse one `frob:...` comment line into an `Edge` or a `MalformedDirective`."""
    origin = f"{path}:{lineno}"
    match = _LINE_RE.match(line)
    if match is None:
        return MalformedDirective(
            file=path, line=lineno, reason=f"unparseable directive: {line!r}"
        )

    verb = match.group("verb")
    rest = (match.group("rest") or "").strip()

    kind = _VERB_TABLE.get(verb)
    if kind is None:
        return MalformedDirective(
            file=path, line=lineno, reason=f"unknown verb {verb!r}"
        )

    if not rest:
        return MalformedDirective(
            file=path, line=lineno, reason=f"missing target for verb {verb!r}"
        )

    target, _, attr_text = rest.partition(" ")
    attr_text = attr_text.strip()

    attrs = dict(_ATTR_RE.findall(attr_text))
    leftover = _ATTR_RE.sub("", attr_text).strip()
    if leftover:
        return MalformedDirective(
            file=path, line=lineno, reason=f"bad attribute syntax: {leftover!r}"
        )

    if verb == "waive" and "reason" not in attrs:
        return MalformedDirective(
            file=path, line=lineno, reason='frob:waive requires reason="..."'
        )

    if verb == "tests":
        attrs.setdefault("kind", "unit")
        if attrs["kind"] not in _TESTS_KINDS:
            return MalformedDirective(
                file=path,
                line=lineno,
                reason=f"invalid tests kind {attrs['kind']!r}",
            )

    return Edge(src=src, kind=kind, target=target, origin=origin, attrs=attrs)


# frob:doc docs/graph.md#comment-dsl
def parse_directives(
    parsed: ParsedFile,
) -> tuple[tuple[Edge, ...], tuple[MalformedDirective, ...]]:
    """Extract every `frob:` directive in `parsed.comments` into edges and errors."""
    edges: list[Edge] = []
    malformed: list[MalformedDirective] = []
    for comment in parsed.comments:
        src = _enclosing_src(comment, parsed.path)
        start_line = comment.span[0]
        for offset, raw_line in enumerate(comment.text.splitlines() or [comment.text]):
            stripped = raw_line.strip()
            if not stripped.startswith("frob:"):
                continue
            lineno = start_line + offset
            result = _parse_line(stripped, path=parsed.path, lineno=lineno, src=src)
            if isinstance(result, Edge):
                edges.append(result)
            else:
                malformed.append(result)
    if malformed:
        _log.warning("%s: %d malformed directive(s)", parsed.path, len(malformed))
    _log.debug("%s: parsed %d directive edge(s)", parsed.path, len(edges))
    return tuple(edges), tuple(malformed)


__all__ = ["markdown_anchors", "parse_directives"]
