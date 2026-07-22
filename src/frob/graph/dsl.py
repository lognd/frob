"""The `frob:<verb> <target> [key="value" ...]` comment DSL (docs/modules/graph.md).

Line-oriented, no expressions, grep-able in any of `frob.lang`'s five
grammars -- delimiters (`#`, `//`, `/* */`) are already stripped by the time
a `RawComment` reaches this module, so parsing here is language-agnostic.
A malformed directive is data (`MalformedDirective`), never a crash and
never silently dropped -- `frob.gates` reports it.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: src/frob/graph/dsl.py's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable \
# by reading the code it annotates) rather than a separate cross-module contract \
# needing its own tracked invariant; disposed as a calibration batch, not \
# claim-by-claim"

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
    # T-0412: frob:debt <RULE> reason="..." ticket="T-####" [until="..."] --
    # a TEMPORARY, ticket-bound, tracked exception (see _parse_attrs' verb
    # == "debt" branch for its required-attrs check).
    "debt": EdgeKind.DEBT,
    # T-0576: frob:deprecated <since> sunset="YYYY-MM-DD" ticket="T-####"
    # [reason="..."] -- a ticket-bound sunset date on a still-callable public
    # symbol (see _parse_attrs' verb == "deprecated" branch for its
    # required-attrs check).
    "deprecated": EdgeKind.DEPRECATED,
    "tests": EdgeKind.TESTS,
    "decision": EdgeKind.DECISION,
    # T-0080: strata directives -- bind a code symbol to a design construct
    # id (Flow/Boundary/Secret-clearance Node) so `frob.gates`' SYS family
    # can join code and model without `frob.graph` learning strata vocabulary.
    "channel": EdgeKind.CHANNEL,
    "boundary": EdgeKind.BOUNDARY,
    "secret": EdgeKind.SECRET,
    # T-0428: `frob:enforces <concept-id>` -- a rule/detector's own code
    # declares which registry concept(s) it enforces; see
    # `frob.gates._registry_exhaustiveness`'s derived-coverage cross-check.
    "enforces": EdgeKind.ENFORCES,
}

_LINE_RE = re.compile(r"^frob:(?P<verb>\S+)(?:\s+(?P<rest>.*))?$")
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
_TESTS_KINDS = frozenset({"unit", "integration", "e2e"})
#: `frob:deprecated`'s `sunset="..."` attribute shape (T-0576) -- a plain
#: calendar date, never a semver: DEBT's `until` already supports a version
#: boundary for a lint exception, but a public symbol's sunset is a
#: real-world date regardless of how the release train moves.
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: Verbs that are intentional `frob:<verb>` literal markers owned by a
#: DIFFERENT subsystem (never routed through `_VERB_TABLE`, never turned
#: into a graph edge) -- the DSL parser must recognize and silently skip
#: them rather than reporting "unknown verb", or the two subsystems'
#: vocabularies drift out of agreement (T-0294). Each entry names its owner
#: so a future reader knows where the marker's contract actually lives.
#: - "secret-fake": owned by `frob.gates._secrets._FAKE_MARKER` -- a
#:   fixture-discharge token scanned directly out of tracked-file text,
#:   deliberately never a graph edge (see that module's docstring, T-0157).
#: - "used-by": owned by `frob.gates._refs` (T-0396) -- the anti-orphan
#:   gate's own regex scan over each tracked file's raw text (`frob:used-by
#:   <consumer>`, REF001/REF002/REF003), independent of `frob.graph`'s
#:   symbol/EdgeKind model since a `frob:used-by` target is a whole FILE,
#:   not a symbol, and every non-source tracked type (yaml/md/toml/...)
#:   must carry it too, most of which `frob.lang` never parses at all.
_RESERVED_MARKER_VERBS = frozenset({"secret-fake", "used-by"})

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
# frob:waive DUP001 reason="tests/unit/test_research_assets.py::_slugify \
# deliberately mirrors this exactly (own docstring: checks the same \
# anchor resolution the doclink/docanchor gates perform, without \
# importing gate internals into a unit test) -- intentional test \
# isolation, not an unaccounted duplicate"
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
    # T-0309: a directive can legitimately share a physical line with a
    # linter-suppression comment (a ruff `noqa` marker, say) once a repo
    # enforces both frob and a linter's line-length rule. Strip a trailing
    # '#'-led tail from `leftover` before judging it non-empty. This is safe
    # against a '#' inside a quoted attribute value (e.g. reason="uses
    # #hashtag"): `_ATTR_RE.sub` above has already consumed any such quoted
    # value in full (the regex's `"[^"]*"` group matches through the closing
    # quote), so a '#' that survives into `leftover` was never inside quotes.
    leftover = leftover.split("#", 1)[0].strip()
    if leftover:
        return MalformedDirective(
            file=path, line=lineno, reason=f"bad attribute syntax: {leftover!r}"
        )
    per_verb_error = _parse_attrs_verb_error(verb, attrs, path=path, lineno=lineno)
    if per_verb_error is not None:
        return per_verb_error
    return attrs


# frob:ticket T-0598
def _parse_attrs_verb_error(
    verb: str, attrs: dict[str, str], *, path: str, lineno: int
) -> MalformedDirective | None:
    """The per-verb attribute requirement `verb` fails to meet, or `None` if
    it meets every requirement its verb declares (`_parse_attrs`'s per-verb
    dispatch, split out for ARCH001 -- T-0598)."""
    if verb == "waive":
        if "reason" not in attrs:
            return MalformedDirective(
                file=path, line=lineno, reason='frob:waive requires reason="..."'
            )
        # T-0753: optional `until="YYYY-MM-DD"` expiry, reusing the same
        # date-only grammar `frob:deprecated`'s `sunset=` established
        # (T-0576) rather than a third bespoke date format -- coordinate
        # with T-0671 (strata's SYSWAIVE002) on this one convention.
        until = attrs.get("until")
        if until is not None and not _DATE_RE.match(until.strip()):
            return MalformedDirective(
                file=path,
                line=lineno,
                reason=(f"frob:waive until={until!r} is not a YYYY-MM-DD date"),
            )
    if verb == "debt":
        missing = [key for key in ("reason", "ticket") if key not in attrs]
        if missing:
            return MalformedDirective(
                file=path,
                line=lineno,
                reason=(
                    'frob:debt requires reason="..." and ticket="T-####" '
                    f"(missing: {', '.join(missing)})"
                ),
            )
    if verb == "deprecated":
        missing = [key for key in ("sunset", "ticket") if key not in attrs]
        if missing:
            return MalformedDirective(
                file=path,
                line=lineno,
                reason=(
                    'frob:deprecated requires sunset="YYYY-MM-DD" and '
                    f'ticket="T-####" (missing: {", ".join(missing)})'
                ),
            )
        if not _DATE_RE.match(attrs["sunset"].strip()):
            return MalformedDirective(
                file=path,
                line=lineno,
                reason=(
                    f"frob:deprecated sunset={attrs['sunset']!r} is not a "
                    "YYYY-MM-DD date"
                ),
            )
    if verb == "tests":
        attrs.setdefault("kind", "unit")
        if attrs["kind"] not in _TESTS_KINDS:
            # T-0237: the literal 'frob:tests' substring lets
            # frob.gates._test010_violations pick this MalformedDirective out
            # of the mixed pile in GraphSnapshot.malformed, mirroring how
            # WAIVE001 filters frob:waive's own malformed directives.
            return MalformedDirective(
                file=path,
                line=lineno,
                reason=(
                    f"frob:tests invalid kind={attrs['kind']!r}; "
                    f"must be one of {sorted(_TESTS_KINDS)}"
                ),
            )
    return None


def _parse_line(
    line: str, *, path: str, lineno: int, src: str
) -> Edge | MalformedDirective | None:
    """Parse one `frob:...` comment line into an `Edge`, a `MalformedDirective`,
    or `None` for a reserved marker verb (`_RESERVED_MARKER_VERBS`) that another
    subsystem owns and the DSL parser must silently ignore."""
    origin = f"{path}:{lineno}"
    match = _LINE_RE.match(line)
    if match is None:
        return MalformedDirective(
            file=path, line=lineno, reason=f"unparseable directive: {line!r}"
        )

    verb = match.group("verb")
    rest = (match.group("rest") or "").strip()

    if verb in _RESERVED_MARKER_VERBS:
        return None

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

    # T-0265: a literal self-referential `frob:tests` directive (target ==
    # src) is NOT rejected here -- it is this repo's own widespread,
    # deliberate convention for a test function to name itself as its own
    # evidence anchor (see e.g. every `TestDebtGate`/`TestDeprecatedGate`
    # method in tests/test_gates.py, and `TestTest010KindValidation.
    # test_dangling_tests_endpoint_still_caught_by_drift002`'s own
    # docstring: a `frob:tests` edge whose CODE-side endpoint no longer
    # resolves is already caught by the existing, edge-kind-agnostic
    # DRIFT002 mechanism, no TESTS-specific parse-time rejection needed).
    # T-0265's actual bug is a MISMATCHED-convention self-reference (the
    # directive's target string uses pytest's `Class::method` collect-only
    # separator while the graph's own qualname is `Class.method`, so the
    # two strings differ and the edge is genuinely dangling) slipping past
    # a ticket-scoped check that never evaluates `drift` at all -- fixed in
    # `frob.gates._build_jobs` (drift now always runs), not by rejecting
    # directives here.

    return Edge(src=src, kind=kind, target=target, origin=origin, attrs=attrs)


# frob:ticket T-0286
# frob:tests tests/unit/graph/test_dsl.py::TestContinuation.\
# test_long_reason_continues_across_lines
# frob:tests tests/unit/graph/test_dsl.py::TestContinuation.\
# test_unrelated_directives_on_consecutive_lines_do_not_fold
def _fold_continuations(
    lines: list[tuple[int, str, str, int]],
) -> list[tuple[str, int, str]]:
    r"""Fold physical comment lines ending in a trailing backslash into the
    line that follows, returning `(logical_text, lineno, src)` triples where
    `lineno`/`src` are always the FIRST physical line of the run -- so a
    folded directive's reported line number and symbol binding are always
    the start of the continuation, never a continuation line (T-0286).

    `lines` is the file's comment text flattened to one entry per physical
    line, in file order, each tagged with its absolute line number, resolved
    symbol binding (`_enclosing_src`), and the identity of the originating
    `RawComment` (its index in `parsed.comments`). Single-line `#`/`//`
    comments are separate `RawComment`s per physical line (`frob.lang`'s
    extractor does not merge adjacent line comments into one span, and even
    a genuine multi-line continuation inside ONE logical directive is
    extracted as several single-physical-line `RawComment`s), so folding
    must operate across `RawComment` boundaries, not just within one block
    comment's multi-line `text` -- flattening first is what makes that
    uniform, and it means `comment_id` on its own cannot gate a fold (a
    legitimate continuation run is several distinct `RawComment`s).

    Folding requires the next entry's `lineno` to be exactly one more than
    the current line's, AND the next entry's own text must NOT itself begin
    a fresh `frob:<verb> ...` directive -- a gap (blank line, unrelated code
    between comments) breaks the run, and so does landing on a line that is
    plainly the start of an independent directive rather than free-text
    continuation content. This is what a genuine continuation line always
    satisfies (its text is prose/attribute fragments, e.g. `long so it
    would overflow...` or `kind="integration"`, never `frob:<verb>`) and
    what the reviewer's T-0286 corruption repro violates: `# frob:ticket
    T-0002` on the physical line right after `# frob:ticket T-0001\` is
    itself a complete, independently-parseable directive, so it must be
    treated as its own comment run rather than swallowed into the previous
    line. (Line-number adjacency and `_enclosing_src` binding are NOT
    reliable discriminators here -- `frob.lang`'s following/enclosing
    heuristic can legitimately resolve two textually-unrelated comments to
    the same symbol, as the repro does when a trailing inline comment's
    "following" lookup reaches past its own statement into the next
    symbol -- so the fold guard must inspect the candidate line's own
    shape, not just its position or binding.)

    Detection is on the RIGHT-stripped line (trailing whitespace ignored, so
    both a trailing backslash with and without preceding whitespace
    continue); only the trailing backslash itself is removed, and any
    whitespace before it is kept -- lines are joined with the empty string,
    so a continuation that wants a space at the join point must put it
    before the backslash (a line ending `that \` keeps the trailing space
    when folded; a line ending `that\` does not).

    A trailing backslash on the LAST physical line available to continue
    into (end of file, next line not adjacent, or next line is itself a
    fresh directive) is treated LITERALLY: it is left in place unfolded
    rather than reported as malformed, since a lone trailing backslash is
    content, not necessarily evidence of a broken continuation.
    """
    folded: list[tuple[str, int, str]] = []
    i = 0
    n = len(lines)
    while i < n:
        lineno, text, src, _comment_id = lines[i]
        head = text.rstrip("\r")
        while (
            head.rstrip().endswith("\\")
            and i + 1 < n
            and lines[i + 1][0] == lines[i][0] + 1
            and _LINE_RE.match(lines[i + 1][1].strip()) is None
        ):
            head = head.rstrip()[:-1]
            i += 1
            head += lines[i][1].rstrip("\r")
        folded.append((head, lineno, src))
        i += 1
    return folded


def _resolve_block_srcs(comments: tuple[RawComment, ...], path: str) -> dict[int, str]:
    """Bind each comment (by its index into `comments`) to a symbol src,
    propagating a resolved `following` binding BACKWARD through an unbroken
    run of line-adjacent comments whose own `following` did not resolve
    (T-0313).

    Some walkers resolve `RawComment.following` against a narrow lookahead
    window measured from each comment's OWN line rather than the whole
    stacked comment block's end line (`frob.lang._walk_strata` is one --
    see its `_extract_comments`, which calls `_find_following_symbol` with
    the comment's own single-line span instead of a block-widened one the
    way `frob.lang._extract`'s generic tree-sitter path does via
    `_block_ends`). That means a directive several lines above the symbol
    it stacks with -- with other directive/comment lines between it and
    the symbol -- can fail to resolve a `following` binding even though a
    directive on the line directly above the symbol succeeds. Nothing
    about a directive's position within a contiguous, gap-free comment
    block changes which symbol the whole block belongs to, so the nearest
    RESOLVED `following` binding within the same unbroken line-adjacent
    run is the correct binding for every comment above it in that run. A
    comment whose own `following` DOES resolve is always left as its own
    source of truth; propagation only fills in where a walker's per-line
    resolution failed. A gap (non-adjacent line number) breaks the run and
    stops propagation, same as `_enclosing_src`'s existing enclosing/path
    fallback would apply on its own.
    """
    order = sorted(range(len(comments)), key=lambda i: comments[i].span[0])
    resolved: dict[int, str] = {}
    carry_start: int | None = None
    carry_src: str | None = None
    for idx in reversed(order):
        comment = comments[idx]
        if comment.following is not None:
            src = f"{path}::{comment.following}"
        elif carry_src is not None and comment.span[1] + 1 == carry_start:
            src = carry_src
        else:
            resolved[idx] = _enclosing_src(comment, path)
            carry_start = None
            carry_src = None
            continue
        resolved[idx] = src
        carry_start = comment.span[0]
        carry_src = src
    return resolved


# T-0526: frob:debt/frob:todo coherence.
#
# A `frob:debt` suppresses a GATE FINDING (the symptom); a `frob:todo`
# tracks DEFERRED WORK (the payoff). Per T-0412's own follow-up
# requirement, a debt without visible payoff-work must not be a silent
# suppression: (1) a `frob:debt` at a site with no co-located explicit
# `frob:todo` implicitly REGISTERS one -- same `src`, target is the debt's
# own `ticket=` attribute -- so the debt's payoff work appears in every
# ordinary todo-edge consumer (the "002" open-ticket check, `frob todo`-
# style listings) for free, with no separate debt/todo wiring anywhere
# else. (2) both directives already require an open ticket today (the
# debt check reuses the same open-ticket check the todo gate applies, per
# T-0412's Done report), so an implicit registration is just as enforced
# as an explicit one. (3) a `frob:debt` and an EXPLICIT co-located
# `frob:todo` naming DIFFERENT tickets is a coherence error: reusing
# DEBT001's own `"frob:debt" in md.reason` substring filter
# (`frob.gates._debt001_violations`) by shaping the `MalformedDirective`
# reason to contain that literal substring, so the mismatch surfaces as a
# DEBT001 violation with no new gate rule id and no `frob.gates` change at
# all -- this coherence rule lives entirely in the DSL parse step, exactly
# like DEBT001/TEST010's existing "shape the malformed reason, let an
# established gate's substring filter pick it up" pattern.
#
# Requirement (4) from T-0412's body -- surfacing BOTH the debt and its
# todo at ticket-close time so neither resolves silently -- is NOT
# implemented here: it is ticket-lifecycle behavior belonging to
# `frob.tickets`/`frob.gates`, outside this module's declared scope
# (T-0526 scopes only `src/frob/graph/dsl.py`). Filed as its own follow-up
# rather than folded in silently; see T-0526's Done report.
def _debt_todo_coherence(
    edges: list[Edge],
) -> tuple[list[Edge], list[MalformedDirective]]:
    """Reconcile `frob:debt`/`frob:todo` edges sharing a `src`: synthesize an
    implicit `frob:todo` for an unpaired debt (payoff work must always be
    visible, never only a gate suppression), and flag a mismatched explicit
    pairing (debt/todo naming different tickets at the same site) as a
    DEBT001-shaped `MalformedDirective` (T-0526)."""
    todo_by_src: dict[str, list[Edge]] = {}
    for edge in edges:
        if edge.kind == EdgeKind.TODO:
            todo_by_src.setdefault(edge.src, []).append(edge)

    extra_edges: list[Edge] = []
    malformed: list[MalformedDirective] = []
    for edge in edges:
        if edge.kind != EdgeKind.DEBT:
            continue
        ticket = edge.attrs.get("ticket")
        if not ticket:
            # A debt with no ticket= is already DEBT001-malformed at parse
            # time (_parse_attrs) and never reaches here as a DEBT edge.
            continue
        co_located = todo_by_src.get(edge.src, [])
        mismatched = [t for t in co_located if t.target != ticket]
        if mismatched:
            file, _, line = edge.origin.rpartition(":")
            _log.debug(
                "T-0526: frob:debt/frob:todo ticket mismatch at %s (debt=%s todo=%s)",
                edge.src,
                ticket,
                mismatched[0].target,
            )
            malformed.append(
                MalformedDirective(
                    file=file or edge.origin,
                    line=int(line) if line.isdigit() else 0,
                    reason=(
                        f"frob:debt/frob:todo mismatch at {edge.src}: "
                        f"frob:debt names ticket={ticket!r} but the co-located "
                        f"frob:todo names {mismatched[0].target!r}; both must "
                        f"name the same ticket"
                    ),
                )
            )
            continue
        if not co_located:
            _log.debug(
                "T-0526: implicit frob:todo registered for unpaired frob:debt "
                "at %s -> %s",
                edge.src,
                ticket,
            )
            extra_edges.append(
                Edge(
                    src=edge.src,
                    kind=EdgeKind.TODO,
                    target=ticket,
                    origin=edge.origin,
                    attrs={"implicit": "debt"},
                )
            )
    return extra_edges, malformed


# frob:doc docs/modules/graph.md#comment-dsl
def parse_directives(
    parsed: ParsedFile,
) -> tuple[tuple[Edge, ...], tuple[MalformedDirective, ...]]:
    """Extract every `frob:` directive in `parsed.comments` into edges and errors."""
    edges: list[Edge] = []
    malformed: list[MalformedDirective] = []
    flat: list[tuple[int, str, str, int]] = []
    block_srcs = _resolve_block_srcs(parsed.comments, parsed.path)
    for comment_id, comment in enumerate(parsed.comments):
        src = block_srcs[comment_id]
        start_line = comment.span[0]
        physical = comment.text.splitlines() or [comment.text]
        flat.extend(
            (start_line + offset, raw_line, src, comment_id)
            for offset, raw_line in enumerate(physical)
        )
    for logical_line, lineno, src in _fold_continuations(flat):
        stripped = logical_line.strip()
        if not stripped.startswith("frob:"):
            continue
        result = _parse_line(stripped, path=parsed.path, lineno=lineno, src=src)
        if result is None:
            continue
        if isinstance(result, Edge):
            edges.append(result)
        else:
            malformed.append(result)
    extra_edges, coherence_malformed = _debt_todo_coherence(edges)
    edges.extend(extra_edges)
    malformed.extend(coherence_malformed)
    if malformed:
        _log.warning("%s: %d malformed directive(s)", parsed.path, len(malformed))
    _log.debug("%s: parsed %d directive edge(s)", parsed.path, len(edges))
    return tuple(edges), tuple(malformed)


__all__ = ["dedupe_slug", "markdown_anchors", "parse_directives", "slugify"]
