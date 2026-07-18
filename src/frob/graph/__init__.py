"""The obligation graph: symbols, comment-DSL edges, and doc anchors
(docs/modules/graph.md).

`frob.graph` is a persistent registry of every symbol's identity and
digests, plus typed edges declared in `frob:` comments and markdown
`frob:describes` anchors, so any change to code, docs, or contracts is
detectable statically -- a type checker for obligations. Built entirely on
`frob.lang`'s uniform `ParsedFile` contract; this package never inspects a
tree-sitter node directly.

`build_graph` is incremental: a per-file sha256 content hash is stored in
the sqlite cache (`frob.graph.cache`), and a file whose hash is unchanged
loads its symbols/edges back from the cache instead of being re-parsed.

Source-file discovery filters through `frob.lang.supported_extensions()`
(T-0129) -- the canonical extension registry -- rather than a hand-copied
local table, so every grammar `frob.lang` gains (including `.strata`)
reaches the graph automatically.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from pathlib import Path

from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob import excludes as _excludes
from frob.graph import cache as _cache
from frob.graph._models import (
    BuildStats,
    DanglingEdge,
    Digests,
    DriftReport,
    Edge,
    EdgeKind,
    GraphSnapshot,
    LockEntry,
    LockFile,
    MalformedDirective,
    StaleItem,
    SymbolId,
    SymbolRecord,
)
from frob.graph.digest import compute_digests
from frob.graph.dsl import dedupe_slug, markdown_anchors, parse_directives, slugify
from frob.lang import LangError, ParsedFile, parse_file, supported_extensions
from frob.logging import get_logger

_log = get_logger(__name__)

_EXCLUDED_DIRS = frozenset(
    {".git", ".venv", "node_modules", "target", "build", "dist", "__pycache__", ".frob"}
)


# frob:doc docs/modules/graph.md#error-types
class GraphError(ErrorSet):
    """Failure values graph read paths can return -- never a bare exception."""

    CacheCorrupt = "Cache file unreadable; delete .frob/cache.db to rebuild"
    CacheStale = "Cache does not match working tree; run build_graph"
    UnknownSymbol = "Symbol reference does not resolve"
    AmbiguousSymbol = "Reference matches more than one symbol"


BuildError = GraphError | LangError


def _content_hash(path: Path) -> str | None:
    """Sha256 hex of `path`'s bytes, or `None` if it cannot be read."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        _log.warning("could not read %s for hashing: %s", path, exc)
        return None


def _display_path(path: Path, root: Path) -> str:
    """Repo-root-relative POSIX path for `path`."""
    return path.relative_to(root).as_posix()


# The [graph] exclude reader and matcher live in frob.excludes (the one
# copy shared with the dup/arch/cycle scanners -- T-0026); these are thin
# aliases so the graph's internal call sites keep their names.
_load_exclude_globs = _excludes.load_exclude_globs
_is_excluded = _excludes.is_excluded


def _walk_source_files(root: Path, exclude_globs: tuple[str, ...] = ()) -> list[Path]:
    """Every source file under `root` with a recognized extension, exclusions pruned."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if Path(name).suffix.lower() not in supported_extensions():
                continue
            if exclude_globs and _is_excluded(_display_path(path, root), exclude_globs):
                continue
            found.append(path)
    return found


def _walk_doc_files(root: Path, exclude_globs: tuple[str, ...] = ()) -> list[Path]:
    """Every `docs/**/*.md` file under `root`."""
    docs_dir = root / "docs"
    if not docs_dir.is_dir():
        return []
    return sorted(
        path
        for path in docs_dir.rglob("*.md")
        if not (
            exclude_globs and _is_excluded(_display_path(path, root), exclude_globs)
        )
    )


def _symbol_record(rel_path: str, symbol) -> SymbolRecord:  # noqa: ANN001
    """A `SymbolRecord` for one `RawSymbol`, digests computed fresh."""
    return SymbolRecord(
        id=SymbolId(path=rel_path, qualname=symbol.qualname),
        kind=symbol.kind,
        public=symbol.public,
        digests=compute_digests(symbol),
        span=symbol.span,
    )


def _dedupe_symbols(rel_path: str, parsed: ParsedFile) -> tuple[SymbolRecord, ...]:
    """Symbol records for `parsed`, last-def-wins on duplicate symrefs.

    @typing.overload stubs and conditional redefinitions legally repeat a
    qualname in one file, and Python's own semantics are that the final def
    is the live one (T-0024; the cache's symref PRIMARY KEY made duplicates
    a hard crash before).
    """
    by_ref: dict[str, SymbolRecord] = {}
    for sym in parsed.symbols:
        record = _symbol_record(rel_path, sym)
        if record.symref in by_ref:
            _log.debug(
                "duplicate symref %s (overload/redef): last def wins", record.symref
            )
        by_ref[record.symref] = record
    return tuple(by_ref.values())


# frob:ticket T-0133
def _process_source_file(
    conn, root: Path, path: Path, on_disk_hash: str
) -> tuple[
    bool, tuple[SymbolRecord, ...], tuple[Edge, ...], tuple[MalformedDirective, ...]
]:
    """Parse (or load) one source file: `(was_parsed, symbols, edges, malformed)`."""
    rel_path = _display_path(path, root)
    cached_hash = _cache.get_file_hash(conn, rel_path)
    if cached_hash == on_disk_hash:
        _log.debug("cache hit: %s", rel_path)
        symbols, edges, malformed = _cache.load_file_data(conn, rel_path)
        return False, symbols, edges, malformed

    parsed_result = parse_file(path)
    if parsed_result.is_err:
        err = parsed_result.danger_err
        if err == LangError.NativeParserUnavailable:
            # Expected degrade path (T-0133): a standalone tool install has
            # no strata-core native extension, so every .strata file skips
            # here every build -- debug, not warning, or a repo with any
            # .strata files would spam a warning line per file per run.
            _log.debug("skipping %s: %s", rel_path, err)
        else:
            _log.warning("skipping %s: %s", rel_path, err)
        return True, (), (), ()
    parsed: ParsedFile = parsed_result.danger_ok
    if parsed.path != rel_path:
        # frob.lang renders paths cwd-relative (or absolute outside cwd); graph's
        # contract is always repo-root-relative, so the path is corrected here.
        parsed = parsed.model_copy(update={"path": rel_path})
    symbols = _dedupe_symbols(rel_path, parsed)
    edges, malformed = parse_directives(parsed)
    _cache.store_file_data(
        conn,
        file_path=rel_path,
        content_hash=on_disk_hash,
        symbols=symbols,
        edges=edges,
        malformed=malformed,
    )
    return True, symbols, edges, malformed


def _process_doc_file(conn, root: Path, path: Path, on_disk_hash: str) -> bool:
    """Parse (or cache-skip) one markdown file for `frob:describes` anchors."""
    rel_path = _display_path(path, root)
    cached_hash = _cache.get_file_hash(conn, rel_path)
    if cached_hash == on_disk_hash:
        _log.debug("cache hit: %s", rel_path)
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("skipping %s: %s", rel_path, exc)
        return True
    edges = markdown_anchors(rel_path, text)
    _cache.store_file_data(
        conn,
        file_path=rel_path,
        content_hash=on_disk_hash,
        symbols=(),
        edges=edges,
        malformed=(),
    )
    return True


def _ingest_source_files(
    conn, root: Path, source_files: Sequence[Path]
) -> tuple[set[str], int, int]:
    """Process every source file; return `(seen_paths, parsed_count, cache_hits)`."""
    seen_paths: set[str] = set()
    parsed_count = 0
    cache_hits = 0
    for path in source_files:
        on_disk = _content_hash(path)
        if on_disk is None:
            continue
        seen_paths.add(_display_path(path, root))
        was_parsed, *_ = _process_source_file(conn, root, path, on_disk)
        if was_parsed:
            parsed_count += 1
        else:
            cache_hits += 1
    return seen_paths, parsed_count, cache_hits


def _ingest_doc_files(
    conn, root: Path, doc_files: Sequence[Path]
) -> tuple[set[str], int, int]:
    """Process every markdown file; return `(seen_paths, parsed_count, cache_hits)`."""
    seen_paths: set[str] = set()
    parsed_count = 0
    cache_hits = 0
    for path in doc_files:
        on_disk = _content_hash(path)
        if on_disk is None:
            continue
        seen_paths.add(_display_path(path, root))
        if _process_doc_file(conn, root, path, on_disk):
            parsed_count += 1
        else:
            cache_hits += 1
    return seen_paths, parsed_count, cache_hits


def _prune_stale_cache(conn, seen_paths: set[str]) -> None:
    """Delete cache rows for files that no longer exist on disk."""
    stale_cached = {row[0] for row in conn.execute("SELECT path FROM files")}
    for stale_path in stale_cached - seen_paths:
        _log.debug("removing deleted file from cache: %s", stale_path)
        conn.execute("DELETE FROM files WHERE path = ?", (stale_path,))
        conn.execute("DELETE FROM symbols WHERE path = ?", (stale_path,))
        conn.execute("DELETE FROM edges WHERE file = ?", (stale_path,))
        conn.execute("DELETE FROM malformed WHERE file = ?", (stale_path,))


# frob:doc docs/modules/graph.md#public-api
def build_graph(root: Path, cache: Path) -> Result[GraphSnapshot, BuildError]:
    """Incrementally (re)build the obligation graph for `root` into `cache`."""
    root = root.resolve()
    _log.info("build_graph: root=%s cache=%s", root, cache)
    conn = _cache.connect(cache)
    try:
        exclude_globs = _load_exclude_globs(root)
        source_files = _walk_source_files(root, exclude_globs)
        doc_files = _walk_doc_files(root, exclude_globs)

        src_seen, src_parsed, src_hits = _ingest_source_files(conn, root, source_files)
        doc_seen, doc_parsed, doc_hits = _ingest_doc_files(conn, root, doc_files)
        seen_paths = src_seen | doc_seen
        parsed_count = src_parsed + doc_parsed
        cache_hits = src_hits + doc_hits

        _prune_stale_cache(conn, seen_paths)
        snapshot = _finalize_build(conn, root, parsed_count, cache_hits)
        return Ok(snapshot)
    finally:
        conn.close()


def _finalize_build(
    conn, root: Path, parsed_count: int, cache_hits: int
) -> GraphSnapshot:
    """Persist the root, commit, and load the final snapshot with build stats."""
    _cache.set_root(conn, root.as_posix())
    conn.commit()
    stats = BuildStats(parsed=parsed_count, cache_hits=cache_hits)
    snapshot = _cache.load_all(conn, stats=stats)
    _log.info(
        "build_graph: done, parsed=%d hits=%d symbols=%d edges=%d malformed=%d",
        parsed_count,
        cache_hits,
        len(snapshot.symbols),
        len(snapshot.edges),
        len(snapshot.malformed),
    )
    return snapshot


# frob:doc docs/modules/graph.md#public-api
# frob:waive TEST005 reason="load_graph 87.0% branch cover, debt T-0160"
def load_graph(cache: Path) -> Result[GraphSnapshot, GraphError]:
    """Cache-only read: `Err(CacheStale)` if any on-disk hash moved, `Err(CacheCorrupt)`
    if the cache is unreadable or has never been built."""
    if not cache.exists():
        _log.warning("load_graph: no cache at %s", cache)
        return Err(GraphError.CacheCorrupt)
    try:
        conn = _cache.connect(cache)
    except Exception as exc:  # sqlite3.DatabaseError and friends
        _log.error("load_graph: cache unreadable at %s: %s", cache, exc)
        return Err(GraphError.CacheCorrupt)
    try:
        root_str = _cache.get_root(conn)
        if root_str is None:
            _log.warning("load_graph: cache at %s has never been built", cache)
            return Err(GraphError.CacheCorrupt)
        root = Path(root_str)
        for path, stored_hash in conn.execute("SELECT path, content_hash FROM files"):
            current = _content_hash(root / path)
            if current != stored_hash:
                _log.warning("load_graph: %s drifted from cache", path)
                return Err(GraphError.CacheStale)
        snapshot = _cache.load_all(conn)
        _log.info(
            "load_graph: loaded %d symbols, %d edges",
            len(snapshot.symbols),
            len(snapshot.edges),
        )
        return Ok(snapshot)
    finally:
        conn.close()


# frob:doc docs/modules/graph.md#public-api
def resolve(snapshot: GraphSnapshot, ref: str) -> Result[SymbolRecord, GraphError]:
    """Resolve `ref`: exact `path::qualname`, else a unique qualname/suffix match."""
    exact = snapshot.symbols.get(ref)
    if exact is not None:
        return Ok(exact)

    suffix = f".{ref}"
    matches = [
        record
        for record in snapshot.symbols.values()
        if record.id.qualname == ref or record.id.qualname.endswith(suffix)
    ]
    if len(matches) == 1:
        return Ok(matches[0])
    if len(matches) > 1:
        _log.warning("resolve(%r): ambiguous, %d matches", ref, len(matches))
        return Err(GraphError.AmbiguousSymbol)
    _log.debug("resolve(%r): no match", ref)
    return Err(GraphError.UnknownSymbol)


# frob:doc docs/modules/graph.md#public-api
def edges_from(snapshot: GraphSnapshot, ref: str) -> tuple[Edge, ...]:
    """All edges whose `src` is exactly `ref`."""
    return tuple(edge for edge in snapshot.edges if edge.src == ref)


# frob:doc docs/modules/graph.md#public-api
def edges_to(snapshot: GraphSnapshot, target: str) -> tuple[Edge, ...]:
    """All edges whose `target` is exactly `target`."""
    return tuple(edge for edge in snapshot.edges if edge.target == target)


__all__ = [
    "BuildError",
    "BuildStats",
    "Digests",
    "DanglingEdge",
    "DriftReport",
    "Edge",
    "EdgeKind",
    "GraphError",
    "GraphSnapshot",
    "LockEntry",
    "LockFile",
    "MalformedDirective",
    "StaleItem",
    "SymbolId",
    "SymbolRecord",
    "build_graph",
    "dedupe_slug",
    "edges_from",
    "edges_to",
    "load_graph",
    "resolve",
    "slugify",
]
