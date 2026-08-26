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
elsewhere, EXCEPT `_doclink_config`/`_obligated_docs`/
`_linked_from_edges`/`_line_index`, which `frob.gates._docstatus`
(T-2843) also imports directly -- a deliberate, disclosed cross-module
seam, not an accidental leak.

T-2843: this module used to also carry docstatus_gate/docmake_gate/
docseverity_gate (DOC009/DOC010/DOC011/DOC013), bolted on after this
docstring was written without updating it. Those three now live in
`frob.gates._docstatus` -- a different actual characteristic
(docs/**/*.md CURRENCY/freshness checks) from this module's own
doc-tree-REACHABILITY concern (DOC001/DOC002).

Genuinely one cohesive family, not two bolted together: both gates
enforce that `docs/**/*.md` and `frob:doc` directives resolve to real,
reachable targets -- DOC001 that every obligated doc file is LINKED FROM
somewhere (crawled from `docs/index.md`/`README.md` outward plus
`frob:describes`/`frob:doc` graph edges), DOC002 that every `frob:doc`
edge's own `<file>#<slug>` target actually resolves to a real anchor in
that file. Both are pure read-only scans over `snapshot`/the doc tree,
with no shared runtime state between them beyond the doc-file-reading
posture itself."""

from __future__ import annotations

import difflib
import fnmatch
import re
import tomllib
from pathlib import Path, PurePosixPath

from typani.option import Nothing, Option, Some

from frob.gates._markdown_scan import strip_code_spans as _strip_code_spans
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
# never a real link. `_strip_code_spans` (T-1700: `frob.gates._markdown_scan.
# strip_code_spans`, imported above under its pre-extraction private name so
# every call site in this file stays unchanged) blanks fenced blocks and
# inline `code` spans first (preserving newlines, so line numbers stay
# correct) before either DOC008's link scan or DOC011's ticket-id scan below
# runs -- shared with TICK006 (`frob.gates._tickets_gate`) rather than a
# second, independently-drifting copy; see that module's own docstring for
# the T-1700 incident (`` `Filed: T-0104` `` inside a Done report) this
# extraction fixed.


def _resolve_relative_link(base: PurePosixPath, target: str) -> str | None:
    """Resolve a markdown link's relative path PART (no `#fragment`, no
    scheme) against `base` (the linking doc's own directory) using real
    `..`-pops-a-directory semantics -- T-2704: the prior `.replace("../",
    "")` deleted the `../` TEXT instead of popping a segment, so every
    valid parent-relative link (`../../design/x.md` from `docs/architecture`
    should resolve to `design/x.md`) instead kept both segments and read
    as broken. Returns `None` if the walk pops past the repo root (an
    escape attempt) -- callers must treat that as unresolvable, not
    silently accept a path outside the tree the crawl/scan is rooted at."""
    stack: list[str] = list(base.parts)
    for part in PurePosixPath(target).parts:
        if part in (".", ""):
            continue
        if part == "..":
            if not stack:
                return None
            stack.pop()
        else:
            stack.append(part)
    return str(PurePosixPath(*stack)) if stack else "."


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
            resolved = _resolve_relative_link(base, target)
            candidates = (
                (target.lstrip("./"),)
                if resolved is None
                else (resolved, target.lstrip("./"))
            )
            for candidate in candidates:
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


# frob:waive DUP001 reason="sibling small violation builders across meta-checks: \
# DOC001 (orphan doc file) here, VET004/VET-missing-read builders in frob.vet -- \
# coincidental short-function shape, unrelated rule domains"
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


# frob:waive DUP001 reason="sibling DOC002/DOC008 violation builders in the same \
# module: same 'every failure mode is the same shape' Violation(...) builder, \
# independently-evolving rule ids"
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
def _doc008_resolve_path_target(
    root: Path,
    doc_rel: str,
    base: PurePosixPath,
    target: str,
    path_part: str,
    line: int,
    slug_cache: dict[str, Option[set[str]]],
) -> tuple[str, set[str], Violation | None] | None:
    """DOC008's path-half resolution (a link with a real file target, as
    opposed to a same-file `#fragment`-only link) -- split out of
    `_doc008_scan_doc` (T-2704) to keep that function under ARCH001's
    length threshold after adding the `../` escape check. Returns `None`
    when the link resolves cleanly with nothing further to check, else
    `(resolved, slugs, violation_or_None)` for the caller's own fragment
    check."""
    resolved = _resolve_relative_link(base, path_part)
    if resolved is None:
        return (
            "",
            set(),
            _doc008_violation(
                doc_rel,
                line,
                f"DOC008: link target {target!r} escapes above the repo root",
            ),
        )
    target_path = root / resolved
    if not target_path.exists():
        return (
            resolved,
            set(),
            _doc008_violation(
                doc_rel,
                line,
                f"DOC008: link target {target!r} does not resolve "
                f"(no file at {resolved!r})",
            ),
        )
    _, _, frag = target.partition("#")
    if not frag or target_path.suffix != ".md":
        return None
    if resolved not in slug_cache:
        slug_cache[resolved] = _doc_anchor_slugs(target_path)
    slugs = slug_cache[resolved].or_else(lambda: Some(set())).danger_some
    return (resolved, slugs, None)


# frob:enforces CHK-GATE-DOC010
def _line_index(text: str):
    """Sorted newline offsets for O(log n) offset->line lookups (PERF002:
    never text.count per match in a loop). Shared with `frob.gates.
    _docstatus` (T-2843's split) -- DOC008 (this module) and DOC010 (that
    one) both need offset->line resolution over doc prose."""
    import bisect as _bisect

    offsets = [i for i, ch in enumerate(text) if ch == "\n"]

    def line_of(offset: int) -> int:
        return _bisect.bisect_right(offsets, offset - 1) + 1

    return line_of


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
            outcome = _doc008_resolve_path_target(
                root, doc_rel, base, target, path_part, line, slug_cache
            )
            if outcome is None:
                continue
            resolved, slugs, early_violation = outcome
            if early_violation is not None:
                violations.append(early_violation)
                continue
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


# frob:waive DUP001 reason="sibling DOC002/DOC008 violation builders in the same \
# module: same 'every failure mode is the same shape' Violation(...) builder, \
# independently-evolving rule ids"
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


__all__ = [
    "_doc_anchor_slugs",
    "_doclink_config",
    "_obligated_docs",
    "_linked_from_edges",
    "_line_index",
    "_docanchor_check_edge",
    "docanchor_gate",
    "doclink_gate",
]
