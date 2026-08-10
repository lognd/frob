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
from frob.lang import ParsedFile, RawComment, SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)

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
    # T-0744: typestate protocol declaration surface (T-0739 child 1). See
    # `_ATTR_ONLY_VERBS`/`_parse_attrs_verb_error` for their grammars.
    "protocol": EdgeKind.PROTOCOL,
    "transition": EdgeKind.TRANSITION,
    "requires": EdgeKind.REQUIRES,
    # T-0809: resource-tracking DSL -- bare-target verbs (like `doc`/
    # `ticket`), no required attributes. `frob:acquire <resource>` /
    # `frob:release <resource>` / `frob:escapes <resource>` on the
    # declaring function; see EdgeKind's docstring for the full contract.
    "acquire": EdgeKind.ACQUIRE,
    "release": EdgeKind.RELEASE,
    "escapes": EdgeKind.ESCAPES,
    # T-1227: `frob:enumerates <doc-anchor>` on a collection literal's own
    # symbol -- the code-side half of the doc<->code enumeration binding,
    # mirroring `frob:doc`'s bare-target, no-required-attrs shape exactly
    # (the DOC/DESCRIBES pair's code->doc direction). The markdown-side
    # half (`markdown_anchors`) carries the actual member CLAIM as a
    # `members=` attribute; this code-side edge only records discoverable
    # traceability from the symbol back to the doc that enumerates it.
    "enumerates": EdgeKind.ENUMERATES,
    # T-1229: `frob:until T-####` -- markdown-side directive, matched by
    # `_UNTIL_RE`/`markdown_anchors` below like `describes`/`enumerates`;
    # this table entry exists only so a code-side `frob:until T-####`
    # comment (bare target, no required attrs, same shape as `frob:ticket`)
    # is also accepted -- e.g. directly above the still-missing symbol a
    # doc's absence claim is about, not just in markdown prose.
    "until": EdgeKind.UNTIL,
}

# frob:ticket T-1970
# T-1970: the DSL had no mention/use distinction -- prose ABOUT a
# directive (a discharge comment quoting `follow_up="T-1956"` while
# explaining it was already handled, a reworded comment describing a
# removed `frob:waive WIRE001`) was parsed AS a live directive, refusing
# two consecutive lands over pure English wording. `frob:quote(...)` is
# the one explicit escape: any text a doubled-parenthesized `frob:quote(`
# ... `)` span wraps is a MENTION, not a directive -- inert to every
# scanner that reads directive-shaped text, whether that scanner is this
# module's own `_LINE_RE`/`_parse_line` or an entirely separate text scan
# (`frob.tickets._live_tracker`'s `git grep` citation check, T-1970's own
# second incident). Deliberately NOT a doubled-colon prefix
# (`frob::waive`) -- the live-tracker incident mentioned a bare
# `follow_up="T-1956"` attribute with no adjacent `frob:` verb at all, so
# an escape tied to the verb position could not have covered it; a
# wrapper covers ANY directive-shaped substring regardless of what
# precedes it. Single-level (no nested parens) is a documented
# limitation, not a silent gap: directive attribute values in this DSL
# are always `key="value"` quoted strings, which do not themselves need
# parens.
_MENTION_RE = re.compile(r"frob:quote\(([^()]*)\)")


def mask_frob_mentions(text: str) -> str:
    # frob:doc docs/modules/graph.md#comment-dsl
    """Replace every `frob:quote(...)` escape span in `text` (wrapper
    delimiters AND contents) with same-length `.` filler, so a mentioned
    directive-shaped substring becomes invisible to every downstream
    directive/citation scanner while every other character's COLUMN
    POSITION in the line is preserved (T-1970) -- a scanner that reports
    `file:line:col` off the masked text still points at the real source
    location. Idempotent and order-independent: `frob:quote(...)` cannot
    itself produce a NEW `frob:quote(...)`-shaped span once masked (the
    filler is `.` characters, never `f`/`r`/`o`/`b`/`:`), so a caller
    never needs to mask twice. The ONE canonical escape this DSL
    recognizes -- every scanner reading directive-shaped text (this
    module's own line parser, `frob.tickets._live_tracker`'s citation
    grep, `frob.gates` DSL001/WAIVE001) must call this before matching,
    documented once in docs/modules/graph.md#comment-dsl rather than
    re-derived per scanner."""
    return _MENTION_RE.sub(lambda m: "." * len(m.group(0)), text)


# frob:ticket T-1989
# T-1989: fenced (```...```) code spans, matched over the WHOLE doc text
# (DOTALL, so a fence's own multi-line body is caught in one span) --
# fences are well-scoped (triple backticks, opened/closed in matched
# pairs almost by construction) so a file-wide regex is safe. Inline
# (`...`) spans are deliberately kept SAME-LINE ONLY (`_INLINE_CODE_RE`,
# below) rather than also spanning newlines: a whole-file inline-backtick
# regex measured unsafe on this repo's own docs (`docs/modules/gates.md`
# alone carries an ODD total backtick count -- 7657 at T-1989 measurement
# time -- so file-wide non-greedy pairing silently mispairs everything
# downstream of whichever single stray backtick breaks parity, blanking
# the wrong spans or none at all). Matches `frob.gates.invariants.
# _INLINE_CODE_RE`'s same same-line-only precedent for the identical
# reason.
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
# frob:ticket T-1989
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


# frob:ticket T-1989
def _blank_code_spans(text: str) -> str:
    """T-1989: replace every fenced code span, and every SAME-LINE inline
    code span, in `text` with same-length `.` filler (newlines preserved
    verbatim, so every OTHER line's number stays correct) -- documentation
    quoting `frob:` syntax as a worked example (a DSL grammar table, a
    directive shown inside backticks to teach its shape) is exactly where
    a doc naturally writes syntax it does not intend to be live, mirroring
    code's own `# frob:describes ...` doctest/example convention of never
    being inside a real triple-quoted docstring by accident. Applied
    BEFORE `mask_frob_mentions` and the per-line directive scan in
    `markdown_anchors`, the same earliest-insertion-point pattern T-1970
    established: masking here can only ever REMOVE a would-be
    `MalformedDirective`/edge match, never manufacture a new one, since
    the filler contains no `frob:`-shaped text of its own. A directive
    example broken across multiple lines by prose wrapping is NOT caught
    by this pass (see `_INLINE_CODE_RE`'s own docstring note above) --
    the doc author's own explicit `frob:quote(...)` escape (T-1970) is
    the correct tool for that shape instead."""

    def _blank(match: re.Match[str]) -> str:
        return "".join("\n" if ch == "\n" else "." for ch in match.group(0))

    text = _FENCED_CODE_RE.sub(_blank, text)
    return _INLINE_CODE_RE.sub(_blank, text)


_LINE_RE = re.compile(r"^frob:(?P<verb>\S+)(?:\s+(?P<rest>.*))?$")
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
# T-0757: "property" joins the existing three kinds -- a `frob:tests`
# edge declared `kind="property"` asserts it exercises a PROPERTY SPACE
# (a comparator's ordering, a round-trip, a monotonicity claim) rather
# than one fixed input, the distinction INV008's establish-property
# obligation (`frob.gates._design_invariants.inv008_violations`) checks
# for.
_TESTS_KINDS = frozenset({"unit", "integration", "e2e", "property"})
#: `frob:deprecated`'s `sunset="..."` attribute shape (T-0576) -- a plain
#: calendar date, never a semver: DEBT's `until` already supports a version
#: boundary for a lint exception, but a public symbol's sunset is a
#: real-world date regardless of how the release train moves.
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: `frob:protocol`'s optional `cleanup=` attribute (T-0744): the per-protocol
#: cleanup obligation later verification (T-0739 child 4) enforces. Defaults
#: to `"on-error"` when omitted (`_parse_attrs_verb_error`'s protocol branch).
_CLEANUP_KINDS = frozenset({"always", "on-error", "process-exit-ok"})

#: Verbs whose grammar is ALL `key="value"` attributes with no bare target
#: token (T-0744): `frob:transition proto="NAME" from="S" to="T"` and
#: `frob:requires proto="NAME" state="S"` bind to their protocol via the
#: `proto=` attribute itself rather than a leading plain word the way every
#: other verb's target works -- `_parse_line` special-cases them so the
#: edge's `target` becomes the parsed `proto` attribute.
_ATTR_ONLY_VERBS = frozenset({"transition", "requires"})

#: `frob:invariant`'s optional `no_import="pkg[,pkg2,...]"` obligation
#: attr (T-0757): each comma-separated entry must be a dotted module path
#: (matches a bare python identifier chain -- no wildcards, no leading/
#: trailing dots), the same shape a raw `frob.lang.extract_imports`
#: specifier or `resolve_local_import` module name takes.
_IMPORT_MODULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")

#: Default zero-declaration init/deinit name-pair patterns (T-0744): a
#: function named `<prefix>_<init_word>` with a sibling `<prefix>_
#: <deinit_word>` in the same file implicitly declares a 3-state protocol
#: (uninitialized -> active -> closed) with no `frob:protocol` comment at
#: all. Inference is ONLY for these declared pairs, never a general
#: machine-inference heuristic (T-0744's explicit scope limit).
_INFER_PAIRS: tuple[tuple[str, str], ...] = (
    ("init", "deinit"),
    ("open", "close"),
    ("acquire", "release"),
)

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
#: - "raises": owned by `frob.gates._exhaustive_handling` (T-0688/T-1022) --
#:   the declared-propagation directive (`# frob:raises <ExceptionType>`,
#:   one type per directive line, stacked above a `def`) that marks a
#:   function's intentional uncaught exception escape for EXHAUST002. Its
#:   own module scans directive text directly (`_DIRECTIVE_PREFIX`), never
#:   a graph edge; the call-site sibling form `frob:callee-raises` (T-0931)
#:   is a same-line trailing comment the DSL's line-based scan never
#:   matches in the first place, so only the standalone-line `raises` verb
#:   needs listing here.
_RESERVED_MARKER_VERBS = frozenset({"secret-fake", "used-by", "raises"})

_DESCRIBES_RE = re.compile(
    r"<!--\s*frob:describes\s+(?P<symref>\S+)(?:\s+(?P<facet>sig|body|doc))?\s*-->"
)
# T-1227: `frob:enumerates`'s markdown-side form -- mirrors `_DESCRIBES_RE`'s
# shape (bare `symref` target) but with a MANDATORY `members="a,b,c"`
# attribute carrying the doc's own claimed member list (the CONTENT
# DOCENUM001 AST-diffs against the collection literal's real members).
_ENUMERATES_RE = re.compile(
    r'<!--\s*frob:enumerates\s+(?P<symref>\S+)\s+members="(?P<members>[^"]*)"\s*-->'
)
# T-1229: `frob:until T-####`'s markdown-side form -- mirrors
# `_DESCRIBES_RE`'s bare-target shape exactly (no attrs, just a ticket id),
# binding the doc section it appears under to the ticket that will build
# the not-yet-built thing the section describes.
_UNTIL_RE = re.compile(r"<!--\s*frob:until\s+(?P<ticket>T-\d+)\s*-->")
# frob:ticket T-1989
# T-1989: `frob:ticket T-####`'s markdown-side form -- the same bare-target
# provenance tag code comments already carry (`_VERB_TABLE["ticket"]`),
# now recognized in markdown too. Measured need: `<!-- frob:ticket T-#### -->`
# is an established doc-authoring convention (docs/strata/*.md and others,
# 35 sites at T-1989 measurement time) marking which ticket a doc section
# belongs to -- consistently well-formed, never prose-shaped, so treating
# it as a real TICKET edge (mirroring `_UNTIL_RE` exactly) rather than an
# unhandled directive is the correct disposition, not a mention to quote.
_TICKET_MD_RE = re.compile(r"<!--\s*frob:ticket\s+(?P<ticket>T-\d+)\s*-->")
# frob:ticket T-1989
# T-1989: `frob:doc <target>`'s markdown-side form -- a doc section
# self-declaring its own `path#slug` as a valid `frob:doc` target for code
# comments to point at (bare-target shape, same as `_UNTIL_RE`/
# `_TICKET_MD_RE`). Measured need: 18 sites at T-1989 measurement time, all
# well-formed self-references, never prose.
_DOC_MD_RE = re.compile(r"<!--\s*frob:doc\s+(?P<target>\S+)\s*-->")
# T-1229: negative-existence prose heuristic (gate-gap class 3,
# docs/audits/docs-staleness-2026-07-29.md) -- "X does not exist yet",
# "not yet built/implemented/wired/supported/available/shipped/landed".
# Deliberately narrow (a handful of fixed phrasings) rather than a broad
# NLP heuristic: a false negative here just means a claim goes unflagged
# (same posture as every other best-effort doc-drift heuristic in this
# module), but a false positive would make NEGEXIST001 noisy enough to be
# ignored, which is worse than under-detecting.
_NEGEXIST_PHRASE_RE = re.compile(
    r"\b(?:does not|doesn't|do not|don't)\s+(?:yet\s+)?exist\b"
    r"|\bnot\s+yet\s+(?:built|implemented|wired(?:\s+up)?|supported|available"
    r"|shipped|landed)\b"
    r"|\b(?:not\s+(?:built|implemented|wired(?:\s+up)?|supported|available"
    r"|shipped|landed)\s+yet)\b",
    re.IGNORECASE,
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


# T-1651: CHANGELOG.md entries describe PAST bug conditions ("X hangs when
# the named ref does not exist") as part of explaining an already-shipped
# fix, never an open commitment the way every other doc's negexist prose
# does -- and CHANGELOG.md is exclusively `frob ticket land`-owned
# (docs/guides/agent-playbook.md, section 4b, T-0731), so a worktree
# agent can never even apply the documented remedy
# (`frob:until T-####`) there. Confirmed empirically (T-1651): every one
# of this repo's own historical NEGEXIST001 CHANGELOG.md hits was this
# exact "bug-condition, not missing-feature" shape.
_NEGEXIST_EXEMPT_DOCS = frozenset({"CHANGELOG.md"})


def _negexist_phrase_edge(
    line: str, doc_path: str, slug: str, lineno: int
) -> Edge | None:
    """T-1229: `CLAIMS_ABSENCE` edge for a negative-existence-claim phrase
    (`_NEGEXIST_PHRASE_RE`) found in `line`, or `None` -- split out of
    `markdown_anchors`'s main loop (ARCH001) since this is the one match
    kind with its own pre-check (a directive comment line is never itself
    prose worth heuristic-scanning, so e.g. this very module's own
    docstring/comment text describing the heuristic never self-matches).
    `doc_path` in `_NEGEXIST_EXEMPT_DOCS` (T-1651) short-circuits before
    the phrase search -- see that set's own docstring."""
    if doc_path in _NEGEXIST_EXEMPT_DOCS:
        return None
    if "<!--" in line and "-->" in line:
        return None
    negexist = _NEGEXIST_PHRASE_RE.search(line)
    if negexist is None:
        return None
    return Edge(
        src=f"{doc_path}#{slug}",
        kind=EdgeKind.CLAIMS_ABSENCE,
        target=negexist.group(0),
        origin=f"{doc_path}:{lineno}",
    )


# frob:ticket T-1989
def _directive_edge(line: str, doc_path: str, slug: str, lineno: int) -> Edge | None:
    """One `DESCRIBES`/`ENUMERATES`/`UNTIL`/`TICKET`/`DOC` edge for `line`,
    or `None` -- split out of `markdown_anchors`'s main loop (ARCH001):
    these directive-comment forms are mutually exclusive per line and
    checked in this fixed order, matching the original inline loop's
    semantics exactly (first match wins, `markdown_anchors` still short-
    circuits on a non-`None` result before falling through to the
    negexist-phrase check). T-1989 adds the `TICKET`/`DOC` cases: measured
    as the two largest classes of `_unhandled_markdown_directive` findings
    (35 and 18 respectively) once T-1968 made unhandled markdown
    directives loud, both consistently well-formed provenance tags (never
    prose), so routing them to real edges is the correct disposition."""
    describes = _DESCRIBES_RE.search(line)
    if describes is not None:
        facet = describes.group("facet") or "sig"
        return Edge(
            src=f"{doc_path}#{slug}",
            kind=EdgeKind.DESCRIBES,
            target=describes.group("symref"),
            origin=doc_path,
            attrs={"facet": facet},
        )
    enumerates = _ENUMERATES_RE.search(line)
    if enumerates is not None:
        return Edge(
            src=f"{doc_path}#{slug}",
            kind=EdgeKind.ENUMERATES,
            target=enumerates.group("symref"),
            origin=f"{doc_path}:{lineno}",
            attrs={"members": enumerates.group("members")},
        )
    until = _UNTIL_RE.search(line)
    if until is not None:
        return Edge(
            src=f"{doc_path}#{slug}",
            kind=EdgeKind.UNTIL,
            target=until.group("ticket"),
            origin=f"{doc_path}:{lineno}",
        )
    ticket = _TICKET_MD_RE.search(line)
    if ticket is not None:
        return Edge(
            src=f"{doc_path}#{slug}",
            kind=EdgeKind.TICKET,
            target=ticket.group("ticket"),
            origin=f"{doc_path}:{lineno}",
        )
    doc = _DOC_MD_RE.search(line)
    if doc is not None:
        return Edge(
            src=f"{doc_path}#{slug}",
            kind=EdgeKind.DOC,
            target=doc.group("target"),
            origin=f"{doc_path}:{lineno}",
        )
    return None


# frob:ticket T-1968
# A bare `<!-- frob:<verb> ... -->` shape, matched generically so a NEW
# unhandled verb needs no new regex here to be caught -- deliberately the
# mirror of `_LINE_RE`'s code-comment shape, but anchored to the
# HTML-comment delimiters markdown directives always use.
_ANY_MD_DIRECTIVE_RE = re.compile(r"<!--\s*frob:(?P<verb>\S+)")
# The `frob:waive <RULE> reason="..."` markdown shape -- several gates
# each independently invented their OWN tiny per-rule regex reading it
# directly out of markdown TEXT, entirely outside `frob.graph`/this
# module: `frob.gates._refs._md_waived_rules` (REF001/REF002, T-0466),
# `frob.gates._docptr._WAIVE_DOC006_RE` (DOC006), `frob.gates.
# _docblocks_refs._WAIVE_DOC004_RE` (DOC004), `frob.gates._inv.
# _DOC_WAIVE_MARKER_RE` (INV003/INV004). T-1968's OWN measured evidence
# (docs/modules/fuzz.md's DOC006 waivers, docs/modules/deploy.md's
# INV003/INV004 waivers, `gate:DOC 0 waived`) undercounted: those two
# files' waivers are almost certainly ALREADY being honored by _docptr.py/
# _inv.py's own mechanisms -- `0 waived` undercounts because those
# mechanisms suppress the violation BEFORE it is ever emitted (no
# graph-edge WaiverRef to count), not because they do nothing. Verified by
# reading each gate's own source, not re-derived from the ticket's claim
# alone. `frob.gates._mutation_evidence`'s BUG002 waiver reads a ticket's
# OWN body text (a different scan surface, tickets/**, not general
# markdown docs) -- included here too since a ticket body IS markdown.
_MD_WAIVE_RE = re.compile(r'frob:waive\s+(?P<rule>\S+)\s+reason="')
# T-1968: every rule id SOME gate's own dedicated mechanism actually
# reads directly out of markdown text today. Any OTHER rule id in the
# same `frob:waive <RULE> reason="..."` shape is accepted syntactically
# and suppresses nothing -- the silent-no-op this ticket exists to make
# loud (T-1968's own measured incident was itself two rules this set
# does NOT cover: a markdown `frob:waive` naming a rule with no such
# mechanism at all is still exactly as silently inert as believed, just
# not fuzz.md/deploy.md's specific two examples).
_MD_WAIVE_HONORED_RULES = frozenset(
    {"REF001", "REF002", "DOC004", "DOC006", "INV003", "INV004", "BUG002"}
)
# Verbs `markdown_anchors`'s OWN loop already turns into a real edge
# (describes/enumerates/until/ticket/doc, T-1989 adding the latter two),
# plus verbs a DIFFERENT module owns and reads directly from markdown
# text -- neither is "unhandled", so neither belongs in this ticket's
# diagnostic:
# - `generated-start`/`generated-end`: `frob.gates._docblocks`'s table
#   fence markers (T-1011).
# - `invariant`: `frob.gates._inv._DOC_INVARIANT_MARKER_RE` (INV002/
#   INV003/INV004's own markdown-side anchor, T-1989 -- the code-comment
#   form `# frob:invariant INV-###` already routes through `_VERB_TABLE`
#   above; this is markdown's separate, independently-read form of the
#   SAME verb, not a second directive).
# - `claims`: `frob.gates._sys._CLAIMS_RE` (DOC003's exhaustiveness-proof
#   marker, T-1989).
# - `_RESERVED_MARKER_VERBS` (used-by/secret-fake/raises): already
#   recognized as owned-elsewhere for the code-comment path above; T-1989
#   folds the same set in here since their own scanners (frob.gates._refs,
#   frob.gates._secrets, frob.gates._exhaustive_handling) read raw text
#   across every tracked file type, markdown included, not just source.
# frob:ticket T-1989
_MD_HANDLED_VERBS = frozenset(
    {"describes", "enumerates", "until", "ticket", "doc"}
    | {"generated-start", "generated-end", "invariant", "claims"}
    | _RESERVED_MARKER_VERBS
)


# frob:ticket T-1968
def _unhandled_markdown_directive(
    line: str, doc_path: str, lineno: int
) -> MalformedDirective | None:
    """T-1968: a `MalformedDirective` for a `<!-- frob:<verb> ... -->`
    markdown directive that nothing in this repo actually reads --
    either an unrecognized verb outright, or a `frob:waive <RULE> ...`
    whose `RULE` is not one of the handful `frob.gates._refs` itself
    consumes from markdown (`_MD_WAIVE_HONORED_RULES`). `None` for a
    handled verb (`_MD_HANDLED_VERBS`) or a line with no `frob:`-shaped
    HTML comment at all. The `.reason` text is deliberately phrased to
    avoid the literal substrings `_dsl001_violations` excludes as
    already-claimed-elsewhere (`frob:waive`/`frob:tests`/`frob:debt`) --
    this finding IS meant to fall through DSL001's own generic catch-all,
    not be mistaken for a WAIVE001 missing-`reason=` case (every
    incident this ticket measured already carries a real `reason=`)."""
    match = _ANY_MD_DIRECTIVE_RE.search(line)
    if match is None:
        return None
    verb = match.group("verb")
    if verb == "waive":
        waive = _MD_WAIVE_RE.search(line)
        if waive is None:
            # Shape-matched "frob:waive" but not the full recognized
            # `frob:waive <RULE> reason="..."` form -- DSL001's own
            # code-comment-shaped malformed handling does not apply to
            # markdown at all today, so this is reported the same
            # generic way as any other unhandled markdown directive
            # rather than invented as a second, markdown-only shape of
            # WAIVE001.
            return MalformedDirective(
                file=doc_path,
                line=lineno,
                reason=(
                    f"unhandled markdown directive (verb={verb!r}): does not "
                    f'match the recognized "waive RULE reason=..." markdown form'
                ),
            )
        rule = waive.group("rule")
        if rule in _MD_WAIVE_HONORED_RULES:
            return None
        return MalformedDirective(
            file=doc_path,
            line=lineno,
            reason=(
                f"unhandled markdown directive (verb={verb!r}, rule={rule!r}): "
                f"only {sorted(_MD_WAIVE_HONORED_RULES)} are read from "
                f"markdown waivers -- this suppresses nothing"
            ),
        )
    if verb in _MD_HANDLED_VERBS:
        return None
    return MalformedDirective(
        file=doc_path,
        line=lineno,
        reason=f"unhandled markdown directive (verb={verb!r}): nothing reads it",
    )


# frob:doc docs/modules/graph.md#comment-dsl
# frob:tests tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence.test_until_directive_emits_until_edge  # noqa: E501
# frob:tests tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence.test_negative_existence_phrase_emits_claims_absence_edge  # noqa: E501
# frob:tests tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence.test_not_yet_wired_phrase_is_also_detected  # noqa: E501
# frob:tests tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence.test_directive_comment_line_itself_never_matches_the_heuristic  # noqa: E501
# frob:tests tests/unit/gates/test_negexist.py::TestMarkdownAnchorsUntilAndClaimsAbsence.test_plain_prose_with_no_matching_phrase_emits_nothing  # noqa: E501
# frob:ticket T-1433
# frob:ticket T-1989
# frob:waive AFFECT001 reason="pure ARCH001 line-count split (extracted \
# _directive_edge/_negexist_phrase_edge helpers, preserving match order and behavior \
# verbatim -- tests/unit/gates/test_negexist.py's tests stay green); the documented \
# comment-DSL contract in docs/modules/graph.md#comment-dsl is unchanged, so it needs \
# no update"
def markdown_anchors(
    doc_path: str, text: str
) -> tuple[tuple[Edge, ...], tuple[MalformedDirective, ...]]:
    """Extract `<!-- frob:describes ... -->` and `<!-- frob:enumerates ... -->`
    anchors bound to the nearest heading (T-1227 adds the latter), plus
    (T-1968) a `MalformedDirective` for any OTHER `<!-- frob:<verb> ... -->`
    HTML-comment directive this function does not itself turn into a real
    edge -- see `_unhandled_markdown_directive` for the exact "handled"
    set. This is markdown's half of DSL001's own catch-all contract
    (`_dsl001_violations`'s docstring: "no frob: comment that fails to
    parse into a real edge goes unreported") -- before T-1968, a markdown
    file's directive comments never even ATTEMPTED this check at all, so
    `<!-- frob:waive DOC006 reason="..." -->` (a real, deliberate T-1023
    burn-down waiver) was accepted as silent prose with no error, no
    warning, and no suppressed finding."""
    edges: list[Edge] = []
    malformed: list[MalformedDirective] = []
    slug = "top"
    seen: dict[str, int] = {}
    # T-1970: escape mentions BEFORE any directive-shaped matching, same
    # single earliest insertion point `parse_directives` uses for code
    # comments.
    text = mask_frob_mentions(text)
    # T-1989: a SECOND, directive-matching-only view with fenced/inline
    # code spans blanked too -- kept separate from `text` (rather than
    # reassigning `text = _blank_code_spans(text)`) because heading-slug
    # computation must still see a heading's own backtick-formatted TEXT
    # (`## \`markdown_anchors\``) verbatim; blanking that would corrupt
    # every DESCRIBES/ENUMERATES target resolving against it. Both views
    # share the exact same line count/newline positions (`_blank_code_
    # spans` preserves newlines), so indexing them in lockstep below is
    # safe.
    directive_view = _blank_code_spans(text)
    directive_lines = directive_view.splitlines()
    for lineno, line in enumerate(text.splitlines(), start=1):
        heading = _HEADING_RE.match(line)
        if heading is not None:
            slug = dedupe_slug(slugify(heading.group(2)), seen)
            continue
        directive_line = directive_lines[lineno - 1]
        directive_edge = _directive_edge(directive_line, doc_path, slug, lineno)
        if directive_edge is not None:
            edges.append(directive_edge)
            continue
        negexist_edge = _negexist_phrase_edge(line, doc_path, slug, lineno)
        if negexist_edge is not None:
            edges.append(negexist_edge)
            continue
        unhandled = _unhandled_markdown_directive(directive_line, doc_path, lineno)
        if unhandled is not None:
            malformed.append(unhandled)
    _log.debug(
        "%s: %d describes/enumerates/until/claims-absence anchor(s), "
        "%d unhandled directive(s)",
        doc_path,
        len(edges),
        len(malformed),
    )
    return tuple(edges), tuple(malformed)


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
# frob:ticket T-1176
def _attrs_verb_error_waive(
    attrs: dict[str, str], *, path: str, lineno: int
) -> MalformedDirective | None:
    """`frob:waive`'s own attribute requirements: `reason=` OR `preset=`
    mandatory (T-1176 -- `preset="<name>"` resolves against
    `frob.graph._waive_presets.WAIVE_PRESETS`, a single documented table,
    instead of every site hand-writing the same boilerplate reason prose;
    an unknown preset name is a malformed directive, never a silent
    no-op), an optional `until=` must be a `YYYY-MM-DD` date (T-0753, the
    same grammar `frob:deprecated`'s `sunset=` uses)."""
    preset = attrs.get("preset")
    if "reason" not in attrs and preset is None:
        return MalformedDirective(
            file=path,
            line=lineno,
            reason='frob:waive requires reason="..." or preset="<name>"',
        )
    if preset is not None:
        from frob.graph._waive_presets import resolve_preset

        resolved = resolve_preset(preset)
        if resolved is None:
            return MalformedDirective(
                file=path,
                line=lineno,
                reason=f"frob:waive preset={preset!r} is not a known preset",
            )
        attrs.setdefault("reason", resolved)
    until = attrs.get("until")
    if until is not None and not _DATE_RE.match(until.strip()):
        return MalformedDirective(
            file=path,
            line=lineno,
            reason=(f"frob:waive until={until!r} is not a YYYY-MM-DD date"),
        )
    return None


def _attrs_verb_error_debt(
    attrs: dict[str, str], *, path: str, lineno: int
) -> MalformedDirective | None:
    """`frob:debt`'s own attribute requirements: `reason=` and `ticket=`
    both mandatory."""
    missing = [key for key in ("reason", "ticket") if key not in attrs]
    if not missing:
        return None
    return MalformedDirective(
        file=path,
        line=lineno,
        reason=(
            'frob:debt requires reason="..." and ticket="T-####" '
            f"(missing: {', '.join(missing)})"
        ),
    )


def _attrs_verb_error_deprecated(
    attrs: dict[str, str], *, path: str, lineno: int
) -> MalformedDirective | None:
    """`frob:deprecated`'s own attribute requirements: `sunset=` and
    `ticket=` both mandatory, `sunset=` must be a `YYYY-MM-DD` date."""
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
                f"frob:deprecated sunset={attrs['sunset']!r} is not a YYYY-MM-DD date"
            ),
        )
    return None


def _attrs_verb_error_protocol(
    attrs: dict[str, str], *, path: str, lineno: int
) -> MalformedDirective | None:
    """`frob:protocol`'s own attribute requirements: `states=`/`initial=`
    mandatory, `initial=` must be one of the declared `states=`, and an
    optional `cleanup=` must be a known kind (defaulted to `on-error`)."""
    missing = [key for key in ("states", "initial") if key not in attrs]
    if missing:
        return MalformedDirective(
            file=path,
            line=lineno,
            reason=(
                'frob:protocol requires states="S1,S2,..." and '
                f'initial="..." (missing: {", ".join(missing)})'
            ),
        )
    states = [s.strip() for s in attrs["states"].split(",") if s.strip()]
    if not states:
        return MalformedDirective(
            file=path,
            line=lineno,
            reason='frob:protocol states="..." must list at least one state',
        )
    if attrs["initial"] not in states:
        return MalformedDirective(
            file=path,
            line=lineno,
            reason=(
                f"frob:protocol initial={attrs['initial']!r} is not one "
                f"of its own states={states!r}"
            ),
        )
    cleanup = attrs.get("cleanup", "on-error")
    if cleanup not in _CLEANUP_KINDS:
        return MalformedDirective(
            file=path,
            line=lineno,
            reason=(
                f"frob:protocol cleanup={cleanup!r} must be one of "
                f"{sorted(_CLEANUP_KINDS)}"
            ),
        )
    attrs.setdefault("cleanup", "on-error")
    return None


def _attrs_verb_error_transition(
    attrs: dict[str, str], *, path: str, lineno: int
) -> MalformedDirective | None:
    """`frob:transition`'s own attribute requirements: `proto=`/`from=`/
    `to=` all mandatory."""
    missing = [key for key in ("proto", "from", "to") if key not in attrs]
    if not missing:
        return None
    return MalformedDirective(
        file=path,
        line=lineno,
        reason=(
            'frob:transition requires proto="NAME" from="S" to="T" '
            f"(missing: {', '.join(missing)})"
        ),
    )


def _attrs_verb_error_requires(
    attrs: dict[str, str], *, path: str, lineno: int
) -> MalformedDirective | None:
    """`frob:requires`'s own attribute requirements: `proto=`/`state=`
    both mandatory."""
    missing = [key for key in ("proto", "state") if key not in attrs]
    if not missing:
        return None
    return MalformedDirective(
        file=path,
        line=lineno,
        reason=(
            'frob:requires requires proto="NAME" state="S" '
            f"(missing: {', '.join(missing)})"
        ),
    )


def _attrs_verb_error_tests(
    attrs: dict[str, str], *, path: str, lineno: int
) -> MalformedDirective | None:
    """`frob:tests`'s own attribute requirements: an optional `kind=`
    (defaulted to `unit`) must be a known kind."""
    attrs.setdefault("kind", "unit")
    if attrs["kind"] in _TESTS_KINDS:
        return None
    # T-0237: the literal 'frob:tests' substring lets
    # frob.gates._test010_violations pick this MalformedDirective out of
    # the mixed pile in GraphSnapshot.malformed, mirroring how WAIVE001
    # filters frob:waive's own malformed directives.
    return MalformedDirective(
        file=path,
        line=lineno,
        reason=(
            f"frob:tests invalid kind={attrs['kind']!r}; "
            f"must be one of {sorted(_TESTS_KINDS)}"
        ),
    )


# frob:ticket T-0757
def _attrs_verb_error_invariant(
    attrs: dict[str, str], *, path: str, lineno: int
) -> MalformedDirective | None:
    """`frob:invariant`'s two OPTIONAL obligation attrs (T-0757, the
    T-0611/T-0682 design-invariant class as gates): `no_import=
    "pkg[,pkg2,...]"` (import-forbidding -- each entry a dotted module
    path, `_IMPORT_MODULE_RE`) and `establishes="<property text>"`
    (establish-property -- non-empty text). A bare `frob:invariant
    INV-###` with neither attr is unaffected and still valid; the two
    attrs may also coexist on one anchor (no exclusivity rule between
    them -- an anchor can carry both obligations at once). Enforcement
    (INV007/INV008) lives in `frob.gates._design_invariants`, joined
    against the graph's import specifiers and TESTS edges respectively --
    this validator only shapes the attribute syntax."""
    no_import = attrs.get("no_import")
    if no_import is not None:
        modules = [m.strip() for m in no_import.split(",")]
        if not modules or any(
            not m or _IMPORT_MODULE_RE.match(m) is None for m in modules
        ):
            return MalformedDirective(
                file=path,
                line=lineno,
                reason=(
                    f"frob:invariant no_import={no_import!r} must be a "
                    "comma-separated list of dotted module paths"
                ),
            )
    establishes = attrs.get("establishes")
    if establishes is not None and not establishes.strip():
        return MalformedDirective(
            file=path,
            line=lineno,
            reason='frob:invariant establishes="..." must not be empty',
        )
    return None


_VERB_ATTRS_VALIDATORS = {
    "waive": _attrs_verb_error_waive,
    "debt": _attrs_verb_error_debt,
    "deprecated": _attrs_verb_error_deprecated,
    "protocol": _attrs_verb_error_protocol,
    "transition": _attrs_verb_error_transition,
    "requires": _attrs_verb_error_requires,
    "tests": _attrs_verb_error_tests,
    "invariant": _attrs_verb_error_invariant,
}


def _parse_attrs_verb_error(
    verb: str, attrs: dict[str, str], *, path: str, lineno: int
) -> MalformedDirective | None:
    """The per-verb attribute requirement `verb` fails to meet, or `None` if
    it meets every requirement its verb declares (`_parse_attrs`'s per-verb
    dispatch, split out for ARCH001 -- T-0598). Each verb's own requirement
    lives in its own `_attrs_verb_error_*` validator; a verb with no
    validator here has no attribute requirements at all."""
    validator = _VERB_ATTRS_VALIDATORS.get(verb)
    if validator is None:
        return None
    return validator(attrs, path=path, lineno=lineno)


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

    if verb in _ATTR_ONLY_VERBS:
        # T-0744: `frob:transition`/`frob:requires` have no bare target
        # token -- the whole `rest` is `key="value"` attributes, and the
        # edge's target is the `proto=` attribute itself (guaranteed present
        # once `_parse_attrs_verb_error`'s per-verb check has passed).
        attrs = _parse_attrs(verb, rest, path=path, lineno=lineno)
        if isinstance(attrs, MalformedDirective):
            return attrs
        target = attrs["proto"]
    else:
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
# frob:tests \
# tests/unit/graph/test_dsl.py::TestContinuation.test_long_reason_continues_across_lines
# frob:tests \
# tests/unit/graph/test_dsl.py::TestContinuation.test_unrelated_directives_on_consecuti\
# ve_lines_do_not_fold
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
    a fresh, genuinely-valid directive (`_is_genuine_directive_start`) -- a
    gap (blank line, unrelated code between comments) breaks the run, and
    so does landing on a line that is plainly the start of an independent
    directive rather than free-text continuation content. This is what a
    genuine continuation line always satisfies (its text is prose/
    attribute fragments -- e.g. `long so it would overflow...` or
    `kind="integration"` -- that either don't look `frob:`-shaped at all,
    or do but fail to structurally parse as a real directive, like
    `frob:describes` mid-prose, T-0987) and what the reviewer's T-0286
    corruption repro violates: `# frob:ticket T-0002` on the physical line
    right after `# frob:ticket T-0001\` is itself a complete,
    independently-parseable directive, so it must be treated as its own
    comment run rather than swallowed into the previous line. (Line-number
    adjacency and `_enclosing_src` binding are NOT reliable discriminators
    here -- `frob.lang`'s following/enclosing heuristic can legitimately
    resolve two textually-unrelated comments to the same symbol, as the
    repro does when a trailing inline comment's "following" lookup reaches
    past its own statement into the next symbol -- so the fold guard must
    inspect the candidate line's own STRUCTURAL VALIDITY, not just its
    shape, position, or binding: a bare `frob:`-shaped prefix is not
    enough, since a directive's own prose can coincidentally contain one,
    T-0987.)

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

    Thin wrapper over `fold_comment_runs` (T-0441), which does the actual
    folding; this just drops the physical-line-count `fold_comment_runs`
    adds for callers (like `frob fmt`) that need to know which physical
    lines a logical directive spans, not just its folded text.
    """
    return [
        (text, lineno, src) for text, lineno, src, _count in fold_comment_runs(lines)
    ]


# frob:ticket T-0987
def _is_genuine_directive_start(line: str) -> bool:
    """Whether a physical comment line, on its own, is the START of a real
    directive rather than wrap-continuation prose that merely happens to
    open with a `frob:`-shaped token (T-0987).

    A bare `_LINE_RE` shape match (`frob:<token> ...`) is NOT enough: a
    directive's own free-text `reason="..."` prose can legitimately contain
    a substring like `frob:describes` (T-0985's repro, `src/frob/vet/
    _allow.py`/`src/frob/dup/_core.py`), and a canonical re-wrap can land
    that substring as the first token of its own physical line -- at which
    point a shape-only check misreads it as a fresh directive. The real
    discriminator is whether the line STRUCTURALLY PARSES: attempting
    `_parse_line` on it and getting back an `Edge` (a real directive) or
    `None` (a recognized `_RESERVED_MARKER_VERBS` marker another subsystem
    owns) means it is a genuine, independent directive start; getting back
    a `MalformedDirective` (unknown verb, missing target, bad attribute
    syntax -- exactly what `frob:describes` produces, since `describes` is
    not a registered verb) means the shape match was coincidental content,
    and the line must fold as a continuation instead. This generalizes
    past the one verified `frob:describes` token: ANY `frob:`-shaped
    substring that is not itself a real, complete directive is folded the
    same way, regardless of what its first token happens to spell.

    Genuinely adjacent, independently-valid directives (this repo's
    widespread stacked `frob:ticket`/`frob:tests` convention, and T-0286's
    own `test_unrelated_directives_on_consecutive_lines_do_not_fold`
    corruption repro) still parse to real `Edge`s here, so they still stop
    the fold exactly as before -- this only widens the exception for
    shape-matches that do not stand up as complete directives.
    """
    stripped = line.strip()
    if _LINE_RE.match(stripped) is None:
        return False
    result = _parse_line(stripped, path="", lineno=0, src="")
    return not isinstance(result, MalformedDirective)


# frob:ticket T-0441
# frob:doc docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441
# frob:tests \
# tests/unit/graph/test_dsl.py::TestFoldCommentRuns.test_run_length_matches_consumed_ph\
# ysical_lines
def fold_comment_runs(
    lines: list[tuple[int, str, str, int]],
) -> list[tuple[str, int, str, int]]:
    """Fold physical comment lines ending in a trailing backslash into the
    line that follows, same rule as `_fold_continuations`, but also return
    each logical line's PHYSICAL LINE COUNT as a 4th tuple element -- how
    many entries of `lines` were consumed into it.

    `_fold_continuations`'s plain `(logical_text, lineno, src)` triples
    cannot tell a caller which physical lines a logical directive's folded
    form actually spans (only where it started); a caller that needs to
    REWRITE those physical lines in place -- `frob fmt`'s canonical-form
    wrap/unwrap (T-0441) -- needs the span, so this is the one place that
    actually walks the fold loop; `_fold_continuations` is now a thin
    wrapper over this that just drops the count.
    """
    folded: list[tuple[str, int, str, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        start = i
        lineno, text, src, _comment_id = lines[i]
        head = text.rstrip("\r")
        while (
            head.rstrip().endswith("\\")
            and i + 1 < n
            and lines[i + 1][0] == lines[i][0] + 1
            and not _is_genuine_directive_start(lines[i + 1][1])
        ):
            head = head.rstrip()[:-1]
            i += 1
            head += lines[i][1].rstrip("\r")
        folded.append((head, lineno, src, i - start + 1))
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


# frob:ticket T-0744
def _protocol_coherence(edges: list[Edge]) -> list[MalformedDirective]:
    """ENFORCEABILITY (T-0744 user mandate): a `frob:protocol` bound by zero
    `frob:transition`/`frob:requires` edges in this file is itself a loud
    error, not a silently-uncatalogued declaration -- the same
    catalogued-is-not-enforced doctrine `frob:debt`/`frob:todo` coherence
    (`_debt_todo_coherence`) already applies. Scope note: this pass only
    sees edges from ONE file's `parse_directives` call, so a protocol
    declared in one file and bound entirely from another still reads as
    unbound here -- cross-file protocol binding tallying belongs to a
    graph-wide consumer (a later T-0739 child), not this per-file DSL pass.
    """
    bound = {
        e.attrs.get("proto")
        for e in edges
        if e.kind in (EdgeKind.TRANSITION, EdgeKind.REQUIRES)
    }
    malformed: list[MalformedDirective] = []
    for edge in edges:
        if edge.kind != EdgeKind.PROTOCOL or edge.target in bound:
            continue
        file, _, line = edge.origin.rpartition(":")
        _log.debug(
            "T-0744: frob:protocol %r declared with zero bindings in %s",
            edge.target,
            file or edge.origin,
        )
        malformed.append(
            MalformedDirective(
                file=file or edge.origin,
                line=int(line) if line.isdigit() else 0,
                reason=(
                    f"frob:protocol {edge.target!r} declared but has zero "
                    "frob:transition/frob:requires bindings in this file "
                    "-- an unenforced protocol is a drift error, never a "
                    "silent no-op"
                ),
            )
        )
    return malformed


# frob:ticket T-0744
def _infer_init_deinit_protocols(parsed: ParsedFile) -> tuple[Edge, ...]:
    """Zero-declaration convenience (T-0744): a bare `<prefix>_<init_word>`/
    `<prefix>_<deinit_word>` function pair (`_INFER_PAIRS`) implicitly
    declares a 3-state `uninitialized -> active -> closed` protocol with no
    `frob:protocol` comment at all, synthesizing the same PROTOCOL/
    TRANSITION edges an explicit declaration would produce (each carrying
    `inferred="true"` so a consumer can tell the two apart). Inference is
    ONLY for these declared name-pair patterns -- never a general machine-
    inference heuristic, per T-0744's explicit scope limit.
    """
    callables = {
        s.qualname
        for s in parsed.symbols
        if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)
    }
    edges: list[Edge] = []
    seen_protocols: set[str] = set()
    for sym in parsed.symbols:
        if sym.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            continue
        for init_word, deinit_word in _INFER_PAIRS:
            pair_edges = _inferred_protocol_edges_for_pair(
                parsed, sym, init_word, deinit_word, callables, seen_protocols
            )
            edges.extend(pair_edges)
    return tuple(edges)


# frob:ticket T-0976
def _inferred_protocol_edges_for_pair(
    parsed: ParsedFile,
    sym,  # noqa: ANN001
    init_word: str,
    deinit_word: str,
    callables: set[str],
    seen_protocols: set[str],
) -> list[Edge]:
    """One `(init_word, deinit_word)` candidate pair's inferred-protocol
    edges for `sym` (T-0744), or `[]` if `sym`'s name does not match the
    pair, its deinit counterpart is not a real callable, or this protocol
    was already synthesized by an earlier symbol -- `seen_protocols` is
    mutated IN PLACE to record a new match so the caller never double-
    counts the same protocol from a later symbol."""
    suffix = f"_{init_word}"
    if not sym.qualname.endswith(suffix):
        return []
    prefix = sym.qualname[: -len(suffix)]
    deinit_qualname = f"{prefix}_{deinit_word}"
    if deinit_qualname not in callables:
        return []
    proto = f"{prefix}#{init_word}/{deinit_word}"
    if proto in seen_protocols:
        return []
    seen_protocols.add(proto)
    origin = f"{parsed.path}:{sym.span[0]}"
    init_src = f"{parsed.path}::{sym.qualname}"
    deinit_src = f"{parsed.path}::{deinit_qualname}"
    _log.debug(
        "T-0744: inferred protocol %r from %s/%s in %s",
        proto,
        sym.qualname,
        deinit_qualname,
        parsed.path,
    )
    return [
        Edge(
            src=parsed.path,
            kind=EdgeKind.PROTOCOL,
            target=proto,
            origin=origin,
            attrs={
                "states": "uninitialized,active,closed",
                "initial": "uninitialized",
                "cleanup": "on-error",
                "inferred": "true",
            },
        ),
        Edge(
            src=init_src,
            kind=EdgeKind.TRANSITION,
            target=proto,
            origin=origin,
            attrs={
                "proto": proto,
                "from": "uninitialized",
                "to": "active",
                "inferred": "true",
            },
        ),
        Edge(
            src=deinit_src,
            kind=EdgeKind.TRANSITION,
            target=proto,
            origin=origin,
            attrs={
                "proto": proto,
                "from": "active",
                "to": "closed",
                "inferred": "true",
            },
        ),
    ]


# frob:doc docs/modules/graph.md#comment-dsl
# frob:doc docs/guides/extending/comment-dsl-directives.md#comment-dsl-directives
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
        # T-1970: mask `frob:quote(...)` mentions BEFORE any per-line
        # directive matching -- the single earliest point every line this
        # module ever inspects passes through, so `_LINE_RE`/`_parse_line`/
        # `_is_genuine_directive_start` all see the masked text uniformly
        # with no separate wiring per call site.
        masked_text = mask_frob_mentions(comment.text)
        physical = masked_text.splitlines() or [masked_text]
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
    edges.extend(_infer_init_deinit_protocols(parsed))
    malformed.extend(_protocol_coherence(edges))
    if malformed:
        _log.warning("%s: %d malformed directive(s)", parsed.path, len(malformed))
    _log.debug("%s: parsed %d directive edge(s)", parsed.path, len(edges))
    return tuple(edges), tuple(malformed)


__all__ = [
    "dedupe_slug",
    "fold_comment_runs",
    "markdown_anchors",
    "parse_directives",
    "slugify",
]
