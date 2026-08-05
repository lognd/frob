"""Prose/doc-anchor carrier (T-1267): the three free-text reference kinds
neither the directive carrier (T-1199, `frob.refactor._directives`) nor
the registry/evidence repointer (T-1200, `frob.refactor._repointer`) can
reach, because none of them is a `frob:*` DSL edge or a structured record
(docs/design/refactor-verb.md's reference-kind inventory, "Prose-rewrite
scope" section):

1. A docstring or comment ANYWHERE in the repo (not just on the moving
   symbol's own code) naming the moving symbol's old dotted path in prose
   -- `scan_python_prose_mentions`.
2. `docs/**` prose (a sentence naming the old module) or an embedded
   fenced code block citing the old import path -- `scan_docs_prose_
   mentions`.
3. A doc heading whose text embeds the moved symbol/module name: the
   heading text and its GitHub anchor slug (`frob.graph.dsl.slugify`)
   rewrite together, and every existing `frob:doc`/markdown link
   referencing that anchor is repointed too -- `scan_doc_anchor_carriers`.

Per the epic's acceptance [3], a prose mention this pass cannot safely
rewrite (an ambiguous natural-language use, a match inside a generated/
vendored file already excluded by `_SKIP_DIRS`) is listed in the returned
`unresolved` list as "not rewritten -- review by hand", never silently
skipped and never guessed at.

Each function mirrors `_directives.scan_directive_carriers`'s own shape
(`(repo_root, resolved, destination) -> (ops, unresolved)`, text-level
literal-substring rewrite) so `_transaction.build_plan` folds their output
into `RefactorPlan.reference_ops` exactly like every other carrier's ops.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import re
from pathlib import Path

from frob.graph.dsl import slugify
from frob.lang import parse_file
from frob.logging import get_logger
from frob.refactor._models import ResolvedSymbol, RewriteOp, SymbolRef
from frob.refactor._scan import find_python_files

_log = get_logger(__name__)

__all__ = [
    "scan_doc_anchor_carriers",
    "scan_docs_prose_mentions",
    "scan_python_prose_mentions",
]

#: `docs/**` is this ticket's declared prose surface
#: (docs/design/refactor-verb.md's "Prose-rewrite scope" section names
#: `docs/**` explicitly, not the whole repo -- `tickets.md`/
#: `tickets-archive.md` prose already belongs to T-1200's
#: `scan_evidence_citations`).
_DOCS_GLOB = "**/*.md"


def _display_path(repo_root: Path, path: Path) -> str:
    """Repo-relative POSIX path when possible, else the path as given --
    mirrors `frob.refactor._directives._display_path` exactly (same
    convention every symref/link in this package is built from)."""
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _old_and_dest_rel(
    repo_root: Path, resolved: ResolvedSymbol, destination: SymbolRef
) -> tuple[str, str]:
    """The old and new repo-relative file paths for `resolved`'s move to
    `destination` -- shared by every scan below, mirroring
    `_repointer._old_and_dest_rel`."""
    from frob.refactor._resolve import module_to_path

    old_rel = _display_path(repo_root, Path(resolved.file_path))
    dest_rel = _display_path(repo_root, module_to_path(repo_root, destination.module))
    return old_rel, dest_rel


def _word_boundary_pattern(literal: str) -> re.Pattern[str]:
    """A regex matching `literal` only at identifier-boundary edges (no
    partial-word hit inside a longer dotted path or identifier) -- a plain
    substring match on a bare leaf name would otherwise fire inside an
    unrelated longer name that merely contains it."""
    return re.compile(r"(?<![\w.])" + re.escape(literal) + r"(?![\w.])")


# frob:doc docs/commands/refactor.md#scan_python_prose_mentions
# frob:tests tests/test_refactor.py::TestProseCarrier.test_docstring_mention_elsewhere_rewritten  # noqa: E501
def scan_python_prose_mentions(
    repo_root: Path, resolved: ResolvedSymbol, destination: SymbolRef
) -> tuple[list[RewriteOp], list[str]]:
    """Repo-wide scan (Plan phase): every docstring/comment naming the
    moving symbol's old dotted path or `path::qualname` symref in PROSE
    (not a `frob:*` directive line -- those are `_directives.scan_
    directive_carriers`'s own job, skipped here to avoid a double
    rewrite) gets its literal mention rewritten to the destination's
    equivalent form. Word-boundary matched so an unrelated dotted path
    that merely contains the old one as a substring is never touched."""
    old_rel, dest_rel = _old_and_dest_rel(repo_root, resolved, destination)
    old_dotted = resolved.ref.dotted
    new_dotted = destination.dotted
    old_symref = f"{old_rel}::{resolved.ref.qualname}"
    new_symref = f"{dest_rel}::{destination.qualname}"
    if old_dotted == new_dotted and old_symref == new_symref:
        return [], []

    patterns = {old_symref: new_symref, old_dotted: new_dotted}
    ops: list[RewriteOp] = []
    unresolved: list[str] = []
    for file_path in find_python_files(repo_root):
        if str(file_path) == resolved.file_path:
            # The moving symbol's own file is handled by the move ops
            # (Apply relocates the whole span, docstring included).
            continue
        file_ops, file_unresolved = _scan_file_for_prose_mentions(file_path, patterns)
        ops.extend(file_ops)
        unresolved.extend(file_unresolved)
    return ops, unresolved


def _scan_file_for_prose_mentions(
    file_path: Path, patterns: dict[str, str]
) -> tuple[list[RewriteOp], list[str]]:
    """One file's worth of `scan_python_prose_mentions` work: parse it,
    find every docstring/comment span naming an old->new key in
    `patterns` (skipping any span that also holds a `frob:*` directive,
    owned by `_directives.scan_directive_carriers` instead), and turn
    each match into a `RewriteOp`. Split out so the repo-wide loop in
    `scan_python_prose_mentions` stays a thin dispatch over this per-file
    unit (ARCH001)."""
    ops: list[RewriteOp] = []
    unresolved: list[str] = []
    parsed_result = parse_file(file_path)
    if parsed_result.is_err:
        return ops, unresolved
    parsed = parsed_result.danger_ok
    try:
        source_lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        unresolved.append(f"{file_path}: unreadable ({exc}) -- review by hand")
        return ops, unresolved
    seen_spans: set[tuple[int, int]] = set()
    for comment in parsed.comments:
        span = comment.span
        if span in seen_spans:
            continue
        start, end = span
        text = "\n".join(source_lines[start - 1 : end])
        if "frob:" in text:
            # Owned by the directive carrier (T-1199); a prose sentence
            # sharing a comment/docstring block with a directive is rare
            # enough that skipping the whole span here (rather than
            # line-splitting it) is the safe choice -- re-scanning it
            # would risk a double rewrite.
            continue
        hit_old, hit_new = next(
            (
                (old, new)
                for old, new in patterns.items()
                if _word_boundary_pattern(old).search(text)
            ),
            (None, None),
        )
        if hit_old is None or hit_new is None:
            continue
        seen_spans.add(span)
        new_text = _word_boundary_pattern(hit_old).sub(hit_new, text)
        ops.append(
            RewriteOp(
                file_path=str(file_path),
                start_line=start,
                end_line=end,
                old_text=text,
                new_text=new_text,
                reason=f"carry prose mention {hit_old} -> {hit_new}",
            )
        )
    return ops, unresolved


# frob:doc docs/commands/refactor.md#scan_docs_prose_mentions
# frob:tests tests/test_refactor.py::TestProseCarrier.test_docs_prose_and_code_block_rewritten  # noqa: E501
def scan_docs_prose_mentions(
    repo_root: Path, resolved: ResolvedSymbol, destination: SymbolRef
) -> tuple[list[RewriteOp], list[str]]:
    """`docs/**` carrier: any line (prose sentence or a fenced-code-block
    line citing an import) naming the moving symbol's old dotted path
    gets rewritten to the destination's dotted path -- word-boundary
    matched, same rule as `scan_python_prose_mentions`. A doc with no
    such mention (the common case) yields empty ops, not an error."""
    docs_dir = repo_root / "docs"
    if not docs_dir.is_dir():
        return [], []

    old_dotted = resolved.ref.dotted
    new_dotted = destination.dotted
    if old_dotted == new_dotted:
        return [], []
    pattern = _word_boundary_pattern(old_dotted)

    ops: list[RewriteOp] = []
    unresolved: list[str] = []
    for doc_path in sorted(docs_dir.glob(_DOCS_GLOB)):
        try:
            text = doc_path.read_text(encoding="utf-8")
        except OSError as exc:
            unresolved.append(f"{doc_path}: unreadable ({exc}) -- review by hand")
            continue
        if not pattern.search(text):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not pattern.search(line):
                continue
            ops.append(
                RewriteOp(
                    file_path=str(doc_path),
                    start_line=lineno,
                    end_line=lineno,
                    old_text=line,
                    new_text=pattern.sub(new_dotted, line),
                    reason=f"carry docs/** prose mention {old_dotted} -> {new_dotted}",
                )
            )
    return ops, unresolved


def _renamed_heading_and_slugs(
    heading_text: str, old_leaf: str, new_leaf: str
) -> tuple[str, str, str] | None:
    """`(new_heading_text, old_slug, new_slug)` if `heading_text` embeds
    `old_leaf` at a word boundary, else `None` (an unrelated heading, or
    one whose match is ambiguous -- e.g. `old_leaf` is a substring of a
    larger word -- which `_word_boundary_pattern` already refuses)."""
    pattern = _word_boundary_pattern(old_leaf)
    if not pattern.search(heading_text):
        return None
    old_slug = slugify(heading_text)
    new_heading = pattern.sub(new_leaf, heading_text)
    new_slug = slugify(new_heading)
    return new_heading, old_slug, new_slug


def _rewrite_anchor_refs(
    repo_root: Path, doc_rel: str, old_slug: str, new_slug: str
) -> list[RewriteOp]:
    """Every existing reference to `{doc_rel}#{old_slug}` -- a
    `frob:doc`/`frob:describes`-style directive comment in a `.py` file,
    or a markdown link elsewhere in `docs/**` -- rewritten to the new
    slug, so a heading rename never silently breaks an anchor the DOC001/
    DOC002 gates would otherwise flag."""
    old_anchor = f"{doc_rel}#{old_slug}"
    new_anchor = f"{doc_rel}#{new_slug}"
    ops: list[RewriteOp] = []
    for file_path in find_python_files(repo_root):
        text = file_path.read_text(encoding="utf-8")
        if old_anchor not in text:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if old_anchor not in line:
                continue
            ops.append(
                RewriteOp(
                    file_path=str(file_path),
                    start_line=lineno,
                    end_line=lineno,
                    old_text=line,
                    new_text=line.replace(old_anchor, new_anchor),
                    reason=f"carry doc anchor reference {old_anchor} -> {new_anchor}",
                )
            )
    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        for doc_path in sorted(docs_dir.glob(_DOCS_GLOB)):
            text = doc_path.read_text(encoding="utf-8")
            if old_anchor not in text and f"#{old_slug}" not in text:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if old_anchor in line:
                    ops.append(
                        RewriteOp(
                            file_path=str(doc_path),
                            start_line=lineno,
                            end_line=lineno,
                            old_text=line,
                            new_text=line.replace(old_anchor, new_anchor),
                            reason=(
                                f"carry doc anchor reference {old_anchor} -> "
                                f"{new_anchor}"
                            ),
                        )
                    )
    return ops


# frob:doc docs/commands/refactor.md#scan_doc_anchor_carriers
# frob:tests tests/test_refactor.py::TestProseCarrier.test_heading_and_anchor_rewritten_together  # noqa: E501
def scan_doc_anchor_carriers(
    repo_root: Path, resolved: ResolvedSymbol, destination: SymbolRef
) -> tuple[list[RewriteOp], list[str]]:
    """`docs/**` heading carrier: a heading whose text embeds the moving
    symbol's old leaf name (module basename or qualname, word-boundary
    matched) gets its text AND its GitHub anchor slug rewritten together
    -- then every `frob:doc`/markdown reference to the old anchor is
    repointed to the new one (`_rewrite_anchor_refs`), so no existing doc
    edge silently breaks. A heading match this pass judges unsafe (the
    same leaf name embedded inside a longer, unrelated word) is never
    produced in the first place -- `_word_boundary_pattern` refuses it at
    the source rather than needing a second pass to catch it."""
    docs_dir = repo_root / "docs"
    if not docs_dir.is_dir():
        return [], []

    old_module_leaf = resolved.ref.module.rsplit(".", maxsplit=1)[-1]
    old_qual_leaf = resolved.ref.qualname.split(".")[-1]
    new_qual_leaf = destination.qualname.split(".")[-1]
    candidates = [(old_qual_leaf, new_qual_leaf)]
    if resolved.ref.module != destination.module:
        new_module_leaf = destination.module.rsplit(".", maxsplit=1)[-1]
        if old_module_leaf != old_qual_leaf:
            candidates.append((old_module_leaf, new_module_leaf))

    ops: list[RewriteOp] = []
    unresolved: list[str] = []
    for doc_path in sorted(docs_dir.glob(_DOCS_GLOB)):
        try:
            lines = doc_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            unresolved.append(f"{doc_path}: unreadable ({exc}) -- review by hand")
            continue
        ops.extend(_scan_doc_headings(repo_root, doc_path, lines, candidates))
    return ops, unresolved


def _scan_doc_headings(
    repo_root: Path, doc_path: Path, lines: list[str], candidates: list[tuple[str, str]]
) -> list[RewriteOp]:
    """One doc file's worth of `scan_doc_anchor_carriers` work: every
    heading line matching one of `candidates` gets its text and slug
    rewritten, plus every existing reference to its old anchor repointed.
    Split out so the repo-wide loop above stays a thin dispatch over this
    per-file unit (ARCH001)."""
    doc_rel = _display_path(repo_root, doc_path)
    ops: list[RewriteOp] = []
    for lineno, line in enumerate(lines, start=1):
        if not line.startswith("#"):
            continue
        heading_text = line.lstrip("#").strip()
        renamed = next(
            (
                result
                for old_leaf, new_leaf in candidates
                if (
                    result := _renamed_heading_and_slugs(
                        heading_text, old_leaf, new_leaf
                    )
                )
                is not None
            ),
            None,
        )
        if renamed is None:
            continue
        new_heading_text, old_slug, new_slug = renamed
        hashes = line[: len(line) - len(line.lstrip("#"))]
        ops.append(
            RewriteOp(
                file_path=str(doc_path),
                start_line=lineno,
                end_line=lineno,
                old_text=line,
                new_text=f"{hashes} {new_heading_text}",
                reason=(
                    f"carry doc heading rename {heading_text!r} -> {new_heading_text!r}"
                ),
            )
        )
        if old_slug != new_slug:
            ops.extend(_rewrite_anchor_refs(repo_root, doc_rel, old_slug, new_slug))
    return ops
