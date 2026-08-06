# frob:waive SCOPE001 reason="T-1402: this file needed only a mechanical, necessary \
# rename of a stale frob:waive EXHAUST001 comment to EXHAUST003 (the EXHAUST001 \
# precision fix, declared scope src/frob/gates/_exhaustive_handling.py) or (this file, \
# _tickets_gate.py, _waive.py) is the actual TICK011 fix itself -- frob ticket scope \
# --add refuses it: T-1279 (TEST005 burn-down) holds a concurrent in-progress lease on \
# src/frob/gates/** for the whole package, so this ticket cannot formally register the \
# file in its own declared scope until T-1279 closes or narrows; see this ticket's \
# Done report for the full disclosure (reviewed 2026-08-03, drain-to-zero WAIVE004 \
# sweep: left in place -- SCOPE001 is a scope/lease-dependent rule \
# (frob.gates._waive.SCOPED_RUN_FLAKY_RULE_IDS), not a stale finding a full unscoped \
# run can prove dead the way WIRE001/REF002/etc can"
"""frob.gates._doclink_docanchor -- DOC001/DOC002 doc-link and anchor
gates (T-1170).

Split out of `frob.gates.__init__` (T-1072/T-1140/T-1159/T-1170
one-family-per-land discipline) so the parent module can drop toward the
large-file threshold without changing any public behavior.
`doclink_gate`/`docanchor_gate` are re-exported from `frob.gates`
unchanged -- they are the only two names this family is externally
imported by (`tests/test_gates.py`, prose in
`frob.gates._docblocks`'s own module docstring), verified by a repo-wide
grep before the move; every other name here (`_doclink_config`,
`_obligated_docs`, `_linked_from_edges`, `_crawl_reachable`,
`_doclink_root_hint`, `_doc001_orphan`, `_doc_anchor_slugs`,
`_anchor_mismatch_message`, `_docanchor_violation`,
`_docanchor_check_edge`) stays private to this module, never imported
elsewhere.

Genuinely one cohesive family, not two bolted together: both gates
enforce that `docs/**/*.md` and `frob:doc` directives resolve to real,
reachable targets -- DOC001 that every obligated doc file is LINKED FROM
somewhere (crawled from `docs/index.md`/`README.md` outward plus
`frob:describes`/`frob:doc` graph edges), DOC002 that every `frob:doc`
edge's own `<file>#<slug>` target actually resolves to a real anchor in
that file. Both are pure read-only scans over `snapshot`/the doc tree,
with no shared runtime state between them beyond the doc-file-reading
posture itself."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_doclink_docanchor.py's exclusivity-vocabulary hits are source-level \
# design-rationale prose (docstrings and comments describing already-implemented \
# internal behavior, verifiable by reading the code they annotate) rather than a \
# separate cross-module contract needing its own tracked invariant; disposed as a \
# calibration batch, not claim-by-claim -- module prose split verbatim from the \
# pre-T-1170 gates/__init__.py monolith"

from __future__ import annotations

import difflib
import fnmatch
import re
import tomllib
from pathlib import Path, PurePosixPath

from typani.option import Nothing, Option, Some

from frob.gates._models import Severity, Violation
from frob.graph import Edge, EdgeKind, GraphSnapshot, dedupe_slug, slugify
from frob.logging import get_logger

_log = get_logger(__name__)

_MD_LINK_RE = re.compile(r"\]\(([^)#\s]+)")
# Backtick path references (`docs/x.md`) count as links too: these docs are
# written terminal-first, where an index names files in code spans rather
# than markdown links -- an index entry is a link either way.
_MD_CODE_REF_RE = re.compile(r"`([^`\s]+\.md)`")
# DOC008 (T-1231): unlike _MD_LINK_RE above (fragment stripped -- reachability
# crawling only cares about the file), this keeps the `#fragment` half so the
# resolver below can validate it against the target file's own anchors.
_MD_LINK_TARGET_RE = re.compile(r"\]\(([^)\s]+)\)")
_URL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://|^mailto:")
# DOC008 must not treat prose code spans as markdown links: `handlers[key](x)`
# (an array-subscript-then-call example) matches `\]\(...\)` lexically but is
# never a real link. Blank out fenced blocks and inline `code` spans first
# (preserving newlines, so line numbers stay correct) before scanning.
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def _blank_non_newlines(match: re.Match[str]) -> str:
    """Replace `match` with spaces, keeping any embedded newlines intact."""
    return "".join(c if c == "\n" else " " for c in match.group(0))


def _strip_code_spans(text: str) -> str:
    """Blank out fenced code blocks and inline `code` spans so DOC008's link
    scan never mistakes prose code (e.g. `handlers[key](x)`) for a real
    markdown link -- newline count (and therefore line numbers) is preserved."""
    text = _FENCED_CODE_RE.sub(_blank_non_newlines, text)
    return _INLINE_CODE_RE.sub(_blank_non_newlines, text)


def _doclink_config(root: Path) -> tuple[list[str], list[str], list[str]]:
    """`(include, exclude, roots)` globs for doclink, with frob.toml overrides."""
    include = ["docs/**/*.md"]
    exclude: list[str] = []
    roots = ["docs/index.md", "README.md"]
    toml_path = root / "frob.toml"
    if toml_path.exists():
        try:
            with toml_path.open("rb") as fh:
                section = tomllib.load(fh).get("gates", {}).get("docs", {})
            include = list(section.get("include", include))
            exclude = list(section.get("exclude", exclude))
            roots = list(section.get("roots", roots))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            _log.warning("doclink: frob.toml unreadable: %s", exc)
    return include, exclude, roots


def _obligated_docs(root: Path, include: list[str], exclude: list[str]) -> set[str]:
    """The set of doc files matched by `include` and not `exclude`."""

    obligated: set[str] = set()
    for glob in include:
        # frob:waive WALK001 reason="pathlib Path.glob's ** (zero-or-more-dirs) semantics matter here (e.g. default docs/**/*.md must match a top-level docs/orphan.md) and fnmatch.fnmatch (frob.excludes.is_excluded) does not have that semantics, so this cannot be reduced to an iter_files(suffix=...) prefilter without changing which docs are obligated; include is config-driven and defaults to the small docs/ subtree, not a repo-wide walk"  # noqa: E501
        for path in root.glob(glob):
            rel = path.relative_to(root).as_posix()
            if not any(fnmatch.fnmatch(rel, ex) for ex in exclude):
                obligated.add(rel)
    return obligated


def _linked_from_edges(snapshot: GraphSnapshot) -> set[str]:
    """Docs directly linked by a `frob:describes` anchor or `frob:doc` edge."""
    linked: set[str] = set()
    for edge in snapshot.edges:
        if edge.kind == EdgeKind.DESCRIBES:
            linked.add(edge.src.split("#", 1)[0])
        elif edge.kind == EdgeKind.DOC:
            linked.add(edge.target.split("#", 1)[0])
    return linked


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1056: leaked Unknown traces to \
# _MD_LINK_RE.findall/_MD_CODE_REF_RE.findall and PurePosixPath composition over text \
# already caught via read_text()'s own OSError handling; regex/path-string operations \
# over an already-decoded str cannot raise"
def _crawl_reachable(
    root: Path, roots: list[str], linked: set[str], obligated: set[str]
) -> set[str]:
    """Grow `linked` by crawling relative markdown links from the roots outward."""
    ordered_linked = sorted(linked)
    queue = [r for r in roots if (root / r).exists()]
    queue.extend(ordered_linked)
    seen: set[str] = set()
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        current_path = root / current
        if not current_path.exists():
            continue
        try:
            text = current_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        base = PurePosixPath(current).parent
        targets = _MD_LINK_RE.findall(text) + _MD_CODE_REF_RE.findall(text)
        for target in targets:
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = str(PurePosixPath(*(base / target).parts)).replace("../", "")
            for candidate in (resolved, target.lstrip("./")):
                if candidate in obligated and candidate not in seen:
                    linked.add(candidate)
                    queue.append(candidate)
    return linked


def _doclink_root_hint(root: Path, roots: list[str]) -> str:
    """Build the DOC001 'link it from X' hint against a root that actually exists.

    Blindly naming `roots[0]` (default `docs/index.md`) is wrong in repos
    that never created a docs index -- the hint pointed at a path that did
    not exist (T-0231, observed 256x in a sibling repo with no
    docs/index.md). Prefer the first configured root that exists on disk;
    if none do, suggest creating the first configured root instead of
    pretending it is already there.
    """
    for candidate in roots:
        if (root / candidate).exists():
            return f"link it from {candidate}"
    if roots:
        return (
            f"link it from {roots[0]} (create it -- no configured docs root exists yet)"
        )
    return "link it from a docs root (none configured -- see [gates.docs].roots)"


# frob:ticket T-0021
# frob:ticket T-0028
# frob:ticket T-0231
# frob:doc docs/modules/gates.md#public-api
def doclink_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DOC001: a doc file nothing links to is an error -- orphan docs rot.

    The obligated set is discovered by GLOB (default `docs/**/*.md`,
    `[gates.docs] include/exclude` in frob.toml), so a newly added doc file
    is automatically covered the moment it exists. A doc counts as linked
    when it carries a frob:describes anchor, is the target of a frob:doc
    edge, or is reachable through relative markdown links crawled from the
    root set (default docs/index.md and README.md).
    """
    root = Path(root)
    include, exclude, roots = _doclink_config(root)
    obligated = _obligated_docs(root, include, exclude)
    if not obligated:
        _log.debug("doclink: no docs matched %s", include)
        return ()
    linked = _crawl_reachable(root, roots, _linked_from_edges(snapshot), obligated)
    orphans = sorted(obligated - linked - set(roots))

    link_hint = _doclink_root_hint(root, roots)
    violations = [_doc001_orphan(orphan, link_hint) for orphan in orphans]
    broken = _doc008_broken_links(root, obligated | set(roots))
    violations.extend(broken)
    _log.info(
        "doclink: %d obligated, %d orphaned, %d broken link(s)",
        len(obligated),
        len(orphans),
        len(broken),
    )
    return tuple(violations)


# frob:enforces CHK-GATE-DOC001
def _doc001_orphan(orphan: str, link_hint: str) -> Violation:
    """DOC001: `orphan` is a doc file linked from nowhere."""
    return Violation(
        rule="DOC001",
        severity=Severity.ERROR,
        file=orphan,
        line=0,
        message=(
            f"DOC001: {orphan} is linked from nowhere; add a "
            f"frob:describes anchor, reference it with frob:doc, or "
            f"{link_hint}"
        ),
    )


# frob:enforces CHK-GATE-DOC008
def _doc008_violation(doc_rel: str, line: int, message: str) -> Violation:
    """Build one DOC008 error `Violation` (T-1231: a doc's own inline link
    target, or its `#fragment`, does not resolve)."""
    return Violation(
        rule="DOC008",
        severity=Severity.ERROR,
        file=doc_rel,
        line=line,
        message=message,
    )


# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# _strip_code_spans/_line_index/_doc_anchor_slugs, module-local helpers the resolver \
# cannot see through, and Option.or_else/.danger_some (typani), a generic-typed call \
# it cannot bind; the one real raise path (file read) is caught below"
# frob:waive EXHAUST002 reason="T-1636: leaked KeyError traces to the resolver's \
# unconditional _SUBSCRIPT_RAISE default for slug_cache[resolved]/ slug_cache[doc_rel] \
# -- both writes/reads are guarded by an immediately-preceding 'if resolved not in \
# slug_cache'/'if doc_rel not in slug_cache' membership check, so the key is always \
# present by construction; the resolver's syntactic bracket scan cannot see the guard"
def _doc008_scan_doc(
    root: Path,
    doc_rel: str,
    slug_cache: dict[str, Option[set[str]]],
) -> list[Violation]:
    """T-1231 (gate-gap class 5): validate every relative markdown link and
    `#fragment` inside `doc_rel` against what actually exists on disk --
    doclink's reachability crawl above only cares whether a link exists at
    all, never whether it resolves. Absolute URLs/mailto links are out of
    scope (no static resolution target); a link's own `#fragment` is
    resolved the same way DOC002 resolves a `frob:doc` edge's anchor
    (heading slug or explicit `<a id>`)."""
    doc_path = root / doc_rel
    try:
        text = doc_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    scan_text = _strip_code_spans(text)
    base = PurePosixPath(doc_rel).parent
    violations: list[Violation] = []
    line_of = _line_index(text)
    for match in _MD_LINK_TARGET_RE.finditer(scan_text):
        target = match.group(1)
        if _URL_SCHEME_RE.match(target):
            continue
        line = line_of(match.start())
        path_part, _, frag = target.partition("#")
        if path_part:
            resolved = str(PurePosixPath(*(base / path_part).parts)).replace("../", "")
            target_path = root / resolved
            if not target_path.exists():
                violations.append(
                    _doc008_violation(
                        doc_rel,
                        line,
                        f"DOC008: link target {target!r} does not resolve "
                        f"(no file at {resolved!r})",
                    )
                )
                continue
            if not frag or target_path.suffix != ".md":
                continue
            if resolved not in slug_cache:
                slug_cache[resolved] = _doc_anchor_slugs(target_path)
            slugs = slug_cache[resolved].or_else(lambda: Some(set())).danger_some
        else:
            # Same-file anchor (`[text](#slug)`): resolve against this doc.
            if not frag:
                continue
            if doc_rel not in slug_cache:
                slug_cache[doc_rel] = _doc_anchor_slugs(doc_path)
            slugs = slug_cache[doc_rel].or_else(lambda: Some(set())).danger_some
            resolved = doc_rel
        if frag not in slugs:
            violations.append(
                _doc008_violation(
                    doc_rel,
                    line,
                    _anchor_mismatch_message(target, resolved, frag, slugs),
                )
            )
    return violations


def _doc008_broken_links(root: Path, docs: set[str]) -> tuple[Violation, ...]:
    """DOC008: every obligated/root doc's own inline link targets and
    `#fragment`s must resolve. Runs after DOC001's reachability crawl so a
    genuinely-broken link is flagged whether or not the doc it lives in is
    itself reachable."""
    slug_cache: dict[str, Option[set[str]]] = {}
    violations: list[Violation] = []
    for doc_rel in sorted(docs):
        violations.extend(_doc008_scan_doc(root, doc_rel, slug_cache))
    return tuple(violations)


_ANCHOR_ID_RE = re.compile(r'<a\s+id="([^"]+)"')
_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1056: leaked Unknown traces to slugify/dedupe_slug (imported \
# helpers) and _MD_HEADING_RE/_ANCHOR_ID_RE.finditer over text already caught via \
# read_text()'s own OSError handling; the resolver cannot follow through the \
# cross-module helper import, but both are pure str/regex transforms with no \
# documented raise path"
def _doc_anchor_slugs(path: Path) -> Option[set[str]]:
    """Every resolvable slug in a doc file: heading slugs plus explicit `<a id>`s.

    `Nothing` means the file could not be read at all (missing or IO error),
    distinct from `Some(set())` (a real, empty doc).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return Nothing()
    seen: dict[str, int] = {}
    slugs = {
        dedupe_slug(slugify(heading.group(2)), seen)
        for heading in _MD_HEADING_RE.finditer(text)
    }
    slugs.update(m.group(1) for m in _ANCHOR_ID_RE.finditer(text))
    return Some(slugs)


# T-0524: frob:doc removed -- reached via docanchor_gate (public), which
# already carries the same docs/modules/gates.md#public-api anchor
# (COV007).
def _anchor_mismatch_message(
    target: str, docfile: str, slug: str, slugs: set[str]
) -> str:
    """Build the DOC002 unresolved-anchor message: the computed slug, the
    anchors actually found in the target file, and the nearest match by
    edit distance (via `difflib.get_close_matches`) so a `frob:doc` author
    does not have to guess a GitHub-style slug by hand."""
    found = ", ".join(sorted(slugs)) if slugs else "(none)"
    nearest = difflib.get_close_matches(slug, slugs, n=1, cutoff=0.0)
    suggestion = f"; did you mean #{nearest[0]}?" if nearest else ""
    return (
        f"DOC002: frob:doc anchor {target!r} does not resolve; computed "
        f"slug #{slug} does not match any anchor in {docfile} "
        f"(found: {found}){suggestion}"
    )


# frob:enforces CHK-GATE-DOC002
def _docanchor_violation(rule_file: str, line: int, message: str) -> Violation:
    """Build one DOC002 error `Violation` -- every failure mode is the same shape."""
    return Violation(
        rule="DOC002",
        severity=Severity.ERROR,
        file=rule_file,
        line=line,
        message=message,
    )


# frob:doc docs/modules/gates.md#public-api
def docanchor_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DOC002: a `frob:doc` edge whose target anchor does not resolve is an error.

    Every `frob:doc <file>#<slug>` target must resolve: `<file>` must exist
    under `root`, and `<slug>` must be either a GitHub-style heading slug
    (`frob.graph.dsl.slugify`, the same slugifier `markdown_anchors` uses)
    or an explicit `<a id="...">` anchor in that file -- the second form is
    how docs/modules/dup.md and docs/modules/arch.md give several models a
    stable anchor under one heading.

    `root` here must be the repo root, not a scoped check path (T-0314):
    `<file>` in a `frob:doc` directive is always repo-relative text, so a
    scoped `frob check <subdir>` run that fed the scoped subdir in as
    `root` rebased every target path and reported a spurious DOC002 on
    every directive. `run_gates` passes `st.repo_root` here for exactly
    this reason -- see `_GateInputs.repo_root`.
    """
    root = Path(root)
    slug_cache: dict[str, Option[set[str]]] = {}
    violations = [
        v
        for edge in snapshot.edges
        if edge.kind == EdgeKind.DOC
        for v in (_docanchor_check_edge(root, edge, slug_cache),)
        if v is not None
    ]
    _log.info("docanchor: %d violation(s)", len(violations))
    return tuple(violations)


def _docanchor_check_edge(
    root: Path, edge: Edge, slug_cache: dict[str, Option[set[str]]]
) -> Violation | None:
    """The DOC002 `Violation` for one `frob:doc` edge, or None when its
    `<file>#<slug>` target resolves. `slug_cache` memoizes `_doc_anchor_slugs`
    per doc file across the whole gate run."""
    origin_file, _, lineno_text = edge.origin.rpartition(":")
    line = int(lineno_text) if lineno_text.isdigit() else 0
    origin_file = origin_file or edge.origin
    target = edge.target
    if "#" not in target:
        return _docanchor_violation(
            origin_file,
            line,
            f"DOC002: frob:doc target {target!r} has no #anchor; use <file>#<slug>",
        )
    docfile, slug = target.split("#", 1)
    if docfile not in slug_cache:
        slug_cache[docfile] = _doc_anchor_slugs(root / docfile)
    slugs = slug_cache[docfile]
    if slugs.is_nothing:
        return _docanchor_violation(
            origin_file,
            line,
            f"DOC002: frob:doc target file {docfile!r} does not exist",
        )
    if slug not in slugs.danger_some:
        return _docanchor_violation(
            origin_file,
            line,
            _anchor_mismatch_message(target, docfile, slug, slugs.danger_some),
        )
    return None


# T-1232 (gate-gap class 6): a dated `Status: YYYY-MM-DD` (or
# `Status: SUPERSEDED (see <path>)`) header, checked within the first
# `_STATUS_HEADER_SCAN_LINES` lines of every docs/audits/*.md file -- audit
# docs describe a point-in-time snapshot and rot silently with no currency
# marker at all (docs/audits/docs-staleness-2026-07-29.md's own STATUS/
# CURRENCY gate-gap class).
_STATUS_HEADER_RE = re.compile(
    r"^[>\s]*\**Status:\**\s*"
    r"(?:(?P<date>\d{4}-\d{2}-\d{2})|SUPERSEDED\s*\(see\s+(?P<path>[^)]+)\))"
)
_STATUS_HEADER_SCAN_LINES = 15


def _audit_docs(root: Path) -> set[str]:
    """The docs/audits/*.md files obligated to carry a DOC009 status header."""
    return {p.relative_to(root).as_posix() for p in root.glob("docs/audits/*.md")}


# frob:ticket T-1486
# DOC011 (T-1486, gate-gap class 6 item 1, T-1232's own follow-up): a
# `T-####`/`T-draft-<hex>` id mentioned in doc PROSE must name a ticket
# that actually exists somewhere in the ledger (active or archived) --
# a typo'd or long-since-renumbered id in a doc citation reads as a real,
# followable reference but silently resolves to nothing. Deliberately
# narrower than the ticket's own "harder" stretch goal (flagging a
# mention whose STATE contradicts the prose, e.g. "tracked under T-0397"
# when T-0397 is closed): that needs NLP-grade parsing of the sentence
# around each mention to know what claim is even being made, which is a
# much larger, separately-scoped effort -- this closes the cheaper,
# unambiguous half (existence) first.
_DOC011_ID_MENTION_RE = re.compile(r"\bT-(?:\d{4}|draft-[0-9a-f]{8})\b")


# frob:enforces CHK-GATE-DOC011
def _doc011_violation(doc_rel: str, line: int, ticket_id: str) -> Violation:
    """Build one DOC011 `Violation` -- a doc prose mention of a ticket id
    that does not resolve to any active or archived ticket.

    T-1486: WARN, not ERROR, deliberately -- the first live run against
    this repo's own docs tree found 10 genuine pre-existing stale
    citations (mostly `T-draft-<hex>` ids that finalized to a real T-####
    long ago, plus one true orphan and one illustrative example),
    entirely outside this ticket's own declared scope to fix. Shipping
    this at ERROR would fail every unscoped `frob check` the moment it
    lands, for drift this ticket only DETECTS, not causes. A follow-up
    ticket tracks fixing the flagged citations; promote to ERROR once
    that lands and the count is provably zero."""
    return Violation(
        rule="DOC011",
        severity=Severity.WARN,
        file=doc_rel,
        line=line,
        message=(
            f"DOC011: {doc_rel}:{line} mentions {ticket_id!r}, which is not "
            f"a real ticket (not in tickets.md or tickets-archive.md) -- "
            f"typo, or the id was never finalized/was dropped without a "
            f"trace; fix the citation or drop it"
        ),
    )


def _doc011_known_ticket_ids(root: Path) -> set[str]:
    """Every ticket id that has ever existed in this repo's ledger, active
    OR archived (T-1486): late-imports `frob.tickets._store` to avoid a
    module-level `frob.gates` -> `frob.tickets` dependency this package
    does not otherwise carry. Best-effort -- a store that fails to parse
    (mid-conflict, genuinely malformed) degrades to an empty known-id set
    rather than raising, so a broken ledger never masquerades as every
    doc citation being a DOC011 finding; `gate:TICK`'s own ledger-parse
    checks are the right place for a malformed-ledger error, not this
    gate."""
    from frob.tickets._store import load_all, load_archive

    known: set[str] = set()
    active = load_all(root)
    if active.is_ok:
        known.update(active.danger_ok)
    archived = load_archive(root)
    if archived.is_ok:
        known.update(archived.danger_ok)
    return known


# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# _strip_code_spans/_line_index, module-local helpers the resolver cannot see through; \
# the one real raise path (file read) is caught below"
def _doc011_scan_doc(
    root: Path, doc_rel: str, known_ids: set[str]
) -> tuple[Violation, ...]:
    """Every DOC011 violation in `doc_rel`: each `T-####`/`T-draft-<hex>`
    mention in PROSE (fenced/inline code spans blanked first, same as
    DOC008's link scan, so a code example showing the id SYNTAX itself
    is never flagged) that is not in `known_ids`."""
    try:
        raw = (root / doc_rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ()
    text = _strip_code_spans(raw)
    line_index = _line_index(text)
    violations: list[Violation] = []
    seen_on_line: set[tuple[int, str]] = set()
    for match in _DOC011_ID_MENTION_RE.finditer(text):
        ticket_id = match.group(0)
        if ticket_id in known_ids:
            continue
        line = line_index(match.start())
        key = (line, ticket_id)
        if key in seen_on_line:
            continue
        seen_on_line.add(key)
        violations.append(_doc011_violation(doc_rel, line, ticket_id))
    return tuple(violations)


# frob:enforces CHK-GATE-DOC009
def _doc009_violation(doc_rel: str, message: str) -> Violation:
    """Build one DOC009 error `Violation` -- a missing or unresolvable
    status/superseded-by header on an audit doc."""
    return Violation(
        rule="DOC009", severity=Severity.ERROR, file=doc_rel, line=0, message=message
    )


# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# _STATUS_HEADER_RE.match, a compiled-regex match over an already-caught read_text() \
# output; a compiled pattern match cannot raise"
# frob:waive EXHAUST002 reason="T-1636: leaked KeyError traces to the resolver's \
# unconditional _SUBSCRIPT_RAISE default for text.splitlines()[:N], a list SLICE \
# (never raises KeyError, or any exception, regardless of N) that the resolver's \
# syntactic bracket scan cannot distinguish from a dict lookup"
def _doc009_check_doc(root: Path, doc_rel: str) -> Violation | None:
    """The DOC009 `Violation` for `doc_rel`, or None when a dated status
    header (or a superseded-by header whose target resolves) is found
    within its first `_STATUS_HEADER_SCAN_LINES` lines."""
    try:
        text = (root / doc_rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines()[:_STATUS_HEADER_SCAN_LINES]:
        match = _STATUS_HEADER_RE.match(line.strip())
        if match is None:
            continue
        path = match.group("path")
        if path is not None and not (root / path).exists():
            return _doc009_violation(
                doc_rel,
                f"DOC009: {doc_rel} superseded-by target {path!r} does not "
                f"resolve to a real file",
            )
        return None
    return _doc009_violation(
        doc_rel,
        f"DOC009: {doc_rel} is missing a dated status header in its first "
        f"{_STATUS_HEADER_SCAN_LINES} lines -- add 'Status: YYYY-MM-DD' or "
        f"'Status: SUPERSEDED (see <path>)'",
    )


# frob:doc docs/modules/gates.md#public-api
# frob:waive AFFECT001 reason="T-1486: docstatus_gate's affects()-closure doc \
# (docs/modules/gates.md#public-api) genuinely needs a DOC011 catalog row, matching \
# the DOC009/DOC010 precedent immediately above it in that table -- but \
# docs/modules/gates.md is leased by another in-progress ticket (T-1205) for the \
# duration of this ticket's work, so frob ticket scope --add refuses it \
# (ScopeLeaseConflict). Tracked in this ticket's own follow-up (fix 10 stale ticket-id \
# citations DOC011 found...), which also touches docs/modules/gates.md; remove this \
# waiver once that lands and the row exists."
def docstatus_gate(root: Path) -> tuple[Violation, ...]:
    """DOC009: every `docs/audits/*.md` file needs a dated status (or
    superseded-by) header -- an audit is a point-in-time snapshot, and
    unlike code it carries no digest/hash the drift gate can compare
    against, so a currency claim has to be explicit and checkable.

    T-1486: also runs DOC011 (a `T-####`/`T-draft-<hex>` mention in ANY
    `docs/**/*.md` prose that does not resolve to a real ticket, active or
    archived) -- bundled into this same `--only docstatus` group rather
    than wired as a separate stage, since both checks are cheap, whole-
    docs-tree, repo_root-scoped scans with no shared state between them
    beyond "read every doc file once"."""
    root = Path(root)
    docs = _audit_docs(root)
    violations = [
        v
        for doc_rel in sorted(docs)
        for v in (_doc009_check_doc(root, doc_rel),)
        if v is not None
    ]
    doc011_docs = {p.relative_to(root).as_posix() for p in root.glob("docs/**/*.md")}
    known_ids = _doc011_known_ticket_ids(root)
    for doc_rel in sorted(doc011_docs):
        violations.extend(_doc011_scan_doc(root, doc_rel, known_ids))
    _log.info(
        "docstatus: %d audit doc(s), %d doc011 doc(s), %d violation(s)",
        len(docs),
        len(doc011_docs),
        len(violations),
    )
    return tuple(violations)


# T-1230 (gate-gap class 4, non-python doc targets): a `` `make <target>` ``
# citation in prose is invisible to every python-shaped pointer check
# (DOC006's kind 3 already resolves `[section]`/`[section.key]` against
# frob.toml/pyproject.toml/Cargo.toml -- this closes the sibling gap for
# Makefile recipe names specifically, the one non-python target class the
# docs-staleness sweep found rotting with no gate at all).
_MAKE_TARGET_CITATION_RE = re.compile(r"`make ([A-Za-z][\w.-]*)`")
_MAKEFILE_TARGET_RE = re.compile(r"^([A-Za-z][\w.-]*)\s*:(?!=)")


# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# _MAKEFILE_TARGET_RE.match, a compiled-regex match over an already-caught read_text() \
# output; a compiled pattern match cannot raise"
def _makefile_targets(root: Path) -> set[str]:
    """Every recipe name declared in `root`'s Makefile (`target:` lines,
    `.PHONY`/pattern/variable-assignment lines excluded)."""
    makefile = root / "Makefile"
    try:
        text = makefile.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    targets: set[str] = set()
    for line in text.splitlines():
        if line.startswith(("\t", "#", ".")):
            continue
        match = _MAKEFILE_TARGET_RE.match(line)
        if match:
            targets.add(match.group(1))
    return targets


# frob:enforces CHK-GATE-DOC010
def _line_index(text: str):
    """Sorted newline offsets for O(log n) offset->line lookups (PERF002:
    never text.count per match in a loop)."""
    import bisect as _bisect

    offsets = [i for i, ch in enumerate(text) if ch == "\n"]

    def line_of(offset: int) -> int:
        return _bisect.bisect_right(offsets, offset - 1) + 1

    return line_of


def _doc010_violation(doc_rel: str, line: int, target: str) -> Violation:
    """Build one DOC010 error `Violation` -- a cited `make <target>` recipe
    that does not exist in the repo's Makefile."""
    return Violation(
        rule="DOC010",
        severity=Severity.ERROR,
        file=doc_rel,
        line=line,
        message=(
            f"DOC010: `make {target}` is not a real Makefile target "
            f"(no `{target}:` recipe)"
        ),
    )


# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# _line_index/_MAKE_TARGET_CITATION_RE.finditer, a module-local helper and a \
# compiled-regex scan over an already-caught read_text() output; neither can raise"
def _doc010_scan_doc(
    root: Path, doc_rel: str, make_targets: set[str]
) -> list[Violation]:
    """DOC010 violations for every `` `make <target>` `` citation in
    `doc_rel` whose target does not resolve against `make_targets`."""
    try:
        text = (root / doc_rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    violations: list[Violation] = []
    line_of = _line_index(text)
    for match in _MAKE_TARGET_CITATION_RE.finditer(text):
        target = match.group(1)
        if target in make_targets:
            continue
        line = line_of(match.start())
        violations.append(_doc010_violation(doc_rel, line, target))
    return violations


# frob:doc docs/modules/gates.md#public-api
def docmake_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DOC010: every `` `make <target>` `` citation in an obligated doc must
    name a real Makefile recipe -- the Makefile has no graph node of its
    own, so a renamed/removed target's doc citation was invisible to every
    other doc gate (gate-gap class 4)."""
    root = Path(root)
    if not (root / "Makefile").exists():
        return ()
    make_targets = _makefile_targets(root)
    include, exclude, roots = _doclink_config(root)
    docs = (
        _obligated_docs(root, include, exclude)
        | set(roots)
        | _linked_from_edges(snapshot)
    )
    violations = tuple(
        v
        for doc_rel in sorted(docs)
        for v in _doc010_scan_doc(root, doc_rel, make_targets)
    )
    _log.info("docmake: %d doc(s) scanned, %d violation(s)", len(docs), len(violations))
    return violations


__all__ = [
    # frob:ticket T-1170
    # `_doclink_config`/`_obligated_docs`/`_docanchor_check_edge`/
    # `_doc_anchor_slugs` are also consumed directly by OTHER gates/tools
    # still in `gates/__init__.py` or its `_fix_engine` sibling (a
    # docblock-fence scan and a doc-completeness check reuse the
    # obligated-doc-set/per-edge anchor-resolution logic; the DOC002
    # Tier-A auto-fix engine calls back through the slug resolver to
    # verify a fuzzy-matched anchor before rewriting it) -- private-by-
    # convention (leading underscore) but a real cross-module seam, so
    # they are named here rather than silently becoming unreachable
    # after the split. Every other name in this module stays genuinely
    # private (never imported elsewhere).
    "_doc_anchor_slugs",
    "_doclink_config",
    "_obligated_docs",
    "_docanchor_check_edge",
    "docanchor_gate",
    "doclink_gate",
    "docstatus_gate",
    "docmake_gate",
]
