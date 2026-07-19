"""The `frob:<verb> <target> [key="value" ...]` comment DSL (docs/modules/graph.md).

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

# frob:doc docs/guides/extending/comment-dsl-directives.md#comment-dsl-directives
_VERB_TABLE: dict[str, EdgeKind] = {
    "doc": EdgeKind.DOC,
    "uses-contract": EdgeKind.USES_CONTRACT,
    "invariant": EdgeKind.INVARIANT,
    "ticket": EdgeKind.TICKET,
    "todo": EdgeKind.TODO,
    "waive": EdgeKind.WAIVE,
    "tests": EdgeKind.TESTS,
    "decision": EdgeKind.DECISION,
    # T-0080: strata directives -- bind a code symbol to a design construct
    # id (Flow/Boundary/Secret-clearance Node) so `frob.gates`' SYS family
    # can join code and model without `frob.graph` learning strata vocabulary.
    "channel": EdgeKind.CHANNEL,
    "boundary": EdgeKind.BOUNDARY,
    "secret": EdgeKind.SECRET,
}

_LINE_RE = re.compile(r"^frob:(?P<verb>\S+)(?:\s+(?P<rest>.*))?$")
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
_TESTS_KINDS = frozenset({"unit", "integration", "e2e"})

_DESCRIBES_RE = re.compile(
    r"<!--\s*frob:describes\s+(?P<symref>\S+)(?:\s+(?P<facet>sig|body|doc))?\s*-->"
)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# T-0212: GitHub strips everything except word chars (unicode-aware, so
# accented letters survive but emoji do not), hyphens, and spaces -- it
# does NOT collapse punctuation runs to a single `-` the way the old
# regex did, which is exactly what made frob's slugs disagree with
# GitHub's in both directions (docs/guides/agent-playbook.md, T-0212).
_SLUG_STRIP_RE = re.compile(r"[^\w\- ]", re.UNICODE)


# frob:doc docs/modules/graph.md#comment-dsl
def slugify(heading: str) -> str:
    """GitHub heading-anchor slug: lowercase, strip disallowed punctuation
    (keeping word chars/hyphens/spaces), spaces become hyphens one-for-one
    (consecutive spaces stay as consecutive hyphens, unlike the old
    collapse-to-single-`-` behavior this replaces, T-0212)."""
    slug = _SLUG_STRIP_RE.sub("", heading.strip().lower())
    slug = slug.replace(" ", "-")
    return slug or "top"


# frob:doc docs/modules/graph.md#comment-dsl
def dedupe_slug(slug: str, seen: dict[str, int]) -> str:
    """Apply GitHub's repeated-heading suffixing (`-1`, `-2`, ...) to `slug`,
    mutating `seen` (a per-document slug -> occurrence-count map) in place;
    the first occurrence of a slug is returned unsuffixed (T-0212)."""
    count = seen.get(slug, 0)
    seen[slug] = count + 1
    return slug if count == 0 else f"{slug}-{count}"


# frob:doc docs/modules/graph.md#comment-dsl
def markdown_anchors(doc_path: str, text: str) -> tuple[Edge, ...]:
    """Extract `<!-- frob:describes ... -->` anchors bound to the nearest heading."""
    edges: list[Edge] = []
    slug = "top"
    seen: dict[str, int] = {}
    for line in text.splitlines():
        heading = _HEADING_RE.match(line)
        if heading is not None:
            slug = dedupe_slug(slugify(heading.group(2)), seen)
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
    """Binding target: following symbol, else enclosing symbol, else bare path.

    `following` wins when both are set (T-0044): a directive placed directly
    above a nested method or property must bind to that method, not to the
    enclosing class whose span happens to contain the comment line. Only
    when nothing follows within range does the comment fall back to
    whatever symbol encloses it (e.g. a directive as the first line inside a
    function body).
    """
    if comment.following is not None:
        return f"{path}::{comment.following}"
    if comment.enclosing is not None:
        return f"{path}::{comment.enclosing}"
    return path


def _parse_attrs(
    verb: str, attr_text: str, *, path: str, lineno: int
) -> dict[str, str] | MalformedDirective:
    """Parse and validate `key="value"` attributes for `verb`, per-verb rules."""
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
                file=path, line=lineno, reason=f"invalid tests kind {attrs['kind']!r}"
            )
    return attrs


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
    attrs = _parse_attrs(verb, attr_text.strip(), path=path, lineno=lineno)
    if isinstance(attrs, MalformedDirective):
        return attrs

    return Edge(src=src, kind=kind, target=target, origin=origin, attrs=attrs)


# frob:doc docs/modules/graph.md#comment-dsl
# frob:ticket T-0286
# frob:tests tests/unit/graph/test_dsl.py::TestContinuation.\
# test_long_reason_continues_across_lines
def _fold_continuations(
    lines: list[tuple[int, str, str]],
) -> list[tuple[str, int, str]]:
    r"""Fold physical comment lines ending in a trailing backslash into the
    line that follows, returning `(logical_text, lineno, src)` triples where
    `lineno`/`src` are always the FIRST physical line of the run -- so a
    folded directive's reported line number and symbol binding are always
    the start of the continuation, never a continuation line (T-0286).

    `lines` is the file's comment text flattened to one entry per physical
    line, in file order, each tagged with its absolute line number and
    resolved symbol binding (`_enclosing_src`). Single-line `#`/`//`
    comments are separate `RawComment`s per physical line (`frob.lang`'s
    extractor does not merge adjacent line comments into one span), so
    folding must operate across `RawComment` boundaries, not just within
    one block comment's multi-line `text` -- flattening first is what makes
    that uniform. Folding requires the next entry's `lineno` to be exactly
    one more than the current line's -- a gap (blank line, unrelated code
    between comments) breaks the run, matching how the DSL already treats
    non-adjacent comment lines as unrelated.

    Detection is on the RIGHT-stripped line (trailing whitespace ignored, so
    both a trailing backslash with and without preceding whitespace
    continue); only the trailing backslash itself is removed, and any
    whitespace before it is kept -- lines are joined with the empty string,
    so a continuation that wants a space at the join point must put it
    before the backslash (a line ending `that \` keeps the trailing space
    when folded; a line ending `that\` does not).

    A trailing backslash on the LAST physical line available to continue
    into (end of file, or the next line is not adjacent) is treated
    LITERALLY: it is left in place unfolded rather than reported as
    malformed, since a lone trailing backslash is content, not necessarily
    evidence of a broken continuation.
    """
    folded: list[tuple[str, int, str]] = []
    i = 0
    n = len(lines)
    while i < n:
        lineno, text, src = lines[i]
        head = text.rstrip("\r")
        while (
            head.rstrip().endswith("\\")
            and i + 1 < n
            and lines[i + 1][0] == lines[i][0] + 1
        ):
            head = head.rstrip()[:-1]
            i += 1
            head += lines[i][1].rstrip("\r")
        folded.append((head, lineno, src))
        i += 1
    return folded


# frob:doc docs/modules/graph.md#comment-dsl
def parse_directives(
    parsed: ParsedFile,
) -> tuple[tuple[Edge, ...], tuple[MalformedDirective, ...]]:
    """Extract every `frob:` directive in `parsed.comments` into edges and errors."""
    edges: list[Edge] = []
    malformed: list[MalformedDirective] = []
    flat: list[tuple[int, str, str]] = []
    for comment in parsed.comments:
        src = _enclosing_src(comment, parsed.path)
        start_line = comment.span[0]
        physical = comment.text.splitlines() or [comment.text]
        flat.extend(
            (start_line + offset, raw_line, src)
            for offset, raw_line in enumerate(physical)
        )
    for logical_line, lineno, src in _fold_continuations(flat):
        stripped = logical_line.strip()
        if not stripped.startswith("frob:"):
            continue
        result = _parse_line(stripped, path=parsed.path, lineno=lineno, src=src)
        if isinstance(result, Edge):
            edges.append(result)
        else:
            malformed.append(result)
    if malformed:
        _log.warning("%s: %d malformed directive(s)", parsed.path, len(malformed))
    _log.debug("%s: parsed %d directive edge(s)", parsed.path, len(edges))
    return tuple(edges), tuple(malformed)


__all__ = ["dedupe_slug", "markdown_anchors", "parse_directives", "slugify"]
