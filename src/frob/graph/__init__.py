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
# frob:waive INV006 preset="split-carried-prose"
# frob:waive ARCH102 reason="19 of 22 exports form one connected build-graph pipeline \
# cluster (load_graph's own ingest/parse/cache-prune chain); the remaining 3 \
# (edges_from, edges_to, resolve) are small read-only query accessors over the exact \
# GraphSnapshot the pipeline produces, coupled to it by the shared data model rather \
# than by direct calls -- splitting query accessors away from the builder of the \
# structure they query would separate one cohesive graph API into pieces with no \
# independent reason to exist apart"

from __future__ import annotations

import hashlib
import os
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob import excludes as _excludes
from frob.check._memo import memoize_per_run
from frob.graph import cache as _cache
from frob.graph._generated import is_generated_source
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
    ParseFailure,
    StaleItem,
    SymbolId,
    SymbolRecord,
)
from frob.graph.affects import (
    AffectedSet,
    ScopeClosureGap,
    affects,
    scope_doc_code_gaps,
    scope_test_gaps,
)
from frob.graph.callgraph import (
    CallGraph,
    OrderedCallGraph,
    PrivateHelperGap,
    build_call_graph,
    build_ordered_call_graph,
    build_reference_graph,
    closure,
    scope_private_helper_gaps,
)
from frob.graph.digest import compute_digests
from frob.graph.dsl import (
    dedupe_slug,
    fold_comment_runs,
    markdown_anchors,
    parse_directives,
    slugify,
)
from frob.graph.summary import (
    FunctionSummary,
    SCCTimeout,
    SummaryResult,
    compute_protocol_summaries,
)
from frob.lang import LangError, ParsedFile, parse_file, supported_extensions
from frob.logging import get_logger
from frob.process._lock import derived_state_write_lock

_log = get_logger(__name__)


# frob:doc docs/modules/graph.md#error-types
class GraphError(ErrorSet):
    """Failure values graph read paths can return -- never a bare exception."""

    CacheCorrupt = "Cache file unreadable; delete .frob/cache.db to rebuild"
    CacheStale = "Cache does not match working tree; run build_graph"
    CacheLocked = "Cache lock held by another process; retry the command"
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


# frob:ticket T-0245
def _stat_key(path: Path) -> tuple[int, int] | None:
    """`(mtime_ns, size)` for `path` via a single `os.stat`, or `None` unreadable.

    One syscall vs. the open+read+close a content hash needs (T-0245); on a
    latency-heavy mount (WSL9p `/mnt/c`, network shares) this is the
    difference between a per-file stat and a per-file full read, and it is
    the cheap check `build_graph`/`load_graph` try first.
    """
    try:
        st = path.stat()
        return st.st_mtime_ns, st.st_size
    except OSError as exc:
        _log.warning("could not stat %s: %s", path, exc)
        return None


def _display_path(path: Path, root: Path) -> str:
    """Repo-root-relative POSIX path for `path`."""
    return path.relative_to(root).as_posix()


# The [graph] exclude reader and matcher live in frob.excludes (the one
# copy shared with the dup/arch/cycle scanners -- T-0026); these are thin
# aliases so the graph's internal call sites keep their names.
_load_exclude_globs = _excludes.load_exclude_globs
_is_excluded = _excludes.is_excluded
# T-0239: directory-pruning helper is intentionally private in frob.excludes
# (leading underscore keeps it off the REL001 public-API surface -- it is an
# internal walker detail, not something outside consumers should call).
_should_prune_dir = _excludes._should_prune_dir  # noqa: SLF001


# frob:ticket T-0239
# frob:ticket T-0245
# frob:ticket T-0544
# frob:tests tests/test_graph.py::TestExclude.test_nested_git_worktree_pruned_without_config  # noqa: E501
# frob:tests tests/test_graph.py::TestExclude.test_walk_source_files_prunes_before_descent  # noqa: E501
# frob:tests tests/test_graph.py::TestExclude.test_walk_repo_files_classifies_top_level_readme_as_doc  # noqa: E501
def _walk_repo_files(
    root: Path, exclude_globs: tuple[str, ...] = ()
) -> tuple[list[Path], list[Path]]:
    """`(source_files, doc_files)` in one `os.walk` pass over `root`.

    Two things folded into one walk: excluded directories -- the builtin
    skip set, `[graph] exclude` globs, and nested git worktree checkouts --
    are pruned from `dirnames` BEFORE `os.walk` descends into them (T-0239:
    filtering files after the walk still pays the full traversal/stat cost
    of every excluded subtree). And source files and `docs/**/*.md` files
    are classified from the SAME walk (T-0245) instead of a full
    `os.walk(root)` for source files plus a separate walk of `docs/` for
    doc files -- on a mount filesystem each `os.scandir` per directory is a
    syscall, and `docs/` was being walked twice.
    """
    docs_dir = root / "docs"
    source_files: list[Path] = []
    doc_files: list[Path] = []
    exts = supported_extensions()
    # frob:waive WALK001 reason="already prunes via frob.excludes._should_prune_dir before descending (T-0239); this IS the underlying primitive walk_pruned wraps, folded with dual source/doc classification in one pass for perf, not a naive raw walk"  # noqa: E501
    for dirpath, dirnames, filenames in os.walk(root):
        dir_path = Path(dirpath)
        dirnames[:] = [
            d
            for d in dirnames
            if not _should_prune_dir(dir_path / d, root, exclude_globs)
        ]
        under_docs = dir_path == docs_dir or docs_dir in dir_path.parents
        # T-0544: a `frob:describes` anchor placed in README.md (or any other
        # top-level *.md note) used to be invisible to the design graph --
        # this walker only ever classified files under docs/ as doc files,
        # so its DESCRIBES edge (and the facet it selects for DRIFT001)
        # never existed even though gates.doclink's own root set
        # (docs/index.md, README.md) already treats README.md as a doc
        # entry point. Top-level *.md files are cheap to fold in here (one
        # directory, no recursive cost) rather than duplicating gates'
        # frob.toml-driven include/exclude glob resolution into this leaf
        # walker.
        at_repo_root = dir_path == root
        for name in filenames:
            path = dir_path / name
            suffix = Path(name).suffix.lower()
            is_source = suffix in exts
            # The ticket ledgers are top-level *.md but HISTORY, not docs:
            # archived Done reports quote frob:describes lines verbatim, and
            # classifying the ledgers as docs resurrects those historical
            # edges as live DRIFT obligations (incident: a dangling
            # describes edge under the archive's 381st done-report heading
            # appeared the moment T-0544 landed).
            is_ledger = at_repo_root and name in (
                "tickets.md",
                "tickets-archive.md",
            )
            is_doc = (under_docs or at_repo_root) and suffix == ".md" and not is_ledger
            if not is_source and not is_doc:
                continue
            if exclude_globs and _is_excluded(_display_path(path, root), exclude_globs):
                continue
            if is_source:
                source_files.append(path)
            if is_doc:
                doc_files.append(path)
    return source_files, sorted(doc_files)


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


# frob:ticket T-0433
# frob:ticket T-0558
# frob:ticket T-0561
# frob:tests tests/test_graph.py::TestBuildIncremental.test_stored_hash_matches_bytes_actually_parsed  # noqa: E501
# frob:tests tests/test_graph.py::TestParseFailures.test_parse_error_is_recorded_as_parse_failure  # noqa: E501
def _parse_source_file_fresh(
    conn, rel_path: str, path: Path, stat_key: tuple[int, int]
) -> tuple[
    bool,
    tuple[SymbolRecord, ...],
    tuple[Edge, ...],
    tuple[MalformedDirective, ...],
    ParseFailure | None,
]:
    """Parse one uncached source file and store the result:
    `(True, symbols, edges, malformed, parse_failure)`.

    T-0433 (G7 fix): the stored `content_hash` is `parsed.content_hash` --
    the hash `frob.lang` computed from the EXACT bytes it read and parsed
    -- never a hash read separately by the caller beforehand. `_content_hash`
    and `parse_file`/`_parse_strata_file` used to each do their own
    `read_bytes()`, so a write landing between the two reads stored the
    SECOND read's symbols under the FIRST read's hash: a cached row whose
    hash no longer described its own symbols. Hashing only the bytes that
    were actually parsed closes that window -- there is exactly one read
    per store, not two.

    T-0558: a parse/IO failure (any `LangError` other than the expected
    `NativeParserUnavailable` degrade) used to come back as
    `(True, (), (), ())` indistinguishable from a genuinely empty file --
    every public symbol and every `frob:doc`/`frob:invariant`/`frob:tests`
    edge in the file silently vanished, and COV001/DRIFT/INV all passed
    vacuously for it. Now that case also returns a non-`None`
    `ParseFailure`, which `gates._parse_failures.parse_failure_gate`
    (PARSE001) surfaces as an ERROR-severity violation instead of a
    swallowed warning.
    """
    parsed_result = parse_file(path)
    if parsed_result.is_err:
        err = parsed_result.danger_err
        if err == LangError.NativeParserUnavailable:
            # Expected degrade path (T-0133): a standalone tool install has
            # no strata-core native extension, so every .strata file skips
            # here every build -- debug, not warning, or a repo with any
            # .strata files would spam a warning line per file per run.
            # Not a ParseFailure: this is a known, environment-level
            # degrade, not a file frob.lang genuinely could not parse.
            _log.debug("skipping %s: %s", rel_path, err)
            return True, (), (), (), None
        _log.warning("skipping %s: %s", rel_path, err)
        return True, (), (), (), ParseFailure(file=rel_path, reason=str(err))
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
        content_hash=parsed.content_hash,
        mtime_ns=stat_key[0],
        size=stat_key[1],
        symbols=symbols,
        edges=edges,
        malformed=malformed,
    )
    return True, symbols, edges, malformed, None


# frob:ticket T-0133
# frob:ticket T-0245
# frob:ticket T-0558
# frob:ticket T-0561
def _process_source_file(
    conn, root: Path, path: Path, stat_key: tuple[int, int]
) -> tuple[
    bool,
    tuple[SymbolRecord, ...],
    tuple[Edge, ...],
    tuple[MalformedDirective, ...],
    ParseFailure | None,
]:
    """Parse (or load) one source file:
    `(was_parsed, symbols, edges, malformed, parse_failure)`.

    Stat-first (T-0245): if `stat_key` (mtime_ns, size) matches what was
    stored last build, trust it and load straight from cache -- no file read
    at all. Only when the stat pair has moved does this fall back to a full
    content hash, and even then a hash match (a `touch` with no edit) still
    skips the reparse, just refreshing the stored stat.

    T-0433 (G7): the `_content_hash` computed here only decides WHETHER to
    reparse (a cheap early-out); it is never what gets stored for an
    actually-reparsed file -- `_parse_source_file_fresh` stores the hash
    `frob.lang` computed from the bytes it itself read and parsed, closing
    the old TOCTOU window where a write between this decision-read and
    `parse_file`'s own read could store fresh symbols under a stale hash.

    T-0558: an unreadable file (`_content_hash` returns `None`) is also a
    parse/IO failure whose entire obligation set silently vanished before
    this fix -- it now returns a `ParseFailure` too, same as a genuine
    `frob.lang.parse_file` error.
    """
    rel_path = _display_path(path, root)
    meta = _cache.get_file_meta(conn, rel_path)
    if meta is not None:
        cached_hash, cached_mtime_ns, cached_size = meta
        if (cached_mtime_ns, cached_size) == stat_key:
            _log.debug("stat cache hit: %s", rel_path)
            symbols, edges, malformed = _cache.load_file_data(conn, rel_path)
            return False, symbols, edges, malformed, None
    else:
        cached_hash = None
    on_disk_hash = _content_hash(path)
    if on_disk_hash is None:
        return (
            True,
            (),
            (),
            (),
            ParseFailure(file=rel_path, reason="could not read file for hashing"),
        )
    if on_disk_hash == cached_hash:
        # mtime moved but content did not (e.g. a checkout/touch): refresh
        # the stat so the next build takes the fast path again, but skip
        # the reparse -- the stored symbols/edges/malformed are still correct.
        _log.debug("content unchanged despite stat move: %s", rel_path)
        _cache.touch_file_stat(conn, rel_path, mtime_ns=stat_key[0], size=stat_key[1])
        symbols, edges, malformed = _cache.load_file_data(conn, rel_path)
        return False, symbols, edges, malformed, None
    return _parse_source_file_fresh(conn, rel_path, path, stat_key)


# frob:ticket T-0245
def _process_doc_file(conn, root: Path, path: Path, stat_key: tuple[int, int]) -> bool:
    """Parse (or cache-skip) one markdown file for `frob:describes` anchors.

    Same stat-first fast path as `_process_source_file` (T-0245).
    """
    rel_path = _display_path(path, root)
    meta = _cache.get_file_meta(conn, rel_path)
    if meta is not None:
        cached_hash, cached_mtime_ns, cached_size = meta
        if (cached_mtime_ns, cached_size) == stat_key:
            _log.debug("stat cache hit: %s", rel_path)
            return False
    else:
        cached_hash = None
    on_disk_hash = _content_hash(path)
    if on_disk_hash is None:
        return True
    if on_disk_hash == cached_hash:
        _log.debug("content unchanged despite stat move: %s", rel_path)
        _cache.touch_file_stat(conn, rel_path, mtime_ns=stat_key[0], size=stat_key[1])
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        # frob:ticket T-0402
        # G2: UnicodeDecodeError subclasses ValueError, not OSError, so it
        # was never caught here -- one non-UTF-8 .md crashed the whole
        # build (and every command layered on `Result`, hard). Degrade the
        # same way an unreadable file already does: log loudly, skip the
        # file, keep the build alive.
        _log.warning("skipping %s: %s", rel_path, exc)
        return True
    edges = markdown_anchors(rel_path, text)
    _cache.store_file_data(
        conn,
        file_path=rel_path,
        content_hash=on_disk_hash,
        mtime_ns=stat_key[0],
        size=stat_key[1],
        symbols=(),
        edges=edges,
        malformed=(),
    )
    return True


# frob:ticket T-0558
# frob:ticket T-0561
def _ingest_source_files(
    conn, root: Path, source_files: Sequence[Path]
) -> tuple[set[str], int, int, tuple[ParseFailure, ...]]:
    """Process every source file; return
    `(seen_paths, parsed_count, cache_hits, parse_failures)`.

    T-0558: `parse_failures` collects every file this build could not
    parse/read at all (never cached -- see `_parse_source_file_fresh` and
    `_process_source_file` -- so a fixed file drops out on its next
    successful build)."""
    seen_paths: set[str] = set()
    parsed_count = 0
    cache_hits = 0
    parse_failures: list[ParseFailure] = []
    for path in source_files:
        stat_key = _stat_key(path)
        if stat_key is None:
            continue
        seen_paths.add(_display_path(path, root))
        was_parsed, _symbols, _edges, _malformed, failure = _process_source_file(
            conn, root, path, stat_key
        )
        if was_parsed:
            parsed_count += 1
        else:
            cache_hits += 1
        if failure is not None:
            parse_failures.append(failure)
    return seen_paths, parsed_count, cache_hits, tuple(parse_failures)


def _ingest_doc_files(
    conn, root: Path, doc_files: Sequence[Path]
) -> tuple[set[str], int, int]:
    """Process every markdown file; return `(seen_paths, parsed_count, cache_hits)`."""
    seen_paths: set[str] = set()
    parsed_count = 0
    cache_hits = 0
    for path in doc_files:
        stat_key = _stat_key(path)
        if stat_key is None:
            continue
        seen_paths.add(_display_path(path, root))
        if _process_doc_file(conn, root, path, stat_key):
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
# frob:doc docs/commands/check.md#run-scoped-memoization
# frob:tests tests/test_graph.py::TestLoadGraph.test_non_utf8_doc_file_is_skipped_not_crashed  # noqa: E501
# frob:tests tests/unit/test_memo.py::test_build_graph_second_call_is_memo_hit
# frob:tests tests/test_graph.py::TestBuildIncremental.test_stats_sum_source_and_doc_counts_not_difference  # noqa: E501
# frob:ticket T-0423
# frob:ticket T-0918
@memoize_per_run
def build_graph(root: Path, cache: Path) -> Result[GraphSnapshot, BuildError]:
    """Incrementally (re)build the obligation graph for `root` into `cache`.

    Memoized per `frob check` run (T-0423, `frob.check._memo.memoize_
    per_run`): a second call with the same `(root, cache)` in the same run
    is a cache hit, not a re-walk -- closes the "same heavy analysis reruns
    across stages" class the T-0418 arch double-run was one instance of.

    T-0918: the whole rebuild below is wrapped in `frob.process._lock.
    derived_state_write_lock`, which takes a real cross-process EXCLUSIVE
    `derived_state_lock` when called standalone but no-ops when this
    process already holds the lock in another thread (e.g. nested inside
    `frob check`'s SHARED hold) -- see that function's docstring for the
    full reentrancy contract and its accepted soundness trade-off.

    T-1423: `_cache.CacheLocked` (raised once `_cache._with_lock_retry`'s
    own retry budget is exhausted under sustained contention) is caught
    here and reported as `Err(GraphError.CacheLocked)`, never an unhandled
    exception reaching `main()`'s top-level handler.
    """
    root = root.resolve()
    _log.info("build_graph: root=%s cache=%s", root, cache)
    with derived_state_write_lock(root):
        try:
            conn = _cache.connect(cache)
        except _cache.CacheLocked as exc:
            _log.error("build_graph: cache lock never released: %s", exc)
            return Err(GraphError.CacheLocked)
        try:
            exclude_globs = _load_exclude_globs(root)
            source_files, doc_files = _walk_repo_files(root, exclude_globs)

            src_seen, src_parsed, src_hits, parse_failures = _ingest_source_files(
                conn, root, source_files
            )
            doc_seen, doc_parsed, doc_hits = _ingest_doc_files(conn, root, doc_files)
            seen_paths = src_seen | doc_seen
            parsed_count = src_parsed + doc_parsed
            cache_hits = src_hits + doc_hits

            _prune_stale_cache(conn, seen_paths)
            snapshot = _finalize_build(
                conn, root, parsed_count, cache_hits, parse_failures
            )
            return Ok(snapshot)
        except _cache.CacheLocked as exc:
            _log.error("build_graph: cache lock never released: %s", exc)
            return Err(GraphError.CacheLocked)
        finally:
            conn.close()


# frob:ticket T-0216
def _log_malformed_files(malformed: tuple[MalformedDirective, ...]) -> None:
    """WARN-log every malformed directive's file:line + parse error (T-0216):
    the aggregate `malformed=N` build-summary count alone gives no way to
    find which file to fix. Runs on every build, including all-cache-hit
    rebuilds, where the per-file warning in `dsl.parse_directives` never
    fires because cached malformed rows are loaded, not re-parsed."""
    for item in malformed:
        _log.warning(
            "malformed directive: %s:%d: %s", item.file, item.line, item.reason
        )


# frob:ticket T-0558
# frob:ticket T-0561
def _log_parse_failures(parse_failures: tuple[ParseFailure, ...]) -> None:
    """WARN-log every parse/IO failure's file + reason, same shape as
    `_log_malformed_files` (T-0216) -- the aggregate count alone gives no
    way to find which file to fix."""
    for item in parse_failures:
        _log.warning("parse failure: %s: %s", item.file, item.reason)


def _finalize_build(
    conn,
    root: Path,
    parsed_count: int,
    cache_hits: int,
    parse_failures: tuple[ParseFailure, ...] = (),
) -> GraphSnapshot:
    """Persist the root, commit, and load the final snapshot with build stats.

    T-0558: `parse_failures` is never persisted to the cache (a failed
    file is never `store_file_data`-d, so the next build simply retries
    it) -- it is folded into the returned snapshot here, live, for this
    build only.
    """
    _cache.set_root(conn, root.as_posix())
    conn.commit()
    stats = BuildStats(parsed=parsed_count, cache_hits=cache_hits)
    snapshot = _cache.load_all(conn, stats=stats)
    if parse_failures:
        snapshot = snapshot.model_copy(update={"parse_failures": parse_failures})
    _log_malformed_files(snapshot.malformed)
    _log_parse_failures(snapshot.parse_failures)
    _log.info(
        "build_graph: done, parsed=%d hits=%d symbols=%d edges=%d malformed=%d "
        "parse_failures=%d",
        parsed_count,
        cache_hits,
        len(snapshot.symbols),
        len(snapshot.edges),
        len(snapshot.malformed),
        len(snapshot.parse_failures),
    )
    return snapshot


# frob:ticket T-0361
# frob:ticket T-0245
def _first_stale_cached_file(conn: sqlite3.Connection, root: Path) -> str | None:
    """The first cached file path whose on-disk state no longer matches the
    cache, or `None` if every cached file still matches; split out of
    `load_graph`'s staleness-check loop (T-0361).

    Stat-first (T-0245): a matching `(mtime_ns, size)` trusts the cache with
    one `os.stat` per file; only a stat mismatch pays for a full content
    read to confirm the bytes actually moved (a `touch` alone should not
    force `CacheStale`). This is the hot path every gate invocation runs
    through, so it is where the mount-filesystem per-file cost (T-0245:
    0.5ms/stat under load) matters most.
    """
    for path, stored_hash, stored_mtime_ns, stored_size in conn.execute(
        "SELECT path, content_hash, mtime_ns, size FROM files"
    ):
        stat_key = _stat_key(root / path)
        if stat_key is not None and stat_key == (stored_mtime_ns, stored_size):
            continue
        current = _content_hash(root / path)
        if current != stored_hash:
            return path
    return None


# frob:ticket T-0402
def _first_added_file(
    conn: sqlite3.Connection, root: Path, exclude_globs: tuple[str, ...]
) -> str | None:
    """The first on-disk source/doc path with no `files` cache row, or
    `None` if every on-disk path is already cached (T-0402, G1).

    `_first_stale_cached_file` only iterates rows already IN the cache, so
    it can never see a file that has never been ingested at all -- a
    brand-new source or doc file made `load_graph` return `Ok` on a
    snapshot silently missing that file's symbols, edges, malformed
    directives, and doc obligations. This pays one extra `os.walk` (the
    same walk `build_graph` already pays) to catch additions, the one
    staleness shape `_first_stale_cached_file`'s hash-only loop cannot see.
    """
    cached = {row[0] for row in conn.execute("SELECT path FROM files")}
    source_files, doc_files = _walk_repo_files(root, exclude_globs)
    for path in source_files + doc_files:
        rel_path = _display_path(path, root)
        if rel_path not in cached:
            return rel_path
    return None


# frob:doc docs/modules/graph.md#public-api
# frob:ticket T-0232
# frob:tests tests/test_graph.py::TestLoadGraph.test_cache_stale_after_new_file_added  # noqa: E501
# frob:tests tests/test_graph.py::TestLoadGraph.test_cache_stale_after_new_doc_added  # noqa: E501
def load_graph(cache: Path) -> Result[GraphSnapshot, GraphError]:
    """Cache-only read: `Err(CacheStale)` if any on-disk hash moved, `Err(CacheCorrupt)`
    if the cache is unreadable, schema-mismatched, or has never been built.

    Opens `cache` via `connect_readonly` (T-0232), not `connect`: a pure
    read has no business taking sqlite's single writer slot, and doing so
    is what serialized concurrent `frob` invocations (agent loop, CI, a
    background `frob vet`) behind each other's cache writes even when
    neither side had anything to write. A cache this can't open read-only
    (missing, corrupt, or mid-rebuild) is exactly `CacheCorrupt` territory
    -- self-healing it is `build_graph`'s job, not a reader's.

    frob:ticket T-0799
    A read-only connection can never DDL its way out of schema drift the
    way `connect()`'s `_apply_schema_with_recovery` does -- a pre-migration
    cache.db (missing a table T-0245/T-0279 added, or missing a column like
    `mtime_ns`) surfaces as `sqlite3.OperationalError` ("no such table:
    symbols", "no such column: mtime_ns") from whatever query happens to
    touch the drifted shape first: `get_root`, the staleness probes, or
    `load_all`. Two such crashes escaped this function mid-land on
    2026-07-23 (one leaving a partial squash staged on main) because only
    `get_root`'s own query was guarded -- every query after it was not. The
    whole read body is wrapped in one `OperationalError` handler now: ANY
    schema-shape error anywhere in this function is `CacheCorrupt`, never a
    propagating exception -- `build_graph` (via `connect()`'s schema-version
    check) is what actually rebuilds it on the next write.
    """
    if not cache.exists():
        _log.warning("load_graph: no cache at %s", cache)
        return Err(GraphError.CacheCorrupt)
    try:
        conn = _cache.connect_readonly(cache)
    except _cache.CacheLocked as exc:
        # T-1423: contended, not corrupt -- do not conflate the two, or a
        # transient lock triggers a needless cache rebuild downstream.
        _log.error("load_graph: cache lock never released at %s: %s", cache, exc)
        return Err(GraphError.CacheLocked)
    except Exception as exc:  # sqlite3.DatabaseError and friends
        _log.error("load_graph: cache unreadable at %s: %s", cache, exc)
        return Err(GraphError.CacheCorrupt)
    try:
        return _load_graph_from_connection(conn, cache)
    finally:
        conn.close()


# frob:ticket T-0976
def _load_graph_from_connection(conn, cache: Path) -> Result[GraphSnapshot, GraphError]:  # noqa: ANN001
    """`load_graph`'s read body once a read-only connection is open: root/
    staleness/added-file checks, then `_cache.load_all` -- split out so
    `load_graph` itself only owns opening and closing `conn`. Any schema-
    shape `OperationalError`/`DatabaseError` here (T-0799) is `CacheCorrupt`,
    never a propagating exception."""
    try:
        root_str = _cache.get_root(conn)
        if root_str is None:
            _log.warning("load_graph: cache at %s has never been built", cache)
            return Err(GraphError.CacheCorrupt)
        root = Path(root_str)
        stale_path = _first_stale_cached_file(conn, root)
        if stale_path is not None:
            _log.warning("load_graph: %s drifted from cache", stale_path)
            return Err(GraphError.CacheStale)
        # T-0402: G1, a hash-only staleness loop is blind to files added
        # since the last build (they simply have no cache row to compare
        # against). Catch that shape too, or a load-only reader silently
        # operates on an incomplete graph forever, never re-triggering a
        # rebuild.
        exclude_globs = _load_exclude_globs(root)
        added_path = _first_added_file(conn, root, exclude_globs)
        if added_path is not None:
            _log.warning("load_graph: %s added since cache built", added_path)
            return Err(GraphError.CacheStale)
        snapshot = _cache.load_all(conn)
    except _cache.CacheLocked as exc:
        # T-1423: contended, not corrupt -- distinct from the OperationalError
        # branch below, which is genuine schema drift.
        _log.error("load_graph: cache lock never released at %s: %s", cache, exc)
        return Err(GraphError.CacheLocked)
    except sqlite3.OperationalError as exc:
        # T-0799: schema drift (missing table/column from a pre-migration
        # cache.db) surfaces here as a query-time OperationalError, not at
        # connect time -- a read-only connection cannot self-heal it, so
        # treat it exactly like the corrupt-bytes case: give up and let
        # the writer path rebuild.
        _log.error("load_graph: schema mismatch/unreadable cache at %s: %s", cache, exc)
        return Err(GraphError.CacheCorrupt)
    except sqlite3.DatabaseError as exc:
        # A read-only connection cannot self-heal a garbage/corrupt file
        # the way `connect()` does (T-0232) -- that would require a write.
        # Corrupt bytes surface as a query-time error here rather than at
        # connect time; still `CacheCorrupt`, same as the old self-healing
        # path's outcome once it found no root ever recorded.
        _log.error("load_graph: cache unreadable at %s: %s", cache, exc)
        return Err(GraphError.CacheCorrupt)
    _log.info(
        "load_graph: loaded %d symbols, %d edges",
        len(snapshot.symbols),
        len(snapshot.edges),
    )
    return Ok(snapshot)


# frob:doc docs/modules/graph.md#public-api
# frob:ticket T-0402
# frob:tests tests/test_graph.py::TestResolve.test_exact_qualname_wins_over_suffix_match  # noqa: E501
# frob:tests tests/test_graph.py::TestResolve.test_ambiguous_suffix_match
def resolve(snapshot: GraphSnapshot, ref: str) -> Result[SymbolRecord, GraphError]:
    """Resolve `ref`: exact `path::qualname`, else a unique qualname match,
    else a unique `.suffix` match.

    G10 (T-0402): exact-qualname and loose-suffix candidates used to be
    merged into one pool before counting, so a top-level `foo` and any
    `X.foo` collided into `AmbiguousSymbol` even though the bare `qualname
    == ref` hit was unambiguous on its own, and a `.suffix` hit could win
    over an exact qualname match that existed elsewhere in the pool. Exact
    qualname matches are now checked -- and count towards ambiguity --
    strictly before suffix matches are even considered.
    """
    exact = snapshot.symbols.get(ref)
    if exact is not None:
        return Ok(exact)

    qualname_matches = [
        record for record in snapshot.symbols.values() if record.id.qualname == ref
    ]
    if len(qualname_matches) == 1:
        return Ok(qualname_matches[0])
    if len(qualname_matches) > 1:
        _log.warning(
            "resolve(%r): ambiguous, %d qualname matches", ref, len(qualname_matches)
        )
        return Err(GraphError.AmbiguousSymbol)

    suffix = f".{ref}"
    suffix_matches = [
        record
        for record in snapshot.symbols.values()
        if record.id.qualname.endswith(suffix)
    ]
    if len(suffix_matches) == 1:
        return Ok(suffix_matches[0])
    if len(suffix_matches) > 1:
        _log.warning(
            "resolve(%r): ambiguous, %d suffix matches", ref, len(suffix_matches)
        )
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


# frob.graph.lock imports `resolve` back from this package, so it must be
# imported only after `resolve` is defined above -- importing it at the top
# with the rest deadlocks on a partially-initialized module (T-0362).
from frob.graph.lock import LockError, acknowledge, load_lock, write_lock  # noqa: E402

__all__ = [
    "AffectedSet",
    "BuildError",
    "BuildStats",
    "CallGraph",
    "Digests",
    "DanglingEdge",
    "DriftReport",
    "Edge",
    "EdgeKind",
    "FunctionSummary",
    "GraphError",
    "GraphSnapshot",
    "LockEntry",
    "LockError",
    "LockFile",
    "MalformedDirective",
    "OrderedCallGraph",
    "ParseFailure",
    "PrivateHelperGap",
    "SCCTimeout",
    "ScopeClosureGap",
    "StaleItem",
    "SummaryResult",
    "SymbolId",
    "SymbolRecord",
    "acknowledge",
    "affects",
    "build_call_graph",
    "build_graph",
    "build_ordered_call_graph",
    "build_reference_graph",
    "closure",
    "compute_protocol_summaries",
    "dedupe_slug",
    "edges_from",
    "edges_to",
    "fold_comment_runs",
    "is_generated_source",
    "load_graph",
    "load_lock",
    "resolve",
    "scope_doc_code_gaps",
    "scope_private_helper_gaps",
    "scope_test_gaps",
    "slugify",
    "write_lock",
]
