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
# src/frob/gates/_doclink_docanchor.py's exclusivity-vocabulary hits are \
# source-level design-rationale prose (docstrings and comments describing \
# already-implemented internal behavior, verifiable by reading the code they annotate) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim -- module prose split verbatim \
# from the pre-T-1170 gates/__init__.py monolith"

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


# frob:waive EXHAUST001 reason="T-1056: leaked Unknown traces to \
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
    violations = tuple(_doc001_orphan(orphan, link_hint) for orphan in orphans)
    _log.info("doclink: %d obligated, %d orphaned", len(obligated), len(violations))
    return violations


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


_ANCHOR_ID_RE = re.compile(r'<a\s+id="([^"]+)"')
_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


# frob:waive EXHAUST001 reason="T-1056: leaked Unknown traces to slugify/dedupe_slug \
# (imported helpers) and _MD_HEADING_RE/_ANCHOR_ID_RE.finditer over text already \
# caught via read_text()'s own OSError handling; the resolver cannot follow through \
# the cross-module helper import, but both are pure str/regex transforms with no \
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
]
